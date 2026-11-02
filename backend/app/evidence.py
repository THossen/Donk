"""Stateless evidence IDs + deterministic authorship rollup.

Evidence IDs encode everything needed to re-resolve them against the pinned
HEAD, so no session registry is required:

- c:<sha>            commit
- s:<path>:<line>:<n>  file snippet at HEAD (path URL-quoted)
- b:<path>:<line>:<n>  blame window at HEAD
- h:<path>:<line>      single search-hit line (resolved as 1-line snippet)

Only Git history/blame evidence is used. No invented people, files, or commits.
"""
from urllib.parse import quote, unquote

from .gittools import GitError, GitRepo


def commit_id(sha: str) -> str:
    return f"c:{sha}"


def snippet_id(path: str, line: int, n: int) -> str:
    return f"s:{quote(path, safe='')}:{line}:{n}"


def blame_id(path: str, line: int, n: int) -> str:
    return f"b:{quote(path, safe='')}:{line}:{n}"


def hit_id(path: str, line: int) -> str:
    return f"h:{quote(path, safe='')}:{line}"


def resolve(repo: GitRepo, evidence_id: str) -> dict:
    """Re-resolve an evidence ID against the repo. Raises GitError if invalid."""
    if not evidence_id or ":" not in evidence_id:
        raise GitError(f"malformed evidence id: {evidence_id!r}")
    kind, rest = evidence_id.split(":", 1)
    if kind == "c":
        sha = rest.strip()
        if len(sha) < 7 or any(c not in "0123456789abcdef" for c in sha.lower()):
            raise GitError(f"invalid commit sha in evidence id: {evidence_id!r}")
        info = repo.log("", 200)
        for c in info["commits"]:
            if c["sha"].startswith(sha) or sha.startswith(c["sha"]):
                return {"id": evidence_id, "kind": "commit", **c}
        # Fall back to a direct show for shas outside the bounded log window.
        try:
            from .gittools import _run_git

            out = _run_git(
                repo.root,
                "show",
                "-s",
                "--format=%H%x1f%an%x1f%ad%x1f%s",
                "--date=short",
                sha,
            ).strip()
            full, author, date, subject = (out.split("\x1f") + ["", "", "", ""])[:4]
            if not full:
                raise GitError(f"unknown commit: {sha}")
            return {
                "id": evidence_id,
                "kind": "commit",
                "sha": full,
                "author": author,
                "date": date,
                "subject": subject,
            }
        except GitError:
            raise GitError(f"unknown commit: {sha}")
    if kind in ("s", "b", "h"):
        parts = rest.split(":")
        if kind == "h" and len(parts) == 2:
            path = unquote(parts[0])
            line, n, want = int(parts[1]), 1, "snippet"
        elif kind in ("s", "b") and len(parts) == 3:
            path = unquote(parts[0])
            line, n = int(parts[1]), int(parts[2])
            want = "snippet" if kind == "s" else "blame"
        else:
            raise GitError(f"malformed evidence id: {evidence_id!r}")
        if want == "snippet":
            data = repo.snippet(path, line, min(n, 500))
        else:
            data = repo.blame(path, line, min(n, 2000))
        return {"id": evidence_id, "kind": want, **data}
    raise GitError(f"unknown evidence kind: {kind!r}")


def explain_authorship(
    repo: GitRepo,
    path_or_prefix: str,
    max_files: int = 8,
    log_per_file: int = 12,
    blame_lines_per_file: int = 2000,
) -> dict:
    """Deterministic authorship rollup over files matching a path/prefix.

    Distinguishes original authorship (earliest commit), recent contributions
    (latest commits), and substantial surviving contributions (blame lines).
    """
    prefix = repo.check_path(path_or_prefix) if path_or_prefix else ""
    files = repo.ls_files(prefix, max_results=max_files + 1)
    truncated_files = len(files) > max_files
    files = files[:max_files]
    if not files:
        return {
            "scope": path_or_prefix,
            "files": [],
            "contributors": [],
            "insufficient": True,
            "reason": f"no tracked files under {path_or_prefix!r}",
        }

    per_author: dict[str, dict] = {}
    file_infos: list[dict] = []

    def touch(name: str) -> dict:
        key = name or "(unknown)"
        return per_author.setdefault(
            key,
            {
                "name": key,
                "surviving_lines": 0,
                "commits": 0,
                "first_date": None,
                "last_date": None,
                "files": [],
            },
        )

    for f in files:
        try:
            blame = repo.blame(f, 1, blame_lines_per_file)
        except GitError:
            continue
        for author, count in blame["rollup"].items():
            a = touch(author)
            a["surviving_lines"] += count
            if f not in a["files"]:
                a["files"].append(f)
        try:
            log = repo.log(f, log_per_file)
        except GitError:
            log = {"commits": [], "truncated": False}
        for c in log["commits"]:
            a = touch(c["author"])
            a["commits"] += 1
            if a["first_date"] is None or c["date"] < a["first_date"]:
                a["first_date"] = c["date"]
            if a["last_date"] is None or c["date"] > a["last_date"]:
                a["last_date"] = c["date"]
            if f not in a["files"]:
                a["files"].append(f)
        last = log["commits"][0] if log["commits"] else None
        file_infos.append(
            {
                "path": f,
                "blame_lines": len(blame["lines"]),
                "recent_commits": [
                    {
                        "sha": c["sha"][:12],
                        "full_sha": c["sha"],
                        "author": c["author"],
                        "date": c["date"],
                        "subject": c["subject"],
                        "evidence_id": commit_id(c["sha"]),
                    }
                    for c in log["commits"][:5]
                ],
                "last_touched": last["date"] if last else None,
            }
        )

    contributors = sorted(
        per_author.values(),
        key=lambda a: (-a["surviving_lines"], -a["commits"], a["name"]),
    )
    for c in contributors:
        c["files"] = sorted(c["files"])[:max_files]

    # Main contributors: top by surviving lines, plus anyone within a
    # substantial share (>=25% of the top). Ambiguity is shown, not hidden.
    mains: list[str] = []
    if contributors:
        top_lines = contributors[0]["surviving_lines"]
        for c in contributors:
            if top_lines > 0 and c["surviving_lines"] >= 0.25 * top_lines:
                mains.append(c["name"])
            elif top_lines == 0 and mains == []:
                mains.append(c["name"])
            if len(mains) >= 4:
                break

    original = None
    dated = [c for c in contributors if c["first_date"]]
    if dated:
        original = min(dated, key=lambda c: c["first_date"])["name"]
    recent = None
    recent_dated = [c for c in contributors if c["last_date"]]
    if recent_dated:
        recent = max(recent_dated, key=lambda c: c["last_date"])["name"]

    return {
        "scope": path_or_prefix,
        "files": file_infos,
        "files_truncated": truncated_files,
        "contributors": contributors,
        "main_contributors": mains,
        "original_author": original,
        "most_recent_contributor": recent,
        "insufficient": False,
    }

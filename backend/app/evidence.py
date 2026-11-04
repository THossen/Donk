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


# Lockfiles and generated bundles: thousands of blame lines that say nothing
# about who wrote the code. Excluded from authorship analysis entirely.
_GENERATED_NAMES = frozenset({
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock",
    "gemfile.lock", "poetry.lock", "composer.lock", "go.sum",
})
_GENERATED_SUFFIXES = (".min.js", ".min.css", ".bundle.js", ".bundle.css",
                       ".js.map", ".css.map")


def _is_generated_noise(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].lower()
    return base in _GENERATED_NAMES or base.endswith(_GENERATED_SUFFIXES)


def _file_tier(path: str) -> tuple[int, str]:
    """Code sorts before docs/config; alphabetical within a tier (deterministic)."""
    tier = 0 if path.lower().endswith(GitRepo.CODE_EXTENSIONS) else 1
    return (tier, path)


def rank_investigated_files(
    repo: GitRepo, mentions: dict[str, int], per_dir: int = 6
) -> list[str]:
    """Rank actually-investigated paths into a deterministic file list.

    Exact tracked files pass through; directory scopes expand to their
    code-first files; unknown paths are dropped. Ordered by mention count
    so the most-investigated files survive downstream caps.
    """
    tracked = set(repo.all_files())
    counts: dict[str, int] = {}
    for path, n in mentions.items():
        if not path:
            continue
        if path in tracked:
            counts[path] = counts.get(path, 0) + n
            continue
        sub = sorted(
            (f for f in tracked if f.startswith(path.rstrip("/") + "/")),
            key=_file_tier,
        )
        for f in sub[:per_dir]:
            counts[f] = counts.get(f, 0) + n
    return sorted(counts, key=lambda f: (-counts[f], f))


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
    # Candidate set: everything under the scope (cached listing), minus
    # vendored mirrors and generated noise — a lockfile's 10k lines would
    # otherwise crown whoever ran `npm install` the main contributor.
    if prefix and prefix != ".":
        candidates = [
            f for f in repo.all_files()
            if f == prefix or f.startswith(prefix + "/")
        ]
    else:
        candidates = list(repo.all_files())
    candidates = [
        f for f in candidates
        if not f.startswith(GitRepo.SEARCH_EXCLUDED_PREFIXES)
        and not _is_generated_noise(f)
    ]
    candidates.sort(key=_file_tier)
    truncated_files = len(candidates) > max_files
    files = candidates[:max_files]
    if not files:
        return {
            "scope": path_or_prefix,
            "files": [],
            "contributors": [],
            "insufficient": True,
            "reason": f"no tracked files under {path_or_prefix!r}",
        }
    return rollup_files(
        repo, files,
        scope=path_or_prefix,
        truncated=truncated_files,
        max_files=max_files,
        log_per_file=log_per_file,
        blame_lines_per_file=blame_lines_per_file,
    )


def rollup_files(
    repo: GitRepo,
    files: list[str],
    scope: str = "",
    truncated: bool = False,
    max_files: int = 8,
    log_per_file: int = 12,
    blame_lines_per_file: int = 2000,
) -> dict:
    """Authorship rollup over an explicit file list.

    Used when the caller already knows exactly which files were investigated,
    so cards and graphs describe those files instead of a re-derived scope.
    """
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
                "file_lines": {},
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
            a["file_lines"][f] = a["file_lines"].get(f, 0) + count
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
        # Most-touched files first: the graph and cards slice from the front,
        # so alphabetical order used to surface .gitignore over real code.
        lines = c["file_lines"]
        c["files"] = sorted(c["files"], key=lambda f: (-lines.get(f, 0), f))[:max_files]

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
        "scope": scope,
        "files": file_infos,
        "files_truncated": truncated,
        "contributors": contributors,
        "main_contributors": mains,
        "original_author": original,
        "most_recent_contributor": recent,
        "insufficient": False,
    }

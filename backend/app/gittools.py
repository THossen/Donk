"""Bounded Git CLI access. The analyzed repo is treated as data: read-only, never executed."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

CACHE_TTL_S = 24 * 3600


class GitError(Exception):
    pass


def _run_git(repo: Path, *args: str, timeout_s: float = 30.0) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
    except FileNotFoundError:
        raise GitError("git executable not found on PATH")
    except subprocess.TimeoutExpired:
        raise GitError("git command timed out")
    if proc.returncode != 0:
        err = GitError((proc.stderr or proc.stdout or "git error").strip()[:300])
        err.returncode = proc.returncode  # type: ignore[attr-defined]
        raise err
    return proc.stdout


class DiskCache:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.root / f"{digest}.json"

    def get(self, key: str):
        p = self._path(key)
        try:
            if not p.exists():
                return None
            if time.time() - p.stat().st_mtime > CACHE_TTL_S:
                return None
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def put(self, key: str, value) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self._path(key).write_text(json.dumps(value), encoding="utf-8")
        except OSError:
            pass


class GitRepo:
    """Read-only, bounded git access pinned to the current HEAD."""

    def __init__(self, path: str | Path, cache: DiskCache | None = None):
        self.root = Path(path)
        if not (self.root / ".git").exists() and not (self.root / "HEAD").exists():
            # `git rev-parse` is the real check; keep a fast pre-check only.
            pass
        self.cache = cache
        try:
            self.head_sha = _run_git(self.root, "rev-parse", "HEAD").strip()
        except GitError as e:
            raise GitError(f"not a readable git repository at {self.root}: {e}")

    def _cached(self, key: str, fn):
        if self.cache is None:
            return fn()
        full = f"{self.head_sha}:{key}"
        hit = self.cache.get(full)
        if hit is not None:
            return hit
        val = fn()
        self.cache.put(full, val)
        return val

    def head_info(self) -> dict:
        out = _run_git(
            self.root, "log", "-1", "--format=%H%x1f%an%x1f%ad%x1f%s", "--date=short"
        ).strip()
        sha, author, date, subject = (out.split("\x1f") + ["", "", "", ""])[:4]
        return {"sha": sha, "author": author, "date": date, "subject": subject}

    def check_path(self, rel: str) -> str:
        """Normalize a repo-relative path; reject traversal and absolute paths."""
        if not rel or os.path.isabs(rel):
            raise GitError(f"invalid repo path: {rel!r}")
        norm = os.path.normpath(rel).replace("\\", "/")
        if norm.startswith("../") or norm == "..":
            raise GitError(f"path escapes repository: {rel!r}")
        if norm.startswith("./"):
            norm = norm[2:]
        return norm or "."

    def ls_files(self, prefix: str = "", max_results: int = 200) -> list[str]:
        prefix = self.check_path(prefix) if prefix else ""
        out = _run_git(self.root, "ls-files", "--", prefix or ".")
        files = [l for l in out.splitlines() if l]
        return files[:max_results]

    def all_files(self) -> list[str]:
        """Full tracked-file listing, cached per HEAD. For path matching."""
        return self._cached("all_files", lambda: [
            l for l in _run_git(self.root, "ls-files").splitlines() if l
        ])

    # Vendored/mirror paths excluded from content search (noise filtering).
    SEARCH_EXCLUDED_PREFIXES = (".repos/", "node_modules/")

    # Recognized code extensions: implementations sort before docs/config
    # when a bounded file set must choose which files to analyze.
    CODE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java",
                       ".rb", ".php", ".c", ".h", ".cpp", ".cs", ".swift", ".kt",
                       ".vue", ".svelte")

    def search(self, query: str, path_prefix: str = "", max_results: int = 20) -> list[dict]:
        """Fixed-string, case-insensitive content search via git grep. Bounded."""
        if not query or not query.strip():
            raise GitError("empty search query")
        if len(query) > 120:
            raise GitError("search query too long (max 120 chars)")
        args = ["grep", "-n", "-I", "-F", "-i", "--", query.strip()]
        if path_prefix:
            args += [self.check_path(path_prefix)]
        key = f"search:{query.strip().lower()}:{path_prefix}:{max_results}"

        def run():
            try:
                out = _run_git(self.root, *args)
            except GitError as e:
                # git grep exits 1 when there are no matches.
                if getattr(e, "returncode", None) == 1:
                    return {"hits": [], "truncated": False, "excluded_vendored": 0}
                raise
            # Over-fetch raw grep lines: vendored mirrors (.repos/) can consume
            # the first N raw hits, so filtering must happen before cutting.
            hits = []
            excluded = 0
            scanned = 0
            per_file: dict[str, int] = {}
            for line in out.splitlines():
                scanned += 1
                if scanned > 3000:
                    break
                # path:lineno:text
                parts = line.split(":", 2)
                if len(parts) != 3:
                    continue
                path, lineno, text = parts
                if path.startswith(self.SEARCH_EXCLUDED_PREFIXES):
                    excluded += 1
                    continue
                # Diversify: one chatty file must not fill the whole result.
                if per_file.get(path, 0) >= 4:
                    continue
                try:
                    ln = int(lineno)
                except ValueError:
                    continue
                per_file[path] = per_file.get(path, 0) + 1
                hits.append({"path": path, "line": ln, "text": text[:300]})
                if len(hits) >= max_results + 1:
                    break
            truncated = len(hits) > max_results or scanned > 2990
            return {
                "hits": hits[:max_results],
                "truncated": truncated,
                "excluded_vendored": excluded,
            }

        return self._cached(key, run)

    def snippet(self, rel_path: str, start_line: int, num_lines: int) -> dict:
        """Read bounded lines of a file at HEAD (not the working tree)."""
        if num_lines < 1 or num_lines > 500:
            raise GitError("num_lines out of range 1..500")
        if start_line < 1:
            raise GitError("start_line must be >= 1")
        path = self.check_path(rel_path)
        key = f"snippet:{path}:{start_line}:{num_lines}"

        def run():
            out = _run_git(self.root, "show", f"HEAD:{path}")
            lines = out.splitlines()
            total = len(lines)
            start_idx = start_line - 1
            if start_idx >= total:
                raise GitError(f"start_line {start_line} beyond EOF ({total} lines)")
            return {
                "path": path,
                "start_line": start_line,
                "num_lines": num_lines,
                "total_lines": total,
                "text": "\n".join(lines[start_idx : start_idx + num_lines]),
                "truncated": start_idx + num_lines < total,
            }

        return self._cached(key, run)

    def log(self, rel_path: str = "", max_count: int = 50) -> dict:
        """Bounded commit history, optionally for one path. Newest first."""
        if max_count < 1 or max_count > 200:
            raise GitError("max_count out of range 1..200")
        args = [
            "log",
            f"--max-count={max_count + 1}",
            "--format=%H%x1f%an%x1f%ad%x1f%s",
            "--date=short",
        ]
        if rel_path:
            args += ["--", self.check_path(rel_path)]
        key = f"log:{rel_path}:{max_count}"

        def run():
            out = _run_git(self.root, *args)
            commits = []
            for line in out.splitlines():
                parts = line.split("\x1f")
                if len(parts) != 4:
                    continue
                sha, author, date, subject = parts
                commits.append(
                    {"sha": sha, "author": author, "date": date, "subject": subject}
                )
            truncated = len(commits) > max_count
            return {"commits": commits[:max_count], "truncated": truncated}

        return self._cached(key, run)

    def blame(self, rel_path: str, start_line: int = 1, num_lines: int = 200) -> dict:
        """Bounded porcelain blame. Returns per-line commits + surviving-line rollup."""
        if num_lines < 1 or num_lines > 2000:
            raise GitError("num_lines out of range 1..2000")
        if start_line < 1:
            raise GitError("start_line must be >= 1")
        path = self.check_path(rel_path)
        key = f"blame:{path}:{start_line}:{num_lines}"

        def run():
            out = _run_git(
                self.root,
                "blame",
                "--line-porcelain",
                "-L",
                f"{start_line},+{num_lines}",
                "HEAD",
                "--",
                path,
            )
            lines: list[dict] = []
            cur: dict = {}
            for raw in out.splitlines():
                if raw.startswith("\t"):
                    lines.append(
                        {
                            "sha": cur.get("sha", ""),
                            "author": cur.get("author", ""),
                            "date": cur.get("author-time", ""),
                            "text": raw[1:][:200],
                        }
                    )
                    cur = {}
                    continue
                # Boundary commits (shallow history) prefix the sha with "^".
                line = raw[1:] if raw.startswith("^") else raw
                if len(line) >= 40 and line[:40].strip("0123456789abcdef") == "":
                    cur = {"sha": line[:40], "boundary": raw.startswith("^")}
                elif raw.startswith("author ") and "author" not in cur:
                    cur["author"] = raw[len("author ") :]
                elif raw.startswith("author-time "):
                    cur["author-time"] = raw[len("author-time ") :]
            rollup: dict[str, int] = {}
            for l in lines:
                rollup[l["author"] or "(unknown)"] = (
                    rollup.get(l["author"] or "(unknown)", 0) + 1
                )
            return {"path": path, "lines": lines, "rollup": rollup}

        return self._cached(key, run)

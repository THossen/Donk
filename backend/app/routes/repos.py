"""Repository endpoints: status, overview, map, listing, selection, evidence."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import evidence as ev
from .. import context as ctx
from ..gittools import GitError, GitRepo

router = APIRouter()

MAX_LISTED_REPOS = 20
MAP_TOP_DIRS = 12
MAP_SUB_DIRS = 6
MAP_MAX_DEPTH = 4


def _scan_repos() -> tuple[list[dict], bool]:
    """Configured repo plus git repos sitting next to it (names only).

    Selection is by exact directory name from this list, so callers can never
    point Donk at an arbitrary path.
    """
    configured = Path(ctx.settings.repo_path).resolve()
    parent = configured.parent
    names: dict[str, Path] = {configured.name: configured}
    try:
        siblings = sorted(
            (p for p in parent.iterdir() if p.is_dir() and (p / ".git").exists()),
            key=lambda p: p.name,
        )
    except OSError:
        siblings = []
    for p in siblings:
        names.setdefault(p.name, p)
    ordered = sorted(names.items())
    truncated = len(ordered) > MAX_LISTED_REPOS
    return (
        [{"name": n, "path": str(p), "configured": p == configured} for n, p in ordered[:MAX_LISTED_REPOS]],
        truncated,
    )


@router.get("/api/status")
def status():
    try:
        repo = ctx.get_repo()
        head = repo.head_info()
        repo_info = {
            "path": str(repo.root),
            "head_sha": head["sha"],
            "head_short": head["sha"][:12],
            "head_author": head["author"],
            "head_date": head["date"],
            "head_subject": head["subject"],
        }
    except HTTPException as e:
        repo_info = {"error": e.detail}
    return {**ctx.settings.public_status(), "repo": repo_info}


@router.get("/api/repo/overview")
def repo_overview():
    repo = ctx.get_repo()
    files = repo.all_files()
    top_dirs: dict[str, int] = {}
    for f in files:
        if f.startswith(".") or "/node_modules/" in f:
            continue  # vendored/mirror noise, same rule as content search
        d = f.rsplit("/", 1)[0] if "/" in f else "(root)"
        top = d.split("/")[0]
        top_dirs[top] = top_dirs.get(top, 0) + 1
    recent = repo.log("", 8)
    return {
        "tracked_total": len(files),
        "top_dirs": sorted(top_dirs.items(), key=lambda kv: (-kv[1], kv[0]))[:12],
        "recent_commits": [
            {**c, "evidence_id": ev.commit_id(c["sha"])} for c in recent["commits"]
        ],
        "head": repo.head_info(),
    }


def _build_repo_map(files: list[str]) -> dict:
    """Bounded directory tree with tracked-file counts, for the repo map.

    Pure function over an ls-files listing. Dotfiles and node_modules are
    excluded (same rule as the overview). Levels past MAP_MAX_DEPTH roll into
    their deepest shown ancestor; siblings past the display caps aggregate
    into "other" leaves; both are reported via ``truncated``.
    """
    kept = [f for f in files if not f.startswith(".") and "/node_modules/" not in f]
    # lineage -> files under it; full parent path -> files directly in it.
    totals: dict[tuple[str, ...], int] = {}
    directs: dict[tuple[str, ...], int] = {}
    for f in kept:
        parts = f.split("/")
        if len(parts) == 1:
            directs[()] = directs.get((), 0) + 1
            continue
        full_parent = tuple(parts[:-1])
        lineage = full_parent[:MAP_MAX_DEPTH]
        for i in range(1, len(lineage) + 1):
            p = lineage[:i]
            totals[p] = totals.get(p, 0) + 1
        if len(full_parent) <= MAP_MAX_DEPTH:
            directs[full_parent] = directs.get(full_parent, 0) + 1

    truncated = False

    def other_leaf(total: int, n_dirs: int) -> dict:
        return {"name": f"other ({n_dirs})", "path": None, "files": total, "children": []}

    def emit(path: tuple[str, ...], depth: int, cap: int) -> list[dict]:
        nonlocal truncated
        kids = sorted(
            [(p[-1], totals[p]) for p in totals if len(p) == depth + 1 and p[:depth] == path],
            key=lambda kv: (-kv[1], kv[0]),
        )
        shown, hidden = kids[:cap], kids[cap:]
        out = []
        for name, total in shown:
            p = path + (name,)
            node: dict = {"name": name, "path": "/".join(p), "files": total, "children": []}
            if depth + 1 < MAP_MAX_DEPTH:
                node["children"] = emit(p, depth + 1, MAP_SUB_DIRS)
                direct = directs.get(p, 0)
                if direct and node["children"]:
                    node["children"].append(
                        {"name": "(files)", "path": "/".join(p), "files": direct, "children": []}
                    )
            out.append(node)
        if hidden:
            truncated = True
            out.append(other_leaf(sum(n for _, n in hidden), len(hidden)))
        return out

    children = emit((), 0, MAP_TOP_DIRS)
    if directs.get((), 0):
        children.append({"name": "(root)", "path": "", "files": directs[()], "children": []})
    return {
        "tree": {"name": "(repo)", "path": "", "files": len(kept), "children": children},
        "mapped_files": len(kept),
        "truncated": truncated,
    }


@router.get("/api/repo/map")
def repo_map():
    repo = ctx.get_repo()
    return repo._cached("repo_map_v2", lambda: _build_repo_map(repo.all_files()))


@router.get("/api/repos")
def list_repos():
    scanned, truncated = _scan_repos()
    active = ctx._resolve_repo_path()
    repos = []
    for entry in scanned:
        info: dict = {"name": entry["name"], "path": entry["path"], "active": entry["path"] == active}
        try:
            repo = GitRepo(entry["path"])
            head = repo.head_info()
            info.update(
                {
                    "head_short": head["sha"][:12],
                    "head_author": head["author"],
                    "head_date": head["date"],
                    "head_subject": head["subject"],
                    "tracked_total": len(repo.all_files()),
                }
            )
        except GitError as e:
            info["error"] = str(e)[:200]
        repos.append(info)
    active_name = next((r["name"] for r in repos if r["active"]), None)
    return {"repos": repos, "active": active_name, "truncated": truncated}


class SelectRepoBody(BaseModel):
    name: str


@router.post("/api/repos/select")
def select_repo(body: SelectRepoBody):
    scanned, _ = _scan_repos()
    match = next((e for e in scanned if e["name"] == body.name), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"unknown repository: {body.name}")
    try:
        GitRepo(match["path"])
    except GitError as e:
        raise HTTPException(status_code=503, detail=f"repository unavailable: {e}")
    ctx.set_active_repo(match["path"])
    return {"active": match["name"]}


@router.get("/api/evidence")
def get_evidence(id: str):
    repo = ctx.get_repo()
    try:
        return ev.resolve(repo, id)
    except GitError as e:
        raise HTTPException(status_code=404, detail=str(e))

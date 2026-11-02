"""Process-wide runtime state: settings, action store, active repository."""
import threading
from pathlib import Path

from fastapi import HTTPException

from .config import Settings
from .gittools import DiskCache, GitError, GitRepo
from .store import Store

settings = Settings()
store = Store(settings.db_path)

_active_repo_path: str | None = None
_active_repo_lock = threading.Lock()


def _resolve_repo_path() -> str:
    """Active repo when one was selected, else the configured repo."""
    with _active_repo_lock:
        if _active_repo_path is not None:
            return _active_repo_path
        return str(Path(settings.repo_path).resolve())


def set_active_repo(path: str | None) -> None:
    """Point Donk at another scanned repository (or reset to configured)."""
    global _active_repo_path
    with _active_repo_lock:
        _active_repo_path = path


def get_repo() -> GitRepo:
    try:
        return GitRepo(_resolve_repo_path(), DiskCache(Path(settings.cache_dir) / "git"))
    except GitError as e:
        raise HTTPException(status_code=503, detail=f"repository unavailable: {e}")

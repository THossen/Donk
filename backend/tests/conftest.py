"""Shared fixtures: build tiny deterministic git repos in tmp_path."""
import os
import subprocess

import pytest


def git(repo, *args, **kwargs):
    env = {**os.environ, **kwargs.pop("env", {})}
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, env=env
    )


def commit_as(repo, name, email, message, files: dict[str, str], date: str):
    for rel, content in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        git(repo, "add", rel)
    env = {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }
    git(repo, "commit", "-m", message, env=env)


@pytest.fixture()
def mini_repo(tmp_path):
    """auth/login.py: Ana writes it, Beth extends it, Cara formats one line."""
    repo = tmp_path / "mini"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.com")
    commit_as(
        repo, "Ana", "ana@example.com", "add login",
        {"auth/login.py": "def login(u, p):\n    return check(u, p)\n"},
        "2024-01-01T10:00:00",
    )
    commit_as(
        repo, "Beth", "beth@example.com", "validate input",
        {"auth/login.py": "def login(u, p):\n    if not u:\n        return False\n    return check(u, p)\n"},
        "2024-02-01T10:00:00",
    )
    commit_as(
        repo, "Cara", "cara@example.com", "format",
        {"auth/login.py": "def login(u, p):\n    if not u:\n        return False\n    return check(u, p)\n\n"},
        "2024-03-01T10:00:00",
    )
    commit_as(
        repo, "Beth", "beth@example.com", "add logout",
        {"auth/logout.py": "def logout(u):\n    clear(u)\n"},
        "2024-04-01T10:00:00",
    )
    return repo


@pytest.fixture()
def tie_repo(tmp_path):
    """Two authors with equal surviving lines -> ambiguity must show both."""
    repo = tmp_path / "tie"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.com")
    commit_as(
        repo, "Dan", "dan@example.com", "part one",
        {"mod/a.py": "x = 1\ny = 2\n"},
        "2024-01-01T10:00:00",
    )
    commit_as(
        repo, "Erin", "erin@example.com", "part two",
        {"mod/a.py": "x = 1\ny = 2\nz = 3\nw = 4\n"},
        "2024-02-01T10:00:00",
    )
    return repo

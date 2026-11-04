"""Attribution: original author, main contributor, ambiguity, unknown scope."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import evidence as ev
from app.gittools import GitRepo


def test_original_vs_main_vs_recent(mini_repo):
    repo = GitRepo(mini_repo)
    rollup = ev.explain_authorship(repo, "auth")
    assert not rollup.get("insufficient")
    assert rollup["original_author"] == "Ana"
    assert rollup["most_recent_contributor"] == "Beth"
    # Beth has the most surviving lines across auth/.
    assert rollup["main_contributors"][0] == "Beth"
    by_name = {c["name"]: c for c in rollup["contributors"]}
    assert by_name["Beth"]["surviving_lines"] >= by_name["Ana"]["surviving_lines"]
    assert by_name["Ana"]["commits"] >= 1


def test_ambiguity_shows_multiple(tie_repo):
    repo = GitRepo(tie_repo)
    rollup = ev.explain_authorship(repo, "mod")
    assert set(rollup["main_contributors"]) == {"Dan", "Erin"}


@pytest.fixture()
def noisy_repo(tmp_path):
    """Docs/config/lockfiles alphabetically ahead of the real code."""
    repo = tmp_path / "noisy"
    repo.mkdir()

    def git(*args, **env):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                       env={"PATH": os.environ["PATH"], **env})

    def commit(name, email, message, files, date):
        for rel, content in files.items():
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            git("add", rel)
        git("commit", "-m", message, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
            GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email,
            GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)

    git("init")
    git("config", "user.name", "t")
    git("config", "user.email", "t@e.com")
    docs = {f"a{i}.md": f"doc {i}\n" for i in range(1, 10)}
    commit("Ana", "ana@e.com", "docs", {
        "README.md": "".join(f"readme line {i}\n" for i in range(30)),
        ".gitignore": "*.pyc\n.env\n",
        "package-lock.json": "".join(f'{{"pkg": {i}}}\n' for i in range(50)),
        **docs,
    }, "2024-01-01T10:00:00")
    commit("Beth", "beth@e.com", "code", {
        "app.py": "".join(f"x{i} = 1\n" for i in range(40)),
        "lib/util.py": "".join(f"y{i} = 2\n" for i in range(20)),
        "server.py": "".join(f"z{i} = 3\n" for i in range(50)),
    }, "2024-02-01T10:00:00")
    return repo


def test_rollup_skips_generated_noise_and_prefers_code(noisy_repo):
    repo = GitRepo(noisy_repo)
    rollup = ev.explain_authorship(repo, "")
    paths = [f["path"] for f in rollup["files"]]
    # The 50-line lockfile is excluded entirely, not ranked.
    assert "package-lock.json" not in paths
    # All three code files make the bounded set of 8 despite 12
    # alphabetically-earlier docs/config competitors.
    assert {"app.py", "lib/util.py", "server.py"} <= set(paths)
    assert rollup["files_truncated"] is True
    # Beth's 110 code lines beat Ana's docs; the lockfile can't crown Ana.
    assert rollup["main_contributors"][0] == "Beth"


def test_contributor_files_ranked_by_lines(noisy_repo):
    repo = GitRepo(noisy_repo)
    rollup = ev.explain_authorship(repo, "")
    by_name = {c["name"]: c for c in rollup["contributors"]}
    # Line-ranked: README (30) before .gitignore (2), not alphabetical.
    assert by_name["Ana"]["files"][0] == "README.md"
    assert by_name["Beth"]["files"] == ["server.py", "app.py", "lib/util.py"]
    assert by_name["Beth"]["file_lines"] == {
        "server.py": 50, "app.py": 40, "lib/util.py": 20,
    }


def test_rank_investigated_files(mini_repo):
    repo = GitRepo(mini_repo)
    ranked = ev.rank_investigated_files(
        repo, {"auth/login.py": 3, "auth": 1, "nope/x.py": 5, "": 2}
    )
    # Unknown and empty paths are dropped; the directory expands to its files.
    assert ranked[0] == "auth/login.py"
    assert set(ranked) == {"auth/login.py", "auth/logout.py"}


def test_rollup_files_matches_prefix_rollup(mini_repo):
    repo = GitRepo(mini_repo)
    via_prefix = ev.explain_authorship(repo, "auth")
    via_files = ev.rollup_files(repo, ["auth/login.py", "auth/logout.py"], scope="auth")
    assert [c["name"] for c in via_files["contributors"]] == [
        c["name"] for c in via_prefix["contributors"]
    ]
    assert via_files["main_contributors"] == via_prefix["main_contributors"]
    assert via_files["scope"] == "auth"


def test_unknown_scope_is_insufficient(mini_repo):
    repo = GitRepo(mini_repo)
    rollup = ev.explain_authorship(repo, "does/not/exist")
    assert rollup["insufficient"] is True


def test_evidence_ids_resolve(mini_repo):
    repo = GitRepo(mini_repo)
    head = repo.head_info()["sha"]
    assert ev.resolve(repo, ev.commit_id(head))["kind"] == "commit"
    snip = ev.resolve(repo, ev.snippet_id("auth/login.py", 1, 2))
    assert snip["kind"] == "snippet" and "def login" in snip["text"]
    blame = ev.resolve(repo, ev.blame_id("auth/login.py", 1, 4))
    assert blame["kind"] == "blame" and len(blame["lines"]) == 4


def test_check_path_keeps_dot_dirs(mini_repo):
    repo = GitRepo(mini_repo)
    assert repo.check_path(".agents/skills/x") == ".agents/skills/x"
    assert repo.check_path("./auth/login.py") == "auth/login.py"
    assert repo.check_path("auth/login.py") == "auth/login.py"


def test_invalid_evidence_rejected(mini_repo):
    repo = GitRepo(mini_repo)
    import pytest

    from app.gittools import GitError

    with pytest.raises(GitError):
        ev.resolve(repo, "c:deadbee")
    with pytest.raises(GitError):
        ev.resolve(repo, "s:../escape.py:1:5")
    with pytest.raises(GitError):
        ev.resolve(repo, "nope")

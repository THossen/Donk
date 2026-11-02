"""Attribution: original author, main contributor, ambiguity, unknown scope."""
import sys
from pathlib import Path

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

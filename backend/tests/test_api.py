"""Endpoint-level tests WITHOUT sockets (sandbox blocks loopback binds).

Calls FastAPI route functions directly and consumes the sync ask event
generator. Same coverage as an HTTP test, runnable everywhere.
"""
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import context as app_context
from app.routes import ask as ask_routes
from app.routes import email as email_routes
from app.routes import investigations as inv_routes
from app.routes import repos as repos_routes
from app.services import investigate as investigate_svc
from app.config import Settings
from app.store import Store


@pytest.fixture()
def env(mini_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "")
    s = Settings(
        MODEL_API_KEY="",
        REPO_PATH=str(mini_repo),
        EMAIL_MODE="outbox",
        DEMO_MODE=True,
        DEMO_EMAIL_REDIRECT="demo@example.com",
        OUTBOX_DIR=str(tmp_path / "outbox"),
        DB_PATH=str(tmp_path / "api.db"),
        TEAM_PATH=str(tmp_path / "team.json"),
        CACHE_DIR=str(tmp_path / "cache"),
    )
    monkeypatch.setattr(app_context, "settings", s)
    monkeypatch.setattr(app_context, "store", Store(s.db_path))
    return s


def collect_events(question: str) -> list[dict]:
    return list(investigate_svc._ask_event_stream(question))


def test_status(env):
    body = repos_routes.status()
    assert body["model_configured"] is False
    assert body["repo"]["head_short"]
    assert "MODEL_API_KEY" not in json.dumps(body)


def test_repo_overview(env, mini_repo):
    from app import evidence as ev
    from app.gittools import GitRepo

    body = repos_routes.repo_overview()
    assert body["tracked_total"] >= 2
    assert any(d == "auth" for d, _ in body["top_dirs"])
    assert len(body["recent_commits"]) >= 1
    repo = GitRepo(mini_repo)
    for c in body["recent_commits"]:
        assert ev.resolve(repo, c["evidence_id"])["kind"] == "commit"


def test_ask_fallback_flow(env):
    events = collect_events("Who worked on login?")
    kinds = [e["type"] for e in events]
    assert "stage" in kinds and "tool" in kinds and "answer" in kinds
    answer = next(e["answer"] for e in events if e["type"] == "answer")
    assert "Beth" in answer["contributor_names"]
    assert answer["verification"]["verified"] is True


def test_ask_unknown_question(env):
    events = collect_events("Who built the quantum flux capacitor?")
    answers = [e["answer"] for e in events if e["type"] == "answer"]
    assert answers and answers[0]["insufficient"] is True


def test_build_repo_map_pure():
    body = repos_routes._build_repo_map([
        "README.md",
        "server/auth.py",
        "server/pairing/store.py",
        "server/pairing/grant.py",
        "client/app.ts",
        ".hidden/x",
        "x/node_modules/y.js",
    ])
    assert body["mapped_files"] == 5
    assert body["truncated"] is False
    kids = {c["name"]: c for c in body["tree"]["children"]}
    assert kids["server"]["files"] == 3
    subs = {c["name"]: c for c in kids["server"]["children"]}
    assert subs["pairing"]["files"] == 2
    assert subs["pairing"]["path"] == "server/pairing"
    assert subs["(files)"]["files"] == 1
    assert kids["client"]["files"] == 1
    assert kids["client"]["children"] == []
    assert kids["(root)"]["files"] == 1


def test_build_repo_map_deep():
    body = repos_routes._build_repo_map([
        "a/b/c/d/e.py",
        "a/b/c/d/e/f.py",
        "a/b/top.py",
        "a/direct.py",
    ])
    assert body["mapped_files"] == 4
    assert body["truncated"] is False
    a = next(c for c in body["tree"]["children"] if c["name"] == "a")
    assert a["files"] == 4
    b = next(c for c in a["children"] if c["name"] == "b")
    assert b["files"] == 3
    c = next(c for c in b["children"] if c["name"] == "c")
    assert c["files"] == 2
    d = next(c for c in c["children"] if c["name"] == "d")
    # d is at max depth: no children shown, deeper files roll into its count.
    assert d["files"] == 2 and d["children"] == []
    subs = {c["name"]: c for c in b["children"]}
    assert subs["(files)"]["files"] == 1
    asubs = {c["name"]: c for c in a["children"]}
    assert asubs["(files)"]["files"] == 1


def test_repo_map_endpoint(env):
    body = repos_routes.repo_map()
    assert body["mapped_files"] >= 2
    assert body["truncated"] is False
    kids = {c["name"]: c for c in body["tree"]["children"]}
    assert kids["auth"]["files"] == 2


def test_repo_map_truncation(tmp_path, monkeypatch):
    import subprocess

    def git(repo, *args, **env):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                       env={"PATH": os.environ["PATH"], **env})

    repo = tmp_path / "wide"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@e.com")
    for i in range(15):
        p = repo / f"d{i:02d}" / "f.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x = 1\n", encoding="utf-8")
        git(repo, "add", f"d{i:02d}/f.py")
    author = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e.com",
              "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e.com"}
    git(repo, "commit", "-m", "wide", **author)

    monkeypatch.setenv("MODEL_API_KEY", "")
    s = Settings(
        MODEL_API_KEY="", REPO_PATH=str(repo), EMAIL_MODE="outbox",
        DEMO_MODE=True, DEMO_EMAIL_REDIRECT="demo@example.com",
        OUTBOX_DIR=str(tmp_path / "outbox"), DB_PATH=str(tmp_path / "map.db"),
        TEAM_PATH=str(tmp_path / "team.json"), CACHE_DIR=str(tmp_path / "cache"),
    )
    monkeypatch.setattr(app_context, "settings", s)
    monkeypatch.setattr(app_context, "store", Store(s.db_path))
    body = repos_routes.repo_map()
    assert body["mapped_files"] == 15
    assert body["truncated"] is True
    names = [c["name"] for c in body["tree"]["children"]]
    assert len(names) == 13  # 12 dirs + aggregated "other (3)"
    assert names[-1] == "other (3)"
    other = body["tree"]["children"][-1]
    assert other["files"] == 3 and other["path"] is None


@pytest.fixture()
def active_repo_reset():
    yield
    app_context.set_active_repo(None)


def _init_repo(path):
    import subprocess

    def git(*args, **env):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True,
                       env={"PATH": os.environ["PATH"], **env})
    path.mkdir(parents=True, exist_ok=True)
    git("init")
    git("config", "user.name", "t")
    git("config", "user.email", "t@e.com")
    (path / "f.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "f.py")
    git("commit", "-m", "init", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e.com",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e.com")


def test_repos_list(env, mini_repo, tmp_path, active_repo_reset):
    _init_repo(tmp_path / "second")
    body = repos_routes.list_repos()
    names = [r["name"] for r in body["repos"]]
    assert names == ["mini", "second"]
    assert body["active"] == "mini"
    assert body["truncated"] is False
    mini = next(r for r in body["repos"] if r["name"] == "mini")
    assert mini["active"] is True and mini["tracked_total"] >= 2
    assert mini["head_short"]


def test_repos_select(env, mini_repo, tmp_path, active_repo_reset):
    _init_repo(tmp_path / "second")
    out = repos_routes.select_repo(repos_routes.SelectRepoBody(name="second"))
    assert out == {"active": "second"}
    assert repos_routes.list_repos()["active"] == "second"
    assert app_context.get_repo().root.name == "second"
    with pytest.raises(HTTPException) as e:
        repos_routes.select_repo(repos_routes.SelectRepoBody(name="../nope"))
    assert e.value.status_code == 404


def test_evidence_roundtrip_and_404(env):
    body = repos_routes.get_evidence("s:auth%2Flogin.py:1:2")
    assert "def login" in body["text"]
    with pytest.raises(HTTPException) as e:
        repos_routes.get_evidence("c:deadbee")
    assert e.value.status_code == 404


def test_propose_send_duplicate(env, tmp_path):
    draft = email_routes.propose_email(
        email_routes.ProposeBody(
            contributor="Beth", question="How does login work?",
            scope="auth", evidence_ids=[], suggested=False,
        )
    )
    assert draft["status"] == "pending"
    assert draft["delivers_to"] == "demo@example.com"

    s1 = email_routes.send_action(
        draft["id"],
        email_routes.SendBody(confirmed=True, idempotency_key=draft["idempotency_key"]),
    )
    assert s1["status"] == "outbox_saved" and s1["duplicate"] is False
    assert (tmp_path / "outbox" / f"{draft['id']}.eml").exists()

    s2 = email_routes.send_action(
        draft["id"],
        email_routes.SendBody(confirmed=True, idempotency_key=draft["idempotency_key"]),
    )
    assert s2["duplicate"] is True

    actions = email_routes.activity()["actions"]
    assert any(a["id"] == draft["id"] and a["status"] == "outbox_saved" for a in actions)


def _propose_beth():
    return email_routes.propose_email(
        email_routes.ProposeBody(
            contributor="Beth", question="How does login work?",
            scope="auth", evidence_ids=[], suggested=False,
        )
    )


def test_get_action_resume_payload(env):
    draft = _propose_beth()
    body = email_routes.get_action(draft["id"])
    assert body["subject"] == draft["subject"]
    assert body["body"] == draft["body"]
    assert body["idempotency_key"] == draft["idempotency_key"]
    assert body["demo_mode"] is True
    assert "Beth" in body["delivery_notice"]
    with pytest.raises(HTTPException) as e:
        email_routes.get_action("nope")
    assert e.value.status_code == 404


def test_discard_route_and_activity_label(env):
    draft = _propose_beth()
    out = email_routes.discard_action(draft["id"])
    assert out["status"] == "discarded"
    assert out["human_status"] == "Discarded"
    row = next(
        a for a in email_routes.activity()["actions"] if a["id"] == draft["id"]
    )
    assert row["human_status"] == "Discarded"
    # Discarding twice, or sending a discarded draft, is rejected.
    with pytest.raises(HTTPException) as e:
        email_routes.discard_action(draft["id"])
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        email_routes.discard_action("nope")
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        email_routes.send_action(
            draft["id"],
            email_routes.SendBody(confirmed=True, idempotency_key=draft["idempotency_key"]),
        )
    assert e.value.status_code == 409


def test_pending_activity_label(env):
    draft = _propose_beth()
    row = next(
        a for a in email_routes.activity()["actions"] if a["id"] == draft["id"]
    )
    assert row["human_status"] == "Pending review — resume or discard"


def test_ask_records_history(env):
    # Recording happens eagerly when /api/ask is hit; the stream itself
    # is never consumed here (sandbox blocks the sockets that needs).
    ask_routes.ask(ask_routes.AskBody(question="who wrote login?"))
    qs = ask_routes.get_history()["questions"]
    assert len(qs) == 1
    assert qs[0]["question"] == "who wrote login?"
    assert qs[0]["repo"] == env.repo_path


def test_investigations_routes(env):
    inv_id = app_context.store.create_investigation(
        "Who built login?", app_context.settings.repo_path
    )
    app_context.store.append_turn(inv_id, "Who built login?", {"headline": "Beth."})
    row = next(
        i for i in inv_routes.list_investigations()["investigations"]
        if i["id"] == inv_id
    )
    assert row["turn_count"] == 1 and row["title"] == "Who built login?"
    got = inv_routes.get_investigation(inv_id)
    assert got["turns"][0]["answer"]["headline"] == "Beth."
    assert inv_routes.delete_investigation(inv_id) == {"deleted": inv_id}
    with pytest.raises(HTTPException) as e:
        inv_routes.get_investigation(inv_id)
    assert e.value.status_code == 404


def test_stream_creates_and_continues_thread(env):
    e1 = list(investigate_svc._ask_event_stream("Who worked on login?"))
    ans1 = next(e for e in e1 if e["type"] == "answer")
    tid = ans1["thread_id"]
    assert tid
    inv = app_context.store.get_investigation(tid)
    assert len(inv["turns"]) == 1
    assert inv["turns"][0]["question"] == "Who worked on login?"

    e2 = list(investigate_svc._ask_event_stream("And who else touched it?", tid))
    ans2 = next(e for e in e2 if e["type"] == "answer")
    assert ans2["thread_id"] == tid
    assert len(app_context.store.get_investigation(tid)["turns"]) == 2
    # The fallback followed up in the prior scope instead of failing cold.
    assert ans2["answer"]["scope"] == "auth"
    assert ans2["answer"].get("continued") is True
    assert "Beth" in ans2["answer"]["contributor_names"]


def test_stream_thread_repo_mismatch_starts_new(env):
    ghost = app_context.store.create_investigation("t", "/some/other/repo")
    app_context.store.append_turn(ghost, "q", {
        "headline": "h", "scope": "auth", "evidence_ids": [],
        "contributor_names": [], "investigated_files": [],
    })
    e = list(investigate_svc._ask_event_stream("Who worked on login?", ghost))
    ans = next(x for x in e if x["type"] == "answer")
    assert ans["thread_id"] != ghost
    assert len(app_context.store.get_investigation(ghost)["turns"]) == 1


def test_history_list_delete_clear(env):
    app_context.store.record_question("first?", "r")
    app_context.store.record_question("second?", "r")
    qs = ask_routes.get_history()["questions"]
    assert [q["question"] for q in qs] == ["second?", "first?"]
    assert ask_routes.get_history(limit=1)["questions"][0]["question"] == "second?"
    assert ask_routes.delete_history_item(qs[0]["id"]) == {"deleted": qs[0]["id"]}
    assert [q["question"] for q in ask_routes.get_history()["questions"]] == ["first?"]
    with pytest.raises(HTTPException) as e:
        ask_routes.delete_history_item(999999)
    assert e.value.status_code == 404
    assert ask_routes.clear_history() == {"deleted": 1}
    assert ask_routes.get_history()["questions"] == []

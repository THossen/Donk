"""Investigation: fallback keywords plus the model tool loop's wire shape."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import evidence as ev
from app.config import Settings
from app.gittools import GitRepo
from app.llm_service import ModelService, fallback_investigate


def settings():
    return Settings(
        MODEL_API_KEY="",
        REPO_PATH=".",
        GIT_MAX_COMMITS=50,
        GIT_MAX_BLAME_LINES=200,
        SEARCH_MAX_RESULTS=20,
        SNIPPET_MAX_LINES=80,
    )


def test_search_no_match_returns_empty(mini_repo):
    repo = GitRepo(mini_repo)
    res = repo.search("zzz-no-such-token-zzz", "", 10)
    assert res["hits"] == []


def test_fallback_unknown_question_is_insufficient(mini_repo):
    repo = GitRepo(mini_repo)
    out = fallback_investigate(repo, "Who built the quantum flux capacitor?", settings())
    assert out["answer"]["insufficient"] is True
    assert "Insufficient evidence" in out["answer"]["headline"]


def test_fallback_finds_auth_contributors(mini_repo):
    repo = GitRepo(mini_repo)
    out = fallback_investigate(repo, "Who worked on login?", settings())
    answer = out["answer"]
    assert answer.get("insufficient") is not True
    assert "Beth" in answer["contributor_names"]
    # Every cited id must resolve against the snapshot.
    for eid in answer["evidence_ids"]:
        assert ev.resolve(repo, eid)["id"] == eid


def test_model_loop_sends_responses_native_tool_results(mini_repo, monkeypatch):
    """Follow-ups echo function_call + function_call_output.

    The Responses API rejects Chat-style {"role": "tool"} input items
    with 400, so the loop must never send them.
    """
    seen_payloads = []
    turns = [
        {"output": [
            {"type": "function_call", "id": "fc_1", "call_id": "call_1",
             "name": "search_files", "arguments": '{"query": "login"}',
             "status": "completed"},
        ]},
        {"output": [
            {"type": "message", "id": "m_1", "role": "assistant",
             "status": "completed",
             "content": [{"type": "output_text",
                          "text": ('{"headline": "Beth wrote login.",'
                                   ' "findings": [],'
                                   ' "contributor_names": ["Beth"],'
                                   ' "evidence_ids": [],'
                                   ' "suggested_question": ""}')} ]},
        ]},
    ]

    def fake_post(self, payload):
        seen_payloads.append(payload)
        return turns[min(len(seen_payloads) - 1, len(turns) - 1)]

    monkeypatch.setattr(ModelService, "_post", fake_post)
    svc = ModelService(Settings(MODEL_API_KEY="test-key", REPO_PATH="."))
    out = svc.investigate(GitRepo(mini_repo), "Who worked on login?")
    assert out["answer"]["contributor_names"] == ["Beth"]
    assert len(seen_payloads) == 2
    followup = seen_payloads[1]["input"]
    assert not any(
        isinstance(i, dict) and i.get("role") == "tool" for i in followup
    )
    outputs = [
        i for i in followup
        if isinstance(i, dict) and i.get("type") == "function_call_output"
    ]
    assert len(outputs) == 1
    assert outputs[0]["call_id"] == "call_1"
    echoed = [
        i for i in followup
        if isinstance(i, dict) and i.get("type") == "function_call"
    ]
    assert len(echoed) == 1 and echoed[0]["call_id"] == "call_1"

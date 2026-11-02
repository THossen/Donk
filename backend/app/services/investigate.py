"""Investigation orchestration: run the agent, verify, enrich the answer."""
import json
import logging
import queue
import threading

from fastapi import HTTPException

from .. import evidence as ev
from .. import context as ctx
from ..gittools import GitError, GitRepo
from ..llm_service import ModelService, fallback_investigate
from ..verify import verify_answer

log = logging.getLogger("donk")


def _enrich_answer(repo: GitRepo, answer: dict) -> dict:
    """Attach full contributor cards (files/commits/dates) for named contributors."""
    names = answer.get("contributor_names", [])[:4]
    scope = answer.get("scope", "")
    rollup = answer.get("rollup")
    if rollup is None and names:
        try:
            rollup = ev.explain_authorship(repo, scope or "")
        except GitError:
            rollup = None
    cards: list[dict] = []
    if rollup and not rollup.get("insufficient"):
        by_name = {c["name"]: c for c in rollup["contributors"]}
        for n in names:
            c = by_name.get(n)
            if c:
                cards.append(c)
        if not cards:
            cards = rollup["contributors"][:3]
        mains = set(rollup.get("main_contributors", []))
        for c in cards:
            c["is_main"] = c["name"] in mains
    # Attach recent commits with evidence ids for card display.
    for c in cards:
        c["evidence_ids"] = []
    answer["contributors"] = cards
    answer["scope"] = scope
    if rollup and not rollup.get("insufficient"):
        answer["files"] = rollup["files"][:8]
        answer["files_truncated"] = rollup.get("files_truncated", False)
        answer["original_author"] = rollup.get("original_author")
        answer["most_recent_contributor"] = rollup.get("most_recent_contributor")
    return answer


def _ask_event_stream(question: str):
    """Sync event generator behind /api/ask. Yields plain event dicts."""
    try:
        repo = ctx.get_repo()
    except HTTPException as e:
        yield {"type": "error", "detail": e.detail}
        return
    yield {"type": "stage", "phase": "starting", "detail": question[:120]}
    if ctx.settings.model_configured:
        yield {"type": "stage", "phase": "asking_model", "detail": ctx.settings.model_id}
    else:
        yield {"type": "stage", "phase": "no_model_key", "detail": "MODEL_API_KEY not set â€” deterministic local analysis"}

    q: queue.Queue = queue.Queue()

    def worker():
        try:
            if ctx.settings.model_configured:
                result = ModelService(ctx.settings).investigate(repo, question, on_event=q.put)
            else:
                result = fallback_investigate(repo, question, ctx.settings, on_event=q.put)
            q.put(("__result__", result))
        except Exception as e:  # noqa: BLE001 - reported via SSE, key redacted below
            q.put(("__error__", e))

    threading.Thread(target=worker, daemon=True).start()
    result = None
    while True:
        item = q.get()
        if isinstance(item, tuple):
            kind, payload = item
            if kind == "__result__":
                result = payload
                break
            detail = str(payload)[:300]
            if ctx.settings.model_api_key and ctx.settings.model_api_key in detail:
                detail = detail.replace(ctx.settings.model_api_key, "[redacted]")
            log.exception("ask failed")
            yield {"type": "error", "detail": detail}
            return
        yield item
    try:
        answer = result["answer"]
        if ctx.settings.model_configured:
            known = set(result["known_ids"])
            texts = [json.dumps(t) for t in result["tool_log"]]
            yield {"type": "stage", "phase": "verifying", "detail": "checking evidence references"}
            verdict = verify_answer(repo, answer, known, texts)
            answer["verification"] = verdict
            # One targeted repair: drop bad ids and re-verify.
            if not verdict["verified"]:
                bad_ids = {
                    p.split(": ", 1)[1].split(" ")[0]
                    for p in verdict["problems"]
                    if p.startswith("uncited") or p.startswith("unresolvable")
                }
                answer["evidence_ids"] = [
                    i for i in answer.get("evidence_ids", []) if i not in bad_ids
                ]
                answer["verification"] = verify_answer(repo, answer, known, texts)
                answer["repaired"] = True
        else:
            answer["verification"] = {
                "checked": len(answer.get("evidence_ids", [])),
                "problems": [],
                "verified": True,
            }
        answer = _enrich_answer(repo, answer)
        yield {"type": "answer", "answer": answer}
        yield {"type": "done"}
    except Exception as e:
        detail = str(e)[:300]
        if ctx.settings.model_api_key and ctx.settings.model_api_key in detail:
            detail = detail.replace(ctx.settings.model_api_key, "[redacted]")
        log.exception("ask failed")
        yield {"type": "error", "detail": detail}

"""Investigation orchestration: run the agent, verify, enrich the answer."""
import json
import logging
import queue
import threading

from fastapi import HTTPException

from .. import evidence as ev
from .. import context as ctx
from ..actions import sanitize_suggested_question
from ..gittools import GitError, GitRepo
from ..llm_service import ModelService, fallback_investigate
from ..verify import verify_answer

log = logging.getLogger("donk")


# Files actually analyzed for cards/graphs. The investigated list is already
# ranked by mention count, so the cap keeps the most-investigated files.
_ENRICH_MAX_FILES = 8


def _derive_scope(files: list[str]) -> str:
    """Scope from analyzed files: the file itself, or their common directory."""
    if not files:
        return ""
    if len(files) == 1:
        return files[0]
    common: list[str] = []
    for parts in zip(*(f.split("/") for f in files)):
        if len(set(parts)) == 1:
            common.append(parts[0])
        else:
            break
    return "/".join(common)


def _enrich_answer(
    repo: GitRepo, answer: dict, prior_files: list[str] | None = None
) -> dict:
    """Attach full contributor cards (files/commits/dates) for named contributors.

    Cards always describe the files actually investigated — never a re-derived
    repository-wide rollup, and never strangers the answer didn't name. When a
    follow-up turn investigated nothing new, the previous turn's files carry
    over so its contributor cards stay attached.
    """
    names = answer.get("contributor_names", [])[:4]
    scope = answer.get("scope", "")
    rollup = answer.get("rollup")
    if rollup is None and names:
        investigated = [f for f in answer.get("investigated_files", []) if f]
        if not investigated and prior_files:
            investigated = [f for f in prior_files if f]
            answer["investigated_files"] = investigated
        if investigated:
            analyzed = investigated[:_ENRICH_MAX_FILES]
            scope = _derive_scope(analyzed)
            try:
                rollup = ev.rollup_files(
                    repo, analyzed, scope=scope,
                    truncated=len(investigated) > _ENRICH_MAX_FILES,
                )
            except GitError:
                rollup = None
    cards: list[dict] = []
    if rollup and not rollup.get("insufficient"):
        by_name = {c["name"]: c for c in rollup["contributors"]}
        for n in names:
            c = by_name.get(n)
            if c:
                cards.append(c)
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
    # The prompt card pre-fills from suggested_question: never let model
    # chatter addressed to the user ("do you also want...") leak into it.
    top_file = (answer.get("files") or [{}])[0].get("path", "")
    answer["suggested_question"] = sanitize_suggested_question(
        answer.get("suggested_question", ""), scope or top_file
    )
    return answer


def _ask_event_stream(question: str, thread_id: str | None = None):
    """Sync event generator behind /api/ask. Yields plain event dicts.

    With a thread_id, earlier turns give context (scope, findings, evidence)
    so follow-ups continue the same investigation. A thread only applies to
    the repo it was created on; on mismatch the ask starts a new one.
    """
    try:
        repo = ctx.get_repo()
    except HTTPException as e:
        yield {"type": "error", "detail": e.detail}
        return
    prior_turns: list[dict] = []
    prior_files: list[str] = []
    prior_ctx: dict | None = None
    if thread_id:
        thread = ctx.store.get_investigation(thread_id)
        if thread and thread.get("repo") == ctx.settings.repo_path and thread.get("turns"):
            prior_turns = thread["turns"]
            last_answer = prior_turns[-1].get("answer", {})
            prior_files = list(last_answer.get("investigated_files") or [])
            if not prior_files:
                prior_files = [
                    f.get("path", "")
                    for f in last_answer.get("files", [])
                    if isinstance(f, dict)
                ]
            prior_ctx = {
                "scope": last_answer.get("scope", ""),
                "contributor_names": last_answer.get("contributor_names", []),
                "evidence_ids": last_answer.get("evidence_ids", []),
                "investigated_files": prior_files,
            }
        else:
            thread_id = None
    yield {"type": "stage", "phase": "starting", "detail": question[:120]}
    if ctx.settings.model_configured:
        yield {"type": "stage", "phase": "asking_model", "detail": ctx.settings.model_id}
    else:
        yield {"type": "stage", "phase": "no_model_key", "detail": "MODEL_API_KEY not set â€” deterministic local analysis"}

    q: queue.Queue = queue.Queue()

    def worker():
        try:
            if ctx.settings.model_configured:
                result = ModelService(ctx.settings).investigate(
                    repo, question, on_event=q.put, prior_turns=prior_turns
                )
            else:
                result = fallback_investigate(
                    repo, question, ctx.settings, on_event=q.put, prior=prior_ctx
                )
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
            # Prior turns' citations stay valid: they were tool-produced
            # against the same thread, so follow-ups may re-cite them.
            for t in prior_turns[-3:]:
                pa = t.get("answer", {})
                known.update(pa.get("evidence_ids", []))
                texts.append(json.dumps(pa)[:4000])
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
        answer = _enrich_answer(repo, answer, prior_files=prior_files)
        try:
            if not thread_id:
                thread_id = ctx.store.create_investigation(question, ctx.settings.repo_path)
            ctx.store.append_turn(thread_id, question, answer)
        except Exception:
            log.exception("failed to persist investigation turn")
            thread_id = None
        yield {"type": "answer", "answer": answer, "thread_id": thread_id}
        yield {"type": "done"}
    except Exception as e:
        detail = str(e)[:300]
        if ctx.settings.model_api_key and ctx.settings.model_api_key in detail:
            detail = detail.replace(ctx.settings.model_api_key, "[redacted]")
        log.exception("ask failed")
        yield {"type": "error", "detail": detail}

"""Email endpoints: draft proposals, confirmed sends, activity feed."""
import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import actions as email_actions
from .. import evidence as ev
from .. import context as ctx
from ..gittools import GitError
from ..llm_service import ModelService

router = APIRouter()
log = logging.getLogger("donk")


class ProposeBody(BaseModel):
    contributor: str
    question: str = ""
    scope: str = ""
    evidence_ids: list[str] = []
    suggested: bool = False  # ask Donk to suggest the question from the code


class SendBody(BaseModel):
    confirmed: bool = False
    idempotency_key: str = ""
    edited_subject: str | None = None
    edited_body: str | None = None


@router.post("/api/email/propose")
def propose_email(body: ProposeBody):
    repo = ctx.get_repo()
    question = body.question.strip()
    # If asked to suggest, ground the suggestion in real code evidence.
    if body.suggested or not question:
        grounds: list[str] = []
        for eid in body.evidence_ids[:6]:
            try:
                r = ev.resolve(repo, eid)
                if r.get("kind") == "snippet":
                    grounds.append(f"{r['path']}:{r['start_line']}")
                elif r.get("kind") == "commit":
                    grounds.append(f"{r['sha'][:12]} {r['subject']}")
            except GitError:
                continue
        scope_txt = body.scope or (grounds[0] if grounds else "the code")
        question = (
            f"Could you walk me through {scope_txt} â€” how it works today,"
            " the trickiest edge cases, and what I should know before changing it?"
        )
    model_draft = None
    if ctx.settings.model_configured:
        try:
            service = ModelService(ctx.settings)
            data = service._post(
                {
                    "model": ctx.settings.model_id,
                    "input": [
                        {"role": "system", "content": "Draft a short, specific email from one developer to a teammate. Return JSON {\"subject\": str, \"body\": str}. No invented claims."},
                        {"role": "user", "content": f"To: {body.contributor}\nAbout: {body.scope or 'the code'}\nQuestion: {question}\nKeep it under 120 words."},
                    ],
                    "temperature": 0.4,
                    "max_output_tokens": 400,
                }
            )
            text, _ = service._extract_output(data)
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                d = json.loads(text[start : end + 1])
                if isinstance(d.get("subject"), str) and isinstance(d.get("body"), str):
                    model_draft = (d["subject"].strip(), d["body"].strip())
        except Exception:
            log.exception("model draft failed; using template")
            model_draft = None
    try:
        action = email_actions.propose(
            ctx.settings, ctx.store, body.contributor, question,
            body.scope, body.evidence_ids, model_draft,
        )
    except email_actions.EmailError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return _action_payload(action)


def _action_payload(action: dict) -> dict:
    """Draft shape the confirm card renders, for both propose and resume."""
    contributor = action["contributor"]
    return {
        **action,
        "demo_mode": ctx.settings.demo_mode,
        "delivery_notice": (
            f"Demo mode: delivers to your configured demo inbox instead of {contributor}."
            if ctx.settings.demo_mode
            else f"Delivers to the approved roster address for {contributor}."
        ),
    }


@router.get("/api/actions/{action_id}")
def get_action(action_id: str):
    action = ctx.store.get(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="unknown action")
    return _action_payload(action)


@router.post("/api/actions/{action_id}/discard")
def discard_action(action_id: str):
    try:
        action = email_actions.discard(ctx.store, action_id)
    except email_actions.EmailError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return {**action, "human_status": "Discarded"}


@router.post("/api/actions/{action_id}/send")
def send_action(action_id: str, body: SendBody):
    try:
        result = email_actions.confirmed_send(
            ctx.settings, ctx.store, action_id, body.confirmed,
            body.idempotency_key, body.edited_subject, body.edited_body,
        )
    except email_actions.EmailError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    status = result["status"]
    if status == "sent":
        human = "Sent (accepted by mail server; receipt not implied)"
    elif status == "outbox_saved":
        human = "Saved to outbox"
    else:
        human = f"Failed: {result.get('error', status)}"
    return {**result, "human_status": human}


@router.get("/api/activity")
def activity():
    items = ctx.store.list_recent()
    for it in items:
        if it["status"] == "sent":
            it["human_status"] = "Sent (accepted by mail server; receipt not implied)"
        elif it["status"] == "outbox_saved":
            it["human_status"] = "Saved to outbox"
        elif it["status"] == "failed":
            it["human_status"] = f"Failed: {it.get('error', '')}"
        elif it["status"] == "pending":
            it["human_status"] = "Pending review — resume or discard"
        elif it["status"] == "discarded":
            it["human_status"] = "Discarded"
        else:
            it["human_status"] = it["status"]
    return {"actions": items}

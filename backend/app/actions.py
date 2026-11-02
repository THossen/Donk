"""Email actions: propose drafts (model or template) and confirmed sends.

Safety invariants:
- The model only proposes drafts; it can never send.
- Sending happens only via the separate confirmed-send path after explicit UI confirmation.
- In demo mode, delivery is FORCED to DEMO_EMAIL_REDIRECT.
- Outside demo mode, the recipient must be in the roster (team.json).
- Git author emails are identity signals only and NEVER delivery destinations.
- One recipient, no CC/BCC/attachments, max 5 sends/hour, idempotent sends.
"""
import json
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from .config import Settings
from .store import Store

SENDS_PER_HOUR = 5


class EmailError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def load_roster(team_path: str | Path) -> list[dict]:
    p = Path(team_path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("members", data.get("teammates", []))
    return data if isinstance(data, list) else []


def find_roster_email(roster: list[dict], contributor: str) -> str | None:
    want = contributor.strip().lower()
    for m in roster:
        if not isinstance(m, dict):
            continue
        names = [str(m.get("name", ""))]
        names += [str(a) for a in (m.get("aliases", []) or [])]
        if any(n.strip().lower() == want for n in names if n):
            email = str(m.get("email", "")).strip()
            return email or None
    return None


def resolve_delivery(settings: Settings, contributor: str) -> tuple[str, str]:
    """Return (roster_email, delivers_to). Raises EmailError if unmailable."""
    roster = load_roster(settings.team_path)
    roster_email = find_roster_email(roster, contributor) or ""
    if settings.demo_mode:
        redirect = settings.demo_email_redirect.strip()
        if not redirect:
            raise EmailError(
                "Demo mode is on but DEMO_EMAIL_REDIRECT is not configured.", 503
            )
        return roster_email, redirect
    if not roster_email:
        raise EmailError(
            f"Unknown recipient {contributor!r}: not in the approved roster.", 422
        )
    return roster_email, roster_email


def build_template_draft(contributor: str, question: str, scope: str) -> tuple[str, str]:
    scope_txt = scope or "the code"
    subject = f"[Donk] Question about {scope_txt}"
    body = (
        f"Hi {contributor},\n\n"
        f"I was looking through {scope_txt} and had a question:\n\n"
        f"{question.strip() or 'Could you walk me through how this part works and any edge cases I should know about?'}\n\n"
        "Thanks!"
    )
    return subject, body


def propose(
    settings: Settings,
    store: Store,
    contributor: str,
    question: str,
    scope: str,
    evidence_ids: list[str],
    model_draft: tuple[str, str] | None = None,
) -> dict:
    if not contributor.strip():
        raise EmailError("contributor is required")
    roster_email, delivers_to = resolve_delivery(settings, contributor)
    if model_draft:
        subject, body = model_draft
    else:
        subject, body = build_template_draft(contributor, question, scope)
    return store.create_email_action(
        contributor.strip(), roster_email, delivers_to,
        subject[:200], body[:4000], evidence_ids[:20],
    )


def discard(store: Store, action_id: str) -> dict:
    """Drop a pending draft. Anything already sent/failed is kept for the audit trail."""
    action = store.get(action_id)
    if action is None:
        raise EmailError("unknown action", 404)
    if action["status"] != "pending":
        raise EmailError(f"action is {action['status']}, cannot discard", 409)
    updated = store.transition(action_id, "pending", "discarded")
    if updated is None:
        raise EmailError("action changed, cannot discard", 409)
    return updated


def _write_outbox(settings: Settings, action: dict, subject: str, body: str) -> str:
    outbox = Path(settings.outbox_dir)
    outbox.mkdir(parents=True, exist_ok=True)
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = action["delivers_to"]
    msg["Subject"] = subject
    msg.set_content(
        f"(Donk demo: question for {action['contributor']};"
        f" routed to demo inbox, not to the contributor.)\n\n{body}"
    )
    path = outbox / f"{action['id']}.eml"
    path.write_text(msg.as_string(), encoding="utf-8")
    return str(path)


def _smtp_send(
    settings: Settings, to_addr: str, subject: str, body: str, contributor: str
) -> None:
    if not settings.smtp_host.strip():
        raise EmailError("SMTP is not configured (SMTP_HOST missing).", 503)
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_addr
    msg["Subject"] = subject
    notice = (
        f"(Donk demo redirect: this question is for {contributor}; "
        "delivery was forced to the configured demo inbox.)\n\n"
        if settings.demo_mode
        else ""
    )
    msg.set_content(notice + body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user.strip():
                smtp.login(settings.smtp_user, settings.smtp_pass)
            smtp.send_message(msg)
    except EmailError:
        raise
    except Exception as e:  # record failures accurately, never as delivered
        raise EmailError(f"SMTP send failed: {e}", 502)


def confirmed_send(
    settings: Settings,
    store: Store,
    action_id: str,
    confirmed: bool,
    idempotency_key: str,
    edited_subject: str | None = None,
    edited_body: str | None = None,
) -> dict:
    if not confirmed:
        raise EmailError("explicit confirmation is required", 400)
    action = store.get(action_id)
    if action is None:
        raise EmailError("unknown action", 404)
    if action["idempotency_key"] != idempotency_key:
        raise EmailError("idempotency key mismatch", 409)
    if action["status"] in ("sent", "outbox_saved"):
        # Idempotent replay: return the original result without resending.
        return {**action, "duplicate": True}
    if action["status"] != "pending":
        raise EmailError(f"action is {action['status']}, cannot send", 409)
    if store.sends_in_last_hour() >= SENDS_PER_HOUR:
        raise EmailError("rate limit: max 5 sends per hour", 429)
    # Re-resolve delivery at send time (redirect enforced even if config changed).
    _, delivers_to = resolve_delivery(settings, action["contributor"])
    subject = (edited_subject or action["subject"])[:200]
    body = (edited_body or action["body"])[:4000]

    locked = store.transition(action["id"], "pending", "sending")
    if locked is None:
        # Lost a race with another sender; report current state, don't resend.
        current = store.get(action_id) or action
        return {**current, "duplicate": True}
    try:
        if settings.email_mode == "smtp":
            _smtp_send(settings, delivers_to, subject, body, action["contributor"])
            final = "sent"
        else:
            _write_outbox(settings, {**action, "delivers_to": delivers_to}, subject, body)
            final = "outbox_saved"
    except EmailError as e:
        store.transition(action["id"], "sending", "failed", error=str(e)[:500])
        raise
    updated = store.transition(
        action["id"], "sending", final,
        delivers_to=delivers_to, subject=subject, body=body, sent_at=time.time(),
    )
    return {**(updated or action), "duplicate": False}

"""Email: propose-never-sends, confirm, duplicate, redirect, rate limit, failure."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import actions as email_actions
from app.config import Settings
from app.store import Store


def make_settings(tmp_path, **over):
    # Init kwargs take precedence over env/.env in pydantic-settings,
    # so these fully isolate the test from ambient configuration.
    kwargs = dict(
        DEMO_MODE=True,
        DEMO_EMAIL_REDIRECT="demo@example.com",
        EMAIL_MODE="outbox",
        OUTBOX_DIR=str(tmp_path / "outbox"),
        DB_PATH=str(tmp_path / "t.db"),
        TEAM_PATH=str(tmp_path / "team.json"),
    )
    kwargs.update(over)
    return Settings(**kwargs)


def test_propose_does_not_send(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    action = email_actions.propose(s, store, "Beth", "How does login work?", "auth", [])
    assert action["status"] == "pending"
    # Nothing written to outbox by proposing.
    assert not (tmp_path / "outbox").exists()
    # Demo redirect forced even though Beth is not in any roster.
    assert action["delivers_to"] == "demo@example.com"


def test_confirm_sends_once_and_replays(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    action = email_actions.propose(s, store, "Beth", "Q?", "auth", [])
    first = email_actions.confirmed_send(
        s, store, action["id"], True, action["idempotency_key"]
    )
    assert first["status"] == "outbox_saved" and first["duplicate"] is False
    assert (tmp_path / "outbox" / f"{action['id']}.eml").exists()
    second = email_actions.confirmed_send(
        s, store, action["id"], True, action["idempotency_key"]
    )
    assert second["duplicate"] is True and second["status"] == "outbox_saved"


def test_unconfirmed_and_unknown_recipient_rejected(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    action = email_actions.propose(s, store, "Beth", "Q?", "auth", [])
    with pytest.raises(email_actions.EmailError):
        email_actions.confirmed_send(s, store, action["id"], False, action["idempotency_key"])
    # Outside demo mode, unknown recipients are rejected.
    s2 = make_settings(tmp_path, DEMO_MODE=False)
    store2 = Store(s2.db_path)
    with pytest.raises(email_actions.EmailError) as e:
        email_actions.propose(s2, store2, "Stranger", "Q?", "auth", [])
    assert e.value.status_code == 422


def test_rate_limit(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    for i in range(5):
        a = email_actions.propose(s, store, f"P{i}", "Q?", "auth", [])
        email_actions.confirmed_send(s, store, a["id"], True, a["idempotency_key"])
    a6 = email_actions.propose(s, store, "P6", "Q?", "auth", [])
    with pytest.raises(email_actions.EmailError) as e:
        email_actions.confirmed_send(s, store, a6["id"], True, a6["idempotency_key"])
    assert e.value.status_code == 429


def test_discard_pending(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    action = email_actions.propose(s, store, "Beth", "Q?", "auth", [])
    out = email_actions.discard(store, action["id"])
    assert out["status"] == "discarded"
    assert store.get(action["id"])["status"] == "discarded"


def test_discard_rejects_sent_and_unknown(tmp_path):
    s = make_settings(tmp_path)
    store = Store(s.db_path)
    action = email_actions.propose(s, store, "Beth", "Q?", "auth", [])
    email_actions.confirmed_send(s, store, action["id"], True, action["idempotency_key"])
    with pytest.raises(email_actions.EmailError) as e:
        email_actions.discard(store, action["id"])
    assert e.value.status_code == 409
    with pytest.raises(email_actions.EmailError) as e:
        email_actions.discard(store, "nope")
    assert e.value.status_code == 404


def test_smtp_failure_recorded_not_delivered(tmp_path):
    s = make_settings(tmp_path, EMAIL_MODE="smtp", SMTP_HOST="127.0.0.1", SMTP_PORT=9)
    store = Store(s.db_path)
    action = email_actions.propose(s, store, "Beth", "Q?", "auth", [])
    with pytest.raises(email_actions.EmailError):
        email_actions.confirmed_send(s, store, action["id"], True, action["idempotency_key"])
    row = store.get(action["id"])
    assert row["status"] == "failed" and row["error"]

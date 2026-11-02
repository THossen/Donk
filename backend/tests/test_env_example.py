"""Guard: .env.example must stay a placeholder-only template.

Failing here means someone copied real values into the committed example
file (or renamed .env over it). Fix by restoring placeholders, never by
adjusting this test to accept real-looking secrets.
"""
from pathlib import Path


def _pairs():
    root = Path(__file__).resolve().parents[2]
    out = {}
    for line in (root / ".env.example").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def test_env_example_has_no_secret_values():
    vals = _pairs()
    assert vals["MODEL_API_KEY"] == "", "MODEL_API_KEY must be empty in .env.example"
    assert vals["SMTP_PASS"] == "", "SMTP_PASS must be empty in .env.example"
    assert vals["SMTP_USER"] == "", "SMTP_USER must be empty in .env.example"


def test_env_example_redirect_is_placeholder():
    redirect = _pairs()["DEMO_EMAIL_REDIRECT"]
    assert "example.com" in redirect, "DEMO_EMAIL_REDIRECT must be a placeholder"


def test_env_example_covers_required_keys():
    vals = _pairs()
    for key in ("MODEL_ID", "MODEL_BASE_URL", "REPO_PATH", "EMAIL_MODE", "DEMO_MODE"):
        assert key in vals, f"{key} missing from .env.example"

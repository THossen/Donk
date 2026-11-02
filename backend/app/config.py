"""Donk backend settings. Secrets come from the environment only."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_id: str = Field(default="muse-wonder-1.0", alias="MODEL_ID")
    model_base_url: str = Field(default="https://api.meta.ai/v1", alias="MODEL_BASE_URL")
    model_api_key: str = Field(default="", alias="MODEL_API_KEY")
    model_timeout_s: float = Field(default=30.0, alias="MODEL_TIMEOUT_S")
    model_max_output_tokens: int = Field(default=1200, alias="MODEL_MAX_OUTPUT_TOKENS")
    model_max_tool_iters: int = Field(default=6, alias="MODEL_MAX_TOOL_ITERS")

    repo_path: str = Field(default="./demo-data/BiddersBlock-v2", alias="REPO_PATH")

    git_max_commits: int = Field(default=50, alias="GIT_MAX_COMMITS")
    git_max_blame_lines: int = Field(default=200, alias="GIT_MAX_BLAME_LINES")
    search_max_results: int = Field(default=20, alias="SEARCH_MAX_RESULTS")
    snippet_max_lines: int = Field(default=80, alias="SNIPPET_MAX_LINES")

    email_mode: str = Field(default="outbox", alias="EMAIL_MODE")  # outbox | smtp
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    demo_email_redirect: str = Field(default="", alias="DEMO_EMAIL_REDIRECT")

    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_pass: str = Field(default="", alias="SMTP_PASS")
    smtp_from: str = Field(default="donk@localhost", alias="SMTP_FROM")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    cache_dir: str = Field(default=".cache", alias="CACHE_DIR")
    outbox_dir: str = Field(default="outbox", alias="OUTBOX_DIR")
    db_path: str = Field(default="donk.db", alias="DB_PATH")
    team_path: str = Field(default="team.json", alias="TEAM_PATH")

    @property
    def model_configured(self) -> bool:
        return bool(self.model_api_key.strip())

    def public_status(self) -> dict:
        """Safe subset for API responses. Never includes secrets."""
        return {
            "model_id": self.model_id,
            "model_base_url": self.model_base_url,
            "model_configured": self.model_configured,
            "email_mode": self.email_mode,
            "demo_mode": self.demo_mode,
            "demo_redirect_set": bool(self.demo_email_redirect.strip()),
            "history_limits": {
                "git_max_commits": self.git_max_commits,
                "git_max_blame_lines": self.git_max_blame_lines,
                "search_max_results": self.search_max_results,
                "snippet_max_lines": self.snippet_max_lines,
            },
        }

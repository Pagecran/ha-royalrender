"""Installation-specific configuration, kept outside the repository."""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Config:
    bridge_id: str
    api_key: str
    rr_root: str
    rr_host: str
    rr_port: int = 7773
    rr_user: str = ""
    rr_password: str = ""
    listen_host: str = "127.0.0.1"
    listen_port: int = 8787
    poll_seconds: int = 15
    error_window_seconds: int = 300
    allow_commands: bool = False
    tls_cert: str = ""
    tls_key: str = ""

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        config = cls(**data)
        if not config.bridge_id or len(config.api_key) < 32:
            raise ValueError("bridge_id and an API key of at least 32 characters are required")
        if not config.rr_host or not config.rr_root:
            raise ValueError("Royal Render host and installation path are required")
        if not 5 <= config.poll_seconds <= 300:
            raise ValueError("poll_seconds must be between 5 and 300")
        if not 30 <= config.error_window_seconds <= 86400:
            raise ValueError("error_window_seconds must be between 30 and 86400")
        if any(not 1 <= p <= 65535 for p in (config.rr_port, config.listen_port)):
            raise ValueError("Invalid TCP port")
        if bool(config.tls_cert) != bool(config.tls_key):
            raise ValueError("Both TLS certificate and key must be configured")
        if not isinstance(config.allow_commands, bool):
            raise ValueError("allow_commands must be a boolean")
        return config

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """
    Load `.env` from the project root reliably (even if the process CWD differs).
    Safe to call multiple times.
    """
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


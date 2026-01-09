"""
Environment variable loader for the MCP server.
Handles loading credentials from .env file or environment.
"""
import os
import json
from pathlib import Path

# Load .env file if it exists
from dotenv import load_dotenv

# Find .env file (look in current dir and parent dirs)
def _find_env_file() -> Path | None:
    current = Path(__file__).parent
    for _ in range(3):  # Check up to 3 levels up
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None

_env_file = _find_env_file()
if _env_file:
    load_dotenv(_env_file)


def get_google_credentials() -> dict:
    """
    Get Google Service Account credentials.

    Priority:
    1. GOOGLE_CREDENTIALS_FILE (path to JSON file)
    2. GOOGLE_CREDENTIALS_JSON (JSON string content)

    Returns:
        dict: Parsed credentials dictionary

    Raises:
        RuntimeError: If no credentials are configured
    """
    # Option 1: File path
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    if creds_file:
        creds_path = Path(creds_file)
        if not creds_path.exists():
            raise RuntimeError(f"GOOGLE_CREDENTIALS_FILE not found: {creds_file}")
        with open(creds_path, "r") as f:
            return json.load(f)

    # Option 2: JSON content
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        try:
            return json.loads(creds_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid GOOGLE_CREDENTIALS_JSON: {e}")

    raise RuntimeError(
        "No Google credentials configured. "
        "Set GOOGLE_CREDENTIALS_FILE or GOOGLE_CREDENTIALS_JSON in .env"
    )


def get_port() -> int:
    """Get server port from environment."""
    return int(os.environ.get("PORT", "8080"))


def is_hmac_required() -> bool:
    """Check if HMAC authentication is required."""
    return os.environ.get("MCP_HMAC_REQUIRED", "false").lower() in {"1", "true", "yes", "on"}


def get_hmac_secret() -> str | None:
    """Get HMAC secret if configured."""
    secret = os.environ.get("MCP_HMAC_SECRET")
    return secret if secret else None

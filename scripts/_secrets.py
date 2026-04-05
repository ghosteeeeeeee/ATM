"""
Centralized secret loader — reads from .secrets.local in project root.
All scripts should `from _secrets import BRAIN_PASSWORD, BRAIN_DB` instead of
hardcoding credentials. This file is gitignored and MUST NOT be committed.

Secrets format in .secrets.local (KEY=VALUE, one per line):
    BRAIN_DB_PASSWORD=your_password_here
    GITHUB_TOKEN=your_token_here
    HL_SIGNING_KEY=0x...
    HL_MAIN_ACCOUNT=0x...
    HL_API_KEY=your_key_here
    HL_API_SECRET=your_secret_here
"""
import pathlib
import os

_HERMES_ROOT = pathlib.Path(__file__).parent.parent
_SECRETS_FILE = _HERMES_ROOT / ".secrets.local"

# Load all key=Value pairs into module namespace
if _SECRETS_FILE.exists():
    for line in _SECRETS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            if key and val:
                globals()[key] = val

# ── Derived configs ─────────────────────────────────────────────────────────────
BRAIN_HOST     = "/var/run/postgresql"
BRAIN_DB_NAME  = "brain"
BRAIN_USER     = "postgres"
BRAIN_PASSWORD = globals().get("BRAIN_DB_PASSWORD") or os.environ.get("BRAIN_DB_PASSWORD")
if not BRAIN_PASSWORD:
    raise RuntimeError(
        "BRAIN_DB_PASSWORD not found in .secrets.local or BRAIN_DB_PASSWORD env var. "
        "Set it before running any Hermes script."
    )

# psycopg2 connection string
BRAIN_DB = (
    f"host={BRAIN_HOST} dbname={BRAIN_DB_NAME} "
    f"user={BRAIN_USER} password={BRAIN_PASSWORD}"
)

# psycopg2 dict config (for scripts that need individual params)
BRAIN_DB_DICT = {
    "host":     BRAIN_HOST,
    "database": BRAIN_DB_NAME,
    "user":     BRAIN_USER,
    "password": BRAIN_PASSWORD,
}

# Hyperliquid credentials
HL_SIGNING_KEY           = globals().get("HL_SIGNING_KEY", "")
HL_MAIN_ACCOUNT          = globals().get("HL_MAIN_ACCOUNT", "0x324a9713603863FE3A678E83d7a81E20186126E7")
SIGNING_WALLET_ADDRESS   = globals().get("SIGNING_WALLET_ADDRESS", "0x5AB4AC1b62A255284b54230b980AbA66D80A")
GITHUB_TOKEN             = globals().get("GITHUB_TOKEN", "")

"""Central config. Loads .env. Key checks are lazy so modules that don't need
Alpaca (e.g. the Featherless classifier) can import and run on their own."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Alpaca (paper) ---
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
PAPER = os.getenv("ALPACA_PAPER_TRADE", "true").lower() == "true"
PAPER_ENDPOINT = os.getenv("ALPACA_PAPER_ENDPOINT", "https://paper-api.alpaca.markets/v2")


def require_alpaca() -> tuple[str, str]:
    """Call this from the trading layer. Fails loudly only when Alpaca is actually used."""
    if not API_KEY or not SECRET_KEY:
        raise RuntimeError(
            "ALPACA_API_KEY / ALPACA_SECRET_KEY not set. "
            "Copy .env.example to .env and paste your paper keys."
        )
    return API_KEY, SECRET_KEY


# --- Risk gates (judged criterion: the write-up must cover these) ---
MAX_POSITION_PCT = 0.05      # max 5% of equity per position
MAX_DAILY_LOSS_PCT = 0.03    # halt trading after -3% on the day
MAX_OPEN_POSITIONS = 10
MIN_DTE = 7                  # don't touch contracts expiring inside a week
MAX_DTE = 45

# --- Featherless AI (partner tech; open-source model inference) ---
# $25 hackathon credit, first-come. Key from https://featherless.ai (Account -> API Keys).
FEATHERLESS_API_KEY = os.getenv("FEATHERLESS_API_KEY")
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
FEATHERLESS_MODEL = os.getenv("FEATHERLESS_MODEL", "Qwen/Qwen2.5-7B-Instruct")

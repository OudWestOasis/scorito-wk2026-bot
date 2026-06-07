"""
Centrale configuratie — leest alles uit omgevingsvariabelen.

In de cloud komen de geheimen binnen als GitHub Secrets (env-vars).
Lokaal kun je een .env gebruiken (wordt geladen als python-dotenv aanwezig is).
Er staan NOOIT echte tokens in dit bestand — alleen namen en defaults.
"""
import os

# .env laden als die er is (handig lokaal; in de cloud niet nodig).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Geheimen (komen uit env / GitHub Secrets) ------------------------------
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")

# --- Niet-geheime instellingen (met fallback) -------------------------------
STATE_FILE = _env("STATE_FILE", "state.json")
# Tijdvenster (minuten) waarin een wedstrijd als "begint zo" geldt voor pre-match.
# In de cloud pollen we minder vaak dan elke minuut, dus iets ruimer dan lokaal.
PREMATCH_WINDOW_MINUTES = int(_env("PREMATCH_WINDOW_MINUTES", "40"))
FINISHED_WINDOW_MINUTES = int(_env("FINISHED_WINDOW_MINUTES", "15"))


def require(name: str) -> str:
    """Haal een verplichte env-var op of geef een duidelijke fout."""
    val = os.environ.get(name, "")
    if not val:
        raise RuntimeError(
            f"Ontbrekende omgevingsvariabele {name!r}. "
            f"Zet 'm als GitHub Secret of in je lokale .env."
        )
    return val

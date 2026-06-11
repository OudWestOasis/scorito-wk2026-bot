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

# --- E-mail (dagelijks ochtendbericht) --------------------------------------
# SMTP-gegevens komen uit Secrets; alleen de ontvanger heeft een vaste default.
EMAIL_TO = _env("EMAIL_TO", "joris.van.iersel@outlook.com")
EMAIL_FROM = _env("EMAIL_FROM")          # leeg => valt terug op EMAIL_USER
EMAIL_SMTP_HOST = _env("EMAIL_SMTP_HOST")
EMAIL_SMTP_PORT = int(_env("EMAIL_SMTP_PORT", "587"))
EMAIL_USER = _env("EMAIL_USER")
EMAIL_PASS = _env("EMAIL_PASS")

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

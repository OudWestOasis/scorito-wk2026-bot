# Scorito WK 2026 — Telegram bot (cloud)

Draait op **GitHub Actions** (gratis) en stuurt Joris updates over zijn poule
**Oud-West Oasis**: pre-match (jouw voorspelling + topscorer-picks), live bij elk
doelpunt (stand, scorer ⭐, gaat het goed?), en post-match (gelijk/ongelijk +
punten). Vragen stellen in Telegram: `/stand`, `/week`, `/log`, `/help`.

➡️ **Opzetten doe je via [SETUP_CLOUD.md](SETUP_CLOUD.md).**

## Architectuur

- `bot.py poll` — één ronde: commando's, pre-match, live goals, post-match.
- Data: **ESPN** (gratis, keyloos, mét doelpuntmakers) via `api_client.py`.
- State: **`state.json`** (idempotency, totaalscore, Telegram-offset, log) —
  de workflow commit dit na elke run terug, want runners zijn wegwerp.
- Geheimen: **GitHub Secrets** `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
  (nooit in de code).
- Schema: `.github/workflows/poll.yml`, cron elke 5 min (UTC) + handmatige knop.

## Lokaal testen

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
copy .env.example .env   # vul TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in
python bot.py test       # testbericht
python bot.py poll       # één ronde
python test_scoring.py   # scoring-check (geen secrets nodig)
```

## Bestanden

| Bestand | Rol |
|---|---|
| `bot.py` | entry point + commando's |
| `config.py` | leest geheimen/instellingen uit env (geen secrets in code) |
| `api_client.py` | ESPN-data (wedstrijden, scorers) |
| `scoring.py` | Scorito-puntenberekening |
| `telegram_bot.py` | berichten + getUpdates |
| `storage.py` | JSON-state (`state.json`) |
| `predictions.json` | jouw picks |
| `.github/workflows/poll.yml` | het cron-schema |

"""
Persistente runner voor Railway (en elke always-on host).

In plaats van de GitHub Actions-cron (elke 5 min een wegwerp-container) draait dit
één proces 24/7 dat elke POLL_SECONDS een poll doet. State staat op een vaste
schijf (Railway Volume), dus geen git-sync, geen botsingen, geen corruptie.

Env-variabelen (zet ze in Railway):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   - verplicht
  STATE_FILE=/data/state.json            - pad op het Volume
  POLL_SECONDS=60                        - hoe vaak pollen (optioneel)
"""
import os
import shutil
import time
from pathlib import Path

POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "60"))

# Eenmalig: als het Volume nog leeg is, neem de meegeleverde state.json over
# (zodat je huidige punten/voortgang meeverhuizen bij de eerste deploy).
_state_file = os.environ.get("STATE_FILE", "state.json")
_target = Path(_state_file)
_seed = Path(__file__).parent / "state.json"
if str(_target) != str(_seed) and not _target.exists() and _seed.exists():
    _target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(_seed, _target)
    print(f"[runner] state geseed vanuit {_seed} -> {_target}", flush=True)

# Pas NA het zetten van STATE_FILE importeren (config leest het bij import).
import bot

print(f"[runner] gestart; poll elke {POLL_SECONDS}s; state={_state_file}", flush=True)
while True:
    try:
        bot.cmd_poll()
    except Exception as e:
        print(f"[runner] poll-fout: {e}", flush=True)
    time.sleep(POLL_SECONDS)

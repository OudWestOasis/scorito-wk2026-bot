"""
State-opslag in één JSON-bestand (state.json).

Zelfde functie-API als de oude SQLite-versie, zodat bot.py onveranderd blijft.
JSON is diff-vriendelijk: de GitHub Actions-workflow commit het bestand na elke
run terug, zodat de wegwerp-runners tóch geheugen hebben (idempotency, totaal,
Telegram-offset, geschiedenis).

State-structuur:
{
  "sent_messages":    ["<match_id>:<type>", ...],     # pre / goal_<stand> / post
  "running_total":    {"<phase>": punten},
  "last_known_score": {"<match_id>": [home, away]},
  "match_goal_points":{"<match_id>": punten},
  "meta":             {"<key>": "<value>"},            # o.a. tg_offset
  "event_log":        [["<iso-ts>", "<text>"], ...]
}
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import config

_PATH = Path(config.STATE_FILE)
_EMPTY = {
    "sent_messages": [],
    "running_total": {},
    "last_known_score": {},
    "match_goal_points": {},
    "meta": {},
    "event_log": [],
}
_STATE: dict | None = None


def _load() -> dict:
    global _STATE
    if _STATE is None:
        if _PATH.exists():
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            # Ontbrekende sleutels aanvullen (voorwaartse compat).
            _STATE = {**{k: (v.copy() if isinstance(v, (list, dict)) else v)
                         for k, v in _EMPTY.items()}, **data}
        else:
            _STATE = {k: (v.copy() if isinstance(v, (list, dict)) else v)
                      for k, v in _EMPTY.items()}
    return _STATE


def _save() -> None:
    _PATH.write_text(
        json.dumps(_load(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """Zorgt dat state.json bestaat."""
    _load()
    if not _PATH.exists():
        _save()


# ---- idempotency -----------------------------------------------------------

def _key(match_id, message_type) -> str:
    return f"{match_id}:{message_type}"


def was_sent(match_id, message_type: str) -> bool:
    return _key(match_id, message_type) in _load()["sent_messages"]


def mark_sent(match_id, message_type: str) -> None:
    s = _load()["sent_messages"]
    k = _key(match_id, message_type)
    if k not in s:
        s.append(k)
        _save()


# ---- goal-detectie ---------------------------------------------------------

def get_last_score(match_id) -> tuple[int, int] | None:
    v = _load()["last_known_score"].get(str(match_id))
    return (v[0], v[1]) if v else None


def set_last_score(match_id, home: int, away: int) -> None:
    _load()["last_known_score"][str(match_id)] = [home, away]
    _save()


# ---- lopende totaalscore ---------------------------------------------------

def add_points(phase: str, points: int) -> None:
    rt = _load()["running_total"]
    rt[phase] = rt.get(phase, 0) + points
    _save()


def get_phase_total(phase: str) -> int:
    return _load()["running_total"].get(phase, 0)


def get_total() -> int:
    return sum(_load()["running_total"].values())


def phase_breakdown() -> dict[str, int]:
    return dict(sorted(_load()["running_total"].items()))


# ---- topscorer-punten per wedstrijd ----------------------------------------

def add_match_goal_points(match_id, points: int) -> None:
    mp = _load()["match_goal_points"]
    mp[str(match_id)] = mp.get(str(match_id), 0) + points
    _save()


def get_match_goal_points(match_id) -> int:
    return _load()["match_goal_points"].get(str(match_id), 0)


# ---- key-value (o.a. Telegram-offset) --------------------------------------

def get_meta(key: str, default: str | None = None) -> str | None:
    return _load()["meta"].get(key, default)


def set_meta(key: str, value: str) -> None:
    _load()["meta"][key] = str(value)
    _save()


# ---- geschiedenis (/log) ---------------------------------------------------

def log_event(text: str) -> None:
    log = _load()["event_log"]
    log.append([_now(), text])
    # Houd 'm behapbaar (laatste 200).
    if len(log) > 200:
        del log[:-200]
    _save()


def recent_events(limit: int = 15) -> list[tuple[str, str]]:
    log = _load()["event_log"]
    return [(ts, text) for ts, text in log[-limit:]]

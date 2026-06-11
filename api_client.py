"""
Wedstrijd- en doelpuntdata voor de Scorito WK 2026 bot.

BRON: ESPN's publieke (ongedocumenteerde) soccer-API. Gratis, geen key,
en — cruciaal — mét doelpuntmakers. Bewezen werkend op de WK-data:
de scorer zit in keyEvents[].participants[].athlete.displayName, met
minuut, team en lopende stand.

Endpoints (league code "fifa.world" = mannen-WK):
  scoreboard:  /scoreboard?dates=YYYYMMDD            (stand + status)
  summary:     /summary?event=<id>                   (keyEvents -> scorers)

football-data.org is NIET meer nodig (gratis tier had geen scorers en
een onzekere WK-dekking). FOOTBALL_API_KEY mag leeg blijven.

Let op (ongedocumenteerde API): het responseformaat kan zonder
aankondiging wijzigen en er is geen SLA. Het is al jaren stabiel en
breed gebruikt, maar check tijdens het toernooi of de berichten lopen.

Eén bron van waarheid voor teamnamen in TEAM_NAME_MAP: wijkt een
ESPN-naam af van predictions.json, voeg het alias daar toe.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

BASE_URL = os.environ.get(
    "ESPN_API_BASE",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world",
)
_HEADERS = {"User-Agent": "scorito-wk2026-bot/1.0"}

# Onze prediction-naam  ->  alle bekende ESPN-aliassen.
# Alleen teams waar de spelling kan afwijken hoeven hier; de rest matcht
# 1-op-1. ESPN-namen voor 2026 nog niet 100% zeker -> ruim aliassen.
TEAM_NAME_MAP = {
    "USA": ["United States", "USA"],
    "South Korea": ["South Korea", "Korea Republic"],
    "Czechia": ["Czechia", "Czech Republic"],
    "Ivory Coast": ["Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire"],
    "Cape Verde": ["Cape Verde", "Cabo Verde"],
    "DR Congo": ["DR Congo", "Congo DR", "Congo Republic", "Congo"],
    "Turkey": ["Turkey", "Türkiye", "Turkiye"],
    "Iran": ["Iran", "IR Iran"],
    "Bosnia": ["Bosnia", "Bosnia & Herzegovina", "Bosnia and Herzegovina",
               "Bosnia-Herzegovina"],
    "Curacao": ["Curacao", "Curaçao"],
}

_ALIAS_TO_PRED = {}
for _pred, _aliases in TEAM_NAME_MAP.items():
    for _a in _aliases:
        _ALIAS_TO_PRED[_a.lower()] = _pred


def normalize_team(api_name: str) -> str:
    """ESPN-teamnaam -> de naam zoals in predictions.json."""
    if not api_name:
        return api_name
    return _ALIAS_TO_PRED.get(api_name.lower(), api_name)


# ---- lage-niveau HTTP ------------------------------------------------------

def _get(path: str, params: dict | None = None) -> dict:
    r = requests.get(
        f"{BASE_URL}{path}", headers=_HEADERS, params=params or {}, timeout=20
    )
    r.raise_for_status()
    return r.json()


def _ymd(d: datetime) -> str:
    return d.strftime("%Y%m%d")


def _scoreboard(start: datetime, end: datetime) -> list[dict]:
    """Alle events tussen twee UTC-dagen (inclusief)."""
    dates = _ymd(start) if start.date() == end.date() else f"{_ymd(start)}-{_ymd(end)}"
    data = _get("/scoreboard", {"dates": dates})
    return [_parse_event(e) for e in data.get("events", [])]


# ---- parsing ---------------------------------------------------------------

def _parse_event(ev: dict) -> dict:
    comp = (ev.get("competitions") or [{}])[0]
    home = away = {}
    for c in comp.get("competitors", []):
        if c.get("homeAway") == "home":
            home = c
        elif c.get("homeAway") == "away":
            away = c
    stype = ((ev.get("status") or {}).get("type") or {})
    state = (stype.get("state") or "").lower()
    status = {"pre": "SCHEDULED", "in": "IN_PLAY", "post": "FINISHED"}.get(state, "SCHEDULED")
    return {
        "id": str(ev.get("id")),
        "home": normalize_team((home.get("team") or {}).get("displayName", "")),
        "away": normalize_team((away.get("team") or {}).get("displayName", "")),
        "utc_date": _iso(ev.get("date")),
        "status": status,
        "status_name": stype.get("name", ""),   # bv. STATUS_HALFTIME, STATUS_FIRST_HALF
        "score_home": _int(home.get("score")),
        "score_away": _int(away.get("score")),
        "minute": _minute(ev.get("status") or {}),
    }


def _iso(espn_date: str | None) -> str | None:
    # ESPN levert bv. "2026-06-15T18:00Z" -> normaliseer naar +00:00.
    if not espn_date:
        return None
    return espn_date.replace("Z", "+00:00")


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _minute(status: dict) -> int | None:
    dc = status.get("displayClock")  # bv. "67'"
    if dc:
        digits = "".join(ch for ch in dc if ch.isdigit())
        if digits:
            return int(digits)
    return None


# ---- publieke API (zelfde signatuur als voorheen) --------------------------

def get_upcoming_matches(window_minutes: int = 60) -> list[dict]:
    """Wedstrijden die binnen `window_minutes` beginnen (nog niet gestart)."""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(minutes=window_minutes)
    out = []
    for m in _scoreboard(now, horizon + timedelta(days=1)):
        if m["status"] != "SCHEDULED" or not m["utc_date"]:
            continue
        kickoff = datetime.fromisoformat(m["utc_date"])
        if now <= kickoff <= horizon:
            out.append(m)
    return out


def get_matches_in_days(days: int = 7) -> list[dict]:
    """Nog te spelen wedstrijden in de komende `days` dagen, op tijd gesorteerd."""
    now = datetime.now(timezone.utc)
    out = [m for m in _scoreboard(now, now + timedelta(days=days))
           if m["status"] == "SCHEDULED" and m["utc_date"]
           and datetime.fromisoformat(m["utc_date"]) >= now]
    return sorted(out, key=lambda m: m["utc_date"])


def get_tournament_results() -> list[dict]:
    """Alle afgeronde wedstrijden van het hele toernooi (voor de bracket-tracker)."""
    start = datetime(2026, 6, 11, tzinfo=timezone.utc)
    end = datetime(2026, 7, 20, tzinfo=timezone.utc)
    return [m for m in _scoreboard(start, end) if m["status"] == "FINISHED"]


def get_next_match() -> dict | None:
    """De eerstvolgende nog te spelen wedstrijd (widening window)."""
    for days in (2, 5, 14, 45):
        ms = get_matches_in_days(days)
        if ms:
            return ms[0]
    return None


def get_live_matches() -> list[dict]:
    """Lopende wedstrijden."""
    now = datetime.now(timezone.utc)
    return [m for m in _scoreboard(now - timedelta(days=1), now + timedelta(days=1))
            if m["status"] == "IN_PLAY"]


def get_finished_matches(since_minutes: int = 10) -> list[dict]:
    """Recent afgelopen wedstrijden. Het venster is ruim; idempotency in
    storage voorkomt dubbele post-match berichten (ESPN geeft geen
    betrouwbare 'lastUpdated', dus `since_minutes` is hier indicatief)."""
    now = datetime.now(timezone.utc)
    return [m for m in _scoreboard(now - timedelta(days=2), now + timedelta(days=1))
            if m["status"] == "FINISHED"]


def get_match_scorers(match_id: str) -> list[dict]:
    """[{"player", "team", "minute"}] in chronologische volgorde."""
    data = _get("/summary", {"event": match_id})
    scorers = []
    for e in data.get("keyEvents", []) or []:
        if not e.get("scoringPlay") or e.get("shootout"):
            continue
        parts = e.get("participants") or []
        name = (parts[0].get("athlete") or {}).get("displayName") if parts else None
        scorers.append({
            "player": name or "onbekend",
            "team": normalize_team((e.get("team") or {}).get("displayName", "")),
            "minute": (e.get("clock") or {}).get("displayValue", ""),
        })
    return scorers

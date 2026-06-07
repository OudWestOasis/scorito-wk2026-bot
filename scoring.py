"""
Scorito WK 2026 point calculator.
"""
from dataclasses import dataclass
from typing import Literal

Position = Literal["DF", "MF", "FW"]
Phase = Literal[
    "group_stage", "round_of_32", "round_of_16",
    "quarterfinal", "semifinal", "final"
]

PHASE_POINTS = {
    "group_stage":   {"exact": 45,  "toto": 30,  "df": 64,  "mf": 32,  "fw": 16},
    "round_of_32":   {"exact": 67,  "toto": 45,  "df": 96,  "mf": 48,  "fw": 24},
    "round_of_16":   {"exact": 90,  "toto": 60,  "df": 128, "mf": 64,  "fw": 32},
    "quarterfinal":  {"exact": 135, "toto": 90,  "df": 192, "mf": 96,  "fw": 48},
    "semifinal":     {"exact": 180, "toto": 120, "df": 256, "mf": 128, "fw": 64},
    "final":         {"exact": 270, "toto": 180, "df": 384, "mf": 192, "fw": 96},
}

POS_KEY = {"DF": "df", "MF": "mf", "FW": "fw"}


@dataclass
class MatchScore:
    home_team: str
    away_team: str
    actual_home: int
    actual_away: int
    pred_home: int
    pred_away: int
    phase: Phase


def score_match(m: MatchScore) -> tuple[int, str]:
    pts = PHASE_POINTS[m.phase]
    if m.actual_home == m.pred_home and m.actual_away == m.pred_away:
        return pts["exact"], "Exacte uitslag 🎯"
    pred_result = _result(m.pred_home, m.pred_away)
    actual_result = _result(m.actual_home, m.actual_away)
    if pred_result == actual_result:
        return pts["toto"], "Toto goed ✅"
    return 0, "Geen punten"


def score_goal(position: Position, phase: Phase) -> int:
    return PHASE_POINTS[phase][POS_KEY[position]]


def _result(h: int, a: int) -> str:
    if h > a: return "H"
    if h < a: return "A"
    return "D"


def detect_phase(match_date_iso: str) -> Phase:
    d = match_date_iso[:10]
    if d <= "2026-06-27": return "group_stage"
    if d <= "2026-07-03": return "round_of_32"
    if d <= "2026-07-07": return "round_of_16"
    if d <= "2026-07-11": return "quarterfinal"
    if d <= "2026-07-15": return "semifinal"
    return "final"

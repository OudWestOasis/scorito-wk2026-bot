"""Telegram message sending helpers."""
import requests

import config


def _base() -> str:
    return f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send(chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:                       # leeg/None => platte tekst (geen opmaak)
        payload["parse_mode"] = parse_mode
    r = requests.post(f"{_base()}/sendMessage", json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def get_updates(offset: int | None = None, timeout: int = 0) -> list:
    """Haal inkomende Telegram-berichten op (voor /commando's)."""
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(f"{_base()}/getUpdates", params=params, timeout=timeout + 15)
    r.raise_for_status()
    return r.json().get("result", [])


def get_chat_id_helper():
    """Run dit eenmalig nadat je /start naar de bot stuurde."""
    r = requests.get(f"{_base()}/getUpdates", timeout=15)
    for update in r.json().get("result", []):
        if "message" in update:
            print(f"chat_id = {update['message']['chat']['id']}")
            return
    print("Geen updates. Stuur eerst /start naar je bot in Telegram.")


def fmt_prematch(home, away, kickoff, pred_h, pred_a, phase_scorers):
    lines = [
        f"⚽ Over 30 minuten: *{home} – {away}*",
        f"🕘 Aftrap {kickoff}",
        "",
        f"Jouw voorspelling: *{pred_h}-{pred_a}*",
    ]
    relevant = [s for s in phase_scorers if s["team"] in (home, away)]
    if relevant:
        lines.append("\nJouw topscorers in deze wedstrijd:")
        for s in relevant:
            mult = " ← 4× multiplier!" if s["position"] == "DF" else ""
            lines.append(f"• {s['name']} ({s['position']}){mult}")
    return "\n".join(lines)


def fmt_goal(home, away, score_h, score_a, minute, scorer, is_my_pick,
             pred_h, pred_a, goal_points=0, outlook="", running_total=None, hype=""):
    opener = (f"*{hype}* {home} {score_h}-{score_a} {away} ({minute}')" if hype
              else f"⚡ GOAL! *{home} {score_h}-{score_a} {away}* ({minute}')")
    lines = [opener]
    if is_my_pick:
        lines.append(f"Scorer: *{scorer}* ⭐ jouw topscorer-pick! +{goal_points} pt")
    else:
        lines.append(f"Scorer: {scorer}")
    lines.append(f"\nJouw voorspelling: {pred_h}-{pred_a}")
    if outlook:
        lines.append(outlook)
    if running_total is not None:
        lines.append(f"Subtotaal toernooi: *{running_total}*")
    return "\n".join(lines)


def fmt_postmatch(home, away, score_h, score_a, pred_h, pred_a,
                  match_points, label, running_total, scoring_points=0):
    total_match = match_points + scoring_points
    lines = [
        f"🏁 FT — *{home} {score_h}-{score_a} {away}*",
        f"Jouw voorspelling: {pred_h}-{pred_a} → {label}",
        f"Uitslag-punten: *{match_points}*",
    ]
    if scoring_points:
        lines.append(f"Topscorer-punten: *{scoring_points}*")
        lines.append(f"Totaal deze wedstrijd: *{total_match}*")
    lines.append(f"Subtotaal toernooi: *{running_total}*")
    return "\n".join(lines)


if __name__ == "__main__":
    get_chat_id_helper()

"""
Scorito WK 2026 Telegram bot — entry point (cloud-versie, GitHub Actions).

Usage:
    python bot.py poll       # 1 ronde: commando's, pre-match, live goals, post-match
    python bot.py status     # stuurt de totaalstand naar Telegram
    python bot.py demo        # stuurt voorbeeldberichten (hoe het eruitziet)
    python bot.py test       # kort testbericht

In Telegram kun je de bot vragen stellen:
    /stand   subtotaal + punten per fase
    /week    komende wedstrijden + wat jij hebt ingevuld
    /log     wat de bot allemaal gedaan heeft
    /help    overzicht
"""
import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config

# utf-8 forceren (emoji/teamnamen) als de console dat ondersteunt.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
PREDICTIONS = json.loads((ROOT / "predictions.json").read_text(encoding="utf-8"))

TELEGRAM_TOKEN = config.TELEGRAM_BOT_TOKEN
CHAT_ID = config.TELEGRAM_CHAT_ID
# Wedstrijddata komt van ESPN (gratis, geen key nodig — zie api_client.py).

AMS = ZoneInfo("Europe/Amsterdam")
WD = ["ma", "di", "wo", "do", "vr", "za", "zo"]
PHASE_NL = {
    "group_stage": "Groepsfase", "round_of_32": "Laatste 32",
    "round_of_16": "Achtste finale", "quarterfinal": "Kwartfinale",
    "semifinal": "Halve finale", "final": "Finale",
}


# ---- helpers ---------------------------------------------------------------

def find_prediction(home: str, away: str):
    """Zoek de groepswedstrijd-voorspelling (beide volgordes)."""
    for grp in PREDICTIONS["groups"].values():
        for m in grp["matches"]:
            if (m["home"] == home and m["away"] == away) or \
               (m["home"] == away and m["away"] == home):
                return m
    # Knockout: alleen de finale heeft een scoreline.
    fin = PREDICTIONS["knockout_predictions"]["final"]
    if {fin["home"], fin["away"]} == {home, away}:
        return fin
    return None


def _oriented_prediction(pred, home, away):
    """Geef (pred_home, pred_away) in de volgorde van de echte wedstrijd."""
    if pred is None:
        return None, None
    if pred["home"] == home:
        return pred["pred_home"], pred["pred_away"]
    return pred["pred_away"], pred["pred_home"]


def _phase_scorers(phase: str):
    return PREDICTIONS["top_scorers_per_phase"].get(phase, [])


def _result(h: int, a: int) -> str:
    if h > a:
        return "H"
    if h < a:
        return "A"
    return "D"


def _outlook(sh, sa, ph, pa) -> str:
    """Korte duiding of de huidige stand goed/niet goed is t.o.v. de pick."""
    if ph is None or pa is None:
        return ""
    if (sh, sa) == (ph, pa):
        return "📈 Precies jouw voorspelling!"
    if _result(sh, sa) == _result(ph, pa):
        return "📈 Toto-richting klopt (zo blijft het goed)"
    return "📉 Nu nog niet jouw voorspelling"


def _kickoff_ams(utc_date: str) -> str:
    dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(AMS)
    return dt.strftime("%H:%M")


def _fmt_dt_ams(utc_date: str) -> str:
    dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(AMS)
    return f"{WD[dt.weekday()]} {dt.strftime('%d-%m %H:%M')}"


def _norm_name(name: str) -> str:
    # Strip accenten zodat "Mbappé" (ESPN) matcht met "Mbappe" (picks).
    nfkd = unicodedata.normalize("NFKD", name or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip().lower()


def _match_pick(scorer_name: str, team: str, phase: str):
    """Geef de topscorer-pick-dict terug als deze scorer een pick is."""
    sn = _norm_name(scorer_name)
    if not sn:
        return None
    for pick in _phase_scorers(phase):
        pn = _norm_name(pick["name"])
        last = pn.split()[-1] if pn else ""
        if pn == sn or pn in sn or (last and last in sn):
            return pick
    return None


# ---- tekstopbouw voor commando's -------------------------------------------

def build_status() -> str:
    import storage
    breakdown = storage.phase_breakdown()
    lines = ["📊 *Scorito-stand — Oud-West Oasis*", ""]
    if breakdown:
        for phase, pts in breakdown.items():
            lines.append(f"• {PHASE_NL.get(phase, phase)}: *{pts}*")
    else:
        lines.append("Nog geen punten geregistreerd.")
    lines.append("")
    lines.append(f"Subtotaal: *{storage.get_total()}*")
    return "\n".join(lines)


def build_week() -> str:
    import api_client as api
    import scoring
    try:
        matches = api.get_matches_in_days(7)
    except Exception as e:
        return f"Kon de agenda niet ophalen: {e}"
    if not matches:
        return "Geen geplande wedstrijden in de komende 7 dagen."
    lines = ["🗓️ *Komende 7 dagen — jouw invulling*", ""]
    for m in matches[:12]:
        phase = scoring.detect_phase(m["utc_date"])
        ph, pa = _oriented_prediction(find_prediction(m["home"], m["away"]),
                                      m["home"], m["away"])
        pred = f"{ph}-{pa}" if ph is not None else "—"
        lines.append(f"*{m['home']} – {m['away']}*")
        lines.append(f"  {_fmt_dt_ams(m['utc_date'])} · jouw uitslag: {pred}")
        picks = [s["name"] for s in _phase_scorers(phase)
                 if s["team"] in (m["home"], m["away"])]
        if picks:
            lines.append(f"  ⭐ jouw picks: {', '.join(picks)}")
    if len(matches) > 12:
        lines.append(f"\n…en nog {len(matches) - 12} later deze week.")
    return "\n".join(lines)


def build_next() -> str:
    import api_client as api
    import scoring
    try:
        m = api.get_next_match()
    except Exception as e:
        return f"Kon de volgende wedstrijd niet ophalen: {e}"
    if not m:
        return "Geen geplande wedstrijd gevonden."
    phase = scoring.detect_phase(m["utc_date"])
    ph, pa = _oriented_prediction(find_prediction(m["home"], m["away"]),
                                  m["home"], m["away"])
    pred = f"{ph}-{pa}" if ph is not None else "—"
    lines = [
        "⏭️ *Jouw volgende voorspelling*",
        "",
        f"*{m['home']} – {m['away']}*",
        f"🕘 {_fmt_dt_ams(m['utc_date'])}",
        f"Jouw uitslag: *{pred}*",
    ]
    picks = [f"{s['name']} ({s['position']})" for s in _phase_scorers(phase)
             if s["team"] in (m["home"], m["away"])]
    if picks:
        lines.append("⭐ jouw picks: " + ", ".join(picks))
    return "\n".join(lines)


def build_fastlane() -> str:
    """Compleet overzicht: punten nu, verleden, volgende + komende wedstrijden."""
    import api_client as api
    import scoring
    import storage

    lines = ["📊 *Jouw Scorito-overzicht*", "", f"Punten nu: *{storage.get_total()}*"]

    # Verleden uit de geschiedenis (afgeronde wedstrijden).
    ft = [t for _, t in storage.recent_events(200) if t.startswith("FT:")]
    if ft:
        exact = sum(1 for t in ft if "Exacte" in t)
        toto = sum(1 for t in ft if "Toto goed" in t)
        lines.append(f"Gespeeld: {len(ft)} · exact {exact} · toto {toto}")

    # Eerstvolgende wedstrijd + jouw voorspelling.
    try:
        nxt = api.get_next_match()
    except Exception:
        nxt = None
    lines.append("")
    if nxt:
        phase = scoring.detect_phase(nxt["utc_date"])
        ph, pa = _oriented_prediction(find_prediction(nxt["home"], nxt["away"]),
                                      nxt["home"], nxt["away"])
        pred = f"{ph}-{pa}" if ph is not None else "—"
        lines.append(f"⏭️ *Volgende:* {nxt['home']} – {nxt['away']}")
        lines.append(f"🕘 {_fmt_dt_ams(nxt['utc_date'])} · jouw uitslag: *{pred}*")
        picks = [s["name"] for s in _phase_scorers(phase)
                 if s["team"] in (nxt["home"], nxt["away"])]
        if picks:
            lines.append(f"⭐ picks: {', '.join(picks)}")
    else:
        lines.append("Geen geplande wedstrijd gevonden.")

    # Daarna komende wedstrijden.
    try:
        upcoming = api.get_matches_in_days(7)
    except Exception:
        upcoming = []
    rest = upcoming[1:5] if nxt else upcoming[:4]
    if rest:
        lines.append("")
        lines.append("🗓️ *Daarna:*")
        for m in rest:
            ph, pa = _oriented_prediction(find_prediction(m["home"], m["away"]),
                                          m["home"], m["away"])
            pred = f"{ph}-{pa}" if ph is not None else "—"
            lines.append(f"• {_fmt_dt_ams(m['utc_date'])} {m['home']}–{m['away']} ({pred})")
    return "\n".join(lines)


def build_log() -> str:
    import storage
    events = storage.recent_events(15)
    if not events:
        return "Nog niks gelogd. Zodra er wedstrijden zijn, verschijnt het hier."
    lines = ["📜 *Wat de bot deed (laatste 15)*", ""]
    for ts, text in events:
        try:
            local = datetime.fromisoformat(ts).astimezone(AMS).strftime("%d-%m %H:%M")
        except ValueError:
            local = ts[:16]
        lines.append(f"• {local} — {text}")
    return "\n".join(lines)


def build_help() -> str:
    return "\n".join([
        "🤖 *Scorito-bot — commando's*",
        "",
        "fastlane — overzicht: punten + volgende & komende wedstrijden",
        "/stand — subtotaal + punten per fase",
        "/week — komende wedstrijden + wat jij hebt ingevuld",
        "/log — wat de bot allemaal gedaan heeft",
        "/help — dit overzicht",
        "",
        "Voor elke wedstrijd krijg je vanzelf een pre-match, live updates "
        "bij elk doelpunt, en de eindstand met je punten.",
    ])


_UNKNOWN = "Onbekend commando. Stuur /help voor de opties."


def _dispatch(cmd: str) -> str:
    if cmd in ("help", "start"):
        return build_help()
    if cmd in ("fastlane", "overzicht", "dashboard"):
        return build_fastlane()
    if cmd in ("volgende", "next", "voorspelling"):
        return build_next()
    if cmd in ("stand", "totaal", "score", "punten"):
        return build_status()
    if cmd in ("week", "komend", "komende", "agenda"):
        return build_week()
    if cmd in ("log", "geschiedenis", "historie"):
        return build_log()
    return _UNKNOWN


def process_commands():
    """Beantwoord inkomende /commando's (offset bijgehouden in state.json)."""
    import storage
    from telegram_bot import get_updates, send

    import time
    offset = storage.get_meta("tg_offset")
    try:
        updates = get_updates(int(offset) + 1 if offset else None)
    except Exception as e:
        print(f"[cmd] getUpdates error: {e}")
        return
    if not updates:
        return
    max_id = max(u["update_id"] for u in updates)
    cutoff = time.time() - 3600  # alleen écht oude backlog (>1 uur) negeren

    for u in updates:
        msg = u.get("message") or {}
        if str((msg.get("chat") or {}).get("id")) != str(CHAT_ID):
            continue
        if (msg.get("date") or 0) < cutoff:
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        # Werkt met én zonder schuine streep (bv. "fastlane" of "/stand").
        is_slash = text.startswith("/")
        cmd = text.split()[0].lstrip("/").split("@")[0].lower()
        reply = _dispatch(cmd)
        # Bij gewone tekst (geen /) alleen reageren als we het herkennen,
        # zodat losse chatberichten geen "onbekend"-antwoord uitlokken.
        if not is_slash and reply == _UNKNOWN:
            continue
        send(CHAT_ID, reply)
        storage.log_event(f"vraag beantwoord: {cmd}")
        print(f"[cmd] {cmd}")
    storage.set_meta("tg_offset", str(max_id))


# ---- commands --------------------------------------------------------------

def cmd_poll():
    """Eén ronde: commando's, pre-match (~vooraf), live goals, post-match."""
    import api_client as api
    import scoring
    import storage
    from telegram_bot import fmt_goal, fmt_postmatch, fmt_prematch, send

    storage.init_db()

    # Coördinatie laptop <-> cloud. Draait de laptop (die zet RUN_LOCATION=laptop
    # en ververst elke minuut een 'heartbeat'), dan gaat de cloud stand-by zodat
    # er geen dubbele berichten komen. State wordt via git gedeeld.
    import os as _os
    import time as _time
    if _os.environ.get("RUN_LOCATION") != "laptop":
        hb = _os.environ.get("LAPTOP_HEARTBEAT", "").strip()
        try:
            if hb and _time.time() - float(hb) < 180:
                print("[poll] laptop is actief — cloud staat stand-by")
                return
        except ValueError:
            pass

    # 0) Inkomende vragen beantwoorden.
    process_commands()

    # 1) PRE-MATCH — wedstrijden die binnenkort beginnen.
    try:
        for m in api.get_upcoming_matches(window_minutes=config.PREMATCH_WINDOW_MINUTES):
            if storage.was_sent(m["id"], "pre"):
                continue
            phase = scoring.detect_phase(m["utc_date"])
            pred = find_prediction(m["home"], m["away"])
            ph, pa = _oriented_prediction(pred, m["home"], m["away"])
            text = fmt_prematch(
                m["home"], m["away"], _kickoff_ams(m["utc_date"]),
                ph if ph is not None else "?", pa if pa is not None else "?",
                _phase_scorers(phase),
            )
            send(CHAT_ID, text)
            storage.mark_sent(m["id"], "pre")
            storage.log_event(f"pre-match: {m['home']}–{m['away']} (jouw {ph}-{pa})")
            print(f"[pre] {m['home']}-{m['away']}")
    except Exception as e:  # de run mag niet omvallen op één fase
        print(f"[pre] error: {e}")

    # 2) LIVE — bij elk nieuw doelpunt.
    try:
        for m in api.get_live_matches():
            sh = m["score_home"] or 0
            sa = m["score_away"] or 0
            last = storage.get_last_score(m["id"])
            if last is None:
                storage.set_last_score(m["id"], sh, sa)
                continue
            if (sh, sa) == last:
                continue

            phase = scoring.detect_phase(m["utc_date"])
            pred = find_prediction(m["home"], m["away"])
            ph, pa = _oriented_prediction(pred, m["home"], m["away"])

            scorer_name, pick = "onbekend", None
            try:
                scorers = api.get_match_scorers(m["id"])
                if scorers:
                    scorer_name = scorers[-1]["player"]
                    pick = _match_pick(scorer_name, scorers[-1]["team"], phase)
            except Exception as e:
                print(f"[live] scorers error: {e}")

            mtype = f"goal_{sh}-{sa}"
            if not storage.was_sent(m["id"], mtype):
                goal_pts = scoring.score_goal(pick["position"], phase) if pick else 0
                if pick:
                    storage.add_points(phase, goal_pts)
                    storage.add_match_goal_points(m["id"], goal_pts)
                text = fmt_goal(
                    m["home"], m["away"], sh, sa, m["minute"] or "?",
                    scorer_name, pick is not None,
                    ph if ph is not None else "?", pa if pa is not None else "?",
                    goal_pts, _outlook(sh, sa, ph, pa), storage.get_total(),
                )
                send(CHAT_ID, text)
                storage.mark_sent(m["id"], mtype)
                tag = f" ⭐{scorer_name} +{goal_pts}" if pick else ""
                storage.log_event(f"goal: {m['home']} {sh}-{sa} {m['away']}{tag}")
                print(f"[goal] {m['home']} {sh}-{sa} {m['away']}{tag}")
            storage.set_last_score(m["id"], sh, sa)
    except Exception as e:
        print(f"[live] error: {e}")

    # 3) POST-MATCH — eindstand + punten.
    try:
        for m in api.get_finished_matches(since_minutes=config.FINISHED_WINDOW_MINUTES):
            if storage.was_sent(m["id"], "post"):
                continue
            sh = m["score_home"] or 0
            sa = m["score_away"] or 0
            phase = scoring.detect_phase(m["utc_date"])
            pred = find_prediction(m["home"], m["away"])
            ph, pa = _oriented_prediction(pred, m["home"], m["away"])

            if ph is None:
                match_pts, label = 0, "geen scoreline-voorspelling"
            else:
                ms = scoring.MatchScore(
                    home_team=m["home"], away_team=m["away"],
                    actual_home=sh, actual_away=sa,
                    pred_home=ph, pred_away=pa, phase=phase,
                )
                match_pts, label = scoring.score_match(ms)
                storage.add_points(phase, match_pts)

            scoring_pts = storage.get_match_goal_points(m["id"])
            text = fmt_postmatch(
                m["home"], m["away"], sh, sa,
                ph if ph is not None else "?", pa if pa is not None else "?",
                match_pts, label, storage.get_total(), scoring_pts,
            )
            send(CHAT_ID, text)
            storage.mark_sent(m["id"], "post")
            storage.set_last_score(m["id"], sh, sa)
            storage.log_event(
                f"FT: {m['home']} {sh}-{sa} {m['away']} → {label} "
                f"(+{match_pts + scoring_pts})"
            )
            print(f"[post] {m['home']} {sh}-{sa} {m['away']} (+{match_pts + scoring_pts})")
    except Exception as e:
        print(f"[post] error: {e}")


def cmd_status():
    import storage
    from telegram_bot import send
    storage.init_db()
    send(CHAT_ID, build_status())


def cmd_demo():
    """Voorbeeldberichten — raakt de echte stand niet aan."""
    import storage
    from telegram_bot import fmt_goal, fmt_postmatch, fmt_prematch, send

    storage.init_db()
    send(CHAT_ID, "🧪 *Demo* — zo zien de berichten er live uit:")
    scorers = _phase_scorers("group_stage")
    send(CHAT_ID, fmt_prematch("Spain", "Cape Verde", "16:00", 3, 0, scorers))
    send(CHAT_ID, fmt_goal(
        "Spain", "Cape Verde", 1, 0, 23, "Lamine Yamal", True,
        3, 0, goal_points=16, outlook=_outlook(1, 0, 3, 0), running_total=16,
    ))
    send(CHAT_ID, fmt_goal(
        "Spain", "Cape Verde", 1, 1, 41, "Ryan Mendes", False,
        3, 0, outlook=_outlook(1, 1, 3, 0), running_total=16,
    ))
    send(CHAT_ID, fmt_postmatch(
        "Spain", "Cape Verde", 3, 0, 3, 0,
        match_points=45, label="Exacte uitslag 🎯",
        running_total=61, scoring_points=16,
    ))
    print("[demo] verstuurd")


def cmd_test():
    from telegram_bot import send
    send(CHAT_ID, "🤖 Bot is live (cloud). Klaar voor het WK.")


# ---- dagelijks e-mail-overzicht --------------------------------------------

def build_daily_email() -> tuple[str, str, str]:
    """Geeft (onderwerp, html, platte_tekst) voor het 08:00-ochtendbericht."""
    import api_client as api
    import scoring
    import storage

    now = datetime.now(AMS)
    datum = f"{WD[now.weekday()]} {now.strftime('%d-%m-%Y')}"
    total = storage.get_total()

    # Verleden (afgeronde wedstrijden) uit de geschiedenis.
    ft = [t for _, t in storage.recent_events(200) if t.startswith("FT:")]
    exact = sum(1 for t in ft if "Exacte" in t)
    toto = sum(1 for t in ft if "Toto goed" in t)

    # Wedstrijden: vandaag (Amsterdamse datum) en de rest van de week.
    try:
        week = api.get_matches_in_days(8)
    except Exception:
        week = []

    def _ams(m):
        return datetime.fromisoformat(m["utc_date"]).astimezone(AMS)

    today, later = [], []
    for m in week:
        (today if _ams(m).date() == now.date() else later).append(m)

    def _row(m):
        phase = scoring.detect_phase(m["utc_date"])
        ph, pa = _oriented_prediction(find_prediction(m["home"], m["away"]),
                                      m["home"], m["away"])
        pred = f"{ph}-{pa}" if ph is not None else "—"
        picks = [s["name"] for s in _phase_scorers(phase)
                 if s["team"] in (m["home"], m["away"])]
        return _ams(m).strftime("%H:%M"), f"{m['home']} – {m['away']}", pred, picks

    # ---- platte tekst ----
    tl = [f"Scorito WK — dagoverzicht ({datum})", "",
          f"Jouw punten: {total}"]
    if ft:
        tl.append(f"Tot nu toe: {len(ft)} gespeeld · {exact} exact · {toto} toto goed")
    tl += ["", "VANDAAG:"]
    if today:
        for t, m, pred, picks in map(_row, today):
            tl.append(f"  {t}  {m}  (jouw {pred})" + (f"  ⭐ {', '.join(picks)}" if picks else ""))
    else:
        tl.append("  Geen wedstrijden vandaag.")
    if later:
        tl += ["", "DAARNA:"]
        for m in later[:6]:
            t, name, pred, _ = _row(m)
            tl.append(f"  {_ams(m).strftime('%d-%m %H:%M')}  {name}  (jouw {pred})")
    text = "\n".join(tl)

    # ---- HTML ----
    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    def html_rows(matches, with_date):
        out = []
        for m in matches:
            t, name, pred, picks = _row(m)
            when = _ams(m).strftime("%d-%m %H:%M") if with_date else t
            pickline = (f"<div style='color:#0a7d33;font-size:12px;margin-top:2px'>"
                        f"⭐ {esc(', '.join(picks))}</div>") if picks else ""
            out.append(
                f"<tr><td style='padding:8px 0;border-bottom:1px solid #eee'>"
                f"<span style='color:#888;font-size:12px'>{when}</span><br>"
                f"<b>{esc(name)}</b>"
                f"<span style='color:#444'> — jouw uitslag {esc(pred)}</span>"
                f"{pickline}</td></tr>")
        return "".join(out)

    stats = (f"<div style='color:#666;font-size:13px;margin-top:4px'>"
             f"Tot nu toe: {len(ft)} gespeeld · {exact} exact · {toto} toto goed</div>"
             if ft else "")
    today_html = (f"<table style='width:100%;border-collapse:collapse'>{html_rows(today, False)}</table>"
                  if today else "<div style='color:#666'>Geen wedstrijden vandaag.</div>")
    later_html = (f"<h3 style='margin:18px 0 6px;font-size:15px'>Daarna</h3>"
                  f"<table style='width:100%;border-collapse:collapse'>{html_rows(later[:6], True)}</table>"
                  if later else "")

    html = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
  <h2 style="margin:0 0 2px">⚽ Scorito WK — dagoverzicht</h2>
  <div style="color:#888;font-size:13px;margin-bottom:16px">{datum} · Oud-West Oasis</div>
  <div style="background:#f4f6f8;border-radius:10px;padding:14px 18px;margin-bottom:18px">
    <div style="font-size:13px;color:#666">Jouw punten</div>
    <div style="font-size:30px;font-weight:700;line-height:1.1">{total}</div>
    {stats}
  </div>
  <h3 style="margin:0 0 6px;font-size:15px">Vandaag</h3>
  {today_html}
  {later_html}
  <div style="color:#aaa;font-size:11px;margin-top:22px">
    Automatisch verstuurd om 08:00 · Scorito WK 2026 bot
  </div>
</div>"""

    subject = f"⚽ Scorito WK — dagoverzicht {datum}"
    return subject, html, text


def cmd_email(force: bool = False):
    """Verstuur het dagoverzicht. Standaard alleen rond 08:00 NL en max 1×/dag.
    `force` (of `python bot.py emailtest`) negeert die checks — voor testen."""
    import storage
    from mailer import send_email

    storage.init_db()
    now = datetime.now(AMS)
    if not force:
        if now.hour != 8:
            print(f"[email] niet 08:00 NL (nu {now.hour}h) — overslaan")
            return
        today = now.strftime("%Y-%m-%d")
        if storage.get_meta("last_email_date") == today:
            print("[email] vandaag al gemaild — overslaan")
            return
    subject, html, text = build_daily_email()
    send_email(subject, html, text)
    storage.set_meta("last_email_date", now.strftime("%Y-%m-%d"))
    storage.log_event(f"dag-mail verstuurd naar {__import__('config').EMAIL_TO}")
    print(f"[email] verstuurd naar {__import__('config').EMAIL_TO}")


def cmd_emailtest():
    cmd_email(force=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "poll"
    {
        "poll": cmd_poll, "status": cmd_status,
        "demo": cmd_demo, "test": cmd_test,
        "email": cmd_email, "emailtest": cmd_emailtest,
    }[cmd]()

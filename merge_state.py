"""
Veilige state-merge bij een git push-botsing.

Wordt aangeroepen als de push wordt afgewezen (laptop en cloud botsten). In
plaats van de lokale state weg te gooien ('origin wint' -> dubbele berichten,
tg_offset-rollback), voegen we de append-only velden samen:
  - sent_messages : union (geen dubbele berichten)
  - event_log     : concat + dedup, op tijd gesorteerd
  - meta.tg_offset: max (commando's niet opnieuw beantwoorden)
  - matches       : per wedstrijd; behoud uitslag + scorers, goal_pts = max
  - scorer_goals  : per speler max

running_total is afgeleid en wordt bij de volgende poll toch herberekend, dus
die laten we ongemoeid.
"""
import json
import subprocess

PATH = "state.json"


def _origin_state():
    r = subprocess.run(["git", "show", "origin/main:" + PATH],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout)


def _as_int(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0


def merge(origin: dict, local: dict) -> dict:
    m = dict(origin)

    m["sent_messages"] = sorted(set(origin.get("sent_messages", []))
                                | set(local.get("sent_messages", [])))

    seen, log = set(), []
    for entry in origin.get("event_log", []) + local.get("event_log", []):
        key = tuple(entry)
        if key not in seen:
            seen.add(key)
            log.append(list(entry))
    log.sort(key=lambda e: e[0])
    m["event_log"] = log[-200:]

    meta = dict(origin.get("meta", {}))
    meta.update(local.get("meta", {}))
    off = max(_as_int(origin.get("meta", {}).get("tg_offset")),
              _as_int(local.get("meta", {}).get("tg_offset")))
    if off:
        meta["tg_offset"] = str(off)
    o_md = origin.get("meta", {}).get("last_morning_date", "")
    l_md = local.get("meta", {}).get("last_morning_date", "")
    if o_md or l_md:
        meta["last_morning_date"] = max(o_md, l_md)
    m["meta"] = meta

    lks = dict(origin.get("last_known_score", {}))
    lks.update(local.get("last_known_score", {}))
    m["last_known_score"] = lks

    matches = {}
    o_m, l_m = origin.get("matches", {}), local.get("matches", {})
    for mid in set(o_m) | set(l_m):
        o, l = o_m.get(mid, {}), l_m.get(mid, {})
        e = dict(o)
        e.update(l)
        if o.get("ah") is not None and l.get("ah") is None:
            e["ah"], e["aw"] = o["ah"], o["aw"]
        if o.get("scorers") is not None and l.get("scorers") is None:
            e["scorers"] = o["scorers"]
        e["goal_pts"] = max(o.get("goal_pts", 0), l.get("goal_pts", 0))
        matches[mid] = e
    m["matches"] = matches

    sg = {}
    for name in set(origin.get("scorer_goals", {})) | set(local.get("scorer_goals", {})):
        sg[name] = max(origin.get("scorer_goals", {}).get(name, 0),
                       local.get("scorer_goals", {}).get(name, 0))
    m["scorer_goals"] = sg

    return m


def main():
    origin = _origin_state()
    if origin is None:
        return
    with open(PATH, encoding="utf-8") as f:
        local = json.load(f)
    merged = merge(origin, local)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2, sort_keys=True)
    print("state gemerged")


if __name__ == "__main__":
    main()

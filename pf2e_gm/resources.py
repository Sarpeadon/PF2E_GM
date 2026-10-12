"""Per-character resources: Focus Points, Hero Points, spell slots, prepared and innate spells, infused
reagents, consumable counts, and your own counters.

Maximums come from the Pathbuilder import (and are recomputed on every refresh). What you've spent is stored
in the character's table state (pc["state"]["res"]["used"], keyed by resource) so a refresh never resets it.

Rules used (Player Core / GM Core):
  * Focus Points refill fully at daily preparations; Refocus restores 1. The pool is capped at 3.
  * Spell slots, prepared spells, innate spell uses, infused reagents, and per-day abilities refresh at
    daily preparations.
  * Infused reagents (alchemist): level + Intelligence modifier batches per day.
  * Hero Points: 3 maximum, start each session with 1 (the GM can change this).
"""

HERO_MAX = 3
GROUPS = ["Points", "Spell slots", "Prepared spells", "Innate spells", "Class", "Custom", "Items"]


def state(pc):
    return pc.setdefault("state", {})


def _res(pc):
    r = state(pc).setdefault("res", {})
    r.setdefault("used", {})
    r.setdefault("max", {})
    r.setdefault("custom", [])
    return r


def _is_alchemist(pc):
    names = {str(x).lower() for x in pc.get("specials", [])} | {f["name"].lower() for f in pc.get("feats", [])}
    return str(pc.get("class", "")).lower() == "alchemist" or "advanced alchemy" in names


def build(pc):
    """Resource rows for a character: [{key, group, label, max, used, cur, refresh, note}]."""
    r = _res(pc)
    used, over = r["used"], r["max"]
    rows = []

    def add(key, group, label, mx, refresh="daily", note="", default_used=None):
        mx = int(over.get(key, mx))
        u = used.get(key, default_used if default_used is not None else 0)
        u = max(0, min(int(u), mx))
        rows.append({"key": key, "group": group, "label": label, "max": mx, "used": u, "cur": mx - u,
                     "refresh": refresh, "note": note})

    fp = int(pc.get("focus_points") or 0)
    if fp:
        add("focus", "Points", "Focus Points", min(3, fp), "focus", "Refills at daily preparations; Refocus +1")
    add("hero", "Points", "Hero Points", HERO_MAX, "session", "Starts each session at 1 (set by the GM)",
        default_used=HERO_MAX - 1)

    for sc in pc.get("slots", []):
        entry = sc.get("entry", "Spells")
        if sc.get("innate"):
            for rank, names in sorted((sc.get("known") or {}).items()):
                n = (sc.get("per_day") or {}).get(rank, 0)
                for nm in names:
                    add(f"innate:{entry}:{rank}:{nm}", "Innate spells", f"{nm} (rank {rank})", n or 1,
                        note="per day")
            continue
        prepared = sc.get("prepared") or {}
        if prepared:
            for rank, names in sorted(prepared.items()):
                for i, nm in enumerate(names):
                    add(f"prep:{entry}:{rank}:{i}:{nm}", "Prepared spells", f"{nm} (rank {rank})", 1,
                        note=f"{entry}, slot {i + 1}")
        else:
            for rank, n in sorted((sc.get("per_day") or {}).items()):
                add(f"slot:{entry}:{rank}", "Spell slots", f"Rank {rank} slots", n, note=entry)

    if _is_alchemist(pc):
        int_mod = (pc.get("mods") or {}).get("int", 0)
        add("reagents", "Class", "Infused Reagents (batches)", max(0, int(pc.get("level") or 1) + int_mod),
            note="level + Int modifier; Set Max if yours differs")

    for c in r["custom"]:
        add(f"custom:{c['name']}", "Custom", c["name"], int(c.get("max") or 1), c.get("refresh", "daily"),
            c.get("note", ""))

    for e in pc.get("equipment", []):
        if e.get("invested"):
            continue
        add(f"item:{e['name']}", "Items", e["name"], int(e.get("qty") or 1), "manual",
            e.get("container") or "carried")
    return rows


def find(pc, key):
    return next((x for x in build(pc) if x["key"] == key), None)


def spend(pc, key, n=1):
    """Use n of a resource. Returns (ok, message)."""
    row = find(pc, key)
    if not row:
        return False, "No such resource."
    if row["cur"] < n:
        return False, f"{row['label']}: none left."
    _res(pc)["used"][key] = row["used"] + n
    return True, f"{row['label']}: {row['cur'] - n}/{row['max']} left"


def restore(pc, key, n=1):
    row = find(pc, key)
    if not row:
        return False, "No such resource."
    _res(pc)["used"][key] = max(0, row["used"] - n)
    return True, f"{row['label']}: {min(row['max'], row['cur'] + n)}/{row['max']}"


def set_max(pc, key, n):
    row = find(pc, key)
    if row:
        _res(pc)["max"][key] = max(0, int(n))
        _res(pc)["used"][key] = min(_res(pc)["used"].get(key, 0), max(0, int(n)))


def daily_rest(pc):
    """Daily preparations: slots, prepared and innate spells, reagents, Focus Points, and 'daily' counters refill.
    Items and Hero Points don't change. Returns the number of resources refilled."""
    n = 0
    for row in build(pc):
        if row["refresh"] in ("daily", "focus") and row["used"]:
            _res(pc)["used"][row["key"]] = 0
            n += 1
    return n


def refocus(pc):
    row = find(pc, "focus")
    if not row or not row["used"]:
        return False, "Nothing to regain (no Focus Points spent)." if row else "No focus pool."
    _res(pc)["used"]["focus"] = row["used"] - 1
    return True, f"Focus Points: {row['cur'] + 1}/{row['max']}"


def new_session(pc):
    """Hero Points reset to 1 at the start of a session."""
    _res(pc)["used"]["hero"] = HERO_MAX - 1


def add_custom(pc, name, mx, refresh="daily", note=""):
    name = name.strip()
    if not name:
        return False
    r = _res(pc)
    r["custom"] = [c for c in r["custom"] if c["name"].lower() != name.lower()]
    r["custom"].append({"name": name, "max": max(1, int(mx)), "refresh": refresh, "note": note})
    return True


def remove_custom(pc, key):
    r = _res(pc)
    name = key.split(":", 1)[1] if key.startswith("custom:") else ""
    r["custom"] = [c for c in r["custom"] if c["name"] != name]
    r["used"].pop(key, None)
    r["max"].pop(key, None)


def summary(pc):
    """Short text for status lines: 'Focus 1/2, Hero 1/3, Reagents 4/12'."""
    short = {"focus": "Focus", "hero": "Hero", "reagents": "Reagents"}
    return ", ".join(f"{short[x['key']]} {x['cur']}/{x['max']}" for x in build(pc) if x["key"] in short)

"""Faction reputation, following the Reputation subsystem (Gamemastery Guide; GM Core). Standard library only.

Reputation Points run from -50 to 50. The party earns points with favors (minor +1, moderate +2, major +5) and loses
them with disservices (minor -1, moderate -2, major -5 or more). A group's reputation is one of seven tiers, and each
tier limits which favors and disservices still move the score:

    Revered   30 to 50    raised by: major favor             lowered by: moderate or major disservice
    Admired   15 to 29    raised by: major favor             lowered by: any disservice
    Liked      5 to 14    raised by: moderate or major       lowered by: any disservice
    Ignored   -4 to 4     raised by: any favor               lowered by: any disservice
    Disliked  -5 to -14   raised by: any favor               lowered by: moderate or major disservice
    Hated    -15 to -29   raised by: any favor               lowered by: major disservice
    Hunted   -30 to -50   raised by: moderate or major       lowered by: major disservice

PCs usually start at Ignored with most groups. Reputation belongs to the whole group; an individual member can feel
differently. A rep dict is {"points": int, "log": [...], "notes": {tier: text}} and lives on the faction's notebook page.
"""
import datetime
import random

MIN_POINTS, MAX_POINTS = -50, 50
SIZES = {"minor": 1, "moderate": 2, "major": 5}
ALL = ("minor", "moderate", "major")

# name, low, high, favors that still raise it, disservices that still lower it
TIERS = [
    ("Revered", 30, 50, {"major"}, {"moderate", "major"}),
    ("Admired", 15, 29, {"major"}, set(ALL)),
    ("Liked", 5, 14, {"moderate", "major"}, set(ALL)),
    ("Ignored", -4, 4, set(ALL), set(ALL)),
    ("Disliked", -14, -5, set(ALL), {"moderate", "major"}),
    ("Hated", -29, -15, set(ALL), {"major"}),
    ("Hunted", -50, -30, {"moderate", "major"}, {"major"}),
]
DESCRIPTION = {
    "Revered": "The group reveres the party as heroes. Every member has heard of them, is helpful toward them, and "
               "would take major risks to help.",
    "Admired": "Most of the group knows the party and thinks very well of them. Many members are helpful; the rest "
               "are friendly.",
    "Liked": "The party has the group's favor. Many members know of them, and those who do are usually friendly.",
    "Ignored": "The party is not on the group's radar, or the group is ambivalent about them. No benefits or "
               "drawbacks.",
    "Disliked": "The party has a poor reputation. Many members know of them and are usually unfriendly.",
    "Hated": "The group's ire is on the party. The vast majority know of them and think very poorly of them. Many "
             "members are hostile, the rest unfriendly, and they will jump at an easy chance to hurt the party.",
    "Hunted": "The group actively hunts the party as scapegoats or nemeses, even at significant cost to itself. "
              "Every member has heard of them, is hostile, and would take major risks to thwart or destroy them.",
}
# Why a member of the group feels the way they do about the party.
REASON = {
    "Revered": "to them the party are heroes",
    "Admired": "they think very highly of the party",
    "Liked": "they have heard good things about the party",
    "Ignored": "they know little or nothing about the party",
    "Disliked": "they have heard bad things about the party",
    "Hated": "they resent the party deeply",
    "Hunted": "they see the party as enemies to be stopped",
}
# NPC starting attitudes this tier tends toward, with relative weights (PF2e attitudes).
ATTITUDES = {
    "Revered": {"Helpful": 10},
    "Admired": {"Helpful": 6, "Friendly": 4},
    "Liked": {"Friendly": 7, "Indifferent": 2, "Helpful": 1},
    "Ignored": {"Indifferent": 8, "Friendly": 1, "Unfriendly": 1},
    "Disliked": {"Unfriendly": 7, "Indifferent": 2, "Hostile": 1},
    "Hated": {"Hostile": 5, "Unfriendly": 5},
    "Hunted": {"Hostile": 10},
}


def clamp(points):
    return max(MIN_POINTS, min(MAX_POINTS, int(points)))


def tier(points):
    """Tier name for a score."""
    p = clamp(points)
    for name, lo, hi, _, _ in TIERS:
        if lo <= p <= hi:
            return name
    return "Ignored"


def tier_row(name):
    return next(t for t in TIERS if t[0] == name)


def tier_range(name):
    _, lo, hi, _, _ = tier_row(name)
    return lo, hi


def can_raise(points, size):
    return size in tier_row(tier(points))[3]


def can_lower(points, size):
    return size in tier_row(tier(points))[4]


def rule_text(name):
    """The tier's raise/lower rule in words."""
    _, lo, hi, up, down = tier_row(name)

    def words(s):
        if s == set(ALL):
            return "any"
        if s == {"moderate", "major"}:
            return "moderate or major"
        return "major" if s == {"major"} else ", ".join(sorted(s))
    return f"Raised by {words(up)} favors. Lowered by {words(down)} disservices."


def new_rep(points=0):
    return {"points": clamp(points), "log": [], "notes": {}}


def ensure(rep):
    """Fill in any missing parts of a rep dict (older pages may have none)."""
    rep = rep if isinstance(rep, dict) else {}
    rep.setdefault("points", 0)
    rep.setdefault("log", [])
    rep.setdefault("notes", {})
    return rep


class Change:
    """The outcome of applying a favor or disservice."""

    def __init__(self, before, after, applied, blocked, message, tier_before, tier_after):
        self.before, self.after, self.applied, self.blocked = before, after, applied, blocked
        self.message, self.tier_before, self.tier_after = message, tier_before, tier_after

    @property
    def tier_changed(self):
        return self.tier_before != self.tier_after

    def __repr__(self):
        return f"Change({self.before}->{self.after}, {self.message})"


def preview(points, kind, size, amount=None, egregious=False):
    """What a favor or disservice would do, without changing anything.

    kind: 'favor' or 'disservice'. size: 'minor', 'moderate', or 'major'. amount overrides the standard points
    (a major disservice takes away at least 5, more if egregious). egregious (major disservice only): lose all
    points, then 5 more. If the current score is negative already, that means 5 more below it.
    """
    if kind not in ("favor", "disservice") or size not in SIZES:
        raise ValueError("kind must be favor or disservice; size must be minor, moderate, or major")
    before = clamp(points)
    t0 = tier(before)
    if egregious:
        if kind != "disservice" or size != "major":
            raise ValueError("Only a major disservice can be egregious.")
        base = min(0, before)
        after = clamp(base - 5)
        msg = ("An egregious major disservice: all Reputation Points are lost, then 5 more"
               if before > 0 else "An egregious major disservice: 5 more points lost")
        return Change(before, after, after - before, False, msg, t0, tier(after))
    if kind == "favor":
        if not can_raise(before, size):
            return Change(before, before, 0, True,
                          f"At {t0}, only {_gate(tier_row(t0)[3])} favors add Reputation Points; this {size} favor "
                          "changes nothing.", t0, t0)
        pts = SIZES[size] if amount is None else max(1, int(amount))
        after = clamp(before + pts)
    else:
        if not can_lower(before, size):
            return Change(before, before, 0, True,
                          f"At {t0}, only {_gate(tier_row(t0)[4])} disservices lower Reputation Points; this {size} "
                          "disservice changes nothing.", t0, t0)
        pts = SIZES[size] if amount is None else int(amount)
        if size == "major":
            pts = max(5, pts)
        after = clamp(before - abs(pts))
    applied = after - before
    verb = "gained" if kind == "favor" else "lost"
    msg = f"{size.capitalize()} {kind}: {verb} {abs(applied)} Reputation Point{'s' if abs(applied) != 1 else ''}"
    if applied == 0:
        msg += " (already at the limit)"
    return Change(before, after, applied, False, msg, t0, tier(after))


def _gate(sizes):
    if set(sizes) == {"major"}:
        return "major"
    if set(sizes) == {"moderate", "major"}:
        return "moderate and major"
    return "any"


def apply(rep, kind, size, note="", amount=None, egregious=False, when=None, source=""):
    """Change a rep dict (and log it). Returns the Change. Blocked changes are logged but move nothing."""
    rep = ensure(rep)
    ch = preview(rep["points"], kind, size, amount, egregious)
    rep["points"] = ch.after
    rep["log"].append({"date": when or datetime.date.today().isoformat(), "kind": kind, "size": size,
                       "delta": ch.applied, "after": ch.after, "tier": ch.tier_after, "blocked": ch.blocked,
                       "note": note, "source": source})
    return ch


def set_points(rep, points, note="Set by hand", when=None):
    rep = ensure(rep)
    before = rep["points"]
    rep["points"] = clamp(points)
    rep["log"].append({"date": when or datetime.date.today().isoformat(), "kind": "set", "size": "",
                       "delta": rep["points"] - before, "after": rep["points"], "tier": tier(rep["points"]),
                       "blocked": False, "note": note, "source": ""})
    return rep


def undo_last(rep):
    """Remove the latest log entry and restore the score before it. Returns the removed entry or None."""
    rep = ensure(rep)
    if not rep["log"]:
        return None
    entry = rep["log"].pop()
    rep["points"] = clamp(rep["points"] - entry.get("delta", 0))
    return entry


def tier_note(rep, name=None):
    """Your own note for what a tier means for this faction (discounts, access, bounties...)."""
    rep = ensure(rep)
    return rep["notes"].get(name or tier(rep["points"]), "")


def attitude(tier_name, rng=None):
    """A starting NPC attitude drawn from the faction's tier."""
    rng = rng or random.Random()
    weights = ATTITUDES.get(tier_name, ATTITUDES["Ignored"])
    return rng.choices(list(weights), weights=list(weights.values()), k=1)[0]


def points_to_next(points):
    """(points to reach the next tier up, points to fall into the next tier down), or None at an end."""
    p = clamp(points)
    t = tier(p)
    names = [x[0] for x in TIERS]
    i = names.index(t)
    up = (TIERS[i - 1][1] - p) if i > 0 else None
    down = (p - TIERS[i + 1][2]) if i < len(TIERS) - 1 else None
    return up, down


def summary_line(title, rep):
    rep = ensure(rep)
    p = rep["points"]
    return f"{title}: {tier(p)} ({p:+d})" if p else f"{title}: {tier(p)} (0)"

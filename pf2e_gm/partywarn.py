"""Party-aware warnings: enemies the party's weapons can't hurt well, and weaknesses they can exploit.

Uses the damage types of PCs' Strikes (from Pathbuilder). Spells and class features aren't read, so
these are prompts to check, not verdicts.
"""
import re

PHYSICAL = {"bludgeoning", "piercing", "slashing"}


def _iwr_map(pairs):
    """[('Physical 5 (except Silver)', 'name:physical'), ('Fire 10', 'name:fire')] -> {'physical': 5, 'fire': 10}"""
    out = {}
    for p in pairs or []:
        text = p[0] if isinstance(p, (list, tuple)) else str(p)
        key = (p[1].split(":", 1)[1] if isinstance(p, (list, tuple)) and len(p) > 1 and p[1] else text)
        key = re.sub(r"\s*\(.*\)", "", key).strip().lower().replace(" ", "-")
        key = re.sub(r"-?\d+$", "", key).strip("-")
        m = re.search(r"\b(\d+)\b", re.sub(r"\(.*\)", "", text))
        out[key] = int(m.group(1)) if m else None
    return out


def party_damage_types(party):
    return {t for pc in party for t in (pc.get("damage_types") or [])}


def creature_warnings(d, party):
    """List of short warnings for one stat block versus the party."""
    types = party_damage_types(party)
    if not d or not types:
        return []
    imm, res, weak = _iwr_map(d.get("immunities")), _iwr_map(d.get("resistances")), _iwr_map(d.get("weaknesses"))
    out = []
    blocked = [t for t in types if t in imm or ("physical" in imm and t in PHYSICAL)]
    if blocked and len(blocked) == len(types):
        out.append(f"immune to all the party's weapon damage ({', '.join(sorted(blocked))})")
    elif blocked:
        out.append(f"immune to {', '.join(sorted(blocked))}")
    resisted = []
    for t in types:
        v = res.get(t) or (res.get("physical") if t in PHYSICAL else None) or res.get("all-damage")
        if v and t not in blocked:
            resisted.append(f"{t} {v}")
    if resisted and len(resisted) + len(blocked) == len(types):
        out.append(f"resists every weapon type the party uses ({', '.join(resisted)})")
    elif resisted:
        out.append(f"resists {', '.join(resisted)}")
    hits = [f"{t} {weak[t]}" for t in types if t in weak and weak[t]]
    if hits:
        out.append(f"weak to {', '.join(hits)} (party has it)")
    return out


def encounter_warnings(groups, details_for, party):
    """{display name: [warnings]} for creatures in an encounter."""
    out = {}
    for c, _ in groups:
        if getattr(c, "is_hazard", False):
            continue
        w = creature_warnings(details_for(c), party)
        if w:
            out[c.display_name] = w
    return out

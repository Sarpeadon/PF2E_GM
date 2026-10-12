"""Custom spells and abilities, turned into rules entries the app can link and render.

Custom entries are registered with DetailsDB.set_custom_rules(), so they are clickable anywhere
(creature spell lists, ability names, rules text) and custom spells get the same "Cast by"
heightening section as official spells.
"""
import re

from .statblock import ACTION_GLYPH, norm

CAST_OPTIONS = ["1", "2", "3", "1 to 3", "reaction", "free", "1 minute", "10 minutes", "1 hour", "1 day"]
CAST_LABEL = {"1": "[1]", "2": "[2]", "3": "[3]", "reaction": "[R]", "free": "[F]"}
TRADITIONS = ["arcane", "divine", "occult", "primal"]
DEFENSES = ["", "AC", "Fortitude", "Reflex", "Will", "basic Fortitude", "basic Reflex", "basic Will"]
AREA_TYPES = ["", "burst", "cone", "emanation", "line", "cylinder", "square", "wall"]
SPELL_KINDS = ["Spell", "Cantrip", "Focus", "Ritual"]
DICE = re.compile(r"^\d+d\d+$")


def spell_entry(sp):
    """Custom spell dict -> rules entry (same shape build_rule() produces)."""
    rank = int(sp.get("rank") or 1)
    kind = sp.get("spell_kind") or "Spell"
    traits = list(sp.get("traits") or [])
    for t in sp.get("traditions") or []:
        if t not in traits:
            traits.append(t)
    if kind == "Cantrip" and "cantrip" not in traits:
        traits.insert(0, "cantrip")
    if kind == "Focus" and "focus" not in traits:
        traits.insert(0, "focus")
    cast = str(sp.get("cast") or "")
    meta = []
    if cast and cast not in CAST_LABEL:
        meta.append(["Cast", cast])
    if sp.get("traditions"):
        meta.append(["Traditions", ", ".join(sp["traditions"])])
    for label, key in (("Range", "range"), ("Targets", "targets"), ("Defense", "defense"), ("Duration", "duration")):
        if sp.get(key):
            meta.append([label, sp[key]])
    if sp.get("area_size"):
        meta.append(["Area", f"{sp['area_size']}-foot {sp.get('area_type') or ''}".strip()])
    text = (sp.get("description") or "").strip()
    heightened = [l.strip() for l in (sp.get("heightened") or "").splitlines() if l.strip()]
    if heightened:
        text += "\n---\n" + "\n".join(heightened)
    damage, heightening = [], None
    if sp.get("damage"):
        damage = [["0", sp["damage"].strip(), (sp.get("damage_type") or "").strip()]]
        inc = (sp.get("heighten_damage") or "").strip()
        if inc and DICE.match(inc):
            heightening = {"type": "interval", "interval": int(sp.get("heighten_interval") or 1),
                           "damage": {"0": inc}}
    return {"name": sp["name"], "kind": "spell", "header": f"{kind} {rank}",
            "glyph": CAST_LABEL.get(cast, ""), "traits": traits, "rarity": sp.get("rarity") or "common",
            "source": sp.get("source") or "Hallowmead", "meta": meta, "text": text,
            "spell_rank": rank, "cantrip": kind == "Cantrip", "damage": damage, "heightening": heightening,
            "flavor": (sp.get("flavor") or "").strip(), "custom": True}


def ability_entry(ab):
    """Custom ability dict -> rules entry (kind 'action')."""
    meta = []
    for label, key in (("Frequency", "frequency"), ("Trigger", "trigger"), ("Requirements", "requirements")):
        if ab.get(key):
            meta.append([label, ab[key]])
    return {"name": ab["name"], "kind": "action", "header": "Ability", "glyph": ab.get("glyph") or "",
            "traits": list(ab.get("traits") or []), "rarity": "common", "source": ab.get("source") or "Hallowmead",
            "meta": meta, "text": (ab.get("text") or "").strip(), "custom": True}


def ability_to_line(ab):
    """Line for a creature's Abilities box: Name [2] (traits): text (trigger/frequency folded in)."""
    head = ab["name"] + (f" {ab['glyph']}" if ab.get("glyph") else "")
    if ab.get("traits"):
        head += f" ({', '.join(ab['traits'])})"
    bits = []
    for label, key in (("Frequency", "frequency"), ("Trigger", "trigger"), ("Requirements", "requirements")):
        if ab.get(key):
            bits.append(f"{label} {ab[key]};")
    body = " ".join(bits + [(ab.get("text") or "").replace("\n", " ").strip()])
    return f"{head}: {body}".rstrip()


def custom_rule_entries(spells, abilities):
    return [spell_entry(s) for s in spells if s.get("name")] + [ability_entry(a) for a in abilities if a.get("name")]


def find(lib, name):
    n = norm(name)
    return next((x for x in lib if norm(x.get("name", "")) == n), None)

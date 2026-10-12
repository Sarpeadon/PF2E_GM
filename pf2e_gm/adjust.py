"""Elite/Weak stat block adjustments and Recall Knowledge summaries."""
import copy
import re

from .gmtables import adjusted_level, elite_hp, recall_dc, recall_skills, weak_hp

SIGNED = re.compile(r"([+-])(\d+)")
DC_RE = re.compile(r"\bDC (\d+)")
DMG_MOD = re.compile(r"^(\d+d\d+)([+-]\d+)?")


def _shift_signed(text, delta):
    """Shift every signed number (+12, -1) in a string by delta."""
    def rep(m):
        v = int(m.group(1) + m.group(2)) + delta
        return f"+{v}" if v >= 0 else str(v)
    return SIGNED.sub(rep, text or "")


def _shift_dc(text, delta):
    return DC_RE.sub(lambda m: f"DC {int(m.group(1)) + delta}", text or "")


def _shift_damage(expr, delta):
    """'2d6+6 piercing' -> '2d6+8 piercing'. Only the first dice expression changes."""
    m = DMG_MOD.match(expr or "")
    if not m:
        return expr
    mod = int(m.group(2) or 0) + delta
    new = m.group(1) + (f"+{mod}" if mod > 0 else str(mod) if mod < 0 else "")
    return new + expr[m.end():]


def apply_adjustment(d, adjust):
    """Return a copy of a stat block dict with the Elite or Weak adjustment applied."""
    if adjust not in ("elite", "weak") or not d or d.get("kind") == "hazard":
        return d
    d = copy.deepcopy(d)
    base = d.get("level") or 0
    sign = 1 if adjust == "elite" else -1
    delta = 2 * sign
    d["level"] = adjusted_level(base, adjust)
    d["name"] = f"{'Elite' if adjust == 'elite' else 'Weak'} {d['name']}"
    if d.get("ac") is not None:
        d["ac"] = d["ac"] + delta
    if d.get("hp") is not None:
        d["hp"] = max(1, d["hp"] + (elite_hp(base) if adjust == "elite" else -weak_hp(base)))
    for key in ("perception", "saves", "skills"):
        if d.get(key):
            d[key] = _shift_signed(d[key], delta)
    for st in d.get("strikes", []) or []:
        if isinstance(st, dict):
            st["bonus"] = _shift_signed(st.get("bonus", ""), delta)
            st["damage"] = [_shift_damage(x, delta) for x in st.get("damage", [])][:1] + st.get("damage", [])[1:]
    for sp in d.get("spells", []) or []:
        if isinstance(sp, dict):
            sp["head"] = _shift_signed(_shift_dc(sp["head"], delta), delta)
    for a in d.get("actions", []) or []:
        a["text"] = _shift_dc(a.get("text", ""), delta)
    d["adjust_delta"] = delta                       # lets rolls show "Elite +2" / "Weak -2" separately
    d["adjust_label"] = "Elite" if adjust == "elite" else "Weak"
    d["adjust_note"] = (
        f"{'Elite' if adjust == 'elite' else 'Weak'} adjustment applied: AC, saves, Perception, skills, "
        f"Strike attacks and damage, spell DC/attack, and ability DCs shifted by {delta:+d}. "
        f"Damage from abilities other than Strikes is NOT changed: use {delta:+d} "
        f"({2 * delta:+d} for limited-use abilities like breath weapons).")
    return d


# ---------- Recall Knowledge ----------
def _saves(saves_text):
    out = {}
    for name, val in re.findall(r"(Fort|Ref|Will) ([+-]\d+)", saves_text or ""):
        out[name] = int(val)
    return out


def _names(pairs):
    out = []
    for p in pairs or []:
        out.append(p[0] if isinstance(p, (list, tuple)) else str(p))
    return out


def recall_knowledge(d):
    """Summary dict: dc, skills, reveal suggestions (ordered roughly most useful first)."""
    if not d or d.get("kind") == "hazard":
        return None
    level = d.get("level") if d.get("level") is not None else 0
    skills = recall_skills(d.get("traits", []))
    reveal = []
    weak = _names(d.get("weaknesses"))
    if weak:
        reveal.append("Weaknesses: " + ", ".join(weak))
    saves = _saves(d.get("saves"))
    if saves:
        low = min(saves, key=saves.get)
        high = max(saves, key=saves.get)
        if saves[low] != saves[high]:
            reveal.append(f"Lowest save: {low} {saves[low]:+d} (highest: {high} {saves[high]:+d})")
    imm = _names(d.get("immunities"))
    res = _names(d.get("resistances"))
    if imm:
        reveal.append("Immunities: " + ", ".join(imm))
    if res:
        reveal.append("Resistances: " + ", ".join(res))
    notable = [a["name"] for a in d.get("actions", []) or []
               if a.get("glyph") or a.get("category") == "offensive"][:4]
    if notable:
        reveal.append("Notable abilities: " + ", ".join(notable))
    return {"dc": recall_dc(level, d.get("rarity")), "skills": skills, "reveal": reveal}

"""Dice rolling for clickable checks, attacks, and damage.

Roll refs live in stat block segments as  roll:<urlencoded fields>
    k  kind: check | attack | damage | expr
    l  label shown in the result ("Stealth", "Jaws", "Fort")
    e  expression: a modifier for checks/attacks ("+13"), a damage expression for damage
    w  who is rolling (creature name)
    t  comma-separated traits (deadly-d10, fatal-d12, agile...) for damage crits and MAP
"""
import json
import random
import re
import urllib.parse
from dataclasses import dataclass, field

DAMAGE_TYPES = ["acid", "bleed", "bludgeoning", "cold", "electricity", "fire", "force", "mental", "piercing",
                "poison", "precision", "slashing", "sonic", "spirit", "vitality", "void", "positive", "negative",
                "chaotic", "evil", "good", "lawful", "holy", "unholy", "persistent", "splash", "untyped"]
TERM = re.compile(r"([+-]?)\s*(\d*)d(\d+)|([+-]?)\s*(\d+)")
DICE_EXPR = re.compile(r"^\s*(?:\d*d\d+|\d+)(?:\s*[+-]\s*(?:\d*d\d+|\d+))*")
# Dice in plain rules text: "2d6+4 fire", "1d6 persistent bleed", "3d8"
TEXT_DICE = re.compile(r"\b\d+d\d+(?:\s*[+-]\s*\d+(?!d))?(?:\s+(?:persistent\s+)?(?:" + "|".join(DAMAGE_TYPES) + r")\b)?",
                       re.IGNORECASE)


def make_ref(kind, label, expr, who="", traits=(), mods=None, dmg=None, dmg_mods=None, note=""):
    """Build a roll ref.

    checks/attacks: expr is the total modifier; mods is [[label, value], ...] summing to it (shown as the
                    breakdown). Attacks can carry dmg (damage expression) and dmg_mods (flat modifiers) so the
                    damage and the crit damage are rolled together with the attack.
    damage:         expr is the base damage expression; mods are flat modifiers added to the first part.
    """
    fields = {"k": kind, "l": label, "e": expr, "w": who}
    if traits:
        fields["t"] = ",".join(traits)
    if mods:
        fields["m"] = json.dumps([[str(l), int(v)] for l, v in mods])
    if dmg:
        fields["d"] = dmg
    if dmg_mods:
        fields["dm"] = json.dumps([[str(l), int(v)] for l, v in dmg_mods])
    if note:
        fields["n"] = note
    return "roll:" + urllib.parse.urlencode(fields)


def parse_ref(ref):
    d = dict(urllib.parse.parse_qsl(ref[5:] if ref.startswith("roll:") else ref, keep_blank_values=True))
    d["t"] = [t for t in d.get("t", "").split(",") if t]
    for key in ("m", "dm"):
        try:
            d[key] = [(str(l), int(v)) for l, v in json.loads(d[key])] if d.get(key) else []
        except (ValueError, TypeError):
            d[key] = []
    return d


@dataclass
class Rolled:
    total: int
    detail: str            # "[3, 5] + 6"
    dice: list = field(default_factory=list)   # (sides, value)


def roll_math(expr, rng, die_override=None):
    """Roll '2d6+6' style math. die_override replaces every die size (fatal)."""
    total, parts, dice, first = 0, [], [], True
    for m in TERM.finditer(expr.replace(" ", "")):
        if m.group(3):
            sign = -1 if m.group(1) == "-" else 1
            n = int(m.group(2) or 1)
            sides = die_override or int(m.group(3))
            vals = [rng.randint(1, sides) for _ in range(n)]
            dice += [(sides, v) for v in vals]
            total += sign * sum(vals)
            parts.append(("- " if sign < 0 else ("" if first else "+ ")) + f"{n}d{sides}{vals}")
        else:
            sign = -1 if m.group(4) == "-" else 1
            v = int(m.group(5))
            total += sign * v
            parts.append(("- " if sign < 0 else ("" if first else "+ ")) + str(v))
        first = False
    return Rolled(total, " ".join(parts), dice)


def split_damage(text):
    """'2d6+6 piercing plus 1d6 fire' or '2d6+6 piercing, 1d6 fire' -> [('2d6+6', 'piercing'), ('1d6', 'fire')]."""
    out = []
    for part in re.split(r"\s+plus\s+|,\s*|\s+and\s+", text or ""):
        part = part.strip()
        m = DICE_EXPR.match(part)
        if not m:
            continue
        expr = m.group(0).replace(" ", "")
        dtype = part[m.end():].strip()
        out.append((expr, dtype))
    return out


def _trait_die(traits, name):
    for t in traits:
        m = re.match(rf"{name}-?d(\d+)$", t.lower())
        if m:
            return int(m.group(1))
    return None


def map_steps(traits):
    return (4, 8) if any(t.lower() == "agile" for t in traits) else (5, 10)


W = 26   # label column width in breakdowns


def _row(label, value, extra=""):
    label = (label + " ").ljust(W, ".")
    return f"  {label} {value}{('  ' + extra) if extra else ''}"


def _signed(v):
    return f"{v:+d}"


def thresholds(total, nat):
    """(highest AC this attack hits, highest AC it crits, or None if it can't crit).

    Hit if total >= AC, crit if total >= AC + 10; a natural 20 improves the result one step,
    a natural 1 worsens it one step."""
    if nat == 20:
        return total + 9, total
    if nat == 1:
        return total - 10, None
    return total, total - 10


def roll_damage(expr, mods=(), traits=(), rng=None, crit=False):
    """Roll damage with a line-by-line breakdown.

    expr: '2d6+6 piercing plus 1d6 fire'; mods: [(label, value)] flat modifiers added to the first part.
    crit=True doubles everything; deadly adds one extra die, fatal rolls the first part with the bigger
    die and adds one. Persistent parts are listed but not doubled. Minimum 1 damage.
    Returns {total, lines (breakdown rows), by_type, parts}.
    """
    rng = rng or random.Random()
    parts = split_damage(expr)
    if not parts:
        return None
    fatal, deadly = _trait_die(traits, "fatal"), _trait_die(traits, "deadly")
    rows, by_type, total = [], [], 0
    for i, (e, dtype) in enumerate(parts):
        first = i == 0
        die = fatal if (crit and fatal and first) else None
        r = roll_math(e, rng, die_override=die)
        dice_vals = [v for _, v in r.dice]
        sub = r.total
        flat = sub - sum(dice_vals)
        if r.dice:
            dice_label = re.sub(r"[+-]\d+$", "", e)
            if die:
                dice_label = re.sub(r"d\d+", f"d{die}", dice_label) + " (fatal)"
            if not first and dtype:
                dice_label += f" {dtype}"
            rows.append(_row(dice_label, sum(dice_vals), str(dice_vals)))
        if flat:
            rows.append(_row("damage modifier" if first else f"modifier ({dtype})", _signed(flat)))
        if first:
            for label, v in mods:
                rows.append(_row(label, _signed(v)))
                sub += v
            sub = max(1, sub)
        extra = 0
        if first and crit and (fatal or deadly):
            size = fatal or deadly
            extra = rng.randint(1, size)
            rows.append(_row(f"{'fatal' if fatal else 'deadly'} extra d{size}", extra, "(added after doubling)"))
        persistent = "persistent" in (dtype or "").lower()
        part_total = (sub if (persistent or not crit) else 2 * sub) + extra
        by_type.append((part_total, dtype))
        total += part_total
    # For applying damage: persistent parts become a condition instead of immediate damage.
    immediate = [(n, t) for (n, t) in by_type if "persistent" not in (t or "").lower()]
    persist = [(e, (t or "").lower().replace("persistent", "").strip())
               for e, t in parts if "persistent" in (t or "").lower()]
    return {"total": total, "lines": rows, "by_type": by_type, "parts": parts,
            "immediate": immediate, "persist": persist}


def _damage_block(label, expr, mods, traits, rng, crit):
    r = roll_damage(expr, mods, traits, rng, crit)
    if r is None:
        return None, []
    types = ", ".join(f"{n} {t}".strip() for n, t in r["by_type"])
    title = (f"Critical damage{(' (' + label + ')') if label else ''}: {r['total']}" if crit
             else f"Damage{(' (' + label + ')') if label else ''}: {r['total']}")
    lines = [r["lines"]]
    note = "  doubled: 2 x (dice + modifiers)" + (", then the extra die" if
                                                   _trait_die(traits, "deadly") or _trait_die(traits, "fatal") else "")
    out = [(title + (f"  ({types})" if len(r["by_type"]) > 1 or r["by_type"][0][1] else "") + "\n",
            "crit" if crit else "big2")]
    out += [(row + "\n", "mono") for row in r["lines"]]
    if crit:
        out.append((note + "\n", "muted"))
    if any("persistent" in (t or "").lower() for _, t in r["parts"]):
        out.append(("  persistent damage isn't doubled; it applies at end of turn\n", "muted"))
    return r, out


def roll(ref, rng=None):
    """Roll a ref. Returns dict with: title, lines (plain, for the log), styled [(text, tag)] for the dice
    window, total, nat, kind, who, and for attacks/damage: damage, crit, hit_ac, crit_ac."""
    rng = rng or random.Random()
    r = parse_ref(ref)
    kind, label, expr, who, traits = r.get("k", "expr"), r.get("l", ""), r.get("e", ""), r.get("w", ""), r["t"]
    head = f"{who}: " if who else ""
    if kind in ("check", "attack"):
        try:
            mod = int(expr.replace(" ", "") or 0)
        except ValueError:
            mod = 0
        mods = r["m"] or [(label or "modifier", mod)]
        mod = sum(v for _, v in mods)
        nat = rng.randint(1, 20)
        total = nat + mod
        flag = "  NAT 20" if nat == 20 else ("  NAT 1" if nat == 1 else "")
        what = f"{label} {'attack' if kind == 'attack' else 'check'}".strip()
        styled = [(f"{head}{what}\n", "title"), (f"{total}{flag}\n", "big")]
        styled.append((_row("d20", nat) + "\n", "mono"))
        styled += [(_row(l, _signed(v)) + "\n", "mono") for l, v in mods]
        styled.append((_row("total", total) + "\n", "monob"))
        res = {"title": what, "total": total, "nat": nat, "kind": kind, "who": who,
               "lines": [f"{head}{what}: d20 ({nat}) " + " ".join(f"{v:+d} {l}" for l, v in mods)
                         + f" = {total}{flag}"]}
        if kind == "attack":
            hit_ac, crit_ac = thresholds(total, nat)
            res["hit_ac"], res["crit_ac"] = hit_ac, crit_ac
            styled.append((f"Hits AC {hit_ac} or below" + (" (natural 20 improves the result one step)"
                                                           if nat == 20 else
                                                           " (natural 1 worsens the result one step)"
                                                           if nat == 1 else "") + "\n", "muted"))
            if r.get("d"):
                dmg, block = _damage_block(label, r["d"], r["dm"], traits, rng, crit=False)
                if dmg:
                    res["damage"] = dmg["total"]
                    res["damage_parts"], res["persist"] = dmg["immediate"], dmg["persist"]
                    styled += block
                if crit_ac is not None:
                    styled.append((f"Crit if AC is {crit_ac} or below:\n", "crithead"))
                    cdmg, cblock = _damage_block(label, r["d"], r["dm"], traits, rng, crit=True)
                    if cdmg:
                        res["crit"] = cdmg["total"]
                        res["crit_parts"] = cdmg["immediate"]
                        styled += cblock
                else:
                    styled.append(("Can't be a critical hit (natural 1).\n", "muted"))
                if dmg:
                    res["lines"][0] += f"; damage {dmg['total']}" + (f", crit {res['crit']}" if "crit" in res else "")
            elif crit_ac is not None:
                styled.append((f"Crit if AC is {crit_ac} or below\n", "crithead"))
        res["styled"] = styled
        return res

    parts = split_damage(expr)
    if not parts:
        return {"title": label or expr, "lines": [f"{head}Can't roll '{expr}'"], "total": None, "kind": kind,
                "who": who, "styled": [(f"Can't roll '{expr}'\n", "muted")]}
    if kind == "expr" or not any(t for _, t in parts) and kind != "damage":
        rolled = [roll_math(e, rng) for e, _ in parts]
        total = sum(x.total for x in rolled)
        detail = " + ".join(x.detail for x in rolled)
        return {"title": label or expr, "lines": [f"{head}{label or expr}: {detail} = {total}"],
                "total": total, "kind": kind, "who": who,
                "styled": [(f"{head}{label or expr}\n", "title"), (f"{total}\n", "big"), (f"  {detail}\n", "mono")]}

    dmg, block = _damage_block(label, expr, r["m"], traits, rng, crit=False)
    cdmg, cblock = _damage_block(label, expr, r["m"], traits, rng, crit=True)
    styled = [(f"{head}{(label + ' ') if label else ''}damage\n", "title"), (f"{dmg['total']}\n", "big")]
    styled += block[1:] + [("If this is a critical hit:\n", "crithead")] + cblock
    lines = [f"{head}{label + ' ' if label else ''}damage {dmg['total']} | crit {cdmg['total']}"]
    return {"title": f"{label} damage".strip(), "lines": lines, "total": dmg["total"], "crit": cdmg["total"],
            "damage": dmg["total"], "kind": "damage", "who": who, "styled": styled,
            "damage_parts": dmg["immediate"], "crit_parts": cdmg["immediate"], "persist": dmg["persist"]}


def roll_expression(text, rng=None):
    """Roll a typed expression: '1d20+7', '2d6+4 fire', 'd20'."""
    t = text.strip()
    if re.fullmatch(r"[+-]?\d+", t):
        return roll(make_ref("check", "", t), rng)
    if t.lower().startswith("d"):
        t = "1" + t
    m = re.fullmatch(r"1d20\s*([+-]\s*\d+)?", t)
    if m:
        return roll(make_ref("check", "", (m.group(1) or "+0").replace(" ", "")), rng)
    has_type = any(dt for _, dt in split_damage(t))
    return roll(make_ref("damage" if has_type else "expr", "", t), rng)

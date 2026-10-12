"""Creature templates: turn any creature or NPC into a mummy, ghost, vampire, werecreature, and so on.

The built-in templates follow the rules for the undead adjustments in Book of the Dead (page 72 to 73) and the
"Creating Werecreatures" steps in Monster Core (page 344). Each one is written as a small function that edits a copy of
a custom creature: traits, languages, senses, immunities, weaknesses, resistances, speeds, Strikes, abilities, level,
and HP. Level-based numbers live in the tables below, so they are easy to check against your books.

The rules text in this file is paraphrased. The numbers and the list of changes are what the books give. Anything the
books leave open is noted in the change log the dialog shows, and listed under "Check these" after you apply a template.

Book of the Dead uses the older words positive and negative. By default they are shown the Remaster way (vitality and
void) so they match the damage types the combat tracker uses. Pass mode="legacy" to keep the book's words.

Your own templates (see CUSTOM_FIELDS) are stored as plain data and applied by the same code.
"""
import copy
import re

try:
    from .gmtables import ATTACK, DAMAGE, SKILL, SPELL
    from .models import Creature
except ImportError:                                  # standalone use (tests)
    from gmtables import ATTACK, DAMAGE, SKILL, SPELL
    from models import Creature

MODES = {"remaster": "Remaster words (void, vitality)", "legacy": "Book of the Dead words (negative, positive)"}
TERMS = {"negative": "void", "positive": "vitality"}
PHYSICAL = ("bludgeoning", "piercing", "slashing")
SIZES = ["tiny", "sm", "med", "lg", "huge", "grg"]
NATURAL = ("jaws", "fangs", "fang", "bite", "teeth", "maw", "claw", "claws", "fist", "slam", "talon", "tail", "horn",
           "hoof", "tentacle", "wing", "tongue", "stinger", "pincer", "beak", "tusk", "gore", "unarmed")


class TemplateError(Exception):
    """A template can't be applied (already on the creature, or the creature has nothing to work with)."""


# ---------------------------------------------------------------------------------------------- level tables
# Each table is [(highest level this row covers, values)], the last row covers everything above.
FIRE_WEAKNESS = [(3, 3), (8, 5), (13, 10), (None, 15)]                    # mummy fire, ghost and shadow weaknesses
SKELETON = [(-1, (-2, 2)), (1, (-4, 2)), (5, (-10, 3)), (10, (-20, 5)), (None, (-40, 10))]   # (HP change, resistance)
VAMPIRE = [(-1, (-3, 2)), (1, (-5, 2)), (5, (-10, 3)), (10, (-20, 5)), (None, (-40, 10))]    # (HP change, resistance and Feed HP)
ZOMBIE = [(1, (10, 5)), (5, (20, 5)), (10, (50, 10)), (15, (75, 15)), (19, (100, 20)), (None, (150, 25))]   # (HP, weaknesses)
WERECREATURE = [(4, (25, 5)), (7, (35, 7)), (14, (50, 10)), (None, (75, 15))]   # (HP, weakness to silver)

WERE_ANIMALS = ["Wolf", "Rat", "Bear", "Boar", "Bat", "Tiger", "Crocodile", "Shark", "Moose"]
VAMPIRE_KINDS = {"Moroi (silver)": "silver", "Vetalarana (cold iron)": "cold iron",
                 "Jiang-shi (wood)": "wood", "Nosferatu (wood)": "wood"}


def pick(level, table):
    level = int(level)
    for top, val in table:
        if top is None or level <= top:
            return val
    return table[-1][1]


# ---------------------------------------------------------------------------------------------- text helpers
def split_commas(text):
    """Split on commas that are not inside parentheses."""
    out, depth, cur = [], 0, ""
    for ch in str(text or ""):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return [x for x in out if x]


IWR_RE = re.compile(r"^(?P<name>[A-Za-z' -]+?)(?:\s+(?P<val>\d+))?(?:\s*\((?P<exc>[^)]*)\))?\s*$")


def parse_iwr(text):
    """'fire 5, physical 5 (except silver)' -> [(name, value or None, exception text)]"""
    out = []
    for part in split_commas(text):
        m = IWR_RE.match(part)
        if m:
            out.append((m.group("name").strip(), int(m.group("val")) if m.group("val") else None, m.group("exc") or ""))
        else:
            out.append((part, None, ""))
    return out


def fmt_iwr(entries):
    return ", ".join(n + (f" {v}" if v is not None else "") + (f" ({e})" if e else "") for n, v, e in entries)


SPEED_RE = re.compile(r"^(?:(?P<kind>[A-Za-z ]+?)\s+)?(?P<val>\d+)\s*(?:feet|ft\.?)?\s*(?P<rest>.*)$")


def parse_speeds(text):
    """'25 feet, fly 30 feet' -> [('land', 25, ''), ('fly', 30, '')]. Unparseable pieces keep their text as the kind."""
    out = []
    for part in split_commas(text):
        m = SPEED_RE.match(part)
        if m:
            out.append(((m.group("kind") or "land").strip().lower(), int(m.group("val")), m.group("rest").strip()))
        else:
            out.append((part, None, ""))
    return out


def fmt_speeds(speeds):
    bits = []
    for kind, val, rest in speeds:
        if val is None:
            bits.append(kind)
        else:
            bits.append((f"{val} feet" if kind == "land" else f"{kind} {val} feet") + (f" {rest}" if rest else ""))
    return ", ".join(bits)


SIGNED_END = re.compile(r"(?<![\w])([+-])(\d+)(?=\s*(?:,|;|$))")


def bump_signed(text, n):
    """Add n to every trailing signed number in a list such as 'Athletics +11, Stealth +13'."""
    return SIGNED_END.sub(lambda m: f"{int(m.group(1) + m.group(2)) + n:+d}", str(text or ""))


def bump_dcs(text, n):
    """Add n to every 'DC 23' in a block of text."""
    return re.sub(r"\bDC (\d+)", lambda m: f"DC {int(m.group(1)) + n}", str(text or ""))


def bump_attacks(text, n):
    """Add n to every 'attack +12' (a spell attack bonus) in a block of text."""
    return re.sub(r"\battack ([+-]\d+)", lambda m: f"attack {int(m.group(1)) + n:+d}", str(text or ""))


def skill_values(text):
    return [(m.group(1).strip(), int(m.group(2))) for m in re.finditer(r"([^,;]+?)\s+([+-]\d+)(?=\s*(?:,|;|$))", str(text or ""))]


DMG_RE = re.compile(r"^\s*(?:(\d+)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*(.*)$")


def parse_dmg(expr):
    """'2d6+6 piercing' -> dict(n, die, flat, rest). A flat-only entry such as '5 bludgeoning' has n == 0."""
    m = DMG_RE.match(str(expr or ""))
    if not m:
        return None
    n, die, flat_only, sign, flat, rest = m.groups()
    if n is not None:
        f = int(flat) * (-1 if sign == "-" else 1) if flat else 0
        return {"n": int(n), "die": int(die), "flat": f, "rest": rest.strip()}
    return {"n": 0, "die": 0, "flat": int(flat_only) + (int(flat) * (-1 if sign == "-" else 1) if flat else 0), "rest": rest.strip()}


def fmt_dmg(p):
    if p["n"]:
        s = f"{p['n']}d{p['die']}" + (f"{p['flat']:+d}" if p["flat"] else "")
    else:
        s = str(max(0, p["flat"]))
    return (s + (" " + p["rest"] if p["rest"] else "")).strip()


def avg_dmg(expr):
    p = parse_dmg(expr)
    if not p:
        return 0.0
    return (p["n"] * (p["die"] + 1) / 2 if p["n"] else 0) + p["flat"]


def shift_dmg(expr, delta):
    p = parse_dmg(expr)
    if not p or not delta:
        return expr
    p["flat"] += delta
    return fmt_dmg(p)


def scale_dmg(expr, factor, new_type=None):
    """A damage expression with about `factor` times the average damage, keeping the die size where it can."""
    p = parse_dmg(expr)
    if not p:
        return expr
    target = round(avg_dmg(expr) * factor)
    if p["n"]:
        n = max(1, round(p["n"] * factor))
        flat = round(target - n * (p["die"] + 1) / 2)
        while flat < 0 and n > 1:
            n -= 1
            flat = round(target - n * (p["die"] + 1) / 2)
        p["n"], p["flat"] = n, max(0, flat)
    else:
        p["flat"] = target
    if new_type:
        p["rest"] = new_type
    return fmt_dmg(p)


ABIL_RE = re.compile(r"^\s*([^:\[\(\n]+?)\s*(\[(?:1|2|3|R|F)\])?\s*(?:\(([^)]*)\))?\s*:\s*(.*)$")
GLYPH = {1: "[1]", 2: "[2]", 3: "[3]", "R": "[R]", "F": "[F]"}


def ability_line(name, glyph="", traits=(), text=""):
    head = name + (f" {GLYPH.get(glyph, glyph)}" if glyph else "")
    if traits:
        head += f" ({', '.join(traits)})"
    return f"{head}: {text}".strip()


def ability_blocks(text):
    """Ability text -> [(lowercase name, full text of the block)]. Lines that don't start an ability continue the last one."""
    blocks = []
    for line in str(text or "").splitlines():
        m = ABIL_RE.match(line)
        if m:
            blocks.append([m.group(1).strip().lower(), line.rstrip(), m.group(2) or ""])
        elif blocks and line.strip():
            blocks[-1][1] += "\n" + line.rstrip()
        elif line.strip():
            blocks.append(["", line.rstrip(), ""])
    return blocks


def parse_strikes(text):
    out = []
    for line in str(text or "").splitlines():
        if not line.strip():
            continue
        p = [x.strip() for x in line.split("|")] + [""] * 5
        out.append({"name": p[0], "bonus": p[1], "damage": split_commas(p[2]), "traits": split_commas(p[3]),
                    "effects": split_commas(p[4])})
    return out


def fmt_strikes(strikes):
    return "\n".join(" | ".join([s["name"], s["bonus"], ", ".join(s["damage"]), ", ".join(s["traits"]),
                                 ", ".join(s["effects"])]) for s in strikes)


def strike_avg(s):
    return avg_dmg(s["damage"][0]) if s["damage"] else 0.0


def is_ranged(s):
    return any(str(t).lower().startswith(("range", "thrown")) for t in s["traits"])


def is_agile(s):
    return any(str(t).lower() == "agile" for t in s["traits"])


def is_unarmed(s):
    return any(str(t).lower() == "unarmed" for t in s["traits"]) or \
        any(w in s["name"].lower() for w in NATURAL)


def bonus_int(s):
    m = re.fullmatch(r"[+-]?\d+", str(s["bonus"]).strip())
    return int(s["bonus"]) if m else None


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


# ---------------------------------------------------------------------------------------------- the working copy
class Work:
    """A copy of a creature plus the notes that say what was changed."""

    def __init__(self, c, mode="remaster"):
        self.c = copy.deepcopy(c)
        self.c.custom = True
        self.c.stats = dict(self.c.stats or {})
        self.st = self.c.stats
        self.mode = mode if mode in MODES else "remaster"
        self.level0 = int(c.level)
        self.log, self.warns = [], []

    # words and notes
    def T(self, word):
        return TERMS.get(word, word) if self.mode == "remaster" else word

    def say(self, text):
        self.log.append(text)

    def warn(self, text):
        self.warns.append(text)

    # traits and lists
    def add_trait(self, *names):
        new = [n for n in names if n and n.lower() not in [t.lower() for t in self.c.traits]]
        self.c.traits = list(self.c.traits) + new
        if new:
            self.say("Traits added: " + ", ".join(new))

    def add_list(self, key, items, label=None, quiet=False):
        cur = split_commas(self.st.get(key, ""))
        have = {x.lower().split(" (")[0] for x in cur}
        new = [i for i in items if i and i.lower() not in have]
        if new:
            self.st[key] = ", ".join(cur + new)
            if not quiet:
                self.say(f"{label or key.title()} added: " + ", ".join(new))
        return new

    def immune(self, *names):
        self.add_list("immunities", [self.T(n) for n in names], "Immunities")

    def merge_iwr(self, key, entries, label):
        """Add weaknesses or resistances. A type the creature already has keeps the higher number."""
        cur = parse_iwr(self.st.get(key, ""))
        done = []
        for name, val, exc in entries:
            name = self.T(name)
            hit = next((i for i, (n, v, e) in enumerate(cur) if n.lower() == name.lower() and e == exc), None)
            if hit is None:
                cur.append((name, val, exc))
                done.append(f"{name} {val}" if val is not None else name)
            elif val is not None and (cur[hit][1] or 0) < val:
                cur[hit] = (cur[hit][0], val, exc)
                done.append(f"{name} raised to {val}")
        if done:
            self.st[key] = fmt_iwr(cur)
            self.say(f"{label}: " + ", ".join(done))

    def language(self, name):
        self.add_list("languages", [name], "Languages")

    def darkvision(self):
        self.add_list("senses", ["darkvision"], "Senses")

    # abilities
    def ability(self, name, glyph="", traits=(), text=""):
        line = ability_line(name, glyph, traits, text)
        blocks = ability_blocks(self.st.get("abilities", ""))
        for b in blocks:
            if b[0] == name.lower():
                b[1] = line
                break
        else:
            blocks.append([name.lower(), line, ""])
        self.st["abilities"] = "\n".join(b[1] for b in blocks)
        self.say(f"Ability added: {name}")

    def void_healing(self):
        name = "Void Healing" if self.mode == "remaster" else "Negative Healing"
        self.ability(name, "", (), f"This creature is healed by {self.T('negative')} effects and harmed by "
                                  f"{self.T('positive')} effects, instead of the other way around.")

    # HP
    def hp_add(self, n):
        if self.c.hp is None:
            self.warn("This creature has no HP set, so the HP change was skipped.")
            return
        old = self.c.hp
        self.c.hp = max(1, old + n)
        self.say(f"HP {old} to {self.c.hp} ({n:+d})")

    # Strikes
    def strikes(self):
        return parse_strikes(self.st.get("strikes", ""))

    def set_strikes(self, strikes):
        if strikes:
            self.st["strikes"] = fmt_strikes(strikes)
        else:
            self.st.pop("strikes", None)

    def add_strike(self, strike):
        s = self.strikes()
        s.append(strike)
        self.set_strikes(s)
        self.say(f"Strike added: {strike['name']} {strike['bonus']} ({', '.join(strike['damage'])})")

    # speeds
    def set_speeds(self, speeds):
        self.st["speed"] = fmt_speeds(speeds)

    # numbers
    def skills(self):
        return skill_values(self.st.get("skills", ""))

    def bump(self, ac=0, attack=0, dc=0, saves=0, skills=0, damage=0):
        """Add flat bonuses (or penalties) the way Elite and the werecreature steps do."""
        c, st = self.c, self.st
        if ac and c.ac is not None:
            c.ac += ac
        if saves:
            for k in ("fort", "ref", "will"):
                if isinstance(st.get(k), int):
                    st[k] += saves
        if skills and st.get("skills"):
            st["skills"] = bump_signed(st["skills"], skills)
        strikes = self.strikes()
        for s in strikes:
            b = bonus_int(s)
            if attack and b is not None:
                s["bonus"] = f"{b + attack:+d}"
            if damage and s["damage"]:
                s["damage"][0] = shift_dmg(s["damage"][0], damage)
        if strikes:
            self.set_strikes(strikes)
        if dc and st.get("abilities"):
            st["abilities"] = bump_dcs(st["abilities"], dc)
        if st.get("spells"):
            t = st["spells"]
            if dc:
                t = bump_dcs(t, dc)
            if attack:
                t = bump_attacks(t, attack)
            st["spells"] = t
        bits = [f"{lab} {v:+d}" for lab, v in (("AC", ac), ("attack bonuses", attack), ("DCs", dc), ("saves", saves),
                                               ("skills", skills), ("Strike damage", damage)) if v]
        if bits:
            self.say("Changed: " + ", ".join(bits))

    def result(self):
        return self.c


# ---------------------------------------------------------------------------------------------- shared pieces
def _mindless(w, mindless):
    if mindless:
        w.add_trait("mindless")
        w.immune("mental")
        if split_commas(w.st.get("languages", "")):
            w.warn("A mindless creature usually speaks no languages. Delete the ones it has if you want it to match.")
    else:
        w.language("Necril")


def _core_undead(w, mindless=False, necril=True):
    w.add_trait("undead")
    if mindless:
        w.add_trait("mindless")
    elif necril:
        w.language("Necril")
    w.immune("death effects", "disease", "paralyzed", "poison", "unconscious")
    if mindless:
        w.immune("mental")


def _physical_to_negative(w, magical=True):
    """Ghost and shadow: physical Strikes deal negative (void) damage and count as magical."""
    strikes, changed = w.strikes(), []
    neg = w.T("negative")
    for s in strikes:
        hit = False
        for i, d in enumerate(s["damage"]):
            new = re.sub(r"\b(bludgeoning|piercing|slashing)\b", neg, d)
            if new != d:
                s["damage"][i], hit = new, True
        if hit:
            if magical and "magical" not in [t.lower() for t in s["traits"]]:
                s["traits"].append("magical")
            changed.append(s["name"])
    if strikes:
        w.set_strikes(strikes)
    if changed:
        w.say(f"Physical Strikes now deal {neg} damage and are magical: " + ", ".join(changed))
    else:
        w.warn("No physical Strikes were found to change to " + neg + " damage.")


def _to_fly(w):
    """Ghost and shadow: if it can't fly, its highest Speed becomes a fly Speed. Every other Speed is removed."""
    speeds = [s for s in parse_speeds(w.st.get("speed", "")) if s[1] is not None]
    if not speeds:
        w.st["speed"] = "fly 25 feet"
        w.warn("It had no Speed on record, so it was given a fly Speed of 25 feet. Change it if that's wrong.")
        w.say("Speed: fly 25 feet")
        return
    fly = next((s for s in speeds if s[0] == "fly"), None)
    top = fly or max(speeds, key=lambda s: s[1])
    w.set_speeds([("fly", top[1], "" if not fly else top[2])])
    w.say(f"Speed: fly {top[1]} feet only" + ("" if fly else " (its highest Speed became a fly Speed)"))


def _weak(w, names, table=FIRE_WEAKNESS):
    v = pick(w.level0, table)
    w.merge_iwr("weaknesses", [(n, v, "") for n in names], "Weaknesses")
    return v


def _lowest_melee(strikes):
    melee = [s for s in strikes if not is_ranged(s) and s["damage"]]
    return min(melee, key=strike_avg) if melee else None


def _strongest_melee(strikes):
    melee = [s for s in strikes if not is_ranged(s) and s["damage"]]
    return max(melee, key=strike_avg) if melee else None


def _bite_strike(strikes):
    return next((s for s in strikes if any(w in s["name"].lower() for w in ("jaws", "fangs", "fang", "bite", "teeth", "maw", "beak", "tusk", "mandible"))), None)


# ---------------------------------------------------------------------------------------------- the templates
def t_undead(w, o):
    _core_undead(w, bool(o.get("mindless")))
    w.say("This is the plain undead adjustment. It adds no abilities of its own.")


def t_ghost(w, o):
    w.add_trait("ghost", "spirit", "undead")
    w.language("Necril")
    w.immune("death effects", "disease", "paralyzed", "poison", "precision", "unconscious")
    _weak(w, ["force", "ghost touch", "positive"])
    _to_fly(w)
    _physical_to_negative(w)
    w.darkvision()
    w.void_healing()
    w.ability("Ghostly Passage", 1, (), "The creature Flies and, during this movement, can pass through walls, creatures, "
              "and other material obstacles as though incorporeal. It must begin and end its movement outside any "
              "physical obstacle, and passing through solid material is difficult terrain.")
    w.say("Not truly incorporeal, and it doesn't necessarily return after being destroyed (the book's own note).")


def t_ghoul(w, o):
    w.add_trait("ghoul", "undead")
    w.immune("death effects", "disease", "paralyzed", "poison", "unconscious")
    saves = [k for k in ("fort", "ref", "will") if isinstance(w.st.get(k), int)]
    for k in saves:
        w.st[k] -= 1
    if saves:
        w.say("All saving throws -1")
    strikes = w.strikes()
    target = _bite_strike(strikes)
    if target is None:
        base = _strongest_melee(strikes)
        if base is not None:
            target = {"name": "Jaws", "bonus": base["bonus"], "damage": list(base["damage"][:1]), "traits": ["unarmed"],
                      "effects": []}
            strikes.append(target)
            w.say(f"Strike added: Jaws {target['bonus']} ({', '.join(target['damage'])}), copied from its strongest melee Strike")
        else:
            w.warn("No melee Strike was found, so Paralysis has nothing to attach to. Add a Strike and add Paralysis to its effects.")
    if target is not None:
        if "Paralysis" not in target["effects"]:
            target["effects"].append("Paralysis")
        w.say(f"Paralysis added to its {target['name'].lower()} Strike")
    if strikes:
        w.set_strikes(strikes)
    w.darkvision()
    w.void_healing()
    w.ability("Paralysis", "", ("occult", "necromancy"), "When the creature gets a critical hit with its jaws, fangs, or "
              "similar attack against a living, non-elf foe of the creature's level or lower, the foe is paralyzed until "
              "the end of the foe's next turn.")
    w.ability("Swift Leap", 1, ("move",), "The creature jumps up to half its Speed. This movement doesn't trigger reactions.")


def t_mummy(w, o):
    w.add_trait("mummy", "undead")
    w.language("Necril")
    w.immune("death effects", "disease", "paralyzed", "poison", "unconscious")
    _weak(w, ["fire"])
    w.darkvision()
    w.void_healing()
    w.ability("Lesser Despair", "", ("aura", "divine", "emotion", "enchantment", "fear", "mental"),
              "30 feet. Living creatures of the mummy's level or lower are frightened 1 while in the aura. They can't "
              "naturally recover from this fear while in the area, but recover instantly once they leave.")


def t_shadow(w, o):
    w.add_trait("undead")
    w.language("Necril")
    sk = w.skills()
    stealth = next((v for n, v in sk if n.lower() == "stealth"), None)
    best = max((v for n, v in sk), default=None)
    if best is None:
        lvl = max(-1, min(24, w.level0))
        best = SKILL[lvl][1]
        w.warn("It had no skills to copy from, so Stealth uses the High skill number for its level.")
    if stealth is None:
        w.add_list("skills", [f"Stealth {best:+d}"], "Skills")
    elif stealth < best:
        w.st["skills"] = re.sub(r"(Stealth\s+)[+-]\d+", lambda m: m.group(1) + f"{best:+d}", w.st["skills"], count=1, flags=re.I)
        w.say(f"Stealth raised to {best:+d}")
    w.immune("death effects", "disease", "paralyzed", "poison", "precision", "unconscious")
    _weak(w, ["force", "ghost touch", "positive"])
    _to_fly(w)
    _physical_to_negative(w)
    dc = _spell_dc(w)
    line = f"Divine Innate Spells DC {dc}; Rank 2: Darkness (x1)"
    w.st["spells"] = (w.st.get("spells", "").rstrip() + "\n" + line).strip()
    w.say("Innate divine spell added: darkness, once per day")
    w.darkvision()
    w.void_healing()
    w.ability("Slink in Shadows", "", (), "The creature can Hide or end its Sneak in a creature's or object's shadow.")


def _spell_dc(w):
    m = re.search(r"\bDC (\d+)", w.st.get("spells", "") or "")
    if m:
        return int(m.group(1))
    dc = SPELL[max(-1, min(24, w.level0))][2][0]
    w.warn(f"The book doesn't give a DC for the innate darkness spell, so it uses the moderate spell DC for level "
           f"{w.level0} ({dc}).")
    return dc


def t_skeleton(w, o):
    mindless = bool(o.get("mindless", True))
    w.add_trait("skeleton")
    _core_undead(w, mindless)
    hp, res = pick(w.level0, SKELETON)
    w.hp_add(hp)
    w.merge_iwr("resistances", [(n, res, "") for n in ("cold", "electricity", "fire", "piercing", "slashing")], "Resistances")
    w.darkvision()
    w.void_healing()


def t_zombie(w, o):
    w.add_trait("mindless", "undead", "zombie")
    w.immune("death effects", "disease", "mental", "paralyzed", "poison", "unconscious")
    hp, weak = pick(w.level0, ZOMBIE)
    w.hp_add(hp)
    w.merge_iwr("weaknesses", [("positive", weak, ""), ("slashing", weak, "")], "Weaknesses")
    w.darkvision()
    w.void_healing()
    w.ability("Slow", "", (), "A zombie is permanently slowed 1 and can't use reactions.")
    if split_commas(w.st.get("languages", "")):
        w.warn("A zombie is mindless and usually speaks no languages. Delete the ones it has if you want it to match.")
    reactions = [b[1].split(":")[0] for b in ability_blocks(w.st.get("abilities", "")) if b[2] == "[R]"]
    if reactions:
        w.warn("A zombie can't use reactions. These need to go or be replaced: " + "; ".join(reactions))
    if any(b[2] == "[3]" for b in ability_blocks(w.st.get("abilities", ""))):
        w.warn("The book warns that a creature with an important 3-action ability doesn't work well as a zombie, "
               "because it is permanently slowed.")


def t_vampire(w, o):
    kind = o.get("kind") or "Moroi (silver)"
    material = VAMPIRE_KINDS.get(kind, kind.lower())
    w.add_trait("undead", "vampire")
    w.language("Necril")
    hp, res = pick(w.level0, VAMPIRE)
    w.hp_add(hp)
    w.immune("death effects", "disease", "paralyzed", "poison", "sleep")
    w.merge_iwr("resistances", [("physical", res, f"except {material}")], "Resistances")
    strikes = w.strikes()
    bite = _bite_strike(strikes)
    if bite is None:
        low = _lowest_melee(strikes)
        if low is not None:
            bite = {"name": "Fangs", "bonus": low["bonus"], "damage": [re.sub(r"\b(bludgeoning|slashing)\b", "piercing", low["damage"][0])],
                    "traits": ["unarmed"], "effects": []}
            strikes.append(bite)
            w.set_strikes(strikes)
            w.say(f"Strike added: Fangs {bite['bonus']} ({bite['damage'][0]}), equal to its lowest melee Strike")
        else:
            w.warn("It has no melee Strike to copy, so no Fangs Strike was added. Add one that deals the damage of its lowest melee Strike.")
    use = bite["name"].lower() if bite else "jaws"
    w.darkvision()
    w.void_healing()
    w.ability("Feed", 1, ("divine", "necromancy"), f"Requirements The creature's most recent action was a successful {use} "
              f"Strike that dealt damage. Effect It drains blood from its victim, dealing minimum {use} damage and "
              f"regaining {res} HP.")
    w.say(f"Resistance to physical damage {res}, except {material} ({kind.split(' (')[0]}). Feed heals {res} HP.")


def t_wight(w, o):
    w.add_trait("undead", "wight")
    w.language("Necril")
    w.immune("death effects", "disease", "paralyzed", "poison", "unconscious")
    strikes = w.strikes()
    chosen = o.get("strikes")
    if chosen is None:
        chosen = default_drain_strikes(strikes)
    cut = max(0, w.level0) // 2
    done = []
    for s in strikes:
        if s["name"] in chosen and "Drain Life" not in s["effects"]:
            s["effects"].append("Drain Life")
            if s["damage"] and cut:
                s["damage"][0] = shift_dmg(s["damage"][0], -cut)
            done.append(s["name"])
    if strikes:
        w.set_strikes(strikes)
    if done:
        w.say(f"Drain Life added to: {', '.join(done)}" + (f"; each deals {cut} less damage (half its level)" if cut else ""))
    else:
        w.warn("No Strike has Drain Life yet. Add Drain Life to a Strike's effects, and lower that Strike's damage by half the creature's level.")
    dc = SPELL[max(-1, min(24, w.level0))][2][0]
    w.darkvision()
    w.void_healing()
    w.ability("Drain Life", "", ("divine", "necromancy"), f"When the creature damages a living creature with this Strike, it gains "
              f"temporary HP equal to its level, and the target must succeed at a DC {dc} Fortitude save or become drained 1.")
    w.say(f"Drain Life save uses the moderate DC for level {w.level0}: DC {dc}")


def default_drain_strikes(strikes):
    """Unarmed Strikes (claws, jaws, fists, slams). If it has none, its strongest melee Strike."""
    names = [s["name"] for s in strikes if not is_ranged(s) and is_unarmed(s)]
    if not names:
        top = _strongest_melee(strikes)
        names = [top["name"]] if top else []
    return names


SIZE_NAMES = {"tiny": "Tiny", "sm": "Small", "med": "Medium", "lg": "Large", "huge": "Huge", "grg": "Gargantuan"}


def t_werecreature(w, o):
    animal = (o.get("animal") or "Wolf").strip()
    senses = (o.get("senses") or "").strip()
    hp, silver = pick(w.level0, WERECREATURE)
    c = w.c
    c.level = w.level0 + 1
    w.say(f"Level {w.level0} to {c.level}")
    w.add_trait("beast", "werecreature")
    if o.get("bigger"):
        if c.size in SIZES and SIZES.index(c.size) < len(SIZES) - 1:
            c.size = SIZES[SIZES.index(c.size) + 1]
            w.say(f"Size now {SIZE_NAMES[c.size]}")
        else:
            w.warn("The size couldn't be raised automatically (it isn't one of tiny, small, medium, large, huge, gargantuan). Change it by hand.")
    w.bump(ac=1, attack=1, dc=1, saves=1, skills=1, damage=1)
    w.warn("The rules list AC, attack bonuses, DCs, saves, skills, and damage. Perception is not on that list, so it was left alone.")
    w.warn("Offensive abilities that deal damage also get +1, or +2 if they are limited-use (a breath weapon, for example). "
           "That isn't automatic, so check any that deal damage.")
    w.hp_add(hp)
    w.merge_iwr("weaknesses", [("silver", silver, "")], "Weaknesses")
    if senses:
        w.add_list("senses", split_commas(senses), "Senses")
    else:
        w.warn(f"A werecreature gains the senses of its animal. Add the {animal.lower()}'s senses in the Senses box.")
    w.ability("Animal Empathy", "", (), f"The werecreature can ask questions of, receive answers from, and use Diplomacy "
              f"with animals of its general kind, such as the {animal.lower()}.")
    strikes = w.strikes()
    melee = [s for s in strikes if not is_ranged(s) and s["damage"]]
    agile = [s for s in melee if is_agile(s)]
    heavy = [s for s in melee if not is_agile(s)]
    best = max([bonus_int(s) for s in strikes if bonus_int(s) is not None], default=None)
    lvl = max(-1, min(24, c.level))
    if best is None:
        best = ATTACK[lvl][2]
        w.warn(f"It had no Strike with an attack bonus, so the new Strikes use the moderate attack bonus for level {c.level} ({best:+d}).")
    if agile:
        claw = shorten(agile[0]["damage"][0], "slashing")
    elif heavy:
        claw = scale_dmg(max(heavy, key=strike_avg)["damage"][0], 0.75, "slashing")
    else:
        claw = shorten(DAMAGE[lvl][3], "slashing")
        w.warn(f"It had no melee Strike to base damage on, so Claw uses the low Strike damage for level {c.level} ({DAMAGE[lvl][3]}).")
    if heavy:
        jaws = shorten(max(heavy, key=strike_avg)["damage"][0], "piercing")
    elif agile:
        jaws = scale_dmg(agile[0]["damage"][0], 4 / 3, "piercing")
    else:
        jaws = shorten(DAMAGE[lvl][2], "piercing")
    have = {x["name"].lower(): x for x in strikes}
    if "claw" in have or "claws" in have:
        w.say("It already has a Claw Strike, so none was added")
    else:
        strikes.append({"name": "Claw", "bonus": f"{best:+d}", "damage": [claw], "traits": ["agile", "unarmed"], "effects": []})
        w.say(f"Strike added: Claw {best:+d} ({claw}, agile)")
    bite = _bite_strike(strikes)
    if bite is not None:
        if "Curse of the Werecreature" not in bite["effects"]:
            bite["effects"].append("Curse of the Werecreature")
        w.say(f"It already has a {bite['name']} Strike, so the curse was added to it")
    else:
        strikes.append({"name": "Jaws", "bonus": f"{best:+d}", "damage": [jaws], "traits": ["unarmed"],
                        "effects": ["Curse of the Werecreature"]})
        w.say(f"Strike added: Jaws {best:+d} ({jaws}) with the curse")
    w.set_strikes(strikes)
    w.ability("Curse of the Werecreature", "", ("curse",), "The creature's jaws can pass on its curse to a living humanoid. "
              "Use the curse's save and stages from the Werecreature family in Monster Core.")
    w.ability("Change Shape", 1, ("concentrate", "polymorph", "primal"), f"The werecreature changes into its humanoid, "
              f"hybrid, or {animal.lower()} shape. Each shape has one fixed appearance, and the hybrid shape is the true "
              f"werecreature's natural form. In humanoid shape it uses its original size, loses its jaws and claw Strikes, "
              f"and gains a fist Strike that deals bludgeoning damage equal to its claw's damage.")
    w.warn("Change Shape's action cost and the other two shapes' statistics aren't in the text this was built from. It is set to "
           "one action; the animal shape needs its own numbers from the book.")
    w.warn("This stat block is the hybrid form, as the rules say.")


def shorten(expr, new_type):
    p = parse_dmg(expr)
    if not p:
        return expr
    p["rest"] = new_type
    return fmt_dmg(p)


# ---------------------------------------------------------------------------------------------- the catalog
STRIKES_OPTION = {"key": "strikes", "label": "Strikes with Drain Life", "type": "strikes"}

BUILTIN = {
    "undead": dict(label="Undead (generic)", source="Book of the Dead p. 72", fn=t_undead,
                   summary="A reanimated corpse of no special kind. Adds the undead trait, the Necril language, and the "
                           "standard undead immunities.",
                   options=[{"key": "mindless", "label": "Mindless (adds mental immunity, no Necril)", "type": "check", "default": False}]),
    "ghost": dict(label="Ghost", source="Book of the Dead p. 72", fn=t_ghost,
                  summary="Flies only, physical Strikes become magical negative damage, weak to force, ghost touch, and positive "
                          "damage by level, and can pass through walls (Ghostly Passage).", options=[]),
    "ghoul": dict(label="Ghoul", source="Book of the Dead p. 72", fn=t_ghoul,
                  summary="Saves drop by 1, a jaws or similar Strike gains Paralysis, and it gains Swift Leap. The creature stays "
                          "the same level.", options=[]),
    "mummy": dict(label="Mummy", source="Book of the Dead p. 72", fn=t_mummy,
                  summary="Weak to fire by level, and living creatures near it are frightened 1 (Lesser Despair, 30 feet).",
                  options=[]),
    "shadow": dict(label="Shadow", source="Book of the Dead p. 72", fn=t_shadow,
                   summary="Flies only, physical Strikes become magical negative damage, weak to force, ghost touch, and positive "
                           "damage, gains Stealth, innate darkness, and Slink in Shadows.", options=[]),
    "skeleton": dict(label="Skeleton", source="Book of the Dead p. 73", fn=t_skeleton,
                     summary="Loses HP by level and resists cold, electricity, fire, piercing, and slashing. Usually mindless.",
                     options=[{"key": "mindless", "label": "Mindless (most skeletons are)", "type": "check", "default": True}]),
    "vampire": dict(label="Vampire", source="Book of the Dead p. 73", fn=t_vampire,
                    summary="Loses HP by level, resists physical damage except one material, gains a fangs Strike and Feed.",
                    options=[{"key": "kind", "label": "Weakness (what bypasses its resistance)", "type": "choice",
                              "choices": list(VAMPIRE_KINDS), "default": "Moroi (silver)"}]),
    "wight": dict(label="Wight", source="Book of the Dead p. 73", fn=t_wight,
                  summary="Chosen Strikes drain life (temporary HP for it, drained 1 for the target) but deal less damage.",
                  options=[STRIKES_OPTION]),
    "zombie": dict(label="Zombie", source="Book of the Dead p. 73", fn=t_zombie,
                   summary="Mindless, gains HP by level, weak to positive damage and slashing, permanently slowed 1, and can't "
                           "use reactions.", options=[]),
    "werecreature": dict(label="Werecreature (hybrid form)", source="Monster Core p. 344", fn=t_werecreature,
                         summary="One level higher with +1 to AC, attacks, DCs, saves, skills, and damage, more HP, weak to silver, "
                                 "and claw and jaws Strikes with the curse. This is the hybrid form.",
                         options=[{"key": "animal", "label": "Animal", "type": "choice", "choices": WERE_ANIMALS, "default": "Wolf",
                                   "free": True},
                                  {"key": "senses", "label": "Animal's senses (for example scent (imprecise) 30 feet)", "type": "text",
                                   "default": ""},
                                  {"key": "bigger", "label": "The animal is bigger than the humanoid (one size up)", "type": "check",
                                   "default": False}]),
}

# Fields a user-made template can have. All optional.
CUSTOM_FIELDS = [
    ("name", "Name"), ("summary", "What it does (one line)"), ("level", "Level change"), ("hp", "HP change"),
    ("ac", "AC bonus"), ("attack", "Attack bonus"), ("dc", "DC bonus"), ("saves", "Saves bonus"), ("skills", "Skills bonus"),
    ("damage", "Strike damage bonus"), ("traits", "Traits to add"), ("languages", "Languages to add"),
    ("senses", "Senses to add"), ("immunities", "Immunities to add"), ("weaknesses", "Weaknesses to add"),
    ("resistances", "Resistances to add"), ("speed", "Speeds to add"), ("strikes", "Strikes to add"),
    ("abilities", "Abilities to add"), ("spells", "Spells to add"), ("notes", "Notes"),
]


def blank_custom():
    spec = {k: "" for k, _ in CUSTOM_FIELDS}
    for k in ("level", "hp", "ac", "attack", "dc", "saves", "skills", "damage"):
        spec[k] = 0
    return spec


def _int(v):
    try:
        return int(str(v).strip().replace("+", "") or 0)
    except ValueError:
        return 0


def t_custom(w, spec):
    if _int(spec.get("level")):
        w.c.level += _int(spec["level"])
        w.say(f"Level {w.level0} to {w.c.level}")
    w.bump(ac=_int(spec.get("ac")), attack=_int(spec.get("attack")), dc=_int(spec.get("dc")), saves=_int(spec.get("saves")),
           skills=_int(spec.get("skills")), damage=_int(spec.get("damage")))
    if _int(spec.get("hp")):
        w.hp_add(_int(spec["hp"]))
    w.add_trait(*[t.strip().lower() for t in split_commas(spec.get("traits"))])
    for key, label in (("languages", "Languages"), ("senses", "Senses"), ("immunities", "Immunities")):
        w.add_list(key, split_commas(spec.get(key)), label)
    for key, label in (("weaknesses", "Weaknesses"), ("resistances", "Resistances")):
        if spec.get(key, "").strip():
            w.merge_iwr(key, parse_iwr(spec[key]), label)
    if spec.get("speed", "").strip():
        speeds = parse_speeds(w.st.get("speed", ""))
        for kind, val, rest in parse_speeds(spec["speed"]):
            speeds = [s for s in speeds if s[0] != kind] + [(kind, val, rest)]
        w.set_speeds(speeds)
        w.say("Speeds: " + w.st["speed"])
    for line in str(spec.get("strikes", "")).splitlines():
        for s in parse_strikes(line):
            if s["name"]:
                w.add_strike(s)
    for line in str(spec.get("abilities", "")).splitlines():
        m = ABIL_RE.match(line)
        if not m:
            if line.strip():
                w.warn(f"Skipped an ability line with no colon: {line.strip()[:50]}")
            continue
        glyph = (m.group(2) or "").strip("[]")
        w.ability(m.group(1).strip(), int(glyph) if glyph.isdigit() else glyph, split_commas(m.group(3)), m.group(4).strip())
    if spec.get("spells", "").strip():
        w.st["spells"] = (w.st.get("spells", "").rstrip() + "\n" + spec["spells"].strip()).strip()
        w.say("Spells added")
    if spec.get("notes", "").strip():
        w.say("Note: " + spec["notes"].strip())


def catalog(custom=()):
    """Every template the dialog can offer: built-in ones first, then the user's own."""
    out = [{"key": k, "label": v["label"], "source": v["source"], "summary": v["summary"], "options": v["options"],
            "builtin": True} for k, v in BUILTIN.items()]
    for spec in custom or ():
        out.append({"key": "my:" + spec["id"], "label": spec.get("name") or "My template", "source": "Your own template",
                    "summary": spec.get("summary") or "", "options": [], "builtin": False})
    return out


def applied(c):
    """The keys of the templates already on this creature, oldest first."""
    return [t.get("key") for t in (c.stats or {}).get("templates", []) if isinstance(t, dict)]


class Result:
    def __init__(self, creature, log, warns):
        self.creature, self.log, self.warns = creature, log, warns


def apply(creature, key, options=None, mode="remaster", name=None, custom=()):
    """A copy of the creature with the template applied. Returns a Result (creature, log, warns). Raises TemplateError."""
    options = dict(options or {})
    spec = None
    if str(key).startswith("my:"):
        spec = next((s for s in custom or () if "my:" + s["id"] == key), None)
        if spec is None:
            raise TemplateError("That template of yours no longer exists.")
        label, source, fn = spec.get("name") or "My template", "your own template", None
    elif key in BUILTIN:
        b = BUILTIN[key]
        label, source, fn = b["label"], b["source"], b["fn"]
    else:
        raise TemplateError(f"There is no template called {key}.")
    if key in applied(creature):
        raise TemplateError(f"{creature.name} already has the {label} template.")
    w = Work(creature, mode)
    first = not applied(creature)
    if spec is not None:
        t_custom(w, spec)
    else:
        fn(w, options)
    c = w.result()
    short = label.split(" (")[0]
    if key == "werecreature" and (options.get("animal") or "").strip():
        short = "Were" + options["animal"].strip().lower()            # Werewolf, Wererat, Werebear...
    shown = [t.get("label") for t in (creature.stats or {}).get("templates", []) if isinstance(t, dict)] + [short]
    root = ((creature.stats or {}).get("template_base") or {}).get("name") or creature.name
    c.name = (name or "").strip() or f"{root} ({', '.join(shown)})"
    rec = {"key": key, "label": short, "source": source, "options": {k: v for k, v in options.items() if v not in (None, "")},
           "from": creature.name, "from_level": int(creature.level)}
    c.stats["templates"] = list(c.stats.get("templates", [])) + [rec]
    if first:
        c.stats["template_base"] = {"name": creature.name, "level": int(creature.level)}
    with_note(c)
    return Result(c, w.log, w.warns)


def note_text(c):
    """One line for the creature's notes saying which templates it carries."""
    recs = [t for t in (c.stats or {}).get("templates", []) if isinstance(t, dict)]
    if not recs:
        return ""
    base = (c.stats or {}).get("template_base") or {}
    names = ", ".join(f"{t['label']} ({t['source']})" for t in recs)
    return f"Templates: {names}" + (f", applied to {base['name']} (level {base['level']})." if base.get("name") else ".")


def strip_note(notes):
    """Remove the template line from notes (so it can be put back fresh)."""
    return "\n".join(ln for ln in str(notes or "").splitlines() if not ln.startswith("Templates: ")).strip()


def with_note(c):
    """Set the creature's notes so exactly one up-to-date template line is on the end. Returns the creature."""
    line = note_text(c)
    base = strip_note(c.notes)
    c.notes = (base + ("\n\n" if base and line else "") + line).strip()
    return c


def apply_chain(base, steps, mode="remaster", name=None, custom=()):
    """Apply a list of (key, options) in order to a base creature (used to redo templates after the base changes)."""
    cur, logs, warns = base, [], []
    for key, opts in steps:
        r = apply(cur, key, opts, mode, custom=custom)
        cur = r.creature
        logs += r.log
        warns += r.warns
    if name and cur is not base:
        cur.name = name
    return Result(cur, logs, warns)


def strike_names(c):
    return [s["name"] for s in parse_strikes((c.stats or {}).get("strikes", ""))]

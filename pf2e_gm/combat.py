"""Combat tracker state: initiative, HP, conditions, turn automation."""
import random
from dataclasses import dataclass, field, asdict

VALUED = ["clumsy", "doomed", "drained", "dying", "enfeebled", "frightened", "sickened", "slowed",
          "stunned", "stupefied", "wounded"]
UNVALUED = ["blinded", "concealed", "confused", "controlled", "dazzled", "deafened", "encumbered",
            "fascinated", "fatigued", "fleeing", "grabbed", "hidden", "immobilized", "invisible",
            "off-guard", "paralyzed", "petrified", "prone", "quickened", "restrained", "unconscious",
            "undetected"]
PERSISTENT = "persistent damage"
ALL_CONDITIONS = sorted(VALUED + UNVALUED) + [PERSISTENT]

OFF_GUARD_FROM = {"off-guard", "grabbed", "prone", "restrained", "paralyzed", "unconscious"}
AC_STATUS = ("frightened", "sickened", "clumsy")   # status penalties (do not stack; highest applies)
DEGREES = ["Critical failure", "Failure", "Success", "Critical success"]
HIT = {3: "CRITICAL HIT", 2: "HIT", 1: "MISS", 0: "MISS (crit fail)"}
# condition -> which checks its status penalty applies to
CHECK_STATUS = {"frightened": "all", "sickened": "all", "clumsy": ("reflex", "dex"),
                "enfeebled": ("str",), "drained": ("fortitude", "con"), "stupefied": ("will", "int", "wis", "cha")}


def degree(total, dc, nat=None):
    """PF2e degree of success: 3 crit success, 2 success, 1 failure, 0 crit failure.
    Beat DC by 10+ -> crit; miss by 10+ -> crit fail; nat 20 / nat 1 shift one step."""
    if total >= dc + 10:
        d = 3
    elif total >= dc:
        d = 2
    elif total <= dc - 10:
        d = 0
    else:
        d = 1
    if nat == 20:
        d = min(3, d + 1)
    elif nat == 1:
        d = max(0, d - 1)
    return d


BASIC_SAVE = {3: "no damage", 2: "half damage", 1: "full damage", 0: "double damage"}

# ---------- condition modifiers ----------
# Which attribute each skill uses (Lores use Int).
SKILL_ATTR = {"acrobatics": "dex", "arcana": "int", "athletics": "str", "crafting": "int", "deception": "cha",
              "diplomacy": "cha", "intimidation": "cha", "medicine": "wis", "nature": "wis", "occultism": "int",
              "performance": "cha", "religion": "wis", "society": "int", "stealth": "dex", "survival": "wis",
              "thievery": "dex"}
# Unvalued conditions that still impose a fixed status penalty.
FIXED_STATUS = {"fatigued": 1, "unconscious": 4}


def _skill_attr(stat):
    s = str(stat or "").lower()
    return "int" if s.startswith("lore") else SKILL_ATTR.get(s, "")


def _status_applies(cond, kind, stat="", ranged=False, finesse=False):
    """Does this condition's status penalty apply to this roll or DC?

    kind: attack | spell_attack | damage | save | perception | skill | ac | dc | spell_dc
    stat: save name (fortitude/reflex/will) or skill name.
    """
    attr = _skill_attr(stat) if kind == "skill" else ""
    if cond in ("frightened", "sickened"):            # all checks and DCs
        return kind != "damage"
    if cond == "clumsy":                               # Dex-based checks and DCs
        return kind == "ac" or (kind == "save" and stat == "reflex") or (kind == "attack" and ranged) \
            or attr == "dex"
    if cond == "enfeebled":                            # Str-based checks, DCs, and damage
        return (kind == "attack" and not ranged and not finesse) or (kind == "damage" and not ranged) \
            or attr == "str"
    if cond == "drained":                              # Con-based checks
        return kind == "save" and stat == "fortitude"
    if cond == "stupefied":                            # Int/Wis/Cha checks and DCs, spells
        return kind in ("spell_attack", "spell_dc", "perception") or (kind == "save" and stat == "will") \
            or attr in ("int", "wis", "cha")
    if cond == "fatigued":
        return kind in ("ac", "save")
    if cond == "unconscious":
        return kind in ("ac", "perception") or (kind == "save" and stat == "reflex")
    return False


# What a bonus/penalty entry can apply to -> roll kinds it affects.
BONUS_TARGETS = {
    "AC": {"ac"},
    "Attack rolls": {"attack", "spell_attack"},
    "Damage": {"damage"},
    "All saves": {"save"},
    "Fortitude": {"save:fortitude"},
    "Reflex": {"save:reflex"},
    "Will": {"save:will"},
    "Perception": {"perception"},
    "Skills": {"skill"},
    "All checks and DCs": {"attack", "spell_attack", "save", "perception", "skill", "dc", "spell_dc"},
}
BONUS_TYPES = ["circumstance", "status", "item", "untyped"]
BONUS_PRESETS = {
    "Cover (+2 circumstance to AC)": dict(label="Cover", type="circumstance", value=2, applies="AC", rounds=0),
    "Greater cover (+4 circumstance to AC)": dict(label="Greater cover", type="circumstance", value=4,
                                                  applies="AC", rounds=0),
    "Lesser cover (+1 circumstance to AC)": dict(label="Lesser cover", type="circumstance", value=1,
                                                 applies="AC", rounds=0),
    "Raise a Shield (+2 circumstance to AC)": dict(label="Raised shield", type="circumstance", value=2,
                                                   applies="AC", rounds=1, self_source=True),
    "Courageous Anthem: attack (+1 status)": dict(label="Courageous Anthem", type="status", value=1,
                                                  applies="Attack rolls", rounds=1),
    "Courageous Anthem: damage (+1 status)": dict(label="Courageous Anthem", type="status", value=1,
                                                  applies="Damage", rounds=1),
    "Bless (+1 status to attack rolls)": dict(label="Bless", type="status", value=1, applies="Attack rolls",
                                              rounds=10),
    "Aid succeeded (+1 circumstance)": dict(label="Aid", type="circumstance", value=1, applies="Attack rolls",
                                            rounds=1),
    "Rage (+2 circumstance to damage, melee only)": dict(label="Rage", type="circumstance", value=2, applies="Damage",
                                                         rounds=0),
    "Rage (-1 circumstance to AC)": dict(label="Rage", type="circumstance", value=-1, applies="AC", rounds=0),
    "Flanking target: off-guard": dict(condition="off-guard"),
    "Heroism 1 (+1 status to attack, saves, Perception, skills)": dict(label="Heroism", type="status", value=1,
                                                                       applies="All checks and DCs", rounds=100),
}


def _bonus_applies(b, kind, stat):
    targets = BONUS_TARGETS.get(b.get("applies"), set())
    return kind in targets or (kind == "save" and f"save:{stat}" in targets)


def condition_mods(conditions, kind, stat="", ranged=False, finesse=False, bonuses=None):
    """Modifiers from conditions and bonus/penalty effects for one roll or DC, as [(label, value)].

    Stacking (PF2e): within each type (circumstance, status, item) only the highest bonus and the worst
    penalty apply; the rest are named as overridden. Untyped modifiers all stack.
    """
    conds = conditions or {}
    entries = []
    for cond, v in conds.items():
        val = v if isinstance(v, int) and not isinstance(v, bool) else FIXED_STATUS.get(cond)
        if val and _status_applies(cond, kind, stat, ranged, finesse):
            entries.append(("status", -val, cond, f"{cond}{f' {v}' if isinstance(v, int) else ''}"))
    if kind in ("attack", "spell_attack") and "prone" in conds:
        entries.append(("circumstance", -2, "prone", "prone"))
    if kind == "ac":
        src = sorted(OFF_GUARD_FROM & set(conds))
        if src:
            why = "off-guard" if "off-guard" in src else f"off-guard from {src[0]}"
            entries.append(("circumstance", -2, "off-guard", why))
    for b in bonuses or []:
        if _bonus_applies(b, kind, stat):
            v = int(b.get("value") or 0)
            if v:
                entries.append((b.get("type") or "untyped", v, b.get("label") or "bonus", b.get("label") or "bonus"))
    out = []
    order = ["status", "circumstance", "item"]
    for typ in order:
        for sign in (-1, 1):
            grp = [e for e in entries if e[0] == typ and (e[1] < 0) == (sign < 0)]
            if not grp:
                continue
            grp.sort(key=lambda e: (e[1] if sign < 0 else -e[1], e[2]))
            best = grp[0]
            others = ", ".join(e[2] for e in grp[1:])
            out.append((f"{best[3]} ({typ}{'; overrides ' + others if others else ''})", best[1]))
    for e in entries:
        if e[0] not in order:
            out.append((f"{e[3]} (untyped)", e[1]))
    return out


def mods_total(mods):
    return sum(v for _, v in mods)


# ---------- immunities, weaknesses, resistances ----------
PHYSICAL = {"bludgeoning", "piercing", "slashing"}
ENERGY = {"acid", "cold", "electricity", "fire", "sonic", "force", "vitality", "void"}


def _slug(s):
    return str(s or "").strip().lower().replace(" ", "-")


def parse_iwr(d):
    """Structured IWR from a stat block dict (pairs like ('Physical 5 (except Silver)', 'name:physical'))."""
    import re as _re

    def entries(key):
        for p in (d or {}).get(key) or []:
            text = p[0] if isinstance(p, (list, tuple)) else str(p)
            ref = p[1] if isinstance(p, (list, tuple)) and len(p) > 1 else None
            slug = ref.split(":", 1)[1] if ref and ":" in ref else _re.sub(r"\s*\(.*\)|\s*\d+$", "", text)
            exc = _re.search(r"\(except ([^)]*)\)", text)
            num = _re.search(r"\b(\d+)\b", _re.sub(r"\(.*\)", "", text))
            yield _slug(_re.sub(r"\s+\d+$", "", slug)), int(num.group(1)) if num else 0, (exc.group(1) if exc else "")
    out = {"immune": [s for s, _, _ in entries("immunities")],
           "weak": {s: n for s, n, _ in entries("weaknesses")},
           "resist": {s: [n, e] for s, n, e in entries("resistances")}}
    return out if (out["immune"] or out["weak"] or out["resist"]) else {}


def _matches(slug, dtypes):
    slug = _slug(slug)
    if slug in dtypes:
        return True
    if slug == "physical" and dtypes & PHYSICAL:
        return True
    if slug == "energy" and dtypes & ENERGY:
        return True
    return slug in ("all-damage", "all") and bool(dtypes)


def apply_iwr(parts, iwr, hardness=None):
    """Apply immunities, then weaknesses, then resistances (GM Core order), then Hardness.

    parts: [(amount, damage type text)]. Returns (total, [explanation lines]).

    Precision damage (sneak attack and similar) has the same damage type as the attack it augments, so it is
    added to that type's total before weakness and resistance are applied once. A creature immune to precision
    damage ignores just that part. Parts of the same type (for example a weapon and a rune) are likewise summed
    before resistance, as GM Core does.
    """
    iwr = iwr or {}
    lines, groups, order = [], {}, []
    for amount, dtype in parts:
        words = {w for w in _slug(dtype).replace("-", " ").split() if w and w not in ("persistent", "splash")} \
            or {"untyped"}
        precision = "precision" in words
        label = dtype or "untyped"
        imm = [s for s in iwr.get("immune", []) if _matches(s, words)]
        if imm:
            lines.append(f"{amount} {label}: immune ({imm[0].replace('-', ' ')}) -> 0")
            continue
        base = frozenset(words - {"precision"}) or frozenset({"untyped"})
        g = groups.get(base)
        if g is None:
            g = groups[base] = {"amount": 0, "precision": 0, "labels": [], "base": " ".join(sorted(base))}
            order.append(base)
        g["amount"] += amount
        g["labels"].append(label)
        if precision:
            g["precision"] += amount
    total = 0
    for base in order:
        g = groups[base]
        n, amount = g["amount"], g["amount"]
        label = g["labels"][0] if len(g["labels"]) == 1 else g["base"]
        if g["precision"] and len(g["labels"]) > 1:
            label += f" (incl. {g['precision']} precision)"
        weak = [(v, s) for s, v in (iwr.get("weak") or {}).items() if v and _matches(s, set(base))]
        if weak and n > 0:
            v, s = max(weak)
            n += v
            lines.append(f"{amount} {label}: weakness {s.replace('-', ' ')} {v} -> {n}")
        res = [(v[0], s, v[1]) for s, v in (iwr.get("resist") or {}).items()
               if v and v[0] and _matches(s, set(base))]
        if res and n > 0:
            v, s, exc = max(res)
            before, n = n, max(0, n - v)
            lines.append(f"{before} {label}: resistance {s.replace('-', ' ')} {v} -> {n}"
                         + (f"  (doesn't apply if the damage is {exc.lower()})" if exc else ""))
        if not weak and not res:
            lines.append(f"{amount} {label}")
        total += n
    if hardness and total > 0:
        before, total = total, max(0, total - int(hardness))
        lines.append(f"Hardness {hardness}: {before} -> {total}")
    return total, lines


# ---------- damage riders (sneak attack and similar extra damage) ----------
RIDER_APPLIES = {
    "Any Strike": "any",
    "Melee Strikes": "melee",
    "Ranged Strikes": "ranged",
    "Agile, finesse, or ranged (sneak attack)": "sneak",
}


def sneak_attack_dice(level):
    """Rogue sneak attack: 1d6, +1 die at levels 5, 11, and 17."""
    lvl = int(level or 1)
    return 1 + (lvl >= 5) + (lvl >= 11) + (lvl >= 17)


def rider_applies(rider, traits=(), ranged=False):
    """Does this rider add damage to a Strike with these traits?"""
    t = {str(x).lower() for x in traits}
    rule = rider.get("applies", "any")
    if rule == "melee":
        return not ranged
    if rule == "ranged":
        return ranged
    if rule == "sneak":
        return ranged or "agile" in t or "finesse" in t
    return True


def rider_text(rider, weapon_type=""):
    """Damage text for a rider. Precision damage takes the weapon's own type ('2d6 piercing precision')."""
    dice = str(rider.get("dice") or "").strip()
    if not dice:
        return ""
    if rider.get("precision", True):
        return f"{dice} {weapon_type} precision".replace("  ", " ").strip()
    return f"{dice} {rider.get('dtype', '')}".strip()


@dataclass
class Combatant:
    id: int
    name: str
    kind: str = "creature"            # "creature" or "pc"
    init: int | None = None
    perception: int | None = None
    hp: int | None = None
    max_hp: int | None = None
    ac: int | None = None
    conditions: dict = field(default_factory=dict)   # name -> int value, None, or str (persistent)
    notes: str = ""
    uid: str = ""                     # creature uid for stat block lookup (base, unadjusted)
    adjust: str = ""
    defeated: bool = False
    effects: list = field(default_factory=list)      # [{"name", "rounds", "source": id or None, "note"}]
    saves: dict = field(default_factory=dict)        # {"fortitude": 11, ...} for save rolls against effects
    pc_key: str = ""                                 # party member name for PC stat blocks
    bonuses: list = field(default_factory=list)      # [{"label","type","value","applies","rounds","source"}]
    iwr: dict = field(default_factory=dict)          # {"immune": [...], "weak": {t: n}, "resist": {t: [n, except]}}
    hardness: int | None = None
    riders: list = field(default_factory=list)       # [{"label","dice","precision","dtype","applies","active"}]

    def active_riders(self):
        return [r for r in self.riders if r.get("active")]

    def mods(self, kind, stat="", ranged=False, finesse=False):
        return condition_mods(self.conditions, kind, stat, ranged, finesse, self.bonuses)

    def check_penalty(self, kind):
        """Total penalty (positive number) from conditions to a save. kind: 'fortitude'|'reflex'|'will'."""
        return -mods_total(self.mods("save", kind))

    def effective_ac(self):
        """AC after condition penalties, or None. Returns (value, reasons)."""
        if self.ac is None:
            return None, []
        m = self.mods("ac")
        return self.ac + mods_total(m), [f"{label} {v:+d}" for label, v in m]

    def condition_text(self):
        parts = []
        for k in sorted(self.conditions):
            v = self.conditions[k]
            if k.startswith("persistent"):
                parts.append(f"persistent {v}")
            elif isinstance(v, int):
                parts.append(f"{k} {v}")
            else:
                parts.append(k)
        return ", ".join(parts)


@dataclass
class CombatState:
    combatants: list = field(default_factory=list)
    round: int = 0
    turn: int = 0                     # index into combatants
    log: list = field(default_factory=list)
    next_id: int = 1
    auto_persistent: bool = True                      # roll and apply persistent damage automatically
    assisted: set = field(default_factory=set)        # persistent keys with Assisted Recovery this turn (DC 10)

    # ----- roster -----
    def add(self, name, **kw):
        names = [c.name for c in self.combatants]
        if name in names:              # Ghoul -> Ghoul 2, Ghoul 3...
            n = 2
            while f"{name} {n}" in names:
                n += 1
            name = f"{name} {n}"
        c = Combatant(id=self.next_id, name=name, **kw)
        if c.max_hp is None:
            c.max_hp = c.hp
        self.next_id += 1
        self.combatants.append(c)
        return c

    def get(self, cid):
        return next((c for c in self.combatants if c.id == cid), None)

    def remove(self, cid):
        cur = self.current()
        self.combatants = [c for c in self.combatants if c.id != cid]
        if cur and cur.id != cid and cur in self.combatants:
            self.turn = self.combatants.index(cur)
        else:
            self.turn = min(self.turn, max(0, len(self.combatants) - 1))

    def clear(self):
        auto = self.auto_persistent
        self.__init__()
        self.auto_persistent = auto

    # ----- initiative -----
    def roll_initiative(self, rng=None, only_missing=True, creatures_only=False):
        rng = rng or random.Random()
        for c in self.combatants:
            if only_missing and c.init is not None:
                continue
            if creatures_only and c.kind == "pc":
                continue
            if c.perception is None:
                continue
            roll = rng.randint(1, 20)
            m = c.mods("perception")
            c.init = roll + c.perception + mods_total(m)
            extra = "".join(f" {v:+d} {label}" for label, v in m)
            self._log(f"{c.name} rolls initiative: d20 ({roll}) {c.perception:+d} Perception{extra} = {c.init}")
        self.sort()

    def sort(self):
        cur = self.current() if self.round else None
        # Higher first; on ties, creatures act before PCs (GM Core), then higher Perception.
        self.combatants.sort(key=lambda c: (-(c.init if c.init is not None else -999),
                                            0 if c.kind == "creature" else 1,
                                            -(c.perception or 0)))
        if cur:
            self.turn = self.combatants.index(cur)

    def start(self):
        self.sort()
        self.round, self.turn = 1, 0
        self._skip_defeated()
        self._log(f"--- Round 1 ---")
        return self._start_of_turn()

    # ----- turns -----
    def current(self):
        if not self.combatants or not self.round:
            return None
        return self.combatants[self.turn % len(self.combatants)]

    def _skip_defeated(self):
        for _ in range(len(self.combatants)):
            if not self.combatants[self.turn].defeated:
                return
            self._advance_index()

    def _advance_index(self):
        self.turn += 1
        if self.turn >= len(self.combatants):
            self.turn = 0
            self.round += 1
            self._log(f"--- Round {self.round} ---")

    def next_turn(self, rng=None):
        """End the current turn, advance, start the next. Returns messages."""
        if not self.combatants:
            return []
        if not self.round:
            return self.start()
        msgs = self._end_of_turn(self.current(), rng)
        self._advance_index()
        self._skip_defeated()
        return msgs + self._start_of_turn()

    def _end_of_turn(self, c, rng=None):
        from .dice import roll_math, split_damage
        rng = rng or random.Random()
        msgs = []
        for k, v in list(c.conditions.items()):
            if not k.startswith("persistent"):
                continue
            parts = split_damage(str(v))
            if parts and self.auto_persistent:
                rolled = [(roll_math(e, rng).total, t.replace("persistent", "").strip()) for e, t in parts]
                raw = sum(a for a, _ in rolled)
                total, why = apply_iwr(rolled, c.iwr, c.hardness)
                msgs.append(f"{c.name}: persistent {v} deals {raw}" + (f" -> {total} ({'; '.join(why)})"
                                                                         if total != raw else ""))
                for m in self.damage(c.id, total, log=False):
                    msgs.append(m)
            else:
                msgs.append(f"{c.name}: take {v} persistent damage")
            flat = rng.randint(1, 20)
            dc = 15 - (5 if k in self.assisted else 0)
            if flat >= dc:
                del c.conditions[k]
                msgs.append(f"{c.name}: flat check {flat} vs DC {dc}: persistent {v} ends")
            else:
                msgs.append(f"{c.name}: flat check {flat} vs DC {dc}: persistent {v} continues")
            self.assisted.discard(k)
        f = c.conditions.get("frightened")
        if isinstance(f, int):
            if f <= 1:
                del c.conditions["frightened"]
                msgs.append(f"{c.name}: frightened ends")
            else:
                c.conditions["frightened"] = f - 1
                msgs.append(f"{c.name}: frightened {f} -> {f - 1}")
        msgs += self._tick_effects(c, "end")
        for m in msgs:
            self._log(m)
        return msgs

    # ----- timed effects -----
    def add_effect(self, cid, name, rounds, source=None, note="", condition=None):
        """Timed effect. Counts down at the start of the source's turn (spell/ability durations in PF2e
        are measured from the caster's turn), or at the end of the bearer's turn if no source is given."""
        c = self.get(cid)
        if not c:
            return
        c.effects.append({"name": name, "rounds": max(1, int(rounds)), "source": source, "note": note,
                          "condition": condition})
        src = self.get(source) if source else None
        self._log(f"{c.name}: {name} for {rounds} round{'s' if int(rounds) != 1 else ''}"
                  + (f" (from {src.name})" if src else ""))

    def add_bonus(self, cid, label, btype, value, applies, rounds=0, source=None):
        c = self.get(cid)
        if not c:
            return
        c.bonuses.append({"label": label, "type": btype, "value": int(value), "applies": applies,
                          "rounds": int(rounds or 0), "source": source})
        self._log(f"{c.name}: {int(value):+d} {btype} to {applies} ({label})"
                  + (f" for {rounds} round{'s' if int(rounds) != 1 else ''}" if rounds else ""))

    def remove_bonus(self, cid, index):
        c = self.get(cid)
        if c and 0 <= index < len(c.bonuses):
            b = c.bonuses.pop(index)
            self._log(f"{c.name}: {b['label']} removed")

    def remove_effect(self, cid, index):
        c = self.get(cid)
        if c and 0 <= index < len(c.effects):
            e = c.effects.pop(index)
            self._log(f"{c.name}: {e['name']} removed")

    def _tick_effects(self, actor, when):
        """when='start': tick effects whose source is actor. when='end': tick sourceless effects on actor."""
        msgs = []
        for c in self.combatants:
            keep = []
            for e in c.effects:
                tick = (when == "start" and e.get("source") == actor.id) or \
                       (when == "end" and c.id == actor.id and not e.get("source"))
                if tick:
                    e["rounds"] -= 1
                    if e["rounds"] <= 0:
                        msgs.append(f"{c.name}: {e['name']} ends" + (f" ({e['note']})" if e.get("note") else ""))
                        if e.get("condition") and e["condition"] in c.conditions:
                            del c.conditions[e["condition"]]
                            msgs.append(f"{c.name}: {e['condition']} removed")
                        continue
                    msgs.append(f"{c.name}: {e['name']}, {e['rounds']} round{'s' if e['rounds'] != 1 else ''} left")
                keep.append(e)
            c.effects = keep
            keepb = []
            for b in c.bonuses:
                tick = b.get("rounds") and ((when == "start" and b.get("source") == actor.id) or
                                            (when == "end" and c.id == actor.id and not b.get("source")))
                if tick:
                    b["rounds"] -= 1
                    if b["rounds"] <= 0:
                        msgs.append(f"{c.name}: {b['label']} ({b['value']:+d} {b['type']} to {b['applies']}) ends")
                        continue
                keepb.append(b)
            c.bonuses = keepb
        return msgs

    def _start_of_turn(self):
        c = self.current()
        if not c:
            return []
        msgs = [f"{c.name}'s turn (round {self.round})"]
        msgs += self._tick_effects(c, "start")
        st = c.conditions.get("stunned")
        if isinstance(st, int):
            lost = min(3, st)
            if st - lost <= 0:
                del c.conditions["stunned"]
            else:
                c.conditions["stunned"] = st - lost
            msgs.append(f"{c.name}: stunned {st}, loses {lost} action(s); stunned now {max(0, st - lost) or 'gone'}")
        sl = c.conditions.get("slowed")
        if isinstance(sl, int):
            msgs.append(f"{c.name}: slowed {sl}, loses {sl} action(s) this turn")
        if "quickened" in c.conditions:
            msgs.append(f"{c.name}: quickened, gains 1 extra action (check the source's restriction)")
        dy = c.conditions.get("dying")
        if isinstance(dy, int):
            msgs.append(f"{c.name}: dying {dy}, recovery check DC {10 + dy}")
        for m in msgs:
            self._log(m)
        return msgs

    # ----- HP -----
    def damage(self, cid, amount, log=True):
        c = self.get(cid)
        if not c or c.hp is None:
            return []
        c.hp = max(0, c.hp - amount)
        msgs = [f"{c.name} takes {amount} damage ({c.hp}/{c.max_hp})"]
        if c.hp == 0:
            if c.kind == "pc":
                wounded = c.conditions.get("wounded", 0) if isinstance(c.conditions.get("wounded"), int) else 0
                c.conditions["dying"] = 1 + wounded
                c.conditions["unconscious"] = None
                msgs.append(f"{c.name} is dying {1 + wounded} (add 1 more if the damage was a critical hit)")
            else:
                c.defeated = True
                msgs.append(f"{c.name} is defeated")
        if log:
            for m in msgs:
                self._log(m)
        return msgs

    # ----- attacks and saves against targets -----
    def attack(self, target_id, total, nat, label=""):
        """Resolve an attack roll against a target's effective AC. Returns (degree, message)."""
        t = self.get(target_id)
        if not t or t.ac is None:
            return None, ""
        ac, why = t.effective_ac()
        d = degree(total, ac, nat)
        msg = f"  vs {t.name} AC {ac}" + (f" (base {t.ac}; {', '.join(why)})" if why else "") + f": {HIT[d]}"
        self._log((label + msg) if label else msg.strip())
        return d, msg

    def save_vs(self, target_id, save, dc, rng=None, basic=False):
        """Roll a target's save against a DC. Returns (degree, message) or (None, reason)."""
        rng = rng or random.Random()
        t = self.get(target_id)
        if not t:
            return None, ""
        mod = (t.saves or {}).get(save)
        if mod is None:
            return None, f"{t.name}: no {save.title()} save on record"
        m = t.mods("save", save)
        nat = rng.randint(1, 20)
        total = nat + mod + mods_total(m)
        d = degree(total, dc, nat)
        res = DEGREES[d] + (f" ({BASIC_SAVE[d]})" if basic else "")
        extra = "".join(f" {v:+d} {label}" for label, v in m)
        msg = (f"{t.name}: {save.title()} save: d20 ({nat}) {mod:+d} {save.title()}{extra}"
               + f" = {total} vs DC {dc}: {res}")
        self._log(msg)
        return d, msg

    def apply_damage(self, cid, parts, crit=False, persistent=()):
        """Typed damage: parts [(amount, type)] after IWR and Hardness, plus persistent damage conditions."""
        c = self.get(cid)
        if not c:
            return []
        lines = []
        if crit and "critical-hits" in (c.iwr or {}).get("immune", []):
            lines.append(f"{c.name} is immune to critical hits: use normal damage")
        total, why = apply_iwr(parts, c.iwr, c.hardness)
        raw = sum(a for a, _ in parts)
        lines.append(f"{c.name}: {raw} damage" + (f" -> {total} after defenses" if total != raw else ""))
        lines += ["  " + w for w in why]
        for m in lines:
            self._log(m)
        if c.hp is not None:
            lines += self.damage(cid, total)
        for expr, dtype in persistent:
            words = {w for w in _slug(dtype).replace("-", " ").split()}
            if any(_matches(s, words) for s in (c.iwr or {}).get("immune", [])):
                msg = f"{c.name}: immune to persistent {dtype}"
            else:
                self.set_condition(cid, PERSISTENT, f"{expr} {dtype}".strip())
                msg = f"{c.name}: gains persistent {expr} {dtype} (dealt at end of its turn)"
            self._log(msg)
            lines.append(msg)
        return lines

    def heal(self, cid, amount):
        c = self.get(cid)
        if not c or c.hp is None:
            return []
        was_zero = c.hp == 0
        c.hp = min(c.max_hp or c.hp + amount, c.hp + amount)
        msgs = [f"{c.name} heals {amount} ({c.hp}/{c.max_hp})"]
        if was_zero and c.hp > 0:
            c.defeated = False
            if "dying" in c.conditions:
                w = c.conditions.get("wounded")
                c.conditions["wounded"] = (w if isinstance(w, int) else 0) + 1
                del c.conditions["dying"]
                msgs.append(f"{c.name} is no longer dying; wounded {c.conditions['wounded']}")
        for m in msgs:
            self._log(m)
        return msgs

    # ----- conditions -----
    def set_condition(self, cid, name, value=None):
        c = self.get(cid)
        if not c:
            return
        if name == PERSISTENT:
            text = str(value or "").strip() or "?"
            c.conditions[f"persistent {text}"] = text
            self._log(f"{c.name}: persistent {text}")
            return
        if name in VALUED:
            try:
                value = max(1, int(value))
            except (TypeError, ValueError):
                value = 1
            c.conditions[name] = value
            self._log(f"{c.name}: {name} {value}")
        else:
            c.conditions[name] = None
            self._log(f"{c.name}: {name}")

    def remove_condition(self, cid, name):
        c = self.get(cid)
        if c and name in c.conditions:
            del c.conditions[name]
            self._log(f"{c.name}: {name} removed")

    # ----- persistence -----
    def _log(self, msg):
        self.log.append(msg)
        self.log = self.log[-300:]

    def to_dict(self):
        return {"combatants": [asdict(c) for c in self.combatants], "round": self.round,
                "turn": self.turn, "log": self.log, "next_id": self.next_id,
                "auto_persistent": self.auto_persistent}

    @classmethod
    def from_dict(cls, d):
        if not d:
            return cls()
        s = cls(round=d.get("round", 0), turn=d.get("turn", 0), log=d.get("log", []),
                next_id=d.get("next_id", 1), auto_persistent=d.get("auto_persistent", True))
        s.combatants = [Combatant(**c) for c in d.get("combatants", [])]
        return s

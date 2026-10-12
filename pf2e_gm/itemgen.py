"""Magic Item Generator: invents items from components, writes their history, and checks custom items.

An item is a plain dict (so it saves as JSON). It is built from PARTS, each of which can be locked, edited, or rerolled:
the form (what it is), its abilities, a look, an optional quirk or drawback, and, for runic weapons and armor, the runes.
Its history is a Story Forge story of the hidden type "item_lore" (who made it, why, who owned it, the secret), so the
same lock, edit, and reroll controls and the same editable tables apply. Knowledge checks reveal that history in tiers.

Numbers follow the GM Core item-building tables (see itemdata.py): level sets a price range, an item's role decides where
in that range it sits, and item DCs come from the Magic Item DC table. Spell ranks follow the wand and scroll level
progression. These are generation heuristics, not a substitute for comparing against a similar official item, and
check_against_data() compares what it can against your downloaded rules data.

Styles: Standard (as above), Grim, Whimsical, and Ridiculous. A style sets the tone of the name and look and adds parts:
a grim drawback with a real cost; a whimsical oddity and a mild drawback; or a ridiculous ability with a severe limit and a
severe drawback, which is off the curve on purpose. The wording is in the item.style.* tables (Edit Tables).

Names say what an item does, in plain words. An item's HEADLINE is the thing it is really about: a worn or held item's main
ability (the spell it casts, the skill or sense it grants: "Hat of Light", "Boots of Speed"), a runic weapon's or armor's rune,
and, in the Ridiculous style, the absurd ability (every absurd ability and oddity line carries a name word, written
nw:Some_Words). make_name uses the item.name.head tables, whose patterns all contain @head, so a name always says it. The
strangeness of a Weird, Light, or Grim tone is a short flourish added to about a third of names ("Hat of Light, Probably"); the
rest of it lives in the quirk and the look. A name is kept short (about 46 characters when it can be). Items with no headline
(a plain wand, a potion) are named from their spell, as before.

Staves and grimoires follow the rules on Archives of Nethys (GM Core, Staves; Secrets of Magic, Grimoires). Their spell
spread and grimoire effects are tuning for this tool (see itemdata.py). A grimoire is a whole spellbook: its pages are filled
from your downloaded rules data and your custom spells (spellgen.py), and it is named for its owner or for its spells' theme.

Standard library plus storygen and itemdata only.
"""
import copy
import datetime
import math
import random
import re
import uuid
from collections import OrderedDict

try:
    from . import itemdata as D
    from . import names as NM
    from . import spellgen as SG
    from . import storygen as sg
except ImportError:                      # running this file directly
    import itemdata as D
    import names as NM
    import spellgen as SG
    import storygen as sg

KINDS = OrderedDict([("worn", "Worn item"), ("held", "Held item"), ("wand", "Wand"), ("staff", "Staff"),
                     ("grimoire", "Grimoire"), ("scroll", "Scroll"), ("potion", "Potion"), ("device", "One-use device"),
                     ("weapon", "Runic weapon"), ("armor", "Runic armor")])
KIND_WEIGHT = {"worn": 30, "held": 14, "wand": 8, "staff": 5, "grimoire": 3, "scroll": 8, "potion": 10, "device": 8,
               "weapon": 12, "armor": 10}
BOOK_KINDS = ("staff", "grimoire")       # spell items that are permanent, prepared during daily preparations
STYLES = OrderedDict([("standard", "Standard"), ("grim", "Grim"), ("whimsical", "Whimsical"), ("ridiculous", "Ridiculous")])
STYLE_TONE = {"grim": "grim", "whimsical": "light", "ridiculous": "weird"}
STYLE_NOTE = {
    "grim": "Grim style: a dark tone and a drawback with a real cost. The numbers are still on the GM Core curve.",
    "whimsical": "Whimsical style: an odd extra ability and a mild drawback. Roughly balanced; the GM rules on edge cases.",
    "ridiculous": "Ridiculous style: an absurd ability that is off the curve on purpose. Its limit and its drawback are what "
                  "pay for it. Price and level still come from the item's ordinary abilities."}


def style_key(value):
    """'Whimsical', 'whimsical' -> 'whimsical'. Anything else is 'standard'."""
    v = str(value or "").strip().lower()
    for k, label in STYLES.items():
        if v in (k, label.lower()):
            return k
    return "standard"
NAME_FLOURISH = {"weird": 0.35, "light": 0.30, "grim": 0.35}     # how often a name gets a short flourish, by tone
NAME_LIMITS = (46, 46, 46, 52, 52, 58, 64, 99)                   # a name's length limit on each try; the last accepts anything
NAME_FLOURISH_MAX = 58                                           # a flourish is added only if the whole name stays this short
CONSUMABLE_KINDS = ("scroll", "potion", "device")
RUNIC_KINDS = ("weapon", "armor")
ROLES = ("primary", "secondary", "tertiary")
RARITIES = ("common", "uncommon", "rare", "unique")
RARITY_WEIGHT = {"common": 80, "uncommon": 14, "rare": 5, "unique": 1}
FOCUS = OrderedDict([("any", "Any abilities"), ("skills", "Skills and luck"), ("spells", "Spell activations"),
                     ("defense", "Defense"), ("senses", "Senses, light, and movement")])
FOCUS_KEYS = {"skills": ("skill", "perception", "fortune"), "spells": ("spell_day", "spell_cantrip"),
              "defense": ("resist", "save_vs"), "senses": ("sense", "speed", "light")}
GLYPH = {1: "[1 action]", 2: "[2 actions]", 3: "[3 actions]", "R": "[reaction]", "F": "[free action]"}
TRADITION_SKILL = {"arcane": "Arcana", "divine": "Religion", "occult": "Occultism", "primal": "Nature"}
VERSION = 1
DEFAULT_FLAVOR = 0.35            # setting lines (Hallowmead) take about a third of a history's weight by default
DEFAULT_THEME_FOCUS = 0.25       # how hard a history sticks to the item's theme: lower gives more variety


# ---------------------------------------------------------------------------------------------- rules helpers
def clamp_level(level):
    return max(1, min(20, int(level)))


def price_range(level, consumable=False):
    return (D.CONS_PRICE if consumable else D.PERM_PRICE)[clamp_level(level)]


def _nice(x):
    if x < 50:
        return int(round(x))
    if x < 500:
        return int(round(x / 5.0) * 5)
    if x < 5000:
        return int(round(x / 10.0) * 10)
    return int(round(x / 50.0) * 50)


def place_price(level, consumable, t):
    """A price inside the GM Core range for the level. t is 0 (bottom of the range) to 1 (top)."""
    lo, hi = price_range(level, consumable)
    t = max(0.0, min(1.0, t))
    if t <= 0:
        return lo
    if t >= 1:
        return hi
    return max(lo, min(hi, _nice(lo + t * (hi - lo))))


def level_dc(level, rarity="common", adj=0):
    """The standard DC for a task of this level (GM Core DCs by level), plus rarity and any adjustment."""
    return sg.DC_BY_LEVEL[max(-1, min(25, int(level)))] + D.RARITY_ADJ.get(rarity, 0) + adj


def item_dc(level, narrow=False, forces_save=False):
    """Table 2-18, Magic Item DCs. Narrow items run up to 2 higher; items that force a save run 2 lower."""
    return D.ITEM_DC[clamp_level(level)] + (2 if narrow else 0) - (2 if forces_save else 0)


def skill_bonus(level):
    for lvl, bonus in D.SKILL_BONUS_LEVELS:
        if level >= lvl:
            return bonus
    return 0


def spell_rank_cap(level, freq="once per day"):
    """The highest spell rank an item of this level should cast at the given frequency (the wand progression:
    a wand of a rank-r spell is level 2r+1; casting more often drops the cap by one rank)."""
    base = (int(level) - 1) // 2
    if "hour" in freq or "10 minutes" in freq:
        base -= 1
    return max(0, min(9, base))


def ordinal(n):
    if n == 0:
        return "cantrip"
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def rank_phrase(rank):
    return "a cantrip" if rank == 0 else f"a {ordinal(rank)}-rank spell"


def gp_text(gp):
    """A price in coins: '920 gp 2 sp', '9 sp', '1,200 gp'. Fractions of a gold piece become silver and copper."""
    cp = int(round(float(gp or 0) * 100))
    if cp <= 0:
        return "0 gp"
    g, rem = divmod(cp, 100)
    sp, c = divmod(rem, 10)
    parts = ([f"{g:,} gp"] if g else []) + ([f"{sp} sp"] if sp else []) + ([f"{c} cp"] if c else [])
    return " ".join(parts)


def titlecase(text):
    small = {"of", "the", "a", "an", "and", "or", "but", "in", "on", "for", "to", "into", "at", "from", "by", "with"}
    words = str(text).split(" ")
    out = []
    for i, w in enumerate(words):
        out.append(w if (i and w.lower() in small) else (w[:1].upper() + w[1:] if w else w))
    return " ".join(out)


def _article(word):
    return sg.article(word)


def possessive(name):
    return name + ("'" if name.endswith("s") else "'s")


# ---------------------------------------------------------------------------------------------- spells
def spell_by_name(name):
    return D.SPELL_BY_NAME.get(str(name).lower())


POTION_OK = {"Heal", "Restoration", "Resist Energy", "Darkvision", "Spider Climb", "Haste", "Fly",
             "Freedom of Movement", "Enlarge"}


def potion_ok(spell):
    """Spells that make sense as something you drink: ones that affect you."""
    return spell["mode"] == "s" or spell["name"] in POTION_OK


def pick_spell(rng, rank_lo, rank_hi, tradition="any", prefer=(), modes=None, exclude=(), predicate=None, strict=False):
    """A spell with a rank in [rank_lo, rank_hi]. Spells matching the preferred effect tags are favored. When the
    tradition has no spell in range, any tradition is used unless strict."""
    def pool(trad):
        return [s for s in D.SPELLS if rank_lo <= s["rank"] <= rank_hi and s["name"] not in exclude
                and (trad in ("any", "", None) or trad in s["traditions"])
                and (modes is None or s["mode"] in modes) and (predicate is None or predicate(s))]
    cands = pool(tradition) or ([] if strict else pool("any"))
    if not cands:
        return None
    ws = [1.0 + 3.0 * len(set(prefer) & set(s["tags"])) for s in cands]
    return rng.choices(cands, weights=ws, k=1)[0]


def spell_for_rank(rng, rank, tradition="any", prefer=(), modes=None, exclude=(), predicate=None, min_rank=1):
    """A spell of exactly this rank, or the highest rank below it that has one. A requested tradition is kept by going
    down in rank before it is given up."""
    passes = (tradition, "any") if tradition not in ("any", "", None) else ("any",)
    for trad in passes:
        for r in range(rank, min_rank - 1, -1):
            s = pick_spell(rng, r, r, trad, prefer, modes, exclude, predicate, strict=True)
            if s:
                return s
    return None


def _trad_for(spell, rng, wanted="any"):
    if wanted in spell["traditions"]:
        return wanted
    return rng.choice(spell["traditions"])


# ---------------------------------------------------------------------------------------------- effects
EFFECTS = OrderedDict()


def effect(key, min_level, kinds=("worn", "held"), weight=1.0, max_level=20):
    def deco(fn):
        EFFECTS[key] = {"key": key, "min": min_level, "max": max_level, "kinds": tuple(kinds), "w": weight, "fn": fn}
        return fn
    return deco


SKILL_STEMS = {
    "Acrobatics": ["Nimble Feet", "the Tightrope", "Soft Landings"], "Arcana": ["Hidden Formulae", "Arcane Study"],
    "Athletics": ["Strong Arms", "the Long Haul"], "Crafting": ["Steady Hands", "the Patient Maker"],
    "Deception": ["Pleasant Lies", "False Faces"], "Diplomacy": ["Gentle Words", "Open Doors"],
    "Intimidation": ["the Long Stare", "Cold Looks"], "Medicine": ["Mended Bones", "Gentle Hands"],
    "Nature": ["Green Ways", "the Wild Mind"], "Occultism": ["Strange Lore", "Quiet Questions"],
    "Performance": ["the Crowd's Ear", "Bright Songs"], "Religion": ["Quiet Prayers", "Faithful Hours"],
    "Society": ["Good Manners", "Local Knowledge"], "Stealth": ["Quiet Steps", "the Unseen"],
    "Survival": ["the Long Trail", "Hard Winters"], "Thievery": ["Light Fingers", "Opened Locks"]}
SKILL_FX = {"Stealth": ["fx:stealth"], "Thievery": ["fx:stealth", "fx:craft"], "Deception": ["fx:social", "fx:stealth"],
            "Diplomacy": ["fx:social"], "Society": ["fx:social", "fx:knowledge"], "Medicine": ["fx:healing"],
            "Crafting": ["fx:craft"], "Arcana": ["fx:knowledge", "fx:magic"], "Occultism": ["fx:knowledge"],
            "Religion": ["fx:knowledge", "fx:protection"], "Nature": ["fx:knowledge", "fx:travel"],
            "Athletics": ["fx:travel", "fx:war"], "Acrobatics": ["fx:travel"], "Survival": ["fx:travel"],
            "Intimidation": ["fx:war", "fx:social"], "Performance": ["fx:social"]}
SPELL_STEMS = {"Invisibility": ["the Vanishing", "Quiet Passage"], "Fly": ["Swift Wings", "the High Road"],
               "Fireball": ["Hot Tempers", "the Burning Hour"], "Heal": ["Mended Hours", "Gentle Mercy"],
               "Sleep": ["Heavy Eyelids", "Idle Winters"], "Fear": ["Cold Dread", "the Long Shadow"],
               "Haste": ["Borrowed Time", "Swift Feet"], "Light": ["Borrowed Light", "the Last Lamp"],
               "Darkness": ["Deep Shade", "the Long Night"], "Gentle Landing": ["Soft Landings", "Gentle Falls"],
               "Mirror Image": ["Many Faces", "Second Selves"], "Teleport": ["Short Journeys", "the Far Door"],
               "Charm": ["Easy Friends", "Warm Welcomes"], "Knock": ["Opened Doors", "Light Fingers"]}


def skill_forms(skill, kind):
    return [k for k, v in D.FORMS.items() if v[3] == kind and skill in v[4]]


@effect("skill", 3, weight=5)
def fx_skill(level, rng, opts, kind, ctx):
    skill = opts.get("skill") or rng.choice(D.SKILLS)
    n = skill_bonus(level)
    return dict(fx="skill", name=f"{skill} bonus", text=f"You gain a +{n} item bonus to {skill} checks.", head=skill,
                act=None, traits=[], stems=SKILL_STEMS.get(skill, ["Fine Work"]), tags=["fx:skill"] + SKILL_FX.get(skill, []),
                role=D.SKILL_ROLE.get(skill, "tertiary"), opts={"skill": skill}, forms=skill_forms(skill, kind))


@effect("perception", 3, weight=2)
def fx_perception(level, rng, opts, kind, ctx):
    n = skill_bonus(level)
    return dict(fx="perception", name="Perception bonus", text=f"You gain a +{n} item bonus to Perception checks.",
                head="Perception", act=None, traits=[], stems=["Sharp Eyes", "the Watchful Hour", "Keen Ears"], tags=["fx:senses", "fx:skill"],
                role="primary", opts={}, forms=[k for k in ("goggles", "spectacles", "monocle", "eyepatch", "hat", "circlet",
                                                            "spyglass", "lantern", "hood") if D.FORMS[k][3] == kind])


@effect("save_vs", 4, kinds=("worn",), weight=1.5)
def fx_save_vs(level, rng, opts, kind, ctx):
    trait = opts.get("trait") or rng.choice(D.SAVE_VS)
    n = 1 if level < 12 else 2
    return dict(fx="save_vs", name=f"Saves against {trait} effects",
                text=f"You gain a +{n} item bonus to saving throws against {trait} effects.", act=None, traits=[],
                head=f"{trait.title()} Warding",
                stems=[f"{trait.title()} Warding", "Steady Nerves", "Hard-Won Calm"], tags=["fx:protection"],
                role="tertiary", opts={"trait": trait}, forms=[])


@effect("resist", 8, kinds=("worn",), weight=1.5)
def fx_resist(level, rng, opts, kind, ctx):
    energy = opts.get("energy") or rng.choice(D.ENERGIES)
    n = 5 if level < 12 else 10
    return dict(fx="resist", name=f"{energy.title()} resistance", text=f"You gain resistance {n} to {energy} damage.",
                head=f"{energy.title()} Resistance", act=None, traits=[], stems=[f"{energy.title()} Warding", "the Warm Hearth" if energy in ("cold",) else "Steady Hands"],
                tags=["fx:protection"] + (["fx:fire"] if energy == "fire" else []), role="secondary",
                opts={"energy": energy}, forms=["cloak", "amulet", "ring", "belt", "mantle", "robe", "coat"])


@effect("sense", 1, weight=2)
def fx_sense(level, rng, opts, kind, ctx):
    choices = [("low-light vision", 1), ("darkvision", 3), ("scent (imprecise) at 30 feet", 5)]
    allowed = [c for c in choices if level >= c[1]]
    best = [c for c in allowed if c[1] >= level - 3] or allowed          # a sense that suits the item's level
    sense = opts.get("sense")
    if sense not in [c[0] for c in allowed]:
        sense = rng.choice(best)[0]
    return dict(fx="sense", name="Sense", text=f"You gain {sense}.", act=None, traits=[],
                head={"low-light vision": "Low-Light Vision", "darkvision": "Darkvision"}.get(sense, "Scent"),
                stems=["Night Eyes", "the Cat's Eye", "Long Sight"], tags=["fx:senses"], role="tertiary",
                opts={"sense": sense}, forms=[k for k in ("goggles", "spectacles", "monocle", "eyepatch", "hood", "circlet",
                                                          "spyglass", "lantern", "pendant", "amulet") if D.FORMS[k][3] == kind])


@effect("speed", 5, kinds=("worn",), weight=1.5)
def fx_speed(level, rng, opts, kind, ctx):
    n = 5 if level < 12 else 10
    return dict(fx="speed", name="Speed bonus", text=f"You gain a +{n}-foot item bonus to your Speed.", act=None,
                head="Speed", traits=[], stems=["Quick Feet", "the Fair Wind", "Swift Errands"], tags=["fx:travel"], role="secondary",
                opts={}, forms=["boots", "sandals", "slippers", "anklet", "belt", "cloak", "cape"])


@effect("light", 1, weight=1, max_level=6)
def fx_light(level, rng, opts, kind, ctx):
    return dict(fx="light", name="Light", text="The item sheds bright light in a 20-foot radius and dim light for another "
                "20 feet. You can Interact to dim it or snuff it out, and to light it again.",
                head="Light", act=None, traits=["light"], stems=["Borrowed Light", "the Last Lamp", "Small Dawns"], tags=["fx:light"],
                role="tertiary", opts={}, forms=["lantern", "circlet", "pendant", "ring", "orb", "hat", "stone"])


def _act_traits(kind):
    return ["concentrate"] if kind == "worn" else ["manipulate"]


def _spell_effect_text(spell, rank, level, targeted_dc=True):
    where = "as a cantrip" if rank == 0 else f"at {ordinal(rank)} rank"
    bits = [f"You cast {spell['name']} ({spell['blurb']}) {where}."]
    if spell["mode"] in ("t", "a") and rank > 0 and spell["name"] not in ("Heal", "Restoration", "Haste", "Fly", "Darkvision",
                                                                           "Spider Climb", "Resist Energy", "Enlarge",
                                                                           "Freedom of Movement", "Dimension Door", "Teleport"):
        bits.append(f"The spell DC is {item_dc(level)}.")
    return " ".join(bits)


@effect("spell_day", 3, weight=7)
def fx_spell_day(level, rng, opts, kind, ctx):
    freq = opts.get("freq") or ("once per hour" if (level >= 7 and rng.random() < 0.18) else "once per day")
    cap = spell_rank_cap(level, freq)
    if cap < 1:
        freq, cap = "once per day", spell_rank_cap(level, "once per day")
    spell = spell_by_name(opts.get("spell")) if opts.get("spell") else None
    if spell is None or spell["rank"] > cap or spell["rank"] < 1:
        trad, used = ctx.get("tradition", "any"), ctx.get("used_spells", ())
        spell = None
        for lo in (max(1, cap - 1), 1):                       # keep the requested tradition by widening the rank window
            spell = pick_spell(rng, lo, max(1, cap), trad, ctx.get("prefer", ()), exclude=used, strict=True)
            if spell:
                break
        if spell is None:
            spell = pick_spell(rng, max(1, cap - 1), max(1, cap), "any", ctx.get("prefer", ()), exclude=used) \
                or pick_spell(rng, 1, max(1, cap), "any", ctx.get("prefer", ()))
    act = {"name": f"Cast {spell['name']}", "actions": spell["cast"], "traits": _act_traits(kind),
           "frequency": freq, "trigger": "You are falling." if spell["name"] == "Gentle Landing" else "",
           "requirements": "", "effect": _spell_effect_text(spell, spell["rank"], level)}
    stems = SPELL_STEMS.get(spell["name"], [spell["name"]])
    role = "secondary" if spell["rank"] >= cap else "tertiary"
    return dict(fx="spell_day", name=f"{spell['name']} activation", text="", act=act, traits=[], head=spell["name"],
                stems=stems, tags=list(spell["tags"]), role=role, opts={"spell": spell["name"], "freq": freq},
                forms=[], tradition=_trad_for(spell, rng, ctx.get("tradition", "any")), spell=spell["name"])


@effect("spell_cantrip", 1, weight=3, max_level=8)
def fx_spell_cantrip(level, rng, opts, kind, ctx):
    spell = spell_by_name(opts.get("spell")) if opts.get("spell") else None
    if spell is None or spell["rank"] != 0:
        spell = pick_spell(rng, 0, 0, ctx.get("tradition", "any"), ctx.get("prefer", ()), exclude=ctx.get("used_spells", ()))
    rank = max(1, (level + 1) // 2)
    act = {"name": f"Cast {spell['name']}", "actions": spell["cast"], "traits": _act_traits(kind),
           "frequency": "once per hour", "trigger": "", "requirements": "",
           "effect": f"You cast {spell['name']} ({spell['blurb']}) as a cantrip heightened to {ordinal(rank)} rank."}
    return dict(fx="spell_cantrip", name=f"{spell['name']} cantrip", text="", act=act, traits=[], head=spell["name"],
                stems=SPELL_STEMS.get(spell["name"], [spell["name"]]), tags=list(spell["tags"]), role="tertiary",
                opts={"spell": spell["name"]}, forms=[], tradition=_trad_for(spell, rng, ctx.get("tradition", "any")),
                spell=spell["name"])


@effect("fortune", 5, weight=1.5)
def fx_fortune(level, rng, opts, kind, ctx):
    skill = opts.get("skill") or rng.choice(D.SKILLS)
    act = {"name": "Lucky Break", "actions": "F", "traits": ["fortune"], "frequency": "once per day",
           "trigger": f"You fail a {skill} check.", "requirements": "",
           "effect": "Reroll the check and take the better result."}
    return dict(fx="fortune", name=f"{skill} luck", text="", act=act, traits=["fortune"], head=f"{skill} Luck",
                stems=["Small Mercies", "the Second Chance", "Lucky Breaks"], tags=["fx:skill"] + SKILL_FX.get(skill, []),
                role="tertiary", opts={"skill": skill}, forms=skill_forms(skill, kind))


# ---------------------------------------------------------------------------------------------- price and level
def role_t(roles, n_abilities, rng=None, jitter=0.07):
    base = sum(D.ROLE_T[r] for r in roles) / max(1, len(roles))
    t = base + 0.07 * (n_abilities - 1)
    if rng is not None:
        t += rng.uniform(-jitter, jitter)
    return max(0.0, min(1.0, t))


def _fixed_part(key, label, text, data=None, locked=False):
    return {"key": key, "label": label, "text": text, "locked": locked, "edited": False, "data": data or {}}


def part(item, key):
    return next((p for p in item["parts"] if p["key"] == key), None)


def parts_of(item, prefix):
    return [p for p in item["parts"] if p["key"].startswith(prefix)]


def effect_parts(item):
    return [p for p in item["parts"] if p["key"].startswith("effect")]


def main_effect(effs):
    """The ability an item is really about: the one with the highest role (primary, then secondary, then tertiary), the first
    of them on a tie. Its head word is what the item's name says."""
    order = {"primary": 0, "secondary": 1, "tertiary": 2}
    best = None
    for p in effs:
        rank = order.get((p.get("data") or {}).get("role"), 2)
        if best is None or rank < best[0]:
            best = (rank, p)
    return best[1] if best else None


def effect_heads(item):
    return [(p.get("data") or {}).get("head") for p in effect_parts(item)]


def all_acts(item):
    """Every activation on the item, in order: [(part key, act dict)]."""
    out = []
    for p in item["parts"]:
        act = (p.get("data") or {}).get("act")
        if act:
            out.append((p["key"], act))
    return out


# ---------------------------------------------------------------------------------------------- ability text
def _trim(text):
    return str(text or "").strip().rstrip(". ").strip()


def format_act(act):
    glyph = GLYPH.get(act.get("actions"), GLYPH[2])
    traits = ", ".join(act.get("traits") or [])
    bits = [f"Activate {glyph} {act.get('name', 'Activation')}" + (f" ({traits})" if traits else "")]
    for label, key in (("Frequency", "frequency"), ("Trigger", "trigger"), ("Requirements", "requirements")):
        if _trim(act.get(key)):
            bits.append(f"{label} {_trim(act[key])}")
    if str(act.get("effect") or "").strip():
        bits.append(f"Effect {act['effect'].strip()}")
    return "; ".join(bits)


def ability_text(res):
    return format_act(res["act"]) if res.get("act") else res.get("text", "")


# ---------------------------------------------------------------------------------------------- runic weapons and armor
def potency_tier(level):
    return 3 if level >= 16 else 2 if level >= 10 else 1 if level >= 2 else 0


def striking_tier(level):
    return 3 if level >= 19 else 2 if level >= 12 else 1 if level >= 4 else 0


def armor_potency_tier(level):
    return 3 if level >= 18 else 2 if level >= 11 else 1 if level >= 5 else 0


def resilient_tier(level):
    return 3 if level >= 20 else 2 if level >= 14 else 1 if level >= 8 else 0


def weapon_rune_ok(rune, base):
    info = D.WEAPONS[base]
    return {"any": True, "melee": info["kind"] == "melee", "thrown": D.weapon_thrown(info)}.get(rune["uses"], True)


def armor_rune_ok(rune, base):
    info = D.ARMORS[base]
    u = rune["uses"]
    if u == "nonmetal-light-medium":
        return (not info["metal"]) and info["cat"] in ("light", "medium")
    if u == "medium-heavy":
        return info["cat"] in ("medium", "heavy")
    return True


def pick_base(rng, kind, culture="", exclude=()):
    """A base weapon or armor. Uncommon ancestry weapons (dogslicer, elven curve blade...) are used only for items made
    in that culture's style, and then favored."""
    table = D.WEAPONS if kind == "weapon" else D.ARMORS
    names, weights = [], []
    for name, info in table.items():
        if name in exclude:
            continue
        anc = info.get("anc", "") if kind == "weapon" else ""
        if anc and anc != culture:
            continue
        names.append(name)
        weights.append(6.0 if anc else 1.0)
    return rng.choices(names, weights=weights, k=1)[0] if names else next(iter(table))


CONFLICTS = ({"holy", "unholy"},)


def _conflicts(name, chosen):
    return any(name in pair and (pair - {name}) & set(chosen) for pair in CONFLICTS)


def _rune_part(key, label, rune, kind):
    return {"key": key, "label": label, "text": f"{titlecase(rune['name'])}: {rune['text']}", "locked": False,
            "edited": False, "data": {"rune": rune["name"], "level": rune["level"], "price": rune["price"],
                                      "slot": kind, "official": True}}


def pick_property_rune(rng, kind, base, level, chosen=(), force_near=False):
    runes = D.WEAPON_RUNES if kind == "weapon" else D.ARMOR_RUNES
    ok = weapon_rune_ok if kind == "weapon" else armor_rune_ok
    cands = [r for r in runes if r["level"] <= level and ok(r, base) and r["name"] not in chosen
             and not _conflicts(r["name"], chosen)]
    if force_near:
        near = [r for r in cands if r["level"] >= level - 3]
        cands = near or cands
    if not cands:
        return None
    ws = [3.0 if r["level"] >= level - 3 else 1.0 for r in cands]
    return rng.choices(cands, weights=ws, k=1)[0]


def mechanical_name(item):
    """'+1 striking flaming longsword' from the item's runes."""
    kind = item["kind"]
    pieces = []
    pot = part(item, "potency")
    if pot:
        pieces.append(pot["data"]["rune"].split(" ")[0] if pot["data"]["rune"].startswith("+") else pot["data"]["rune"])
    second = part(item, "striking") or part(item, "resilient")
    if second:
        pieces.append(second["data"]["rune"])
    pieces += [p["data"]["rune"] for p in parts_of(item, "rune")]
    base = part(item, "base")
    if base:
        pieces.append(base["data"]["base"])
    return " ".join(pieces)


# ---------------------------------------------------------------------------------------------- base weapon and armor stats
def _num(n):
    return f"+{n}" if n > 0 else str(n)


def _mod(n):
    return f"+{n}" if n >= 0 else str(n)


def armor_noun(name):
    """'a suit of leather armor', 'a suit of chain mail', 'a breastplate': the armor's name with its article."""
    n = str(name)
    if n.endswith(("armor", "mail", "plate")) and n != "breastplate":
        return f"a suit of {n}"
    return f"{_article(n)} {n}"


def item_noun(kind, base):
    """'a longsword' or 'a suit of leather armor' (with the article)."""
    return armor_noun(base) if kind == "armor" else f"{_article(base)} {base}"


def _bulk_text(b):
    return "light (L)" if b == "L" else str(b)


def _tier_of(item, key, table):
    """Which tier (1 to 3) a fundamental rune part is, from its rune name, or 0 when the item doesn't have one."""
    p = part(item, key)
    if not p:
        return 0
    name = (p.get("data") or {}).get("rune") or ""
    for tier, row in table.items():
        if row[0] == name:
            return tier
    return 0


def _base_info(item):
    p = part(item, "base")
    if not p:
        return None, None
    name = (p.get("data") or {}).get("base") or p.get("text")
    table = D.WEAPONS if item["kind"] == "weapon" else D.ARMORS if item["kind"] == "armor" else None
    return (name, table[name]) if table and name in table else (None, None)


def rune_extras(item):
    """Extra damage from property runes: [(dice, type, condition)]."""
    out = []
    by = {r["name"]: r for r in D.WEAPON_RUNES}
    for p in parts_of(item, "rune"):
        r = by.get((p.get("data") or {}).get("rune"))
        if r and r.get("extra"):
            out.append(tuple(r["extra"]))
    return out


def weapon_damage_text(item):
    """'3d8 slashing plus 1d6 fire plus 1d6 spirit against undead' from the base weapon, striking rune, and property runes."""
    name, info = _base_info(item)
    if info is None:
        return ""
    dice = 1 + _tier_of(item, "striking", D.STRIKING)
    text = f"{dice}{info['die']} {D.DAMAGE_NAMES[info['dtype']]}"
    for dd, typ, cond in rune_extras(item):
        text += f" plus {dd} {typ}" + (f" {cond}" if cond else "")
    return text


def armor_ac_bonus(item):
    """(total item bonus to AC, base bonus, potency bonus)."""
    name, info = _base_info(item)
    if info is None:
        return 0, 0, 0
    pot = _tier_of(item, "potency", D.ARMOR_POTENCY)
    return info["ac"] + pot, info["ac"], pot


def trait_gloss_rows(traits):
    rows = []
    for t in traits:
        key = t.split()[0]
        if key in D.TRAIT_GLOSS:
            rows.append((t, D.TRAIT_GLOSS[key], "gloss"))
    return rows


def stat_lines(item):
    """The base weapon's or armor's own numbers, as [(label, text, style)] with style row or gloss. Empty for items that
    aren't weapons or armor, or have no base item chosen."""
    name, info = _base_info(item)
    if info is None:
        return []
    rows = []
    if item["kind"] == "weapon":
        pot = _tier_of(item, "potency", D.WEAPON_POTENCY)
        cat = f"{info['cat'].title()} {info['kind']} weapon" + (f", {info['group']} group" if info["group"] else "")
        if info["rarity"] != "common":
            cat += f", {info['rarity']}"
        rows.append(("Weapon", cat, "row"))
        rows.append(("Damage", weapon_damage_text(item), "row"))
        rows.append(("Hands and bulk", f"Hands {info['hands']}; Bulk {_bulk_text(info['bulk'])}", "row"))
        if info["kind"] == "ranged" and info["reload"] is None:
            rows.append(("Range", f"{info['range']} feet when thrown (no reload: it has to be drawn to throw)", "row"))
        elif info["kind"] == "ranged":
            rows.append(("Range", f"{info['range']} feet; Reload {info['reload']}", "row"))
        elif info["range"]:
            rows.append(("Range", f"{info['range']} feet when thrown", "row"))
        rows.append(("Traits", ", ".join(info["traits"]) or "none", "row"))
        if pot:
            rows.append(("Attack", f"{_num(pot)} item bonus to attack rolls", "row"))
        rows += trait_gloss_rows(info["traits"])
    else:
        total, base, pot = armor_ac_bonus(item)
        rows.append(("Armor", f"{info['cat'].title()} armor, {info['group']} group", "row"))
        rows.append(("AC bonus", f"{_num(total)} item bonus to AC" + (f" ({_num(base)} base, {_num(pot)} armor potency)" if pot else ""), "row"))
        rows.append(("Dex cap", _mod(info["dex"]), "row"))
        s_txt = f"if your Strength modifier is {_mod(info['strength'])} or more"
        rows.append(("Check penalty", (f"{info['check']} to Strength- and Dexterity-based skill checks other than attacks "
                                       f"(none {s_txt})") if info["check"] else "none", "row"))
        rows.append(("Speed penalty", (f"{info['speed']} feet (reduced by 5 feet {s_txt})") if info["speed"] else "none", "row"))
        rows.append(("Strength and bulk", f"Strength {_mod(info['strength'])}; Bulk {_bulk_text(info['bulk'])}", "row"))
        res = _tier_of(item, "resilient", D.RESILIENT)
        if res:
            rows.append(("Saves", f"{_num(res)} item bonus to saving throws", "row"))
        rows.append(("Traits", ", ".join(info["traits"]) or "none", "row"))
        rows += trait_gloss_rows(info["traits"])
    return rows


def runic_price_text(item):
    base = part(item, "base")
    runes = sum(p["data"]["price"] for p in item["parts"] if p["data"].get("official"))
    bp = base["data"]["price"] if base else 0
    if bp <= 0:
        return f"{gp_text(runes)} (all in runes; the base item is free)"
    return f"{gp_text(runes + bp)} ({gp_text(runes)} in runes, {gp_text(bp)} for the base item)"


# ---------------------------------------------------------------------------------------------- the item skeleton
def new_item(kind, level, rarity, settings=None):
    return {"id": uuid.uuid4().hex[:10], "version": VERSION, "mode": "generated", "kind": kind, "name": "",
            "name_edited": False, "subtitle": "", "level": int(level), "rarity": rarity, "price_gp": 0.0,
            "price_edited": False, "price_t": 0.5, "role": "secondary", "role_locked": False, "traits": [],
            "tradition": "", "usage": "", "bulk": "L", "consumable": kind in CONSUMABLE_KINDS, "parts": [],
            "lore": None, "settings": dict(settings or {}), "created": datetime.date.today().isoformat(), "notes": ""}


def item_tags(item):
    """The effect tags (fx:...) describing what the item does, used to keep its history and name coherent. A runic
    weapon or armor also gets the tags its runes imply (fx:fire for a flaming rune) and what it does at heart."""
    tags = list((item.get("settings") or {}).get("fx_tags") or [])
    for p in item["parts"]:
        data = p.get("data") or {}
        tags += list(data.get("tags") or [])
        if data.get("rune"):
            tags += D.RUNE_FX.get(data["rune"], [])
    tags += D.BASE_FX.get(item.get("kind"), []) if item.get("mode") != "custom" or part(item, "base") else []
    return sorted(set(tags))


def item_traits(item):
    if item.get("mode") == "custom":
        own = [t for t in (item.get("traits") or []) if t not in RARITIES]
        return ([item["rarity"]] if item["rarity"] != "common" else []) + own
    traits = set()
    kind = item["kind"]
    if item["tradition"]:
        traits.add(item["tradition"])
    else:
        traits.add("magical")
    if kind in ("worn",):
        traits.add("invested")
    if item["consumable"]:
        traits.add("consumable")
    if kind in ("wand", "scroll", "potion", "staff", "grimoire"):
        traits.add(kind)
    for p in item["parts"]:
        for t in (p.get("data") or {}).get("traits") or []:
            traits.add(t)
    ordered = sorted(traits)
    if item["rarity"] != "common":
        ordered = [item["rarity"]] + ordered
    return ordered


def recompute(item):
    """Level, price, role, and traits from the item's parts (unless you set the price by hand)."""
    kind = item["kind"]
    if item.get("mode") == "custom":
        item["price_range"] = list(price_range(item["level"], item["consumable"]))
        item["traits"] = item_traits(item)                       # your traits, with the rarity first
        return item
    if kind in RUNIC_KINDS:
        runes = [p["data"] for p in item["parts"] if p["data"].get("official")]
        base = part(item, "base")
        item["level"] = clamp_level(max([r["level"] for r in runes] or [1]))
        if not item["price_edited"]:
            item["price_gp"] = round(sum(r["price"] for r in runes) + (base["data"]["price"] if base else 0), 2)
        item["price_range"] = None
        item["role"] = "primary"
        item["subtitle"] = mechanical_name(item)
        base_name = base["data"]["base"] if base else ""
        item["usage"] = f"etched onto {item_noun(kind, base_name)}" if base_name else ""
        _n, _info = _base_info(item)
        item["bulk"] = str(_info["bulk"]) if _info else "as the base item"
    elif kind in ("wand", "scroll", "potion", "device"):
        sp = part(item, "spell")
        rank = sp["data"]["rank"] if sp else 1
        item["level"] = {"wand": 2 * rank + 1, "scroll": 2 * rank - 1, "potion": 2 * rank, "device": 2 * rank}[kind]
        item["level"] = clamp_level(max(item["level"], 1))
        if not item["price_edited"]:
            item["price_gp"] = place_price(item["level"], item["consumable"], item["price_t"])
        item["price_range"] = list(price_range(item["level"], item["consumable"]))
    else:
        item["level"] = clamp_level(item["level"])
        if not item["price_edited"]:
            item["price_gp"] = place_price(item["level"], False, item["price_t"])
        item["price_range"] = list(price_range(item["level"], False))
    if not item["role_locked"] and kind not in RUNIC_KINDS:
        t = item["price_t"]
        item["role"] = "primary" if t >= 0.75 else "secondary" if t >= 0.4 else "tertiary"
    if item["tradition"] == "" and not item["settings"].get("tradition") in D.TRADITIONS:
        for p in item["parts"]:
            tr = (p.get("data") or {}).get("tradition")
            if tr:
                item["tradition"] = tr
                break
    item["traits"] = item_traits(item)
    return item


# ---------------------------------------------------------------------------------------------- the generator
_PURPOSE = [(re.compile(rx, re.IGNORECASE), key) for rx, key in D.PURPOSE_RULES]
_OCCUPATION = re.compile(D.OCCUPATION_PURPOSE, re.IGNORECASE)


def purpose_key(text):
    """What an item was made for, from the history's 'made for' line: a key such as 'thief' or 'healer' (which has word
    tables), 'trade:cartwright' for 'to help a cartwright do their work', or '' when the line names no particular use."""
    t = str(text or "")
    for rx, key in _PURPOSE:
        if rx.search(t):
            return key
    m = _OCCUPATION.search(t)
    return "trade:" + m.group(1).strip().lower() if m else ""


DEVICE_NOUN = {"pinch of dust in a twist of paper": "Dust", "stick of incense": "Incense", "short candle": "Candle",
               "dried seed": "Seed", "glass bead": "Bead", "gray feather": "Feather", "piece of chalk": "Chalk",
               "pouch of powder": "Powder", "small wafer": "Wafer", "smooth pebble": "Pebble", "scrap of ribbon": "Ribbon",
               "dried leaf": "Leaf", "wax-sealed vial": "Vial", "tiny paper bird": "Paper Bird", "knot of cord": "Knot",
               "coin with a hole in it": "Coin"}


class ItemGenerator:
    def __init__(self, registry=None, campaign=None, rng=None):
        self.registry = registry or sg.default_registry()
        # recent=12: a table won't repeat what it gave out in roughly the last dozen items while it has other choices
        self.gen = sg.Generator(self.registry, campaign=campaign or sg.Campaign(),
                                history=sg.History(strength=0.25, decay=0.85, recent=12), rng=rng or random.Random())

    @property
    def rng(self):
        return self.gen.rng

    def set_campaign(self, campaign):
        self.gen.campaign = campaign

    def set_registry(self, registry):
        self.registry = registry
        self.gen.registry = registry

    # ----- helpers
    def _ctx(self, settings, tags=(), strict=None, loose=None):
        """A Story Forge rolling context. strict (0 to 1) lowers entries with no tone when a tone is chosen; loose lowers
        tone-specific entries when no tone is chosen. Names and looks use both so the tone you pick shows."""
        st = {"themes": list(settings.get("themes") or []), "env": settings.get("env", "any"),
              "tone": settings.get("tone", "any"), "level": int(settings.get("level", 5)), "focus": 0.6,
              "use_campaign": 0.0, "packs": settings.get("packs") or ["core"]}
        st["pack_share"] = self._flavor(settings)
        if strict is not None:
            st["tone_strict"] = strict
        if loose is not None:
            st["tone_loose"] = loose
        return sg.Ctx(self.gen, st, set(tags))

    @staticmethod
    def _flavor(settings):
        """How much of the weight setting lines (Hallowmead) may take in a table: 0 to 1, or None when that pack is off."""
        if "hallowmead" not in (settings.get("packs") or []):
            return None
        return max(0.0, min(0.95, float(settings.get("flavor", DEFAULT_FLAVOR))))

    @staticmethod
    def _prefer(themes):
        out = []
        for fx, th in D.FX_THEMES.items():
            if set(th) & set(themes or ()):
                out.append(fx)
        return out

    def _effect_ctx(self, settings, item=None):
        used = []
        if item:
            for p in effect_parts(item):
                sp = (p.get("data") or {}).get("spell")
                if sp:
                    used.append(sp)
        culture = (item or {}).get("culture") or (settings.get("culture") if settings.get("culture") in D.CULTURE_INFO else "")
        return {"tradition": settings.get("tradition", "any") if settings.get("tradition") in D.TRADITIONS else "any",
                "prefer": self._prefer(settings.get("themes")), "used_spells": used, "culture": culture}

    def _pick_effect(self, kind, level, rng, ectx, focus="any", used_keys=(), settings=None):
        allowed = FOCUS_KEYS.get(focus)

        def cands(restrict):
            return [e for e in EFFECTS.values() if kind in e["kinds"] and e["min"] <= level <= e["max"]
                    and e["key"] not in used_keys and (not restrict or e["key"] in allowed)]
        pool = cands(bool(allowed)) or cands(False)
        if not pool:
            return None
        built = []
        for e in pool:
            res = e["fn"](level, rng, {}, kind, ectx)
            built.append((e, res))
        # favor abilities that suit the item's level (a level-7 item should not be built around a level-1 effect)
        ws = [e["w"] * (3.0 if level - e["min"] <= 3 else 1.0) * (1.0 + 2.0 * len(set(ectx["prefer"]) & set(res["tags"])))
              for e, res in built]
        return rng.choices(built, weights=ws, k=1)[0][1]

    @staticmethod
    def _effect_part(res, key):
        p = _fixed_part(key, "Ability", ability_text(res), dict(res))
        p["data"] = {k: v for k, v in res.items() if k != "text"}
        p["data"]["text"] = res.get("text", "")
        return p

    def _form_for(self, rng, kind, results):
        prefs = []
        for r in results:
            prefs += list(r.get("forms") or [])
        pool = [k for k in prefs if D.FORMS[k][3] == kind] or [k for k, v in D.FORMS.items() if v[3] == kind]
        return rng.choice(pool)

    # ----- the builders: each fills item["parts"] and the fields that depend on them
    def _build_wondrous(self, item, level, rng, ectx, focus="any", abilities=0, settings=None):
        kind = item["kind"]
        n = abilities if abilities in (1, 2, 3) else rng.choices([1, 2, 3], weights=[62, 30, 8])[0]
        each = max(1, level - 2 * (n - 1))
        results, used = [], []
        for _ in range(n):
            res = self._pick_effect(kind, each, rng, ectx, focus, used, settings)
            if res is None:
                break
            results.append(res)
            used.append(res["fx"])
            if res.get("spell"):
                ectx["used_spells"] = list(ectx["used_spells"]) + [res["spell"]]
        if not results:                                         # always at least a light
            results.append(EFFECTS["light"]["fn"](1, rng, {}, kind, ectx))
        form = self._form_for(rng, kind, results)
        fname, usage, bulk, fkind, _ = D.FORMS[form]
        item["parts"].append(_fixed_part("form", "Item", fname, {"form": form, "usage": usage, "bulk": bulk, "kind": fkind}))
        for i, res in enumerate(results, 1):
            item["parts"].append(self._effect_part(res, f"effect{i}"))
        item["usage"], item["bulk"] = usage, bulk
        item["price_t"] = role_t([r["role"] for r in results], len(results), rng)

    def _build_worn(self, item, level, rng, ectx, **kw):
        self._build_wondrous(item, level, rng, ectx, **kw)

    def _build_held(self, item, level, rng, ectx, **kw):
        self._build_wondrous(item, level, rng, ectx, **kw)

    def _spell_part(self, spell, rank, kind):
        return _fixed_part("spell", "Spell", f"{spell['name']} ({rank_phrase(rank)})",
                           {"spell": spell["name"], "rank": rank, "tags": list(spell["tags"]), "kind": kind})

    def _build_wand(self, item, level, rng, ectx, **kw):
        rank = max(1, min(9, (level - 1) // 2))
        sp = spell_for_rank(rng, rank, ectx["tradition"], ectx["prefer"])
        item["parts"].append(self._spell_part(sp, sp["rank"], "wand"))
        item["tradition"] = _trad_for(sp, rng, ectx["tradition"])
        item["usage"], item["bulk"] = "held in 1 hand", "L"
        item["price_t"] = 1.0

    def _build_staff(self, item, level, rng, ectx, **kw):
        """A staff: one cantrip and one or two spells of each rank up to the wand cap, all from one tradition."""
        cap = max(1, min(9, (level - 1) // 2))
        trad = ectx["tradition"]
        top = spell_for_rank(rng, cap, trad, ectx["prefer"])
        trad = _trad_for(top, rng, trad)
        spells = {top["rank"]: [top]}
        used = {top["name"]}
        can = pick_spell(rng, 0, 0, trad, ectx["prefer"], exclude=used, strict=True) or pick_spell(rng, 0, 0, "any", ectx["prefer"])
        for r in range(1, top["rank"] + 1):
            want = 1 if r == top["rank"] else rng.choice([1, 1, 2])
            have = spells.setdefault(r, [])
            while len(have) < want:
                sp = pick_spell(rng, r, r, trad, ectx["prefer"], exclude=used, strict=True)
                if sp is None:
                    break
                have.append(sp)
                used.add(sp["name"])
        item["parts"].append(self._spell_part(top, top["rank"], "staff"))       # the signature spell names the staff
        listing = {"cantrip": can["name"] if can else "", "ranks": {str(r): [x["name"] for x in v] for r, v in sorted(spells.items()) if v}}
        item["parts"].append(_fixed_part("spells", "Spells", staff_list_text(listing), {"list": listing, "tags": list(top["tags"])}))
        item["parts"].append(_fixed_part("act1", "Activation", "", {"act": staff_act(listing)}))
        item["parts"][-1]["text"] = format_act(item["parts"][-1]["data"]["act"])
        item["tradition"] = trad
        item["usage"], item["bulk"] = "held in 1 hand", "1"
        item["price_t"] = 0.85

    GRIMOIRE_NEW_SPELL = {"grim": 0.35, "whimsical": 0.5, "ridiculous": 0.75}     # chance a styled book holds a brand-new spell

    def _grimoire_owner(self, item, rng):
        """Who the book belongs to: the owner you gave (an NPC who carries it), or a made-up person of the item's culture."""
        owner = (item["settings"].get("owner") or "").strip()
        if not owner:
            info = D.CULTURE_INFO.get(item.get("culture") or "")
            anc = rng.choice(info["ancestries"]) if info else NM.pick_ancestry(rng, (), self.gen.campaign.ancestry_weights or None)
            owner = NM.make_name(anc, rng)
            item["settings"]["owner"] = owner
        item["owner"] = owner
        return owner

    def _build_grimoire(self, item, level, rng, ectx, **kw):
        """A grimoire: a spellbook of cantrips and spells up to the rank its level allows, from one tradition, with a theme,
        plus the once-a-day activation that strengthens a spell cast from a spell slot."""
        level = max(3, level)
        style = style_key(item["settings"].get("style"))
        self._grimoire_owner(item, rng)
        name, _lo, text = rng.choice([e for e in D.GRIMOIRE_EFFECTS if e[1] <= level])
        cap = max(1, min(10, (level + 1) // 2))
        trad = ectx["tradition"] if ectx["tradition"] in D.TRADITIONS else rng.choice(D.TRADITIONS)
        themes = SG.themes_available(trad, cap)
        theme = rng.choices(list(themes), weights=list(themes.values()), k=1)[0] if themes and rng.random() < 0.75 else ""
        book = SG.pick_spellbook(rng, cap, trad, theme)
        new = []
        if rng.random() < self.GRIMOIRE_NEW_SPELL.get(style, 0.0):
            r = rng.randint(1, cap)
            sp = SG.generate_spell(r, style, trad, "Spell", rng, self.registry, owner=item.get("owner", ""))
            book["ranks"].setdefault(str(r), []).append({"name": sp["name"], "rank": r, "generated": True})
            new.append(sp)
        if not theme:                                          # name the book for what it turned out to hold
            counts = {}
            for t in SG.book_traits(book):
                for th, words in D.GRIMOIRE_THEMES.items():
                    if t in words:
                        counts[th] = counts.get(th, 0) + 1
            theme = max(counts, key=counts.get) if counts and max(counts.values()) >= 3 else ""
        act = {"name": name, "actions": "F", "traits": ["concentrate"], "frequency": "once per day",
               "trigger": "You Cast a Spell from a spell slot",
               "effect": text.format(n=max(1, level // 3)) + " This works only on spells cast from spell slots, not cantrips, "
                                                              "focus spells, or innate spells."}
        item["parts"].append(_fixed_part("act1", "Activation", format_act(act), {"act": act, "grimoire": name,
                                                                                  "tags": ["fx:magic", "fx:knowledge"]}))
        item["parts"].append(_fixed_part("spells", "Spells in the book", "\n".join(SG.book_lines(book)),
                                         {"book": book, "generated": new, "theme": theme, "tradition": trad}))
        item["tradition"] = trad
        item["usage"], item["bulk"] = "carried (studied during daily preparations)", "L"
        item["price_t"] = 0.6

    def _build_scroll(self, item, level, rng, ectx, **kw):
        rank = max(1, min(9, (level + 1) // 2))
        sp = spell_for_rank(rng, rank, ectx["tradition"], ectx["prefer"])
        item["parts"].append(self._spell_part(sp, sp["rank"], "scroll"))
        item["tradition"] = _trad_for(sp, rng, ectx["tradition"])
        item["usage"], item["bulk"] = "held in 1 hand", "L"
        item["price_t"] = 0.95

    def _build_potion(self, item, level, rng, ectx, **kw):
        rank = max(1, min(9, level // 2))
        sp = spell_for_rank(rng, rank, ectx["tradition"], ectx["prefer"], predicate=potion_ok)
        item["parts"].append(self._spell_part(sp, sp["rank"], "potion"))
        item["tradition"] = _trad_for(sp, rng, ectx["tradition"])
        item["usage"], item["bulk"] = "held in 1 hand", "L"
        item["price_t"] = 0.85 if ({"fx:stealth", "fx:travel", "fx:healing"} & set(sp["tags"])) else 0.5

    def _build_device(self, item, level, rng, ectx, **kw):
        rank = max(1, min(9, level // 2))
        sp = spell_for_rank(rng, rank, ectx["tradition"], ectx["prefer"])
        name, verb = rng.choice(D.DEVICES)
        item["parts"].append(_fixed_part("form", "Item", name, {"form": name, "verb": verb}))
        item["parts"].append(self._spell_part(sp, sp["rank"], "device"))
        item["tradition"] = _trad_for(sp, rng, ectx["tradition"])
        item["usage"], item["bulk"] = "held in 1 hand", "L"
        item["price_t"] = 0.5

    def _build_weapon(self, item, level, rng, ectx, **kw):
        level = max(2, level)
        base = pick_base(rng, "weapon", ectx.get("culture", ""))
        item["parts"].append(_fixed_part("base", "Weapon", base, {"base": base, "price": D.WEAPONS[base]["price"], "level": 0}))
        pot = potency_tier(level)
        if pot > 1 and rng.random() < 0.2:
            pot -= 1
        st = striking_tier(level) if pot else 0
        if st and rng.random() < 0.15:
            st -= 1
        n, name_l, price = D.WEAPON_POTENCY[pot][1], D.WEAPON_POTENCY[pot][0], D.WEAPON_POTENCY[pot][2]
        item["parts"].append(_fixed_part("potency", "Potency rune", f"{name_l}: +{pot} item bonus to attack rolls",
                                         {"rune": name_l, "level": n, "price": price, "official": True, "slot": "weapon"}))
        if st:
            sname, slvl, sprice = D.STRIKING[st]
            item["parts"].append(_fixed_part("striking", "Striking rune",
                                             f"{titlecase(sname)}: the weapon deals {st + 1} weapon damage dice",
                                             {"rune": sname, "level": slvl, "price": sprice, "official": True,
                                              "slot": "weapon"}))
        chosen = []
        for i in range(pot):
            chance = (1.0 if i == 0 and level >= 4 else 0.55, 0.45, 0.3)[i]
            if rng.random() > chance:
                continue
            r = pick_property_rune(rng, "weapon", base, level, chosen, force_near=(i == 0))
            if r:
                chosen.append(r["name"])
                item["parts"].append(_rune_part(f"rune{len(chosen)}", "Property rune", r, "weapon"))
        item["price_t"] = 1.0

    def _build_armor(self, item, level, rng, ectx, **kw):
        level = max(5, level)
        base = pick_base(rng, "armor", ectx.get("culture", ""))
        item["parts"].append(_fixed_part("base", "Armor", base, {"base": base, "price": D.ARMORS[base]["price"], "level": 0}))
        pot = armor_potency_tier(level)
        if pot > 1 and rng.random() < 0.2:
            pot -= 1
        res = resilient_tier(level) if pot else 0
        if res and rng.random() < 0.15:
            res -= 1
        n, name_l, price = D.ARMOR_POTENCY[pot][1], D.ARMOR_POTENCY[pot][0], D.ARMOR_POTENCY[pot][2]
        item["parts"].append(_fixed_part("potency", "Potency rune", f"{name_l}: +{pot} item bonus to AC",
                                         {"rune": name_l, "level": n, "price": price, "official": True, "slot": "armor"}))
        if res:
            rname, rlvl, rprice = D.RESILIENT[res]
            item["parts"].append(_fixed_part("resilient", "Resilient rune",
                                             f"{titlecase(rname)}: +{res} item bonus to saving throws",
                                             {"rune": rname, "level": rlvl, "price": rprice, "official": True,
                                              "slot": "armor"}))
        chosen = []
        for i in range(pot):
            chance = (1.0 if i == 0 and level >= 6 else 0.5, 0.4, 0.3)[i]
            if rng.random() > chance:
                continue
            r = pick_property_rune(rng, "armor", base, level, chosen, force_near=(i == 0))
            if r:
                chosen.append(r["name"])
                item["parts"].append(_rune_part(f"rune{len(chosen)}", "Property rune", r, "armor"))
        item["price_t"] = 1.0

    # ----- looks, quirks, drawbacks
    def _deco_ctx(self, item):
        return self._ctx(item["settings"], item_tags(item), strict=0.3, loose=0.4)

    def _cu_table(self, item, part_name, rng, chance=0.85):
        """A culture's own table for a look, material, or quirk (most of the time), else the general one."""
        c = item.get("culture") or ""
        name = f"item.cu.{c}.{part_name}"
        if c and self.registry.has(name) and rng.random() < chance:
            return name
        return {"look": "item.motif", "material": "item.material.decor", "quirk": "item.quirk"}[part_name]

    def _look_text(self, item, rng, ctx):
        kind = item["kind"]
        motif = ctx.roll(self._cu_table(item, "look", rng)).text
        material = ctx.roll(self._cu_table(item, "material", rng)).text
        if kind in ("worn", "held"):
            name = part(item, "form")["text"]
            return f"{sg.cap(_article(name) + ' ' + name)} made of {material}, {motif}."
        if kind == "wand":
            look = rng.choice(D.WAND_LOOKS)
            return sg.cap(look) + (f", {motif}" if rng.random() < 0.6 else "") + "."
        if kind == "staff":
            return sg.cap(rng.choice(D.STAFF_LOOKS)) + (f", {motif}" if rng.random() < 0.5 else "") + "."
        if kind == "grimoire":
            return sg.cap(rng.choice(D.GRIMOIRE_LOOKS)) + (f", {motif}" if rng.random() < 0.5 else "") + "."
        if kind == "scroll":
            return f"A scroll written on {rng.choice(D.SCROLL_LOOKS)}."
        if kind == "potion":
            return f"A small vial holding {rng.choice(D.POTION_LOOKS)}."
        if kind == "device":
            name = part(item, "form")["text"]
            return sg.cap(_article(name) + " " + name) + (f", {motif}" if rng.random() < 0.5 else "") + "."
        base = part(item, "base")["text"]
        noun = sg.cap(item_noun(kind, base))
        if kind == "weapon":
            return f"{noun} with a grip of {material}, {motif}."
        return f"{noun} trimmed with {material}, {motif}."

    def _decorate(self, item, rng, quirk=True, drawback=False):
        ctx = self._deco_ctx(item)
        item["parts"].append(_fixed_part("look", "Appearance", self._look_text(item, rng, ctx)))
        if quirk:
            item["parts"].append(_fixed_part("quirk", "Quirk", ctx.roll(self._cu_table(item, "quirk", rng, 0.7)).text))
        style = style_key(item["settings"].get("style"))
        if style != "standard":
            self._style_parts(item, rng, style)
        elif drawback and not item["consumable"]:                       # a potion gets drunk; a drawback means nothing to it
            item["parts"].append(_fixed_part("drawback", "Drawback", ctx.roll("item.drawback").text))

    # ----- styles
    def _style_ctx(self, item):
        ctx = self._deco_ctx(item)
        lvl = clamp_level(item["level"])
        ctx.vars.update(lvl=str(lvl), dc=str(item_dc(lvl, forces_save=True)), gp=f"{max(1, round(price_range(lvl, True)[0])):g}")
        ctx.tags.add("it:" + item["kind"])
        ctx.tone = "any"                    # the style tables are tagged for their own style (t:weird), not for the tone you chose
        return ctx

    def _style_text(self, item, key, ctx):
        """The text for one style part. key is drawback, oddity, absurd, or limit."""
        return self._style_roll(item, key, ctx)[0]

    def _style_roll(self, item, key, ctx):
        """(text, name word) for one style part. The name word is the line's nw:Some_Words tag, or '' for a line without one
        (one you added in Edit Tables)."""
        style = style_key(item["settings"].get("style"))
        if key == "drawback":
            if item["consumable"]:
                table = {"grim": "item.style.after.grim", "whimsical": "item.style.after.whimsy",
                         "ridiculous": "item.style.after.ridic"}.get(style, "item.drawback")
            else:
                table = {"grim": "item.style.cost.grim", "whimsical": "item.style.cost.whimsy",
                         "ridiculous": "item.style.cost.severe"}.get(style, "item.drawback")
        else:
            table = {"oddity": "item.style.oddity", "absurd": "item.style.absurd", "limit": "item.style.limit"}[key]
        if not self.registry.has(table):                    # a table edited away: fall back to the minor drawbacks
            table = "item.drawback"
        r = ctx.roll(table)
        word = next((t[3:].replace("_", " ") for t in sorted(r.tags) if t.startswith("nw:")), "")
        return re.sub(r"\s+", " ", r.text).strip(), word

    def _style_parts(self, item, rng, style):
        ctx = self._style_ctx(item)
        if style == "whimsical" and not item["consumable"]:
            text, word = self._style_roll(item, "oddity", ctx)
            item["parts"].append(_fixed_part("oddity", "Oddity", text, {"nw": word}))
        if style == "ridiculous":
            text, word = self._style_roll(item, "absurd", ctx)
            item["parts"].append(_fixed_part("absurd", "Absurd ability", text, {"nw": word}))
            item["parts"].append(_fixed_part("limit", "Limit", self._style_text(item, "limit", ctx)))
        label = "Aftereffect" if item["consumable"] else "Drawback"
        item["parts"].append(_fixed_part("drawback", label, self._style_text(item, "drawback", ctx)))

    # ----- history
    # ----- culture: whose style an item is made in
    def _culture_of_entities(self, entities):
        """The culture of a maker: a campaign faction or NPC page (by its kind or ancestry), or a generated NPC's ancestry."""
        camp = self.gen.campaign
        for e in entities or []:
            title = str(e.get("title") or "").strip()
            if e.get("ancestry"):
                c = D.culture_for_text(e["ancestry"])
                if c:
                    return c
            low = title.lower()
            if not low:
                continue
            for f in getattr(camp, "factions", []) or []:
                if f["title"].lower() == low:
                    c = D.culture_for_text(f["title"]) or D.culture_for_text(f.get("kind", ""))
                    if c:
                        return c
            for n in getattr(camp, "npcs", []) or []:
                if n["title"].lower() == low:
                    c = D.culture_for_text(n.get("ancestry", "")) or D.culture_for_text(n.get("role", ""))
                    if c:
                        return c
        return ""

    def _lore_culture(self, item):
        """Culture from an item's history: the maker's tags (mk:goblin...) or the maker's page."""
        story = self.lore_story(item)
        who = story.slots.get("who") if story else None
        if who is None:
            return ""
        for t in who.tags:
            if t.startswith("mk:") and t[3:] in D.CULTURE_INFO:
                return t[3:]
        return self._culture_of_entities(who.entities)

    def _culture_preset(self, culture, settings):
        """A maker of that people, for the history's 'made by' line."""
        info = D.CULTURE_INFO[culture]
        anc = self.rng.choice(info["ancestries"])
        ctx = self._ctx(settings, ["anc:" + anc.lower().replace(" ", "_")])
        r = ctx.roll("npc.named")
        return {"text": r.text, "tags": sorted(set(r.tags) | {"mk:" + info["mk"], "k:npc"}), "entities": list(r.entities)}

    def make_lore(self, item, presets=None):
        s = item["settings"]
        tags = item_tags(item)
        themes = list(s.get("themes") or [])
        if not themes:
            for t in tags:
                for th in D.FX_THEMES.get(t, []):
                    if th not in themes:
                        themes.append(th)
            themes = themes[:1]
        story = self.gen.generate("item_lore", themes=themes, env=s.get("env", "any"), tone=s.get("tone", "any"),
                                  level=item["level"], focus=float(s.get("theme_focus", DEFAULT_THEME_FOCUS)),
                                  use_campaign=float(s.get("use_campaign", 0.5)), packs=s.get("packs") or ["core"],
                                  extra_tags=tags + ["it:" + item["kind"]], presets=presets, pack_share=self._flavor(s))
        self._trim_lore(item, story)
        item["lore"] = story.to_dict()
        if s.get("culture", "auto") == "auto":
            item["culture"] = self._lore_culture(item) or item.get("culture", "")
        return item

    @staticmethod
    def _trim_lore(item, story):
        """A consumable is used up, so it has no long line of owners or incidents: those lines are left empty and locked."""
        if item["consumable"]:
            for key in ("owner", "fate", "incident", "state"):
                if key in story.slots:
                    story.slots[key].text, story.slots[key].entities = "", []
                    story.slots[key].locked = True

    def reroll_lore(self, item, keys=None):
        """Reroll the history's unlocked lines (or just the named ones)."""
        if not item.get("lore"):
            return self.make_lore(item)
        story = sg.Story.from_dict(item["lore"])
        if keys:
            for k in keys:
                if k in story.slots:
                    story.slots[k].locked = story.slots[k].edited = False
        story.settings["extra_tags"] = item_tags(item) + ["it:" + item["kind"]]
        story.settings["level"] = item["level"]
        story.settings["pack_share"] = self._flavor(item["settings"])
        self.gen.reroll(story, keys=keys)
        self._trim_lore(item, story)
        item["lore"] = story.to_dict()
        if item["settings"].get("culture", "auto") == "auto":
            item["culture"] = self._lore_culture(item) or item.get("culture", "")
        return item

    def lore_story(self, item):
        return sg.Story.from_dict(item["lore"]) if item.get("lore") else None

    # ----- names
    def _maker_name(self, item):
        """The maker's own name from the history, as long as it reads as a name."""
        lore = self.lore_story(item)
        if lore and "who" in lore.slots:
            for e in lore.slots["who"].entities:
                nm = (e.get("display") or e.get("title") or "").strip()
                if e.get("type") in ("NPC", "Faction") and nm[:1].isupper() and len(nm) <= 26:
                    return nm
        return ""

    def _name_plan(self, item, maker):
        """What the item gives its name, worked out before any pattern is rolled: the tags that let the right pattern
        lines apply (nm:fx, nm:purpose, nm:place, nm:owner, plus wd/wp/wk for a weapon and ac/am for an armor), and the
        words to roll from. Nothing here reads the secret or the false tale."""
        kind, rng = item["kind"], self.rng
        story = self.lore_story(item)
        plan = {"tags": [], "fx": None, "purpose_table": "", "purpose_text": "", "place": "", "owner": "", "head_mode": "",
                "odd": ""}
        # what it does
        slot = D.FX_NAME_SLOT.get(kind)
        if slot:
            cands = [t for t in item_tags(item) if t.startswith("fx:") and self.registry.has(f"item.name.fx.{slot}.{t[3:]}")]
            if cands:
                basic = set(D.BASE_FX.get(kind, []))
                specific = [t for t in cands if t not in basic]
                pool = specific if (specific and kind in RUNIC_KINDS) else cands     # a rune's word, not just "war"
                plan["fx"] = (slot, rng.choices(pool, weights=[1.0 if t in basic else 3.0 for t in pool], k=1)[0])
                plan["tags"].append("nm:fx")
                if kind in RUNIC_KINDS and specific:
                    plan["head_mode"] = "fx"
        # what it was made for, where, and by whom it was owned
        if story is not None:
            what = story.slots.get("what")
            key = purpose_key(what.text) if what else ""
            if key.startswith("trade:"):
                plan["purpose_text"] = titlecase(key[6:]) + "'s"
            elif key and self.registry.has(f"item.name.purpose.{key}"):
                plan["purpose_table"] = f"item.name.purpose.{key}"
            if plan["purpose_text"] or plan["purpose_table"]:
                plan["tags"].append("nm:purpose")
            plan["place"] = self._place_name(story)
            if plan["place"]:
                plan["tags"].append("nm:place")
            plan["owner"] = self._owner_name(story)
            if plan["owner"]:
                plan["tags"].append("nm:owner")
        # what kind of weapon or armor it is, so a name never contradicts the base item
        name, info = _base_info(item)
        if info is not None and kind == "weapon":
            plan["tags"] += ["wd:" + info["dtype"], "wk:" + info["kind"]] + (["wp:" + info["group"]] if info["group"] else [])
            if "reach" in info["traits"]:
                plan["tags"].append("wt:reach")
        elif info is not None and kind == "armor":
            plan["tags"] += ["ac:" + info["cat"], "am:" + info["group"]]
        # the headline: what the name has to say
        style = style_key(item["settings"].get("style"))
        absurd = (part(item, "absurd") or {}).get("data") or {}
        if style == "ridiculous" and absurd.get("nw"):
            plan["head_mode"] = "absurd"                    # the absurd ability, beside the real one
            plan["tags"].append("nm:absurd")
        else:
            if kind in ("worn", "held") and effect_parts(item):
                plan["head_mode"] = "effect"
            odd = (part(item, "oddity") or {}).get("data") or {}
            if style == "whimsical" and odd.get("nw") and plan["head_mode"] == "effect":
                plan["odd"] = odd["nw"]                     # a Whimsical name carries its oddity: "Hat of Light and Fresh Bread"
                plan["tags"].append("nm:odd")
            elif plan["head_mode"]:
                plan["tags"].append("nm:head")
        return plan

    @staticmethod
    def _place_name(story):
        """A named place from the history's 'made at' line: one from your Notebook, or a setting place."""
        where = story.slots.get("where")
        if where is None or not where.text.strip():
            return ""
        for e in where.entities:
            if e.get("campaign") and e.get("type") in ("Location", "Faction") and e.get("title"):
                return re.sub(r"^The\s+", "", e["title"].strip())
        low = where.text.lower()
        for word, shown in D.PLACE_WORDS:
            if word in low:
                return shown
        return ""

    @staticmethod
    def _owner_name(story):
        """The first name of a named person in the 'notable owner' line, as a possessive: Orrin's."""
        owner = story.slots.get("owner")
        for e in (owner.entities if owner else []):
            if e.get("type") == "NPC" and e.get("title"):
                first = e["title"].split()[0]
                if first[:1].isupper() and len(first) >= 3 and first.lower() not in ("the", "and"):
                    return possessive(first)
        return ""

    def _name_vars(self, item, maker, plan, ctx):
        kind, rng = item["kind"], self.rng
        v = {"maker": possessive(maker) if maker else "", "place": plan["place"], "owner": plan["owner"], "head": "",
             "odd": plan.get("odd", "")}
        if kind in ("worn", "held"):
            v["form"] = titlecase(re.sub(r"^(pair|set) of ", "", part(item, "form")["data"]["form"]))
            main = main_effect(effect_parts(item))
            mdata = main["data"] if main else {}
            v["stem"] = mdata.get("head") or rng.choice(mdata.get("stems") or ["Quiet Hours"])      # the real ability, in plain words
        elif kind in RUNIC_KINDS:
            v["base"] = titlecase(part(item, "base")["data"]["base"])
        else:
            v["spell"] = titlecase(part(item, "spell")["data"]["spell"])
            v["kind"] = DEVICE_NOUN.get(part(item, "form")["text"], "Charm") if kind == "device" else kind.title()
        if plan["fx"]:
            slot, tag = plan["fx"]
            v[{"thing": "fxthing", "wpn": "fxwpn", "arm": "fxarm"}[slot]] = ctx.roll(f"item.name.fx.{slot}.{tag[3:]}").text
        mode = plan.get("head_mode")
        if mode == "absurd":
            v["head"] = ((part(item, "absurd") or {}).get("data") or {}).get("nw", "")
        elif mode == "fx" and plan["fx"]:
            v["head"] = v[{"thing": "fxthing", "wpn": "fxwpn", "arm": "fxarm"}[plan["fx"][0]]]
        elif mode == "effect":
            main = main_effect(effect_parts(item))
            data = main["data"] if main else {}
            v["head"] = data.get("head") or ""
            if not v["head"]:                                   # an item saved before names were literal: a word for its effect
                words = list(data.get("stems") or [])
                for t in data.get("tags") or []:
                    tbl = f"item.name.fx.thing.{t[3:]}"
                    if t.startswith("fx:") and self.registry.has(tbl):
                        words += [e["t"] for e in self.registry.entries(tbl) if not e.get("off") and "{" not in e["t"]]
                v["head"] = rng.choice(words) if words else ""
        if plan["purpose_table"]:
            v["purpose"] = ctx.roll(plan["purpose_table"]).text
        elif plan["purpose_text"]:
            v["purpose"] = plan["purpose_text"]
        return v

    def make_name(self, item, force=False):
        """A name from the name-pattern tables, in the item's culture and tone, built from what the item does, what it
        was made for, where it was made, and who owned it, so the name fits the item. Patterns are ordinary Story Forge
        entries (item.name for the general ones, item.name.<culture> for each culture), so they can be edited."""
        if item.get("name_edited") and not force:
            return item["name"]
        if item["kind"] == "grimoire" and part(item, "spells") and (part(item, "spells")["data"] or {}).get("book"):
            item["name"] = self._grimoire_name(item)
            return item["name"]
        kind, rng = item["kind"], self.rng
        maker = self._maker_name(item)
        plan = self._name_plan(item, maker)
        tags = item_tags(item) + ["it:" + kind] + (["mk:named"] if maker else []) + plan["tags"]
        if kind in BOOK_KINDS:
            tags.append("it:wand")                        # staves and grimoires use the wand name patterns ("Staff of Haste")
        culture = item.get("culture") or ""
        has_head = bool(plan.get("head_mode")) and self.registry.has("item.name.head")
        item.pop("name_head", None)
        name, last_nv = "", None
        for attempt, limit in enumerate(NAME_LIMITS):
            last = attempt == len(NAME_LIMITS) - 1
            # the head tables are not tone-strict (their patterns are plain; the tone adds a short flourish below)
            ctx = self._ctx(item["settings"], tags, strict=0.9 if has_head else 0.05, loose=0.08)
            nv = self._name_vars(item, maker, plan, ctx)
            ctx.vars.update(nv)
            last_nv = nv
            use_head = has_head and bool(nv.get("head"))
            base = "item.name.head" if use_head else "item.name"
            table = f"{base}.{culture}"
            if not (culture and self.registry.has(table)) or last:
                table = base                                        # the general patterns, or a last resort
            raw = re.sub(r"\s+", " ", ctx.roll(table).text).strip()
            words = re.findall(r"[a-z]{4,}", raw.lower())
            ok = (raw and not ctx.problems and "[?" not in raw and len(raw) <= limit and len(words) == len(set(words))
                  and (not use_head or nv["head"].lower() in raw.lower()))
            if ok or (last and raw and not ctx.problems and "[?" not in raw):
                name = raw
                if use_head and nv["head"].lower() in raw.lower():
                    item["name_head"] = nv["head"]
                    flo = self._flourish(item, tags, NAME_FLOURISH_MAX - len(raw) - 2)
                    if flo:
                        name = f"{raw}, {flo}"
                break
        if not name:                                            # a safe fallback if every table was edited away
            v = last_nv or self._name_vars(item, maker, {"fx": None, "purpose_table": "", "purpose_text": "", "place": "",
                                                          "owner": "", "head_mode": "", "odd": ""}, ctx)
            name = (f"{v['form']} of {v.get('head') or v['stem']}" if "form" in v else f"{v['kind']} of {v['spell']}" if "spell" in v
                    else v.get("head") or v["base"])
            if "form" in v and v.get("head"):
                item["name_head"] = v["head"]
        item["name"] = titlecase(name)
        return item["name"]

    def _flourish(self, item, tags, room):
        """A short flourish for the end of a name, on about a third of Weird, Light, and Grim names: ', Probably'. Grim names use
        the grim epithet for the kind of item. Returns '' when there is no flourish or it would not fit."""
        tone = item["settings"].get("tone") or "any"
        if room < 6 or self.rng.random() >= NAME_FLOURISH.get(tone, 0.0):
            return ""
        if tone == "grim":
            table = "item.name.grim.epithet." + {"worn": "worn", "held": "worn", "weapon": "weapon", "armor": "armor"}.get(item["kind"], "cons")
        else:
            table = f"item.name.flourish.{tone}"
        if not self.registry.has(table):
            return ""
        text = re.sub(r"\s+", " ", self._ctx(item["settings"], tags, strict=1.0, loose=0.08).roll(table).text).strip()
        return text if text and "[?" not in text and len(text) <= room else ""

    def _grimoire_name(self, item):
        """Named for its owner ("Vellora's Almanac of Cinders") or for the theme of its spells ("The Drowned Codex")."""
        owner = item.get("owner") or item["settings"].get("owner") or ""
        theme = (part(item, "spells")["data"] or {}).get("theme") or "general"
        if not self.registry.has(f"item.grim.theme.{theme}.adj"):
            theme = "general"
        tags = item_tags(item) + (["nm:owner"] if owner else [])
        absurd = style_key(item["settings"].get("style")) == "ridiculous" and ((part(item, "absurd") or {}).get("data") or {}).get("nw")
        table = "item.grim.name.absurd" if (absurd and self.registry.has("item.grim.name.absurd")) else "item.grim.name"
        item.pop("name_head", None)
        for attempt, limit in enumerate(NAME_LIMITS):
            ctx = self._ctx(item["settings"], tags, strict=0.05, loose=0.08)
            first = owner.split()[0] if owner else ""
            ctx.vars.update(owner=possessive(owner) if owner else "", ownerfirst=first, book=ctx.roll("item.grim.book").text,
                            adj=ctx.roll(f"item.grim.theme.{theme}.adj").text,
                            thing=ctx.roll(f"item.grim.theme.{theme}.thing").text, head=absurd or "")
            raw = re.sub(r"\s+", " ", ctx.roll(table).text).strip() if self.registry.has(table) else ""
            words = re.findall(r"[a-z]{4,}", raw.lower())
            tidy = len(raw) <= limit and len(words) == len(set(words))              # short, and no word twice ("The Last Last Pages")
            if raw and not ctx.problems and "[?" not in raw and (tidy or attempt == len(NAME_LIMITS) - 1):
                if absurd and table == "item.grim.name.absurd":
                    item["name_head"] = absurd
                return titlecase(raw)
        return titlecase(f"{possessive(owner)} Grimoire" if owner else "Grimoire")

    # ----- making an item
    def generate(self, kind="any", level=5, vary=0, rarity="any", role="auto", tradition="any", focus="any", themes=(),
                 env="any", tone="any", abilities=0, quirk=True, drawback=False, lore=True, packs=None,
                 use_campaign=0.5, theme_focus=DEFAULT_THEME_FOCUS, presets=None, seed=None, culture="auto", flavor=DEFAULT_FLAVOR,
                 style="standard", owner=""):
        """Roll one item. kind is any, worn, held, wand, staff, grimoire, scroll, potion, device, weapon, or armor. culture is
        auto (the maker's people, if known), none, or a culture key such as goblin; it styles the name, look, and quirk.
        style is standard, grim, whimsical, or ridiculous (see STYLES); unless you chose a tone, it also sets the tone.
        owner names who a grimoire belongs to (an NPC carrying it); without one, a grimoire gets a made-up owner."""
        if seed is not None:
            self.gen.rng = random.Random(seed)
        rng = self.rng
        if kind not in KINDS:
            kind = rng.choices(list(KIND_WEIGHT), weights=list(KIND_WEIGHT.values()), k=1)[0]
        level = clamp_level(int(level) + (rng.randint(-int(vary), int(vary)) if vary else 0))
        style = style_key(style)
        if style in STYLE_TONE and tone in (None, "", "any"):
            tone = STYLE_TONE[style]
        if kind == "grimoire":
            level = max(3, level)
        if rarity not in RARITIES:
            rarity = rng.choices(RARITIES, weights=[RARITY_WEIGHT[r] for r in RARITIES], k=1)[0]
        settings = {"kind": kind, "level": level, "vary": int(vary), "rarity": rarity, "role": role, "tradition": tradition,
                    "focus": focus, "themes": list(themes or []), "env": env, "tone": tone, "abilities": int(abilities or 0),
                    "quirk": bool(quirk), "drawback": bool(drawback), "lore": bool(lore), "packs": list(packs or ["core"]),
                    "use_campaign": float(use_campaign), "theme_focus": float(theme_focus), "flavor": float(flavor),
                    "culture": culture if (culture in D.CULTURE_INFO or culture == "none") else "auto", "style": style,
                    "owner": str(owner or "").strip()}
        c_key = settings["culture"] if settings["culture"] in D.CULTURE_INFO else ""
        if settings["culture"] == "auto" and presets and presets.get("who"):
            c_key = self._culture_of_entities(presets["who"].get("entities") or [])
        item = new_item(kind, level, rarity, settings)
        item["culture"] = c_key
        ectx = self._effect_ctx(settings, item)
        getattr(self, "_build_" + kind)(item, level, rng, ectx, focus=focus, abilities=int(abilities or 0), settings=settings)
        if tradition in D.TRADITIONS:
            item["tradition"] = tradition
        if role in ROLES and kind not in RUNIC_KINDS + CONSUMABLE_KINDS + ("wand",) + BOOK_KINDS:
            item["price_t"] = max(0.0, min(1.0, D.ROLE_T[role] + 0.07 * (len(effect_parts(item)) - 1) + rng.uniform(-0.07, 0.07)))
            item["role"], item["role_locked"] = role, True
        recompute(item)
        if lore:
            pre = presets
            if settings["culture"] in D.CULTURE_INFO and not (presets and presets.get("who")):
                pre = dict(presets or {})
                pre["who"] = self._culture_preset(settings["culture"], settings)     # a maker of that people
            self.make_lore(item, pre)
        self._decorate(item, rng, quirk, drawback)
        recompute(item)
        self.make_name(item)
        return item

    # ----- rerolling and rescaling
    def _new_spell(self, item, rng, settings):
        sp = part(item, "spell")
        kind = item["kind"]
        rank = sp["data"]["rank"] if sp else 1
        ectx = self._effect_ctx(settings)
        pred = potion_ok if kind == "potion" else None
        for _ in range(6):
            new = spell_for_rank(rng, rank, ectx["tradition"], ectx["prefer"], predicate=pred)
            if new and (new["name"] != (sp["data"]["spell"] if sp else "") or rank == 0):
                break
        new = new or spell_for_rank(rng, rank, "any", (), predicate=pred)
        sp["text"] = f"{new['name']} ({rank_phrase(new['rank'])})"
        sp["data"].update(spell=new["name"], rank=new["rank"], tags=list(new["tags"]))
        item["tradition"] = _trad_for(new, rng, ectx["tradition"]) if settings.get("tradition") not in D.TRADITIONS else item["tradition"]
        if kind == "potion":
            item["price_t"] = 0.85 if ({"fx:stealth", "fx:travel", "fx:healing"} & set(new["tags"])) else 0.5

    def reroll(self, item, keys=None):
        """Reroll the named parts, or every part that isn't locked or edited. Changing an ability also refreshes the
        item's unlocked history and, unless you named it yourself, its name."""
        if item.get("mode") == "custom":
            return item
        rng, kind, s = self.rng, item["kind"], item["settings"]
        every = keys is None
        if every:
            keys = [p["key"] for p in item["parts"] if not p["locked"] and not p["edited"]]
        else:
            for k in keys:
                p = part(item, k)
                if p:
                    p["locked"] = p["edited"] = False
        mechanical = False
        for k in keys:
            p = part(item, k)
            if p is None:
                continue
            if k.startswith("effect"):
                others = [q["data"].get("fx") for q in effect_parts(item) if q is not p]
                n = len(effect_parts(item))
                res = self._pick_effect(kind, max(1, item["level"] - 2 * (n - 1)), rng, self._effect_ctx(s, item),
                                        s.get("focus", "any"), others, s)
                if res:
                    new = self._effect_part(res, k)
                    p.update(text=new["text"], data=new["data"], edited=False)
                    mechanical = True
            elif k == "form" and kind in ("worn", "held"):
                form = self._form_for(rng, kind, [q["data"] for q in effect_parts(item)])
                fname, usage, bulk, fkind, _ = D.FORMS[form]
                p.update(text=fname, data={"form": form, "usage": usage, "bulk": bulk, "kind": fkind})
                item["usage"], item["bulk"] = usage, bulk
                mechanical = True
            elif k == "form" and kind == "device":
                name, verb = rng.choice(D.DEVICES)
                p.update(text=name, data={"form": name, "verb": verb})
            elif k in ("spell", "spells", "act1") and kind in BOOK_KINDS:
                self._rebuild_book(item, rng, s)
                mechanical = True
            elif k == "spell":
                self._new_spell(item, rng, s)
                mechanical = True
            elif k in ("drawback", "oddity", "absurd", "limit") and style_key(s.get("style")) != "standard":
                p["text"], word = self._style_roll(item, k, self._style_ctx(item))
                if k in ("oddity", "absurd"):
                    p["data"] = dict(p.get("data") or {}, nw=word)
                    mechanical = True                      # the name follows it
            elif k in ("look", "quirk", "drawback"):
                ctx = self._deco_ctx(item)
                if k == "look":
                    p["text"] = self._look_text(item, rng, ctx)
                elif k == "quirk":
                    p["text"] = ctx.roll(self._cu_table(item, "quirk", rng, 0.7)).text
                else:
                    p["text"] = ctx.roll("item.drawback").text
            elif k == "base" and kind in RUNIC_KINDS:
                self._new_base(item, rng)
                mechanical = True
            elif k.startswith("rune") and kind in RUNIC_KINDS:
                self._new_rune(item, p, rng)
                mechanical = True
        recompute(item)
        if item.get("lore") and (mechanical or every):
            self.reroll_lore(item)
        if not item["name_edited"] and (mechanical or every):
            self.make_name(item)
        return item

    def _rebuild_book(self, item, rng, settings):
        """New spells (staff) or a new activation (grimoire), keeping the item's level and its other parts."""
        keep = [p for p in item["parts"] if p["key"] not in ("spell", "spells", "act1")]
        item["parts"] = []
        getattr(self, "_build_" + item["kind"])(item, item["level"], rng, self._effect_ctx(settings), settings=settings)
        item["parts"] += keep

    def _new_base(self, item, rng):
        kind = item["kind"]
        table = D.WEAPONS if kind == "weapon" else D.ARMORS
        old = part(item, "base")["data"]["base"]
        base = pick_base(rng, kind, item.get("culture", ""), exclude=(old,))
        p = part(item, "base")
        p.update(text=base, data={"base": base, "price": table[base]["price"], "level": 0})
        ok = weapon_rune_ok if kind == "weapon" else armor_rune_ok
        runes = D.WEAPON_RUNES if kind == "weapon" else D.ARMOR_RUNES
        by_name = {r["name"]: r for r in runes}
        chosen = []
        for rp in parts_of(item, "rune"):
            r = by_name.get(rp["data"]["rune"])
            if r is not None and not ok(r, base):               # the new base can't carry this rune: swap it
                new = pick_property_rune(rng, kind, base, item["level"], chosen + [q["data"]["rune"] for q in parts_of(item, "rune")])
                if new:
                    rp.update(_rune_part(rp["key"], "Property rune", new, kind))
                else:
                    item["parts"].remove(rp)
                    continue
            chosen.append(rp["data"]["rune"])

    def _new_rune(self, item, p, rng):
        kind = item["kind"]
        base = part(item, "base")["data"]["base"]
        others = [q["data"]["rune"] for q in parts_of(item, "rune") if q is not p]
        r = pick_property_rune(rng, kind, base, max(item["level"], 3), others)
        if r:
            p.update(_rune_part(p["key"], "Property rune", r, kind))

    def rescale(self, item, level):
        """Change the item's level, redoing the numbers on every part that isn't locked or edited."""
        level = clamp_level(level)
        rng, kind, s = self.rng, item["kind"], item["settings"]
        if item.get("mode") == "custom":
            item["level"] = level
            return recompute(item)
        heads_before = effect_heads(item)
        if kind in ("worn", "held"):
            item["level"] = level
            n = len(effect_parts(item))
            each = max(1, level - 2 * (n - 1))
            used = []
            for p in effect_parts(item):
                if p["locked"] or p["edited"]:
                    used.append(p["data"].get("fx"))
                    continue
                fx, opts = p["data"].get("fx"), dict(p["data"].get("opts") or {})
                e = EFFECTS.get(fx)
                if e and e["min"] <= each <= e["max"] and kind in e["kinds"]:
                    res = e["fn"](each, rng, opts, kind, self._effect_ctx(s, item))
                else:
                    res = self._pick_effect(kind, each, rng, self._effect_ctx(s, item), s.get("focus", "any"), used, s)
                if res:
                    new = self._effect_part(res, p["key"])
                    p.update(text=new["text"], data=new["data"])
                    used.append(res["fx"])
        elif kind in ("wand", "scroll", "potion", "device"):
            sp = part(item, "spell")
            target = {"wand": (level - 1) // 2, "scroll": (level + 1) // 2, "potion": level // 2, "device": level // 2}[kind]
            target = max(1, min(9, target))
            if not (sp["locked"] or sp["edited"]) and sp["data"]["rank"] != target:
                sp["data"]["rank"] = target
                self._new_spell(item, rng, s)
        else:
            fresh = new_item(kind, level, item["rarity"], s)
            getattr(self, "_build_" + kind)(fresh, level, rng, self._effect_ctx(s, item), focus="any", abilities=0, settings=s)
            keep = {p["key"]: p for p in item["parts"] if p["locked"] or p["edited"]}
            new_parts = [keep.pop(p["key"], p) for p in fresh["parts"]] + list(keep.values())
            extra = [p for p in item["parts"] if p["key"] in ("look", "quirk", "drawback", "oddity", "absurd", "limit")]
            item["parts"] = new_parts + extra
        recompute(item)
        if effect_heads(item) != heads_before and not item.get("name_edited"):
            self.make_name(item)                              # the ability changed, so the name that says what it does must too
        if item.get("lore"):
            lore = item["lore"]
            lore.setdefault("settings", {})["level"] = item["level"]
        return item


# ---------------------------------------------------------------------------------------------- staves
def staff_list_text(listing):
    """'Cantrip Light; 1st rank Fear, Grease; 2nd rank Blur'."""
    bits = []
    if listing.get("cantrip"):
        bits.append(f"Cantrip {listing['cantrip']}")
    for r, names in sorted(listing.get("ranks", {}).items(), key=lambda kv: int(kv[0])):
        bits.append(f"{ordinal(int(r))} rank {', '.join(names)}")
    return "; ".join(bits)


def staff_act(listing):
    return {"name": "Cast a Spell", "actions": 2, "traits": ["manipulate"],
            "effect": ("You cast a spell from the staff's list, spending charges equal to its rank; its cantrip costs none. "
                       "The staff gains charges when someone prepares it during daily preparations: as many as the rank of their "
                       "highest spell slot. You can cast only spells on your spell list, of a rank you can cast. "
                       "See GM Core, Staves, for how prepared and spontaneous casters add charges.")}


# ---------------------------------------------------------------------------------------------- spell-based item text
def spell_ability(item):
    """The activation for a wand, scroll, potion, or one-use device, built from its spell."""
    sp = part(item, "spell")
    if sp is None:
        return None
    spell = spell_by_name(sp["data"]["spell"]) or {"name": sp["data"]["spell"], "blurb": "its effect", "cast": 2, "mode": "o"}
    rank = sp["data"]["rank"]
    what = f"{spell['name']} ({spell['blurb']}) at {ordinal(rank)} rank"
    kind = item["kind"]
    if kind == "wand":
        return {"name": "Cast a Spell", "actions": spell["cast"], "traits": ["manipulate"], "frequency": "once per day",
                "trigger": "", "requirements": "",
                "effect": f"You cast {what}. Casting it again the same day overcharges the wand (see the rules for wands)."}
    if kind == "scroll":
        return {"name": "Cast a Spell", "actions": spell["cast"], "traits": ["manipulate"], "frequency": "",
                "trigger": "", "requirements": "You can cast spells of the spell's tradition.",
                "effect": f"You cast {what}. The scroll is used up."}
    if kind == "potion":
        return {"name": "Drink", "actions": 1, "traits": ["manipulate"], "frequency": "", "trigger": "", "requirements": "",
                "effect": f"You gain the benefits of {what}, as if you had cast it on yourself. The potion is used up."}
    verb = part(item, "form")["data"].get("verb", "use it")
    return {"name": sg.cap(verb), "actions": spell["cast"], "traits": ["manipulate"], "frequency": "", "trigger": "",
            "requirements": "", "effect": f"You cast {what}. The device is used up."}


# ---------------------------------------------------------------------------------------------- knowledge checks
TIER_ADJ = (-2, 0, 2, 5)
TIER_LABELS = ("Folk knowledge", "Workmanship and origin", "Provenance", "The secret")


def _slot_text(story, key):
    sl = story.slots.get(key) if story else None
    return sl.display() if sl is not None and sl.text.strip() else ""


def lore_skill_name(story):
    """A Lore skill that fits the item's maker or home: 'Lore (Finders Keep)', or a generic description."""
    if story:
        for key in ("who", "where"):
            sl = story.slots.get(key)
            for e in (sl.entities if sl else []):
                if e.get("campaign") and e.get("title"):
                    return f"Lore ({e['title']})"
    return "a Lore skill that fits its maker or home"


def knowledge_tiers(item):
    """What knowledge checks reveal, tier by tier. Each row: label, skills, dc, learn [(label, text)], crit_fail."""
    story = sg.Story.from_dict(item["lore"]) if item.get("lore") else None
    base = level_dc(item["level"], item["rarity"])
    trad = TRADITION_SKILL.get(item.get("tradition") or "", None)
    ident_skill = trad or "Arcana, Nature, Occultism, or Religion"
    lore = lore_skill_name(story)
    false = _slot_text(story, "false")
    fail = f"On a critical failure, you recall the wrong story: {false}" if false else ""

    def learn(*pairs):
        return [(lab, _slot_text(story, key)) for lab, key in pairs if _slot_text(story, key)]
    secret = learn(("The secret", "secret"))
    cond = _slot_text(story, "condition")
    if cond and secret:
        secret.append(("To confirm it", cond))
    rows = [
        {"label": "Identify Magic", "skills": [ident_skill], "dc": base, "adj": 0,
         "learn": [("What it does", "Its abilities, how to activate it, and what it costs to use.")],
         "crit_fail": "On a critical failure, you misread it as a different item."},
        {"label": TIER_LABELS[0], "skills": ["Society", lore], "dc": base - 2, "adj": -2,
         "learn": learn(("Made for", "what"), ("Made", "when"), ("A notable incident", "incident")), "crit_fail": fail},
        {"label": TIER_LABELS[1], "skills": ["Crafting", "Society"], "dc": base, "adj": 0,
         "learn": learn(("Made by", "who"), ("Made at", "where"), ("Maker's mark", "mark"), ("Its condition", "state")),
         "crit_fail": "On a critical failure, you judge the workmanship to be someone else's."},
        {"label": TIER_LABELS[2], "skills": ["Society", lore], "dc": base + 2, "adj": 2,
         "learn": learn(("Made because", "why"), ("A notable owner", "owner"), ("How it was lost", "fate"),
                        ("How it was found", "found")), "crit_fail": fail},
        {"label": TIER_LABELS[3], "skills": [ident_skill if trad else "Occultism", lore], "dc": base + 5, "adj": 5,
         "learn": secret, "crit_fail": ""},
    ]
    return [r for r in rows if r["learn"]]


# ---------------------------------------------------------------------------------------------- the card
def price_line(item):
    if item["kind"] in RUNIC_KINDS and item.get("mode") != "custom" and not item["price_edited"]:
        return runic_price_text(item)
    return gp_text(item["price_gp"])


def _ability_segments(text, add):
    if text.startswith("Activate"):
        head, _, rest = text.partition(" ")
        add(head + " ", "label")
        add(rest + "\n", "body")
    else:
        add(text + "\n", "body")


def knowledge_segments(item):
    """The knowledge checks as styled segments: each tier, its skills and DC, and what a success reveals."""
    segs = []
    for row in knowledge_tiers(item):
        segs.append((f"{row['label']}: ", "label", None))
        segs.append((f"{' or '.join(row['skills'])}, DC {row['dc']}\n", "body", None))
        for lab, text in row["learn"]:
            segs.append((f"    {lab}: {text}\n", "body", None))
        if row["crit_fail"]:
            segs.append((f"    {row['crit_fail']}\n", "muted", None))
    return segs


def spell_rows(add, rows):
    """A book's or staff's spells as lines of clickable names: '    1st rank: Fear, Grease (custom), Mirror Image (new)'. A name
    opens the spell's rules entry; a (new) spell, made for this book and not yet one of yours, opens from the book itself."""
    for label, entries in rows:
        add(f"    {label}: ")
        for i, e in enumerate(entries):
            add(e["name"], "body", ("newspell:" if e.get("generated") else "spell:") + e["name"])
            if e.get("custom"):
                add(" (custom)", "muted")
            elif e.get("generated"):
                add(" (new)", "muted")
            add(", " if i < len(entries) - 1 else "\n")


def card_segments(item, gm=False, header=True):
    """The item as styled segments for the app's rich-text view: (text, style, ref). header=False leaves out the name,
    traits, price, and usage lines (used when the card is saved as an item's description)."""
    segs = []

    def add(text, style="body", ref=None):
        segs.append((text, style, ref))
    if header:
        add(item["name"] + "   ", "title")
        add(f"Item {item['level']}\n", "head")
        if item.get("subtitle"):
            add(item["subtitle"] + "\n", "muted")
        if item.get("traits"):
            add("  ".join(t.upper() for t in item["traits"]) + "\n", "trait")
        add("Price ", "label")
        add(price_line(item) + "\n")
        if item.get("usage") or item.get("bulk"):
            if item.get("usage"):
                add("Usage ", "label")
                add(item["usage"] + ("; " if item.get("bulk") else "\n"))
            if item.get("bulk"):
                add("Bulk ", "label")
                add(item["bulk"] + "\n")
        add("\n")
    kind = item["kind"]
    look = part(item, "look")
    if look and look["text"]:
        add(look["text"] + "\n\n", "muted")
    rows = stat_lines(item)
    for label, text, style in rows:
        if style == "gloss":
            add(f"    {label}: ", "label")
            add(text + "\n", "muted")
        else:
            add(label + " ", "label")
            add(text + "\n")
    if rows:
        add("\n")
    if kind in RUNIC_KINDS and item.get("mode") != "custom":
        fund = [p for p in item["parts"] if p["key"] in ("potency", "striking", "resilient")]
        props = parts_of(item, "rune")
        for p in fund:
            add(p["text"] + "\n")
        for p in props:
            add(p["text"] + "\n")
    elif kind in ("wand", "scroll", "potion", "device") and item.get("mode") != "custom":
        act = spell_ability(item)
        if act:
            _ability_segments(format_act(act), add)
    for p in item["parts"]:
        if p["key"].startswith(("effect", "act")) and p["text"]:
            _ability_segments(p["text"], add)
    if kind in BOOK_KINDS and item.get("mode") != "custom":
        sp = part(item, "spells")
        sdata = (sp or {}).get("data") or {}
        if sp and sp["text"] and kind == "grimoire":
            if item.get("owner"):
                add("Owner ", "label")
                add(item["owner"] + "\n")
            add(f"{sp['label']}\n", "label")
            if sdata.get("book"):
                spell_rows(add, SG.book_rows(sdata["book"]))
            else:
                for ln in sp["text"].splitlines():
                    add("    " + ln + "\n")
            for g in sdata.get("generated") or []:
                add("A new spell written in it\n", "label")
                add(SG.spell_text(g) + "\n\n")
        elif sp and sp["text"]:
            add(f"{sp['label']}\n" if sdata.get("list") else f"{sp['label']} ", "label")
            if sdata.get("list"):
                spell_rows(add, SG.staff_rows(sdata["list"]))
            else:
                add(sp["text"] + "\n")
    style = style_key((item.get("settings") or {}).get("style"))
    for key, label in (("oddity", "Oddity"), ("absurd", "Absurd ability"), ("limit", "Limit")):
        p = part(item, key)
        if p and p["text"]:
            add(f"{label} ", "label")
            add(p["text"] + "\n")
    for key, label in (("quirk", "Quirk"), ("drawback", "Drawback")):
        p = part(item, key)
        if p and p["text"]:
            if key == "drawback":
                label = p.get("label") or label
                tail = {"standard": " (a minor cost; the GM decides when it applies)", "whimsical": " (a mild cost)"}.get(style, "")
            else:
                tail = ""
            add(f"{label} ", "label")
            add(p["text"] + tail + "\n", "muted")
    if item.get("notes"):
        add("\n" + item["notes"] + "\n", "muted")
    if gm:
        add("\n")
        add("GM notes\n", "head")
        if item.get("culture"):
            add(f"Made in the {D.culture_label(item['culture'])} style, which shaped its name, look, and quirk.\n", "muted")
        if style in STYLE_NOTE:
            add(STYLE_NOTE[style] + "\n", "muted")
        if kind in BOOK_KINDS:
            add(("Staff rules: GM Core, Staves. The spell spread is generated, not taken from a book.\n" if kind == "staff" else
                 "Grimoire rules: Secrets of Magic, Grimoires. The activation is generated, not taken from a book.\n"), "muted")
        if kind == "grimoire":
            src, known = SG.pool_info()
            add(f"Its spells come from {src}. (custom) marks one of your own spells; (new) marks a spell made for this book "
                "by the spell generator. A caster still has to Learn a Spell to add any of them to their own book.\n", "muted")
            if not known:
                add("Your rules index was built before spell traditions were stored, so this book may mix traditions. "
                    "Use Download / Update Data once to fix that.\n", "warn")
        rng_ = item.get("price_range")
        if rng_:
            add(f"Price range at level {item['level']}: {gp_text(rng_[0])} to {gp_text(rng_[1])}. "
                f"Role: {item['role']}.\n", "muted")
        story = sg.Story.from_dict(item["lore"]) if item.get("lore") else None
        if story:
            add("\nHistory (GM only)\n", "head")
            if story.summary:
                add(story.summary + "\n", "body")
            for sl in story.extras():
                add(sl.label + " ", "label")
                add(sl.display() + "\n")
            add("\nKnowledge checks\n", "head")
            segs += knowledge_segments(item)
    return segs


def segments_text(segs):
    return "".join(t for t, s, r in segs).rstrip() + "\n"


def card_text(item, gm=False, header=True):
    return segments_text(card_segments(item, gm, header))


# ---------------------------------------------------------------------------------------------- editing helpers
def edit_part(item, key, text):
    p = part(item, key)
    if p is not None:
        p["text"] = text.strip()
        p["edited"] = True
    return item


def set_price(item, gp):
    item["price_gp"] = round(float(gp), 2)
    item["price_edited"] = True
    return item


def clear_price_edit(item):
    item["price_edited"] = False
    return recompute(item)


def set_rarity(item, rarity):
    if rarity in RARITIES:
        item["rarity"] = rarity
        item["traits"] = item_traits(item)
    return item


# ---------------------------------------------------------------------------------------------- saving the item elsewhere
def to_custom_item(item, source="Magic Item Generator"):
    """A models.Item for Custom Content, so Treasure and Shops can use it."""
    try:
        from .models import Item
    except ImportError:
        from models import Item
    notes = card_text(item, gm=False, header=False).strip()
    traits = [t for t in item["traits"] if t not in RARITIES]
    if "magical" not in traits:                       # an item with only a tradition trait would not look magical to filters
        traits.append("magical")
    # a runic weapon or armor is a weapon or armor, as in the Foundry data, so shops and filters sort it correctly
    item_type = item["kind"] if item["kind"] in RUNIC_KINDS else ("consumable" if item["consumable"] else "equipment")
    return Item(name=item["name"], level=item["level"], rarity=item["rarity"],
                traits=traits, item_type=item_type,
                price_gp=float(item["price_gp"]), consumable=bool(item["consumable"]), magical=True, source=source,
                notes=notes, custom=True, system="pf")


def _link_titles(text, titles):
    for t in sorted(titles, key=len, reverse=True):
        if t and f"[[{t}" not in text:
            m = re.search(r"(?<!\[)\b" + re.escape(t) + r"\b", text, re.IGNORECASE)
            if m:
                shown = m.group(0)
                text = text[:m.start()] + (f"[[{t}]]" if shown == t else f"[[{t}|{shown}]]") + text[m.end():]
    return text


def to_page(item, existing_titles=()):
    """Fields for a Notebook Item page. The history sits under a GM ONLY marker; the page keeps the full item so it can
    be reopened. Campaign names that have a page are linked."""
    existing = {t for t in existing_titles}
    story = sg.Story.from_dict(item["lore"]) if item.get("lore") else None
    campaign = {e["title"] for sl in (story.slots.values() if story else []) for e in sl.entities
                if e.get("campaign") and e.get("title") in existing}
    player = card_text(item, gm=False).strip()
    body = player
    gm = card_text(item, gm=True).split("GM notes", 1)
    if len(gm) == 2:
        body += "\n\nGM ONLY:\nGM notes" + gm[1].rstrip()
    body = _link_titles(body, campaign)
    return {"title": item["name"], "type": "Item", "status": "", "tags": ["item", item["kind"]], "body": body,
            "magic_item": copy.deepcopy(item)}


def export_markdown(item, gm=True):
    """The item as Markdown: a heading, then the card (with the GM notes if gm)."""
    body = card_text(item, gm=gm).split("\n", 1)[1]
    return f"# {item['name']}\n\n*Item {item['level']}*\n\n{body}"


# ---------------------------------------------------------------------------------------------- custom items
FX_WORDS = {"fx:stealth": ("invisible", "stealth", "unseen", "sneak", "hide"), "fx:travel": ("fly", "speed", "climb", "travel", "jump", "swim"),
            "fx:healing": ("heal", "hit points", "recover", "cure"), "fx:light": ("light", "glow", "dark"),
            "fx:war": ("damage", "strike", "attack", "weapon"), "fx:protection": ("resist", "ward", "shield", "armor", "protect"),
            "fx:knowledge": ("know", "lore", "identify", "recall", "sense"), "fx:social": ("persuade", "diplomacy", "charm", "deceive", "lie"),
            "fx:craft": ("craft", "repair", "build", "mend"), "fx:control": ("slow", "paralyze", "stun", "bind"),
            "fx:magic": ("spell", "magic", "arcane", "cast")}


def guess_fx_tags(text):
    low = str(text or "").lower()
    return [fx for fx, words in FX_WORDS.items() if any(w in low for w in words)]


def custom_item(name, kind="worn", level=3, rarity="common", price_gp=None, traits=(), usage="", bulk="L", effect="",
                activations=(), look="", notes="", role="secondary", base=""):
    """A hand-built item. Activations are dicts with name, actions, traits, frequency, trigger, requirements, effect.
    For a weapon or armor, base names the base item (such as 'longsword' or 'chain mail') so its stats are shown."""
    kind = kind if kind in KINDS else "worn"
    item = new_item(kind, clamp_level(level), rarity if rarity in RARITIES else "common", {})
    table = D.WEAPONS if kind == "weapon" else D.ARMORS if kind == "armor" else {}
    base = str(base or "").strip().lower()
    if base in table:
        item["parts"].append(_fixed_part("base", "Weapon" if kind == "weapon" else "Armor", base,
                                         {"base": base, "price": table[base]["price"], "level": 0}))
        usage = usage or f"etched onto {item_noun(kind, base)}"
        bulk = str(table[base]["bulk"]) if bulk in ("", "L", None) else bulk
    item.update(mode="custom", name=str(name).strip() or "Unnamed item", name_edited=True, usage=usage, bulk=bulk,
                traits=list(traits), notes=notes, role=role if role in ROLES else "secondary", role_locked=True)
    if look:
        item["parts"].append(_fixed_part("look", "Appearance", look.strip()))
    if str(effect).strip():
        item["parts"].append(_fixed_part("effect", "Effects", effect.strip(), {"fx": "custom", "tags": guess_fx_tags(effect)}))
    for i, act in enumerate(activations, 1):
        act = dict(act)
        act.setdefault("traits", [])
        item["parts"].append(_fixed_part(f"act{i}", "Activation", format_act(act),
                                         {"fx": "custom", "act": act, "tags": guess_fx_tags(act.get("effect", ""))}))
    item["settings"] = {"packs": ["core"], "use_campaign": 0.5, "fx_tags": guess_fx_tags(" ".join(p["text"] for p in item["parts"]))}
    if price_gp is None:
        item["price_t"] = D.ROLE_T[item["role"]]
        item["price_gp"] = place_price(item["level"], item["consumable"], item["price_t"])
    else:
        item["price_gp"], item["price_edited"] = round(float(price_gp), 2), True
    return recompute(item)


def update_custom(item, **fields):
    """Apply form fields to a custom item and rebuild its parts."""
    _bp = part(item, "base")
    new = custom_item(fields.get("name", item["name"]), fields.get("kind", item["kind"]), fields.get("level", item["level"]),
                      fields.get("rarity", item["rarity"]), fields.get("price_gp"), fields.get("traits", item["traits"]),
                      fields.get("usage", item["usage"]), fields.get("bulk", item["bulk"]), fields.get("effect", ""),
                      fields.get("activations", ()), fields.get("look", ""), fields.get("notes", item.get("notes", "")),
                      fields.get("role", item["role"]), fields.get("base", _bp["data"]["base"] if _bp else ""))
    new["id"], new["created"], new["lore"] = item["id"], item["created"], item.get("lore")
    return new


# ---------------------------------------------------------------------------------------------- checks
def check_item(item):
    """Balance notes for an item (generated or hand-built): [(severity, message)], severity is ok, note, or warn."""
    out = []
    level, kind = item["level"], item["kind"]
    consumable = item["consumable"]
    texts = " ".join(p["text"] for p in item["parts"] if p["key"].startswith(("effect", "act", "spell", "rune", "potency")))
    if not 1 <= level <= 20:
        out.append(("warn", f"Level {level} is outside the 1 to 20 range the price tables cover."))
        return out
    lo, hi = price_range(level, consumable)
    if kind in RUNIC_KINDS and item.get("mode") != "custom":
        out.append(("ok", "Price is the sum of the base item and its runes, as the rune tables set it."))
    else:
        gp = float(item["price_gp"])
        if lo <= gp <= hi:
            pos = 0 if hi == lo else int(round(100 * (gp - lo) / (hi - lo)))
            out.append(("ok", f"Price {gp_text(gp)} is inside the GM Core range for level {level} ({gp_text(lo)} to {gp_text(hi)}), "
                              f"{pos}% of the way up."))
        else:
            sev = "warn" if gp < lo * 0.6 or gp > hi * 1.6 else "note"
            out.append((sev, f"Price {gp_text(gp)} is outside the GM Core range for level {level} ({gp_text(lo)} to {gp_text(hi)})."))
    allowed = skill_bonus(level)
    for m in re.finditer(r"\+(\d) item bonus", texts):
        n = int(m.group(1))
        if n > max(allowed, 1) and kind not in RUNIC_KINDS:
            out.append(("warn", f"A +{n} item bonus is above the usual curve at level {level} (skill items are +1 from level 3, "
                                f"+2 from level 9, +3 from level 17)."))
    for m in re.finditer(r"(?<!heightened to )(\d+)(?:st|nd|rd|th)(?:[- ]rank| rank)", texts):
        r = int(m.group(1))
        cap = {"scroll": (level + 1) // 2, "potion": level // 2, "device": level // 2, "wand": (level - 1) // 2,
               "staff": (level - 1) // 2, "grimoire": (level + 1) // 2}.get(
            kind, spell_rank_cap(level))
        if r > cap:
            out.append(("warn", f"It casts a {ordinal(r)}-rank spell. Items of level {level} usually cast up to {ordinal(max(cap, 1))} rank."))
    for m in re.finditer(r"resistance (\d+)", texts):
        n, cap = int(m.group(1)), (5 if level < 12 else 10 if level < 16 else 15)
        if n > cap and kind not in RUNIC_KINDS:
            out.append(("note", f"Resistance {n} is high for level {level}; energy-resistant runes give 5 at level 8 and 10 at level 12."))
    for m in re.finditer(r"\bDC (\d+)", texts):
        dc, typical = int(m.group(1)), item_dc(level)
        if abs(dc - typical) > 3:
            out.append(("note", f"DC {dc} is far from the typical item DC {typical} at level {level} (narrow items run up to 2 "
                                f"higher, items that force a save run 2 lower)."))
            break
    traits = [t.lower() for t in item.get("traits") or []]
    if kind == "worn" and "invested" not in traits and item.get("mode") == "custom":
        out.append(("note", "Most worn magic items have the invested trait."))
    if consumable and "consumable" not in traits and item.get("mode") == "custom":
        out.append(("note", "A consumable item should carry the consumable trait."))
    for key, act in all_acts(item):
        if not (act.get("frequency") or consumable):
            out.append(("note", f"The activation '{act.get('name', '')}' has no frequency or cost. Most activations have one."))
    if not out or all(s == "ok" for s, _ in out):
        out.append(("ok", "Nothing stands out. Compare it to a similar official item before using it."))
    return out


def official_names(name):
    """Names an official copy of this rune might use in a data set."""
    n = str(name).strip()
    cands = [n.title(), n]
    m = re.match(r"^\+(\d) (weapon|armor) potency$", n)
    if m:
        cands.insert(0, f"{m.group(2).title()} Potency (+{m.group(1)})")
    for tier, tail in (("greater ", "Greater"), ("major ", "Major")):
        if n.startswith(tier):
            cands.insert(0, f"{n[len(tier):].title()} ({tail})")
    if n.endswith("-resistant") and not n.startswith(("greater", "major")):
        cands.insert(0, "Energy-Resistant")
    if n.startswith("greater ") and n.endswith("-resistant"):
        cands.insert(0, "Energy-Resistant (Greater)")
    return cands


def check_against_data(item, lookup):
    """Compare the item's runes with your downloaded data. lookup(name) -> (level, price_gp) or None.
    Returns {"checked": count, "problems": [messages]}."""
    checked, problems = 0, []
    for p in item["parts"]:
        d = p.get("data") or {}
        if not d.get("official"):
            continue
        found = None
        for cand in official_names(d["rune"]):
            found = lookup(cand)
            if found:
                break
        if not found:
            continue
        checked += 1
        lvl, price = found
        if int(lvl) != int(d["level"]) or abs(float(price) - float(d["price"])) > 0.5:
            problems.append(f"{titlecase(d['rune'])}: your data lists level {int(lvl)} and {gp_text(price)}; this tool used "
                            f"level {d['level']} and {gp_text(d['price'])}.")
    return {"checked": checked, "problems": problems}


def similar_items(items, level, price, consumable=False, k=5):
    """Items from your data at about the same level and price, for comparison."""
    out = []
    for it in items:
        if bool(getattr(it, "consumable", False)) != bool(consumable) or not getattr(it, "magical", True):
            continue
        if abs(int(it.level) - int(level)) > 1:
            continue
        p = float(getattr(it, "price_gp", 0) or 0)
        if p <= 0 or price <= 0 or not (price / 2.5 <= p <= price * 2.5):
            continue
        out.append((abs(math.log(p / price)) + 0.5 * abs(int(it.level) - int(level)), it))
    out.sort(key=lambda x: x[0])
    return [it for _, it in out[:k]]


def item_tags_extra(item):
    return list(item.get("settings", {}).get("fx_tags") or [])

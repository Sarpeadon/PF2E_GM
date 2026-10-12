"""Spells for grimoires, and a spell generator for the Custom Content Spells tab.

SPELL POOL. Grimoires fill their pages from the spells in your downloaded rules data (DetailsDB.spell_pool), plus your own
custom spells, which have a chance to turn up in any slot they fit (CUSTOM_CHANCE). The app hands the pool over with
set_pool(); with no data loaded, the built-in list in itemdata.SPELLS is used. Focus spells and rituals are never written
into a spellbook, and uncommon spells turn up rarely. An index built before traditions were stored has no tradition for its
spells: then any spell can go in any book until you use Download / Update Data (or Build / Rebuild Index) once.

SPELL GENERATOR. generate_spell() builds a spell in the same shape the Spells tab saves (library.spell_entry), so it can be
edited, saved, and linked like one you typed. It has a shape (area, bolt, hex, ward, utility), a theme (fire, mental...), and
a style:
  Standard     the numbers below.
  Grim         one more damage die (or a worse condition on a critical failure), paid for by a cost line.
  Whimsical    the standard numbers, plus a harmless oddity and a mild quirk.
  Ridiculous   an absurd effect, a severe limit, and a severe drawback. Off the curve on purpose.
Numbers. Area damage is the limited-use column of the GM Core Area Damage table (gmtables.AREA_DAMAGE) at the level a spell of
that rank matches (2 x rank - 1); that gives 2d6 at 1st rank and 6d6 at 3rd, as Fireball has. Everything else is tuning for
this tool, not a book rule: a single-target attack uses the same number of dice one size up (d8), a cantrip uses the
unlimited-use column at level 1 (2d4) and heightens by 1d4, a hex gives condition 1 (2 on a critical failure), and a ward
gives resistance equal to twice the rank. The wording is in the spell.* and item.grim.theme.* tables (Edit Tables).
Every generated spell also gets FLAVOR (spell_flavor): not rules, but what the spell is like to cast and to watch (its smell, taste,
sound, and feel; what the effect looks like; what is left afterward). It is built from the spell.flavor.* tables, and the effects
that have a story of their own (a utility spell, a Ridiculous one) have sentences written for them. generate_spells() makes
several at once, with different names, so you can pick the ones to keep.
"""
import random
import re

try:
    from . import itemdata as D
    from . import storygen as sg
    from .gmtables import area_damage
except ImportError:
    import itemdata as D
    import storygen as sg
    from gmtables import area_damage

TRADITIONS = ["arcane", "divine", "occult", "primal"]
STYLES = ["standard", "grim", "whimsical", "ridiculous"]
STYLE_LABELS = {"standard": "Standard", "grim": "Grim", "whimsical": "Whimsical", "ridiculous": "Ridiculous"}
STYLE_TONE = {"grim": "grim", "whimsical": "light", "ridiculous": "weird"}
CUSTOM_CHANCE = 0.15          # each slot of a grimoire that a custom spell fits takes one this often
UNCOMMON_WEIGHT = 0.08        # an uncommon spell is this likely, compared with a common one

_POOL = None


def style_key(value):
    v = str(value or "").strip().lower()
    return v if v in STYLES else "standard"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------------------------------------------------------------------------------------------- the pool
_FX_TRAITS = {"fx:fire": ["fire"], "fx:healing": ["healing"], "fx:light": ["light"], "fx:stealth": ["illusion"],
              "fx:travel": ["teleportation"], "fx:knowledge": ["mental"], "fx:social": ["mental"], "fx:control": ["mental"],
              "fx:protection": ["force"], "fx:war": ["force"]}


def builtin_pool():
    """The item generator's own short spell list, as pool entries (used when no rules data is loaded)."""
    out = []
    for s in D.SPELLS:
        traits = sorted({t for tag in s["tags"] for t in _FX_TRAITS.get(tag, [])})
        out.append({"name": s["name"], "rank": s["rank"], "traditions": list(s["traditions"]), "traits": traits,
                    "rarity": "common", "cantrip": s["rank"] == 0, "focus": False, "ritual": False, "system": "pf",
                    "source": "builtin"})
    return out


def custom_pool(lib_spells):
    """Your custom spells (the Spells tab) as pool entries. Focus spells and rituals are left out."""
    out = []
    for sp in lib_spells or []:
        kind = sp.get("spell_kind") or "Spell"
        if not sp.get("name") or kind in ("Focus", "Ritual"):
            continue
        try:
            rank = int(sp.get("rank") or 1)
        except ValueError:
            rank = 1
        out.append({"name": sp["name"], "rank": 0 if kind == "Cantrip" else rank,
                    "traditions": [t.lower() for t in sp.get("traditions") or []],
                    "traits": [str(t).lower() for t in sp.get("traits") or []], "rarity": sp.get("rarity") or "common",
                    "cantrip": kind == "Cantrip", "focus": False, "ritual": False, "system": "pf", "custom": True})
    return out


def set_pool(data_spells=None, lib_spells=None, systems=("pf",)):
    """Give grimoires their spells: the rules data's spells (DetailsDB.spell_pool()) and your custom spells."""
    global _POOL
    data = [dict(s, source="data") for s in data_spells or [] if (s.get("system") or "pf") in systems]
    _POOL = {"data": data, "custom": custom_pool(lib_spells)}


def pool_info():
    """(where the spells come from, whether traditions are known) for the GM notes."""
    p = _POOL or {}
    if p.get("data"):
        known = any(s["traditions"] for s in p["data"])
        return "your downloaded rules data", known
    return "the built-in spell list (download rules data for many more)", True


def _base():
    p = _POOL or {}
    return p.get("data") or builtin_pool()


def _usable(s, rank, tradition, trad_known):
    if s.get("focus") or s.get("ritual") or s["rank"] != rank:
        return False
    if tradition in TRADITIONS and trad_known and s.get("traditions") and tradition not in s["traditions"]:
        return False
    if tradition in TRADITIONS and trad_known and not s.get("traditions") and not s.get("custom"):
        return False
    return (s.get("rarity") or "common") in ("common", "uncommon")


def theme_of(spell):
    traits = set(spell.get("traits") or [])
    return [t for t, words in D.GRIMOIRE_THEMES.items() if traits & set(words)]


def themes_available(tradition="any", cap=9):
    """Themes with at least four spells a book of this tradition could hold."""
    base = _base()
    known = any(s.get("traditions") for s in base)
    count = {}
    for s in base:
        if s["rank"] <= cap and _usable(s, s["rank"], tradition, known):
            for t in theme_of(s):
                count[t] = count.get(t, 0) + 1
    return {t: n for t, n in count.items() if n >= 4}


def pick_spellbook(rng, cap, tradition="any", theme=""):
    """The spells written in a grimoire: {"cantrips": [entry], "ranks": {"1": [entry], ...}}, each entry {name, rank,
    custom}. Ranks run from 1 to cap. Spells that share the book's theme are favored, and your custom spells can take a slot."""
    base = _base()
    customs = (_POOL or {}).get("custom") or []
    known = any(s.get("traditions") for s in base)
    want = set(D.GRIMOIRE_THEMES.get(theme, []))
    used = set()

    def choose(rank, n):
        got = []
        for _ in range(n):
            fits = [c for c in customs if c["name"].lower() not in used and _usable(c, rank, tradition, True)]
            if fits and rng.random() < CUSTOM_CHANCE:
                c = rng.choice(fits)
            else:
                cands = [s for s in base if s["name"].lower() not in used and _usable(s, rank, tradition, known)]
                if not cands and not got:              # another tradition only when the rank would otherwise be empty
                    cands = [s for s in base if s["name"].lower() not in used and _usable(s, rank, "any", known)]
                if not cands:
                    break
                ws = [(4.0 if want & set(s.get("traits") or []) else 1.0)
                      * (UNCOMMON_WEIGHT if s.get("rarity") == "uncommon" else 1.0) for s in cands]
                c = rng.choices(cands, weights=ws, k=1)[0]
            used.add(c["name"].lower())
            got.append({"name": c["name"], "rank": rank, "custom": bool(c.get("custom"))})
        return sorted(got, key=lambda e: e["name"])

    book = {"cantrips": choose(0, rng.randint(3, 5)), "ranks": {}}
    for r in range(1, max(1, cap) + 1):
        n = rng.randint(1, 2) if r == cap else rng.randint(2, 4)
        spells = choose(r, n)
        if spells:
            book["ranks"][str(r)] = spells
    return book


def book_lines(book):
    """['Cantrips: Light, Shield', '1st rank: Fear, Grease (custom)', ...]"""
    def names(lst):
        return ", ".join(e["name"] + (" (custom)" if e.get("custom") else " (new)" if e.get("generated") else "")
                         for e in lst)
    lines = []
    if book.get("cantrips"):
        lines.append("Cantrips: " + names(book["cantrips"]))
    for r, lst in sorted(book.get("ranks", {}).items(), key=lambda kv: int(kv[0])):
        if lst:
            lines.append(f"{ordinal(int(r))} rank: " + names(lst))
    return lines


def book_rows(book):
    """[(label, [entry])] for a grimoire's spells: Cantrips, then 1st rank and so on. Each entry is {name, rank, custom?, generated?}."""
    rows = []
    if book.get("cantrips"):
        rows.append(("Cantrips", list(book["cantrips"])))
    for r, lst in sorted(book.get("ranks", {}).items(), key=lambda kv: int(kv[0])):
        if lst:
            rows.append((f"{ordinal(int(r))} rank", list(lst)))
    return rows


def staff_rows(listing):
    """[(label, [entry])] for a staff's spell list ({'cantrip': name, 'ranks': {'1': [names]}})."""
    rows = []
    if listing.get("cantrip"):
        rows.append(("Cantrip", [{"name": listing["cantrip"], "rank": 0}]))
    for r, names in sorted(listing.get("ranks", {}).items(), key=lambda kv: int(kv[0])):
        rows.append((f"{ordinal(int(r))} rank", [{"name": n, "rank": int(r)} for n in names]))
    return rows


def book_count(book):
    return len(book.get("cantrips") or []) + sum(len(v) for v in (book.get("ranks") or {}).values())


def book_traits(book):
    """Every trait of the spells in a book (for picking its theme)."""
    by = {s["name"].lower(): s for s in _base() + ((_POOL or {}).get("custom") or [])}
    out = []
    for e in (book.get("cantrips") or []) + [x for v in (book.get("ranks") or {}).values() for x in v]:
        out += list((by.get(e["name"].lower()) or {}).get("traits") or [])
    return out


# ---------------------------------------------------------------------------------------------- the generator
TRAD_DAMAGE = {"arcane": ["fire", "cold", "electricity", "acid", "force"], "divine": ["spirit", "fire", "void", "sonic"],
               "occult": ["mental", "force", "sonic", "spirit"], "primal": ["fire", "cold", "electricity", "acid", "sonic", "poison"]}
DAMAGE_THEME = {"fire": "fire", "cold": "cold", "electricity": "electricity", "acid": "acid", "force": "force",
                "spirit": "spirit", "void": "void", "sonic": "sonic", "mental": "mental", "poison": "poison"}
HEX = {"mental": ("stupefied", ["mental"]), "fear": ("frightened", ["emotion", "fear", "mental"]),
       "poison": ("sickened", ["poison"]), "void": ("enfeebled", ["void"]), "cold": ("clumsy", ["cold"]),
       "light": ("dazzled", ["light", "visual"]), "illusion": ("dazzled", ["illusion", "visual"]),
       "earth": ("clumsy", ["earth"]), "spirit": ("frightened", ["spirit", "fear"])}
TRAD_HEX = {"arcane": ["mental", "cold", "illusion"], "divine": ["fear", "light", "void", "spirit"],
            "occult": ["mental", "fear", "illusion"], "primal": ["poison", "earth", "cold"]}
SHAPES = {"area": 4, "bolt": 4, "hex": 3, "ward": 2, "utility": 2}
CANTRIP_SHAPES = {"area": 2, "bolt": 4, "utility": 3}
AREAS = [("burst", "15", "120 feet"), ("burst", "10", "60 feet"), ("cone", "30", ""), ("cone", "15", ""), ("line", "60", "")]


_HISTORY = sg.History(strength=0.25, decay=0.85, recent=14)       # remembered across spells, so a batch doesn't repeat itself


def _ctx(reg, tone, rng, tags=()):
    _HISTORY.tick()
    gen = sg.Generator(reg, campaign=sg.Campaign(), history=_HISTORY, rng=rng)
    st = {"themes": [], "env": "any", "tone": tone, "level": 1, "focus": 0.3, "use_campaign": 0.0, "packs": ["core"],
          "tone_strict": 0.5, "tone_loose": 0.0}              # tone lines (t:grim...) are used only in their own style
    return sg.Ctx(gen, st, set(tags))


def _roll(ctx, table):
    return re.sub(r"\s+", " ", ctx.roll(table).text).strip() if ctx.reg.has(table) else ""


def _rolled(ctx, table):
    """(text, tags) of a rolled line. The tags are the line's own (nw:Name_Word, th:theme, rg:30_feet ...)."""
    if not ctx.reg.has(table):
        return "", set()
    r = ctx.roll(table)
    return re.sub(r"\s+", " ", r.text).strip(), set(r.tags)


FIELD_TAGS = {"rg": "range", "tg": "targets", "du": "duration", "df": "defense"}


def effect_fields(tags):
    """The spell fields an effect line asks for, from its tags: rg:30_feet, tg:1_creature, du:1_round, df:Will, ar:burst-20."""
    out = {}
    for t in tags:
        k, _, v = t.partition(":")
        if not v:
            continue
        if k in FIELD_TAGS:
            out[FIELD_TAGS[k]] = v.replace("_", " ")
        elif k == "ar":
            kind, _, size = v.partition("-")
            out["area_type"], out["area_size"] = kind, size
    return out


def tag_value(tags, key, default=""):
    for t in sorted(tags):
        if t.startswith(key + ":"):
            return t[len(key) + 1:]
    return default


def _dice(rank, cantrip=False, die="d6"):
    """(dice, heighten step) for a spell of this rank."""
    if cantrip:
        return "2d4", "1d4"
    lvl = 2 * max(1, rank) - 1
    now = area_damage(lvl, limited=True)[0]
    nxt = area_damage(lvl + 2, limited=True)[0]
    n_now, n_next = int(now.split("d")[0]), int(nxt.split("d")[0])
    if die != "d6":
        return f"{n_now}{die}", f"{max(1, n_next - n_now)}{die}"
    return now, f"{max(1, n_next - n_now)}d6"


def _more_dice(expr, extra=1):
    n, d = expr.split("d")
    return f"{int(n) + extra}d{d}"


def generate_spell(rank=1, style="standard", tradition="any", kind="Spell", rng=None, registry=None, shape="any",
                   owner=""):
    """A new spell as a dict for the Spells tab (the fields of GUI._spell_from_form), plus style, theme, and shape.
    kind is Spell or Cantrip. tradition is arcane, divine, occult, primal, or any. The rules are in 'description' and
    'heightened'; the flavor (what it smells, sounds, and looks like) is in 'flavor'."""
    rng = rng or random.Random()
    reg = registry or sg.default_registry()
    style = style_key(style)
    cantrip = kind == "Cantrip"
    rank = 1 if cantrip else max(1, min(10, int(rank or 1)))
    trad = tradition if tradition in TRADITIONS else rng.choice(TRADITIONS)
    shapes = CANTRIP_SHAPES if cantrip else SHAPES
    shape = shape if shape in shapes else rng.choices(list(shapes), weights=list(shapes.values()), k=1)[0]
    tone = STYLE_TONE.get(style, "any")
    ctx = _ctx(reg, tone, rng)
    sp = {"name": "", "spell_kind": "Cantrip" if cantrip else "Spell", "rank": str(rank), "rarity": "common",
          "traditions": [trad], "traits": ["concentrate", "manipulate"], "cast": "2", "range": "", "area_size": "",
          "area_type": "", "targets": "", "defense": "", "duration": "", "damage": "", "damage_type": "",
          "heighten_damage": "", "heighten_interval": "1", "source": "Spell Generator", "description": "",
          "heightened": "", "flavor": "", "style": style}
    lines, theme, head, nw = [], "general", "", ""
    if style == "ridiculous":
        text, tags = _rolled(ctx, "spell.style.absurd")
        nw, theme = tag_value(tags, "nw"), tag_value(tags, "th", "general")
        sp.update(rarity="uncommon", range="30 feet")
        sp.update(effect_fields(tags))
        lines.append(text)
        lines.append("Limit " + _roll(ctx, "spell.style.limit"))
        lines.append("Drawback " + _roll(ctx, "spell.style.cost.severe"))
        lines.append("This spell is off the curve on purpose. Its limit and drawback are what pay for it.")
        shape = "absurd"
        head = nw.replace("_", " ")
    elif shape in ("area", "bolt"):
        dtype = rng.choice(TRAD_DAMAGE[trad])
        theme = DAMAGE_THEME.get(dtype, "general")
        die = "d8" if shape == "bolt" else "d6"
        dmg, step = _dice(rank, cantrip, die)
        if style == "grim":
            dmg = _more_dice(dmg)
        sp.update(damage=dmg, damage_type=dtype, heighten_damage=step, traits=sp["traits"] + [dtype])
        if shape == "area":
            atype, size, rng_ = rng.choice(AREAS[:2] if cantrip else AREAS)
            if cantrip:
                atype, size, rng_ = "burst", "5", "30 feet"
            sp.update(area_type=atype, area_size=size, range=rng_, defense="basic Reflex")
            lines.append(f"A blast of {dtype} deals {dmg} {dtype} damage to each creature in the area.")
        else:
            sp.update(range="30 feet" if cantrip else rng.choice(["30 feet", "60 feet", "120 feet"]), targets="1 creature",
                      defense="AC", traits=sp["traits"] + ["attack"])
            lines += ["Make a spell attack roll against the target's AC.",
                      "Critical Success The target takes double damage.",
                      f"Success The target takes {dmg} {dtype} damage.",
                      "Failure The spell misses."]
        sp["heightened"] = f"Heightened (+1) The damage increases by {step}."
    elif shape == "hex":
        theme = rng.choice(TRAD_HEX[trad])
        cond, traits = HEX.get(theme, ("frightened", ["mental"]))
        worse = 3 if style == "grim" else 2
        sp.update(range="30 feet", targets="1 creature", defense="Will", duration="1 minute",
                  traits=sp["traits"] + [t for t in traits if t not in sp["traits"]])
        lines += ["The target must attempt a Will save.",
                  "Critical Success The target is unaffected.",
                  f"Success The target is {cond} 1 until the end of your next turn.",
                  f"Failure The target is {cond} 1 for 1 minute.",
                  f"Critical Failure The target is {cond} {worse} for 1 minute."]
        sp["heightened"] = "Heightened (+2) You can target one more creature."
    elif shape == "ward":
        dtype = rng.choice(TRAD_DAMAGE[trad])
        theme = DAMAGE_THEME.get(dtype, "general")
        amt = 2 * rank + (2 if style == "grim" else 0)
        sp.update(range="30 feet", targets="1 willing creature", duration="10 minutes")
        lines.append(f"The target gains resistance {amt} to {dtype} damage for the duration.")
        sp["heightened"] = "Heightened (+1) The resistance increases by 2."
    else:                                                    # utility: one of the utility effects, with its own name and fields
        text, tags = _rolled(ctx, "spell.utility")
        nw, theme = tag_value(tags, "nw"), tag_value(tags, "th", "general")
        sp.update(range="30 feet", duration="1 minute" if cantrip else "")
        sp.update(effect_fields(tags))
        lines.append(text)
        head = nw.replace("_", " ")
    if style == "grim" and shape != "absurd":
        lines.append(_roll(ctx, "spell.style.cost.grim"))
        if shape in ("area", "bolt"):
            lines.append("(The cost buys one more damage die than a standard spell of this rank.)")
    if style == "whimsical":
        lines.append("Oddity " + _roll(ctx, "spell.style.oddity"))
        lines.append("Quirk " + _roll(ctx, "spell.style.cost.whimsy"))
    sp["description"] = "\n".join(x for x in lines if x)
    sp["theme"], sp["shape"] = theme, shape
    sp["flavor"] = spell_flavor(reg, rng, style, theme, shape, nw)
    sp["name"] = spell_name(ctx, theme, shape, owner, rng, head)
    return sp


def generate_spells(count, rank=1, style="standard", tradition="any", kind="Spell", rng=None, registry=None, shape="any",
                    avoid=()):
    """count different spells (different names, none in avoid). rank may be 'any' (a mix of 1 to 10, mostly low). Returns a list."""
    rng = rng or random.Random()
    taken = {str(n).lower() for n in avoid}
    out = []
    for _ in range(int(count) * 6 if count else 0):
        if len(out) >= int(count):
            break
        r = rank
        if str(rank).lower() == "any":
            r = rng.choices(range(1, 11), weights=[5, 5, 4, 4, 3, 3, 2, 2, 1, 1], k=1)[0]
        sp = generate_spell(r, style, tradition, kind, rng, registry, shape)
        if sp["name"].lower() in taken:
            continue
        taken.add(sp["name"].lower())
        out.append(sp)
    return out


# ---------------------------------------------------------------------------------------------- flavor
SENSES = ("smell", "taste", "sound", "feel")
PAIRS = [(a, b) for i, a in enumerate(SENSES) for b in SENSES[i + 1:]]
TONE_MIX = {"grim": 0.4, "whimsical": 0.4, "ridiculous": 0.55}      # how often a sense comes from the style's own lines
FLAVOR_THEMES = ("fire", "cold", "electricity", "acid", "force", "spirit", "void", "sonic", "mental", "poison", "fear", "light",
                 "illusion", "earth", "air", "travel", "general")


def _sentence(text):
    t = re.sub(r"\s+", " ", str(text)).strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else t + "."


def _pick(ctx, table, tags):
    """Roll a table with exactly these tags in play, or None when no line fits them (so an effect with no sentence of its own
    falls back to the general ones instead of borrowing someone else's)."""
    if not ctx.reg.has(table):
        return None
    ctx.tags = set(tags)
    if not any(ctx.weight(e) > 0 for e in ctx.reg.entries(table)):
        return None
    ctx.tags = set(tags)
    return re.sub(r"\s+", " ", ctx.roll(table).text).strip()


def spell_flavor(reg, rng, style, theme, shape, nw=""):
    """Flavor text for a spell: two or three sentences, and sometimes a fourth, about what it is like to cast and to watch.
    Not rules. theme picks the smells, tastes, sounds, and looks (fire, cold, mental...); shape picks how the effect is described;
    nw is the name word of a utility or Ridiculous effect, whose own sentences (spell.flavor.effect) are used when they exist."""
    tone = STYLE_TONE.get(style, "any")
    ctx = _ctx(reg, tone, rng)
    theme_table = f"spell.flavor.{theme}" if reg.has(f"spell.flavor.{theme}") else "spell.flavor.general"
    base = {"sh:" + shape}
    own = {"nw:" + nw} if nw else set()
    mix = TONE_MIX.get(style, 0.0)

    def sense(kind, table):
        return _pick(ctx, table, base | {"fv:" + kind})

    s1, s2 = rng.choice(PAIRS)
    for kind in (s1, s2):
        text = None
        if rng.random() < mix:
            text = sense(kind, "spell.flavor.general")
        ctx.vars[kind] = text or sense(kind, theme_table) or sense(kind, "spell.flavor.general") or ""
    sentences = []
    # the casting
    cast = _pick(ctx, "spell.flavor.effect", own | {"fv:cast"}) if (nw and rng.random() < 0.55) else None
    sentences.append(cast or _pick(ctx, "spell.flavor.cast", base | {"fv:" + s1, "fv:" + s2}) or "")
    # how it looks
    look = _pick(ctx, "spell.flavor.effect", own | {"fv:look"}) if nw else None
    if not look:
        ctx.vars["look"] = sense("look", theme_table) or sense("look", "spell.flavor.general") or ""
        look = _pick(ctx, "spell.flavor.look", base) if ctx.vars["look"] else ""
    sentences.append(look or "")
    # one more detail, now and then
    if rng.random() < 0.4:
        sentences.append(_pick(ctx, "spell.flavor.detail", base) or "")
    # what is left
    if rng.random() < 0.8:
        after = _pick(ctx, "spell.flavor.effect", own | {"fv:after"}) if nw else None
        if not after:
            ctx.vars["after"] = sense("after", theme_table) or sense("after", "spell.flavor.general") or ""
            after = _pick(ctx, "spell.flavor.after", base) if ctx.vars["after"] else ""
        sentences.append(after or "")
    return " ".join(x for x in (_sentence(t) for t in sentences) if x)


NOUN_SHAPE = {"area": "spell.noun.area", "bolt": "spell.noun.bolt", "hex": "spell.noun.hex", "ward": "spell.noun.ward",
              "utility": "spell.noun.utility", "absurd": "spell.noun.utility"}
SMALL_WORDS = {"of", "the", "a", "an", "and", "or", "in", "on", "for", "to", "at", "from", "by", "with"}


def _titled(name):
    return " ".join(w if (i and w.lower() in SMALL_WORDS) else w[:1].upper() + w[1:] for i, w in enumerate(name.split()))


def spell_name(ctx, theme, shape, owner, rng, head=""):
    """A name. A utility or Ridiculous spell is named for what it does (head: 'Rain of Soft Cheese'); the others for their theme
    and shape ('Crackling Storm')."""
    first = (owner or "").split()[0] if owner else ""
    if not first:
        try:
            from . import names
        except ImportError:
            import names
        first = names.make_name("Human", rng).split()[0]
    if head and ctx.reg.has("spell.name.head"):
        ctx.tags = set()
        ctx.vars.update(head=head, first=first, adj=_roll(ctx, "spell.name.head.adj"))
        name = _roll(ctx, "spell.name.head") or head
        return _titled(name)
    t = theme if ctx.reg.has(f"item.grim.theme.{theme}.adj") else "general"
    ctx.vars.update(adj=_roll(ctx, f"item.grim.theme.{t}.adj"), thing=_roll(ctx, f"item.grim.theme.{t}.thing"),
                    noun=_roll(ctx, NOUN_SHAPE.get(shape, "spell.noun.utility")), first=first)
    name = _roll(ctx, "spell.name") or f"{ctx.vars['adj']} {ctx.vars['noun']}"
    return _titled(name)


def spell_text(sp):
    """A generated spell as plain text, for a grimoire's card."""
    head = f"{sp['name']} ({'Cantrip' if sp.get('spell_kind') == 'Cantrip' else 'Spell ' + str(sp.get('rank'))})"
    bits = []
    for label, key in (("Traditions", None), ("Range", "range"), ("Targets", "targets"), ("Defense", "defense"),
                       ("Duration", "duration")):
        val = ", ".join(sp.get("traditions") or []) if key is None else sp.get(key)
        if val:
            bits.append(f"{label} {val}")
    if sp.get("area_size"):
        bits.append(f"Area {sp['area_size']}-foot {sp.get('area_type', '')}".strip())
    out = [head, "; ".join(bits)] + ([sp["flavor"]] if sp.get("flavor") else []) + sp.get("description", "").splitlines()
    if sp.get("heightened"):
        out.append(sp["heightened"])
    return "\n".join(x for x in out if x)

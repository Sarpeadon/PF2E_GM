"""NPC kit: the gear, magic items, consumables, spells, and coins that make sense for an NPC's role, people, and level.

Used by npcgen.generate (and the NPC Generator's Reroll Gear button). It does not change an NPC's numbers: Perception,
AC, saves, HP, attack, and damage still come from the level tables in gmtables.suggest(). What the kit adds is the
description of what produces them, and things the NPC carries:

  * a real base weapon and armor from the Player Core tables in itemdata.py, chosen for the role and, for goblins, elves,
    halflings, and dwarves, sometimes their own ancestry weapon (dogslicer, elven curve blade, filcher's fork, clan dagger).
    The Strike line shows that weapon's damage type and traits, plus extra damage from property runes.
  * fundamental runes (potency, striking, resilient) at the levels the rune tables use, lagging a little for a standard
    kit and matching the level for a well-equipped one, and a property rune for the well-equipped.
  * magic items made by the Magic Items generator at or below the NPC's level, styled for the NPC's people, with their
    activations added to the stat block as abilities.
  * a few consumables, level-appropriate spells for spellcasters, role gear, and coins.

  * trappings: a little money, something to eat (or oil and thread, for those who don't eat), what their work needs, a
    keepsake, and at the Grim, Whimsical, or Ridiculous style something odd. Every NPC gets trappings, whatever the
    Equipment setting. They come from the npc.trap.* tables in itemdata.py, so Edit Tables changes them.
  * a style (Standard, Grim, Whimsical, Ridiculous) passed to the Magic Items generator, so an NPC's items can carry the
    same drawbacks, oddities, and absurd abilities. Casters sometimes carry a staff, and a mage a grimoire.

Everything is optional and fails soft: if the item generator or the item data can't be loaded, the NPC is generated the
old way and a note says why.
"""
import random
import re

try:
    from . import itemdata as D
except ImportError:                      # running outside the package (tests)
    import itemdata as D

GEAR_LABELS = ["None", "Light", "Standard", "Well-equipped"]
GEAR_KEYS = {"None": "none", "Light": "light", "Standard": "standard", "Well-equipped": "well"}
GEAR_LABEL_OF = {v: k for k, v in GEAR_KEYS.items()}
ACT_GLYPH = {1: "[1]", 2: "[2]", 3: "[3]", "R": "[R]", "F": "[F]"}

# Party currency per level (GM Core Treasure by Level). An NPC carries a fraction of it.
PARTY_CURRENCY = {1: 40, 2: 70, 3: 120, 4: 200, 5: 320, 6: 500, 7: 720, 8: 1000, 9: 1400, 10: 2000, 11: 2800, 12: 4000,
                  13: 6000, 14: 9000, 15: 13000, 16: 20000, 17: 30000, 18: 48000, 19: 80000, 20: 140000}
COIN_SHARE = {"light": 0.05, "standard": 0.15, "well": 0.35}

# Roles whose weapon and armor are worth putting runes on.
RUNIC_ROLES = {"Guard", "Soldier", "Bandit", "Hunter / Scout", "Guide / Ranger", "Thief / Scavenger", "Spy / Informant"}
RUNIC_WEAPON_ROLES = {"Guard", "Soldier", "Bandit", "Hunter / Scout", "Guide / Ranger"}
# Roles that may carry their people's own weapon (a goblin guard's dogslicer).
ANCESTRY_WEAPON_ROLES = {"Guard", "Soldier", "Bandit", "Thief / Scavenger", "Hunter / Scout", "Spy / Informant",
                         "Guide / Ranger", "Commoner", "Miner / Laborer", "Artisan / Smith"}

# armor: names from itemdata.ARMORS with weights; "" is no armor (explorer's clothing).
ROLE_KITS = {
    "Guard": dict(armor={"studded leather armor": 2, "chain shirt": 2, "scale mail": 3, "chain mail": 3, "breastplate": 2},
                  melee=["spear", "halberd", "longsword", "mace", "glaive"], ranged=["crossbow"],
                  mundane=["Shield", "Rope", "Torch"], items="defense"),
    "Soldier": dict(armor={"chain mail": 3, "breastplate": 3, "scale mail": 2, "half plate": 2, "splint mail": 1},
                    melee=["longsword", "battle axe", "warhammer", "falchion", "glaive", "greatsword", "flail"],
                    ranged=["longbow", "shortbow", "crossbow"], mundane=["Shield", "Rations", "Bedroll"], items="defense"),
    "Bandit": dict(armor={"leather armor": 3, "studded leather armor": 3, "hide armor": 1, "chain shirt": 1},
                   melee=["shortsword", "rapier", "hatchet", "scimitar", "club", "dagger"],
                   ranged=["shortbow", "hand crossbow", "sling"], mundane=["Rope", "Torch"], items="skills"),
    "Thief / Scavenger": dict(armor={"leather armor": 3, "padded armor": 2, "studded leather armor": 1},
                              melee=["dagger", "shortsword", "sap", "main-gauche", "starknife"],
                              ranged=["hand crossbow", "dart", "sling"], mundane=["Thieves' Toolkit", "Rope"], items="skills"),
    "Hunter / Scout": dict(armor={"leather armor": 3, "studded leather armor": 2, "hide armor": 2},
                           melee=["hatchet", "spear", "shortsword", "dagger"], ranged=["shortbow", "longbow"],
                           mundane=["Rations", "Bedroll", "Waterskin"], items="senses"),
    "Merchant": dict(armor={"": 4, "padded armor": 1}, melee=["dagger", "club", "sap", "rapier"], ranged=[],
                     mundane=["Merchant's ledger"], items="skills"),
    "Noble": dict(armor={"": 4, "padded armor": 1, "chain shirt": 1}, melee=["rapier", "shortsword", "main-gauche"],
                  ranged=[], mundane=["Signet ring", "Fine clothing"], items="skills"),
    "Acolyte / Priest": dict(armor={"": 2, "padded armor": 2, "leather armor": 2, "scale mail": 1},
                             melee=["mace", "staff", "morningstar", "light mace"], ranged=[],
                             mundane=["Religious Symbol (Wooden)", "Healer's Toolkit"], items="spells"),
    "Cultist": dict(armor={"": 3, "padded armor": 2, "leather armor": 2}, melee=["sickle", "dagger", "light mace"],
                    ranged=[], mundane=["Religious Symbol (Wooden)", "Ritual candles"], items="spells"),
    "Mage": dict(armor={"": 5, "padded armor": 1}, melee=["staff", "dagger"], ranged=[], mundane=["Spellbook"],
                 items="spells"),
    "Scholar / Sage": dict(armor={"": 5}, melee=["dagger", "staff"], ranged=[], mundane=["Spellbook", "Writing set"],
                           items="senses"),
    "Healer": dict(armor={"": 3, "padded armor": 2, "leather armor": 1}, melee=["staff", "club", "sickle"], ranged=[],
                   mundane=["Healer's Toolkit", "Bandages"], items="skills"),
    "Entertainer": dict(armor={"": 3, "padded armor": 2, "leather armor": 1}, melee=["rapier", "shortsword", "starknife"],
                        ranged=["dart"], mundane=["Musical instrument", "Costume"], items="skills"),
    "Artisan / Smith": dict(armor={"leather armor": 3, "padded armor": 2, "hide armor": 1},
                            melee=["light hammer", "warhammer", "maul", "hatchet"], ranged=[],
                            mundane=["Artisan's Toolkit", "Leather apron"], items="skills"),
    "Commoner": dict(armor={"": 6, "padded armor": 1}, melee=["club", "dagger", "sickle", "staff"], ranged=[],
                     mundane=["Waterskin"], items="skills"),
    "Innkeeper": dict(armor={"": 6}, melee=["club", "mace", "dagger"], ranged=[], mundane=["Ring of keys", "Ledger"],
                      items="skills"),
    "Sailor / Ferryman": dict(armor={"": 3, "leather armor": 2, "padded armor": 1}, melee=["spear", "trident", "scimitar", "hatchet"],
                              ranged=[], mundane=["Rope", "Waterskin", "Lantern (Hooded)"], items="skills"),
    "Miner / Laborer": dict(armor={"": 3, "padded armor": 1, "leather armor": 1},
                            melee=["pick", "light pick", "maul", "hatchet", "greatpick"], ranged=[],
                            mundane=["Lantern (Hooded)", "Rope", "Crowbar"], items="senses"),
    "Farmer / Herder": dict(armor={"": 5, "padded armor": 1}, melee=["sickle", "hatchet", "club", "scythe", "spear"],
                            ranged=["sling"], mundane=["Waterskin", "Rope"], items="skills"),
    "Alchemist": dict(armor={"": 3, "padded armor": 2, "leather armor": 1}, melee=["dagger", "club"], ranged=[],
                      mundane=["Alchemist's Toolkit", "Formula Book"], items="skills"),
    "Spy / Informant": dict(armor={"": 2, "leather armor": 3, "padded armor": 1}, melee=["dagger", "main-gauche", "shortsword", "sap"],
                            ranged=["hand crossbow", "dart"], mundane=["Disguise Kit", "Cipher"], items="skills"),
    "Guide / Ranger": dict(armor={"leather armor": 3, "studded leather armor": 2, "hide armor": 2},
                           melee=["shortsword", "hatchet", "spear"], ranged=["shortbow", "longbow"],
                           mundane=["Climbing Kit", "Rations", "Waterskin"], items="senses"),
}
DEFAULT_KIT = ROLE_KITS["Commoner"]

CASTER_KIND = {"Mage": "Prepared", "Acolyte / Priest": "Prepared", "Healer": "Prepared", "Cultist": "Spontaneous",
               "Entertainer": "Spontaneous"}
ROLE_SPELL_TAGS = {"Mage": ("fx:war", "fx:control", "fx:protection"), "Acolyte / Priest": ("fx:healing", "fx:protection", "fx:war"),
                   "Healer": ("fx:healing", "fx:protection"), "Cultist": ("fx:control", "fx:social", "fx:war"),
                   "Entertainer": ("fx:social", "fx:stealth", "fx:control")}
ROLE_THEMES = {"Guard": ["military"], "Soldier": ["military"], "Bandit": ["crime"], "Thief / Scavenger": ["crime"],
               "Hunter / Scout": ["nature"], "Merchant": ["trade"], "Noble": ["politics"], "Acolyte / Priest": ["religion"],
               "Cultist": ["religion"], "Mage": ["magic"], "Scholar / Sage": ["mystery"], "Healer": ["disease"],
               "Entertainer": ["festival"], "Artisan / Smith": ["craft"], "Spy / Informant": ["mystery"]}


# ---------------------------------------------------------------------------------------------- small helpers
def gear_key(value):
    """'Standard', 'standard', or 'Well-equipped' -> 'standard' / 'well'. Unknown means standard; None and '' mean none."""
    if value in (None, "", False):
        return "none"
    v = str(value).strip()
    if v in GEAR_KEYS:
        return GEAR_KEYS[v]
    low = v.lower()
    return low if low in ("none", "light", "standard", "well") else ("well" if low.startswith("well") else "standard")


def culture_of(ancestry):
    try:
        return D.culture_for_text(ancestry) or ""
    except Exception:
        return ""


def _choice(rng, weights):
    names = list(weights)
    return rng.choices(names, weights=[weights[n] for n in names], k=1)[0]


def creature_traits(info):
    """A weapon's traits in the form creature stat blocks use: 'thrown 10 ft.' -> 'thrown-10', 'versatile P' ->
    'versatile-p', 'deadly d8' -> 'deadly-d8'. Ranged weapons also get range-increment and reload traits."""
    out = []
    for t in info["traits"]:
        t = t.strip().lower()
        t = re.sub(r"\s*ft\.?$", "", t)
        out.append(re.sub(r"\s+", "-", t))
    if info.get("kind") == "ranged" and info.get("range"):
        out.append(f"range-increment-{info['range']}")
        if info.get("reload"):
            out.append(f"reload-{info['reload']}")
    return out


def _cap(text):
    """Capitalize the first letter: 'staff' -> 'Staff', '+1 striking dagger' stays."""
    t = str(text)
    i = next((n for n, ch in enumerate(t) if ch.isalpha()), None)
    return t if i is None or t[:i].strip("+0123456789 ") else t[:i] + t[i].upper() + t[i + 1:]


def _titled(name):
    return " ".join(w[:1].upper() + w[1:] if w else w for w in str(name).split(" "))


# ---------------------------------------------------------------------------------------------- weapons and armor
def pick_weapon(role, culture, rng, ranged=False):
    """A base weapon name from itemdata.WEAPONS for the role (None when the role has no weapon of that kind)."""
    kit = ROLE_KITS.get(role, DEFAULT_KIT)
    names = [n for n in (kit["ranged"] if ranged else kit["melee"]) if n in D.WEAPONS]
    weights = {n: 1.0 for n in names}
    if not ranged and role in ANCESTRY_WEAPON_ROLES:
        base = sum(weights.values()) or 1.0
        for n, info in D.WEAPONS.items():
            if info.get("anc") and info["anc"] == culture:           # their own people's weapon: about 40% of the time
                weights[n] = base * 0.7
    return _choice(rng, weights) if weights else None


def pick_armor(role, level, rng):
    """A base armor name from itemdata.ARMORS, or '' for none. Heavy armor waits until the NPC is level 3 or higher."""
    kit = ROLE_KITS.get(role, DEFAULT_KIT)
    weights = {n: w for n, w in kit["armor"].items() if n == "" or (n in D.ARMORS and (D.ARMORS[n]["cat"] != "heavy" or level >= 3))}
    return _choice(rng, weights) if weights else ""


def _tier(table, level):
    """Highest tier (1 to 3) whose rune level is at or below the given level, else 0."""
    best = 0
    for tier, row in table.items():
        if row[1] <= level:
            best = max(best, tier)
    return best


def _prop_ok(rune, info):
    u = rune.get("uses", "any")
    if u == "melee":
        return info.get("kind") == "melee"
    if u == "thrown":
        return D.weapon_thrown(info) if hasattr(D, "weapon_thrown") else any(t.startswith("thrown") for t in info["traits"])
    return True


def weapon_runes(info, level, tier, rng, runic=True):
    """{'potency': 0-3, 'striking': 0-3, 'property': [rune dicts]} for a weapon. light: none; standard: the fundamental
    runes for a level two lower than the NPC; well: for the NPC's own level, and sometimes a property rune."""
    out = {"potency": 0, "striking": 0, "property": []}
    if not runic or tier in ("none", "light"):
        return out
    eff = level - 2 if tier == "standard" else level
    out["potency"] = _tier(D.WEAPON_POTENCY, eff)
    out["striking"] = _tier(D.STRIKING, eff) if out["potency"] else 0
    if tier == "well" and out["potency"] and rng.random() < 0.6:
        cands = [r for r in D.WEAPON_RUNES if r["level"] <= level and _prop_ok(r, info)]
        if cands:
            out["property"].append(rng.choice(cands))
    return out


def armor_runes(level, tier, runic=True):
    out = {"potency": 0, "resilient": 0}
    if not runic or tier in ("none", "light"):
        return out
    eff = level - 2 if tier == "standard" else level
    out["potency"] = _tier(D.ARMOR_POTENCY, eff)
    out["resilient"] = _tier(D.RESILIENT, eff) if out["potency"] else 0
    return out


def weapon_display(name, runes):
    bits = []
    if runes["potency"]:
        bits.append(f"+{runes['potency']}")
    if runes["striking"]:
        bits.append(D.STRIKING[runes["striking"]][0])
    bits += [r["name"] for r in runes["property"]]
    return " ".join(bits + [name])


def armor_display(name, runes):
    if not name:
        return "Explorer's clothing"
    bits = []
    if runes["potency"]:
        bits.append(f"+{runes['potency']}")
    if runes["resilient"]:
        bits.append(D.RESILIENT[runes["resilient"]][0])
    return " ".join(bits + [name])


def strike_line(label, atk, dmg, info, runes):
    """'Dogslicer | +9 | 2d6+4 slashing, 1d6 fire | agile, finesse, goblin | ' in the creature editor's Strike format."""
    dtype = D.DAMAGE_NAMES.get(info["dtype"], "bludgeoning")
    parts = [f"{dmg} {dtype}"]
    for r in runes.get("property", []):
        if r.get("extra"):
            dd, typ, cond = r["extra"]
            parts.append(f"{dd} {typ}" + (f" {cond}" if cond else ""))
    return f"{label} | {atk:+d} | {', '.join(parts)} | {', '.join(creature_traits(info))} | "


# ---------------------------------------------------------------------------------------------- spells
def build_spells(role, spec, level, s, rng):
    """Spell entry text for a spellcasting role, with spells chosen by tradition, rank, and what the role does. Returns
    None for roles without spellcasting."""
    if not spec.get("tradition") or "spell_dc" not in s:
        return None
    trad = str(spec["tradition"]).lower()
    top = max(1, min(9, (level + 1) // 2))
    prefer = ROLE_SPELL_TAGS.get(role, ())
    pool = list(getattr(D, "SPELLS", []))
    kind = CASTER_KIND.get(role, "Spontaneous")

    def pick(rank, n, avoid):
        cands = [x for x in pool if x["rank"] == rank and trad in x["traditions"] and x["name"] not in avoid]
        if not cands:
            cands = [x for x in pool if x["rank"] == rank and x["name"] not in avoid]
        out = []
        for _ in range(min(n, len(cands))):
            ws = [1.0 + 3.0 * len(set(prefer) & set(x["tags"])) for x in cands]
            c = rng.choices(cands, weights=ws, k=1)[0]
            out.append(c["name"])
            cands = [x for x in cands if x is not c]
        return out
    taken, parts = set(), [f"{spec['tradition']} {kind} Spells DC {s['spell_dc']}, attack {s['spell_attack']:+d}"]
    ranks = [r for r in range(top, max(0, top - 3), -1) if r >= 1]
    for r in ranks:
        names = []
        if r == ranks[-1]:                                      # the role's signature spells, heightened if the rank is above 1st
            names = [n for n in spec.get("spells", []) if n not in taken][:2]
        names += pick(r, max(0, 2 - len(names)), taken | set(names))
        taken |= set(names)
        if names:
            parts.append(f"Rank {r}: {', '.join(names)}")
    cants = list(spec.get("cantrips", []))
    extra = pick(0, 1, set(cants))
    cants += extra
    if cants:
        parts.append(f"Cantrips: {', '.join(dict.fromkeys(cants))}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------------------------- items
def perm_count(level, tier):
    """How many permanent magic items (worn or held) the NPC carries."""
    base = max(0, (int(level) + 1) // 4)
    if tier == "light":
        return base // 2
    if tier == "well":
        return base + (1 if level >= 2 else 0)
    return base if tier == "standard" else 0


def consumable_count(level, tier, rng):
    if tier == "light":
        return rng.choice([0, 0, 1])
    base = 1 + int(level) // 6
    return min(4, base + (1 if tier == "well" else 0))


def _try_generate(gen, **kw):
    """Call the item generator, dropping options an older copy doesn't know about."""
    optional = ["owner", "style", "culture", "tone", "quirk", "drawback", "lore"]
    while True:
        try:
            return gen.generate(**kw)
        except TypeError:
            drop = next((k for k in optional if k in kw), None)
            if drop is None:
                raise
            kw.pop(drop)


def act_line(act, item_name):
    """An item activation as a stat block ability line: 'Cast Fear [2] (concentrate): From the Cloak. Frequency once per day; Effect ...'."""
    glyph = ACT_GLYPH.get(act.get("actions"), "[2]")
    traits = ", ".join(act.get("traits") or [])
    bits = []
    for label, key in (("Frequency", "frequency"), ("Trigger", "trigger"), ("Requirements", "requirements")):
        v = str(act.get(key) or "").strip().rstrip(".")
        if v:
            bits.append(f"{label} {v}")
    eff = str(act.get("effect") or "").strip()
    if eff:
        bits.append(f"Effect {eff}")
    name = " ".join(re.sub(r"[:\[\]\(\)\n]+", " ", str(act.get("name") or "Activate")).split()) or "Activate"
    head = f"{name} {glyph}" + (f" ({traits})" if traits else "")
    return f"{head}: From {item_name}. " + "; ".join(bits)


def item_abilities(item):
    lines = []
    try:
        from . import itemgen
    except ImportError:
        try:
            import itemgen
        except ImportError:
            return lines
    try:
        acts = [a for _, a in itemgen.all_acts(item)]
        if item.get("kind") in ("wand", "scroll", "potion", "device"):
            a = itemgen.spell_ability(item)
            if a:
                acts.append(a)
        lines += [act_line(a, item["name"]) for a in acts]
    except Exception:
        pass
    return lines


STAFF_ROLES = {"Mage": 0.45, "Acolyte / Priest": 0.4, "Healer": 0.3, "Cultist": 0.3, "Scholar / Sage": 0.2}
GRIMOIRE_ROLES = {"Mage": 0.5, "Scholar / Sage": 0.2}


def make_items(role, ancestry, level, rng, tier, tone="any", registry=None, campaign=None, culture=None, style="standard",
               owner=""):
    """(items, consumables, notes) from the Magic Items generator. Any failure gives ([], [], [note]). A caster may carry a
    staff (level 3 and up) and a mage a grimoire, in place of one of its permanent items. owner (the NPC's name) is who a
    grimoire belongs to, so the book is named for them."""
    notes = []
    if tier == "none":
        return [], [], notes
    n_perm, n_cons = perm_count(level, tier), consumable_count(level, tier, rng)
    if not (n_perm or n_cons):
        return [], [], notes
    try:
        try:
            from . import itemgen
        except ImportError:
            import itemgen
        gen = itemgen.ItemGenerator(registry, campaign=campaign, rng=rng)
    except Exception as e:
        return [], [], [f"Magic items skipped ({type(e).__name__}: {e})"]
    cult = culture if culture is not None else culture_of(ancestry)
    focus = ROLE_KITS.get(role, DEFAULT_KIT).get("items", "any")
    caster = role in CASTER_KIND
    themes = ROLE_THEMES.get(role, [])
    common = dict(vary=0, rarity="common", role="auto", tradition="any", themes=themes, tone=tone or "any", quirk=True,
                  drawback=False, lore=False, culture=cult or "none", use_campaign=0.0, style=style or "standard",
                  owner=owner or "")
    items, cons = [], []
    bump = 1.5 if tier == "well" else 1.0
    special = []
    if int(level) >= 3 and tier != "light":
        if rng.random() < min(0.9, GRIMOIRE_ROLES.get(role, 0) * bump):
            special.append("grimoire")
        if rng.random() < min(0.9, STAFF_ROLES.get(role, 0) * bump):
            special.append("staff")
    for i in range(n_perm):
        kind = special[i] if i < len(special) else \
            rng.choices(["worn", "held", "wand"], weights=[6, 2, 2 if caster else 0.4], k=1)[0]
        lvl = max(1, int(level) - rng.randint(0, 2))
        try:
            it = _try_generate(gen, kind=kind, level=lvl, focus=focus if kind in ("worn", "held") else "any",
                               abilities=0, **common)
            items.append(it)
        except Exception as e:
            notes.append(f"An item couldn't be generated ({type(e).__name__}: {e})")
    for _ in range(n_cons):
        kind = rng.choices(["potion", "scroll", "device"], weights=[5, 3 if caster else 1, 2], k=1)[0]
        lvl = max(1, int(level) - rng.randint(0, 3))
        try:
            it = _try_generate(gen, kind=kind, level=lvl, focus="any", abilities=0, **common)
            cons.append(it)
        except Exception as e:
            notes.append(f"A consumable couldn't be generated ({type(e).__name__}: {e})")
    return items, cons, notes


def coins(level, tier, rng):
    lvl = max(1, min(20, int(level)))
    raw = PARTY_CURRENCY[lvl] * COIN_SHARE.get(tier, 0.15) * rng.uniform(0.6, 1.4)
    step = 1 if raw < 20 else 5 if raw < 200 else 10 if raw < 2000 else 50
    return max(step, int(round(raw / step) * step))


# ---------------------------------------------------------------------------------------------- trappings
# How much pocket money an NPC with no equipment kit carries, by how their work pays. Tuning for this tool, not a book rule:
# (copper dice, silver dice, gold dice), each as (count, sides), scaled up a little with level.
POCKET = {"poor": ((2, 6), (0, 0), (0, 0)), "working": ((2, 6), (1, 6), (0, 0)), "wealthy": ((0, 0), (1, 10), (1, 4))}
WEALTH = {"Merchant": "wealthy", "Noble": "wealthy", "Commoner": "poor", "Farmer / Herder": "poor", "Miner / Laborer": "poor",
          "Bandit": "poor", "Thief / Scavenger": "poor", "Cultist": "poor", "Sailor / Ferryman": "poor"}
UNDERHALLOW = {"goblin", "kobold", "ratfolk", "grippli", "leshy", "arboreal", "automaton", "poppet", "awakened animal"}
NO_FOOD = {"automaton", "poppet"}
STYLE_TAG = {"grim": "s:grim", "whimsical": "s:whim", "ridiculous": "s:ridic"}
ODD_CHANCE = {"whimsical": 0.6, "ridiculous": 0.9, "grim": 0.6}


def role_tag(role):
    """'Thief / Scavenger' -> 'r:thief', 'Acolyte / Priest' -> 'r:acolyte'."""
    return "r:" + re.split(r"[\s/]+", str(role or "commoner").strip().lower())[0]


def culture_tag(ancestry):
    a = str(ancestry or "").strip().lower()
    if a == "arboreal":
        return "c:leshy"
    if a == "awakened animal":
        return "c:awakened"
    return "c:" + a.replace(" ", "-")


def pocket_money(role, level, rng):
    """A few coins for an NPC with no equipment kit, as text: '7 cp', '3 sp and 4 cp', '2 gp and 6 sp'."""
    dice = POCKET[WEALTH.get(role, "working")]
    scale = 1 + max(0, int(level)) // 4
    amounts = [sum(rng.randint(1, d) for _ in range(n)) * scale if n else 0 for n, d in dice]
    total = max(1, amounts[0] + 10 * amounts[1] + 100 * amounts[2])          # in copper, then written as coins
    gp, rest = divmod(total, 100)
    sp, cp = divmod(rest, 10)
    bits = [f"{v} {u}" for v, u in ((gp, "gp"), (sp, "sp"), (cp, "cp")) if v]
    return (", ".join(bits[:-1]) + " and " + bits[-1]) if len(bits) > 1 else bits[0]


def trappings(role, ancestry, level, rng=None, style="standard", packs=None, registry=None, env=None, coins_text=None):
    """What the NPC carries besides arms, armor, and magic: [lines]. packs decides whether the Hallowmead lines are used."""
    rng = rng or random.Random()
    try:
        try:
            from . import storygen as sg
        except ImportError:
            import storygen as sg
        reg = registry or sg.default_registry()
        packs = list(packs or ["core"])
        tags = {role_tag(role), culture_tag(ancestry)}
        anc = str(ancestry or "").strip().lower()
        if "hallowmead" in packs and anc in UNDERHALLOW:
            tags.add("uh")
        if style in STYLE_TAG:
            tags.add(STYLE_TAG[style])
        gen = sg.Generator(reg, campaign=sg.Campaign(), history=sg.History(strength=0.25, decay=0.85, recent=8), rng=rng)
        st = {"themes": [], "env": env or "any", "tone": {"grim": "grim", "whimsical": "light", "ridiculous": "weird"}.get(style, "any"),
              "level": max(1, int(level)), "focus": 0.3, "use_campaign": 0.0, "packs": packs,
              "pack_share": 0.6 if "hallowmead" in packs and anc in UNDERHALLOW else (0.2 if "hallowmead" in packs else None),
              "tone_strict": 1.0, "tone_loose": 0.3}
        ctx = sg.Ctx(gen, st, tags)

        def roll(table):
            if not reg.has(table):
                return ""
            ctx.tags = set(tags)
            return re.sub(r"\s+", " ", ctx.roll(table).text).strip()
    except Exception:
        return [coins_text or pocket_money(role, level, rng)]
    out = [coins_text or pocket_money(role, level, rng)]
    out.append(roll("npc.trap.upkeep" if anc in NO_FOOD else "npc.trap.snack"))
    tools = [roll("npc.trap.tool") for _ in range(2)]
    out += list(dict.fromkeys(t for t in tools if t))[:rng.choice([1, 1, 2])]
    if rng.random() < 0.55:
        out.append(roll("npc.trap.keepsake"))
    if style in ("whimsical", "ridiculous") and rng.random() < ODD_CHANCE[style]:
        out.append(roll("npc.trap.odd"))
    if style == "grim" and rng.random() < ODD_CHANCE["grim"]:
        out.append(roll("npc.trap.grim"))
    seen, lines = set(), []
    for x in out:
        if x and x.lower() not in seen:
            seen.add(x.lower())
            lines.append(x[:1].upper() + x[1:])
    return lines


# ---------------------------------------------------------------------------------------------- putting it together
def build_kit(role, ancestry, level, rng=None, gear="standard", tone="any", spec=None, s=None, registry=None,
              campaign=None, magic=True, style="standard", packs=None, env=None, owner=""):
    """The NPC's kit. spec is npcgen's ROLES[role]; s is gmtables.suggest() for the NPC. Returns a dict (see below).

    keys: gear, culture, armor (display), armor_base, weapon (display), weapon_base, ranged (display or ''),
          strikes (list of Strike lines), spells (text or None), items, consumables (item dicts), coins (gp),
          mundane (list), gear_lines (list), abilities (list of ability lines), trappings (list), style, notes (list of text).
    gear 'none' still gives trappings (pocket money, food, tools, a keepsake), and nothing else.
    """
    rng = rng or random.Random()
    tier = gear_key(gear)
    spec = spec or {}
    s = s or {}
    level = int(level)
    kit = {"gear": tier, "culture": culture_of(ancestry), "armor": "", "armor_base": "", "weapon": "", "weapon_base": "",
           "ranged": "", "strikes": [], "spells": None, "items": [], "consumables": [], "coins": 0, "mundane": [],
           "gear_lines": [], "abilities": [], "trappings": [], "style": style or "standard", "notes": []}
    if tier == "none":
        kit["trappings"] = trappings(role, ancestry, level, rng, kit["style"], packs, registry, env)
        return kit
    rk = ROLE_KITS.get(role, DEFAULT_KIT)
    culture = kit["culture"]
    runic_w, runic_a = role in RUNIC_WEAPON_ROLES, role in RUNIC_ROLES
    atk, dmg = s.get("attack"), s.get("damage")

    melee = pick_weapon(role, culture, rng)
    if melee:
        info = D.WEAPONS[melee]
        runes = weapon_runes(info, level, tier, rng, runic_w)
        kit.update(weapon_base=melee, weapon=_cap(weapon_display(melee, runes)))
        if atk is not None and dmg is not None:
            kit["strikes"].append(strike_line(_titled(melee), atk, dmg, info, runes))
    if rk["ranged"] and (role not in CASTER_KIND):
        rname = pick_weapon(role, culture, rng, ranged=True)
        if rname:
            info = D.WEAPONS[rname]
            runes = weapon_runes(info, level, tier, rng, runic_w and tier == "well")
            kit["ranged"] = _cap(weapon_display(rname, runes))
            if atk is not None and dmg is not None:
                kit["strikes"].append(strike_line(_titled(rname), atk - 1, dmg, info, runes))
    armor = pick_armor(role, level, rng)
    kit["armor_base"] = armor
    kit["armor"] = _cap(armor_display(armor, armor_runes(level, tier, runic_a)))
    kit["spells"] = build_spells(role, spec, level, s, rng)

    if magic:
        items, cons, notes = make_items(role, ancestry, level, rng, tier, tone, registry, campaign, culture, kit["style"],
                                        owner)
        kit["items"], kit["consumables"] = items, cons
        kit["notes"] += notes
        for it in items + cons:
            kit["abilities"] += item_abilities(it)
    kit["mundane"] = list(rk.get("mundane", []))
    if any(it.get("kind") == "grimoire" for it in kit["items"]):
        kit["mundane"] = [m for m in kit["mundane"] if m != "Spellbook"]          # the grimoire is the spellbook
    kit["coins"] = coins(level, tier, rng)
    kit["trappings"] = [t for t in trappings(role, ancestry, level, rng, kit["style"], packs, registry, env,
                                             coins_text="-")[1:]]                 # the kit's own coins replace pocket money

    lines = []
    for text in (kit["armor"], kit["weapon"], kit["ranged"]):
        if text:
            lines.append(_cap(text))
    lines += [it["name"] for it in kit["items"]] + [it["name"] for it in kit["consumables"]]
    lines += kit["mundane"] + [f"{kit['coins']} gp in coins"]
    kit["gear_lines"] = lines
    kit["notes"].append("Armor, weapons, and runes describe where the numbers come from. AC, attack, and damage "
                        "still follow the level tables.")
    return kit


def apply_kit(stats, kit, spec=None):
    """Write a kit into a creature's stats dict: Strikes, spells, abilities, the gear list, and trappings. Returns stats."""
    if kit and kit.get("trappings"):
        stats["trappings"] = "\n".join(kit["trappings"])
    else:
        stats.pop("trappings", None)
    if not kit or kit.get("gear") == "none":
        stats.pop("gear", None)
        return stats
    if kit.get("strikes"):
        stats["strikes"] = "\n".join(kit["strikes"])
    if kit.get("spells"):
        stats["spells"] = kit["spells"]
    base = (spec or {}).get("abilities", "")
    lines = [base] if base else []
    lines += kit.get("abilities", [])
    if lines:
        stats["abilities"] = "\n".join(lines)
    stats["gear"] = "\n".join(kit.get("gear_lines", []))
    return stats


def kit_text(kit, cards=False):
    """Plain text of what the NPC carries (for a Notebook page). cards=True adds each item's player card."""
    if not kit:
        return ""
    if kit.get("gear") == "none":
        return ("Carries: " + "; ".join(kit["trappings"])) if kit.get("trappings") else ""
    out = ["Equipment (" + GEAR_LABEL_OF.get(kit["gear"], kit["gear"]) + ")"]
    if kit.get("armor"):
        out.append(f"Armor: {kit['armor']}")
    for label, key in (("Weapon", "weapon"), ("Ranged", "ranged")):
        if kit.get(key):
            out.append(f"{label}: {kit[key]}")
    if kit.get("items"):
        out.append("Magic items: " + "; ".join(f"{it['name']} (level {it['level']})" for it in kit["items"]))
    if kit.get("consumables"):
        out.append("Consumables: " + "; ".join(f"{it['name']} (level {it['level']})" for it in kit["consumables"]))
    if kit.get("mundane"):
        out.append("Also carries: " + ", ".join(kit["mundane"]))
    out.append(f"Coins: {kit.get('coins', 0)} gp")
    if kit.get("trappings"):
        out.append("Carries: " + "; ".join(kit["trappings"]))
    if cards and (kit.get("items") or kit.get("consumables")):
        try:
            try:
                from . import itemgen
            except ImportError:
                import itemgen
            for it in kit["items"] + kit["consumables"]:
                out.append("")
                out.append(itemgen.card_text(it, gm=False).rstrip())
        except Exception:
            pass
    return "\n".join(out)


def kit_items(kit):
    """Every generated item in the kit (permanent first)."""
    return list((kit or {}).get("items", [])) + list((kit or {}).get("consumables", []))

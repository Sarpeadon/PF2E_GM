"""NPC generator: ancestry + role + level -> name, a layered personality, and a playable stat block.

Personalities are built from independent axes (temperament, voice, mannerism, quirk, appearance, goal, flaw,
virtue, fear, ties, beliefs, what they are doing right now, what they know, a catchphrase, background, attitude,
and a secret), each drawn from its own large table in storydata.py. A character gets the core axes plus a random
handful of the others, so two NPCs differ in shape as well as in content. Every table can be edited in the app,
and a recent-use memory makes repeats unlikely.

Stat blocks use the creature-building tables in gmtables.suggest(). Everything is editable afterward.
"""
import random
import re

try:
    from . import gmtools as gt
    from . import names as _names
    from . import storygen
    from .gmtables import suggest
    from .models import Creature
except ImportError:                           # standalone use (tests, demo)
    import gmtools as gt
    import names as _names
    import storygen
    from gmtables import suggest
    from models import Creature

DEFAULT_ANCESTRIES = list(_names.ANCESTRIES)
SMALL, TINY = _names.SMALL, _names.TINY
make_name = _names.make_name

CREATURE_TYPE = {"leshy": "plant", "skeleton": "undead", "automaton": "construct", "poppet": "construct",
                 "sprite": "fey", "conrasu": "aeon", "ghoran": "plant", "barathu": "aberration",
                 "arboreal": "plant", "awakened-animal": "animal"}
LANGUAGE = {"dwarf": "Dwarven", "elf": "Elven", "gnome": "Fey, Gnomish", "goblin": "Goblin", "halfling": "Halfling",
            "orc": "Orcish", "leshy": "Fey", "kobold": "Sakvroth", "catfolk": "Amurrun", "tengu": "Tengu",
            "ratfolk": "Ysoki", "ysoki": "Ysoki", "vesk": "Vesk", "kasatha": "Kasatha", "lashunta": "Castrovelian",
            "shirren": "Shirren", "hobgoblin": "Goblin", "gnoll": "Kholo", "kitsune": "Sakvroth",
            "lizardfolk": "Iruxi", "nagaji": "Nagaji", "fetchling": "Shadowtongue", "skeleton": "Necril"}

# ---------------------------------------------------------------------------------------------- roles
# tiers feed gmtables.suggest; skills are (name, tier); strike is (name, damage type, traits, ranged)
ROLES = {
    "Guard": dict(tiers=dict(perception="High", ac="High", fort="High", ref="Moderate", will="Low", hp="High",
                             attack="High", damage="Moderate"),
                  skills=[("Athletics", "High"), ("Intimidation", "Moderate")],
                  strike=("Spear", "piercing", ["reach-10"], False),
                  extra=("Crossbow", "piercing", ["range-increment-120"]),
                  abilities="Attack of Opportunity [R]: Trigger A creature within reach uses a manipulate or move "
                            "action, makes a ranged attack, or leaves a square during a move action. Effect Make a "
                            "melee Strike against it."),
    "Soldier": dict(tiers=dict(perception="Moderate", ac="High", fort="High", ref="Moderate", will="Moderate",
                               hp="High", attack="High", damage="High"),
                    skills=[("Athletics", "High"), ("Survival", "Moderate")],
                    strike=("Longsword", "slashing", ["versatile-p"], False),
                    extra=("Shortbow", "piercing", ["range-increment-60"]),
                    abilities="Shield Block [R]: reduce damage by the shield's Hardness."),
    "Bandit": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="Moderate", ref="High", will="Low",
                              hp="Moderate", attack="High", damage="Moderate"),
                   skills=[("Stealth", "High"), ("Intimidation", "Moderate"), ("Thievery", "Moderate")],
                   strike=("Shortsword", "piercing", ["agile", "finesse"], False),
                   extra=("Shortbow", "piercing", ["range-increment-60"]),
                   abilities="Sneak Attack: deals an extra 1d6 precision damage to off-guard creatures."),
    "Thief / Scavenger": dict(tiers=dict(perception="High", ac="Moderate", fort="Low", ref="High", will="Moderate",
                                         hp="Low", attack="Moderate", damage="Moderate"),
                              skills=[("Thievery", "High"), ("Stealth", "High"), ("Acrobatics", "Moderate")],
                              strike=("Dagger", "piercing", ["agile", "finesse", "thrown-10"], False), extra=None,
                              abilities="Scrounge [1]: finds a useful scrap, bolt, or makeshift tool nearby."),
    "Hunter / Scout": dict(tiers=dict(perception="Extreme", ac="Moderate", fort="Moderate", ref="High", will="Moderate",
                                      hp="Moderate", attack="High", damage="Moderate"),
                           skills=[("Survival", "High"), ("Stealth", "High"), ("Nature", "Moderate")],
                           strike=("Hatchet", "slashing", ["agile", "sweep"], False),
                           extra=("Longbow", "piercing", ["deadly-d10", "range-increment-100"]),
                           abilities="Hunt Prey [1]: designates one creature; gains +2 circumstance to Perception "
                                     "to Seek it and ignores the second range increment against it."),
    "Merchant": dict(tiers=dict(perception="Moderate", ac="Low", fort="Low", ref="Moderate", will="High", hp="Low",
                                attack="Low", damage="Low"),
                     skills=[("Diplomacy", "High"), ("Society", "High"), ("Deception", "Moderate"),
                             ("Lore (Mercantile)", "Extreme")], strike=("Club", "bludgeoning", [], False),
                     extra=None, abilities=""),
    "Noble": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="Low", ref="Moderate", will="High",
                             hp="Low", attack="Moderate", damage="Low"),
                  skills=[("Society", "High"), ("Diplomacy", "High"), ("Deception", "Moderate")],
                  strike=("Rapier", "piercing", ["deadly-d8", "finesse"], False), extra=None, abilities=""),
    "Acolyte / Priest": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="Moderate", ref="Low",
                                        will="High", hp="Moderate", attack="Low", damage="Low", spell="High"),
                             skills=[("Religion", "High"), ("Medicine", "Moderate"), ("Diplomacy", "Moderate")],
                             strike=("Mace", "bludgeoning", ["shove"], False), extra=None, tradition="Divine",
                             spells=["Heal", "Bless"], cantrips=["Divine Lance"], abilities=""),
    "Cultist": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="Moderate", ref="Low", will="High",
                               hp="Moderate", attack="Moderate", damage="Moderate", spell="Moderate"),
                    skills=[("Religion", "Moderate"), ("Deception", "High"), ("Intimidation", "Moderate")],
                    strike=("Sickle", "slashing", ["agile", "finesse", "trip"], False), extra=None,
                    tradition="Occult", spells=["Fear", "Harm"], cantrips=["Void Warp"], abilities=""),
    "Mage": dict(tiers=dict(perception="Moderate", ac="Low", fort="Low", ref="Moderate", will="High", hp="Low",
                            attack="Low", damage="Low", spell="High"),
                 skills=[("Arcana", "High"), ("Society", "Moderate"), ("Occultism", "Moderate")],
                 strike=("Staff", "bludgeoning", ["two-hand-d8"], False), extra=None, tradition="Arcane",
                 spells=["Force Barrage", "Mystic Armor"], cantrips=["Ignition", "Shield"], abilities=""),
    "Scholar / Sage": dict(tiers=dict(perception="High", ac="Low", fort="Low", ref="Low", will="High", hp="Low",
                                      attack="Low", damage="Low"),
                           skills=[("Arcana", "High"), ("Occultism", "High"), ("Society", "High"),
                                   ("Lore (History)", "Extreme")],
                           strike=("Dagger", "piercing", ["agile", "finesse"], False), extra=None, abilities=""),
    "Healer": dict(tiers=dict(perception="Moderate", ac="Low", fort="Moderate", ref="Low", will="High",
                              hp="Moderate", attack="Low", damage="Low", spell="Moderate"),
                   skills=[("Medicine", "Extreme"), ("Nature", "Moderate"), ("Diplomacy", "Moderate")],
                   strike=("Staff", "bludgeoning", [], False), extra=None, tradition="Primal", spells=["Heal"],
                   cantrips=["Stabilize"], abilities=""),
    "Entertainer": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="Low", ref="High", will="Moderate",
                                   hp="Low", attack="Moderate", damage="Low", spell="Moderate"),
                        skills=[("Performance", "Extreme"), ("Deception", "High"), ("Diplomacy", "Moderate")],
                        strike=("Rapier", "piercing", ["deadly-d8", "finesse"], False), extra=None,
                        tradition="Occult", spells=["Charm"], cantrips=["Daze"], abilities=""),
    "Artisan / Smith": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="High", ref="Low", will="Moderate",
                                       hp="Moderate", attack="Moderate", damage="Moderate"),
                            skills=[("Crafting", "Extreme"), ("Athletics", "Moderate"), ("Lore (Smithing)", "High")],
                            strike=("Light Hammer", "bludgeoning", ["agile", "thrown-20"], False), extra=None,
                            abilities=""),
    "Commoner": dict(tiers=dict(perception="Low", ac="Low", fort="Moderate", ref="Low", will="Low", hp="Low",
                                attack="Low", damage="Low"),
                     skills=[("Lore (Local)", "Moderate"), ("Athletics", "Low")],
                     strike=("Fist", "bludgeoning", ["agile", "nonlethal", "unarmed"], False), extra=None,
                     abilities=""),
    "Innkeeper": dict(tiers=dict(perception="High", ac="Low", fort="Moderate", ref="Low", will="Moderate",
                                 hp="Moderate", attack="Low", damage="Low"),
                      skills=[("Diplomacy", "High"), ("Society", "Moderate"), ("Lore (Local)", "High")],
                      strike=("Club", "bludgeoning", ["backswing"], False), extra=None, abilities=""),
    "Sailor / Ferryman": dict(tiers=dict(perception="Moderate", ac="Moderate", fort="High", ref="Moderate",
                                         will="Low", hp="Moderate", attack="Moderate", damage="Moderate"),
                              skills=[("Athletics", "High"), ("Survival", "Moderate"), ("Lore (Sailing)", "High")],
                              strike=("Boat Hook", "piercing", ["reach-10"], False), extra=None, abilities=""),
    "Miner / Laborer": dict(tiers=dict(perception="Low", ac="Low", fort="High", ref="Low", will="Low", hp="High",
                                       attack="Moderate", damage="Moderate"),
                            skills=[("Athletics", "High"), ("Crafting", "Moderate"), ("Lore (Mining)", "High")],
                            strike=("Pickaxe", "piercing", ["fatal-d10"], False), extra=None, abilities=""),
    "Farmer / Herder": dict(tiers=dict(perception="Moderate", ac="Low", fort="Moderate", ref="Low", will="Moderate",
                                       hp="Moderate", attack="Low", damage="Low"),
                            skills=[("Nature", "High"), ("Survival", "Moderate"), ("Lore (Farming)", "High")],
                            strike=("Sickle", "slashing", ["agile", "finesse", "trip"], False), extra=None,
                            abilities=""),
    "Alchemist": dict(tiers=dict(perception="Moderate", ac="Low", fort="Moderate", ref="Moderate", will="Moderate",
                                 hp="Low", attack="Moderate", damage="Moderate"),
                      skills=[("Crafting", "Extreme"), ("Medicine", "Moderate"), ("Arcana", "Moderate")],
                      strike=("Dagger", "piercing", ["agile", "finesse"], False), extra=None,
                      abilities="Quick Bomber [1]: draws and throws a bomb in one action."),
    "Spy / Informant": dict(tiers=dict(perception="High", ac="Moderate", fort="Low", ref="High", will="High",
                                       hp="Low", attack="Moderate", damage="Low"),
                            skills=[("Deception", "High"), ("Stealth", "High"), ("Society", "Moderate"),
                                    ("Diplomacy", "Moderate")],
                            strike=("Dagger", "piercing", ["agile", "finesse"], False), extra=None, abilities=""),
    "Guide / Ranger": dict(tiers=dict(perception="High", ac="Moderate", fort="Moderate", ref="High", will="Moderate",
                                      hp="Moderate", attack="High", damage="Moderate"),
                           skills=[("Survival", "High"), ("Nature", "High"), ("Stealth", "Moderate")],
                           strike=("Short Sword", "piercing", ["agile", "finesse"], False),
                           extra=("Shortbow", "piercing", ["range-increment-60"]), abilities=""),
}
ROLE_THEMES = {
    "Guard": ["military", "crime"], "Soldier": ["military"], "Bandit": ["crime"], "Thief / Scavenger": ["crime"],
    "Hunter / Scout": ["nature"], "Merchant": ["trade"], "Noble": ["politics", "family"],
    "Acolyte / Priest": ["religion"], "Cultist": ["religion", "undead"], "Mage": ["magic"],
    "Scholar / Sage": ["mystery", "ruin"], "Healer": ["disease", "nature"], "Entertainer": ["festival"],
    "Artisan / Smith": ["craft"], "Innkeeper": ["trade"], "Sailor / Ferryman": ["trade"], "Alchemist": ["magic", "craft"],
    "Spy / Informant": ["mystery", "politics"], "Guide / Ranger": ["nature"], "Miner / Laborer": ["craft"],
    "Farmer / Herder": ["nature"],
}


def role_slug(role):
    return re.sub(r"[^a-z0-9]+", "_", str(role).lower()).strip("_")


# ---------------------------------------------------------------------------------------------- personality
OPTIONAL_AXES = [("voice", 3), ("mannerism", 3), ("appearance", 3.5), ("flaw", 3), ("virtue", 2), ("fear", 2),
                 ("bond", 2), ("belief", 2), ("job", 3.5), ("knows", 2.5), ("catchphrase", 1.5), ("backstory", 2.5),
                 ("attitude", 2)]
FIELD_ORDER = ["demeanor", "voice", "mannerism", "appearance", "quirk", "goal", "flaw", "virtue", "fear", "bond",
               "belief", "job", "knows", "catchphrase", "backstory", "attitude", "secret"]
LABELS = {"demeanor": "Demeanor", "voice": "Voice", "mannerism": "Mannerism", "appearance": "Looks",
          "quirk": "Quirk", "goal": "Goal", "flaw": "Flaw", "virtue": "Virtue", "fear": "Fears", "bond": "Ties",
          "belief": "Believes", "job": "Right now", "knows": "Knows", "catchphrase": "Says",
          "backstory": "Background", "attitude": "Toward strangers", "secret": "Secret"}


def _cap1(text):
    t = str(text).strip()
    return t[:1].upper() + t[1:]


def _ctx(rng, themes=(), env=None, tone="any", registry=None, focus=0.35):
    gen = storygen.Generator(registry=registry, rng=rng)
    st = {"themes": list(themes), "env": env or "any", "tone": tone or "any", "level": 1, "focus": focus,
          "use_campaign": 0.0, "packs": None}
    tags = set(themes) | ({env} if env else set())
    return storygen.Ctx(gen, st, tags)


LABEL_TO_AXIS = {v: k for k, v in LABELS.items()}
LABEL_TO_AXIS["Toward the party"] = "attitude"


APPEARANCE_BY_ANCESTRY = {"automaton": "npc.appearance.construct", "poppet": "npc.appearance.poppet",
                          "arboreal": "npc.appearance.plant", "leshy": "npc.appearance.plant",
                          "awakened-animal": "npc.appearance.animal"}


def _appearance_table(ancestry):
    slug = str(ancestry or "").strip().lower().replace(" ", "-")
    return APPEARANCE_BY_ANCESTRY.get(slug, "npc.appearance")


def _roll_text(ctx, name):
    return re.sub(r"\s+", " ", ctx.roll(name).text).strip()


def _axis_text(ctx, rng, axis, role=None, faction_tier=None, ancestry=None):
    """The text for one personality axis. Used for new personalities and for rerolling a single line."""
    roll = lambda name: _roll_text(ctx, name)
    if axis == "demeanor":
        base = roll("npc.demeanor")
        mod = roll("npc.demeanor.mod") if rng.random() < 0.4 else ""
        return base + (f", {mod}" if mod else "")
    if axis == "goal":
        goal = roll("npc.goal")
        why = roll("npc.goal.why") if rng.random() < 0.55 else ""
        return goal + (f", {why}" if why else "")
    if axis == "appearance":
        look = roll(_appearance_table(ancestry))
        return look + (f", wearing {roll('npc.clothing')}" if rng.random() < 0.45 else "")
    if axis == "job":
        table = f"npc.job.{role_slug(role)}" if role else "npc.job.generic"
        if not ctx.reg.has(table) or rng.random() < 0.15:
            table = "npc.job.generic"
        return roll(table)
    if axis == "attitude":
        if faction_tier:
            try:
                from . import reputation        # the faction's standing with the party sets the mood
            except ImportError:
                import reputation
            att = reputation.attitude(faction_tier, rng)
            return f"{att}: {reputation.REASON.get(faction_tier, 'they are unsure what to make of the party')}"
        return f"{ctx.roll('npc.attitude').text}: {roll('npc.attitude.why')}"
    table = {"quirk": "npc.quirk", "secret": "npc.secret", "voice": "npc.voice", "mannerism": "npc.mannerism",
             "flaw": "npc.flaw", "virtue": "npc.virtue", "fear": "npc.fear", "bond": "npc.bond",
             "belief": "npc.belief", "knows": "npc.knows", "catchphrase": "npc.catchphrase",
             "backstory": "npc.backstory"}.get(axis)
    return roll(table) if table else ""


def personality(rng=None, role=None, ancestry=None, tone="any", env=None, faction_tier=None, registry=None,
                extras=None):
    """A layered personality.

    Returns a dict with the four keys the app has always used (demeanor, motivation, quirk, secret), the other axes
    that were picked (voice, appearance, flaw, ...), and `fields`, an ordered list of (label, text) ready to show.
    `faction_tier` (a reputation tier such as 'Liked') sets the starting attitude toward the party.
    `extras` forces a number of optional axes (default: a random 3 to 5).
    """
    rng = rng or random.Random()
    storygen.DEFAULT_HISTORY.tick()
    ctx = _ctx(rng, ROLE_THEMES.get(role, []), env, tone, registry)

    n = extras if extras is not None else rng.choice([3, 3, 4, 4, 5])
    pool = list(OPTIONAL_AXES)
    chosen = []
    while pool and len(chosen) < n:
        pick = rng.choices([a for a, _ in pool], weights=[w for _, w in pool], k=1)[0]
        chosen.append(pick)
        pool = [(a, w) for a, w in pool if a != pick]
    if faction_tier and "attitude" not in chosen:
        chosen.append("attitude")

    text = {}
    for axis in ["demeanor", "goal", "quirk", "secret"] + chosen:
        text[axis] = _axis_text(ctx, rng, axis, role, faction_tier, ancestry)
    demeanor_plain = text["demeanor"]
    goal_text = text["goal"]

    p = {"base_demeanor": demeanor_plain, "goal": goal_text, "quirk": text["quirk"], "secret": text["secret"]}
    for axis in chosen:
        p[axis] = text[axis]

    # the four keys older screens read, enriched with the extra variety
    p["demeanor"] = demeanor_plain + (f"; {p['voice']}" if p.get("voice") and rng.random() < 0.6 else "")
    p["motivation"] = goal_text
    p["quirk"] = text["quirk"] + (f"; {p['mannerism']}" if p.get("mannerism") and rng.random() < 0.5 else "")
    p["secret"] = text["secret"]

    fields = []
    for axis in FIELD_ORDER:
        if axis == "goal":
            fields.append((LABELS[axis], "Wants to " + goal_text))
        elif axis in ("demeanor", "quirk", "secret"):
            fields.append((LABELS[axis], _cap1(text[axis])))
        elif p.get(axis):
            fields.append((LABELS[axis], p[axis] if axis == "catchphrase" else _cap1(p[axis])))
    if faction_tier:
        fields = [("Toward the party" if lab == "Toward strangers" else lab, txt) for lab, txt in fields]
    p["fields"] = fields
    p["axes"] = ["demeanor", "goal", "quirk", "secret"] + chosen
    p["entities"] = [e for e in ctx.slot_entities if e.get("title")]      # people and groups the text mentions
    return p


def reroll_axis(label, role=None, tone="any", env=None, faction_tier=None, registry=None, rng=None, ancestry=None):
    """New text for one personality line, given its label ('Quirk', 'Goal', 'Looks'...). Returns the full
    line text exactly as personality() would show it, or None for a label this generator doesn't make."""
    axis = LABEL_TO_AXIS.get(str(label).strip())
    if not axis:
        return None
    rng = rng or random.Random()
    ctx = _ctx(rng, ROLE_THEMES.get(role, []), env, tone, registry)
    out = _axis_text(ctx, rng, axis, role, faction_tier, ancestry)
    if axis == "goal":
        return "Wants to " + out
    return out if axis == "catchphrase" else _cap1(out)


def notes_from(p, ancestry="", role=""):
    """Compact notes text from a personality (used for the creature's notes field)."""
    head = f"{ancestry} {role.lower()}." if ancestry or role else ""
    body = " ".join(f"{label}: {text.rstrip('.')}." for label, text in p.get("fields", []))
    return (head + " " + body).strip()


# ---------------------------------------------------------------------------------------------- generation
def _skill_value(level, tier):
    return suggest(level, {"skill": tier})["skill"]


def _default_strikes(spec, s):
    """The role's own Strike lines (used when the NPC has no equipment kit)."""
    sname, dtype, straits, ranged = spec["strike"]
    strikes = [f"{sname} | {s['attack']:+d} | {s['damage']} {dtype} | {', '.join(straits)} | "]
    if spec.get("extra"):
        en, et, etr = spec["extra"]
        strikes.append(f"{en} | {s['attack'] - 1:+d} | {s['damage']} {et} | {', '.join(etr)} | ")
    return strikes


def _default_spells(spec, s, level):
    if not (spec.get("tradition") and "spell_dc" in s):
        return None
    rank = max(1, min(10, (level + 1) // 2))
    parts = [f"{spec['tradition']} Spontaneous Spells DC {s['spell_dc']}, attack {s['spell_attack']:+d}"]
    if spec.get("spells") and level >= 1:
        parts.append(f"Rank {rank}: {', '.join(spec['spells'])}")
    if spec.get("cantrips"):
        parts.append(f"Cantrips: {', '.join(spec['cantrips'])}")
    return "; ".join(parts)


def _npckit():
    try:
        from . import npckit
    except ImportError:
        import npckit
    return npckit


def _kit_for(role, anc, level, rng, gear, tone, spec, s, registry, campaign, style="standard", packs=None, env=None,
             owner=""):
    """An equipment kit, or a stub carrying the reason it couldn't be built. gear 'none' gives only trappings."""
    try:
        return _npckit().build_kit(role, anc, level, rng, gear=gear, tone=tone, spec=spec, s=s, registry=registry,
                                   campaign=campaign, style=style, packs=packs, env=env, owner=owner)
    except Exception as e:                                   # the NPC is still generated, just without a kit
        return {"gear": "none", "notes": [f"Equipment skipped ({type(e).__name__}: {e})"]}


def regear(creature, role, ancestry, level, gear="standard", rng=None, tone="any", registry=None, campaign=None,
           style="standard", packs=None, env=None):
    """Roll new equipment for an NPC that already exists: replaces its Strikes, spells, abilities, and gear list and
    leaves everything else alone. Returns the kit (gear 'none' restores the role's plain Strikes)."""
    rng = rng or random.Random()
    spec = ROLES.get(role) or ROLES["Commoner"]
    level = max(-1, min(24, int(level)))
    s = suggest(level, spec["tiers"])
    st = creature.stats
    st["strikes"] = "\n".join(_default_strikes(spec, s))
    plain = _default_spells(spec, s, level)
    if plain:
        st["spells"] = plain
    else:
        st.pop("spells", None)
    if spec.get("abilities"):
        st["abilities"] = spec["abilities"]
    else:
        st.pop("abilities", None)
    st.pop("gear", None)
    key = _npckit().gear_key(gear)
    kit = _kit_for(role, (ancestry or "Human").strip(), level, rng, key, tone, spec, s, registry, campaign, style, packs, env,
                   creature.name)
    _npckit().apply_kit(st, kit, spec)                 # gear 'none' writes only the trappings
    return kit


def generate(ancestry, role, level, rng=None, name=None, source="Hallowmead", system="pf", tone="any", env=None,
             faction_tier=None, registry=None, extras=None, gear="none", campaign=None, style="standard", packs=None):
    """Returns (Creature, personality). The creature is custom=True and ready to save.
    gear: 'none' (the role's plain Strikes), 'light', 'standard', or 'well': an equipment kit with a real weapon and
    armor, runes, magic items, consumables, spells, and coins (see npckit.py). The kit is also returned as p['kit'].
    Every NPC also gets trappings (pocket money, food, tools, a keepsake). style (standard, grim, whimsical, ridiculous) sets
    how odd its items and trappings are; packs (['core', 'hallowmead']) decides whether the Hallowmead lines are used."""
    rng = rng or random.Random()
    spec = ROLES.get(role) or ROLES["Commoner"]
    level = max(-1, min(24, int(level)))
    s = suggest(level, spec["tiers"])
    anc = (ancestry or "Human").strip()
    slug = anc.lower().replace(" ", "-")
    traits = [slug, CREATURE_TYPE.get(slug, "humanoid")]
    size = "tiny" if slug in TINY else "sm" if slug in SMALL else "med"
    skills = ", ".join(f"{n} {_skill_value(level, t):+d}" for n, t in spec["skills"])
    stats = {"perception": s["perception"], "fort": s["fort"], "ref": s["ref"], "will": s["will"],
             "skills": skills, "languages": ", ".join(x for x in ("Common", LANGUAGE.get(slug, "")) if x),
             "speed": "25 feet" if size in ("sm", "tiny") else "30 feet", "strikes": "\n".join(_default_strikes(spec, s))}
    if slug in ("dwarf", "elf", "goblin", "orc", "gnome", "kobold", "fetchling", "hobgoblin", "skeleton"):
        stats["senses"] = "darkvision" if slug in ("dwarf", "orc", "fetchling", "skeleton") else "low-light vision"
    plain = _default_spells(spec, s, level)
    if plain:
        stats["spells"] = plain
    if spec.get("abilities"):
        stats["abilities"] = spec["abilities"]
    key = _npckit().gear_key(gear) if gear else "none"
    nm = name or make_name(anc, rng)                    # named first, so a grimoire it carries is named for it
    kit = _kit_for(role, anc, level, rng, key, tone, spec, s, registry, campaign, style, packs, env, nm)
    _npckit().apply_kit(stats, kit, spec)              # gear 'none' writes only the trappings
    p = personality(rng, role=role, ancestry=anc, tone=tone, env=env, faction_tier=faction_tier, registry=registry,
                    extras=extras)
    p["kit"] = kit
    c = Creature(name=nm, level=level, rarity="common", traits=traits, size=size, hp=s["hp"], ac=s["ac"],
                 source=source, notes=notes_from(p, anc, role), custom=True, stats=stats, system=system)
    return c, p


# ================================================================================================ INFLUENCE
# An influence stat block for an NPC (GM Tools tab). Follows the GM Core influence subsystem: Influence and Discover results,
# resistances that add +2 DC (or +5 for stronger ones), and thresholds. Tuning, not book rules: the point totals behind the
# thresholds. The wording is in the influence.* tables (Edit Tables).
INFLUENCE_SKILLS = ["Deception", "Diplomacy", "Intimidation", "Performance", "Society", "Crafting", "Nature", "Occultism",
                    "Religion", "Acrobatics", "Athletics"]
INF_OPTIONS = [
    gt.opt("name", "NPC name", "text", "", width=26, hint="blank = made up for you"),
    gt.opt("ancestry", "Ancestry", "choice", "", [], free=True, width=16, hint="blank = random", source="ancestry"),
    gt.opt("occupation", "Role", "choice", "", [], free=True, width=24, hint="blank = random", source="occupation"),
    gt.opt("level", "Social level", "int", 3, width=5), gt.SIZE_OPT,
    gt.opt("rounds", "Rounds", "int", 6, width=4),
    gt.opt("thresholds", "Thresholds", "choice", "3", ["2", "3", "4"], width=4),
    gt.SILLY_OPT, gt.FLAVOR_OPT]


def generate_influence(params, rng=None):
    rng = rng or random.Random()
    rl = gt.Roller(rng, params["silly"], params["flavor"], params["level"])
    level = gt.clamp(params["level"], -1, 24)
    anc = params["ancestry"].strip() or gt.pick_ancestry(rng, params["flavor"])
    name = params["name"].strip() or _names.make_name(anc, rng)
    anc = anc.lower()
    occ = params["occupation"].strip() or rl.roll("occupation")
    base = gt.dc(level)
    trait = rl.roll("influence.trait")
    quirk = rl.roll("influence.quirk")
    adjs = ", ".join(rl.roll("adjective.person") for _ in range(3))
    rows = [gt.row("NPC", f"{name}, {gt.article(anc)} {anc} {occ}. Traits: {trait}.", "info"),
            gt.row("Personality", f"{adjs}. {gt.sentence(quirk)}", "flavor", table="influence.quirk", fmt=f"{adjs}. " + "{}")]
    rows.append(gt.row("Base DC", f"DC {base} (the standard DC for social level {level}). Adjust with easy -2, hard +2, very hard +5.", "info", gm=True))
    # weaknesses and resistances (each carries the skill it touches)
    weak = [rl.payload("influence.weakness") for _ in range(2)]
    res = [rl.payload("influence.resist") for _ in range(2)]
    bias = rl.roll("influence.bias")
    # influence skills, lowest DC first. Weakness skills are easy; Diplomacy is rarely the easiest (GM Core)
    skill_dc = {}
    for t, sk in weak:
        sk = sk if sk in INFLUENCE_SKILLS else "Society"
        skill_dc[sk] = min(skill_dc.get(sk, 99), base - 2)
    others = [s for s in INFLUENCE_SKILLS if s not in skill_dc and s != "Diplomacy"]
    rng.shuffle(others)
    skill_dc["Diplomacy"] = max(skill_dc.get("Diplomacy", 0), base) if "Diplomacy" in skill_dc else base
    if skill_dc["Diplomacy"] <= min(skill_dc.values()):
        skill_dc["Diplomacy"] = min(skill_dc.values()) + 2
    for s, adj in zip(others[:3], (0, 2, 5)):
        skill_dc[s] = base + adj
    for t, sk in res:                                       # resistances raise a DC by +2 (or +5 when stronger)
        if sk in skill_dc:
            skill_dc[sk] += 2
    ordered = sorted(skill_dc.items(), key=lambda kv: (kv[1], kv[0]))
    rows.append(gt.row("Influence skills", ", ".join(f"{s} DC {d}" for s, d in ordered) +
                    ". A strong narrative reason can add another skill at the highest DC listed.", "info", gm=True))
    lore = f"{anc.title()} Lore"
    rows.append(gt.row("Discovery", f"Perception DC {base}; {lore} DC {base - 2}; Society DC {base + 2}. A success reveals the lowest-DC skill not yet known, a bias, a resistance, or a weakness.", "info", gm=True))
    def _sk(sk):
        return sk if sk in skill_dc else "Society"
    rows.append(gt.row("Weaknesses", "; ".join(f"{t[0].upper() + t[1:]} (try {_sk(sk)}, DC {skill_dc[_sk(sk)]})" for t, sk in weak) + ".", "flavor", gm=True))
    rows.append(gt.row("Resistances", "; ".join(f"{t[0].upper() + t[1:]} (+2 DC to {sk}, or +5 if it is a sore point)" for t, sk in res) + ".", "flavor", gm=True))
    rows.append(gt.row("Bias", gt.sentence(bias), "flavor", gm=True, table="influence.bias", fmt="{}"))
    # thresholds
    n = int(params["thresholds"])
    target = max(n, round(params["size"] * params["rounds"] * 0.45))     # tuning: about half of all attempts earn a point
    fractions = {2: [0.5, 1.0], 3: [0.35, 0.7, 1.0], 4: [0.25, 0.5, 0.75, 1.0]}[n]
    tiers = ["influence.benefit.1", "influence.benefit.2", "influence.benefit.3"]
    pts, bits = [], []
    for i, fr in enumerate(fractions):
        p = max(i + 1, round(target * fr))
        if pts and p <= pts[-1]:
            p = pts[-1] + 1
        pts.append(p)
        tier = tiers[min(i, 2)] if n > 2 or i == n - 1 else tiers[min(i, 1) if i == 0 else 2]
        bits.append(f"{p} points: {rl.roll(tier)}")
    rows.append(gt.row("Thresholds", "; ".join(bits) + f". Tuned so {params['size']} PCs acting for {params['rounds']} rounds can reach the top with a bit of luck.", "info", gm=True))
    rows.append(gt.row("If they fail", gt.sentence(rl.roll("influence.penalty")), "flavor", gm=True, table="influence.penalty", fmt="{}"))
    rows.append(gt.row("Hidden agenda", gt.sentence(rl.roll("influence.agenda")), "flavor", gm=True, table="influence.agenda", fmt="{}"))
    rows.append(gt.row("Rules reminder", "Influence: critical success +2 points, success +1, failure 0, critical failure -1. Discover: success reveals one piece of information; critical failure reveals a false one.", "info", gm=True))
    return gt.result("influence", f"Influence: {name}", rows, params)


TOOL_INFLUENCE = {"key": "influence", "label": "Influence", "page_type": "Note", "options": INF_OPTIONS, "generate": generate_influence, "single": True,
                  "intro": "An influence stat block for an NPC: skills with DCs, weaknesses, resistances, thresholds and a hidden agenda."}

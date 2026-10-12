"""Dropdown vocabularies built from the indexed data, with sensible defaults when no data is loaded.

Everything here only feeds dropdown suggestions. Every dropdown stays editable, so typing a
completely custom value always works.
"""
import json
import os
from collections import Counter

SIZES = [("tiny", "Tiny"), ("sm", "Small"), ("med", "Medium"), ("lg", "Large"), ("huge", "Huge"), ("grg", "Gargantuan")]
SIZE_LABEL = dict(SIZES)
SIZE_CODE = {v.lower(): k for k, v in SIZES}

CREATURE_TYPES = ["aberration", "animal", "astral", "beast", "celestial", "construct", "dragon", "dream",
                  "elemental", "ethereal", "fey", "fiend", "fungus", "giant", "humanoid", "monitor", "ooze",
                  "petitioner", "plant", "shade", "spirit", "time", "undead"]

# Traits that describe mechanics rather than "what kind of creature this is".
GENERIC_TRAITS = set(CREATURE_TYPES) | {
    "common", "uncommon", "rare", "unique", "good", "evil", "lawful", "chaotic", "neutral", "holy", "unholy",
    "air", "earth", "fire", "water", "metal", "wood", "acid", "cold", "electricity", "sonic", "force", "mental",
    "poison", "void", "vitality", "positive", "negative", "aquatic", "amphibious", "mindless", "incorporeal",
    "minion", "summoned", "swarm", "troop", "magical", "arcane", "divine", "occult", "primal", "light", "shadow",
    "tiny", "small", "medium", "large", "huge", "gargantuan", "sm", "med", "lg", "grg",
}

DAMAGE_TYPES = ["acid", "bleed", "bludgeoning", "cold", "electricity", "fire", "force", "mental", "piercing",
                "poison", "precision", "slashing", "sonic", "spirit", "vitality", "void"]
SKILLS = ["Acrobatics", "Arcana", "Athletics", "Crafting", "Deception", "Diplomacy", "Intimidation", "Medicine",
          "Nature", "Occultism", "Performance", "Religion", "Society", "Stealth", "Survival", "Thievery"]
SPEED_TYPES = ["land", "burrow", "climb", "fly", "swim"]
DEFAULT_SENSES = ["darkvision", "greater darkvision", "low-light vision", "scent", "tremorsense", "wavesense",
                  "lifesense", "thoughtsense", "see invisibility", "truesight"]
DEFAULT_LANGUAGES = ["Common", "Aklo", "Chthonian", "Diabolic", "Draconic", "Dwarven", "Elven", "Empyrean", "Fey",
                     "Gnomish", "Goblin", "Halfling", "Jotun", "Muan", "Necril", "Orcish", "Petran", "Pyric",
                     "Sakvroth", "Shadowtongue", "Sussuran", "Thalassic"]
STRIKE_TRAITS = ["agile", "backstab", "deadly-d8", "deadly-d10", "deadly-d12", "fatal-d10", "fatal-d12", "finesse",
                 "forceful", "magical", "reach-10", "reach-15", "reach-20", "shove", "sweep", "trip", "grapple",
                 "unarmed", "versatile-p", "versatile-s", "range-increment-30", "range-increment-60", "thrown-20"]
STRIKE_NAMES = ["Jaws", "Claw", "Fist", "Horn", "Tail", "Tentacle", "Wing", "Talon", "Stinger", "Slam", "Hoof",
                "Tusk", "Beak", "Fangs", "Longsword", "Shortsword", "Dagger", "Spear", "Shortbow", "Longbow",
                "Crossbow", "Club", "Greataxe", "Scimitar", "Warhammer"]
COMMON_ABILITIES = ["Attack of Opportunity", "Grab", "Improved Grab", "Knockdown", "Improved Knockdown", "Push",
                    "Improved Push", "Constrict", "Swallow Whole", "Trample", "Ferocity", "Frightful Presence",
                    "Breath Weapon", "Throw Rock", "Rend", "Regeneration", "Shield Block", "Sneak Attack",
                    "Negative Healing", "Void Healing", "Aura", "Engulf", "Fast Healing"]
SPELL_ENTRIES = [f"{t} {k} Spells" for t in ("Arcane", "Divine", "Occult", "Primal")
                 for k in ("Innate", "Prepared", "Spontaneous")]
SPELL_RANKS = ["Cantrips"] + [f"Rank {n}" for n in range(1, 11)] + ["Constant (1st)", "Rituals"]
ITEM_TRAITS = ["alchemical", "consumable", "elixir", "invested", "magical", "potion", "scroll", "talisman", "wand",
               "staff", "worn", "fire", "cold", "healing", "mental", "poison", "bomb", "fulu", "oil", "spellheart"]


def _titleize(slug):
    return str(slug).replace("-", " ").replace("_", " ").strip().title()


def family_traits(traits):
    return [t for t in traits or [] if str(t).lower() not in GENERIC_TRAITS]


def _merge(counter, defaults, key=str.lower):
    """Values ordered by frequency in the data, then any defaults not already present."""
    out, seen = [], set()
    for v, _ in counter.most_common():
        if v and key(v) not in seen:
            seen.add(key(v)); out.append(v)
    for v in defaults:
        if key(v) not in seen:
            seen.add(key(v)); out.append(v)
    return out


def _ref_name(pair):
    """[display, 'name:slug'] -> 'slug' (or display if no ref)."""
    if isinstance(pair, (list, tuple)) and len(pair) > 1 and pair[1] and ":" in pair[1]:
        return pair[1].split(":", 1)[1]
    return pair[0] if isinstance(pair, (list, tuple)) else str(pair)


def build_vocab(creatures, items, details_db=None, custom_creatures=(), custom_items=()):
    traits, fams, sources, item_traits, item_sources = Counter(), Counter(), Counter(), Counter(), Counter()
    for c in list(creatures) + list(custom_creatures):
        if getattr(c, "kind", "creature") == "hazard":
            continue
        traits.update(t.lower() for t in c.traits)
        fams.update(t.lower() for t in family_traits(c.traits))
        if c.source:
            sources[c.source] += 1
    for i in list(items) + list(custom_items):
        item_traits.update(t.lower() for t in i.traits)
        if i.source:
            item_sources[i.source] += 1

    langs, senses, iwr, speeds, strike_names, strike_traits, dmg_types, abilities = (Counter() for _ in range(8))
    spells, rule_actions = [], []
    if details_db is not None:
        for d in details_db.iter_creatures():
            langs.update(x.strip() for x in str(d.get("languages") or "").split(",") if x.strip())
            for s in d.get("senses") or []:
                senses[_ref_name(s).replace("-", " ").lower()] += 1
            for key in ("immunities", "weaknesses", "resistances"):
                for p in d.get(key) or []:
                    iwr[_ref_name(p)] += 1
            for part in str(d.get("speed") or "").split(","):
                w = part.strip().split()
                if w and not w[0].isdigit():
                    speeds[w[0].lower()] += 1
            for st in d.get("strikes") or []:
                if isinstance(st, dict):
                    strike_names[st.get("name", "")] += 1
                    strike_traits.update(st.get("traits") or [])
                    for dm in st.get("damage") or []:
                        bits = dm.split(" ", 1)
                        if len(bits) > 1:
                            dmg_types.update(bits[1].split())
            for a in d.get("actions") or []:
                abilities[a.get("name", "")] += 1
        spells = details_db.rule_names("spell")
        rule_actions = details_db.rule_names("action")

    return {
        "traits": _merge(traits, CREATURE_TYPES),
        "families": [f"{f} ({n})" for f, n in fams.most_common() if n >= 2] or [],
        "types": CREATURE_TYPES,
        "sources": _merge(sources, ["Hallowmead"]),
        "sizes": [label for _, label in SIZES],
        "languages": _merge(langs, DEFAULT_LANGUAGES),
        "senses": _merge(senses, DEFAULT_SENSES),
        "iwr": _merge(iwr, DAMAGE_TYPES + ["physical", "precision", "critical-hits", "death-effects", "disease",
                                           "paralyzed", "poison", "sleep", "mental", "bleed", "all-damage"]),
        "speeds": _merge(speeds, SPEED_TYPES),
        "skills": SKILLS + ["Lore"],
        "strike_names": _merge(strike_names, STRIKE_NAMES),
        "strike_traits": _merge(strike_traits, STRIKE_TRAITS),
        "damage_types": _merge(dmg_types, DAMAGE_TYPES),
        "abilities": _merge(abilities, COMMON_ABILITIES),
        "spells": spells,
        "rule_actions": rule_actions,
        "spell_entries": SPELL_ENTRIES,
        "spell_ranks": SPELL_RANKS,
        "item_traits": _merge(item_traits, ITEM_TRAITS),
        "item_sources": _merge(item_sources, ["Hallowmead"]),
        "creature_names": sorted({c.name for c in list(creatures) + list(custom_creatures)
                                  if getattr(c, "kind", "creature") != "hazard"}),
        "hazard_traits": _merge(Counter(t.lower() for c in creatures if getattr(c, "kind", "") == "hazard"
                                        for t in c.traits if t.lower() not in ("complex", "common")),
                                ["trap", "haunt", "environmental", "mechanical", "magical"]),
    }


def cached_vocab(path, details_path, index_path, build):
    """Return vocab from cache when the index/database haven't changed, else rebuild and save."""
    def stamp(p):
        try:
            st = os.stat(p)
            return [st.st_size, int(st.st_mtime)]
        except OSError:
            return None
    key = {"details": stamp(details_path), "index": stamp(index_path), "v": 1}
    try:
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("key") == key:
            return cached["vocab"]
    except (OSError, ValueError, KeyError):
        pass
    vocab = build()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"key": key, "vocab": vocab}, f)
    except OSError:
        pass
    return vocab


def strip_count(value):
    """'goblin (34)' -> 'goblin'."""
    v = str(value or "").strip()
    if v.endswith(")") and " (" in v:
        head, _, tail = v.rpartition(" (")
        if tail[:-1].isdigit():
            return head
    return v

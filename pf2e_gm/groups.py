"""Creature grouping: themes, regions, and which creatures belong together.

Pathfinder 2e stat blocks have no environment or "found with" field, so grouping uses two real
signals from the data:
  * family traits shared between creatures (goblin, kobold, ghoul, demon, skeleton...), and
  * publication: creatures from the same adventure or module were written to appear together.
Large general bestiaries (hundreds of creatures) count as a weak signal only.

Regions are user-defined filters (traits, families, types, sources, specific creatures). A few
starter regions are provided; they are trait-based approximations, not official habitat data.
"""
from collections import Counter

from .vocab import family_traits

THEMES = {
    "Undead": {"types": ["undead"], "traits": ["ghost", "ghoul", "skeleton", "vampire", "wight", "zombie", "lich", "mummy"]},
    "Fiends": {"types": ["fiend"], "traits": ["demon", "devil", "daemon", "div", "qlippoth", "rakshasa"]},
    "Celestials and monitors": {"types": ["celestial", "monitor"], "traits": ["angel", "archon", "azata", "aeon", "psychopomp"]},
    "Dragons and kobolds": {"types": ["dragon"], "traits": ["kobold", "drake"]},
    "Goblinoids": {"traits": ["goblin", "hobgoblin", "bugbear"]},
    "Giants and trolls": {"types": ["giant"], "traits": ["troll", "ogre"]},
    "Elementals": {"types": ["elemental"], "traits": []},
    "Fey courts": {"types": ["fey"], "traits": ["sprite", "gremlin", "nymph"]},
    "Aberrations": {"types": ["aberration"], "traits": []},
    "Constructs": {"types": ["construct"], "traits": ["golem", "clockwork"]},
    "Oozes and fungi": {"types": ["ooze", "fungus"], "traits": ["leshy"]},
    "Plants": {"types": ["plant"], "traits": []},
    "Beasts and animals": {"types": ["animal", "beast"], "traits": []},
    "Lycanthropes": {"traits": ["werecreature"]},
    "Swarms": {"traits": ["swarm"]},
    "Troops": {"traits": ["troop"]},
    "Humanoid bands": {"types": ["humanoid"], "traits": []},
}

STARTER_REGIONS = [
    {"name": "Crypts and graveyards (trait-based)", "types": ["undead"], "traits": ["spirit", "ghost"],
     "notes": "Starter region built from traits. Edit or replace with your own."},
    {"name": "Deep caverns (trait-based)", "types": ["fungus", "ooze", "aberration"], "traits": [],
     "notes": "Starter region built from traits. Edit or replace with your own."},
    {"name": "Wilds and forests (trait-based)", "types": ["animal", "beast", "plant", "fey"], "traits": [],
     "notes": "Starter region built from traits. Edit or replace with your own."},
    {"name": "Waters and coasts (trait-based)", "traits": ["aquatic", "amphibious", "water"],
     "notes": "Starter region built from traits. Edit or replace with your own."},
    {"name": "Frozen wastes (trait-based)", "traits": ["cold", "ice"],
     "notes": "Starter region built from traits. Edit or replace with your own."},
    {"name": "Volcanic and fiery (trait-based)", "traits": ["fire"],
     "notes": "Starter region built from traits. Edit or replace with your own."},
    {"name": "Infernal and abyssal (trait-based)", "types": ["fiend"], "traits": ["demon", "devil"],
     "notes": "Starter region built from traits. Edit or replace with your own."},
]

SPEC_KEYS = ("traits", "families", "types", "sources", "creatures", "exclude_traits")


def matches_spec(c, spec):
    """True if a creature fits a theme/region. Any listed trait, family, type, source, or name counts."""
    if not spec:
        return True
    traits = {t.lower() for t in c.traits}
    if traits & {t.lower() for t in spec.get("exclude_traits", [])}:
        return False
    names = {n.lower() for n in spec.get("creatures", [])}
    if c.name.lower() in names:
        return True
    wanted = {t.lower() for t in list(spec.get("traits", [])) + list(spec.get("families", [])) + list(spec.get("types", []))}
    if wanted & traits:
        return True
    sources = {s.lower() for s in spec.get("sources", [])}
    if sources and (c.source or "").lower() in sources:
        return True
    return not (wanted or sources or names)


def general_sources(creatures, threshold=150):
    """Sources big enough to be general bestiaries (weak 'appear together' signal)."""
    counts = Counter(c.source for c in creatures if c.source)
    return {s for s, n in counts.items() if n >= threshold}


class Affinity:
    """Score how strongly two creatures belong together."""

    def __init__(self, general=()):
        self.general = set(general)

    def reasons(self, a, b):
        out = []
        shared = {t.lower() for t in family_traits(a.traits)} & {t.lower() for t in family_traits(b.traits)}
        if shared:
            out.append("shares " + ", ".join(sorted(shared)))
        if a.source and a.source == b.source:
            out.append(("same bestiary: " if a.source in self.general else "same book: ") + a.source)
        return out

    def score(self, a, b):
        if a.base_uid == b.base_uid:
            return 4
        s = 0
        if {t.lower() for t in family_traits(a.traits)} & {t.lower() for t in family_traits(b.traits)}:
            s += 3
        if a.source and a.source == b.source:
            s += 0.25 if a.source in self.general else 2
        return s


def related(creature, pool, affinity, party_level=None, limit=60):
    """Creatures that belong with `creature`, best first: [(creature, score, reasons)]."""
    from .rules import creature_xp
    out = []
    for c in pool:
        if c.base_uid == creature.base_uid or c.adjust or getattr(c, "kind", "creature") == "hazard":
            continue
        if party_level is not None and creature_xp(c.level, party_level) is None:
            continue
        s = affinity.score(creature, c)
        if s >= 1:
            out.append((c, s, affinity.reasons(creature, c)))
    out.sort(key=lambda x: (-x[1], abs(x[0].level - creature.level), x[0].name))
    return out[:limit]

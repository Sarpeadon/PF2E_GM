"""Rules tables (GM Core). Edit here if you want to correct or house-rule anything.

NOTE: The treasure table was entered from memory of the Party Treasure by Level
table. Spot-check it against your copy of GM Core before relying on it.
"""

# threat: (XP budget for 4 PCs, adjustment per PC above/below 4)
THREATS = {
    "Trivial": (40, 10),
    "Low": (60, 20),
    "Moderate": (80, 20),
    "Severe": (120, 30),
    "Extreme": (160, 40),
}

# creature level minus party level -> XP
CREATURE_XP = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120, 4: 160}


# simple hazards: hazard level minus party level -> XP (complex hazards use CREATURE_XP)
SIMPLE_HAZARD_XP = {-4: 2, -3: 3, -2: 4, -1: 6, 0: 8, 1: 12, 2: 16, 3: 24, 4: 32}


def xp_of(c, party_level):
    """XP for a creature or hazard, or None if outside the -4..+4 window."""
    if getattr(c, "kind", "creature") == "hazard" and not getattr(c, "complex", False):
        return SIMPLE_HAZARD_XP.get(c.level - party_level)
    return CREATURE_XP.get(c.level - party_level)


def hazard_xp(hazard_level, party_level, complex_hazard=False):
    """XP for a hazard of a level, for a party of a level. Beyond +4 it is paid as +4; below -4 it is worth nothing."""
    rel = int(hazard_level) - int(party_level)
    if rel < -4:
        return 0
    return (CREATURE_XP if complex_hazard else SIMPLE_HAZARD_XP)[min(rel, 4)]


def xp_budget(threat: str, party_size: int) -> int:
    base, adj = THREATS[threat]
    return max(0, base + (party_size - 4) * adj)


def creature_xp(creature_level: int, party_level: int):
    """XP value of a creature, or None if outside the -4..+4 window."""
    return CREATURE_XP.get(creature_level - party_level)


# level: total gp, permanent [(item level, count)], consumables [(item level, count)],
#        party currency gp, currency per additional PC
TREASURE = {
    1:  dict(total=175,    permanent=[(2, 2), (1, 2)],   consumables=[(2, 2), (1, 3)],            currency=40,     per_pc=10),
    2:  dict(total=300,    permanent=[(3, 2), (2, 2)],   consumables=[(3, 2), (2, 2), (1, 2)],    currency=70,     per_pc=18),
    3:  dict(total=500,    permanent=[(4, 2), (3, 2)],   consumables=[(4, 2), (3, 2), (2, 2)],    currency=120,    per_pc=30),
    4:  dict(total=850,    permanent=[(5, 2), (4, 2)],   consumables=[(5, 2), (4, 2), (3, 2)],    currency=200,    per_pc=50),
    5:  dict(total=1350,   permanent=[(6, 2), (5, 2)],   consumables=[(6, 2), (5, 2), (4, 2)],    currency=320,    per_pc=80),
    6:  dict(total=2000,   permanent=[(7, 2), (6, 2)],   consumables=[(7, 2), (6, 2), (5, 2)],    currency=500,    per_pc=125),
    7:  dict(total=2900,   permanent=[(8, 2), (7, 2)],   consumables=[(8, 2), (7, 2), (6, 2)],    currency=720,    per_pc=180),
    8:  dict(total=4000,   permanent=[(9, 2), (8, 2)],   consumables=[(9, 2), (8, 2), (7, 2)],    currency=1000,   per_pc=250),
    9:  dict(total=5700,   permanent=[(10, 2), (9, 2)],  consumables=[(10, 2), (9, 2), (8, 2)],   currency=1400,   per_pc=350),
    10: dict(total=8000,   permanent=[(11, 2), (10, 2)], consumables=[(11, 2), (10, 2), (9, 2)],  currency=2000,   per_pc=500),
    11: dict(total=11500,  permanent=[(12, 2), (11, 2)], consumables=[(12, 2), (11, 2), (10, 2)], currency=2800,   per_pc=700),
    12: dict(total=16500,  permanent=[(13, 2), (12, 2)], consumables=[(13, 2), (12, 2), (11, 2)], currency=4000,   per_pc=1000),
    13: dict(total=25000,  permanent=[(14, 2), (13, 2)], consumables=[(14, 2), (13, 2), (12, 2)], currency=6000,   per_pc=1500),
    14: dict(total=36500,  permanent=[(15, 2), (14, 2)], consumables=[(15, 2), (14, 2), (13, 2)], currency=9000,   per_pc=2250),
    15: dict(total=54500,  permanent=[(16, 2), (15, 2)], consumables=[(16, 2), (15, 2), (14, 2)], currency=13000,  per_pc=3250),
    16: dict(total=82500,  permanent=[(17, 2), (16, 2)], consumables=[(17, 2), (16, 2), (15, 2)], currency=20000,  per_pc=5000),
    17: dict(total=128000, permanent=[(18, 2), (17, 2)], consumables=[(18, 2), (17, 2), (16, 2)], currency=30000,  per_pc=7500),
    18: dict(total=208000, permanent=[(19, 2), (18, 2)], consumables=[(19, 2), (18, 2), (17, 2)], currency=48000,  per_pc=12000),
    19: dict(total=355000, permanent=[(20, 2), (19, 2)], consumables=[(20, 2), (19, 2), (18, 2)], currency=80000,  per_pc=20000),
    20: dict(total=490000, permanent=[(20, 4)],          consumables=[(20, 4), (19, 2)],          currency=140000, per_pc=35000),
}

# Your table's usual party size. Budgets, treasure, and XP awards all adjust from the 4-PC baseline.
DEFAULT_PARTY_SIZE = 5

RARITIES = ["common", "uncommon", "rare", "unique"]

"""GM Core tables: creature building, Elite/Weak adjustments, Recall Knowledge.

NOTE: These tables were entered by hand from memory of GM Core (Building Creatures,
Elite/Weak adjustments, DCs by Level, Identifying Creatures). Spot-check them against
your book. Every table is keyed by creature level and is easy to correct here.
"""

LEVELS = list(range(-1, 25))

# ---------- Building Creatures ----------
# Perception and saving throws: (extreme, high, moderate, low, terrible)
PERCEPTION_SAVES = {
    -1: (9, 8, 5, 2, 0), 0: (10, 9, 6, 3, 1), 1: (11, 10, 7, 4, 2), 2: (12, 11, 8, 5, 3),
    3: (14, 12, 9, 6, 4), 4: (15, 14, 11, 8, 6), 5: (17, 15, 12, 9, 7), 6: (18, 17, 14, 11, 8),
    7: (20, 18, 15, 12, 10), 8: (21, 19, 16, 13, 11), 9: (23, 21, 18, 15, 12), 10: (24, 22, 19, 16, 14),
    11: (26, 24, 21, 18, 15), 12: (27, 25, 22, 19, 16), 13: (29, 26, 23, 20, 18), 14: (30, 28, 25, 22, 19),
    15: (32, 29, 26, 23, 20), 16: (33, 30, 28, 25, 22), 17: (35, 32, 29, 26, 23), 18: (36, 33, 30, 27, 24),
    19: (38, 35, 32, 29, 26), 20: (39, 36, 33, 30, 27), 21: (41, 38, 35, 32, 28), 22: (43, 39, 36, 33, 30),
    23: (44, 40, 37, 34, 31), 24: (46, 42, 38, 36, 32),
}
TIERS5 = ["Extreme", "High", "Moderate", "Low", "Terrible"]

# Armor Class: (extreme, high, moderate, low)
AC = {
    -1: (18, 15, 14, 12), 0: (19, 16, 15, 13), 1: (19, 16, 15, 13), 2: (21, 18, 17, 15),
    3: (22, 19, 18, 16), 4: (24, 21, 20, 18), 5: (25, 22, 21, 19), 6: (27, 24, 23, 21),
    7: (28, 25, 24, 22), 8: (30, 27, 26, 24), 9: (31, 28, 27, 25), 10: (33, 30, 29, 27),
    11: (34, 31, 30, 28), 12: (36, 33, 32, 30), 13: (37, 34, 33, 31), 14: (39, 36, 35, 33),
    15: (40, 37, 36, 34), 16: (42, 39, 38, 36), 17: (43, 40, 39, 37), 18: (45, 42, 41, 39),
    19: (46, 43, 42, 40), 20: (48, 45, 44, 42), 21: (49, 46, 45, 43), 22: (51, 48, 47, 45),
    23: (52, 49, 48, 46), 24: (54, 51, 50, 48),
}
TIERS4 = ["Extreme", "High", "Moderate", "Low"]

# Hit Points: high, moderate, low as (top, bottom) ranges
HP = {
    -1: ((9, 9), (8, 7), (6, 5)), 0: ((20, 17), (16, 14), (13, 11)), 1: ((26, 24), (21, 19), (16, 14)),
    2: ((40, 36), (32, 28), (25, 21)), 3: ((59, 53), (48, 42), (37, 31)), 4: ((78, 72), (63, 57), (48, 42)),
    5: ((97, 91), (78, 72), (59, 53)), 6: ((123, 115), (99, 91), (75, 67)), 7: ((148, 140), (119, 111), (90, 82)),
    8: ((173, 165), (139, 131), (105, 97)), 9: ((198, 190), (159, 151), (120, 112)),
    10: ((223, 215), (179, 171), (135, 127)), 11: ((248, 240), (199, 191), (150, 142)),
    12: ((273, 265), (219, 211), (165, 157)), 13: ((298, 290), (239, 231), (180, 172)),
    14: ((323, 315), (259, 251), (195, 187)), 15: ((348, 340), (279, 271), (210, 202)),
    16: ((373, 365), (299, 291), (225, 217)), 17: ((398, 390), (319, 311), (240, 232)),
    18: ((423, 415), (339, 331), (255, 247)), 19: ((448, 440), (359, 351), (270, 262)),
    20: ((473, 465), (379, 371), (285, 277)), 21: ((505, 495), (405, 395), (305, 295)),
    22: ((544, 532), (436, 424), (329, 317)), 23: ((581, 569), (466, 454), (351, 339)),
    24: ((633, 617), (508, 492), (383, 367)),
}
HP_TIERS = ["High", "Moderate", "Low"]

# Strike attack bonus: (extreme, high, moderate, low)
ATTACK = {
    -1: (10, 8, 6, 4), 0: (10, 8, 6, 4), 1: (11, 9, 7, 5), 2: (13, 11, 9, 7), 3: (14, 12, 10, 8),
    4: (16, 14, 12, 9), 5: (17, 15, 13, 11), 6: (19, 17, 15, 12), 7: (20, 18, 16, 13), 8: (22, 20, 18, 15),
    9: (23, 21, 19, 16), 10: (25, 23, 21, 17), 11: (27, 24, 22, 19), 12: (28, 26, 24, 20),
    13: (29, 27, 25, 21), 14: (31, 29, 27, 23), 15: (32, 30, 28, 24), 16: (34, 32, 30, 25),
    17: (35, 33, 31, 27), 18: (37, 35, 33, 28), 19: (38, 36, 34, 29), 20: (40, 38, 36, 31),
    21: (41, 39, 37, 32), 22: (43, 41, 39, 33), 23: (44, 42, 40, 35), 24: (46, 44, 42, 36),
}

# Strike damage: (extreme, high, moderate, low)
DAMAGE = {
    -1: ("1d6+1", "1d4+1", "1d4", "1d4"), 0: ("1d6+3", "1d6+2", "1d4+2", "1d4+1"),
    1: ("1d8+4", "1d6+3", "1d6+2", "1d4+2"), 2: ("1d12+4", "1d10+4", "1d8+4", "1d6+3"),
    3: ("1d12+8", "1d10+6", "1d8+6", "1d6+5"), 4: ("2d10+7", "2d8+5", "2d6+5", "2d4+4"),
    5: ("2d12+7", "2d8+7", "2d6+6", "2d4+6"), 6: ("2d12+10", "2d8+9", "2d6+8", "2d4+7"),
    7: ("2d12+12", "2d10+9", "2d8+8", "2d6+6"), 8: ("2d12+15", "2d10+11", "2d8+9", "2d6+8"),
    9: ("2d12+17", "2d10+13", "2d8+11", "2d6+9"), 10: ("2d12+20", "2d12+13", "2d10+11", "2d6+10"),
    11: ("2d12+22", "2d12+15", "2d10+12", "2d8+10"), 12: ("3d12+19", "3d10+14", "3d8+12", "3d6+10"),
    13: ("3d12+21", "3d10+16", "3d8+14", "3d6+11"), 14: ("3d12+24", "3d10+18", "3d8+15", "3d6+13"),
    15: ("3d12+26", "3d12+17", "3d10+14", "3d6+14"), 16: ("3d12+29", "3d12+18", "3d10+15", "3d6+15"),
    17: ("3d12+31", "3d12+19", "3d10+16", "3d6+16"), 18: ("3d12+34", "3d12+20", "3d10+17", "3d6+17"),
    19: ("4d12+29", "4d10+20", "4d8+17", "4d6+14"), 20: ("4d12+32", "4d10+22", "4d8+19", "4d6+15"),
    21: ("4d12+34", "4d10+24", "4d8+20", "4d6+17"), 22: ("4d12+37", "4d10+26", "4d8+22", "4d6+18"),
    23: ("4d12+39", "4d12+24", "4d10+20", "4d6+19"), 24: ("4d12+42", "4d12+26", "4d10+22", "4d6+21"),
}

# Spell DC and spell attack: (extreme, high, moderate) as (DC, attack)
SPELL = {
    -1: ((19, 11), (16, 8), (13, 5)), 0: ((19, 11), (16, 8), (13, 5)), 1: ((20, 12), (17, 9), (14, 6)),
    2: ((22, 14), (18, 10), (15, 7)), 3: ((23, 15), (20, 12), (17, 9)), 4: ((25, 17), (21, 13), (18, 10)),
    5: ((26, 18), (22, 14), (19, 11)), 6: ((27, 19), (24, 16), (21, 13)), 7: ((29, 21), (25, 17), (22, 14)),
    8: ((30, 22), (26, 18), (23, 15)), 9: ((32, 24), (28, 20), (25, 17)), 10: ((33, 25), (29, 21), (26, 18)),
    11: ((34, 26), (30, 22), (27, 19)), 12: ((36, 28), (32, 24), (29, 21)), 13: ((37, 29), (33, 25), (30, 22)),
    14: ((39, 31), (34, 26), (31, 23)), 15: ((40, 32), (36, 28), (33, 25)), 16: ((41, 33), (37, 29), (34, 26)),
    17: ((43, 35), (38, 30), (35, 27)), 18: ((44, 36), (40, 32), (37, 29)), 19: ((46, 38), (41, 33), (38, 30)),
    20: ((47, 39), (42, 34), (39, 31)), 21: ((48, 40), (44, 36), (41, 33)), 22: ((50, 42), (45, 37), (42, 34)),
    23: ((51, 43), (46, 38), (44, 36)), 24: ((52, 44), (48, 40), (45, 37)),
}
SPELL_TIERS = ["Extreme", "High", "Moderate"]

# Skills: (extreme, high, moderate, low)  (low uses the top of the book's range)
SKILL = {
    -1: (8, 5, 4, 2), 0: (9, 6, 5, 3), 1: (10, 7, 6, 4), 2: (11, 8, 7, 5), 3: (13, 10, 9, 7),
    4: (15, 12, 10, 8), 5: (16, 13, 12, 10), 6: (18, 15, 13, 11), 7: (20, 17, 15, 13), 8: (21, 18, 16, 14),
    9: (23, 20, 18, 16), 10: (25, 22, 19, 17), 11: (26, 23, 21, 19), 12: (28, 25, 22, 20),
    13: (30, 27, 24, 22), 14: (31, 28, 25, 23), 15: (33, 30, 27, 25), 16: (35, 32, 28, 26),
    17: (36, 33, 30, 28), 18: (38, 35, 31, 29), 19: (40, 37, 33, 31), 20: (41, 38, 34, 32),
    21: (43, 40, 36, 34), 22: (45, 42, 37, 35), 23: (46, 43, 38, 36), 24: (48, 45, 40, 38),
}


def _lvl(level):
    return max(-1, min(24, int(level)))


def suggest(level, tiers):
    """tiers: dict of stat -> tier name. Returns dict of suggested values."""
    L = _lvl(level)
    t = tiers
    out = {}
    out["perception"] = PERCEPTION_SAVES[L][TIERS5.index(t.get("perception", "Moderate"))]
    for save in ("fort", "ref", "will"):
        out[save] = PERCEPTION_SAVES[L][TIERS5.index(t.get(save, "Moderate"))]
    out["ac"] = AC[L][TIERS4.index(t.get("ac", "Moderate"))]
    top, bottom = HP[L][HP_TIERS.index(t.get("hp", "Moderate"))]
    out["hp"] = (top + bottom) // 2
    out["attack"] = ATTACK[L][TIERS4.index(t.get("attack", "Moderate"))]
    out["damage"] = DAMAGE[L][TIERS4.index(t.get("damage", "Moderate"))]
    if t.get("spell", "None") != "None":
        out["spell_dc"], out["spell_attack"] = SPELL[L][SPELL_TIERS.index(t["spell"])]
    out["skill"] = SKILL[L][TIERS4.index(t.get("skill", "Moderate"))]
    return out


# ---------- Area Damage (hazards, afflictions, and other damaging abilities) ----------
# level: (unlimited-use dice, average, limited-use dice, average). Unlimited use is for something that acts every round;
# limited use is for something that goes off once. Take two levels off when the ability also applies a condition.
AREA_DAMAGE = {
    -1: ("1d4", 2, "1d6", 4), 0: ("1d6", 4, "1d10", 6), 1: ("2d4", 5, "2d6", 7), 2: ("2d6", 7, "3d6", 11),
    3: ("2d8", 9, "4d6", 14), 4: ("3d6", 11, "5d6", 18), 5: ("2d10", 12, "6d6", 21), 6: ("4d6", 14, "7d6", 25),
    7: ("4d6", 15, "8d6", 28), 8: ("5d6", 17, "9d6", 32), 9: ("5d6", 18, "10d6", 35), 10: ("6d6", 20, "11d6", 39),
    11: ("6d6", 21, "12d6", 42), 12: ("5d8", 23, "13d6", 46), 13: ("7d6", 24, "14d6", 49), 14: ("4d12", 26, "15d6", 53),
    15: ("6d8", 27, "16d6", 56), 16: ("8d6", 28, "17d6", 60), 17: ("8d6", 29, "18d6", 63), 18: ("9d6", 30, "19d6", 67),
    19: ("7d8", 32, "20d6", 70), 20: ("6d10", 33, "21d6", 74), 21: ("10d6", 35, "22d6", 77), 22: ("8d8", 36, "23d6", 81),
    23: ("11d6", 38, "24d6", 84), 24: ("11d6", 39, "25d6", 88),
}


def area_damage(level, limited=False):
    """(dice, average) from the Area Damage table. limited=True is the column for once-only abilities (simple traps)."""
    row = AREA_DAMAGE[_lvl(level)]
    return (row[2], row[3]) if limited else (row[0], row[1])


def high_ac(level):
    """The High AC for a level (the AC column of the Building Creatures table)."""
    return AC[_lvl(level)][1]


# ---------- Elite / Weak ----------
def elite_level(level):
    return level + 2 if level in (-1, 0) else level + 1


def weak_level(level):
    return level - 2 if level == 1 else level - 1


def elite_hp(level):
    """HP increase for the Elite adjustment, by starting level."""
    if level <= 1:
        return 10
    if level <= 4:
        return 15
    if level <= 19:
        return 20
    return 30


def weak_hp(level):
    """HP decrease for the Weak adjustment, by starting level."""
    if level <= 2:
        return 10
    if level <= 5:
        return 15
    if level <= 20:
        return 20
    return 30


def adjusted_level(level, adjust):
    if adjust == "elite":
        return elite_level(level)
    if adjust == "weak":
        return weak_level(level)
    return level


# ---------- Recall Knowledge ----------
DC_BY_LEVEL = {
    -1: 13, 0: 14, 1: 15, 2: 16, 3: 18, 4: 19, 5: 20, 6: 22, 7: 23, 8: 24, 9: 26, 10: 27,
    11: 28, 12: 30, 13: 31, 14: 32, 15: 34, 16: 35, 17: 36, 18: 38, 19: 39, 20: 40,
    21: 42, 22: 44, 23: 46, 24: 48, 25: 50,
}
RARITY_DC = {"common": 0, "uncommon": 2, "rare": 5, "unique": 10}

# Creature trait -> skill(s) used to Recall Knowledge
TRAIT_SKILLS = {
    "aberration": ["Occultism"], "animal": ["Nature"], "astral": ["Occultism"], "beast": ["Arcana", "Nature"],
    "celestial": ["Religion"], "construct": ["Arcana", "Crafting"], "dragon": ["Arcana"],
    "dream": ["Occultism"], "elemental": ["Arcana", "Nature"], "ethereal": ["Occultism"], "fey": ["Nature"],
    "fiend": ["Religion"], "fungus": ["Nature"], "giant": ["Society"], "humanoid": ["Society"],
    "monitor": ["Religion"], "ooze": ["Occultism"], "plant": ["Nature"], "shade": ["Religion"],
    "spirit": ["Occultism"], "time": ["Occultism"], "undead": ["Religion"],
}


def recall_dc(level, rarity="common"):
    lvl = max(-1, min(25, int(level)))
    return DC_BY_LEVEL[lvl] + RARITY_DC.get(rarity or "common", 0)


def recall_skills(traits):
    skills = []
    for t in traits or []:
        for s in TRAIT_SKILLS.get(str(t).lower(), []):
            if s not in skills:
                skills.append(s)
    return skills

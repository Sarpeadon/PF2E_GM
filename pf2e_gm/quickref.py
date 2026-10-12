"""GM quick reference: DCs by level, simple DCs, adjustments, XP tables.

Values follow GM Core (DCs by Level, Simple DCs, DC Adjustments, Encounter Budget, Creature and
Hazard XP). They were entered by hand; spot-check against your book.
"""
from .gmtables import DC_BY_LEVEL
from .rules import CREATURE_XP, DEFAULT_PARTY_SIZE, SIMPLE_HAZARD_XP, THREATS

SIMPLE_DCS = [("Untrained", 10), ("Trained", 15), ("Expert", 20), ("Master", 30), ("Legendary", 40)]
ADJUSTMENTS = [("Incredibly easy", -10), ("Very easy", -5), ("Easy", -2), ("Normal", 0),
               ("Hard", 2), ("Very hard", 5), ("Incredibly hard", 10)]
RARITY_ADJ = [("Common", 0), ("Uncommon", 2), ("Rare", 5), ("Unique", 10)]
SPELL_RANK_LEVEL = {r: 2 * r - 1 for r in range(1, 11)}   # rank 1 = level 1, rank 2 = level 3, ...


def dc_for(level, difficulty="Normal", rarity="Common"):
    lvl = max(-1, min(25, int(level)))
    adj = dict(ADJUSTMENTS).get(difficulty, 0) + dict(RARITY_ADJ).get(rarity, 0)
    return DC_BY_LEVEL[lvl] + adj


def spell_rank_dc(rank, difficulty="Normal", rarity="Common"):
    """DC for a spell effect of a given rank (uses the level that rank corresponds to)."""
    return dc_for(SPELL_RANK_LEVEL.get(int(rank), 1), difficulty, rarity)


def reference_segments(party_size=DEFAULT_PARTY_SIZE):
    """[(text, style, ref)] for the reference panel."""
    out = []

    def add(t, s="body", r=None):
        out.append((t, s, r))
    add("DCs by Level\n", "head")
    rows = sorted(DC_BY_LEVEL.items())
    for i in range(0, len(rows), 6):
        add("   ".join(f"L{l:>2}: {dc:>2}" for l, dc in rows[i:i + 6]) + "\n", "mono")
    add("\nSimple DCs (proficiency rank needed)\n", "head")
    add("   ".join(f"{n} {dc}" for n, dc in SIMPLE_DCS) + "\n", "mono")
    add("\nDC Adjustments\n", "head")
    add("   ".join(f"{n} {v:+d}" for n, v in ADJUSTMENTS if v) + "\n", "mono")
    add("Rarity: " + "   ".join(f"{n} {v:+d}" for n, v in RARITY_ADJ if v) + "\n", "mono")
    add("\nSpell rank to level (for spell-effect DCs)\n", "head")
    add("   ".join(f"R{r}: L{l}" for r, l in SPELL_RANK_LEVEL.items()) + "\n", "mono")
    add(f"\nEncounter Budget (party of {party_size})\n", "head")
    add("   ".join(f"{t} {b + (party_size - 4) * adj}" for t, (b, adj) in THREATS.items()) + "\n", "mono")
    add("Per PC above/below 4: " + "   ".join(f"{t} {adj:+d}" for t, (b, adj) in THREATS.items()) + "\n", "mono")
    add("\nCreature / complex hazard XP (level vs party)\n", "head")
    add("   ".join(f"{d:+d}: {x}" for d, x in sorted(CREATURE_XP.items())) + "\n", "mono")
    add("Simple hazard XP\n", "head")
    add("   ".join(f"{d:+d}: {x}" for d, x in sorted(SIMPLE_HAZARD_XP.items())) + "\n", "mono")
    add("\nDegrees of success\n", "head")
    add("Beat the DC by 10+: critical success. Meet or beat: success. Miss: failure. Miss by 10+: critical "
        "failure. A natural 20 improves the result one step; a natural 1 worsens it one step.\n")
    add("\nAdvancement\n", "head")
    add("1,000 XP per level. Each PC earns the XP listed for a group of four, even when you raised the "
        "budget for a bigger party (a Moderate fight for 5 PCs is built on 100 XP but awards 80).\n")
    if party_size > 4:
        x = party_size - 4
        add(f"\nTreasure for {party_size} PCs\n", "head")
        add(f"Per level, add {x} permanent item{'s' if x > 1 else ''} (party level or +1), {2 * x} consumables "
            "(party level and +1), and the Currency per Additional PC amount for each extra PC.\n")
    return out

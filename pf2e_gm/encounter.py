"""Encounter generation using GM Core XP budgets."""
import random
from collections import Counter
from dataclasses import dataclass, field, replace

from .gmtables import adjusted_level, elite_hp, weak_hp
from .groups import Affinity, matches_spec
from .rules import CREATURE_XP, creature_xp, xp_budget, xp_of

HAZARD_MODES = {"No hazards": "none", "Simple hazards": "simple", "Complex hazards": "complex",
                "Any hazards": "both"}

COHESION = {"Any mix": "any", "Prefer related creatures": "related", "Related only (same family or book)": "strict"}


def make_variant(c, adjust):
    """Return an Elite or Weak copy of a creature (or the base creature for adjust='')."""
    if c.is_hazard:
        return c                     # Elite/Weak don't apply to hazards
    base_level = c.base_level if c.base_level is not None else c.level
    base = replace(c, level=base_level, adjust="", base_level=None,
                   hp=c.hp if not c.adjust else None, ac=c.ac if not c.adjust else None)
    if c.adjust:   # recover base hp/ac from the variant
        delta = 2 if c.adjust == "elite" else -2
        base.ac = c.ac - delta if c.ac is not None else None
        hp_d = elite_hp(base_level) if c.adjust == "elite" else -weak_hp(base_level)
        base.hp = c.hp - hp_d if c.hp is not None else None
    if not adjust:
        return base
    delta = 2 if adjust == "elite" else -2
    hp_d = elite_hp(base_level) if adjust == "elite" else -weak_hp(base_level)
    return replace(base, level=adjusted_level(base_level, adjust), adjust=adjust, base_level=base_level,
                   ac=base.ac + delta if base.ac is not None else None,
                   hp=max(1, base.hp + hp_d) if base.hp is not None else None)


def expand_variants(creatures, party_level):
    """Add Elite and Weak versions of creatures whose adjusted level lands in the XP window."""
    out = list(creatures)
    for c in creatures:
        if c.adjust or c.is_hazard:
            continue
        for adj in ("elite", "weak"):
            if creature_xp(adjusted_level(c.level, adj), party_level) is not None:
                out.append(make_variant(c, adj))
    return out


@dataclass
class Encounter:
    groups: list            # [(Creature, count)]
    xp: int
    budget: int
    warnings: list = field(default_factory=list)

    def signature(self):
        return tuple(sorted((c.uid, n) for c, n in self.groups))


def filter_pool(creatures, party_level, rarities=None, include_traits=None,
                exclude_traits=None, name_or_source="", custom_only=False, variants=False,
                source="", family="", ctype="", size="", spec=None, hazards="none", hazard_traits=None,
                systems=None):
    """Filter creatures for the generator. Empty filters are ignored. `spec` is a theme/region dict.

    Hazards are excluded unless `hazards` is "simple", "complex", or "both". Creature filters (traits,
    family, type, size, theme/region) don't apply to hazards; rarity, level, name, and `hazard_traits`
    (e.g. trap, haunt, environmental) do.
    """
    htr = {t.lower() for t in (hazard_traits or []) if t}
    inc = {t.lower() for t in (include_traits or []) if t}
    exc = {t.lower() for t in (exclude_traits or []) if t}
    q = name_or_source.lower().strip()
    out = []
    if variants:
        creatures = expand_variants(creatures, party_level)
    for c in creatures:
        if systems and (getattr(c, "system", "pf") or "pf") not in systems:
            continue
        if xp_of(c, party_level) is None:
            continue
        if rarities and c.rarity not in rarities:
            continue
        if c.is_hazard:
            if hazards == "none" or (hazards == "simple" and c.complex) or (hazards == "complex" and not c.complex):
                continue
            if htr and not (htr & {t.lower() for t in c.traits}):
                continue
            if q and q not in c.name.lower() and q not in c.source.lower():
                continue
            if custom_only and not c.custom:
                continue
            out.append(c)
            continue
        traits = {t.lower() for t in c.traits}
        if inc and not (inc & traits):
            continue
        if exc & traits:
            continue
        if custom_only and not c.custom:
            continue
        if q and q not in c.name.lower() and q not in c.source.lower():
            continue
        if source and (c.source or "") != source:
            continue
        if family and family.lower() not in traits:
            continue
        if ctype and ctype.lower() not in traits:
            continue
        if size and (c.size or "") != size:
            continue
        if spec and not matches_spec(c, spec):
            continue
        out.append(c)
    return out


def _choose(cands, picks, rng, cohesion, affinity, bias):
    """Pick a candidate, weighting toward creatures related to those already picked."""
    if not picks or cohesion == "any":
        weights = [bias.get(c.base_uid, 1.0) for c in cands]
    else:
        anchor = picks[0]
        scores = [1 if c.is_hazard else max(affinity.score(p, c) for p in picks) for c in cands]
        if cohesion == "strict":
            keep = [(c, s) for c, s in zip(cands, scores) if c.is_hazard or affinity.score(anchor, c) >= 1]
            if not keep:
                return None
            cands, scores = [c for c, _ in keep], [s for _, s in keep]
        weights = [bias.get(c.base_uid, 1.0) * (1 + 3 * s) for c, s in zip(cands, scores)]
    return rng.choices(cands, weights=weights, k=1)[0]


def _build_one(pool, party_level, budget, max_creatures, max_types, style, rng,
               cohesion="any", affinity=None, bias=None, seed_creature=None, max_hazards=1,
               start_with_hazard=False):
    affinity = affinity or Affinity()
    bias = bias or {}
    picks, spent = [], 0
    if seed_creature is not None:
        xp = xp_of(seed_creature, party_level)
        if xp is not None and xp <= budget:
            picks.append(seed_creature); spent += xp
    if start_with_hazard and max_hazards > 0:
        hz = [c for c in pool if c.is_hazard and xp_of(c, party_level) <= budget - spent]
        if hz:
            h = rng.choice(hz)
            picks.append(h); spent += xp_of(h, party_level)
    if not picks and style == "boss":
        bosses = [c for c in pool if not c.is_hazard and c.level - party_level >= 1
                  and xp_of(c, party_level) <= budget]
        if bosses:
            b = _choose(bosses, [], rng, "any", affinity, bias)
            picks.append(b); spent += xp_of(b, party_level)
    elif not picks and style == "horde":
        pool = [c for c in pool if c.level - party_level <= -1] or pool
    while len(picks) < max_creatures:
        remaining = budget - spent
        types = {c.uid for c in picks if not c.is_hazard}
        hazards_used = {c.uid for c in picks if c.is_hazard}
        affordable = [c for c in pool if xp_of(c, party_level) <= remaining]
        # each hazard appears at most once, and only up to max_hazards per encounter
        affordable = [c for c in affordable if not c.is_hazard
                      or (c.uid not in hazards_used and len(hazards_used) < max_hazards)]
        if len(types) >= max_types:
            affordable = [c for c in affordable if c.uid in types or c.is_hazard]
        if not affordable:
            break
        repeats = [c for c in affordable if c.uid in types]
        if repeats and rng.random() < 0.55:
            c = rng.choice(repeats)
        else:
            c = _choose(affordable, picks, rng, cohesion, affinity, bias)
            if c is None:
                break
        picks.append(c); spent += xp_of(c, party_level)
    return picks, spent


def generate(pool, party_level, party_size, threat, count=5, max_creatures=8,
             max_types=3, attempts=600, seed=None, cohesion="any", affinity=None, bias=None,
             seed_creature=None, max_hazards=1):
    rng = random.Random(seed)
    budget = xp_budget(threat, party_size)
    if not pool or budget <= 0:
        return []
    results = {}
    has_hazards = max_hazards > 0 and any(c.is_hazard for c in pool)
    for n in range(attempts):
        style = rng.choice(["mixed", "mixed", "boss", "horde"])
        picks, spent = _build_one(pool, party_level, budget, max_creatures, max_types, style, rng,
                                  cohesion, affinity, bias, seed_creature, max_hazards,
                                  start_with_hazard=has_hazards and n % 2 == 0)
        if not picks:
            continue
        counts = Counter(c.uid for c in picks)
        lookup = {c.uid: c for c in picks}
        groups = sorted(((lookup[u], n) for u, n in counts.items()), key=lambda g: -g[0].level)
        enc = Encounter(groups, spent, budget)
        results.setdefault(enc.signature(), enc)
    ranked = sorted(results.values(), key=lambda e: (budget - e.xp, rng.random()))
    best = ranked[:count]
    if has_hazards:
        # When hazards are requested, make sure about half the options actually include one.
        with_h = [e for e in ranked if any(c.is_hazard for c, _ in e.groups)][:(count + 1) // 2]
        rest = [e for e in ranked if e not in with_h][:count - len(with_h)]
        best = sorted(with_h + rest, key=lambda e: budget - e.xp)
    for e in best:
        _annotate(e, party_level)
    return best


def _annotate(enc, party_level):
    gap = enc.budget - enc.xp
    if gap > 0:
        enc.warnings.append(f"{gap} XP under budget")
    total = sum(n for _, n in enc.groups)
    for c, n in enc.groups:
        diff = c.level - party_level
        if diff >= 3 and total == 1:
            enc.warnings.append(f"Solo PL+{diff} creature: expect swingy crits")
        elif diff >= 3:
            enc.warnings.append(f"{c.display_name} is PL+{diff}")
    if total >= 7:
        enc.warnings.append("Large group: watch action economy")


def encounter_to_dict(enc, name="", threat=""):
    return {"name": name, "threat": threat, "xp": enc.xp, "budget": enc.budget,
            "groups": [{"creature": c.to_dict(), "count": n} for c, n in enc.groups],
            "warnings": list(enc.warnings)}


def encounter_from_dict(d):
    from .models import Creature
    groups = [(Creature(**g["creature"]), g["count"]) for g in d.get("groups", [])]
    return Encounter(groups, d.get("xp", 0), d.get("budget", 0), list(d.get("warnings", [])))


def recompute(enc, party_level):
    """Recalculate XP and warnings after changing creatures in an encounter."""
    enc.xp = sum(xp_of(c, party_level) or 0 for c, n in enc.groups for _ in range(n))
    enc.warnings = []
    _annotate(enc, party_level)
    if enc.xp > enc.budget:
        enc.warnings.insert(0, f"{enc.xp - enc.budget} XP over budget")
    if any(xp_of(c, party_level) is None for c, _ in enc.groups):
        enc.warnings.insert(0, "A creature is outside the -4..+4 level range")
    return enc


# ---------------------------------------------------------------------------------------------- spending a budget exactly
# The Quest Builder (session.py) wants a fight that costs exactly the budget, described by concept ("a boss and four minions")
# rather than by named creatures. These find every way to spend the budget and pick one.
def budget_combos(budget, party_level, max_count=7):
    """All ways to spend a budget exactly: lists of (relative level, count). Creature levels stay at -1 or higher."""
    rels = [r for r in sorted(CREATURE_XP, reverse=True) if party_level + r >= -1]
    out = []

    def go(i, left, chosen, count):
        if left == 0:
            out.append(list(chosen))
            return
        if i >= len(rels) or count >= max_count:
            return
        r = rels[i]
        xp = CREATURE_XP[r]
        for n in range(left // xp, -1, -1):
            if n and count + n > max_count:
                continue
            if n:
                chosen.append((r, n))
            go(i + 1, left - n * xp, chosen, count + n)
            if n:
                chosen.pop()
    go(0, budget, [], 0)
    return out


def pick_combo(budget, party_level, rng):
    options = [c for c in budget_combos(budget, party_level) if 1 <= len(c) <= 3]
    if not options:
        options = budget_combos(budget, party_level)
    if not options:                                    # no exact way to spend it: go to the nearest budget below
        if budget > 20:
            return pick_combo(budget - 5, party_level, rng)
        return [(0, 1)], budget
    weights = []
    for c in options:
        n = sum(k for _, k in c)
        weights.append(3.0 if len(c) == 2 else (1.5 if len(c) == 1 else 1.0) * (1.0 if n <= 5 else 0.4))
    return rng.choices(options, weights=weights, k=1)[0], budget


def quest_fight(rl, level, size, threat):
    """A fight for the Quest Builder: the threat's XP budget for this party size, spent exactly. Returns (text, xp)."""
    budget = xp_budget(threat, size)
    combo, spent = pick_combo(budget, level, rl.rng)
    parts, xp_total = [], 0
    for idx, (rel, n) in enumerate(sorted(combo, key=lambda c: -c[0])):
        xp = CREATURE_XP[rel]
        xp_total += xp * n
        role = "quest.monster.boss" if (idx == 0 and rel >= 2) else ("quest.monster.minion" if rel <= -2 else "quest.monster.standard")
        concept = rl.roll(role)
        lvl = level + rel
        parts.append(f"{n} x level {lvl} ({xp} XP each): {concept}")
    head = f"{threat} threat for {size} PCs: {xp_total} XP of a {budget} XP budget (GM Core encounter budgets, adjusted for party size)."
    return head + "\n" + "\n".join(parts), xp_total

"""Treasure generation and ledger tracking based on Party Treasure by Level, plus the GM Tools salvage piles, peddler carts and
weird wares (items with a gimmick, in the style of a gnome peddler's cart).

Weird wares are built from an archetype (escalating risk, inverted weapon, literal reading, petty sentient, overly specific,
side-effect consumable, swap box) and get their numbers from the level tables. Tuning, not book rules: item bonuses (+1 up to
level 8, +2 up to level 16, +3 above), and how a salvage haul is priced (a share of the party currency in the Party Treasure by
Level table). The wording lives in the item.*, peddler.* and salvage.* tables in itemdata.py.
"""
import random
from dataclasses import dataclass, field

from . import gmtools as gt
from . import names
from .rules import TREASURE


@dataclass
class LootBundle:
    level: int
    permanent: list = field(default_factory=list)
    consumables: list = field(default_factory=list)
    currency: float = 0
    notes: list = field(default_factory=list)


def currency_for(level, party_size):
    t = TREASURE[level]
    return max(0, t["currency"] + (party_size - 4) * t["per_pc"])


def filter_items(items, rarities=None, magical_only=True, include_traits=None, exclude_names=(), systems=None):
    inc = {t.lower() for t in (include_traits or []) if t}
    out = []
    for i in items:
        if systems and (getattr(i, "system", "pf") or "pf") not in systems:
            continue
        if rarities and i.rarity not in rarities:
            continue
        if magical_only and not i.magical and not i.custom:
            continue
        if inc and not (inc & {t.lower() for t in i.traits}):
            continue
        if i.name in exclude_names:
            continue
        out.append(i)
    return out


def pick(items, level, consumable, n, rng, avoid=()):
    pool = [i for i in items if i.level == level and i.consumable == consumable and i.name not in avoid]
    if len(pool) <= n:
        rng.shuffle(pool)
        return pool
    return rng.sample(pool, n)


def extra_pc_items(level, party_size):
    """GM Core, Different Party Sizes: for each PC beyond four, add one permanent item of the party's
    level or 1 higher, and two consumables (one of the party's level, one 1 higher).
    Returns (permanent [(item level, count)], consumables [(item level, count)])."""
    extra = max(0, party_size - 4)
    perm, cons = {}, {}
    for i in range(extra):
        lvl = level + 1 if i % 2 == 0 else level       # alternate, starting with the higher item
        perm[lvl] = perm.get(lvl, 0) + 1
        cons[level] = cons.get(level, 0) + 1
        cons[level + 1] = cons.get(level + 1, 0) + 1
    return sorted(perm.items(), reverse=True), sorted(cons.items(), reverse=True)


def _merge_counts(base, extra):
    out = dict(base)
    for lvl, n in extra:
        out[lvl] = out.get(lvl, 0) + n
    return sorted(out.items(), reverse=True)


def targets(level, party_size):
    """Permanent/consumable (level, count) lists for this party size."""
    t = TREASURE[level]
    ep, ec = extra_pc_items(level, party_size)
    return _merge_counts(t["permanent"], ep), _merge_counts(t["consumables"], ec)


def _pick_with_fallback(items, lvl, consumable, n, rng, avoid, max_level=25):
    """Pick n items at lvl; if short (e.g. few level 21 items), fill from one level lower."""
    got = pick(items, min(lvl, max_level), consumable, n, rng, avoid)
    if len(got) < n and lvl > 1:
        taken = set(avoid) | {i.name for i in got}
        got += pick(items, lvl - 1, consumable, n - len(got), rng, taken)
    return got


def generate_level(items, level, party_size, seed=None, avoid=()):
    rng = random.Random(seed)
    b = LootBundle(level=level, currency=currency_for(level, party_size))
    perm_t, cons_t = targets(level, party_size)
    used = set(avoid)
    for kind, plan, consumable in (("permanent", perm_t, False), ("consumables", cons_t, True)):
        for lvl, n in plan:
            got = _pick_with_fallback(items, lvl, consumable, n, rng, used)
            used |= {i.name for i in got}
            getattr(b, kind).extend(got)
            if len(got) < n:
                b.notes.append(f"Only {len(got)}/{n} {'consumables' if consumable else 'permanent items'} "
                               f"available at level {lvl}")
    if party_size > 4:
        x = party_size - 4
        b.notes.append(f"Includes GM Core extras for {x} PC{'s' if x > 1 else ''} beyond four: "
                       f"+{x} permanent, +{2 * x} consumables, +currency")
    elif party_size < 4:
        b.notes.append("Party below 4 PCs: currency reduced; items kept (GM Core suggests subtracting less "
                       "for small groups)")
    return b


def ledger_summary(ledger, level, party_size):
    """Compare awarded treasure for a level against the table."""
    t = TREASURE[level]
    rows = [e for e in ledger if e["level"] == level]
    perm = sum(1 for e in rows if e["kind"] == "permanent")
    cons = sum(1 for e in rows if e["kind"] == "consumable")
    cur = sum(e["value_gp"] for e in rows if e["kind"] == "currency")
    value = sum(e["value_gp"] for e in rows)
    perm_t, cons_t = targets(level, party_size)
    # Total value is listed for four PCs; scale it for bigger parties (approximate: extra items vary in price).
    target_value = round(t["total"] * party_size / 4) if party_size > 4 else \
        t["total"] + (party_size - 4) * t["per_pc"]
    return {
        "permanent": (perm, sum(n for _, n in perm_t)),
        "consumables": (cons, sum(n for _, n in cons_t)),
        "currency": (cur, currency_for(level, party_size)),
        "value": (round(value, 2), target_value),
    }


def permanent_text(level):
    """The permanent items the Party Treasure by Level table gives for a level of play, as words."""
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    parts = [f"{words.get(n, n)} item{'s' if n != 1 else ''} of level {lv}" for lv, n in TREASURE[gt.clamp(int(level), 1, 20)]["permanent"]]
    return " and ".join(parts)


# ------------------------------------------------------------------------------------------------ weird wares, salvage, peddlers
POTION_TIERS = [(1, "minor healing potion"), (3, "lesser healing potion"), (6, "moderate healing potion"),
                (12, "greater healing potion"), (15, "major healing potion")]
WARE_SPELLS = {1: ["Heal", "Grease", "Sure Strike", "Ray of Frost", "Shield", "Fear", "Feather Fall", "Ventriloquism"],
          2: ["Invisibility", "Mirror Image", "Web", "Darkness"],
          3: ["Slow", "Haste", "Fireball", "Lightning Bolt"],
          4: ["Fly", "Dimension Door", "Freedom of Movement"]}
WARE_SKILLS = ["Athletics", "Acrobatics", "Stealth", "Diplomacy", "Deception", "Survival", "Crafting", "Society", "Perception"]


def item_bonus(level):
    return 1 if level <= 8 else (2 if level <= 16 else 3)


def potion_tier(level):
    name = POTION_TIERS[0]
    for lv, nm in POTION_TIERS:
        if level >= lv:
            name = (lv, nm)
    return name


def spell_for(rl, level):
    rank = gt.clamp((level + 1) // 2, 1, 4)
    return rl.choice(WARE_SPELLS[rank]), rank


def _escalating(rl, level, dc):
    box = rl.roll("item.container")
    starts = rl.choice([1, 2, 2, 3])
    reset = rl.roll("item.reset")
    variants = [
        (f"Duplicating {box.title()}", ["manipulate"], "two actions",
         f"Place one object of Bulk 1 or less inside the {box} and close it. When you open it, there are two of that object: the original and a perfect copy.",
         "all copies this item has ever made turn to ash. The originals are untouched, and so is the sense of loss.",
         "A box that copies anything, with a temper."),
        (f"Wand of Instant Cheese", ["manipulate"], "one action",
         "Point the wand at a clear surface within 10 feet. A wheel of excellent cheese appears there (Bulk 1, feeds four for a day).",
         f"the cheese turns on you: add a creature of level {max(-1, level - 2)} that is somehow made of cheese and wants to be reunited with its wheel.",
         "It makes cheese. It makes it with enthusiasm."),
        (f"Pocket Door", ["manipulate"], "two actions",
         "Touch a solid wall up to 1 foot thick. A 5-foot-wide door appears in it and opens onto the other side. It stays until you close it.",
         "the door opens onto somewhere awkward instead (the GM decides: a kitchen mid-argument, a courtroom, someone's bath).",
         "A door, wherever you need one, and sometimes elsewhere."),
        (f"Echo Bell", ["auditory", "manipulate"], "one action",
         "Ring the bell and say a phrase of up to ten words. One creature within 60 feet hears it as though a person it trusts had spoken.",
         "everyone within 120 feet hears the phrase as though a person they distrust had said it.",
         "A bell that repeats things, whether you like it or not."),
        (f"Lucky Coin", ["fortune", "manipulate"], "reaction",
         "Trigger You are about to make an attack roll or skill check. Effect You flip the coin and reroll the check, taking the better result.",
         "the coin becomes entirely ordinary, and your next check is made with misfortune.",
         "A lucky coin, if you are lucky with it."),
        (f"Hat of Growing Things", ["manipulate"], "two actions",
         "Put an object in the hat and wait one round. When you take it out, it is one size category larger for 1 hour.",
         "it grows two sizes and does not return to its size until sunrise.",
         "A hat that makes things grow, including its own opinion of itself."),
        (f"Teleporting Sock", ["teleportation", "manipulate"], "one action",
         "You teleport up to 30 feet to a place you can see, carried by a sock that does not belong to you.",
         "you teleport, but your boots do not.",
         "A sock that teleports, with excellent timing and poor judgment.")]
    name, traits, cost, does, fail, tag = rl.choice(variants)
    lines = [f"Activate [{cost}] ({', '.join(traits)}); Frequency unlimited; Effect {does}",
             f"Escalating Risk: Each time you use it, roll a d20. On a result of {starts} or lower, {fail} "
             f"Each use raises that number by 1 and the number resets {reset}."]
    return name, ["magical", "cursed"] + [t for t in traits if t not in ("manipulate",)], lines, tag


def _inverted(rl, level, dc):
    base = rl.roll("item.weapon")
    prefix = rl.choice(["Great", "", "", ""]) if rl.dial < 3 else rl.roll("item.prefix")
    if base.startswith("great") and prefix == "Great":
        prefix = ""
    effects = [
        ("Healing", "On a hit, the {base} deals no damage. Instead the target regains Hit Points equal to the damage you rolled (doubled on a critical hit). Undead and other creatures that are harmed by healing take the damage normally."),
        ("Cuddling", "On a hit, the {base} deals no damage. Instead the target gains temporary Hit Points equal to the damage you rolled, which last 1 minute."),
        ("Appreciation", f"On a hit, the {{base}} deals no damage. The target must succeed at a DC {dc} Will save or become friendly toward you for 1 minute, until you or an ally does something hostile to it."),
        ("Washing", "On a hit, the {base} deals no damage. Instead it ends one persistent damage condition of your choice affecting the target, and removes mud, grime, and fresh paint."),
        ("Cozy Naps", f"On a hit, the {{base}} deals no damage. The target must succeed at a DC {dc} Fortitude save or be slowed 1 for 1 round from sheer cosiness."),
        ("Mild Encouragement", "On a hit, the {base} deals no damage. Instead the target gains a +1 status bonus to its next attack roll within 1 minute, and compliments you on your form.")]
    eff, text = rl.choice(effects)
    name = f"{(prefix + ' ') if prefix else ''}{base.title()} of {eff}".strip()
    lines = [f"Strike: {text.format(base=base)}",
             f"Otherwise it is a perfectly ordinary {base}, and it is rather proud of that."]
    return name, ["magical", "evocation" if eff in ("Healing", "Cuddling") else "enchantment"], lines, \
        f"A {base} that hits, in the sense that it helps."


LITERAL = [
    ("Rope of Literal Climbing", "one action", ["manipulate"],
     "Throw the rope at any surface. It climbs to the top at a Climb Speed of 10 feet and stays there.",
     "It will not come down on its own, and it will not stay put after being told twice."),
    ("Lantern of Literal Revealing", "one action", ["manipulate", "light"],
     "Everything hidden in a 10-foot emanation is revealed: hidden creatures and objects stop being hidden.",
     "Each creature in the area must succeed at a DC {dc} Will save or blurt out a secret it is keeping."),
    ("Boots of Literal Leaping", "one action", ["concentrate"],
     "Command the boots to leap. They jump 20 feet in the direction you point.",
     "They go with or without your feet in them. It is always worth checking."),
    ("Gloves of Literal Grasping", "one action", ["manipulate"],
     "The gloves grasp whatever they are touching.",
     "Removing them from a held object takes an Athletics check against DC {dc}."),
    ("Hat of Literal Disguise", "one action", ["concentrate"],
     "The hat looks like a different hat.",
     "You do not. You look exactly as you did."),
    ("Bag of Holding Things Dear", "one action", ["manipulate"],
     "The bag holds whatever you put in it, and it will not drop it.",
     "Getting an item back out requires a Diplomacy check against DC {dc}, politely."),
    ("Cloak of Literal Hiding", "one action", ["manipulate"],
     "Set the cloak down and it becomes hidden (Stealth DC {dc} to notice).",
     "You, unfortunately, are still there."),
    ("Sword of Wounding Remarks", "one action", ["auditory", "emotion"],
     "Aim the sword at a creature within 30 feet. The sword says something wounding about it.",
     "The creature must succeed at a DC {dc} Will save or be frightened 1. The sword has opinions about your fighting too."),
    ("Shield of Literal Reflection", "one action", ["visual"],
     "Raise the shield. Creatures that can see it must succeed at a DC {dc} Reflex save or be dazzled until the start of your next turn.",
     "They are dazzled by their own reflection, and the shield will not stop commenting on how they look."),
    ("Candle of Embarrassing Light", "one action", ["light", "manipulate"],
     "The candle sheds bright light in a 20-foot radius.",
     "The light is exactly as bright as it needs to be to embarrass whatever you are looking at.")]


def _literal(rl, level, dc):
    name, cost, traits, does, quirk = rl.choice(LITERAL)
    lines = [f"Activate [{cost}] ({', '.join(traits)}); Effect {does.format(dc=dc)}", f"Literal: {quirk.format(dc=dc)}"]
    return name, ["magical"], lines, "It does exactly what the name says. Read the name carefully."


MOODS = [
    ("Vain", "compliment it sincerely (Diplomacy DC {dc})", "huffs and asks for a better compliment"),
    ("Lonely", "talk to it for 10 minutes (once a day is enough)", "insists on being carried in your hands for the rest of the day"),
    ("Hungry", "feed it a meal worth at least 1 sp, which it consumes", "rattles until it is fed"),
    ("Contrary", "ask it to do the opposite of what you want", "does exactly what you asked, which was the wrong thing"),
    ("Easily Bored", "tell it a story (Performance DC {dc})", "sighs loudly, then falls asleep"),
    ("Grumpy", "apologize to it (Diplomacy DC {dc})", "makes a remark about your previous owner")]


def _simple_effect(rl, level):
    roll = rl.rng.random()
    if roll < 0.4:
        b = item_bonus(level)
        sk = rl.choice(WARE_SKILLS)
        return f"you gain a +{b} item bonus to {sk} checks for 10 minutes"
    if roll < 0.75:
        sp, rank = spell_for(rl, level)
        return f"it casts {sp} (rank {rank}) once per day on your behalf, with a DC of {gt.dc(level)}"
    lv, nm = potion_tier(level)
    return f"you regain Hit Points as if you had drunk a {nm}, once per day"


def _sentient(rl, level, dc):
    base = rl.roll("item.tool")
    mood, demand, refuse = rl.choice(MOODS)
    eff = _simple_effect(rl, level)
    lines = [f"Mood: {mood}. Before it will work, you must {demand.format(dc=dc)}.",
             f"Activate [one action] (concentrate); Effect If its demand is met, {eff}.",
             f"If the demand is not met, the item {refuse}, and you can try again in 10 minutes."]
    name = f"{mood} {base.title()}"
    return name, ["magical", "intelligent"], lines, f"A {base} with feelings, all of them strong."


def _specific(rl, level, dc):
    base = rl.roll("item.tool")
    cond, short = rl.payload("item.condition")
    b = item_bonus(level)
    what = rl.choice(["attack rolls", "Stealth checks", "saving throws", "Diplomacy checks", "Perception checks"])
    lines = [f"Effect You gain a +{b} item bonus to {what} {cond}.",
             "Otherwise it does nothing at all, and the item is smug about it."]
    name = f"{base.title()} of {short or 'Conditions'}"
    return name, ["magical", "invested"], lines, "It works wonderfully, under conditions."


def _consumable(rl, level, dc):
    side = rl.roll("item.side")
    kind = rl.choice(["heal", "heal", "dark", "bonus"])
    lv, nm = potion_tier(level)
    if kind == "heal":
        eff = f"You regain Hit Points as if you had drunk a {nm}."
        name = rl.choice(["Pretty Good Healing Tonic", "Almost Medicinal Draught", "Questionable Remedy", "Cheerful Restorative"])
        itemlv = lv
    elif kind == "dark":
        eff = "You gain darkvision for 1 hour."
        name = rl.choice(["Tonic of Seeing Dim Things", "Cave-Eye Syrup"])
        itemlv = gt.clamp(level, 2, 8)
    else:
        eff = f"You gain a +1 status bonus to Athletics checks for 10 minutes."
        name = rl.choice(["Mug of Moderate Strength", "Sturdy Brew"])
        itemlv = gt.clamp(level, 1, 6)
    lines = [f"Activate [one action] (manipulate); Effect {eff}", f"Side effect: {side}."]
    return name, ["consumable", "magical", "potion"], lines, "Drinks well. Not always kindly.", itemlv


def _swap(rl, level, dc):
    box = rl.roll("item.container")
    lines = [f"Activate [one minute] (manipulate); Effect Place one item of level {max(0, level - 1)} or lower inside the {box} and close it. "
             f"When it is opened, the {box} contains a different item of the same level or lower, chosen from the GM's secret list.",
             "One time in six, it is your original item, wrong in some small way the GM decides."]
    return f"Swapping {box.title()}", ["magical"], lines, "You put something in; something comes out."


ARCHETYPES = {"escalating": _escalating, "inverted": _inverted, "literal": _literal, "sentient": _sentient,
              "specific": _specific, "consumable": _consumable, "swap": _swap}
ARCHETYPE_NAMES = {"escalating": "Escalating risk", "inverted": "Inverted weapon", "literal": "Literal reading",
                   "sentient": "Petty sentient", "specific": "Overly specific", "consumable": "Side-effect consumable",
                   "swap": "Swapping box"}


def usage_for(name, kind):
    n = name.lower()
    if kind == "consumable":
        return "-"
    for word, use in (("boots", "worn boots"), ("gloves", "worn gloves"), ("hat", "worn headwear"), ("cloak", "worn cloak"),
                      ("sock", "worn footwear")):
        if word in n:
            return use
    if "swapping" in n or "duplicating" in n or "pocket door" in n or "greataxe" in n or "halberd" in n or "shortbow" in n:
        return "held in 2 hands"
    return "held in 1 hand"


def weird_item(rl, level, kind=None):
    """A weird ware as a dict: name, level, traits, usage, lines, pitch, price, counts_as, kind."""
    kind = kind or rl.choice(list(ARCHETYPES))
    level = gt.clamp(int(level), 1, 20)
    lvl = gt.clamp(level + rl.choice([-1, 0, 0, 1]), 1, 20)
    dc = gt.dc(lvl)
    out = ARCHETYPES[kind](rl, lvl, dc)
    name, traits, lines, tag = out[0], out[1], out[2], out[3]
    if len(out) > 4:
        lvl = out[4]
    traits = list(dict.fromkeys(["uncommon"] + traits))
    usage = usage_for(name, kind)
    price = f"{rl.rng.randint(2, 18) * max(1, lvl)} gp" + (" " + rl.roll("item.price.extra") if rl.chance(0.6) else "")
    price = price.strip()
    counts = ("a consumable item of level %d" % lvl) if kind == "consumable" else ("a permanent item of level %d" % lvl)
    return {"name": name, "level": lvl, "traits": traits, "usage": usage, "lines": lines, "tag": tag, "kind": kind,
            "pitch": rl.roll("item.pitch"), "price": price, "counts_as": counts}


def item_text(d, pitch=True):
    head = f"{d['name']}   Item {d['level']}"
    lines = [head, f"Traits: {', '.join(t.title() for t in d['traits'])}"]
    if d["usage"] != "-":
        lines.append(f"Usage: {d['usage']}")
    lines += d["lines"]
    if pitch:
        lines.append(f"Sold with the words: {d['pitch']}")
    lines.append(f"Price: {d['price']} (peddler's price)")
    lines.append(f"Treasure: counts as {d['counts_as']} toward the party's treasure ({permanent_text(d['level'])} per level of play).")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ SALVAGE / PEDDLER
HAUL = {"Scraps": (4, 0.10, 0.10), "Pile": (7, 0.25, 0.35), "Cartload": (10, 0.5, 0.6), "Hoard": (14, 1.0, 1.0)}
SALVAGE_OPTIONS = [
    gt.opt("what", "What", "choice", "Salvage", ["Salvage", "Peddler's cart"], width=14),
    gt.opt("haul", "Haul", "choice", "Pile", list(HAUL), width=10, hint="How much there is. Peddler's cart ignores this."),
    gt.opt("where", "Where", "choice", "", [], free=True, width=34, hint="blank = chosen for you", source="place"),
    gt.LEVEL_OPT, gt.SIZE_OPT,
    gt.opt("weird", "Weird find", "choice", "Maybe", ["Never", "Maybe", "Always"], width=8),
    gt.opt("wares", "Wares", "int", 5, width=4, hint="How many items the peddler's cart has."),
    gt.SILLY_OPT, gt.FLAVOR_OPT]


def _split(total, n, rng):
    cuts = sorted(rng.random() for _ in range(n - 1))
    parts, last = [], 0.0
    for c in cuts + [1.0]:
        parts.append(max(0.05, c - last)); last = c
    s = sum(parts)
    return [total * p / s for p in parts]


def generate_salvage(params, rng=None):
    rng = rng or random.Random()
    rl = gt.Roller(rng, params["silly"], params["flavor"], params["level"])
    level = gt.clamp(params["level"], 1, 20)
    size = params["size"]
    if params["what"].lower().startswith("peddler"):
        return generate_peddler(params, rl, level)
    count, frac, weird_p = HAUL.get(params["haul"], HAUL["Pile"])
    where = params["where"].strip() or rl.roll("salvage.where")
    budget = currency_for(gt.clamp(level, 1, 20), size) * frac
    n_valuable = {"Scraps": 0, "Pile": 1, "Cartload": 2, "Hoard": 3}.get(params["haul"], 1)
    n_useful = max(1, count // 3)
    n_junk = count - n_valuable - n_useful
    val_total = budget * 0.65
    use_total = budget * 0.35
    rows = [gt.row("Found at", where, "info"), gt.row("Value budget", f"about {gt.money(budget)} in all (a share of the party currency for level {level}, from the Party Treasure by Level table)", "info", gm=True)]
    real_total = 0.0
    for amount in (_split(val_total, n_valuable, rng) if n_valuable else []):
        amount = max(0.1, round(amount, 2))
        real_total += amount
        rows.append(gt.row("Valuable", f"{rl.roll('salvage.valuable')}, worth about {gt.money(amount)}", "find-valuable"))
    for amount in _split(use_total, n_useful, rng):
        amount = max(0.05, round(amount, 2))
        text, tag = rl.payload("salvage.useful")
        real_total += amount
        rows.append(gt.row("Useful", f"{text} ({tag or 'parts'}), worth about {gt.money(amount)} to a crafter or quartermaster", "find-useful"))
    for _ in range(max(0, n_junk)):
        cp = rng.randint(1, 9)
        real_total += cp / 100
        rows.append(gt.row("Junk", f"{rl.roll('salvage.junk')}, worth {cp} cp, if that", "find-junk"))
    show_weird = {"Never": False, "Always": True}.get(params["weird"], rng.random() < weird_p)
    if show_weird:
        d = weird_item(rl, level)
        rows.append(gt.row("Odd find: " + d["name"], item_text(d), "block", item=d))
    rows.insert(2, gt.row("Total", f"about {gt.money(real_total)}, before anyone haggles", "info"))
    title = f"Salvage: {params['haul'].lower()} at {where}"
    return gt.result("salvage", title, rows, params)


def generate_peddler(params, rl, level):
    rng = rl.rng
    anc = "gnome" if rl.dial >= 2 or rng.random() < 0.5 else gt.pick_ancestry(rng, params["flavor"])
    name = rl.roll("peddler.name.gnome") if anc == "gnome" else names.make_name(anc, rng)
    anc = anc.lower()
    cart = rl.roll("peddler.cart")
    n = gt.clamp(params["wares"], 1, 12)
    rows = [gt.row("Peddler", f"{name}, {gt.article(anc)} {anc}, with {cart}", "info"),
            gt.row("Patter", rl.roll("item.pitch"), "info", player="")]
    kinds = list(ARCHETYPES)
    rng.shuffle(kinds)
    for i in range(n):
        d = weird_item(rl, level, kinds[i % len(kinds)])
        rows.append(gt.row(d["name"], item_text(d, pitch=True), "block", item=d))
    rows[1]["player"] = None
    return gt.result("salvage", f"Peddler's cart: {name}", rows, params)


TOOL_SALVAGE = {"key": "salvage", "label": "Salvage & Wares", "options": SALVAGE_OPTIONS, "generate": generate_salvage, "multi": True,
                "page_type": "Note",
                "intro": "Roll a pile of salvage or a peddler's cart of weird wares. Odd finds are full item blocks."}

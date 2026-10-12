"""Shop generator: stock for a settlement, sized and leveled by settlement level, in themed shops.

GM Core gives settlements a level that caps what is normally for sale; items above it are rare finds. A shop stocks mostly
items at or below the settlement level, a few one or two levels above ("special orders"), and can be any size you need,
from a village stall of 8 to a grand bazaar of 300 different items. Counts and quantities are a table aid, not a rule.

Themed shops (a blacksmith, an alchemist, a rune dealer...) draw most of their stock from what that kind of shop sells and
the rest from related sundries. Each theme says what counts as its own with plain rules (item types, traits, and name
words), so a theme works with whatever is in your downloaded data, and the shop tells you when your data has fewer
matching items than you asked for instead of quietly filling the shelves with something else.
"""
import random
import re
from dataclasses import dataclass, field

from .models import price_text

# Traits that make an item magical. The tradition traits count: the Magic Items generator saves its items with a tradition
# and often no "magical" trait at all, and Foundry's own data uses them too. "alchemical" is not here: alchemical gear is
# not magical (the index's own magical flag is true for it, which is why the shops don't use that flag).
TRADITIONS = {"arcane", "divine", "occult", "primal"}
MAGICAL = {"magical"} | TRADITIONS
MAGIC_TRAITS = MAGICAL | {"invested", "rune", "wand", "scroll", "staff", "talisman", "potion", "spellheart"}
OUTLAW = {"alchemical", "poison", "illicit"}     # not on a general shelf: the Alchemist and the Black market sell these
NOT_SOLD = {"artifact"}                          # nobody sells these


def _w(*words):
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.IGNORECASE)


GEAR = {"equipment", "backpack"}                 # the index holds weapon, armor, shield, equipment, consumable, backpack, ammo
ARMS = {"weapon", "armor", "shield"}

# Each theme: types / traits / words say what the shop sells. word_types limits the name words to those item types.
# need_traits: an item must carry one of these. not_*: things the shop never sells. also: related sundries.
# focus: the share of the stock that is the shop's own specialty. cons_share: the share that is consumable.
SHOP_TYPES = {
    "General store": {
        "blurb": "Everyday gear and supplies, with a few basic arms. Nothing magical.",
        "not_types": ARMS, "not_traits": MAGIC_TRAITS | OUTLAW, "cons_share": 0.25, "focus": 0.9,
        "also": {"types": ARMS, "not_traits": MAGIC_TRAITS},
        "shop": ["General Store", "Mercantile", "Trading Post", "Provisioner", "Emporium"],
        "thing": ["Barrel", "Cart", "Lantern", "Pump", "Scale"]},
    "Adventuring outfitter": {
        "blurb": "Packs, rope, tools, and travel gear for people heading somewhere dangerous.",
        "types": GEAR, "not_traits": MAGIC_TRAITS | OUTLAW, "cons_share": 0.2, "focus": 0.9,
        "also": {"types": {"consumable", "ammo"}, "not_traits": MAGIC_TRAITS | OUTLAW},
        "shop": ["Outfitters", "Supply", "Provisions", "Pack and Rope", "Wayfarer's Supply"],
        "thing": ["Pack", "Rope", "Compass", "Boot", "Lantern"]},
    "Blacksmith (weapons and armor)": {
        "blurb": "Ordinary weapons, armor, and shields, plus ironmongery and tools.",
        "types": ARMS, "not_traits": MAGIC_TRAITS, "cons_share": 0.1, "focus": 0.88,
        "also": {"words": _w("tools?", "hammers?", "crowbars?", "anvils?", "whetstones?", "repair", "chains?", "manacles",
                             "shackles", "caltrops", "pitons?", "grappling", "crampons", "horseshoes?", "tongs", "nails?"),
                 "not_traits": MAGIC_TRAITS},
        "shop": ["Forge", "Smithy", "Ironworks", "Hammer and Tongs", "Smithworks"],
        "thing": ["Anvil", "Hammer", "Bellows", "Tongs", "Forge"]},
    "Weaponsmith": {
        "blurb": "Weapons of every ordinary kind, with ammunition.",
        "types": {"weapon"}, "not_traits": MAGIC_TRAITS, "cons_share": 0.15, "focus": 0.88,
        "also": {"words": _w("arrows?", "bolts?", "bullets?", "ammunition", "ammo", "pellets?", "cartridges?"),
                 "consumable": True, "not_traits": MAGIC_TRAITS},
        "shop": ["Arms", "Armory", "Blades", "Weaponry", "Arms and Edges"],
        "thing": ["Blade", "Edge", "Pike", "Axe", "Spear"]},
    "Armorer": {
        "blurb": "Armor and shields, with fittings and repairs.",
        "types": {"armor", "shield"}, "not_traits": MAGIC_TRAITS, "cons_share": 0.0, "focus": 0.95,
        "also": {"words": _w("shields?", "armor", "helms?", "gauntlets?", "bucklers?", "repair", "barding", "buckles?"),
                 "not_traits": MAGIC_TRAITS},
        "shop": ["Armory", "Harness and Mail", "Plate and Mail", "Armorers", "Shield and Mail"],
        "thing": ["Shield", "Helm", "Gauntlet", "Cuirass", "Buckler"]},
    "Bowyer and fletcher": {
        "blurb": "Bows, crossbows, slings, and the ammunition for them.",
        "words": _w(r"\w*bows?", "slings?", "arrows?", "bolts?", "bullets?", "quivers?", "darts?", "javelins?",
                    "blowguns?", "ammunition", "ammo", "shuriken", "boomerangs?"),       # \w*bow: Shortbow, Longbow, Crossbow
        "word_types": {"weapon", "ammo"}, "not_traits": MAGIC_TRAITS, "cons_share": 0.5, "focus": 0.95,
        "shop": ["Bowyers", "Fletchery", "Bows and Bolts", "Archery Supply", "Quiver and String"],
        "thing": ["Quiver", "Arrow", "Bowstring", "Fletching", "Crossbow"]},
    "Alchemist": {
        "blurb": "Alchemical elixirs, bombs, tools, and reagents.",
        "traits": {"alchemical"}, "words": _w("elixirs?", "bombs?", "antidotes?", "antiplague", "tindertwigs?", "alchemist'?s?",
                                              "acid flask", "oil of"),
        "not_traits": {"illicit"}, "cons_share": 0.85, "focus": 0.95,
        "also": {"words": _w("vials?", "flasks?", "mortar", "crucible", "reagents?"), "not_traits": MAGIC_TRAITS},
        "shop": ["Alchemy", "Alembic", "Apothecary and Alchemy", "Elixirs", "Reagents"],
        "thing": ["Alembic", "Retort", "Vial", "Cauldron", "Crucible"]},
    "Apothecary and healer": {
        "blurb": "Salves, tonics, antidotes, and the tools of healing.",
        "traits": {"healing"}, "words": _w("healer'?s?", "salves?", "tonics?", "bandages?", "antidotes?", "antiplague", "herbs?",
                                           "poultices?", "smelling salts", "elixir of life", "restorative", "panacea",
                                           "cordial", "remedy", "healing", "medic"),
        "not_traits": {"staff", "wand", "rune", "scroll", "talisman", "illicit"},        # healing potions yes, a Staff of Healing no
        "cons_share": 0.8, "focus": 0.9,
        "shop": ["Apothecary", "Herbalist", "Healing House", "Remedies", "Salves and Tonics"],
        "thing": ["Mortar", "Poultice", "Lancet", "Tonic", "Herb"]},
    "Magic shop": {
        "blurb": "Anything magical, from potions to worn items.",
        "traits": MAGICAL, "cons_share": 0.4, "focus": 1.0,
        "shop": ["Arcana", "Wonders", "Curios and Charms", "Enchantments", "Thaumaturgy"],
        "thing": ["Lantern", "Star", "Sigil", "Wand", "Orb"]},
    "Scrolls and wands": {
        "blurb": "Scrolls, wands, staves, and the like.",
        "traits": {"scroll", "wand", "staff"}, "words": _w("scrolls?", "wands?", "staves", "staff", "spellheart"),
        "need_traits": MAGICAL,                  # the plain Staff weapon is not a magic staff
        "cons_share": 0.7, "focus": 0.95,
        "shop": ["Scribes", "Scrolls and Wands", "Quill and Wand", "Spellwright", "Ink and Ember"],
        "thing": ["Quill", "Scroll", "Inkwell", "Wand", "Seal"]},
    "Curio dealer (worn and held magic items)": {
        "blurb": "Lasting magic items you wear or carry: cloaks, rings, boots, and trinkets.",
        "traits": MAGICAL, "consumable": False, "not_types": ARMS, "not_traits": {"wand", "staff", "scroll", "rune"},
        "cons_share": 0.0, "focus": 1.0,
        "shop": ["Curios", "Oddments", "Trinkets and Treasures", "Rarities", "Keepsakes"],
        "thing": ["Curio", "Trinket", "Oddment", "Cabinet", "Locket"]},
    "Rune dealer": {
        "blurb": "Potency, striking, resilient, and property runes for weapons and armor.",
        "traits": {"rune"}, "words": _w("potency", "striking", "resilient", "fortification", "ghost touch", "disrupting",
                                        "flaming", "frost", "shock", "corrosive", "thundering", "wounding", "returning", "keen",
                                        "grievous", "holy", "unholy", "slick", "shadow", "invisibility", "glamered",
                                        "energy-resistant", "ready", "bolstering", "rune", "reinforcing", "anarchic",
                                        "axiomatic", "vorpal", "speed", "spell-storing", "spell storing", "serrating",
                                        "impactful", "bloodthirsty", "brilliant", "dancing", "deathless", "hopeful",
                                        "fire-resistant", "cold-resistant", "acid-resistant", "electricity-resistant",
                                        "antimagic", "assisting", "bitter", "advancing"),
        "need_traits": MAGICAL | {"rune"},       # "Holy Symbol (Wooden)" is not a holy rune
        "name_not": re.compile(r"\bof\b", re.IGNORECASE),     # runes have short names: "Boots of Speed" is not one
        "word_types": {"equipment"}, "cons_share": 0.0, "focus": 1.0,
        "shop": ["Runewrights", "Runes and Etchings", "Engravers", "Sigilworks", "Chisel and Rune"],
        "thing": ["Rune", "Chisel", "Sigil", "Stone", "Etching"]},
    "Magic armory (specific magic weapons and armor)": {
        "blurb": "Individual enchanted weapons, armor, and shields.",
        "types": ARMS, "need_traits": MAGICAL, "cons_share": 0.0, "focus": 1.0,
        "shop": ["Armory", "Arms of Power", "Enchanted Arms", "War Relics", "Arsenal"],
        "thing": ["Aegis", "Warding", "Sigil", "Banner", "Bastion"]},
    "Black market": {
        "blurb": "Poisons, illicit goods, and thieves' gear, sold quietly.",
        "traits": {"illicit", "poison"}, "words": _w("poisons?", "forged", "forgery", "disguise", "thieves'?", "lockpicks?",
                                                    "smoke", "toxins?", "venom", "counterfeit", "knockout", "cutpurse"),
        "not_traits": MAGIC_TRAITS, "cons_share": 0.6, "focus": 0.85,
        "also": {"words": _w("lockpicks?", "disguise", "thieves'?", "rope", "grappling", "crowbar", "dark", "mask", "cloak"),
                 "not_traits": MAGIC_TRAITS},
        "shop": ["Back Door", "Quiet Wares", "Fence", "Under the Counter", "Shadow Market"],
        "thing": ["Lamp", "Shadow", "Latch", "Coin", "Hood"]},
    "Tech dealer (Starfinder)": {
        "blurb": "Starfinder technology and equipment.",
        "traits": {"tech"}, "cons_share": 0.4, "focus": 1.0,
        "shop": ["Tech", "Circuits", "Salvage and Systems", "Parts and Packs", "Gear Dock"],
        "thing": ["Circuit", "Nova", "Dock", "Relay", "Core"]},
}

# story themes a shop's Notebook page carries, so Story Forge can use the shop as a place
THEME_TAGS = {
    "General store": ["trade"], "Adventuring outfitter": ["trade", "road"],
    "Blacksmith (weapons and armor)": ["craft", "trade", "military"], "Weaponsmith": ["craft", "trade", "military"],
    "Armorer": ["craft", "trade", "military"], "Bowyer and fletcher": ["craft", "trade", "nature"],
    "Alchemist": ["magic", "craft", "trade"], "Apothecary and healer": ["disease", "nature", "trade"],
    "Magic shop": ["magic", "trade"], "Scrolls and wands": ["magic", "trade"],
    "Curio dealer (worn and held magic items)": ["magic", "trade", "treasure"], "Rune dealer": ["magic", "craft"],
    "Magic armory (specific magic weapons and armor)": ["magic", "military", "treasure"], "Black market": ["crime", "trade"],
    "Tech dealer (Starfinder)": ["trade"],
}

SIZES = {"Village": 8, "Town": 14, "City": 22, "Metropolis": 32, "Market district": 60, "Grand bazaar": 120}
MAX_COUNT = 400

OWNERS = ["Tamsin", "Hollis", "Brenna", "Osric", "Mattis", "Willa", "Garrick", "Nell", "Fenna", "Corin", "Bram", "Una",
          "Pell", "Dessa", "Joss", "Hester", "Orla", "Dunstan", "Maren", "Tobias", "Ilse", "Rafe", "Sorrel", "Quill",
          "Edda", "Perrin", "Wynn", "Ansel", "Mirel", "Gideon"]
ADJECTIVES = ["Rusty", "Gilded", "Iron", "Crooked", "Silver", "Hollow", "Merry", "Lucky", "Quiet", "Broken", "Copper",
              "Black", "Sleepy", "Golden", "Bent", "Honest", "Dented", "Wandering"]


def theme_names():
    return list(SHOP_TYPES)


def make_shop_name(theme, rng=None):
    """A name that fits the theme: 'Tamsin's Forge' or 'The Rusty Anvil'."""
    rng = rng or random.Random()
    spec = SHOP_TYPES.get(theme, SHOP_TYPES["General store"])
    if rng.random() < 0.6:
        return f"{rng.choice(OWNERS)}'s {rng.choice(spec['shop'])}"
    return f"The {rng.choice(ADJECTIVES)} {rng.choice(spec['thing'])}"


# ------------------------------------------------------------------------------------------------ what an item is
def _traits(item):
    return {str(t).lower() for t in (getattr(item, "traits", None) or [])}


_SAVED_WEAPON = re.compile(r"(?m)^Weapon .*\n(?:.*\n)*?^Damage \d")
_SAVED_ARMOR = re.compile(r"(?m)^Armor .*\n(?:.*\n)*?^AC bonus ")


def _kind(item):
    """The item's type. A runic weapon or armor the Magic Items generator saved before it learned to set the type is
    recognized by the stat lines in its notes, so those older saved items still sort into the right shop."""
    kind = str(getattr(item, "item_type", "") or "").lower()
    if kind == "equipment" and getattr(item, "custom", False):
        notes = str(getattr(item, "notes", "") or "")
        if "Damage " in notes and _SAVED_WEAPON.search(notes):
            return "weapon"
        if "AC bonus " in notes and _SAVED_ARMOR.search(notes):
            return "armor"
    return kind


def _level(item):
    try:
        return int(getattr(item, "level", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _price_text(item):
    try:
        return price_text(item)
    except Exception:
        return "no price"


def _price(item):
    try:
        return float(getattr(item, "price_gp", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _credits(item):
    try:
        return float(getattr(item, "price_credits", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def is_mundane(item):
    return not (_traits(item) & MAGIC_TRAITS)


def purchasable(item):
    """Whether a shop could sell it: not an artifact, and a magic item has to have a price (the index has none for
    artifacts and a few unique items, so they would otherwise sit on a shelf at no cost)."""
    if _traits(item) & NOT_SOLD:
        return False
    return not (_price(item) <= 0 and _credits(item) <= 0 and not is_mundane(item))


def matches(item, spec):
    """Whether an item belongs to a shop spec (a theme, or its 'also' sundries)."""
    if not spec:
        return False
    kind, tr, name = _kind(item), _traits(item), str(getattr(item, "name", "") or "")
    if spec.get("not_types") and kind in spec["not_types"]:
        return False
    if spec.get("not_traits") and tr & spec["not_traits"]:
        return False
    if spec.get("need_traits") and not (tr & spec["need_traits"]):
        return False
    if spec.get("name_not") and spec["name_not"].search(name):
        return False
    cons = spec.get("consumable")
    if cons is not None and bool(getattr(item, "consumable", False)) != cons:
        return False
    positive = spec.get("types") or spec.get("traits") or spec.get("words")
    if not positive:
        return True                                   # no positive rule: anything that passes the filters above
    if spec.get("types") and kind in spec["types"]:
        return True
    if spec.get("traits") and tr & spec["traits"]:
        return True
    words = spec.get("words")
    return bool(words and words.search(name) and (not spec.get("word_types") or kind in spec["word_types"]))


# ------------------------------------------------------------------------------------------------ the shop
@dataclass
class Line:
    item: object
    tag: str = "stock"          # stock or special order
    qty: int = 1
    side: bool = False          # a related sundry rather than the shop's own specialty


@dataclass
class Shop:
    name: str = ""
    theme: str = "General store"
    level: int = 1
    count: int = 14
    lines: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)

    def total_gp(self):
        """Value of everything on the shelves, in gp, for Pathfinder items (Starfinder prices are credits)."""
        return sum(_price(l.item) * l.qty for l in self.lines if getattr(l.item, "system", "pf") in ("pf", "", None))

    def total_credits(self):
        """Value of everything on the shelves in credits, for Starfinder items (their prices are credits, not gp)."""
        return sum(_credits(l.item) * l.qty for l in self.lines if getattr(l.item, "system", "pf") == "sf")

    def items(self):
        return [l.item for l in self.lines]


def _weight_fn(level):
    def w(i):
        return max(0.1, 1.0 + 0.4 * max(0, _level(i) - level + 4))     # favor items near the settlement level
    return w


def _draw(src, k, rng, wfun):
    src, out = list(src), []
    while k > 0 and src:
        i = rng.choices(range(len(src)), weights=[wfun(x) for x in src], k=1)[0]
        out.append(src.pop(i))
        k -= 1
    return out


def _pick(cands, k, cons_share, rng, wfun):
    """k items, weighted toward the settlement level, with about cons_share of them consumable. If one kind runs out the
    other fills the gap, so the shelves are as full as the data allows."""
    if k <= 0 or not cands:
        return []
    cons = [i for i in cands if getattr(i, "consumable", False)]
    perm = [i for i in cands if not getattr(i, "consumable", False)]
    kc = min(len(cons), int(round(k * cons_share)))
    kp = min(len(perm), k - kc)
    short = k - kc - kp
    if short > 0:
        more = min(len(cons) - kc, short)
        kc += more
        short -= more
        kp += min(len(perm) - kp, short)
    return _draw(cons, kc, rng, wfun) + _draw(perm, kp, rng, wfun)


def _qty(item, level, rng):
    """How many are on the shelf: cheap consumables and everyday gear come in numbers, magic items one at a time."""
    if _level(item) > level:
        return 1
    gap = level - _level(item)
    if getattr(item, "consumable", False):
        return rng.randint(1, 6 if gap >= 4 else 4 if gap >= 2 else 3)
    if is_mundane(item):
        price = _price(item) or _credits(item)
        return rng.randint(1, 4 if price <= 5 else 3 if price <= 30 else 2 if price <= 150 else 1)
    return 1


def _pool(items, level, rarities, special_orders, exclude):
    cap = level + (2 if special_orders else 0)
    out, seen = [], set(exclude)
    for i in items:
        name = str(getattr(i, "name", "")).lower()
        if name in seen or (rarities and getattr(i, "rarity", "common") not in rarities) or _level(i) > cap \
                or not purchasable(i):
            continue
        seen.add(name)
        out.append(i)
    return out


def _select(items, level, count, spec, rarities, special_orders, focus, rng, exclude=()):
    """Pick up to `count` items. Returns ([(item, tag, side)], notes)."""
    wfun = _weight_fn(level)
    pool = _pool(items, level, rarities, special_orders, exclude)
    side_spec = spec.get("also")
    core = [i for i in pool if matches(i, spec)]
    side = [i for i in pool if side_spec and not matches(i, spec) and matches(i, side_spec)]
    cons_share = spec.get("cons_share", 0.4)
    notes = []
    core_stock = [i for i in core if _level(i) <= level]
    core_spec = [i for i in core if _level(i) > level]
    side_stock = [i for i in side if _level(i) <= level]
    side_spec_items = [i for i in side if _level(i) > level]
    n_special = min(len(core_spec) + len(side_spec_items), max(1, count // 8), count) if special_orders else 0
    n_stock = count - n_special
    n_side = int(round(n_stock * (1 - focus))) if side_stock else 0
    n_core = n_stock - n_side
    got_core = _pick(core_stock, n_core, cons_share, rng, wfun)
    if len(got_core) < n_core:                                  # the specialty ran out: sundries fill the gap
        n_side += n_core - len(got_core)
    got_side = _pick(side_stock, n_side, min(cons_share, 0.3), rng, wfun)
    if len(got_core) + len(got_side) < n_stock:                 # sundries ran out too: more of the specialty, if any left
        left = [i for i in core_stock if i not in got_core]
        got_core += _pick(left, n_stock - len(got_core) - len(got_side), cons_share, rng, wfun)
    specials = _pick(core_spec, n_special, cons_share, rng, wfun)
    if len(specials) < n_special:
        specials += _pick(side_spec_items, n_special - len(specials), cons_share, rng, wfun)
    out = [(i, "stock", False) for i in got_core] + [(i, "stock", True) for i in got_side] + \
          [(i, "special order", i in side_spec_items) for i in specials]
    if not core:
        notes.append("Nothing in your data matches this kind of shop at this level and rarity.")
    return out, notes


def _a(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def _shortfall_note(got, count, level, rarities, theme, more=False):
    if got >= count:
        return None
    rar = "/".join(sorted(rarities)) if rarities else "any rarity"
    kind = theme.split(" (")[0].lower()
    return (f"Only {got}{' more' if more else ''} different items in your data fit {_a(kind)} {kind} at settlement level {level} "
            f"({rar}). Raise the settlement level, allow uncommon items, or lower the specialty share to stock more.")


def _sort(lines):
    lines.sort(key=lambda l: (l.tag != "stock", _level(l.item), str(l.item.name)))


def build_shop(items, level, count=14, theme="General store", rarities=("common",), special_orders=True, quantities=True,
               focus=None, seed=None, name=None):
    """A stocked shop. count is the number of different items (1 to 400); with quantities on, cheap consumables and
    everyday gear come in several copies. focus (0 to 1) is the share of stock that is the shop's own specialty."""
    rng = random.Random(seed)
    spec = SHOP_TYPES.get(theme, SHOP_TYPES["General store"])
    count = max(1, min(MAX_COUNT, int(count)))
    level = max(0, int(level))
    rarities = set(rarities or ())
    f = spec.get("focus", 0.9) if focus is None else max(0.0, min(1.0, float(focus)))
    picks, notes = _select(items, level, count, spec, rarities, special_orders, f, rng)
    lines = [Line(i, tag, _qty(i, level, rng) if quantities else 1, side) for i, tag, side in picks]
    _sort(lines)
    note = _shortfall_note(len(lines), count, level, rarities, theme)
    if note and not notes:
        notes.append(note)
    return Shop(name=name or make_shop_name(theme, rng), theme=theme, level=level, count=count, lines=lines, notes=notes,
                settings={"rarities": sorted(rarities), "special_orders": bool(special_orders), "quantities": bool(quantities),
                          "focus": f})


def add_more(shop, items, k, seed=None):
    """Add up to k more different items to an existing shop, in the same theme. Returns how many were added."""
    rng = random.Random(seed)
    st = shop.settings
    spec = SHOP_TYPES.get(shop.theme, SHOP_TYPES["General store"])
    k = max(0, min(MAX_COUNT, int(k)))
    have = {str(l.item.name).lower() for l in shop.lines}
    picks, _ = _select(items, shop.level, k, spec, set(st.get("rarities") or ()), st.get("special_orders", True),
                       st.get("focus", spec.get("focus", 0.9)), rng, exclude=have)
    added = [Line(i, tag, _qty(i, shop.level, rng) if st.get("quantities", True) else 1, side) for i, tag, side in picks]
    shop.lines += added
    shop.count = len(shop.lines)
    _sort(shop.lines)
    shop.notes = [n for n in shop.notes if not n.startswith("Only ")]            # an out-of-date shortfall note
    note = _shortfall_note(len(added), k, shop.level, set(st.get("rarities") or ()), shop.theme, more=True)
    if note:
        shop.notes.append(note)
    return len(added)


def reroll_line(shop, index, items, seed=None):
    """Replace one line with another item of a similar level and kind. Returns True if it found one."""
    if not (0 <= index < len(shop.lines)):
        return False
    rng = random.Random(seed)
    old = shop.lines[index]
    st = shop.settings
    spec = SHOP_TYPES.get(shop.theme, SHOP_TYPES["General store"])
    rarities = set(st.get("rarities") or ())
    have = {str(l.item.name).lower() for l in shop.lines}
    pool = _pool(items, shop.level, rarities, st.get("special_orders", True), have)
    want = spec.get("also") if old.side else spec
    cands = [i for i in pool if matches(i, want)]
    if old.tag == "stock":
        cands = [i for i in cands if _level(i) <= shop.level]
    else:
        cands = [i for i in cands if _level(i) > shop.level]
    near = [i for i in cands if abs(_level(i) - _level(old.item)) <= 2 and bool(getattr(i, "consumable", False)) == bool(getattr(old.item, "consumable", False))]
    for group in (near, [i for i in cands if bool(getattr(i, "consumable", False)) == bool(getattr(old.item, "consumable", False))], cands):
        if group:
            new = _draw(group, 1, rng, _weight_fn(shop.level))[0]
            shop.lines[index] = Line(new, old.tag, _qty(new, shop.level, rng) if st.get("quantities", True) else 1, old.side)
            _sort(shop.lines)
            return True
    return False


def remove_lines(shop, indexes):
    drop = set(indexes)
    shop.lines = [l for i, l in enumerate(shop.lines) if i not in drop]
    shop.count = len(shop.lines)


def shop_text(shop_or_rows, title=""):
    """The stock as Markdown. Accepts a Shop, or the older list of (item, tag) pairs."""
    if isinstance(shop_or_rows, Shop):
        s = shop_or_rows
        head = f"# {s.name or title or s.theme}"
        sub = f"{s.theme.split(' (')[0]}, settlement level {s.level}, {len(s.lines)} different items"
        lines = [head, "", sub, ""]
        for l in s.lines:
            it = l.item
            qty = f"{l.qty}x " if l.qty > 1 else ""
            lines.append(f"- {qty}{it.name} (item {_level(it)}, {_price_text(it)})" + (" - special order" if l.tag != "stock" else ""))
        gp, cr = s.total_gp(), s.total_credits()
        if gp:
            lines += ["", f"Everything on the shelves is worth about {gp:,.0f} gp."]
        if cr:
            lines += ["", f"Everything on the shelves is worth about {cr:,.0f} credits."]
        return "\n".join(lines)
    lines = [f"# {title}", ""]
    for it, tag in shop_or_rows:
        lines.append(f"- {it.name} (item {_level(it)}, {_price_text(it)})" + (" - special order" if tag != "stock" else ""))
    return "\n".join(lines)


def _spread(items, k):
    """k items spread through a list sorted by level and name, so a sample shows low and high levels alike."""
    items = sorted(items, key=lambda i: (_level(i), str(getattr(i, "name", ""))))
    if len(items) <= k:
        return items
    return [items[round(n * (len(items) - 1) / (k - 1))] for n in range(k)] if k > 1 else items[:1]


def theme_report(items, level, rarities=("common",), special_orders=True, samples=4):
    """For every kind of shop, how many different items in your data fit it at this settlement level and rarity:
    [{theme, stock, special, sundries, largest, state, sample}]. 'largest' is the most different items that shop can hold
    (what a 400-item stock would come to); state is ok, thin (under 20), or empty. Use it to see which themes your data
    supports before stocking one."""
    level = max(0, int(level))
    pool = _pool(items, level, set(rarities or ()), special_orders, ())
    rows = []
    for theme, spec in SHOP_TYPES.items():
        core = [i for i in pool if matches(i, spec)]
        stock = [i for i in core if _level(i) <= level]
        special = [i for i in core if _level(i) > level]
        also = spec.get("also")
        side = [i for i in pool if also and not matches(i, spec) and matches(i, also)]
        side_stock = [i for i in side if _level(i) <= level]
        side_special = [i for i in side if _level(i) > level]
        specials = len(special) + len(side_special)               # special orders include the sundries sold that way
        n_special = min(specials, MAX_COUNT // 8) if special_orders else 0
        largest = min(MAX_COUNT, len(stock) + len(side_stock) + n_special)
        rows.append({"theme": theme, "stock": len(stock), "special": specials, "sundries": len(side_stock),
                     "largest": largest, "state": "empty" if largest == 0 else "thin" if largest < 20 else "ok",
                     "sample": [i.name for i in _spread(stock + special, samples)]})
    return rows


def theme_report_text(rows, level, rarities=("common",)):
    """The theme check as plain text, for pasting into a message."""
    rar = "/".join(sorted(rarities)) if rarities else "any rarity"
    out = [f"Shop themes at settlement level {level}, rarity {rar}", ""]
    for r in rows:
        out.append(f"{r['theme']}: {r['stock']} in stock, {r['special']} special orders, {r['sundries']} sundries, "
                   f"largest shop {r['largest']} ({r['state']})")
        if r["sample"]:
            out.append("    e.g. " + "; ".join(r["sample"]))
    return "\n".join(out)


def generate_shop(items, settlement_level, size="Town", shop_type="General store", rarities=("common",),
                  seed=None, special_orders=True):
    """The older interface: [(item, 'stock' | 'special order')] for a named size."""
    shop = build_shop(items, settlement_level, SIZES.get(size, 14), shop_type, rarities, special_orders=special_orders,
                      quantities=False, seed=seed)
    return [(l.item, l.tag) for l in shop.lines]

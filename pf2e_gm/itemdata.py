"""Built-in content for the Magic Item Generator (itemgen.py). Standard library only.

Two kinds of content live here.

RULES AND COMPONENTS (Python data, edited here): the price ranges and DCs from the GM Core item-building tables, the
fundamental and property runes with their levels and prices, the spells an item can cast, and the forms an item can
take. Numbers marked VERIFIED were checked against the Archives of Nethys copy of GM Core. Rune and spell entries not
marked are written from the Core Rulebook and Player Core and are spot-checked by the app against your downloaded data
(see itemgen.check_against_data), so a wrong number is reported instead of trusted.

FLAVOR (text tables): names, looks, makers, history, secrets, and rumors. These tables are folded into Story Forge's
registry, so the Edit Tables window can add, change, or turn off any entry, and your edits are saved with your other
table edits. Lines are written as  text | tags | weight | needs | not  exactly like storydata.py.
"""

TABLES = {}
RECIPES = {}
HALLOWMEAD = {}          # table additions limited to the Hallowmead content pack (p:hallowmead)


def table(name, title, text, into=None):
    (TABLES if into is None else into)[name] = {
        "title": title, "entries": [ln.strip() for ln in text.strip().splitlines()
                                    if ln.strip() and not ln.strip().startswith("#")]}


# ============================================================ GM Core numbers (VERIFIED, GM Core pg. 133)
PERM_PRICE = {1: (10, 20), 2: (25, 35), 3: (45, 60), 4: (75, 100), 5: (125, 160), 6: (200, 250), 7: (300, 360),
              8: (415, 500), 9: (575, 700), 10: (820, 1000), 11: (1160, 1400), 12: (1640, 2000), 13: (2400, 3000),
              14: (3600, 4500), 15: (5300, 6500), 16: (7900, 10000), 17: (12000, 15000), 18: (18600, 24000),
              19: (30400, 40000), 20: (52000, 70000)}
CONS_PRICE = {1: (3, 4), 2: (5, 7), 3: (8, 12), 4: (13, 20), 5: (21, 30), 6: (31, 50), 7: (51, 70), 8: (71, 100),
              9: (101, 150), 10: (151, 200), 11: (201, 300), 12: (301, 400), 13: (401, 600), 14: (601, 900),
              15: (901, 1300), 16: (1301, 2000), 17: (2001, 3000), 18: (3001, 5000), 19: (5001, 8000),
              20: (8001, 14000)}
# Table 2-18, Magic Item DCs. A narrow-function item may be up to 2 higher; an item that forces a save is typically 2 lower.
ITEM_DC = {1: 15, 2: 16, 3: 17, 4: 18, 5: 19, 6: 20, 7: 23, 8: 24, 9: 25, 10: 27, 11: 28, 12: 29, 13: 30, 14: 31,
           15: 34, 16: 35, 17: 37, 18: 38, 19: 41, 20: 43}
RARITY_ADJ = {"common": 0, "uncommon": 2, "rare": 5, "unique": 10}
# Skill items: +1 at 3rd level, +2 at 9th, +3 at 17th (the "core item" column of the price table).
SKILL_BONUS_LEVELS = ((17, 3), (9, 2), (3, 1))
# Role of an item decides where in its price range it sits: primary near the top, secondary in the middle, tertiary low.
ROLE_T = {"primary": 0.9, "secondary": 0.55, "tertiary": 0.2}

SKILLS = ["Acrobatics", "Arcana", "Athletics", "Crafting", "Deception", "Diplomacy", "Intimidation", "Medicine",
          "Nature", "Occultism", "Performance", "Religion", "Society", "Stealth", "Survival", "Thievery"]
# Skills whose items sit higher in the price range (the book names Medicine and Crafting as consequential secondary skills).
SKILL_ROLE = {"Medicine": "secondary", "Crafting": "secondary", "Thievery": "secondary", "Stealth": "secondary",
              "Athletics": "secondary", "Acrobatics": "secondary", "Diplomacy": "secondary", "Arcana": "secondary"}
ENERGIES = ["acid", "cold", "electricity", "fire"]
SAVE_VS = ["poison", "disease", "fear", "mental", "emotion", "curse", "fire", "cold"]
TRADITIONS = ["arcane", "divine", "occult", "primal"]
THEMES = ["crime", "politics", "trade", "religion", "undead", "fey", "monster", "nature", "ruin", "magic", "military",
          "family", "mystery", "disease", "weather", "festival", "craft", "treasure"]
# Effect tags used to keep history coherent with what an item does, and the story themes they lean toward.
FX_THEMES = {"fx:stealth": ["crime", "mystery"], "fx:travel": ["trade", "nature"], "fx:war": ["military"],
             "fx:protection": ["military", "religion"], "fx:healing": ["religion", "disease", "nature"],
             "fx:knowledge": ["mystery", "ruin", "magic"], "fx:social": ["politics", "trade"],
             "fx:craft": ["craft", "trade"], "fx:light": ["ruin"], "fx:control": ["magic"], "fx:magic": ["magic"],
             "fx:senses": ["mystery"], "fx:fire": ["military", "craft"], "fx:skill": []}

# ============================================================ forms (what the item is)
# key: (name, usage, bulk, kind, preferred skills)   kind is worn or held
FORMS = {
    "hat": ("hat", "worn headwear", "L", "worn", ["Deception", "Diplomacy", "Society"]),
    "circlet": ("circlet", "worn headwear", "L", "worn", ["Arcana", "Diplomacy", "Occultism"]),
    "cap": ("cap", "worn headwear", "L", "worn", ["Stealth", "Survival", "Thievery"]),
    "hood": ("hood", "worn headwear", "L", "worn", ["Stealth", "Deception", "Occultism"]),
    "headband": ("headband", "worn headwear", "L", "worn", ["Athletics", "Acrobatics", "Medicine"]),
    "crown": ("crown", "worn headwear", "L", "worn", ["Diplomacy", "Intimidation", "Society"]),
    "mask": ("mask", "worn headwear", "L", "worn", ["Deception", "Performance", "Intimidation"]),
    "goggles": ("pair of goggles", "worn eyepiece", "L", "worn", ["Crafting", "Survival", "Medicine"]),
    "monocle": ("monocle", "worn eyepiece", "L", "worn", ["Society", "Arcana", "Crafting"]),
    "spectacles": ("pair of spectacles", "worn eyepiece", "L", "worn", ["Arcana", "Society", "Medicine"]),
    "eyepatch": ("eyepatch", "worn eyepiece", "L", "worn", ["Intimidation", "Survival", "Occultism"]),
    "amulet": ("amulet", "worn amulet", "-", "worn", ["Religion", "Medicine", "Nature"]),
    "pendant": ("pendant", "worn necklace", "-", "worn", ["Occultism", "Diplomacy", "Religion"]),
    "locket": ("locket", "worn necklace", "-", "worn", ["Society", "Medicine", "Deception"]),
    "torc": ("torc", "worn necklace", "L", "worn", ["Athletics", "Intimidation", "Survival"]),
    "medallion": ("medallion", "worn necklace", "-", "worn", ["Diplomacy", "Society", "Religion"]),
    "scarf": ("scarf", "worn garment", "L", "worn", ["Survival", "Stealth", "Performance"]),
    "cloak": ("cloak", "worn cloak", "L", "worn", ["Stealth", "Survival", "Deception"]),
    "mantle": ("mantle", "worn cloak", "L", "worn", ["Diplomacy", "Religion", "Intimidation"]),
    "cape": ("cape", "worn cloak", "L", "worn", ["Acrobatics", "Performance", "Athletics"]),
    "shawl": ("shawl", "worn cloak", "L", "worn", ["Medicine", "Nature", "Society"]),
    "gloves": ("pair of gloves", "worn gloves", "L", "worn", ["Thievery", "Crafting", "Medicine"]),
    "bracers": ("pair of bracers", "worn bracers", "L", "worn", ["Athletics", "Acrobatics", "Intimidation"]),
    "armbands": ("pair of armbands", "worn armbands", "L", "worn", ["Athletics", "Survival", "Crafting"]),
    "wristbands": ("pair of wristbands", "worn bracers", "L", "worn", ["Acrobatics", "Performance", "Thievery"]),
    "ring": ("ring", "worn ring", "-", "worn", ["Deception", "Diplomacy", "Thievery", "Arcana"]),
    "signet": ("signet ring", "worn ring", "-", "worn", ["Society", "Diplomacy", "Intimidation"]),
    "belt": ("belt", "worn belt", "L", "worn", ["Athletics", "Survival", "Crafting"]),
    "sash": ("sash", "worn belt", "L", "worn", ["Performance", "Acrobatics", "Diplomacy"]),
    "girdle": ("girdle", "worn belt", "L", "worn", ["Athletics", "Intimidation", "Medicine"]),
    "boots": ("pair of boots", "worn boots", "L", "worn", ["Stealth", "Survival", "Athletics", "Acrobatics"]),
    "sandals": ("pair of sandals", "worn boots", "L", "worn", ["Acrobatics", "Nature", "Performance"]),
    "slippers": ("pair of slippers", "worn boots", "L", "worn", ["Stealth", "Acrobatics", "Thievery"]),
    "anklet": ("anklet", "worn boots", "-", "worn", ["Acrobatics", "Performance", "Stealth"]),
    "robe": ("robe", "worn garment", "L", "worn", ["Arcana", "Religion", "Occultism", "Nature"]),
    "tunic": ("tunic", "worn garment", "L", "worn", ["Society", "Diplomacy", "Crafting"]),
    "vest": ("vest", "worn garment", "L", "worn", ["Thievery", "Crafting", "Survival"]),
    "coat": ("coat", "worn garment", "L", "worn", ["Survival", "Society", "Deception"]),
    "apron": ("apron", "worn garment", "L", "worn", ["Crafting", "Medicine", "Nature"]),
    "lantern": ("lantern", "held in 1 hand", "1", "held", ["Survival", "Arcana", "Society"]),
    "compass": ("compass", "held in 1 hand", "L", "held", ["Survival", "Nature", "Society"]),
    "mirror": ("hand mirror", "held in 1 hand", "L", "held", ["Deception", "Occultism", "Diplomacy"]),
    "bell": ("handbell", "held in 1 hand", "L", "held", ["Religion", "Diplomacy", "Performance"]),
    "whistle": ("whistle", "held in 1 hand", "L", "held", ["Survival", "Nature", "Performance"]),
    "flute": ("flute", "held in 2 hands", "L", "held", ["Performance", "Nature", "Diplomacy"]),
    "horn": ("horn", "held in 2 hands", "L", "held", ["Performance", "Intimidation", "Survival"]),
    "drum": ("small drum", "held in 2 hands", "1", "held", ["Performance", "Intimidation", "Athletics"]),
    "key": ("key", "held in 1 hand", "L", "held", ["Thievery", "Society", "Crafting"]),
    "orb": ("orb", "held in 1 hand", "L", "held", ["Arcana", "Occultism", "Religion"]),
    "tome": ("slim book", "held in 1 hand", "1", "held", ["Arcana", "Society", "Occultism", "Religion"]),
    "stone": ("smooth stone", "held in 1 hand", "L", "held", ["Nature", "Occultism", "Survival"]),
    "flask": ("flask", "held in 1 hand", "L", "held", ["Medicine", "Crafting", "Nature"]),
    "cup": ("cup", "held in 1 hand", "L", "held", ["Diplomacy", "Medicine", "Society"]),
    "hourglass": ("hourglass", "held in 1 hand", "L", "held", ["Arcana", "Society", "Occultism"]),
    "spyglass": ("spyglass", "held in 1 hand", "L", "held", ["Survival", "Society", "Nature"]),
    "tuning fork": ("tuning fork", "held in 1 hand", "L", "held", ["Performance", "Crafting", "Arcana"]),
    "dice": ("set of dice", "held in 1 hand", "L", "held", ["Deception", "Thievery", "Society"]),
    "brush": ("paintbrush", "held in 1 hand", "L", "held", ["Crafting", "Performance", "Society"]),
    "lockpicks": ("set of lockpicks", "held in 1 hand", "L", "held", ["Thievery", "Crafting", "Stealth"]),
    "hammer": ("small hammer", "held in 1 hand", "L", "held", ["Crafting", "Athletics", "Intimidation"]),
    "chisel": ("chisel", "held in 1 hand", "L", "held", ["Crafting", "Society", "Survival"]),
    "needle": ("needle and thread", "held in 1 hand", "L", "held", ["Crafting", "Medicine", "Performance"]),
    "ladle": ("ladle", "held in 1 hand", "L", "held", ["Medicine", "Diplomacy", "Nature"]),
    "pouch": ("belt pouch", "worn belt", "L", "worn", ["Thievery", "Crafting", "Survival"]),
}
WORN_FORMS = [k for k, v in FORMS.items() if v[3] == "worn"]
HELD_FORMS = [k for k, v in FORMS.items() if v[3] == "held"]

# One-use devices: (name, verb phrase)
DEVICES = [("pinch of dust in a twist of paper", "throw the dust"), ("stick of incense", "light the incense"),
           ("short candle", "light the candle"), ("dried seed", "crush the seed"), ("glass bead", "crush the bead"),
           ("gray feather", "release the feather"), ("piece of chalk", "snap the chalk"), ("pouch of powder", "scatter the powder"),
           ("small wafer", "eat the wafer"), ("smooth pebble", "drop the pebble"), ("scrap of ribbon", "tear the ribbon"),
           ("dried leaf", "crush the leaf"), ("wax-sealed vial", "break the seal"), ("tiny paper bird", "unfold the bird"),
           ("knot of cord", "pull the knot loose"), ("coin with a hole in it", "flip the coin")]
POTION_LOOKS = ["a cloudy green liquid", "a thin silver liquid", "a warm amber liquid", "a smoky blue liquid",
                "a liquid that is slightly too clear", "a thick red liquid", "a pale violet liquid",
                "a liquid that fizzes when no one is watching", "a milky liquid with flecks of gold",
                "a dark liquid that smells of rain", "a bright yellow liquid", "a liquid the color of old copper"]
SCROLL_LOOKS = ["parchment tied with red thread", "a strip of waxed cloth", "vellum sealed with a thumbprint",
                "a single page torn from a book", "bark paper rolled around a bone",
                "cheap paper in confident handwriting", "a rolled sheet with an ink blot in the corner"]
WAND_LOOKS = ["a straight rod", "a twisted rod", "a slender rod of polished wood", "a rod of bone", "a short brass rod",
              "a rod carved with a spiral", "a rod wrapped in leather", "a rod with a glass tip", "a thin rod of black wood"]

# ============================================================ weapons and armor (Player Core equipment tables)
# Checked against the Player Core tables as shown by Archives of Nethys, Roll20's compendium, and Demiplane: every melee
# weapon, the ranged weapons listed, and every armor, with damage, hands, bulk, group, traits, and the armor numbers.
# Weapon groups for the two crossbows are left blank on purpose: the Core and Remaster books label them differently.
def _w(price, cat, kind, die, dtype, bulk, hands, group, traits=(), rng=0, reload=None, anc="", rarity="common"):
    return dict(price=price, cat=cat, kind=kind, die=die, dtype=dtype, bulk=bulk, hands=hands, group=group,
                traits=list(traits), range=rng, reload=reload, anc=anc, rarity=rarity)


DAMAGE_NAMES = {"B": "bludgeoning", "P": "piercing", "S": "slashing"}
WEAPONS = {
    # simple melee
    "club": _w(0, "simple", "melee", "d6", "B", 1, "1", "club", ["thrown 10 ft."], 10),
    "dagger": _w(0.2, "simple", "melee", "d4", "P", "L", "1", "knife", ["agile", "finesse", "thrown 10 ft.", "versatile S"], 10),
    "light mace": _w(0.4, "simple", "melee", "d4", "B", "L", "1", "club", ["agile", "finesse", "shove"]),
    "longspear": _w(0.5, "simple", "melee", "d8", "P", 2, "2", "spear", ["reach"]),
    "mace": _w(1, "simple", "melee", "d6", "B", 1, "1", "club", ["shove"]),
    "morningstar": _w(1, "simple", "melee", "d6", "B", 1, "1", "club", ["versatile P"]),
    "sickle": _w(0.2, "simple", "melee", "d4", "S", "L", "1", "knife", ["agile", "finesse", "trip"]),
    "spear": _w(0.1, "simple", "melee", "d6", "P", 1, "1", "spear", ["thrown 20 ft."], 20),
    "staff": _w(0, "simple", "melee", "d4", "B", 1, "1", "club", ["two-hand d8"]),
    # martial melee
    "battle axe": _w(1, "martial", "melee", "d8", "S", 1, "1", "axe", ["sweep"]),
    "falchion": _w(3, "martial", "melee", "d10", "S", 2, "2", "sword", ["forceful", "sweep"]),
    "flail": _w(0.8, "martial", "melee", "d6", "B", 1, "1", "flail", ["disarm", "sweep", "trip"]),
    "glaive": _w(1, "martial", "melee", "d8", "S", 2, "2", "polearm", ["deadly d8", "forceful", "reach"]),
    "greataxe": _w(2, "martial", "melee", "d12", "S", 2, "2", "axe", ["sweep"]),
    "greatclub": _w(1, "martial", "melee", "d10", "B", 2, "2", "club", ["backswing", "shove"]),
    "greatpick": _w(1, "martial", "melee", "d10", "P", 2, "2", "pick", ["fatal d12"]),
    "greatsword": _w(2, "martial", "melee", "d12", "S", 2, "2", "sword", ["versatile P"]),
    "halberd": _w(2, "martial", "melee", "d10", "P", 2, "2", "polearm", ["reach", "versatile S"]),
    "hatchet": _w(0.4, "martial", "melee", "d6", "S", "L", "1", "axe", ["agile", "sweep", "thrown 10 ft."], 10),
    "light hammer": _w(0.3, "martial", "melee", "d6", "B", "L", "1", "hammer", ["agile", "thrown 20 ft."], 20),
    "light pick": _w(0.4, "martial", "melee", "d4", "P", "L", "1", "pick", ["agile", "fatal d8"]),
    "longsword": _w(1, "martial", "melee", "d8", "S", 1, "1", "sword", ["versatile P"]),
    "main-gauche": _w(0.5, "martial", "melee", "d4", "P", "L", "1", "knife", ["agile", "disarm", "finesse", "parry", "versatile S"]),
    "maul": _w(3, "martial", "melee", "d12", "B", 2, "2", "hammer", ["shove"]),
    "pick": _w(0.7, "martial", "melee", "d6", "P", 1, "1", "pick", ["fatal d10"]),
    "rapier": _w(2, "martial", "melee", "d6", "P", 1, "1", "sword", ["deadly d8", "disarm", "finesse"]),
    "sap": _w(0.1, "martial", "melee", "d6", "B", "L", "1", "club", ["agile", "nonlethal"]),
    "scimitar": _w(1, "martial", "melee", "d6", "S", 1, "1", "sword", ["forceful", "sweep"]),
    "scythe": _w(2, "martial", "melee", "d10", "S", 2, "2", "polearm", ["deadly d10", "trip"]),
    "shortsword": _w(0.9, "martial", "melee", "d6", "P", "L", "1", "sword", ["agile", "finesse", "versatile S"]),
    "starknife": _w(2, "martial", "melee", "d4", "P", "L", "1", "knife", ["agile", "deadly d6", "finesse", "thrown 20 ft.", "versatile S"], 20),
    "trident": _w(1, "martial", "melee", "d8", "P", 1, "1", "spear", ["thrown 20 ft."], 20),
    "war flail": _w(2, "martial", "melee", "d10", "B", 2, "2", "flail", ["disarm", "sweep", "trip"]),
    "warhammer": _w(1, "martial", "melee", "d8", "B", 1, "1", "hammer", ["shove"]),
    "whip": _w(0.1, "martial", "melee", "d4", "S", 1, "1", "flail", ["disarm", "finesse", "nonlethal", "reach", "trip"]),
    # uncommon ancestry weapons (chosen only for items in that culture's style)
    "dogslicer": _w(0.1, "martial", "melee", "d6", "S", "L", "1", "sword", ["agile", "backstabber", "finesse", "goblin"], 0, None, "goblin", "uncommon"),
    "elven curve blade": _w(4, "martial", "melee", "d8", "S", 2, "2", "sword", ["elf", "finesse", "forceful"], 0, None, "elf", "uncommon"),
    "filcher's fork": _w(1, "martial", "melee", "d4", "P", "L", "1", "spear", ["agile", "backstabber", "deadly d6", "finesse", "halfling", "thrown 20 ft."], 20, None, "halfling", "uncommon"),
    "clan dagger": _w(2, "simple", "melee", "d4", "P", "L", "1", "knife", ["agile", "dwarf", "parry", "versatile B"], 0, None, "dwarf", "uncommon"),
    # ranged
    "shortbow": _w(3, "martial", "ranged", "d6", "P", 1, "1+", "bow", ["deadly d10"], 60, 0),
    "longbow": _w(6, "martial", "ranged", "d8", "P", 2, "1+", "bow", ["deadly d10", "volley 30 ft."], 100, 0),
    "crossbow": _w(3, "simple", "ranged", "d8", "P", 1, "2", "", [], 120, 1),
    "hand crossbow": _w(3, "simple", "ranged", "d6", "P", "L", "1", "", [], 60, 1),
    "sling": _w(0, "simple", "ranged", "d6", "B", "L", "1", "sling", ["propulsive"], 50, 1),
    "dart": _w(0.01, "simple", "ranged", "d4", "P", "L", "1", "dart", ["agile", "thrown 20 ft."], 20),
    "javelin": _w(0.1, "simple", "ranged", "d6", "P", "L", "1", "dart", ["thrown 30 ft."], 30),
}
# What each weapon trait does, in short (Player Core wording, condensed). Only traits used above are listed.
TRAIT_GLOSS = {
    "agile": "The multiple attack penalty is -4 on the second attack in a turn and -8 on the third, not -5 and -10.",
    "backstabber": "A hit on an off-guard creature deals 1 extra precision damage (2 with a +3 weapon).",
    "backswing": "After you miss with it on your turn, you gain a +1 circumstance bonus to your next attack with it that turn.",
    "deadly": "On a critical hit, add one extra damage die of the listed size after doubling (two dice with greater striking, three with major).",
    "disarm": "You can Disarm with Athletics even without a free hand, using the weapon's reach and its item bonus to attack rolls.",
    "fatal": "On a critical hit, the damage die becomes the listed size, and you add one more die of that size.",
    "finesse": "You can use Dexterity instead of Strength on melee attack rolls with it. Strength still adds to damage.",
    "forceful": "When you attack with it more than once on your turn, the second attack deals extra damage equal to its number of weapon dice, and later ones double that.",
    "goblin": "A weapon made and used by goblins.",
    "dwarf": "A weapon made and used by dwarves.",
    "elf": "A weapon made and used by elves.",
    "halfling": "A weapon made and used by halflings.",
    "nonlethal": "Its attacks are nonlethal, and it can make nonlethal attacks without the usual -2 penalty.",
    "parry": "You can spend an action to hold it defensively for a +1 circumstance bonus to AC until your next turn.",
    "propulsive": "You add half your Strength modifier (if positive) to damage with this ranged weapon.",
    "reach": "Strikes with it can target creatures up to 10 feet away.",
    "shove": "You can Shove with Athletics even without a free hand, using the weapon's reach and its item bonus to attack rolls.",
    "sweep": "You gain a +1 circumstance bonus to attack if you already attacked a different target this turn with it.",
    "thrown": "You can throw it as a ranged attack with the listed range increment. Strength adds to its damage.",
    "trip": "You can Trip with Athletics even without a free hand, using the weapon's reach and its item bonus to attack rolls.",
    "two-hand": "Wielding it with two hands changes its damage die to the listed size.",
    "versatile": "It can deal the listed damage type instead of its usual type. Choose each time you attack.",
    "volley": "Ranged attacks with it take a -2 penalty against targets within the listed distance.",
    "bulwark": "On Reflex saves against damaging effects, you add +3 instead of your Dexterity modifier.",
    "comfort": "You can rest normally while wearing it.",
    "flexible": "Its check penalty doesn't apply to Acrobatics or Athletics checks.",
    "noisy": "It is loud: its check penalty applies to Stealth even if you meet the Strength threshold.",
}


def _a(price, cat, ac, dex, check, speed, strength, bulk, group, traits=(), metal=False, level=0):
    return dict(price=price, cat=cat, ac=ac, dex=dex, check=check, speed=speed, strength=strength, bulk=bulk, group=group,
                traits=list(traits), metal=metal, level=level)


# strength is the Strength modifier that removes the check penalty and eases the speed penalty (Player Core).
ARMORS = {
    "padded armor": _a(0.2, "light", 1, 3, 0, 0, 0, "L", "cloth", ["comfort"]),
    "leather armor": _a(2, "light", 1, 4, -1, 0, 0, 1, "leather"),
    "studded leather armor": _a(3, "light", 2, 3, -1, 0, 1, 1, "leather"),
    "chain shirt": _a(5, "light", 2, 3, -1, 0, 1, 1, "chain", ["flexible", "noisy"], True),
    "hide armor": _a(2, "medium", 3, 2, -2, -5, 2, 2, "leather"),
    "scale mail": _a(4, "medium", 3, 2, -2, -5, 2, 2, "composite", (), True),
    "chain mail": _a(6, "medium", 4, 1, -2, -5, 3, 2, "chain", ["flexible", "noisy"], True),
    "breastplate": _a(8, "medium", 4, 1, -2, -5, 3, 2, "plate", (), True),
    "splint mail": _a(13, "heavy", 5, 1, -3, -10, 3, 3, "composite", (), True, 1),
    "half plate": _a(18, "heavy", 5, 1, -3, -10, 3, 3, "plate", (), True, 1),
    "full plate": _a(30, "heavy", 6, 0, -3, -10, 4, 4, "plate", ["bulwark"], True, 2),
}


def weapon_thrown(info):
    return any(t.startswith("thrown") for t in info["traits"])


# ============================================================ runes
# Fundamental runes (VERIFIED from the upgrade tables, GM Core and Core Rulebook): (name, level, price gp)
WEAPON_POTENCY = {1: ("+1 weapon potency", 2, 35), 2: ("+2 weapon potency", 10, 935), 3: ("+3 weapon potency", 16, 8935)}
STRIKING = {1: ("striking", 4, 65), 2: ("greater striking", 12, 1065), 3: ("major striking", 19, 31065)}
ARMOR_POTENCY = {1: ("+1 armor potency", 5, 160), 2: ("+2 armor potency", 11, 1060), 3: ("+3 armor potency", 18, 20560)}
RESILIENT = {1: ("resilient", 8, 340), 2: ("greater resilient", 14, 3440), 3: ("major resilient", 20, 49440)}

# Property runes: dict(name, level, price, text, uses). `uses` limits what it can be etched onto.
# Checked against the Archives of Nethys: ghost touch, holy, brilliant, keen, shadow, slick (all three tiers), fortification,
# and greater fire-resistant. The rest come from the Core Rulebook rune tables. The app compares every rune against your
# downloaded rules data each time an item is shown and reports any level or price that differs.
WEAPON_RUNES = [
    dict(name="returning", level=3, price=55, uses="thrown", text="After you throw the weapon, it flies back to your hand."),
    dict(name="ghost touch", level=4, price=75, uses="any", text="The weapon can harm creatures without physical form."),
    dict(name="disrupting", level=5, price=150, uses="any", extra=("1d6", "spirit", "against undead"),
         text="Deals an extra 1d6 spirit damage to undead. A critical hit has an additional effect on undead (see the rune)."),
    dict(name="fearsome", level=5, price=160, uses="any", text="A critical hit also makes the target frightened 1."),
    dict(name="wounding", level=7, price=340, uses="any", extra=("1d6", "persistent bleed", ""),
         text="A hit deals an extra 1d6 persistent bleed damage."),
    dict(name="flaming", level=8, price=500, uses="any", extra=("1d6", "fire", ""),
         text="Deals an extra 1d6 fire damage on a hit. A critical hit also deals 1d10 persistent fire damage."),
    dict(name="frost", level=8, price=500, uses="any", extra=("1d6", "cold", ""),
         text="Deals an extra 1d6 cold damage on a hit. A critical hit also slows the target (see the rune)."),
    dict(name="shock", level=8, price=500, uses="any", extra=("1d6", "electricity", ""),
         text="Deals an extra 1d6 electricity damage on a hit. A critical hit arcs electricity to nearby creatures (see the rune)."),
    dict(name="corrosive", level=8, price=500, uses="any", extra=("1d6", "acid", ""),
         text="Deals an extra 1d6 acid damage on a hit. A critical hit corrodes the target's gear (see the rune)."),
    dict(name="thundering", level=8, price=500, uses="any", extra=("1d6", "sonic", ""),
         text="Deals an extra 1d6 sonic damage on a hit. A critical hit can deafen the target (see the rune)."),
    dict(name="grievous", level=9, price=700, uses="melee", text="A critical hit also applies the weapon group's critical specialization effect."),
    dict(name="holy", level=11, price=1400, uses="any", extra=("1d4", "spirit", "against unholy creatures"),
         text="Deals an extra 1d4 spirit damage to unholy creatures. If you are unholy, you are enfeebled 2 while wielding it."),
    dict(name="unholy", level=11, price=1400, uses="any", extra=("1d4", "spirit", "against holy creatures"),
         text="Deals an extra 1d4 spirit damage to holy creatures. If you are holy, you are enfeebled 2 while wielding it."),
    dict(name="brilliant", level=12, price=2000, uses="any", text="Sheds bright light and burns with extra fire damage (see the rune)."),
    dict(name="keen", level=13, price=3000, uses="melee",
         text="When you roll a natural 19 on a Strike with it and the result would be a success, it becomes a critical success."),
    dict(name="dancing", level=13, price=2700, uses="melee", text="The weapon can fight on its own for a short time."),
]
ARMOR_RUNES = [
    dict(name="glamered", level=5, price=140, uses="any", text="The armor can look like ordinary clothing or another outfit."),
    dict(name="shadow", level=5, price=55, uses="nonmetal-light-medium", text="You gain a +1 item bonus to Stealth checks while wearing the armor."),
    dict(name="slick", level=5, price=45, uses="any", text="You gain a +1 item bonus to Acrobatics checks to Escape and Squeeze."),
    dict(name="ready", level=6, price=200, uses="any", text="You can don the armor with a single action."),
    dict(name="acid-resistant", level=8, price=420, uses="any", text="You gain resistance 5 to acid damage."),
    dict(name="cold-resistant", level=8, price=420, uses="any", text="You gain resistance 5 to cold damage."),
    dict(name="electricity-resistant", level=8, price=420, uses="any", text="You gain resistance 5 to electricity damage."),
    dict(name="fire-resistant", level=8, price=420, uses="any", text="You gain resistance 5 to fire damage."),
    dict(name="greater slick", level=8, price=450, uses="any", text="You gain a +2 item bonus to Acrobatics checks to Escape and Squeeze."),
    dict(name="invisibility", level=8, price=500, uses="any", text="Once per day, you can activate the armor to turn invisible."),
    dict(name="greater fire-resistant", level=12, price=1650, uses="any", text="You gain resistance 10 to fire damage."),
    dict(name="greater cold-resistant", level=12, price=1650, uses="any", text="You gain resistance 10 to cold damage."),
    dict(name="fortification", level=12, price=2000, uses="medium-heavy", text="A critical hit against you can become a normal hit (a flat check, DC 17)."),
    dict(name="major slick", level=16, price=9000, uses="any", text="You gain a +3 item bonus to Acrobatics checks to Escape and Squeeze."),
]

# ============================================================ spells an item can cast
# (name, rank, cast actions, traditions, tags, mode, blurb)   mode: s self, t target, a area, o object or utility
# Rank 0 is a cantrip. Ranks follow Player Core; the app cross-checks what it can against your data.
_SPELLS = [
    ("Light", 0, 2, "ADOP", "fx:light", "o", "a drifting globe of light"),
    ("Detect Magic", 0, 2, "ADOP", "fx:knowledge fx:magic", "a", "a pulse that reveals nearby magic"),
    ("Telekinetic Hand", 0, 2, "AO", "fx:craft", "o", "an unseen hand that moves small objects"),
    ("Ghost Sound", 0, 2, "AO", "fx:stealth", "a", "a sound that seems to come from elsewhere"),
    ("Shield", 0, 1, "AO", "fx:protection fx:war", "s", "a shimmering barrier of force"),
    ("Fear", 1, 2, "ADOP", "fx:war fx:control", "t", "a surge of dread"),
    ("Grease", 1, 2, "AP", "fx:control fx:travel", "a", "a slick coating on the ground or an object"),
    ("Sleep", 1, 2, "AO", "fx:control fx:stealth", "a", "drowsiness that drops the weak"),
    ("Charm", 1, 2, "AOP", "fx:social", "t", "a creature briefly regards you as a friend"),
    ("Command", 1, 2, "DO", "fx:social fx:control", "t", "a one-word order"),
    ("Bless", 1, 2, "DP", "fx:war fx:protection", "a", "a boon to nearby allies"),
    ("Illusory Disguise", 1, 2, "AO", "fx:stealth fx:social", "s", "a convincing false face"),
    ("Force Barrage", 1, 2, "AO", "fx:war", "t", "darts of force that never miss"),
    ("Mystic Armor", 1, 2, "AO", "fx:protection fx:war", "s", "a coat of magical armor"),
    ("Sure Strike", 1, 1, "DO", "fx:war", "s", "a blow guided by luck"),
    ("Jump", 1, 1, "AP", "fx:travel", "s", "a mighty leap"),
    ("Gentle Landing", 1, "R", "AOP", "fx:travel fx:protection", "s", "a fall slowed to a drift"),
    ("Unseen Servant", 1, 2, "AO", "fx:craft", "o", "an unseen helper that fetches and carries"),
    ("Ventriloquism", 1, 2, "AO", "fx:stealth fx:social", "o", "your voice from another place"),
    ("Heal", 1, 2, "DP", "fx:healing", "t", "restorative energy"),
    ("Pest Form", 1, 2, "AP", "fx:stealth fx:travel", "s", "the shape of a harmless animal"),
    ("Floating Disk", 1, 2, "AO", "fx:craft fx:travel", "o", "a disk of force that carries a load"),
    ("Invisibility", 2, 2, "AO", "fx:stealth", "s", "vanishing from sight"),
    ("Darkvision", 2, 2, "AO", "fx:senses", "t", "sight in the dark"),
    ("See the Unseen", 2, 2, "ADO", "fx:senses fx:knowledge", "s", "sight that pierces invisibility"),
    ("Web", 2, 2, "AP", "fx:control", "a", "a mass of sticky strands"),
    ("Mirror Image", 2, 2, "AO", "fx:protection fx:stealth", "s", "illusory duplicates"),
    ("Resist Energy", 2, 2, "ADOP", "fx:protection", "t", "resistance to a type of energy"),
    ("Restoration", 2, 2, "DP", "fx:healing", "t", "relief from a lingering affliction"),
    ("Spider Climb", 2, 2, "AOP", "fx:travel", "t", "the grip of a spider"),
    ("Knock", 2, 2, "AO", "fx:craft fx:stealth", "o", "locks that open"),
    ("Dispel Magic", 2, 2, "ADOP", "fx:magic", "t", "an end to a magical effect"),
    ("Enlarge", 2, 2, "AP", "fx:war", "t", "growth to a larger size"),
    ("Humanoid Form", 2, 2, "AP", "fx:stealth fx:social", "s", "a humanoid shape"),
    ("Obscuring Mist", 2, 2, "AP", "fx:stealth fx:control", "a", "a cloud of fog"),
    ("Darkness", 2, 2, "AO", "fx:control fx:stealth", "a", "an area of magical darkness"),
    ("Revealing Light", 2, 2, "DO", "fx:knowledge fx:war", "a", "a flash that outlines the hidden"),
    ("Fireball", 3, 2, "AP", "fx:war fx:fire", "a", "a roaring burst of flame"),
    ("Lightning Bolt", 3, 2, "AP", "fx:war", "a", "a line of lightning"),
    ("Haste", 3, 2, "AOP", "fx:war fx:travel", "t", "a surge of speed"),
    ("Slow", 3, 2, "AO", "fx:control fx:war", "t", "sluggish movement"),
    ("Blindness", 3, 2, "ADO", "fx:control", "t", "sight taken away"),
    ("Paralyze", 3, 2, "AO", "fx:control", "t", "frozen limbs"),
    ("Mind Reading", 3, 2, "AO", "fx:knowledge fx:social", "t", "a glimpse of surface thoughts"),
    ("Meld into Stone", 3, 2, "DP", "fx:stealth fx:travel", "s", "sinking into solid rock"),
    ("Fly", 4, 2, "AOP", "fx:travel", "t", "flight"),
    ("Dimension Door", 4, 2, "AO", "fx:travel", "t", "a short teleport"),
    ("Freedom of Movement", 4, 2, "ADOP", "fx:protection fx:travel", "t", "unhindered motion"),
    ("Phantasmal Killer", 4, 2, "AO", "fx:war", "t", "a lethal illusion of fear"),
    ("Wall of Fire", 4, 2, "AP", "fx:control fx:fire", "a", "a curtain of flame"),
    ("Confusion", 4, 2, "AO", "fx:control", "t", "scrambled thoughts"),
    ("Cone of Cold", 5, 2, "AP", "fx:war", "a", "a cone of freezing blast"),
    ("Banishment", 5, 2, "ADO", "fx:control", "t", "a creature cast out to another plane"),
    ("Mislead", 6, 2, "AO", "fx:stealth fx:social", "s", "an illusory double that draws attention while you slip away"),
    ("Truesight", 6, 2, "ADO", "fx:senses fx:knowledge", "s", "sight that sees through illusions and disguises"),
    ("Teleport", 6, 3, "AO", "fx:travel", "t", "a long-distance teleport"),
    ("Chain Lightning", 6, 2, "AP", "fx:war", "a", "lightning that leaps between foes"),
    ("Disintegrate", 6, 2, "A", "fx:war", "t", "a ray that unmakes"),
    ("Dominate", 6, 2, "AO", "fx:social fx:control", "t", "a creature bends to your will"),
    ("Energy Aegis", 7, 2, "ADOP", "fx:protection", "s", "protection against every kind of energy"),
    ("Ethereal Jaunt", 7, 2, "AO", "fx:travel fx:stealth", "s", "a shift into the Ethereal Plane"),
    ("Prismatic Spray", 7, 2, "AO", "fx:war", "a", "a spray of many-colored light"),
    ("Mind Blank", 8, 2, "AO", "fx:protection fx:knowledge", "s", "a mind closed to magic that probes it"),
    ("Maze", 8, 2, "AO", "fx:control", "t", "a creature lost in an extradimensional maze"),
    ("Meteor Swarm", 9, 3, "AP", "fx:war fx:fire", "a", "meteors from the sky"),
    ("Time Stop", 9, 1, "AO", "fx:magic", "s", "moments that others do not share"),
    ("Shapechange", 9, 2, "AP", "fx:social fx:travel", "s", "a new form"),
]
TRAD_NAMES = {"A": "arcane", "D": "divine", "O": "occult", "P": "primal"}
SPELLS = [dict(name=n, rank=r, cast=c, traditions=[TRAD_NAMES[x] for x in t], tags=g.split(), mode=m, blurb=b)
          for n, r, c, t, g, m, b in _SPELLS]
SPELL_BY_NAME = {s["name"].lower(): s for s in SPELLS}


# ============================================================ flavor tables (names and looks)
table("item.adj", "Item name adjectives", """
Wayward
Patient
Stubborn
Merry
Quiet
Sleepless
Borrowed
Faithful
Lucky
Forgotten
Tarnished
Winding
Wandering
Sparing
Hungry
Bright
Dutiful
Thrifty
Cunning
Gentle
Restless
Salt-Stained
Moonlit
Ember-Bright
Mossy
Cracked
Mended
Patched
Humming
Crooked
Honest
Weary
Nimble
Shy
Proud
Plain
Gray
Gilded
Hollow
Silent
Crimson
Iron
""")
table("item.stem", "Name endings (used when an effect has none of its own)", """
the Long Road
Quiet Hours
Small Mercies
the Patient Hand
Borrowed Light
the Last Lamp
Idle Winters
Narrow Doors
the Open Hand
Slow Water
the Third Bell
Gray Mornings
Honest Weights
the Second Chance
Careful Steps
the Quiet Room
Late Arrivals
the Fair Wind
""")
table("item.motif", "How an item is decorated", """
etched with a ring of tiny stars
stitched with a pattern of ravens
inlaid with chips of colored glass
wrapped in cord that is never the same knot twice
carved with a long row of small doors
engraved with a map that matches no coast
set with a single dull stone that is not dull in the dark
worn smooth by many thumbs
marked with rows of tally scratches
banded with copper gone green
patched in three different cloths
etched with tiny owls
ringed with a fine line of silver wire
decorated with a braid of horsehair
painted with a faded wave pattern
studded with small brass rivets
trimmed along its edges in worn velvet
burned with a brand shaped like a key
scored with a row of shallow fingerholds
inscribed with a verse in a language nobody speaks
hung with a small bell that never rings
tied with a ribbon someone clearly meant to keep
dotted with tiny holes that spell nothing
decorated with leaves pressed flat under glass
covered in a pattern of interlocking hands
""")
table("item.material.decor", "What an item is made of (for looks)", """
bone
horn
oak
yew
ash wood
pewter
tin
copper
bronze
dull silver
black iron
river glass
smoked glass
amber
jet
mother-of-pearl
waxed leather
oiled canvas
gray wool
spider silk
stitched hide
salvaged brass
woven reed
braided hair
fired clay
slate
soapstone
obsidian
dried moss
horn and brass
""")
table("item.mark", "Maker's marks", """
a tiny hammer stamped near the edge
a pair of initials scratched where only a thumb would find them
a thumbprint pressed into the maker's wax
a tiny open eye
three short lines like a tally
a knot burned into the underside
a small crescent stamped in the metal
a small flame
a spiral hidden in the lining
a tiny crowned bird
a maker's glyph in red thread
no mark at all, which is itself a kind of mark
a name filed off, and badly
a seal that matches no registry
a repair stitch in a different color, signed
a row of small dots like a constellation
a letter that might be an N or a Z
""")
table("item.quirk", "Quirks (cosmetic, no effect on level or price)", """
It hums a note only its owner can hear when rain is coming.
It is always slightly warm, even in snow.
It smells faintly of baking bread whenever it is used.
It refuses to stay clean, however often it is washed.
It leaves a faint trail of glitter that fades within the hour.
It tarnishes whenever someone nearby tells a lie, and polishes itself when they stop.
It is sticky to the touch on Tuesdays, according to every owner.
It plays a few notes of a lullaby when put down on a hard surface.
It cannot be photographed by any means anyone has tried, which is probably a coincidence.
It grows a little warmer whenever its owner is being watched.
It turns up in odd places, always within a day's walk of where it was left.
It makes birds nervous, and cats very interested.
It rattles faintly when a door nearby is about to open.
It always seems to fit, whoever wears it.
It stays dry in the rain, which the owner finds more suspicious than useful.
It casts a shadow that is a little too long.
It cannot be sold without the buyer paying for the previous owner's drink.
Its owner always dreams of the same corridor on the first night.
It smells of someone else's pipe smoke.
It is remembered as being a slightly different color by every person who has seen it.
""")
table("item.drawback", "Minor drawbacks (flavor with a small cost; the GM decides if it applies)", """
Using it makes a clear chime that carries about 30 feet.
It does not work while another item of the same kind is worn or carried.
It must be wetted at least once a day, or using it takes one extra action.
It resents being hidden: while concealed, its owner feels a faint, steady unease.
Its activation phrase is long and must be said aloud, which makes it hard to use quietly.
It tugs toward its maker's grave. After a day of travel, the owner notices which way.
In bright sunlight, using it takes one extra action.
Its owner must tell it a small truth each dawn, or it grows sulky and sluggish until they do.
It dislikes being lent and works for no one else for the first day.
It draws the eye. Anyone looking for it notices it from twice the usual distance.
""")
table("item.weapon.a", "Weapon name starts (a line with a Needs tag, such as fx:fire, fits only a weapon with that rune)", """
Thorn
Rook
Briar
Oath
Hollow
Wren
Moss
Needle
Dawn
Dusk
Ash
Bright
Grim
Quill
Marrow
Sable
Tarn
Bramble
Hazel
Nettle
Raven
Lark
Sorrow
Flint
Ember||3|fx:fire
Cinder||3|fx:fire
Kindle||2|fx:fire
Frost||3|fx:cold
Rime||3|fx:cold
Winter||2|fx:cold
Storm||3|fx:electricity
Spark||3|fx:electricity
Rust||3|fx:acid
Sour||2|fx:acid
Hush||3|fx:fear
Bell||3|fx:sonic
Grave||3|fx:undead
Mercy||3|fx:holy
Vesper||3|fx:unholy
Thread||3|fx:bleed
""")
table("item.weapon.b", "Weapon name endings (Needs tags: wd:S, wd:P, wd:B for the damage type, wp:<group> for the weapon group)", """
fang||3|wd:P/wd:S
bite||3|wd:P/wd:S
song
edge||3|wd:S/wd:P
wing
tooth||2|wd:P/wd:S
brand
reach||3|wt:reach
whisper
bane
cleaver||3|wd:S
sting||3|wd:P
splitter||2|wp:axe/wp:hammer/wp:pick/wp:polearm
keeper
mark
wake
breaker||3|wd:B
knell||2|wd:B
thump||2|wd:B
spike||2|wd:P
sweep||2|wd:S
""")
table("item.armor.a", "Armor name starts", """
Oak
Hearth
Iron
Stone
Thorn
Bulwark
Willow
Barrow
Sentry
Mother
""")
table("item.armor.b", "Armor name endings", """
ward
hold
shell
wall
keep
guard
bough
mantle
""")

# ============================================================ flavor tables (history and lore)
# Slots of the hidden "item_lore" story: who made it, what for, where, when, why, plus mark, owner, fate, found, secret.
table("item.who", "Made by", """
{campaign.npc}|k:npc|4
{campaign.faction}|k:faction|4
{npc.named}|k:npc|5
{faction.generic}|k:faction|2
{group}|k:group|2
a forgotten guild of {pl occupation}|k:group pl|2
{a ancestry.adj} {occupation} whose name nobody recorded|k:npc|2
the private workshop of {official}|politics|1
the apprentices of a master who vanished|craft k:group pl|1
{npc.named} under a false name|crime mystery k:npc|1
a traveling {occupation} who made one of these in every town|road trade k:npc|1
{a occupation} who never learned the proper way but did it better|craft k:npc|1
the {name.adj} {name.collective}|k:group|2
a hedge witch with more skill than sense|magic nature k:npc|1
a monk who made it as a penance|religion k:npc|1
""")
table("item.where", "Made at", """
{where.any}||6
{campaign.location}||3
in a workshop above {shop.name}
in a forge that no longer exists
aboard a river barge|water
in a monastery kitchen|religion
in a village that was later flooded
somewhere in {settlement.name}
in the back room of {tavern.name}
in a cellar under {street}
in a ruin whose name is lost|ruin
in a tent at a traveling fair|festival road
on the ground where {settlement.name} would later stand
on the kitchen table of someone who should not have been able to afford the materials
""")
table("item.when", "Made when", """
three centuries ago
{n:2-9} generations back
before {settlement.name} was founded
in the year of the long winter|weather
during the last great war|military
{n:2-9} years ago
in a hard season nobody likes to remember
a lifetime ago
in the first years after the plague|disease
on the eve of a famous siege|military
roughly two hundred years ago, by most counts
in the reign of a king nobody names now|politics
when the roads were still new|road
last spring, or so the rumors say
when the river still ran the old way|water
in the age of the great fairs|festival
""")
table("item.why", "Made because (reads after: It exists ...)", """
to settle a debt
as a wedding gift that was never delivered
to win a bet with a rival
because a flood took the maker's first attempt
because a patron paid in advance and then vanished
to protect someone who could not protect themselves
as a quiet act of grief after a loss that was never spoken of
because the maker lost a competition and wanted another chance
as the maker's test piece for a guild that rejected it
to keep a promise to a dying friend
to impress someone who never even saw it
because the maker was bored and had good materials
to hide something inside it
as payment for a favor from something that does not forget
on commission from {faction.generic}
as one of a matched set, the rest of which are lost
because the maker was told it could not be done
""")
table("item.what", "Made for", """
to make a hard job a little easier|||
to serve as a keepsake that happened to be useful
to help {a occupation} do their work
as a gift for an apprentice
to be sold at a fair for more than it was worth
to see its maker through a bad winter
to settle a quarrel between two guilds|trade politics
to be lost on purpose|mystery
to help thieves cross the rooftops unseen||3|fx:stealth
to keep a smuggler one step ahead of the watch||3|fx:stealth
to guide caravans through the passes in bad weather||3|fx:travel
to carry a soldier through a long campaign||3|fx:war
to keep a healer's patients alive until dawn||3|fx:healing
to catch liars at a magistrate's table||3|fx:knowledge/fx:social
to light a miner's way through lightless tunnels||3|fx:light
to keep a ward intact through the night||3|fx:protection
to help a craftsperson finish what lesser hands could not||3|fx:craft
to calm a crowd, or to start a riot||3|fx:social
to hold back a flood, a fire, or a rumor||3|fx:control
to teach a student something they were not ready for||3|fx:magic/fx:knowledge
to see through a fog, a lie, or a disguise||3|fx:senses/fx:knowledge
to win a duel by a very small margin||2|fx:war
to keep a mountain pass open for one more winter||2|fx:travel/fx:protection
""")
table("item.owner", "A notable owner", """
{npc.named}, who used it to build a small fortune and then lost the fortune|k:npc|3
a hedge knight who died with it still on, and was buried without it|military
{campaign.npc}, who has never admitted owning it|k:npc|3
{a ancestry.adj} {occupation} who swore it brought luck, and was right exactly once
the {name.adj} {name.collective}, whose last member sold it for a meal|k:group
a wandering {occupation} who traded it away for a night's lodging|road trade
a child who treated it as a toy for years|family
a magistrate who never used it but kept it locked away|politics
{faction.generic}, who treated it as a sacred relic|religion
a famed {occupation} whose name is on three songs and no tombstones|festival
{npc.named}, who is still looking for it|k:npc|2
a smuggler who hid it inside a loaf of bread|crime
a king's courier who delivered everything but this|politics road
a widow who wore it every day and never explained why|family
{campaign.faction}, who count it among their lost treasures|k:faction|2
""")
table("item.fate", "How it was lost", """
It was lost in a fire that took its owner's workshop.
It was stolen from a dying owner by someone who was there to help.
It was sold to pay a debt, and the buyer was never found.
It was left behind in a hurry when its owner fled a town.
It was won, and then lost, in a single game of cards.
It was given away by an owner who was told it was cursed, which it is not.
It was buried with its owner, and later dug up by someone with fewer scruples.
It was dropped into a river during a chase and was never seen again, until now.
It was confiscated by the watch and then, somehow, never entered into the records.
It was carried off by a jackdaw, according to the only witness.
It was hidden for safekeeping and the hiding place was forgotten.
It was exchanged for something far less valuable by a person who thought they were getting the better deal.
It was taken as a trophy and kept on a shelf for decades.
It was lent to a friend, who then died without mentioning it.
""")
table("item.found", "How it was found", """
It turned up in a sack of refuse, wrapped in a child's sock.
It was found in the lining of an old coat sold at auction.
It was dug up by a farmer who thought it was a stone.
It was pulled from a river by a net meant for fish.
It was discovered behind a loose brick in a house being torn down.
It was inherited by someone who had no idea what they were holding.
It was won as a prize at a tavern game, to the embarrassment of the host.
It was sold by a peddler who could not remember where he got it.
It was found in the belly of a creature that had no business swallowing it.
It was recovered from a sunken wagon in a dry season.
It was presented as a gift by someone who asked for nothing in return, which was suspicious.
It was handed over by a dying stranger who refused to give a name.
""")
table("item.secret", "The secret (hidden truth, sentences)", """
It is one of a matched set, and the others are in worse hands.
Its maker is still alive, and wants it back.
The maker's mark is a forgery, and the real maker is far more famous.
It works only because something small and patient is bound inside it.|t:weird
It was made to be a trap, and has not yet sprung.|t:grim
It remembers its previous owners, and sometimes behaves as one of them would.|t:weird mystery
Someone has been paying a quiet fee for decades to make sure it is never destroyed.|mystery
Its effect is a debt that someone is still paying, and the payments are getting harder.|t:grim
It was made as an apology, and the apology was never accepted.
It is a copy of something far more dangerous that the maker could not bring themselves to destroy.|mystery
Its first owner is buried nearby, and the grave is not as quiet as the town believes.|undead t:grim
A famous person had it, and never mentioned it, because they used it to cheat.|crime politics
A faction would pay more for its history than for the item.|politics trade
The maker hid a message in it that has never been read.|mystery
It was blessed by a saint, and the saint's followers do not know it exists.|religion
It sees to it that its owners always have just enough, and never more.|t:light
Its power comes from a promise, and the promise is nearly due.|t:grim
The item thinks of itself as a person's guardian, and tries, clumsily, to be one.|t:light fx:protection
It lets its owner pass unnoticed because it quietly makes people forget them, a little.|fx:stealth t:weird
Healing with it costs something small and personal, and the owner has stopped noticing what.|fx:healing t:grim
It knows secrets about people in the room, and has no way to say so.|fx:knowledge fx:social t:weird
""")
table("item.secret.condition", "How the secret comes out", """
The truth shows only when the item is held in moonlight.
The secret appears if the maker's mark is compared with an official registry stamp.
The secret is revealed when someone says the maker's name aloud in front of it.
Only a person who has lost someone close to them can see it.
It takes a night of quiet watching to notice.
It surfaces if the item is taken to the place where it was made.
It shows up under bright, hot light, and nowhere else.
A skilled repairer would spot it while taking the item apart.
""")
table("item.false", "A false tale (what people believe, wrongly)", """
Folk say a saint made it. No saint ever did.
Everyone insists it has never failed its owner. It has, several times.
People claim it was stolen from a king's tomb. It was not.
It is said to be cursed, because three owners died. All three were very old.
A popular song says it was made by a dragon. The maker was a baker.
Many believe it only works for people with a good heart. It works for anyone.
The story goes that it was made in a single night. It took years.
Locals say it vanishes when its owner dies. It does not, and has never been lost that way.
A traveling storyteller claims it can be destroyed only by fire. That is a guess.
Most people think it is far older than it is.
It is said to grant one wish a year, a story invented to sell it.
Folk say it brings bad luck to anyone who sells it. It brings bad luck to anyone who buys it cheaply, which is different.
""")

# ---- more entries, so repeated rolls feel different
for _name, _lines in {'item.owner': '\na bell-ringer who wore it to every funeral in a hard decade|religion\na river pilot who credited it with a hundred safe crossings|water trade\na tax assessor who confiscated it and then quietly kept it|politics\na nun who carried it in a hymn book and never explained why|religion\na mercenary captain who lost three companies and kept the item|military\nan apprentice who stole it from a master and never used it|craft crime\na street performer who built an entire act around it|festival\n{faction.generic}, whose records list it under a different name|politics\nan archivist who cataloged it and then lost the catalog|mystery\n{npc.named}, who sold it twice to two different buyers|crime k:npc\n', 'item.fate': '\nIt was left in a rented room when its owner skipped town without paying.\nIt was carried off by a flood along with a ruined cart.\nIt was handed to a priest for safekeeping, and the priest was transferred.\nIt was won in a wrestling match by someone who did not want it.\nIt was mistaken for a common one and sold in a bundle for a few coppers.\nIt was thrown into a well to keep it from a creditor and then forgotten.\nIt was surrendered under a flag of truce and never returned.\nIt was hidden in a hollow tree during a war, and the war outlasted the owner.\n', 'item.found': '\nIt was sold by a child who found it in a lost-and-found chest.\nIt surfaced in a clearance sale of a bankrupt shop.\nIt arrived in the post, wrapped in a note that was mostly an apology.\nIt was pulled out of the wall of an old inn during repairs.\nIt was handed back by a thief who said the owner was cursed with bad luck, which was not entirely a lie.\nIt was picked from a pile of tolls collected at a gate.\nIt was found in a coffin where it did not belong.\nIt was returned by a crow, according to a very serious witness.\n', 'item.secret': "\nIt is far more valuable than it looks, and one buyer already knows.|trade treasure\nIt was stolen long ago, and the original owner's heirs are still searching.|crime family\nIts maker worked on it for decades and never finished it. The unfinished part matters.|craft mystery\nIt was made from something that was not supposed to be used that way.|t:grim magic\nIt has been quietly used in a famous trial, and the verdict is in doubt because of it.|politics crime\nSomeone has been replacing it with copies for years, and no one has noticed.|crime mystery\nIt is the only one of its kind that the maker did not sign, on purpose.|craft mystery\nIt exists because of a promise made at a deathbed, and the promise has an unreasonable condition.|family t:grim\nA collector would pay a great deal for it, and the wrong collectors are already asking.|treasure\n", 'item.false': '\nPeople swear it can only be used by someone born under a certain moon. That is not true.\nLocals say it never needs repair. It has been repaired many times, quietly.\nSome say it was a gift from a king. It was a bribe, and a small one.\nA famous song says it can find the way home. It cannot, and several people have learned that.\nIt is said to be a copy of a lost original. It is the original.\nMost tell the tale that only one exists. Several do.\n', 'item.mark': '\na tiny bird scratched beside the edge\na row of three small rivets in a triangle\na stamped number with no year attached\na looped line like a signature that was never finished\na half moon pressed into the leather\na tiny gate with its bars drawn\na bee with six legs and a small crown\na notch cut into one side, always the left\na stamp that has been scratched over and then, regretfully, left alone\n', 'item.quirk': '\nIt is warm on cold nights and cool on hot ones, which is only sometimes helpful.\nIt collects dust on every surface but one.\nIt leaves a taste of pepper in the mouth of anyone who holds it for long.\nIt is a little too loud when set down on stone.\nIt makes a faint ticking sound at midnight.\nIt gets lost in a pocket more often than it has any right to.\nIt seems to be a slightly different size to each person who holds it.\nIt smells faintly of lavender, whoever carries it.\n'}.items():
    TABLES[_name]["entries"] += [ln.strip() for ln in _lines.strip().splitlines() if ln.strip()]


# ============================================================ the hidden story type that holds an item's history
RECIPES["item_lore"] = {
    "title": "Item lore", "page_type": "Item", "status": "", "threat": None, "hidden": True,
    "slots": [{"key": "who", "label": "Made by", "table": "item.who"},
              {"key": "what", "label": "Made for", "table": "item.what"},
              {"key": "where", "label": "Made at", "table": "item.where"},
              {"key": "when", "label": "Made when", "table": "item.when"},
              {"key": "why", "label": "Made because", "table": "item.why"}],
    "extras": [{"key": "mark", "label": "Maker's mark", "table": "item.mark"},
               {"key": "owner", "label": "A notable owner", "table": "item.owner"},
               {"key": "fate", "label": "How it was lost", "table": "item.fate"},
               {"key": "found", "label": "How it was found", "table": "item.found"},
               {"key": "incident", "label": "A notable incident", "table": "item.incident", "chance": 70},
               {"key": "state", "label": "Its condition", "table": "item.state", "chance": 60},
               {"key": "secret", "label": "The secret", "table": "item.secret"},
               {"key": "condition", "label": "To learn the secret", "table": "item.secret.condition", "chance": 35},
               {"key": "false", "label": "A false tale", "table": "item.false"}],
    # Different shapes, and some leave a clause out of the summary (every line still shows in the list below it).
    "compose": ["{@who} made it {@where}, {@when}, {@what}. It exists {@why}.",
                "{@when}, {@who} made it {@where}, {@what}. It exists {@why}.",
                "{@where}, {@when}, {@who} made it {@what}. It exists {@why}.",
                "Its maker, {@who}, made it {@where}, {@when}. It was meant {@what}, and it exists {@why}.",
                "{@who} made it {@what}, {@where}, {@when}. It exists {@why}.",
                "It exists {@why}: {@who} made it {@where}, {@when}, {@what}.",
                "It was made {@when}, {@where}, by {@who}. It was meant {@what}, and it exists {@why}.",
                "By most accounts, {@who} made it {@where}, {@when}, {@what}. It exists {@why}.",
                "{@who} made it {@where}, {@when}. It exists {@why}.",
                "{@when}, {@who} made it {@what}. It exists {@why}.",
                "{@who} made it {@where}, {@what}. It exists {@why}.",
                "It was made {@what}, by {@who}, {@when}. It exists {@why}.",
                "{@who} made it {@where}. It was meant {@what}, and it exists {@why}.",
                "As the story goes, {@who} made it {@when}, {@where}. It exists {@why}."],
    "title_template": "{@what.short}",
}

# ============================================================ Hallowmead and Underhallow flavor (content pack: hallowmead)
# Every line here is limited to the hallowmead pack, so the Story tab's Hallowmead checkbox turns it all on or off.
# Marks use the banner designs from the setting bible. Nothing here names Corebound equipment or the Immortals.
def _pack(text):
    lines = []
    for ln in text.strip().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("|")
        while len(parts) < 2:
            parts.append("")
        tags = parts[1].split()
        if "p:hallowmead" not in tags:                  # the pack tag only: an environment tag here made these lines
            tags.append("p:hallowmead")                 # about 6 times likelier whenever the Setting was underground
        parts[1] = " ".join(tags)
        lines.append("|".join(parts))
    return "\n".join(lines)


_HM = {
    "item.who": """
a Finders Keep tinker working from refuse|craft treasure k:npc mk:goblin|3
a kobold mason of the Grand Underhall|craft k:npc mk:kobold|3
a Hushwarrens broker who never signs anything|crime mystery k:npc mk:ratfolk|3
a Stillwater Hollow water-shaper|nature k:npc mk:grippli|2
a root leshy gardener of the Quiet Ring|nature k:npc mk:leshy|2
a mender of the Mending, who repaired it more than made it|craft family k:npc mk:mender|3
an awakened animal building something it was still working out|t:light k:npc mk:awakened|1
the workshop of a surface artisan who threw the work away as flawed|craft politics|2
""",
    "item.where": """
in the salvage yards of Finders Keep, under the refuse chutes|craft treasure|3
in a Mending workshop crowded with half-repaired tools|craft family|3
in a kobold masons' yard at the Grand Underhall|craft|3
in the sewer-level corridors near the Hushwarrens|crime mystery|3
on a stilt platform at Stillwater Hollow|nature|2
in the root halls of the Quiet Ring|nature|2
at a stall in the Crossings, beneath the crystal spire|trade festival|3
beside the glowing teal pools of Firstlight|magic nature|2
""",
    "item.when": """
in the early years of the Underhallow settlements||2
in the generation after the grippli followed the river down|nature|2
two generations ago, when the ratfolk were blamed for a plague|disease politics|2
not long after Hallowmead began dumping its refuse down the chutes|trade|2
after a great collapse closed half the tunnels|craft|2
""",
    "item.material.decor": """
salvaged brass||2
tunnel glass||2
root-wood||2
stitched cloth scraps||2
kobold-cut stone||2
rusted scrap beaten smooth||2
dried bracket fungus||1
woven grippli reed||1
""",
    "item.mark": """
a rough off-white skull, crudely inked|craft treasure|3|mk:goblin
a white dragon-shaped question mark, painted with great care|craft|3|mk:kobold
a pale broken crescent over a small downward fang, drawn very thin|crime mystery|3|mk:ratfolk
a flowing pale water-current of loose brush strokes|nature|2|mk:grippli
a pale living root-circle with one gap left open|nature|2|mk:leshy
a broken repair-circle around a central node, with one patch in another color|craft family|3|mk:mender
a branching pale mark with a vertical center, scratched in a hurry|magic nature|2|mk:awakened
""",
    "item.found": """
It came down a refuse chute from Hallowmead, wrapped in a surface family's tablecloth.|treasure|3
A repair crew from the Mending found it inside a machine they were fixing.|craft|3
A Hushwarrens courier carried it down from the surface in a hollowed loaf of bread.|crime mystery|3
It washed down the river through Stillwater Hollow and caught on a sluice gate.|nature|2
It was left at the Crossings with a note asking only that someone take it.|trade mystery|2
A goblin salvage crew sorted it out of a load of lamp glass and nearly threw it back.|treasure t:light|2
A leshy found it pushed up from below, wrapped in roots.|nature|1
""",
    "item.owner": """
a Finders Keep salvager who traded it for three good ropes|treasure craft|2
a kobold mason who used it for decades and never once mentioned it|craft|2
a Mending storykeeper who recorded every repair it ever made|craft family mystery|2
""",
    "item.what": """
to keep a tunnel crew alive through a collapse||3|fx:protection/fx:travel
to find the good salvage before the other crews do||3|fx:senses/fx:knowledge
to carry word between settlements without anyone reading it||3|fx:stealth/fx:travel
to keep a sluice from flooding the lower tunnels||2|fx:control/fx:protection
to help a repairer keep one more old friend running||3|fx:craft/fx:healing
""",
    "item.secret": """
It was thrown away by a surface workshop as a failure, and the workshop has been looking for it ever since.|mystery politics
Its maker kept meticulous proof of who really owned it, and the proof still exists.|crime mystery
Its repairs hide an older object, and the repairers know exactly what.|craft
The Grand Underhall would claim it, because the stone in it came from a famous arch.|politics craft
It carries a message from someone on the surface who wants to be found.|mystery
""",
    "item.quirk": """
It is always slightly damp, as if it spent years near the water at Stillwater Hollow.|nature
It smells of fresh-cut root, even in the middle of the Crossings.|nature
It hums faintly when carried under a kobold-built arch.|craft
It ticks softly when something nearby needs repair.|craft family
""",
    "item.adj": """
Salvaged||2
Found||2
Mended||2
Refuse-Born
Re-Stitched
Underhall
""",
    "item.stem": """
the Crossings||2
Found Things||2
Mended Hands||2
the Lower Routes
Deep Water
Salvage Days
the Open Arch
Small Repairs||2
""",
}
for _name, _lines in _HM.items():
    table(_name, _name, _pack(_lines), into=HALLOWMEAD)


def hallowmead_additions():
    """{table name: [entry lines]} for the Hallowmead content pack."""
    return {name: list(spec["entries"]) for name, spec in HALLOWMEAD.items()}


# ============================================================ cultures: whose style an item is made in
# A culture changes an item's NAME, LOOK, and QUIRK (and, for a few, the weapon it is built on). The tables below are
# ordinary Story Forge tables, so Edit Tables can change any of them. Tone (any, grim, light, weird) steers which name
# patterns are used: with a tone chosen, only patterns for that tone are favored.
CULTURE_INFO = {
    "goblin": dict(label="Goblin", ancestries=["Goblin"], mk="goblin", words=("goblin",)),
    "kobold": dict(label="Kobold", ancestries=["Kobold"], mk="kobold", words=("kobold",)),
    "ratfolk": dict(label="Ratfolk", ancestries=["Ratfolk"], mk="ratfolk", words=("ratfolk", "ysoki")),
    "grippli": dict(label="Grippli", ancestries=["Grippli"], mk="grippli", words=("grippli",)),
    "leshy": dict(label="Leshy and arboreal", ancestries=["Leshy", "Arboreal"], mk="leshy", words=("leshy", "arboreal")),
    "mender": dict(label="Mender (automaton or poppet)", ancestries=["Automaton", "Poppet"], mk="mender",
                   words=("automaton", "poppet")),
    "awakened": dict(label="Awakened animal", ancestries=["Awakened Animal"], mk="awakened", words=("awakened",)),
    "dwarf": dict(label="Dwarf", ancestries=["Dwarf"], mk="dwarf", words=("dwarf", "dwarven")),
    "elf": dict(label="Elf", ancestries=["Elf"], mk="elf", words=("elf", "elven")),
    "gnome": dict(label="Gnome", ancestries=["Gnome"], mk="gnome", words=("gnome", "gnomish")),
    "halfling": dict(label="Halfling", ancestries=["Halfling"], mk="halfling", words=("halfling",)),
    "orc": dict(label="Orc", ancestries=["Orc"], mk="orc", words=("orc", "orcish")),
}
# Factions in the Hallowmead setting, by name, in case a page's kind text was edited.
FACTION_CULTURE = {"finders keep": "goblin", "the grand underhall": "kobold", "the hushwarrens": "ratfolk",
                   "stillwater hollow": "grippli", "the quiet ring": "leshy", "the mending": "mender",
                   "firstlight": "awakened"}


def culture_for_text(text):
    """The culture a piece of text (an ancestry, a faction's kind, a page title) points to, or ''."""
    import re as _re
    low = str(text or "").lower()
    if low.strip() in FACTION_CULTURE:
        return FACTION_CULTURE[low.strip()]
    for key, info in CULTURE_INFO.items():
        if any(_re.search(r"\b" + _re.escape(w) + r"\b", low) for w in info["words"]):
            return key
    return ""


CU_PATTERNS = """
# Name variables: @form @stem @maker @base @kind @spell, and from the item's own history and effects:
#   @purpose (what it was made for)   @place (where it was made)   @owner (a notable owner)
#   @fxthing @fxwpn @fxarm (words for what it does)
# A line with nm:purpose, nm:place, nm:owner, or nm:fx is used only when that variable exists for the item.
# neutral patterns (used when no tone is chosen, and mixed in lightly otherwise)
{item.cu.@C@.adj} {@form}||5|it:worn/it:held
{@form} of {item.cu.@C@.thing}||4|it:worn/it:held
{item.cu.@C@.adj} {@form} of {item.cu.@C@.thing}||2|it:worn/it:held
{@maker} {item.cu.@C@.adj} {@form}||3|it:worn/it:held mk:named
{@maker} {@form} of {item.cu.@C@.thing}||2|it:worn/it:held mk:named
{@form} of {@stem}||1|it:worn/it:held
{@form} of {@fxthing}||4|it:worn/it:held nm:fx
{item.cu.@C@.adj} {@form} of {@fxthing}||3|it:worn/it:held nm:fx
{@purpose} {@form}||4|it:worn/it:held nm:purpose
{item.cu.@C@.adj} {@purpose} {@form}||2|it:worn/it:held nm:purpose
{@place} {@form}||3|it:worn/it:held nm:place
{@owner} {@form}||2|it:worn/it:held nm:owner
{item.cu.@C@.wpn}||7|it:weapon
{item.cu.@C@.wpn}, the {@base}||3|it:weapon
{item.cu.@C@.adj} {@base}||2|it:weapon
{@maker} {item.cu.@C@.wpn}||2|it:weapon mk:named
{@fxwpn}||4|it:weapon nm:fx
{item.cu.@C@.adj} {@fxwpn}||2|it:weapon nm:fx
{@purpose} {@base}||3|it:weapon nm:purpose
{@place} {@base}||2|it:weapon nm:place
{@owner} {@base}||1|it:weapon nm:owner
{item.cu.@C@.arm}||7|it:armor
{item.cu.@C@.adj} {@base}||2|it:armor
{@maker} {item.cu.@C@.arm}||2|it:armor mk:named
{@fxarm}||4|it:armor nm:fx
{item.cu.@C@.adj} {@fxarm}||2|it:armor nm:fx
{@purpose} {@base}||3|it:armor nm:purpose
{@place} {@base}||2|it:armor nm:place
{@kind} of {@spell}||2|it:wand/it:scroll/it:potion/it:device
{item.cu.@C@.adj} {@kind} of {@spell}||6|it:wand/it:scroll/it:potion/it:device
{@maker} {item.cu.@C@.adj} {@kind} of {@spell}||2|it:wand/it:scroll/it:potion/it:device mk:named
{@purpose} {@kind} of {@spell}||2|it:wand/it:scroll/it:potion/it:device nm:purpose
{@place} {@kind} of {@spell}||1|it:wand/it:scroll/it:potion/it:device nm:place
# weird
{@form} of {item.cu.@C@.thing}, More or Less|t:weird|2|it:worn/it:held
{item.cu.@C@.wpn} of {item.name.weird.thing}|t:weird|3|it:weapon
The {@base} Called {item.cu.@C@.wpn}|t:weird|2|it:weapon
{@maker} {item.cu.@C@.wpn} of {item.name.weird.thing}|t:weird|2|it:weapon mk:named
{item.cu.@C@.arm} of {item.name.weird.thing}|t:weird|3|it:armor
{@fxarm} of {item.name.weird.thing}|t:weird|2|it:armor nm:fx
{item.cu.@C@.adj} {@kind} of Mostly {@spell}|t:weird|4|it:wand/it:scroll/it:potion/it:device
{item.cu.@C@.adj} {@kind} of {@spell}, Possibly|t:weird|2|it:wand/it:scroll/it:potion/it:device
The {item.cu.@C@.adj} {@kind} That Wants to {@spell}|t:weird|2|it:wand/it:scroll/it:potion/it:device
{@maker} {item.cu.@C@.adj} {@kind} of Mostly {@spell}|t:weird|2|it:wand/it:scroll/it:potion/it:device mk:named
# light
{@maker} Little {item.cu.@C@.wpn}|t:light|2|it:weapon mk:named
{@maker} Good Old {item.cu.@C@.arm}|t:light|2|it:armor mk:named
{@maker} {item.cu.@C@.adj} {@form} of {item.name.light.thing}|t:light|2|it:worn/it:held mk:named
{@maker} {item.cu.@C@.adj} {@kind} of Cheerful {@spell}|t:light|2|it:wand/it:scroll/it:potion/it:device mk:named
Sir {item.cu.@C@.adj} {@form}|t:light|3|it:worn/it:held
{item.cu.@C@.adj} {@form} of {item.name.light.thing}|t:light|4|it:worn/it:held
{@form} of {item.cu.@C@.thing} (Lightly Used)|t:light|2|it:worn/it:held
Little {@purpose} {@form}|t:light|2|it:worn/it:held nm:purpose
Little {item.cu.@C@.wpn}|t:light|4|it:weapon
Sir {item.cu.@C@.wpn}|t:light|3|it:weapon
{item.cu.@C@.wpn} the {item.cu.@C@.adj}|t:light|2|it:weapon
Good Old {item.cu.@C@.arm}|t:light|3|it:armor
{item.cu.@C@.arm} of {item.name.light.thing}|t:light|3|it:armor
{item.cu.@C@.adj} {@kind} of {@spell} (Loud)|t:light|2|it:wand/it:scroll/it:potion/it:device
{item.cu.@C@.adj} {@kind} of Cheerful {@spell}|t:light|3|it:wand/it:scroll/it:potion/it:device
# grim
{@maker} {item.cu.@C@.adj} {@form} of {item.name.grim.thing}|t:grim|2|it:worn/it:held mk:named
{@maker} {item.cu.@C@.wpn}, {item.name.grim.epithet.weapon}|t:grim|2|it:weapon mk:named
{@maker} {item.cu.@C@.arm}, {item.name.grim.epithet.armor}|t:grim|2|it:armor mk:named
{@maker} {item.cu.@C@.adj} {@kind} of {@spell}, {item.name.grim.epithet.cons}|t:grim|2|it:wand/it:scroll/it:potion/it:device mk:named
{item.cu.@C@.adj} {@form} of {item.name.grim.thing}|t:grim|4|it:worn/it:held
{item.cu.@C@.adj} {@form} of the {item.name.grim.noun}|t:grim|3|it:worn/it:held
{item.cu.@C@.adj} {@form}, {item.name.grim.epithet.worn}|t:grim|2|it:worn/it:held
{@purpose} {@form}, {item.name.grim.epithet.worn}|t:grim|2|it:worn/it:held nm:purpose
{item.cu.@C@.wpn}, {item.name.grim.epithet.weapon}|t:grim|4|it:weapon
{item.cu.@C@.wpn} of {item.name.grim.thing}|t:grim|2|it:weapon
{@fxwpn}, {item.name.grim.epithet.weapon}|t:grim|2|it:weapon nm:fx
{item.cu.@C@.arm}, {item.name.grim.epithet.armor}|t:grim|4|it:armor
{@fxarm}, {item.name.grim.epithet.armor}|t:grim|2|it:armor nm:fx
{item.cu.@C@.adj} {@kind} of {@spell}, {item.name.grim.epithet.cons}|t:grim|3|it:wand/it:scroll/it:potion/it:device
The Last {item.cu.@C@.adj} {@kind} of {@spell}|t:grim|2|it:wand/it:scroll/it:potion/it:device
"""

# the same shapes with the generic (no culture) vocabulary
GENERIC_PATTERNS = """
{@form} of {@stem}||5|it:worn/it:held
{item.adj} {@form}||2|it:worn/it:held
{item.adj} {@form} of {@stem}||3|it:worn/it:held
{@maker} {@form}||2|it:worn/it:held mk:named
{@maker} {@form} of {@stem}||2|it:worn/it:held mk:named
{@form} of {@fxthing}||5|it:worn/it:held nm:fx
{item.adj} {@form} of {@fxthing}||3|it:worn/it:held nm:fx
{@purpose} {@form}||5|it:worn/it:held nm:purpose
{item.adj} {@purpose} {@form}||2|it:worn/it:held nm:purpose
{@place} {@form}||3|it:worn/it:held nm:place
{@owner} {@form}||2|it:worn/it:held nm:owner
{item.weapon.a}{item.weapon.b}||6|it:weapon
{@maker} {@base}||2|it:weapon mk:named
{item.adj} {@base}||1|it:weapon
{@fxwpn}||5|it:weapon nm:fx
{@purpose} {@base}||3|it:weapon nm:purpose
{@place} {@base}||2|it:weapon nm:place
{@owner} {@base}||1|it:weapon nm:owner
{item.armor.a}{item.armor.b}||6|it:armor
{@maker} {@base}||2|it:armor mk:named
{item.adj} {@base}||1|it:armor
{@fxarm}||5|it:armor nm:fx
{@purpose} {@base}||3|it:armor nm:purpose
{@place} {@base}||2|it:armor nm:place
{@kind} of {@spell}||4|it:wand/it:scroll/it:potion/it:device
{item.adj} {@kind} of {@spell}||2|it:wand/it:scroll/it:potion/it:device
{@maker} {@kind} of {@spell}||1|it:wand/it:scroll/it:potion/it:device mk:named
{@purpose} {@kind} of {@spell}||2|it:wand/it:scroll/it:potion/it:device nm:purpose
{@place} {@kind} of {@spell}||1|it:wand/it:scroll/it:potion/it:device nm:place
{item.weapon.a}{item.weapon.b} of {item.name.weird.thing}|t:weird|3|it:weapon
{item.armor.a}{item.armor.b} of {item.name.weird.thing}|t:weird|3|it:armor
{@fxarm} of {item.name.weird.thing}|t:weird|2|it:armor nm:fx
{@kind} of Mostly {@spell}|t:weird|4|it:wand/it:scroll/it:potion/it:device
The {@kind} That Wants to {@spell}|t:weird|2|it:wand/it:scroll/it:potion/it:device
Sir {item.adj} {@form}|t:light|3|it:worn/it:held
{item.adj} {@form} of {item.name.light.thing}|t:light|4|it:worn/it:held
Little {@purpose} {@form}|t:light|2|it:worn/it:held nm:purpose
Little {item.weapon.a}{item.weapon.b}|t:light|4|it:weapon
Sir {item.weapon.a}{item.weapon.b}|t:light|3|it:weapon
Good Old {item.armor.a}{item.armor.b}|t:light|3|it:armor
{@kind} of Cheerful {@spell}|t:light|3|it:wand/it:scroll/it:potion/it:device
{@form} of {item.name.grim.thing}|t:grim|4|it:worn/it:held
{item.adj} {@form} of the {item.name.grim.noun}|t:grim|3|it:worn/it:held
{@purpose} {@form}, {item.name.grim.epithet.worn}|t:grim|2|it:worn/it:held nm:purpose
{item.weapon.a}{item.weapon.b}, {item.name.grim.epithet.weapon}|t:grim|4|it:weapon
{@fxwpn}, {item.name.grim.epithet.weapon}|t:grim|2|it:weapon nm:fx
{item.armor.a}{item.armor.b}, {item.name.grim.epithet.armor}|t:grim|4|it:armor
{@fxarm}, {item.name.grim.epithet.armor}|t:grim|2|it:armor nm:fx
{@kind} of {@spell}, {item.name.grim.epithet.cons}|t:grim|3|it:wand/it:scroll/it:potion/it:device
The Last {@kind} of {@spell}|t:grim|2|it:wand/it:scroll/it:potion/it:device
"""
table("item.name", "Item name patterns (no culture). Variables: @form @stem @maker @base @kind @spell @purpose @place @owner @fxthing @fxwpn @fxarm", GENERIC_PATTERNS)

table("item.name.weird.verb", "Weird names: what it did (no longer used by the built-in name patterns, which now name an item for what it does; kept for patterns you write yourself)", """
Hummed to Itself
Was Never Where You Left It
Remembered Your Name
Argued with Doors
Tasted of Thursday
Knew What You Did
Smelled of Rain Indoors
Leaned Toward Trouble
Counted Backwards
Blinked When Unobserved
Kept Small Secrets
Asked Too Many Questions
Would Rather Be a Spoon
Dreamed of Larger Rooms
Had Opinions About Weather
Got Lost on Purpose
Whispered in a Borrowed Voice
Learned Your Name First
Never Quite Fit
""")
table("item.name.weird.thing", "Weird names: strange things (reads after 'of ...')", """
Seventeen Small Mistakes
Borrowed Thursdays
the Second Left Shoe
Unfinished Sentences
the Wrong Answer
Quiet Thunder
Soft Corners
Half a Moon
Forgotten Weather
the Inside of Doors
Polite Lightning
Extra Tuesdays
the Fifth Direction
Unlit Candles
Tiny Large Things
a Very Specific Smell
""")
table("item.name.light.thing", "Light names: cheerful things (reads after 'of ...')", """
Mild Enthusiasm
Small Triumphs
Good Intentions
Happy Accidents
Lucky Socks
Reasonable Hopes
Unearned Confidence
Tiny Victories
Optimistic Mornings
a Cheerful Din
Warm Pockets
Better Days
""")
table("item.name.grim.thing", "Grim names: dark things (reads after 'of ...')", """
Slow Ends
Cold Hands
the Last Candle
Hollow Oaths
Burned Bridges
Bitter Salt
the Long Dark
Quiet Graves
Unpaid Debts
Ashes and Iron
Unfinished Funerals
Grim Tidings
""")
table("item.name.grim.noun", "Grim names: nouns (reads after 'of the ...')", """
Last Fire
Cold Grave
Long Winter
Final Hour
Gray Road
Hollow Crown
Empty Hearth
Burning Field
""")
table("item.name.grim.epithet.weapon", "Grim weapon epithets (follow a comma)", """
Widow-Maker
the Last Argument
Ender of Feuds
Debt-Collector
Bringer of Quiet
the Long Goodbye
Oathbreaker
the Final Word
Marrow-Seeker
Closer of Doors
Hollow Promise
""")
table("item.name.grim.epithet.armor", "Grim armor epithets (follow a comma)", """
the Last Wall
Grave-Warden
the Long Vigil
Keeper of Quiet Doors
Mourner's Bulwark
the Shut Gate
Winter's Door
Hollow Bastion
Oathkeeper
the Patient Shell
""")
table("item.name.grim.epithet.worn", "Grim worn and held item epithets (follow a comma)", """
Grave-Tender
Mourner's Friend
Keeper of Small Debts
the Long Goodbye
Teller of Endings
Hollow Promise
Bearer of Bad News
Winter's Companion
the Last Courtesy
""")
table("item.name.grim.epithet.cons", "Grim wand, scroll, potion, and device epithets (follow a comma)", """
the Last Resort
Final Mercy
Bitter Medicine
Sorrow's End
the Last Word
Cold Comfort
Last Orders
""")
# --- tone for the existing look and quirk tables (used with a tone chosen)
TABLES["item.motif"]["entries"] += [ln.strip() for ln in """
covered in tiny doors that do not open|t:weird
etched with a map of a place that is slightly different each day|t:weird
set with an eye that is definitely just glass|t:weird
stitched with thread that is not quite any color|t:weird
decorated with cheerful little flags|t:light
painted with smiling suns|t:light
tied with a very festive bow|t:light
etched with a ring of tiny skulls|t:grim
stained dark along one edge|t:grim
scored with a tally of something unpleasant|t:grim
""".strip().splitlines()]
TABLES["item.quirk"]["entries"] += [ln.strip() for ln in """
It whispers a single word when no one is near, and the word changes.|t:weird
It is always found one step to the left of where it was set down.|t:weird
It dreams, and its owner hears about it in the morning.|t:weird
It sneezes just before it is about to be useful.|t:light
It plays the first line of a happy tune when picked up.|t:light
It grows colder when someone nearby is lying.|t:grim
It remembers every death within sight of it, and says nothing.|t:grim
""".strip().splitlines()]

# --- the cultures
_CU = {
    "goblin": dict(
        adj="""
Stabby
Pokey
Bitey
Chompy
Rusty
Clangy
Burny
Sparky
Squeaky
Lumpy
Crooked
Dented
Wobbly
Greasy
Soggy
Smelly
Spiky
Bent
Patched
Gnawed
Sticky
Twice-Stolen
Borrowed
Found
Lucky
Loud
Extra-Pointy
Questionable
""",
        thing="""
Many Pockets
Questionable Origins
Poor Decisions
Lost Teeth
Stolen Afternoons
Good Smells
Bad Ideas
Burnt Fingers
Fine Rot
Shiny Things
Loud Noises
Very Sharp Sticks
Borrowed Luck
Sudden Doors
the Third Pocket
the Old Dog
""",
        wpn="""
Stabbity
Pokey Stick
Old Bitey
Gnawbone
Skullrattle
Fingerbiter
Big Bonk
Little Bonk
Chompa
Rustfang
Scrapper
Clangor
Sparky Stick
Burnbrand
Kneecapper
Poke-Poke
Thumper
Snaggletooth
Rat Biter
Wobblewhack
Splinter
Pointy End
Chopchop
""",
        arm="""
Tin Hugger
Pot Lid Mail
Bucket Shell
Mostly Armor
Scrap Hide
Clanky Coat
Soup Pot
Dented Pride
Rattlecoat
Lid and Twine
Barrel Vest
Kettle Jerkin
Crunchy Coat
""",
        look="""
patched together from at least three other things
held on with twine and optimism
covered in tiny scratch-drawn teeth
tied with bright rags
dented in a way that looks deliberate
stuck with feathers and bent nails
scorched along one edge
hung with small bells that were clearly stolen
painted with a crude red skull
decorated with mismatched buttons
sticky with something nobody will name
bound with a lot more string than seems necessary
""",
        material="""
scrap tin
bent nails
bucket tin
old boot leather
cooking-pot iron
salvaged brass
rusted iron
barrel-stave wood
gnawed bone
rat-tail cord
bottle glass
cart-wheel iron
""",
        quirk="""
It smells faintly of woodsmoke and old stew.
It rattles whenever a goblin nearby tells a lie, its owner included.
It is always slightly sticky.
It makes a small, pleased squeak when it works.
Goblins find it very funny, for reasons they cannot explain.
Small fires seem to find it.|t:weird
It howls like a dog when dropped.|t:weird
It was named three times and answers to none.|t:light
It is loudly proud of itself, in a language of clangs.|t:light
It has been burned, drowned, and stolen, and takes each as a personal compliment.|t:grim
"""),
    "kobold": dict(
        adj="""
Plumb
Overbuilt
Squared
Reinforced
Keystone
Mortared
Carefully Chiseled
Load-Bearing
Immaculate
Level
True-Cut
Proudly Finished
Arch-Grade
""",
        thing="""
Perfect Joints
Honest Stone
the Long Arch
Properly Set Stones
Twelve Hundred Measurements
the Master Mason
Sound Foundations
Even Courses
a Flawless Corner
the Third Pillar
""",
        wpn="""
Plumbline
Mallet of Correction
Chiselbite
Squarehand
Keystrike
Trowel of Judgment
Mortarbreaker
Straightedge
Levelheart
Rubblesplitter
Grand Hammerette
""",
        arm="""
Arch Mantle
Buttress Coat
Keystone Plate
Overbuilt Hide
Courseplate
Foundation Vest
""",
        look="""
squared at every corner, with a small plumb-bob stamped on it
chiseled with tiny, perfect arches
polished until the maker could see their own pride in it
overbuilt in at least three places
edged in neat, even stitches
set with a tiny keystone
""",
        material="""
kobold-cut stone
tunnel glass
quarried slate
mortared brick
pale limestone
iron banding
tempered copper
""",
        quirk="""
It is slightly heavier than it should be, and its owner insists that is a feature.
It is perfectly level, and cannot be made to stop being level.
It hums faintly under a well-built arch.|t:weird
It looks better after being polished, and demands polishing.|t:light
Its maker's mark is stamped three times, to be sure.|t:light
It has never once been wrong about a measurement, and it has opinions about yours.|t:grim
"""),
    "ratfolk": dict(
        adj="""
Quiet
Whisper-Thin
Unremarked
Hidden
Folded
Pocket-Sized
Quick
Unsigned
Borrowed
Discreet
Many-Pocketed
Slipknot
""",
        thing="""
Small Courtesies
Quiet Routes
Folded Messages
Unsigned Letters
Back Doors
Second Keys
Careful Silence
the Last Light Out
Well-Kept Secrets
""",
        wpn="""
Quickwhisper
Tailwrap
Silent Fang
Needlepoint
Thinblade
Whiskerthorn
Chalkcut
Runner's Bite
Hushpoint
""",
        arm="""
Wrap of Many Folds
Shadow Wrap
Dusk Weave
Layered Quiet
Climbing Coat
""",
        look="""
dark, muted cloth, almost invisible in the shade
wrapped in layers so thin they can be counted by touch
fitted for small, quick hands
marked with one faint pale line, easily rubbed off
stitched with hidden pockets
worn smooth where a thumb always rests
""",
        material="""
dark linen
charcoal wool
blackened tin
sealed wax
thin leather
waxed cord
""",
        quirk="""
It has more pockets than it appears to.
It never makes a sound it does not intend to.
It is always warm from being carried close.
Its seams hide a second, smaller seam.|t:weird
It delivers itself to the right person if left alone long enough.|t:light
It has kept more secrets than its owner, and is smug about it.|t:grim
"""),
    "grippli": dict(
        adj="""
Slick
Flowing
Damp
Dripping
Mossy
Rippling
Tide-Worn
Reed-Wrapped
Pond-Green
Slippery
Steady
""",
        thing="""
Still Water
Patient Rain
Gentle Currents
the Long Pool
Reed Songs
Quiet Ripples
Slow Rivers
Cool Hands
""",
        wpn="""
Reedspear
Rippleblade
Dripthorn
Tidecutter
Slickfang
Pondsting
Sluice-Splitter
Croakbite
""",
        arm="""
Reed Weave
Mud Mantle
Wet Wrap
Lilypad Coat
Stilt-Walker
""",
        look="""
painted with loose, flowing strokes of blue-green
wrapped in damp reed
marked with a quick brush-stroke wave
woven from pond grass and left a little wet
stitched with silver-green thread
worn smooth by running water
""",
        material="""
reed
mud-fired clay
river glass
pond leather
woven grass
wet slate
""",
        quirk="""
It is always a little damp, however dry the day.
It smells of rain.
It ripples in a way that has nothing to do with the wind.|t:weird
It makes frogs inexplicably calm.|t:light
It remembers the shape of every river it has been near.|t:grim
"""),
    "leshy": dict(
        adj="""
Rooted
Budding
Mossy
Grown
Knotted
Gnarled
Sapling
Tendriled
Sprouting
Barked
Twining
Fungal
Dew-Wet
Overgrown
""",
        thing="""
Slow Growing
Deep Roots
Quiet Seasons
Patient Seeds
Green Hours
the Long Winter's Sleep
Soft Moss
Many Small Leaves
""",
        wpn="""
Thornreach
Rootbreaker
Bramblebite
Splinterkin
Twigfang
Seedspitter
Heartwood
Knotfist
""",
        arm="""
Barkhide
Bough Wrap
Briar Mantle
Lichen Coat
Thornbark
""",
        look="""
grown rather than made, with a seam that is really a vein
wrapped in a tight spiral of pale roots
still sprouting a few stubborn leaves
uneven in a way that looks natural, because it is
veined with faint green light
set with a small, determined mushroom
""",
        material="""
living wood
pale root
dried bracket fungus
bark
woven vine
amber sap
""",
        quirk="""
A new leaf appears on it each spring, whatever it is made of.
It leans toward light, and complains when kept in a pack.
It grows slightly if left in the dark long enough.|t:weird
It smells of fresh-cut root.|t:light
It remembers being a tree, and will not discuss it.|t:grim
"""),
    "mender": dict(
        adj="""
Repaired
Patched
Mended
Stitched
Re-Set
Well-Worn
Carefully Fixed
Rebuilt
Salvaged
Re-Fitted
Second-Hand
Imperfectly Sound
""",
        thing="""
Small Repairs
Remembered Hands
Careful Stitches
Second Chances
Mended Hours
Patient Gears
the Last Fix
Borrowed Parts
Gentle Rewinding
""",
        wpn="""
Gearbite
Stitchblade
Mendmaul
Rivet Spike
Wrenchheart
Patchhammer
Second Wind
Springfang
""",
        arm="""
Patchwork Plate
Stitched Shell
Repaired Cuirass
Gear-Woven Mantle
Seamed Hide
""",
        look="""
mended in at least three places, each in a slightly different color
etched with a small circle of repair marks
stitched with bright thread where it was once torn
riveted with care, if not with matching rivets
worn bright where it has been fixed many times
set with one mismatched gear that is clearly loved
""",
        material="""
salvaged brass
mismatched gears
stitched canvas
riveted tin
copper wire
patched leather
""",
        quirk="""
It ticks softly when something nearby needs repair.
It is always almost fixed.
It remembers every hand that has ever mended it, and says so, quietly.|t:weird
It sheds a loose screw whenever it is feeling dramatic.|t:light
It was broken once, and has been very careful ever since.|t:grim
"""),
    "awakened": dict(
        adj="""
Sniffed-At
Gnawed
Burrowed
Whiskery
Feathered
Pawed
Wild-Eyed
Nibbled
Newly Thoughtful
Curious
Clumsy
Instinctive
""",
        thing="""
First Words
New Ideas
Sudden Thoughts
Warm Burrows
Sharp Senses
Wild Fancies
Small Wonders
the Wall's Whispers
""",
        wpn="""
Clawthought
Biteful
Quickpaw
Tuskling
Snapjaw
Peckpoint
Scruffbane
""",
        arm="""
Fur Wrap
Feather Cloak
Burrow Coat
Shell Vest
""",
        look="""
clearly made by someone who had only just discovered thumbs
gnawed at one corner for reasons of its own
stuffed with soft nesting material
decorated with whatever shiny thing was nearest
bound with grass and determination
scratched with a first attempt at a word
""",
        material="""
woven nest straw
chewed leather
feathers and twine
sticks and sinew
shed fur
bright pebbles
""",
        quirk="""
It has been named, and renamed, and renamed again, by someone still learning words.
It smells strongly of whatever its maker ate.
It holds a faint, proud warmth where it was first held.|t:light
It squeaks when a door is about to open.|t:weird
It was made in a hurry by someone who had just understood something frightening.|t:grim
"""),
    "dwarf": dict(
        adj="""
Forge-Marked
Deep-Delved
Oath-Bound
Stout
Anvil-Struck
Rune-Stamped
Hearth-Forged
Granite-Hard
Stubborn
Ironbound
Clan-Marked
""",
        thing="""
Cold Iron Oaths
the Long Hall
Seven Generations
Deep Stone
the Hearth-Fire
Honest Weight
Anvil and Ember
an Old Grudge
""",
        wpn="""
Grudgebreaker
Oathhammer
Stonebiter
Deepdelver
Ironhide Cleaver
Anvilsong
Longbeard
Clanfang
""",
        arm="""
Hearthplate
Stonehold
Oathmail
Deepward
Ironwall
""",
        look="""
stamped with a clan rune, deeply
banded in dark iron
polished by generations of the same family
carved with a row of ancestor names
heavy-set, with a long braid of wire along the edge
""",
        material="""
black iron
deep-mined steel
river stone
red-gold
cold forge-iron
""",
        quirk="""
It will not be lent, and says so in rune.
It remembers grudges.|t:grim
It rings when struck, on the same note, every time.|t:light
It grows heavier when its owner is about to break an oath.|t:weird
"""),
    "elf": dict(
        adj="""
Moonlit
Willow-Slender
Silver-Threaded
Long-Lived
Whisper-Light
Starwoven
Leaf-Edged
Gracile
Dawn-Touched
Ageless
""",
        thing="""
Long Memory
Falling Leaves
Starlight
Slow Seasons
the Quiet Wood
Silver Rain
Ten Thousand Mornings
""",
        wpn="""
Leafwhisper
Starthorn
Moonedge
Willowcut
Dawnreach
Silverthread
Quiet Sorrow
Windlance
""",
        arm="""
Leafmail
Silkward
Starweave
Moonmantle
Willowguard
""",
        look="""
etched with long, curving vines of silver
so light it seems to float
set with a single pale starlike stone
woven from something finer than silk
carved to look like a falling leaf
""",
        material="""
silverwood
moonsilk
pale leaf-gold
fine ash
spun glass
""",
        quirk="""
It feels lighter in moonlight.
It hums faintly, a half-remembered melody.|t:weird
It remembers a longer life than its owner's.|t:grim
It is gentle with strangers and strict with its owner.|t:light
"""),
    "gnome": dict(
        adj="""
Curious
Whirring
Tinkered
Many-Colored
Fizzy
Bubbling
Experimental
Whimsical
Prototype
Spring-Loaded
Overthought
""",
        thing="""
Bright Ideas
Small Explosions
Strange Colors
Fascinating Failures
a Great Many Gears
Unfinished Projects
the Next Experiment
""",
        wpn="""
Whizbang
Pincherette
Sprocketsnap
Clickety
Zapperbolt
Hookhammer
Doodad
Whirlwhack
""",
        arm="""
Gizmo Vest
Tinkerplate
Bubblecoat
Gearweave
Prismshell
""",
        look="""
covered in tiny, labeled dials
brightly dyed in colors that do not match
springing out in several unexpected places
dotted with small, optimistic gems
ticking softly
""",
        material="""
colored glass
tinker's brass
dyed silk
spring steel
bubbling tubes
""",
        quirk="""
It fizzes slightly when idle.
It changes color with its owner's mood.|t:weird
It has a button nobody has found the use of.|t:light
Every repair of it makes it a little more complicated.|t:grim
"""),
    "halfling": dict(
        adj="""
Comfy
Well-Fed
Hearth-Warm
Cheerful
Snug
Home-Spun
Pocket-Sized
Lucky
Tidy
Honest-Stitched
Good-Natured
""",
        thing="""
Second Breakfasts
Warm Hearths
Good Luck
Small Pleasures
Kind Neighbors
Soft Beds
Well-Kept Gardens
""",
        wpn="""
Luckpoint
Skewer
Hearthbane
Wee Pike
Stout Pin
Larder Guard
Goodwill
""",
        arm="""
Cozy Coat
Quilted Hearth
Burrow Vest
Patchwork Cheer
""",
        look="""
stitched with tiny flowers
patched with a neighbor's old quilt
smelling faintly of bread
embroidered with a lucky clover
worn soft by many kind hands
""",
        material="""
homespun wool
soft leather
quilted cloth
polished wood
brass buttons
""",
        quirk="""
It is somehow always warm.
It brings a small, inexplicable good luck at mealtimes.|t:light
It smells of bread.
It is lost far more often than it is found, and always turns up on a kitchen table.|t:weird
It remembers every kindness, and every unpaid pie.|t:grim
"""),
    "orc": dict(
        adj="""
Scarred
Battle-Won
Blood-Marked
Roaring
Tusked
Fire-Hardened
Savage
War-Forged
Brutal
Ash-Born
""",
        thing="""
Many Battles
Fresh Wounds
Hard Roads
Tribal Oaths
Broken Shields
the Last Roar
Hot Blood
""",
        wpn="""
Skullcleaver
Bonesplitter
Warpike
Gorefang
Ironroar
Stonefist
Hardblow
Wolfbane
""",
        arm="""
Warhide
Scarplate
Bonecoat
Tuskguard
Ashmail
""",
        look="""
scratched with a tally of old fights
hung with trophies of fang and horn
blackened by many fires
marked with a clan brand
scarred in a way that looks proud
""",
        material="""
black iron
boar hide
cracked bone
beaten bronze
ox horn
""",
        quirk="""
It goes quiet when its owner is afraid.
It is warm after a fight and cold after a lie.|t:weird
Every dent on it has a story, and someone will tell you.|t:light
It has outlived three owners and means to outlive a fourth.|t:grim
"""),
}
# --- a culture's weapon and armor names that imply a kind of weapon or armor are used only for that kind
#     (wd:S/P/B = damage type, wp:<group> = weapon group, wk:ranged, wt:reach, ac:<light|medium|heavy>, am:<armor group>)
_NEEDS = {
    ("goblin", "wpn"): {"Stabbity": "wd:P/wd:S", "Pokey Stick": "wp:spear/wp:knife/wp:polearm", "Skullrattle": "wd:B",
                        "Fingerbiter": "wd:S/wd:P", "Big Bonk": "wd:B", "Little Bonk": "wd:B", "Chompa": "wd:S/wd:P",
                        "Rustfang": "wd:S/wd:P", "Kneecapper": "wd:B", "Poke-Poke": "wd:P", "Thumper": "wd:B",
                        "Snaggletooth": "wd:P/wd:S", "Rat Biter": "wd:P/wd:S", "Pointy End": "wd:P", "Chopchop": "wd:S"},
    ("goblin", "arm"): {"Pot Lid Mail": "ac:medium/ac:heavy", "Bucket Shell": "ac:medium/ac:heavy",
                        "Scrap Hide": "am:leather/ac:light", "Clanky Coat": "am:chain/am:composite", "Soup Pot": "ac:medium/ac:heavy",
                        "Rattlecoat": "ac:light/am:chain", "Barrel Vest": "ac:light", "Kettle Jerkin": "ac:light",
                        "Crunchy Coat": "am:leather/am:cloth"},
    ("kobold", "wpn"): {"Mallet of Correction": "wp:hammer/wp:club", "Chiselbite": "wd:P/wp:pick/wp:knife",
                        "Keystrike": "wd:B/wp:hammer", "Trowel of Judgment": "wp:knife/wp:sword", "Mortarbreaker": "wd:B",
                        "Straightedge": "wd:S/wp:sword", "Rubblesplitter": "wp:axe/wp:hammer/wp:pick", "Grand Hammerette": "wp:hammer"},
    ("kobold", "arm"): {"Buttress Coat": "ac:heavy/ac:medium", "Keystone Plate": "am:plate/am:composite",
                        "Overbuilt Hide": "am:leather", "Courseplate": "am:plate/am:composite", "Foundation Vest": "ac:light"},
    ("ratfolk", "wpn"): {"Tailwrap": "wp:flail", "Silent Fang": "wd:P/wd:S", "Needlepoint": "wd:P",
                         "Thinblade": "wp:sword/wp:knife", "Whiskerthorn": "wd:P", "Chalkcut": "wd:S/wp:knife", "Hushpoint": "wd:P"},
    ("ratfolk", "arm"): {"Wrap of Many Folds": "ac:light", "Shadow Wrap": "ac:light", "Dusk Weave": "ac:light",
                         "Layered Quiet": "am:cloth/am:leather", "Climbing Coat": "ac:light"},
    ("grippli", "wpn"): {"Reedspear": "wp:spear", "Rippleblade": "wp:sword/wp:knife", "Dripthorn": "wd:P", "Tidecutter": "wd:S",
                         "Slickfang": "wd:P/wd:S", "Pondsting": "wd:P", "Sluice-Splitter": "wp:axe"},
    ("grippli", "arm"): {"Reed Weave": "ac:light", "Mud Mantle": "ac:medium/am:leather", "Wet Wrap": "am:cloth",
                         "Lilypad Coat": "ac:light"},
    ("leshy", "wpn"): {"Thornreach": "wt:reach", "Rootbreaker": "wd:B", "Bramblebite": "wd:P/wd:S", "Splinterkin": "wd:P/wd:B",
                       "Twigfang": "wd:P", "Seedspitter": "wk:ranged", "Heartwood": "wd:B", "Knotfist": "wd:B"},
    ("leshy", "arm"): {"Barkhide": "am:leather", "Bough Wrap": "ac:light", "Lichen Coat": "ac:light/am:leather"},
    ("mender", "wpn"): {"Gearbite": "wd:P/wd:S", "Stitchblade": "wd:S/wp:sword/wp:knife", "Mendmaul": "wp:hammer/wd:B",
                        "Rivet Spike": "wd:P", "Wrenchheart": "wd:B", "Patchhammer": "wp:hammer", "Springfang": "wd:P"},
    ("mender", "arm"): {"Patchwork Plate": "am:plate/am:composite", "Stitched Shell": "am:leather/am:cloth",
                        "Repaired Cuirass": "am:plate/am:chain/am:composite", "Seamed Hide": "am:leather"},
    ("awakened", "wpn"): {"Clawthought": "wd:S/wd:P", "Tuskling": "wd:P", "Snapjaw": "wd:S/wd:P", "Peckpoint": "wd:P"},
    ("awakened", "arm"): {"Fur Wrap": "ac:light", "Feather Cloak": "ac:light", "Burrow Coat": "ac:light"},
    ("dwarf", "wpn"): {"Grudgebreaker": "wd:B/wp:hammer/wp:axe", "Oathhammer": "wp:hammer", "Stonebiter": "wp:pick/wp:axe",
                       "Deepdelver": "wp:pick", "Ironhide Cleaver": "wd:S", "Anvilsong": "wp:hammer/wd:B", "Clanfang": "wd:P/wd:S"},
    ("dwarf", "arm"): {"Hearthplate": "ac:heavy/am:plate", "Stonehold": "ac:heavy/ac:medium", "Oathmail": "am:chain/am:composite",
                       "Ironwall": "ac:heavy"},
    ("elf", "wpn"): {"Leafwhisper": "wp:sword/wp:knife", "Starthorn": "wd:P", "Moonedge": "wd:S", "Willowcut": "wd:S",
                     "Dawnreach": "wt:reach/wp:bow", "Windlance": "wp:spear/wp:polearm"},
    ("elf", "arm"): {"Leafmail": "am:chain/am:composite", "Silkward": "am:cloth", "Starweave": "ac:light", "Moonmantle": "ac:light"},
    ("gnome", "wpn"): {"Pincherette": "wp:knife/wd:P", "Hookhammer": "wp:hammer/wp:pick", "Whirlwhack": "wd:B"},
    ("gnome", "arm"): {"Gizmo Vest": "ac:light", "Tinkerplate": "am:plate/am:composite", "Bubblecoat": "ac:light",
                       "Gearweave": "ac:light/am:chain"},
    ("halfling", "wpn"): {"Luckpoint": "wd:P", "Skewer": "wd:P", "Wee Pike": "wp:spear/wp:polearm", "Stout Pin": "wd:P"},
    ("halfling", "arm"): {"Cozy Coat": "ac:light", "Quilted Hearth": "am:cloth/ac:light", "Burrow Vest": "ac:light",
                          "Patchwork Cheer": "ac:light"},
    ("orc", "wpn"): {"Skullcleaver": "wd:S/wd:B", "Bonesplitter": "wd:S/wp:axe", "Warpike": "wp:spear/wp:polearm/wd:P",
                     "Gorefang": "wd:P/wd:S", "Stonefist": "wd:B", "Hardblow": "wd:B"},
    ("orc", "arm"): {"Warhide": "am:leather", "Scarplate": "am:plate/am:composite/ac:heavy", "Bonecoat": "ac:medium/ac:light",
                     "Ashmail": "am:chain/am:composite"},
}
for (_c, _part), _m in _NEEDS.items():
    _have = {x.strip() for x in _CU[_c][_part].splitlines()}
    assert all(k in _have for k in _m), (_c, _part, [k for k in _m if k not in _have])
    _CU[_c][_part] = "\n".join(f"{_t}|||{_m[_t]}" if _t in _m else _t for _t in (x.strip() for x in _CU[_c][_part].strip().splitlines()))
# neutral names for every culture, so a weapon or armor of any kind always has something that fits
_FREE = {
    ("kobold", "arm"): ["Arch Guard", "Plumb Guard"], ("ratfolk", "wpn"): ["Quietfang", "Unsigned Blade"],
    ("ratfolk", "arm"): ["Hushguard", "Quietguard", "Unremarked Armor"], ("grippli", "wpn"): ["Reedsong", "Slowwater"],
    ("grippli", "arm"): ["Poolguard", "Dampguard"], ("leshy", "wpn"): ["Greenwake", "Oldgrowth", "Deepseed"],
    ("leshy", "arm"): ["Rootguard"], ("mender", "wpn"): ["Mended Tool", "Careful Hand"], ("mender", "arm"): ["Fixguard", "Spare Shell"],
    ("awakened", "arm"): ["Nestguard", "Warmguard"], ("dwarf", "wpn"): ["Stonekeeper", "Oathmark"], ("dwarf", "arm"): ["Hallguard", "Clanguard"],
    ("elf", "arm"): ["Gladeguard", "Starguard"], ("gnome", "arm"): ["Tinkerguard", "Curious Armor"],
    ("halfling", "arm"): ["Hearthguard", "Burrowguard", "Cozy Armor"], ("orc", "wpn"): ["Tuskbrand"], ("orc", "arm"): ["Roarguard"],
}
for (_c, _part), _more_names in _FREE.items():
    _CU[_c][_part] = _CU[_c][_part].rstrip("\n") + "\n" + "\n".join(_more_names) + "\n"
for _key, _d in _CU.items():
    _label = CULTURE_INFO[_key]["label"]
    for _part, _text in _d.items():
        table(f"item.cu.{_key}.{_part}", f"{_label} style: {_part}", _text)
    table(f"item.name.{_key}", f"Item name patterns, {_label} style", CU_PATTERNS.replace("@C@", _key))


def culture_label(key):
    return CULTURE_INFO.get(key, {}).get("label", "")


# ============================================================ more variety for item histories
# Every table below is extended, not replaced, so your own edits to the older lines keep working. Sub-tables
# (item.maker.tail, item.workspace, item.near) multiply the combinations: a few dozen lines give hundreds of histories.
def _more(name, text):
    TABLES[name]["entries"] += [ln.strip() for ln in text.strip().splitlines() if ln.strip() and not ln.strip().startswith("#")]


table("item.maker.tail", "What is said about a maker (each line starts with who or whose)", """
who worked only at night
who never charged the same price twice
who signed nothing and trusted no one
who was better known for a feud than for the trade
who trained under three masters and listened to none
who only built things when it rained
who gave away half of what they made
who left town before the paint dried
who kept a ledger of every piece and never showed it to anyone
who was a little too proud of the work
whose hands shook except when working
whose apprentices all quit on the same day
who hummed the whole time and never repeated a tune
who was said to owe someone a great deal of money
whose shop burned twice and who rebuilt it both times
who preferred barter and refused coin
who built to order and never kept a spare
who worked from a cart and never stayed a season
whose work turns up in odd places
who claimed to have learned the craft from a dream
""")
table("item.workspace", "Where a maker worked (a kind of space)", """
a cramped workshop
a borrowed forge
an attic
a lean-to
a barn loft
the back of a wagon
a rented cellar
a scriptorium
a corner of a market stall
a tent
a shed behind a bakery
a boathouse|water
a loft above a stable
a chapel's side room|religion
a drafty tower room
a ropewalk
a quiet corner of a library
a tannery yard
a ferry house|water
a toll house|road
""")
table("item.near", "Where that space was", """
above {shop.name}
behind {tavern.name}
off {street}
at the edge of {settlement.name}
by the river|water
near a crossroads|road
beside a chapel|religion
under a bridge|water
within sight of the walls
far from anyone who might ask questions|crime mystery
next to a noisy mill
where the road bends|road
two doors from the watch house
""")

_more("item.who", """
{a ancestry.adj} {occupation} {item.maker.tail}|k:npc|6
{npc.named}, {item.maker.tail}|k:npc|4
a workshop collective of {pl occupation}|k:group pl|3
a family of {pl occupation} who passed the craft down for generations|family k:group pl|3
a pair of rival {pl occupation} who each took the credit|k:group pl|2
a crew of {pl occupation} working under a single seal|k:group pl|2
{a occupation} and their three apprentices|craft k:group pl|2
{a occupation} who was paid in advance and delivered late|trade k:npc|2
{a occupation} who worked for the {name.adj} {name.collective}|k:npc|2
a veteran {occupation} on their last commission before retiring|k:npc|3
a young {occupation} making a name for themselves|k:npc|3
{a occupation} from a long line of {pl occupation}|family k:npc|2
a pilgrim who learned the craft on the road|religion road k:npc|2
a prisoner who made it in the yard and talked a guard into carrying it out|crime k:npc|1
an orphan taught by a patient {occupation}|family k:npc|2
the town's only {occupation}, who was asked to make everything|k:npc|3
a retired {occupation} who could not stop tinkering|k:npc|3
a retired soldier with an unexpected talent|military k:npc|2
{faction.generic}'s own workshop|k:faction|2
a bored noble with a lathe and too much free time|politics k:npc|2
a hermit who rarely spoke and never explained|nature k:npc|2
a stranger whose name nobody asked|mystery k:npc|2
an unlicensed apprentice working in a master's off hours|craft crime k:npc|2
""")
_more("item.where", """
in {item.workspace} {item.near}||6
in the back room of a pawnshop|crime trade
in a cell at a monastery|religion
inside a hollowed wagon wheel|road
in a smithy that has since become a bakery|craft
in the loft of a granary|nature
at a toll gate in the middle of nowhere|road
in a vineyard cellar|nature
in a theater's prop room|festival
on a barge tied up for the winter|water
in a lighthouse keeper's cottage|water
in a shuttered inn|trade
at a leper house that has long since closed|disease religion
in a guild hall's cold storage|trade politics
at a mill that stopped turning|nature
at a battlefield camp|military
in a hedge witch's cottage|magic nature
in a cave mouth shielded from the wind
in a clock tower|craft
in the sacristy of a half-built church|religion
at a fair that came through only once|festival
""")
_more("item.when", """
{n:2-9} winters ago
in the third year of a long drought|weather
the summer the bridge fell
just after the old mayor died|politics
back when {settlement.name} still had walls|military
in a leap year nobody remembers
within living memory, though only just
a few years before the last war|military
three owners and one flood ago
in the final days of {settlement.name}'s market charter|trade politics
at the end of the great fairs|festival
when the road tolls doubled|road trade
during the long quiet after the siege|military
in a lean spring
the year the river froze|weather water
in the reign of a queen who is now only a street name|politics
before the bells were hung|religion
twelve harvests back|nature
on the night the old tavern burned
in the same year as a very bad winter and a very good wedding
in the last good summer before the plague|disease
when {settlement.name} was still a crossroads
""")
_more("item.why", """
to prove a point to a teacher who never believed in them
because a customer would not stop asking
to settle a wager about whether it could be done
because the old one wore out and nobody else could repair it
to apologize to someone who would not listen
as a joke that got out of hand
because a dying relative asked for something to remember them by
because the maker had a vision and no one to tell
to pay off a long stay at an inn
because the maker misread the commission and made something better
to replace one that was stolen
because a rival bragged about theirs
to give a friend something to hold during a long trip
because the maker could not sleep and could not stop working
so that something would outlast the maker
because a plague emptied the town and left the materials behind
to finish what the maker's mentor began
because an officer promised a post and never delivered
to win favor with a patron who kept changing their mind
as a retirement gift the maker made for themselves
because a stranger left a deposit and never returned
as a trade for passage on a boat that was already full
to test a method the maker was not supposed to use
because a child asked for it and the maker could not say no
out of spite, mostly
because a festival needed a prize and no one else had one
because the maker owed a favor to the wrong person
so the maker's apprentice would have something to inherit
because the maker found the materials and could not leave them alone
to keep a promise made while very drunk
to hide a debt from a spouse
to see if the old stories about the craft were true
""")
_more("item.what", """
to be given away at a wedding
to make a bad day slightly better
to serve a household for a generation
to be a prize at a harvest fair
to thank a neighbor who never asked for thanks
to carry out one very specific job, and then be forgotten
to settle who owned a field|politics family
to survive being dropped
to be passed from parent to child
to be loaned out and never returned
as a test of a new technique
as a display piece for a guild hall|craft trade
for a bride's dowry|family
to be left at a shrine as an offering|religion
to be hidden at the bottom of a chest
to hold a bridge against a larger force||3|it:weapon
to settle a duel over a very small insult||3|it:weapon
to be carried by a watch sergeant who never once drew it||2|it:weapon
to see a nervous recruit through a first winter on the wall||3|it:armor
to keep a city gate guard alive through one more riot||3|it:armor
to be worn to a wedding the wearer was not invited to||2|it:worn
to make a long watch feel shorter||3|fx:senses
to keep a forge hot through a bitter winter||3|fx:fire
to clear a cellar of vermin without burning down the house||2|fx:fire/fx:acid
to keep a cold cellar cold through the summer||3|fx:cold
to lay restless dead to rest||3|fx:undead
to answer an old curse||3|fx:holy/fx:unholy
to track a wounded creature through bad country||3|fx:bleed
to end a standoff without a fight||3|fx:fear
to call workers in from the far fields||3|fx:sonic
to etch a mark no one could forge||2|fx:acid
to settle a storm for a nervous sailor||2|fx:electricity
""")
table("item.incident", "A notable incident (a story people tell about it)", """
It once saved its owner from a thrown bottle and a worse reputation.
It was blamed for a fire it did not start.
It won a wager in the last hour of a festival.
It was used as evidence in a trial, and the trial never ended.
It was nearly sold to pay for a funeral, and then it was not.
It survived a flood in a locked chest while everything around it rotted.
It was held up as a prize at a fair and went unclaimed for three years.
It changed hands four times in a single night.
It was once mistaken for a common one and used to prop open a door.
It was carried across a mountain pass by someone who did not know what it was.
It was lost during a feast and found in the soup.
It was left on a doorstep with a note that said only that the sender was sorry.
It was blamed for a string of bad luck that turned out to be a coincidence.
It was used to settle a boundary dispute between two farms.
It is said to have saved a life, though no one agrees whose.
It was hidden during an inspection and forgotten for a decade.
It was part of a dowry that was disputed for years.
It was stolen, returned, and stolen again by the same thief.
It once made a tavern go silent for a full minute.
It was borrowed for a play and never returned to the stage.
It sat in a shop window for a season and drew more attention than the shop deserved.
It was involved in a small scandal that is still told at weddings.
It was carried by a courier who was never seen again, though it turned up later.
It was cursed by a rival, according to the rival, and the curse had no effect.
It was repaired by a stranger who refused payment and left before the work could be inspected.
""")
table("item.state", "Its condition now", """
It is in good order, apart from a small chip its owner refuses to fix.
It has been repaired twice, once badly.
It is cleaner than it has any right to be.
It has scratched initials on it, and nobody knows whose.
It is worn smooth where hands have held it most.
Its original finish has long since worn off, and a better one was never applied.
It has been polished so often that its details have blurred.
It smells of its last owner's pipe, even after a thorough airing.
It has been carried in a sack so long it has taken the shape of one.
It has survived much worse than its current owner will ever put it through.
It has a mended place that is stronger than the rest.
A previous owner glued a small charm to it.
It looks newer than its age, and it is hard to say why.
It is missing a small piece that does not seem to matter, until it does.
It has been wrapped in cloth so long the cloth has stuck to it.
Its decoration is mostly gone, and what remains is an acquired taste.
""")


# ---- more Hallowmead lines (content pack hallowmead). Only places and factions from the setting bible are named, and
#      nothing here states new history as fact. The Magic Items tab's "Setting flavor" slider limits how often they appear.
_HM_MORE = {
    "item.who": """
a Finders Keep salvager who rebuilt it from three broken things|craft treasure k:npc mk:goblin|3
a goblin tinker from Finders Keep with a reputation for overselling|trade craft k:npc mk:goblin|2
a Finders Keep crew that sorts the refuse chutes and kept the best piece|treasure k:group pl mk:goblin|2
a kobold mason who built it between arches|craft k:npc mk:kobold|2
an apprentice mason of the Grand Underhall working off a debt|craft k:npc mk:kobold|2
a Hushwarrens courier who made it to fill the hours between runs|crime mystery k:npc mk:ratfolk|2
a ratfolk of the Hushwarrens who sold it unsigned|crime mystery trade k:npc mk:ratfolk|3
a grippli water-shaper of Stillwater Hollow who built it to match the current|nature k:npc mk:grippli|2
a grippli craftsperson who traded it for fresh reeds|nature trade k:npc mk:grippli|2
a leshy of the Quiet Ring who grew the frame and shaped the rest|nature k:npc mk:leshy|2
a leshy herbalist who made it for a neighbor and never mentioned it|nature family k:npc mk:leshy|1
a Mending repairer who has fixed it more times than anyone has used it|craft family k:npc mk:mender|3
a Mending apprentice making it as a first project|craft k:npc mk:mender|2
a poppet seamstress of the Mending|craft family k:npc mk:mender|2
an awakened animal of Firstlight who worked it out by trial and error|nature t:light k:npc mk:awakened|2
a Crossings stallholder who commissioned it and then claimed to have made it|trade k:npc|2
a surface artisan from Hallowmead whose rejected work was thrown down the chutes|craft politics k:npc|2
""",
    "item.where": """
in a salvage stall on the sorting floor of Finders Keep|craft treasure|3
under a half-built arch at the Grand Underhall|craft|2
in a stone-cutters' lean-to at the Grand Underhall|craft|2
in a corridor of the Hushwarrens where the lamps are kept low|crime mystery|3
in a room off the Hushwarrens where no one asks what is being made|crime mystery|2
on a stilt platform above the slow water of Stillwater Hollow|nature|3
in a reed hut at Stillwater Hollow|nature|2
in a root-ringed chamber of the Quiet Ring|nature|3
in a quiet clearing between the roots of the Quiet Ring|nature|2
in a cramped Mending workshop full of half-repaired tools|craft family|3
in a Mending storeroom stacked with tools waiting for owners|craft family|2
in a hollow beside the glowing teal pools of Firstlight|magic nature|3
in a burrow workshop at Firstlight|nature|2
at a stall in the Crossings, in the shadow of the crystal spire|trade festival|3
at a corner of the Crossings where traders swap what they cannot sell|trade|2
in a service passage under the Crossings|crime trade|2
at the mouth of a refuse chute below Hallowmead|treasure|2
in an unmarked side tunnel between two settlements|crime mystery|2
in a cave pocket that someone turned into a workroom|craft|2
""",
    "item.when": """
in a season when the lamp oil ran short|craft trade|2
back when the Crossings fair was smaller|trade festival|2
a few collapses ago|craft|2
in a year nobody wrote down|mystery|2
when the chutes ran fuller|treasure|2
before the last tunnel was repaired|craft|2
in a quiet winter the surface does not remember|weather|2
shortly after a new stall opened at the Crossings|trade|1
in the days when each settlement still guarded its own shortcuts|crime politics|2
during a feud over a shortcut|politics|2
""",
    "item.why": """
because a surface family threw out something the maker thought could be made good|treasure|3
because a repair was cheaper than a replacement|craft|3
to say thank you to someone who shared lamp oil during a bad winter|trade family|2
because the maker wanted proof that the Underhallow could make things as fine as the surface|craft politics|3
to settle a debt owed to a settlement that remembers every debt|politics trade|2
because someone promised to buy it and then moved to another settlement|trade|2
because a neighbor's child asked and the maker could not say no|family|2
to keep a message safe on its way between settlements|crime mystery|2
as a quiet bribe for a gatekeeper|crime politics|2
because a repaired thing is worth more than a new one, according to the maker|craft|2
""",
    "item.what": """
to make the long walk between settlements a little less lonely||3|fx:travel
to carry coin through a crowded market without being noticed||3|fx:stealth
to settle a dispute at the Crossings without a fight||3|fx:social
to read the room before a trade was agreed||3|fx:senses/fx:knowledge
to light a dark junction for travelers||3|fx:light
to keep goods dry through a flooded passage||2|fx:control/fx:protection
""",
    "item.found": """
It was returned by a ratfolk courier who swore it had been found in a stranger's coat.|crime mystery|2
It was bought at the Crossings from a seller who could not name the maker.|trade|3
It was pulled out of a water channel near Stillwater Hollow after a tunnel flooded.|nature|2
It was traded for a sack of lamp oil at a Finders Keep stall.|treasure trade|2
""",
    "item.owner": """
a ratfolk courier who carried it for years and never admitted what it was|crime mystery|2
a Crossings trader who sold it three times and bought it back twice|trade|2
""",
    "item.incident": """
It was once left on a Crossings counter overnight and no one dared touch it.|trade mystery|2
It was lost in a tunnel collapse and recovered a season later, none the worse.|craft|2
It was auctioned off at the Crossings and bought back by the person who sold it.|trade|2
It was the only thing in a flooded passage that stayed dry, to the annoyance of everyone nearby.|nature|1
""",
}
for _name, _lines in _HM_MORE.items():
    HALLOWMEAD.setdefault(_name, {"title": _name, "entries": []})["entries"] += [
        ln for ln in _pack(_lines).splitlines() if ln.strip()]


# ============================================================ name logic: names that fit the item
# A name can draw on four things the item already has, so it never contradicts it:
#   what it does   (item.name.fx.<slot>.<effect>, from the item's effect tags, including its runes)
#   what it was made for   (item.name.purpose.<key>, from the history's "Made for" line)
#   where it was made      (a named place in the history: PLACE_WORDS, or a place from your Notebook)
#   a notable owner        (a named person in the history)
# It never draws on the secret or the false tale, so a name can't give either away.

# What each rune implies, so a flaming sword is named like a flaming sword and a shadow armor like a shadow armor.
RUNE_FX = {
    "returning": ["fx:travel"], "ghost touch": ["fx:undead"], "disrupting": ["fx:undead", "fx:holy"], "fearsome": ["fx:fear"],
    "wounding": ["fx:bleed"], "flaming": ["fx:fire"], "frost": ["fx:cold"], "shock": ["fx:electricity"], "corrosive": ["fx:acid"],
    "thundering": ["fx:sonic"], "grievous": ["fx:war"], "holy": ["fx:holy"], "unholy": ["fx:unholy"],
    "brilliant": ["fx:fire", "fx:light"], "keen": ["fx:war"], "dancing": ["fx:magic"],
    "glamered": ["fx:stealth", "fx:social"], "shadow": ["fx:stealth"], "slick": ["fx:travel"], "greater slick": ["fx:travel"],
    "major slick": ["fx:travel"], "ready": ["fx:war"], "acid-resistant": ["fx:acid"], "cold-resistant": ["fx:cold"],
    "electricity-resistant": ["fx:electricity"], "fire-resistant": ["fx:fire"], "greater fire-resistant": ["fx:fire"],
    "greater cold-resistant": ["fx:cold"], "invisibility": ["fx:stealth"], "fortification": ["fx:protection"],
}
for _r in WEAPON_RUNES + ARMOR_RUNES:
    _r["fx"] = list(RUNE_FX.get(_r["name"], []))
BASE_FX = {"weapon": ["fx:war"], "armor": ["fx:protection"]}      # what any runic weapon or armor does at heart

# words for what an item does. Slots: thing (reads after "of": Cloak of Quiet Doors), wpn (a weapon's own name), arm (an armor's)
FX_NAME_WORDS = {
    "thing": {
        "stealth": "Quiet Doors|Soft Footfalls|Closed Mouths|Unlit Alleys|the Unremarked|Muffled Bells|Turned Backs",
        "travel": "the Long Road|Short Cuts|Many Miles|Sure Footing|the Open Gate|Fair Winds|Narrow Ledges",
        "war": "Hard Knocks|Steady Hands|Rough Company|Standing Ground|Close Quarters|Cold Steel",
        "protection": "Bolted Doors|Warm Hearths|Safe Harbor|Thick Walls|Held Lines|Shut Gates",
        "healing": "Gentle Hands|Clean Bandages|Warm Broth|Strong Tonic|Slow Recovery|Patient Beds",
        "knowledge": "Hidden Letters|Old Maps|Small Print|Overheard Things|Quiet Questions|Cross-Checked Facts",
        "social": "Easy Welcomes|Warm Introductions|Smooth Talk|Good Terms|Open Palms|Kind Words",
        "craft": "Steady Benches|Clean Joins|Patient Making|True Edges|Well-Made Things|Sharp Tools",
        "light": "Small Dawns|Lit Corners|Borrowed Daylight|Steady Flames|Open Shutters|Lantern Hours|Bright Windows",
        "control": "Held Breath|Gentle Leashes|Tied Knots|Quiet Orders|Slow Hands|Fast Locks",
        "magic": "Borrowed Words|Folded Spells|Small Miracles|Careful Wording|Tidy Magic|Old Tricks",
        "senses": "Sharp Eyes|Night Watches|Long Sight|Keen Evenings|Quiet Ears|Open Eyes",
        "fire": "Banked Coals|Warm Hands|Quick Kindling|Last Embers|Hearth Smoke|Hot Iron",
    },
    "wpn": {
        "war": "Last Argument|Fair Fight|Closer|Persuader|Old Reliable|Straight Talk|Final Opinion|Harsh Teacher|Short Temper",
        "fire": "Cinderbite|Hearthbrand|Emberwake|Kindler|Smolder|Hotfoot|Candlebane|Forgeheart",
        "cold": "Rimefang|Frostwake|Coldcomfort|Winterbite|Icepick|Chillblain|Hoarbrand",
        "electricity": "Forkflash|Spark-Tongue|Tingler|Cloudsplitter|Thunderhead|Live Wire",
        "acid": "Acid Tongue|Sourbite|Pitting|Vitriol|Rustcall|Tarnisher",
        "sonic": "Clamor|Ringer|Bellmaker|Hush-Breaker|Gong|Rattlewake",
        "undead": "Gravemender|Lay-to-Rest|Unquiet|Barrow-Bane|Quieter|Wake-Keeper",
        "holy": "Mercy|Kindly Light|Redeemer|Benediction|Lantern-Bearer|Daybreak",
        "unholy": "Vespers|Penance|Hollow Verse|Dirge|Ill Tidings|Last Rites",
        "bleed": "Red Thread|Seamstress|Thin Red Line|Leech|Scarlet Whisper|Trail-Maker",
        "fear": "Dread|Cold Shoulder|Glare|Scarecrow|Showdown|Bogey",
        "travel": "Homing|Fetch|Comes-Home|Faithful Hound|Swallow|Return Visit",
        "magic": "Dancer|Waltz|Puppeteer|Second Hand|Free Spirit",
        "light": "Lantern-Blade|Noon|Daystar|Bright Idea|Candlemaker",
    },
    "arm": {
        "protection": "Bulwark|Last Wall|Hearthward|Safe Harbor|Shut Door|Stubborn Hide|Winter Coat|Held Line",
        "stealth": "Hushmail|Quiet Wrap|Shadowfold|Dusk Hide|Moth|Dim Hours|Soft Step",
        "travel": "Eel-Skin|Slipshell|Greasewalker|Squeeze-Through|Wriggler|Slip-Knot",
        "war": "Quickhide|Quick-Don|Ready Coat|Alarm Bell|Fast Friend|Short Notice",
        "fire": "Emberward|Hearth-Hide|Cinder-Coat|Fireproof Pride|Kettle-Skin",
        "cold": "Winter-Warm|Frostward|Cold-Shoulder|Furnace Coat|Thaw",
        "electricity": "Rodmail|Groundwire|Stormward|Spark-Catcher|Earthed",
        "acid": "Rustproof|Acid-Proof|Etch-Resist|Tanned Tough|Sour Skin",
        "social": "Sunday Best|Costume|Plain Clothes|Courtier's Disguise|Fine Print",
    },
}
# the slot for each kind of item
FX_NAME_SLOT = {"worn": "thing", "held": "thing", "wand": "thing", "scroll": "thing", "potion": "thing", "device": "thing",
                "weapon": "wpn", "armor": "arm"}
for _slot, _by in FX_NAME_WORDS.items():
    for _tag, _words in _by.items():
        table(f"item.name.fx.{_slot}.{_tag}", f"Names for what it does ({_slot}, {_tag})", _words.replace("|", "\n"))

# What an item was made for, found in the history's "Made for" line. Each rule is (pattern, key); keys have word tables.
PURPOSE_RULES = [
    (r"thieves|rooftops", "thief"), (r"smuggler", "smuggler"), (r"caravan|passes in bad weather", "road"),
    (r"long walk between settlements", "road"), (r"soldier|long campaign", "soldier"), (r"healer|patients", "healer"),
    (r"liars|magistrate", "magistrate"), (r"miner|lightless", "miner"), (r"ward intact", "warden"),
    (r"watch sergeant|long watch|watch feel shorter", "warden"), (r"craftsperson|lesser hands", "craft"),
    (r"calm a crowd|riot\b", "crowd"), (r"flood|keep goods dry", "flood"), (r"student", "student"),
    (r"fog, a lie|read the room", "watcher"), (r"\bduel\b", "duelist"), (r"mountain pass", "pass"),
    (r"tunnel crew|failing tunnel|repair crew", "tunnel"), (r"salvage", "salvage"), (r"word between settlements", "courier"),
    (r"sluice", "sluice"), (r"repairer", "repair"), (r"keepsake", "keepsake"), (r"gift for an apprentice", "apprentice"),
    (r"sold at a fair|harvest fair", "fair"), (r"bad winter", "winter"), (r"quarrel between two guilds|guild hall|dispute at the crossings", "guild"),
    (r"given away at a wedding|bride's dowry|wedding the wearer", "wedding"), (r"household for a generation", "household"),
    (r"passed from parent to child", "heirloom"), (r"who owned a field", "boundary"), (r"offering", "shrine"),
    (r"thank a neighbor", "neighbor"), (r"hold a bridge", "bridge"), (r"recruit through a first winter", "recruit"),
    (r"city gate guard", "gate"), (r"forge hot", "forge"), (r"vermin", "vermin"), (r"cold cellar", "cellar"),
    (r"restless dead", "grave"), (r"old curse", "curse"), (r"wounded creature", "tracker"), (r"standoff", "standoff"),
    (r"far fields", "bell"), (r"etch a mark", "etcher"), (r"storm for a nervous sailor", "storm"),
    (r"coin through a crowded market", "market"), (r"dark junction", "lamp"),
]
PURPOSE_WORDS = {
    "thief": "Rooftop|Cutpurse's|Lightfoot|Nightwalker's|Gutter", "smuggler": "Smuggler's|Contraband|Back-Door|Customs-Dodger's",
    "road": "Caravan|Wayfarer's|Pass-Crosser's|Drover's|Long-Walk", "soldier": "Soldier's|Campaigner's|Veteran's|Sergeant's",
    "healer": "Healer's|Bedside|Night-Nurse's|Bandage-Roll", "magistrate": "Magistrate's|Truth-Teller's|Clerk's|Straight-Dealing",
    "miner": "Miner's|Deep-Shift|Pit-Boss's|Lampless", "warden": "Warden's|Night-Watch|Ward-Keeper's|Vigil|Short-Watch",
    "craft": "Craftsman's|Bench|Journeyman's|Master's", "crowd": "Crowd-Calmer's|Rabble|Rally|Town-Square",
    "flood": "Floodgate|Firebreak|Rumor-Stopper's|Waterproof", "student": "Student's|Lesson|Primer|Schoolroom",
    "watcher": "Watcher's|Fog-Piercer's|Truthseer's|Room-Reader's", "duelist": "Duelist's|Margin|Honor-Bound|Point-of-Honor",
    "pass": "Pass-Keeper's|Winter-Road|Gap|High-Road", "tunnel": "Tunnel-Crew's|Collapse|Prop-Setter's|Shaft",
    "salvage": "Salvager's|Scavenger's|Sorting-Floor|Refuse-Chute", "courier": "Courier's|Runner's|Sealed-Letter|Go-Between",
    "sluice": "Sluice-Keeper's|Flood-Watch|Lowwater|Gate-Tender's", "repair": "Mender's|Fixer's|Second-Wind|Patch-Job",
    "keepsake": "Keepsake|Pocket-Worn|Memento|Trinket", "apprentice": "Apprentice's|First-Day|Learner's|Gift-Day",
    "fair": "Fairground|Barker's|Fair-Day|Prize", "winter": "Winter-Season|Hard-Winter|Lean-Year|Bad-Season",
    "guild": "Guild-Peace|Arbiter's|Compromise|Peacemaker's", "wedding": "Wedding|Dowry|Bridal|Betrothal",
    "household": "Household|Hearthside|Homestead|Kitchen", "heirloom": "Heirloom|Inherited|Hand-Me-Down|Old-Line",
    "boundary": "Boundary|Field-Line|Deed-Keeper's|Hedgerow", "shrine": "Shrine|Votive|Offering|Pilgrim's",
    "neighbor": "Neighbor's|Thank-You|Fence-Line|Doorstep", "bridge": "Bridge-Holder's|Narrow-Pass|Chokepoint|Last-Stand",
    "recruit": "Recruit's|First-Winter|Wall-Watch|Greenhorn's", "gate": "Gatekeeper's|Riot-Season|Gate-Watch|Turnstile",
    "forge": "Forge|Bellows|Hearth-Keeper's|Anvil-Side", "vermin": "Ratcatcher's|Cellar-Cat|Pest-Control|Rat-Run",
    "cellar": "Cellar|Icehouse|Cold-Store|Larder", "grave": "Gravedigger's|Wake-Night|Barrow-Watch|Churchyard",
    "curse": "Curse-Breaker's|Old-Debt|Vow|Undoing", "tracker": "Tracker's|Hunter's|Wounded-Trail|Blood-Trail",
    "standoff": "Standoff|Bluff|Face-Off|Cool-Head", "bell": "Bellringer's|Call-Up|Long-Field|Harvest-Call",
    "etcher": "Etcher's|Sealmaker's|Mark-Maker's|Engraver's", "storm": "Stormwatch|Lightning-Rod|Weathervane|Sailor's",
    "market": "Market-Day|Stallholder's|Crowded-Aisle|Coin-Purse", "lamp": "Lamplighter's|Junction|Waystation|Crossroads",
}
for _key, _words in PURPOSE_WORDS.items():
    table(f"item.name.purpose.{_key}", f"Names for what it was made for ({_key})", _words.replace("|", "\n"))
# "to help a cartwright do their work" names the trade: Cartwright's Cloak
OCCUPATION_PURPOSE = r"to help (?:an? )?([a-z][a-z' -]*?) do their work"

# Named places in a history (lowercase text to find, how the name reads). The Mending is left out on purpose: "Mending
# Cloak" would read as a cloak that mends.
PLACE_WORDS = [("finders keep", "Finders Keep"), ("grand underhall", "Underhall"), ("underhall", "Underhall"),
               ("hushwarrens", "Hushwarrens"), ("stillwater", "Stillwater"), ("quiet ring", "Quiet Ring"),
               ("firstlight", "Firstlight"), ("crossings", "Crossings"), ("hallowmead", "Hallowmead")]

# story themes the new effect tags lean toward (so a frost weapon's history leans toward weather, a holy one toward religion)
FX_THEMES.update({"fx:cold": ["weather"], "fx:electricity": ["weather"], "fx:acid": ["craft"], "fx:sonic": ["festival"],
                  "fx:undead": ["undead"], "fx:holy": ["religion"], "fx:unholy": ["religion", "undead"],
                  "fx:bleed": ["crime", "monster"], "fx:fear": ["military", "mystery"]})


# ============================================================ GM Tools: weird wares, peddlers and salvage
# The wording for loot.py's weird wares, peddler carts and salvage piles. Not item generator tables: they only feed the GM Tools tab.
table("item.container", "Containers (for weird wares)", """
box
jar
hat
drawer
bucket
sock
mailbox
tin
pocket
lunchbox
teapot|||s2
boot|||s2
filing cabinet||2|s3
""")

table("item.weapon", "Weapons (for inverted wares)", """
greataxe
longsword
shortbow
mace
spear
dagger
war hammer
club
whip
sling
halberd
frying pan|||s2
ladle|||s2
walking stick|||s2
""")

table("item.prefix", "Name prefixes", """
Great
Grand
Well-Meaning
Remarkable
Most Reliable
Proudly Mundane|||s2
Practically Legendary|||s2
Unreasonably Honest||2|s3
""")

table("item.tool", "Everyday tools", """
lantern
rope
bell
bag
hat
cloak
shield
boots
gloves
ladle
teapot
candle
spoon
comb
""")

table("item.condition", "Overly specific conditions", """
on a Tuesday|pl:Tuesdays
while standing on a barrel|pl:Barrel_Standing
while holding a cheese|pl:Cheese_Holding
within sight of a goat|pl:Goat_Watching
while someone nearby is humming|pl:Humming_Nearby
against creatures wearing a hat|pl:Hat_Hunting
underground|pl:the_Underground
when nobody is watching|pl:Not_Being_Watched
while you are wearing mismatched socks|pl:Mismatched_Socks||s2
against anyone named Greg|pl:Specifically_Greg|2|s3
while it is being very quietly insulted|pl:Quiet_Insults|2|s3
""")

table("item.reset", "Reset conditions", """
at dawn
when it is thanked sincerely
when you apologize to it
when it is buried overnight
when someone new says hello to it|||s2
never, and it seems to like that||2|s3
""")

table("item.side", "Potion side effects", """
your skin turns {color} for {#2-8} hours
you hiccup small bubbles for the next hour
everything you say sounds like a question for an hour
you smell strongly of pie until you sleep
your hair stands straight up for {#2-8} hours
your shadow arrives a few seconds late
you cannot stop humming a tune nobody knows|||s2
you speak in rhyme for {#1-4} hours|||s2
small birds follow you for the rest of the day|||s2
your left foot develops opinions||2|s3
every door you pass politely holds itself open, then slams||2|s3
""")

table("color", "Colors", """
green
violet
orange
sky blue
a faint, dignified gold
the exact color of a nearby wall
""")

table("item.pitch", "Peddler patter", """
"Never been used, apart from the times I have used it. You can ask the goat."
"No refunds. I will not be told it is working, I will be told it is thriving."
"I have one. I had two. Do not ask about the other one."
"A steal, if you are a thief, and a bargain, if you are not."
"It does exactly what it says on the tin, and the tin is lying."
"It has never failed me. Mind, I have used it twice."
"A previous owner loved it dearly. A later owner was less fond. Do not ask about the middle one."
"Warranty void upon sight."
"Fifty-fifty, mostly in my favor."
"You will want it, and then you will want a different one."
"I had a customer buy three. I think that tells you everything, or nothing."
""")

table("item.price.extra", "Price extras", """
or two good stories
and a favorite spoon
and a promise
or a decent hat|||s2
plus tax, in cheese|||s2
and the right to feel smug|||s2
and your word that you did not see it||2|s3
""")

table("peddler.cart", "Peddler carts", """
a cart with one wheel, expertly balanced
a wheelbarrow with a velvet lining
a very long coat with many pockets
a stall that is also, apparently, a tent
a mule, a bag, and a great deal of confidence
a cart pulled by a goat who has no obvious loyalty|||s2
a wagon that appears to be a bit larger on the inside||2|s3
""")

table("peddler.name.gnome", "Peddler names", """
Fizzwick the Honest
Pim Brassbuckle, Purveyor of Mostly Things
Dazzel Fumblewick
Quibbins, Merchant of the Not-Quite-Cursed
Tink Sparklesnout, Peddler Extraordinary
Wibble Nimbwit, Dealer in Wares
""")

table("salvage.junk", "Salvage: junk", """
a single boot, still warm
a bag of mismatched buttons
forty-one identical bolts
a rolled-up carpet with something in it, probably a rug
a bent spoon
a bucket with a hole, patched with a smaller bucket
a perfectly good hinge
three hundred feet of tangled twine
a chunk of broken lantern glass
a pile of unreadable receipts
a hat that is mostly brim
a left glove, and a right glove from a different pair|||s2
a mop that has seen things|||s2
a tin of nails, labeled SOUP|||s2
a clock with seven hands||2|s3
a box of unlabeled screws, all of them left-handed||2|s3
""")

table("salvage.useful", "Salvage: useful parts", """
a length of good rope|pl:rope
a coil of copper wire|pl:metal
a bag of brass gears|pl:gears
a stack of seasoned planks|pl:wood
a bolt of decent cloth|pl:cloth
a roll of oiled leather|pl:leather
a crate of salvageable pipe|pl:metal
a handful of clean lantern glass|pl:glass
a drum of lamp oil|pl:oil
a sack of good nails|pl:metal
a pair of working pulleys|pl:gears
a barrel of dry mortar|pl:stone
a tangle of fishing line that works|||s2
a surprisingly good ladder|||s2
a goblin-made tool that is secretly well made|||s2
""")

table("salvage.valuable", "Salvage: valuables", """
a candlestick of mostly real silver
a spoon with a gem in the handle
an old coin, rare to the right collector
a small brass statue of a very smug cat
a bracelet with a few honest stones
a signet ring from a family that has ended
a music box that plays half a tune
a set of surgeon's tools, extremely clean
a carved bone comb, nicely made
a gilded frame with a portrait of someone's goat|||s2
a gold tooth, extra large|||s2
a medal for something quite impressive that nobody remembers|||s2
a tiny crown, for a very small ruler||2|s3
""")

table("salvage.where", "Salvage places", """
a collapsed mine office|p:hallowmead
a goblin midden heap|p:hallowmead
a derelict mine cart|p:hallowmead
an abandoned lamp-lighters' stair|p:hallowmead
the bottom of a flooded cistern|p:hallowmead
a kobold storage alcove|p:hallowmead
the Crossings salvage yard, after hours|p:hallowmead
an old dwarven pump house|p:hallowmead
a collapsed cellar||||hm
a burnt-out wagon||||hm
the back room of an abandoned shop||||hm
a roadside ditch||||hm
a dockside warehouse after a flood||||hm
a half-buried shed||||hm
""")


# ============================================================ item styles: Standard, Grim, Whimsical, Ridiculous
# The Magic Items tab and the NPC Generator have a Style setting. Standard is the generator as it always was. The other three
# add parts to an item, rolled from the tables below:
#   Grim         a drawback with a real cost (item.style.cost.grim; item.style.after.grim for consumables). Numbers stay
#                on the GM Core curve.
#   Whimsical    an odd extra ability (item.style.oddity) and a mild drawback (item.style.cost.whimsy). Roughly balanced.
#   Ridiculous   an absurd ability (item.style.absurd), a severe limit on it (item.style.limit), and a severe drawback
#                (item.style.cost.severe). Off the curve on purpose: the limit and the drawback are what pay for it.
# Lines can use {@lvl} (the item's level), {@dc} (the item's DC from the Magic Item DC table), and {@gp} (a small sum in gp
# for its level). None of these are book rules; they are tuning for this tool.
table("item.style.cost.grim", "Grim drawbacks (a real cost; numbers stay on the curve)", """
Each activation draws blood: you take {@lvl} damage, which can't be reduced or prevented in any way.|t:grim
After you use it, you are drained 1 until your next daily preparations. Using it again while drained raises the value by 1.|t:grim
Every use costs a memory. You forget one name you knew, and the GM chooses which.|t:grim
It feeds on fear. You are frightened 1 for 1 round after each activation, and the condition can't be reduced below 1 during that round.|t:grim
Each night it asks for a drop of your blood. If you refuse, you are fatigued the next day.|t:grim
Animals within 30 feet go quiet and still around it. You take a -2 circumstance penalty to checks to handle or calm animals.|t:grim
Undead and haunts can sense it from 100 feet away, and they come to see what it is.|t:grim undead
While it is invested, the first time each day you would regain Hit Points from a spell, you regain {@lvl} fewer.|t:grim
Using it chills the air. Plants within 10 feet wither, and anyone who sees that remembers your face.|t:grim
Each activation leaves a small burn on your palm. The burns are slowly spelling out a name, and its owner wants the item back.|t:grim
When you critically fail a check while carrying it, you are also doomed 1 until your next daily preparations.|t:grim
It hungers. If it isn't used in a fight at least once a week, you wake sickened 1 each morning until it is.|t:grim
Using it draws the attention of whatever it was made to fight, and that thing has started looking for you.|t:grim
Its power came from a death. Once a month you dream that death, and wake fatigued.|t:grim
Your shadow lags half a second behind you while you carry it. Anyone who notices treats you with suspicion.|t:grim
Each time you activate it, someone you love feels a sudden cold and knows that you did.|t:grim family
It doesn't work within 10 feet of a holy symbol, and a holy symbol carried near it slowly tarnishes.|t:grim religion
Using it takes a little warmth from the nearest living creature other than you, which feels it and turns to look.|t:grim
While it is invested, you can't benefit from a fortune effect on saves against fear.|t:grim
It will not let go. Putting it down or removing it takes 1 more action than usual, and it is always found back in your pack by morning.|t:grim
""")
table("item.style.after.grim", "Grim aftereffects (for consumables)", """
For 10 minutes after you use it, you are sickened 1.|t:grim
Using it costs you {@lvl} Hit Points that come back only after a full night's rest.|t:grim
It leaves a black stain on your hands that won't wash off for a week, and people who know what it means will ask.|t:grim
For 1 minute after you use it, you can't regain Hit Points from magic.|t:grim
For an hour afterward, you hear the last words of anyone who died within 30 feet in the past day.|t:grim undead
You are fatigued until your next full rest.|t:grim
For a day afterward, everything you eat tastes of ash.|t:grim
Your reflection is a few seconds late for the next hour.|t:grim
""")
table("item.style.oddity", "Whimsical oddities (an odd extra ability, roughly balanced)", """
Activate [1 action] (manipulate); Frequency once per hour; Effect It plays a short fanfare. Allies within 30 feet who hear it gain a +1 status bonus to their next initiative roll within the next minute.|t:light nw:Tiny_Fanfares
It can recite, word for word, the last thing said within 10 feet of it. It does this once a day, usually at an awkward moment.|t:light nw:Repeated_Words
It always knows the time to the minute, and will tell you whether or not you ask.|t:light nw:Exact_Minutes
Activate [2 actions] (manipulate); Frequency once per day; Effect A perfect cup of tea appears in your hand. Drinking it takes 1 action and grants temporary Hit Points equal to the item's level ({@lvl}) for 1 minute.|t:light nw:Perfect_Tea
Activate [1 action] (manipulate); Frequency once per day; Effect A small butterfly made of light flutters out and lands on whoever within 30 feet the GM thinks most needs a hug.|t:light nw:Small_Butterflies
You can ask it one yes-or-no question a day about food. It is always right about food.|t:light nw:Food_Opinions
Activate [1 action] (auditory); Frequency once per 10 minutes; Effect It makes the sound of footsteps somewhere within 30 feet. You gain a +1 circumstance bonus to your next check to Create a Diversion.|t:light nw:Distant_Footsteps
Small birds are fond of it and perch on you when they can. Bird-lovers warm to you quickly.|t:light nature nw:Fond_Birds
Bread you hold stays fresh forever. Other food is on its own.|t:light nw:Fresh_Bread
Once a day you can sneeze to put out a candle or a small torch within 15 feet.|t:light nw:Polite_Sneezes
It translates any animal's noises into very confident, completely wrong commentary.|t:light nature nw:Confident_Animals
Once a day it can point you to the nearest kitchen. It is never wrong.|t:light nw:Nearby_Kitchens
When you fall 10 feet or less, you land on your feet with a small, cheerful boing and take no damage.|t:light nw:Soft_Boings
Activate [1 action] (manipulate); Frequency once per day; Effect You and an adjacent willing ally swap places with a flourish. This movement doesn't trigger reactions.|t:light nw:Swapped_Seats
Activate [reaction]; Frequency once per day; Trigger An ally within 30 feet critically fails a check; Effect It lets out a sympathetic sigh. The ally gains {@lvl} temporary Hit Points for 1 minute.|t:light nw:Kind_Sighs
When you say its name, it glows like a candle, in a color that matches your mood.|t:light nw:Mood_Candles
If you're more than 30 feet from it for a full minute, it folds itself into a paper bird and flies back to you.|t:light nw:Paper_Birds
Once a day you can declare a chair within 10 feet yours. Until the end of the scene, nobody else can get comfortable in it.|t:light nw:Claimed_Chairs
It can whistle any tune it has heard once, and it has heard a lot of tunes.|t:light festival nw:Borrowed_Tunes
Activate [1 action] (manipulate); Frequency once per hour; Effect It brushes your boots, clothes, and hair perfectly clean. You gain a +1 circumstance bonus to your next check to Make an Impression within 10 minutes.|t:light nw:Clean_Boots
Once a day it can tell you which of two paths has more mud. It cares about mud a great deal.|t:light nw:Mud_Reports
Any lock it touches politely says "just a moment". This does not open it any faster.|t:light nw:Patient_Locks
Activate [1 action] (concentrate); Frequency once per day; Effect It hums a lullaby. One willing creature within 10 feet can fall asleep instantly and wakes refreshed after 10 minutes of rest that count as an hour for recovering from fatigue.|t:light nw:Short_Naps
Once a day it can produce a single small coin from behind someone's ear. The coin is always a copper, and always the same copper.|t:light nw:Same_Copper
""")
table("item.style.cost.whimsy", "Whimsical drawbacks (mild)", """
It narrates what you do under its breath. You take a -1 circumstance penalty to Stealth while it's awake; telling it to nap is a free action you can take once an hour.|t:light
It insists on being polished each morning (10 minutes). If you skip it, its first activation of the day takes 1 more action.|t:light
It sneezes glitter when used. The glitter lasts a day and is visible from 30 feet.|t:light
It only works if you thank it afterward. If you forget, it sulks and can't be activated for 1 hour.|t:light
It is jealous of other magic items. If you activate a different item first in a round, it refuses to activate that round.|t:light
It smells strongly of cinnamon. Creatures tracking you by scent gain a +2 circumstance bonus.|t:light
It whistles whenever anyone within 10 feet tells a lie, including you.|t:light
Each time you use it, a small flower blooms on your clothes. At ten flowers people start asking questions.|t:light
It is ticklish. While you are grabbed, you can't stop giggling and can't speak quietly.|t:light
It hates the rain and won't activate in a downpour.|t:light weather
It hiccups once an hour, loudly.|t:light
It wants a name. Until you give it one, it calls you by the wrong name in front of other people.|t:light
It hums the tune of whatever you're doing, and it isn't always a flattering tune.|t:light
It only works if it can see the sky, or a painting of the sky.|t:light
It asks a riddle each dawn. Until someone answers it, its first activation of the day takes 1 more action.|t:light
""")
table("item.style.after.whimsy", "Whimsical aftereffects (for consumables)", """
For an hour afterward, your voice comes out an octave higher.|t:light
Your hair changes color with your mood for a day.|t:light
You can't stop humming for 10 minutes.|t:light
Small birds follow you for an hour, expecting something.|t:light
For a day, everything you say sounds slightly like a question?|t:light
You hiccup bubbles for 10 minutes.|t:light
""")
table("item.style.absurd", "Ridiculous abilities (absurd power; the limit and the drawback pay for it)", """
You can speak with any piece of furniture for 10 minutes. Furniture remembers everything that happened in its room and gossips freely.|t:weird nw:Talking_Furniture
You become a perfect copy of the nearest statue, pigeons included, for up to 1 hour. You can't move or act, and nothing short of a hammer can harm you.|t:weird nw:Perfect_Statues
The next door you open leads to any other door you've personally opened in the last week. You choose; the item comments on your choice.|t:weird nw:Wrong_Doors
A small marching band appears and follows you for 1 minute. Allies within 30 feet gain a +1 status bonus to attack rolls; everyone within 30 feet, you included, is too loud to Hide.|t:weird festival nw:Marching_Bands
Time stops for everyone except you and one goose for 1 round. You can't affect anyone else during that time, but the goose can.|t:weird nw:Stopped_Clocks
For 1 minute, every weapon within 30 feet becomes a loaf of bread. The bread is heavy and still deals 1d4 bludgeoning damage.|t:weird nw:Hard_Bread
You can fly at your Speed for 10 minutes, but only while flapping your arms, which uses both hands.|t:weird nw:Flapping_Arms
Every enemy within 30 feet must attempt a DC {@dc} Will save or dance: off-guard and unable to use reactions for 1 round.|t:weird nw:Compulsory_Dancing
A creature you can see shrinks to Tiny for 1 minute (DC {@dc} Fortitude save negates). Its voice does not shrink.|t:weird nw:Tiny_Complaints
Gravity reverses in a 20-foot burst for 1 round. Everything in it falls up 10 feet, then back down, taking 1d6 bludgeoning damage each way.|t:weird nw:Reversed_Gravity
You teleport up to 500 feet to a place you can see, and arrive wearing an outfit the item chose.|t:weird nw:Chosen_Outfits
A creature you touch must tell the truth for 1 minute (DC {@dc} Will save negates), but only in rhyme, and you must answer it in rhyme too.|t:weird nw:Truthful_Rhymes
All liquid within 30 feet becomes the one liquid of your choice: water, milk, ale, or lamp oil.|t:weird nw:Changed_Liquids
You regain all your Hit Points. Your hair falls out at once, and grows back as feathers over the next week.|t:weird nw:Feathered_Hair
A copy of you appears in an adjacent space for 1 minute. It has your statistics, acts on your turn, and disagrees with every decision you make.|t:weird nw:Contrary_Copies
Your past self from exactly one year ago appears beside you for 1 round. They are furious, and they remember everything.|t:weird nw:Last_Year's_You
The 1d4 nearest doors within 60 feet all fly open at once, however well they are locked.|t:weird nw:Open_Doors
You can breathe water, smoke, and any other gas for 1 hour, and you know what each one tastes like.|t:weird nw:Tasty_Smoke
You learn the true name of one object you touch. The object learns yours, and tells other objects.|t:weird nw:Object_Gossip
Every creature within 30 feet must Stride directly toward the nearest cake on its next turn (DC {@dc} Will save negates). If there's no cake, it's stupefied 1 for 1 round instead.|t:weird nw:Nearest_Cake
For 10 minutes you can walk on walls and ceilings, as long as you keep whistling.|t:weird nw:Whistled_Ceilings
You and everything you are carrying become invisible for 1 minute, and so does the floor beneath you, wherever you go.|t:weird nw:Invisible_Floors
For 1 hour, you can understand and speak with any creature that has a tail.|t:weird nw:Tail_Talk
One unattended object of up to 1 Bulk within 30 feet comes to life for 1 minute, acts on your turn, and does exactly one thing you ask, very badly.|t:weird nw:Helpful_Objects
You can have the weapon announce your attack in a booming voice. Enemies within 30 feet that hear it must attempt a DC {@dc} Will save or be off-guard until the start of your next turn.|t:weird nw:Announced_Attacks|4|it:weapon
On a critical hit, the target must attempt a DC {@dc} Fortitude save or become a goose for 1 round. It keeps its own Hit Points and is extremely upset.|t:weird nw:Sudden_Geese|4|it:weapon
You can Interact to turn the weapon into a fresh loaf of bread for 1 minute. It can't be used to Strike until you turn it back, and everyone within 30 feet gets hungry.|t:weird nw:Convenient_Bread|4|it:weapon
On a hit, the target swaps places with a creature you choose within 30 feet (DC {@dc} Will negates).|t:weird nw:Swapped_Places|4|it:weapon
The first Strike you make each round against a creature that can hear makes a completely wrong noise. The target is stupefied 1 until the end of its next turn from laughing at it.|t:weird nw:Wrong_Noises|4|it:weapon
On a hit, the target's boots swap feet (DC {@dc} Reflex negates): it takes a -10-foot penalty to its Speed for 1 round.|t:weird nw:Wrong_Boots|4|it:weapon
When you hold perfectly still for 1 round, you become a hat stand. Creatures must succeed at a DC {@dc} Perception check to notice you until you move.|t:weird nw:Hat_Stands|4|it:armor
Reaction: you are hit by a Strike. The armor shouts "ow" on your behalf, and you reduce the damage by an amount equal to the item's level. Everyone within 100 feet hears it.|t:weird nw:Loud_Ouches|4|it:armor
Once a day, the armor makes you look exactly like the nearest wall for 1 minute. You can't move while it lasts.|t:weird nw:Wall_Manners|4|it:armor
Reaction: you are targeted by a melee Strike. You teleport to an adjacent space of your choice, and the attacker is off-guard from embarrassment until the start of its next turn.|t:weird nw:Polite_Dodges|4|it:armor
You hover an inch above the ground. You ignore difficult terrain and pressure plates, but you can't Climb and you can't sit down.|t:weird nw:Hovering_Politely|4|it:armor
When you are critically hit, the armor sings the national anthem of a country that doesn't exist. Allies within 30 feet gain a +1 status bonus to saves for 1 round.|t:weird nw:Imaginary_Anthems|4|it:armor
""")
table("item.style.limit", "Ridiculous limits (severe)", """
It works once, ever. Afterward it is a slightly sad spoon.|t:weird
Activating it requires a DC 15 flat check. On a failure, the effect lands on you instead, or the GM picks something worse.|t:weird
It works only on Tuesdays, and the item decides what counts as a Tuesday.|t:weird
It works only while you sing loudly, and you can't use reactions or Stealth while you sing.|t:weird
Activating it takes 3 actions and a full spin on the spot, and you're off-guard until your next turn.|t:weird
It works once a month, and recharging it takes a cheese worth at least {@gp} gp.|t:weird
It works only if nobody present believes it will. The GM has the last word.|t:weird
After using it, you can say nothing but the item's name for 1 hour.|t:weird
It works only in the presence of a goat.|t:weird
Each use permanently removes one random word from your vocabulary. The GM keeps the list.|t:weird
It recharges only after you do something genuinely kind for a stranger, and it knows when you're faking.|t:weird
If anyone in the effect critically fails a check during it, the whole effect reverses.|t:weird
After each use it runs away. Finding it again takes a day.|t:weird
It needs the target's written consent, in triplicate, before it works on them.|t:weird
It works only while you're upside down.|t:weird
The effect lasts only as long as you can hold your breath.|t:weird
It can't be activated within a mile of where it was last used.|t:weird
Each use summons a very small, very angry inspector who fines you {@gp} gp. If you don't pay, it won't work for a week.|t:weird
It obeys only its rightful owner, and it decides who that is each morning (DC 11 flat check, rolled at dawn).|t:weird
Roll a d6 when you activate it. On a 1, nothing happens and the item laughs at you for a full minute.|t:weird
It works once per day, and only right after you've eaten something you hate.|t:weird
""")
table("item.style.cost.severe", "Ridiculous drawbacks (severe)", """
While you carry it, every animal within a mile knows exactly where you are, and most have opinions.|t:weird
It is cursed to be loved. You can't sell, discard, or give it away; it is back in your pack by morning.|t:weird
Using it makes you glow brightly for 1 hour. You can't Hide, and you shed bright light in a 20-foot radius.|t:weird
Whenever you roll a natural 1, the item describes it loudly to everyone within a mile.|t:weird
A single goose follows you everywhere. It can't be harmed, only negotiated with.|t:weird
After each use you are fatigued, and your shoes are on the wrong feet.|t:weird
While you carry it, you can't tell a lie. You can stay silent, but every lie comes out as a hiccup.|t:weird
Each use turns a random coin in your purse into a button. Merchants know.|t:weird
It needs a lullaby every night. If you skip one, it screams at dawn.|t:weird
Each use makes you briefly famous: everyone within a mile learns your name and what you just did.|t:weird
While it's invested, your reflection stops cooperating with you.|t:weird
After each use, the next creature you speak to sees you as its long-lost relative and won't let it go.|t:weird
It weighs 1 Bulk more for every lie told within 30 feet of it today.|t:weird
Every time it activates, it changes its own name, and it only answers to the new one.|t:weird
""")
table("item.style.after.ridic", "Ridiculous aftereffects (for consumables)", """
You float 1 inch off the ground for an hour, and doors that open inward are now your enemies.|t:weird
For a day your voice is extremely deep, and it echoes.|t:weird
You can only walk backward for 10 minutes.|t:weird
You burp a small cloud shaped like your worst decision.|t:weird
For an hour you narrate everything you do in the third person, out loud.|t:weird
You are briefly convinced you are a duck. This lasts 1 round, and everyone saw.|t:weird
""")

# ============================================================ staves and grimoires
# Staves (GM Core, Staves): a staff is prepared during daily preparations and gains charges equal to the preparer's highest
# spell slot rank; casting a spell from it spends charges equal to the spell's rank, and its cantrips cost none. The spell
# list here is generated: one cantrip plus one or two spells for each rank up to the cap, with the cap following the wand
# progression ((level - 1) / 2). That spread is tuning for this tool, not a book rule.
# Grimoires (Secrets of Magic, Grimoires): studied during daily preparations by a caster who prepares spells; the benefit lasts
# until the next preparations even if the book is lost, applies only to spells cast from spell slots, and nobody can use more
# than one grimoire a day. The activation effects below are tuning for this tool, not taken from a book.
STAFF_LOOKS = ["a straight staff of black ash shod in iron", "a gnarled staff with a knot like a closed eye",
               "a staff of pale birch wrapped in leather at the grip", "a tall staff topped with a cage of copper wire",
               "a staff of driftwood, smooth from the river", "a walking staff carved with a spiral of small runes",
               "a staff of dark oak with a crystal set in the head", "a staff of bone-white wood that is always cool to the touch",
               "a staff of stacked rings of horn", "a staff of twisted vine that has not quite stopped growing"]
GRIMOIRE_LOOKS = ["a thick book bound in cracked red leather", "a slim book with an iron clasp shaped like a hand",
                  "a book whose pages are thin sheets of beaten copper", "a book bound in gray cloth that is warm to the touch",
                  "a palm-sized book with a lock and no key", "a heavy book with pages of three different sizes",
                  "a book covered in pressed leaves", "a ledger-like book with margins full of another person's notes",
                  "a book stitched together from several older books", "a book whose title changes with the light"]
GRIMOIRE_EFFECTS = [
    # name, minimum level, effect (use {n} for a number that grows with level)
    ("Extended Reach", 3, "The spell's range increases by {n}0 feet. A spell with a range of touch gets a range of {n}0 feet instead."),
    ("Lingering Echo", 4, "If the spell deals damage to at least one creature, it deals an extra {n} damage of the same type to one of those creatures at the start of your next turn."),
    ("Wider Working", 5, "If the spell has a burst, cone, or line area, the area grows by 5 feet."),
    ("Quiet Casting", 3, "The spell gains the subtle trait: it has no obvious signs that you cast it, though its effects can still be noticed."),
    ("Stubborn Ward", 4, "If the spell grants a status bonus to AC or saves, its duration increases by 1 round."),
    ("Second Target", 7, "If the spell targets exactly one creature and has no duration longer than 1 round, it can target one more creature within range."),
    ("Mending Margin", 3, "If the spell restores Hit Points, one target regains {n} more."),
    ("Shield of Pages", 4, "You gain resistance {n} to all damage until the start of your next turn."),
    ("Careful Words", 5, "One creature of your choice in the spell's area is unaffected by it."),
    ("Sharp Ink", 6, "If the spell requires a spell attack roll, you gain a +1 circumstance bonus to that roll."),
]
GRIMOIRE_FREQ = ["once per day"]

# ============================================================ NPC trappings
# What an NPC carries besides weapons, armor, and magic: a little money, something to eat, what their work needs, a keepsake,
# and, at the Whimsical, Ridiculous, or Grim style, something odd. Every NPC gets these, whatever their Equipment setting, and
# none of it changes their numbers. Lines can ask for the NPC's role (needs r:guard), people (c:goblin), an Underhallow
# native in a Hallowmead game (uh), or the style (s:grim, s:whim, s:ridic). Lines tagged p:hallowmead are in the Hallowmead
# content pack. Underhallow lines draw only on the setting bible: salvage from the refuse chutes, kobold masonry and signs,
# ratfolk ledgers, grippli nets and reeds, leshy glow-moss and seeds (no fire), Mending spare parts and keepsakes.
table("npc.trap.snack", "NPC trappings: something to eat", """
a heel of bread wrapped in a cloth
a wedge of hard cheese
a twist of dried apple slices
a strip of salted pork
a boiled egg, carefully wrapped
a pocketful of roasted chestnuts|urban
an onion, for later
a meat pie gone cold|urban road
a handful of hazelnuts|wild nature
a flask of weak ale
a few trail biscuits|road wild
a smoked fish wrapped in leaves|water
a honey cake, slightly squashed
a pickled egg in a small jar|urban
a sausage of doubtful origin
a lump of fruitcake older than some of the people in the room|t:light
a sack of cave mushrooms, the edible kind (probably)|underground
a sandwich with one bite taken out of it by someone else|t:light
a heel of scrap-bread with something crunchy baked in|p:hallowmead|1.5|c:goblin
half a surface pastry fished out of the refuse, still mostly good|p:hallowmead|1.5|c:goblin
a jar of pickled cave beetles|p:hallowmead|1|c:goblin
a stone-baked flatbread with crumbly cheese|p:hallowmead|1.5|c:kobold
a pouch of roasted grubs|p:hallowmead|1.2|c:kobold
a wedge of good cheese, rewrapped very carefully|p:hallowmead|1.5|c:ratfolk
a tin of dried fruit from the surface, almost certainly smuggled|p:hallowmead|1.2|c:ratfolk
a twist of candied nuts|p:hallowmead|1|c:ratfolk
a skewer of fried blind fish|p:hallowmead|1.5|c:grippli
a pouch of crisp water beetles|p:hallowmead|1.2|c:grippli
a flask of clean mineral water|p:hallowmead|1.5|c:leshy
a pouch of rich, dark loam|p:hallowmead|1.2|c:leshy
a pocket of nuts and berries|p:hallowmead|1.5|c:awakened
a single, very treasured cave-fruit|p:hallowmead|1.2|c:awakened
a honeyed grub saved for later|p:hallowmead|1|c:awakened
a bowl-sized fungus cake wrapped in a leaf|p:hallowmead|1.2|uh
a few boiled cave tubers|p:hallowmead|1|uh
""")
table("npc.trap.upkeep", "NPC trappings: upkeep (for those who don't eat)", """
a tin of machine oil|p:hallowmead|1.5|c:automaton
a polishing cloth and a little wax|p:hallowmead|1.2|c:automaton
a pouch of spare screws, sorted by size|p:hallowmead|1|c:automaton
a spool of thread and a spare button|p:hallowmead|1.5|c:poppet
a darning needle stuck in a cork|p:hallowmead|1.2|c:poppet
a sugared biscuit, carried for someone else|p:hallowmead|1|c:poppet
a tin of oil||1|c:automaton
a spool of thread||1|c:poppet
""")
table("npc.trap.tool", "NPC trappings: what their work needs", """
a whistle on a cord|||r:guard
a set of manacles|||r:guard
a duty roster with their name misspelled|||r:guard
a lantern and a spare wick|||r:guard
a whetstone|||r:soldier
a dented mess tin|||r:soldier
orders folded small in a pocket|||r:soldier
a patched spare cloak|||r:soldier
a flour sack with eyeholes cut in it|||r:bandit
a list of "customers"|||r:bandit
a length of cord|||r:bandit
a ring of mismatched keys|||r:thief
a small pry bar|||r:thief
chalk for marking doors|||r:thief
soft-soled slippers|||r:thief
a coil of snare wire|||r:hunter
a skinning knife|||r:hunter
a pouch of tinder|||r:hunter
a bundle of arrows, half fletched|||r:hunter
a set of small brass scales|||r:merchant
a bundle of receipts|||r:merchant
an abacus|||r:merchant
samples of their wares|||r:merchant
a perfumed handkerchief|||r:noble
a stack of calling cards|||r:noble
a small silver mirror|||r:noble
a letter of introduction|||r:noble
prayer beads|||r:acolyte
a hymnal with dog-eared pages|||r:acolyte
a stick of incense|||r:acolyte
a hooded robe, folded small|||r:cultist
a diagram of a chalk circle|||r:cultist
black candles|||r:cultist
a list of names, some crossed out|t:grim||r:cultist
a pouch of material components|||r:mage
spare ink and quills|||r:mage
a notebook of half-finished theories|||r:mage
a magnifying lens|||r:scholar
a book that is borrowed and overdue|||r:scholar
a wax tablet and stylus|||r:scholar
a roll of clean bandages|||r:healer
a jar of salve|||r:healer
a bundle of dried herbs|||r:healer
a deck of cards, some of them marked|||r:entertainer
a pot of face paint|||r:entertainer
a pocketful of juggling balls|||r:entertainer
a songbook|||r:entertainer
a measuring cord|||r:artisan
a pouch of nails|||r:artisan
a half-finished commission|||r:artisan
a basket|||r:commoner
a ball of twine|||r:commoner
a flint and steel|||r:commoner
a ring of room keys|||r:innkeeper
a grease-stained apron|||r:innkeeper
a tally slate|||r:innkeeper
a coil of tarred line|||r:sailor
a marlinspike|||r:sailor
a knotted cord for counting|||r:sailor
a chunk of interesting ore|||r:miner
a hard leather cap|||r:miner
chalk for marking tunnels|||r:miner
a pouch of seed|||r:farmer
a lucky horseshoe|||r:farmer
a ball of twine|||r:farmer
glass vials, some of them empty|||r:alchemist
stained leather gloves|||r:alchemist
a small mortar and pestle|||r:alchemist
a hollow coin|||r:spy
a vial of invisible ink|||r:spy
a coded letter|||r:spy
a hand-drawn map|||r:guide
a compass|||r:guide
a bundle of trail markers|||r:guide
a hook on a pole for fishing things out of the refuse chutes|p:hallowmead|1.5|c:goblin
a sack of sorted salvage, labeled in three handwritings|p:hallowmead|1.5|c:goblin
a chisel and mallet|p:hallowmead|1.5|c:kobold
a plumb line|p:hallowmead|1.2|c:kobold
a hand-lettered sign that reads WE DIG BIG HOLE|p:hallowmead|1|c:kobold
a ledger of debts in very small writing|p:hallowmead|1.5|c:ratfolk
a lamp hook and a hooded lamp|p:hallowmead|1|c:ratfolk
a fishing net folded into a pouch|p:hallowmead|1.5|c:grippli
a reed pen and a packet of reed paper|p:hallowmead|1.2|c:grippli
a few pouches of seeds, each labeled|p:hallowmead|1.5|c:leshy
a jar of glow-moss for light (it never needs a flame)|p:hallowmead|1.2|c:leshy
a pouch of spare parts, each with a name tag|p:hallowmead|1.5|c:automaton
string labels for salvaged parts|p:hallowmead|1.2|c:poppet
a shiny crystal it can't stop looking at|p:hallowmead|1.2|c:awakened
a list of every word it has learned so far|p:hallowmead|1.2|c:awakened
""")
table("npc.trap.keepsake", "NPC trappings: a keepsake", """
a lock of someone's hair in a locket
a letter they have read so often it is falling apart
a carved wooden animal
a ring that doesn't fit any finger
a pressed flower in a little book
a smooth river stone
a child's drawing, folded small
a coin from a country that doesn't exist any more
a button from a coat they no longer own
a lucky die that has never once been lucky|t:light
a ticket to a play that closed years ago
a tooth, and they won't say whose|t:grim
a ribbon in a faded color
a small tin soldier
the first thing they ever salvaged, wrapped in cloth|p:hallowmead|1.5|c:goblin
a chip of stone from the first arch they ever built|p:hallowmead|1.5|c:kobold
a copied page from the plague records, carefully folded|p:hallowmead|1.5|c:ratfolk
a shell from the old river delta|p:hallowmead|1.5|c:grippli
a pressed leaf from their first bloom|p:hallowmead|1.5|c:leshy
a part from a friend the Mending could not save|p:hallowmead|2|c:automaton
a button from a friend the Mending could not save|p:hallowmead|2|c:poppet
a pebble from the place it first woke|p:hallowmead|1.5|c:awakened
a scrap of a Hallowmead banner, fallen down a refuse chute|p:hallowmead|1|uh
""")
table("npc.trap.odd", "NPC trappings: something odd (Whimsical and Ridiculous styles)", """
a jar of buttons, sorted by mood|t:light|1|s:whim/s:ridic
a very small hat, for a very small friend who hasn't arrived yet|t:light|1|s:whim/s:ridic
a list titled THINGS THAT ARE NOT MY FAULT|t:light|1|s:whim/s:ridic
a spoon with a name engraved on it, not theirs|t:light|1|s:whim/s:ridic
a rubber duck, in case|t:light|1|s:whim/s:ridic
a sock full of other socks|t:light|1|s:whim/s:ridic
a map of a city that is mostly bakeries|t:light|1|s:whim/s:ridic
a pocket watch that runs backward and is never wrong about it|t:light|1|s:whim/s:ridic
an IOU from a dragon, for one sandwich|t:weird|1|s:ridic
a live chicken, which has opinions about the party|t:weird|1|s:ridic
a jar labeled DO NOT OPEN, which is empty, which is somehow worse|t:weird|1|s:ridic
a letter addressed to the party, dated next week|t:weird|1|s:ridic
a deed to a small cloud|t:weird|1|s:ridic
a single shoe, which they insist is a pair|t:weird|1|s:ridic
a portrait of themselves riding a much larger version of themselves|t:weird|1|s:ridic
a sealed envelope containing a smaller sealed envelope, and so on|t:weird|1|s:ridic
a cheese wheel with a door in it|t:weird|1|s:ridic
a stone they swear is a sleeping egg|t:weird|1|s:ridic
a bag of salvaged doorknobs with no doors, kept "for later"|p:hallowmead|1|c:goblin s:whim/s:ridic
a sign that reads ROCK IS GOOD, signed by a rock|p:hallowmead|1|c:kobold s:ridic
""")
table("npc.trap.grim", "NPC trappings: something grim (Grim style)", """
a black armband
a list of the dead, with space left at the bottom|t:grim
a letter they never sent
a key to a house that burned down|t:grim
a single bloodstained glove|t:grim
a small bottle of something they plan to use on themselves if it comes to that|t:grim
a debt marker with their own name on it|t:grim
a wanted poster, folded small, showing someone they loved|t:grim
a lock of hair tied with black thread|t:grim
a page torn from a temple's record of births|t:grim
""")


# ============================================================ grimoire names and spell themes
# A grimoire is named for its owner or for the theme of the spells in it. A theme is picked from the traits of the spells the
# book holds (fire, mental, healing...); its words also name generated spells. Patterns use @owner (Vellora's), @ownerfirst
# (Vellora), @book, @adj, and @thing. Lines with nm:owner are used only when the book has an owner.
GRIMOIRE_THEMES = {
    "fire": ["fire"], "cold": ["cold"], "electricity": ["electricity"], "acid": ["acid"], "sonic": ["sonic"],
    "force": ["force"], "mental": ["mental"], "healing": ["healing", "vitality"], "void": ["void", "death"],
    "illusion": ["illusion"], "water": ["water"], "air": ["air"], "earth": ["earth", "metal"], "plant": ["plant", "wood"],
    "light": ["light"], "darkness": ["darkness", "shadow"], "fear": ["fear", "emotion"], "travel": ["teleportation"],
    "poison": ["poison"], "spirit": ["spirit"],
}
_GRIM_WORDS = {
    "fire": ("Ember|Smoldering|Cinder-Stained|Scorched|Hearth-Warm", "Quick Fires|Cinders|the Long Burn|Kindling|Banked Coals"),
    "cold": ("Frostbitten|Rime-Edged|Winter|Hoarfrost", "Long Winters|Cold Hands|Hoarfrost|the Deep Freeze"),
    "electricity": ("Storm-Struck|Crackling|Sparking", "Storms|Bottled Lightning|Loud Skies|Sparks"),
    "acid": ("Corroded|Sour|Pitted", "Slow Dissolving|Sour Waters|Etched Things"),
    "sonic": ("Ringing|Thunderous|Echoing", "Echoes|Broken Bells|Loud Silence"),
    "force": ("Unseen|Hammering|Pressing", "Invisible Hands|Pressure|Unseen Walls"),
    "mental": ("Whispering|Dreaming|Wandering-Minded", "Quiet Minds|Borrowed Thoughts|Waking Dreams"),
    "healing": ("Mending|Gentle|Bandaged", "Small Mercies|Mended Bones|Second Breaths"),
    "void": ("Ashen|Hollow|Withering", "Quiet Graves|Last Breaths|Empty Rooms"),
    "illusion": ("Mirrored|Deceiving|Painted", "Pleasant Lies|False Faces|Seeming"),
    "water": ("Drowned|Tide-Stained|Rain-Soaked", "Deep Water|Rising Tides|Slow Rivers"),
    "air": ("Windswept|Gusting|Feather-Light", "Fair Winds|Open Skies|Breath"),
    "earth": ("Stone-Bound|Iron-Clasped|Graveled", "Deep Stone|Bedrock|Old Iron"),
    "plant": ("Overgrown|Rooted|Thorned", "Green Things|Patient Roots|Bramble"),
    "light": ("Lantern|Dawn-Lit|Gleaming", "Small Dawns|Lamplight|Bright Corners"),
    "darkness": ("Shadowed|Lightless|Dusk", "Long Nights|Shadows|Closed Shutters"),
    "fear": ("Dreadful|Shivering|Haunted", "Cold Dread|Nightmares|Closing Doors"),
    "travel": ("Wandering|Restless|Far-Stepping", "Short Journeys|Far Doors|Missed Connections"),
    "poison": ("Venomous|Bitter|Green-Glassed", "Slow Poisons|Bitter Draughts|Nightshade"),
    "spirit": ("Haunting|Soulful|Lingering", "Restless Spirits|Old Souls|Lingering Voices"),
    "general": ("Battered|Annotated|Dog-Eared|Patient|Well-Thumbed", "Practical Workings|Many Small Spells|Useful Words|Careful Study"),
}
for _t, (_a, _n) in _GRIM_WORDS.items():
    table(f"item.grim.theme.{_t}.adj", f"Grimoire and spell words: {_t} (adjectives)", _a.replace("|", "\n"))
    table(f"item.grim.theme.{_t}.thing", f"Grimoire and spell words: {_t} (reads after 'of')", _n.replace("|", "\n"))
table("item.grim.book", "Kinds of spellbook", """
Grimoire
Ledger
Almanac
Codex
Primer
Folio
Compendium
Notebook
Workbook
Commonplace Book
Casebook
Treatise
Daybook
Scrapbook|t:light
Diary|t:light
Testament|t:grim
Last Pages|t:grim
Book of Questionable Ideas|t:weird
""")
table("item.grim.name", "Grimoire name patterns (variables: @owner @ownerfirst @book @adj @thing)", """
{@owner} {@book}||3|nm:owner
{@owner} {@book} of {@thing}||4|nm:owner
{@owner} {@adj} {@book}||3|nm:owner
The {@adj} {@book}||4
{@book} of {@thing}||4
The {@book} of {@thing}||3
The {@adj} {@book} of {@ownerfirst}||1|nm:owner
{@owner} Mostly Correct Notes on {@thing}|t:light|4|nm:owner
Notes on {@thing}, Probably|t:light|3
The Cheerful {@book} of {@thing}|t:light|2
{@owner} Big Book of Absolutely Safe {@thing}|t:weird|4|nm:owner
{@thing} for the Recently Exploded|t:weird|3
The {@book} That Ate {@ownerfirst}|t:weird|2|nm:owner
The Last {@book} of {@ownerfirst}|t:grim|4|nm:owner
{@owner} Confession|t:grim|3|nm:owner
The {@adj} Testament|t:grim|3
""")

# ============================================================ the spell generator (Custom Content, Spells)
# spellgen.py builds a spell from an effect shape (area, bolt, hex, ward, utility), a theme, and a style. The numbers come from
# the GM Core Area Damage table in gmtables.py (see spellgen.py for what is tuning). The wording is below.
table("spell.noun.area", "Spell names: area spells", """
Burst
Bloom
Wave
Storm
Spray
Surge
Flood
""")
table("spell.noun.bolt", "Spell names: single-target attacks", """
Lance
Dart
Lash
Bolt
Arrow
Spike
Needle
""")
table("spell.noun.hex", "Spell names: curses and hexes", """
Curse
Mark
Whisper
Grip
Touch
Hex
""")
table("spell.noun.ward", "Spell names: wards", """
Ward
Mantle
Shell
Veil
Shroud
Aegis
""")
table("spell.noun.utility", "Spell names: utility spells", """
Trick
Knack
Charm
Working
Favor
Gesture
""")
table("spell.name", "Spell name patterns (variables: @adj @noun @thing @first)", """
{@adj} {@noun}||5
{@noun} of {@thing}||4
{@first}'s {@adj} {@noun}||1
Mildly {@adj} {@noun}|t:light|3
{@first}'s Polite {@noun}|t:light|2
{@noun} of Gentle {@thing}|t:light|2
Absolutely Safe {@noun}|t:weird|3
{@noun} of Regrettable {@thing}|t:weird|3
{@first}'s Inadvisable {@noun}|t:weird|2
{@noun} of the Last {@thing}|t:grim|3
{@adj} {@noun} of Ending|t:grim|3
""")
table("spell.utility", "Utility spell effects (a line's tags: nw name word, th theme for its flavor, and rg range, tg targets, du duration, ar area, df defense)", """
One object of 1 Bulk or less within range floats beside you and follows you at your Speed for the duration.|nw:Following_Object th:force rg:30_feet tg:1_object du:10_minutes
You clean, dry, and fold one outfit or one set of bedding within range.|nw:Tidy_Laundry th:general rg:30_feet tg:1_outfit_or_set_of_bedding
You learn the direction to the nearest source of fresh water within 1 mile.|nw:Water_Sense th:general rg:self
One lock you touch clicks and remembers the last key used on it, showing you its shape in the air.|nw:Remembered_Keys th:general rg:touch tg:1_lock
A door or lid within range opens or closes, as you choose, as long as it isn't locked.|nw:Obedient_Doors th:force rg:30_feet tg:1_door_or_lid
A small light the size of a candle flame follows you for the duration. It doesn't count as a light source for spells that need one.|nw:Candle_Companion th:light rg:self du:1_hour
You write up to 25 words on a surface within range without touching it. The words fade when the spell ends.|nw:Distant_Writing th:mental rg:30_feet du:10_minutes
You warm or cool up to 1 gallon of liquid within range to the temperature you choose.|nw:Right_Temperature th:general rg:30_feet tg:up_to_1_gallon_of_liquid
You sense the emotion most strongly felt by one creature within range: fear, anger, joy, or none.|nw:Honest_Moods th:mental rg:30_feet tg:1_creature
A creature you touch smells of the scent you choose for the duration, which can hide its trail from scent.|nw:Borrowed_Scent th:illusion rg:touch tg:1_creature du:1_hour
A bundle, pack, or sack you carry of up to 3 Bulk counts as 1 Bulk less for the duration (minimum light Bulk), and its straps and clasps stop creaking.|nw:Lighter_Loads th:air rg:touch tg:1_bundle du:1_hour
You ask whether it will rain, snow, or clear within the next day over the area within 1 mile. The spell answers truthfully with a nod or a shake.|nw:Weather_Nods th:air rg:self
A thin cord of light stretches between two points within range, up to 30 feet apart. It bears the weight of one Medium creature and can be climbed or walked along as if it were a rope.|nw:Light_Rope th:light rg:30_feet du:10_minutes
You mend a small break, tear, or crack in one object of 1 Bulk or less, such as a split seam, a cracked cup, or a snapped bootlace. The object works again, though it keeps a faint scar.|nw:Small_Repairs th:general rg:touch tg:1_object
A gentle breeze moves around you in a 20-foot emanation, clearing smoke, fog, and flies and cooling creatures in the area.|nw:Handy_Breeze th:air ar:emanation-20 du:1_minute
Up to a dozen words you speak in a normal voice are heard clearly by one creature within 120 feet, and by no one else.|nw:Carrying_Voice th:air rg:120_feet tg:1_creature
One garment you touch takes on any color or simple pattern you describe until the spell ends.|nw:Chosen_Colors th:illusion rg:touch tg:1_garment du:1_hour
You know exactly which way is north, what the time of day is, and how far you have walked since you last slept, until the end of your next turn.|nw:Plain_Directions th:travel rg:self du:until_the_end_of_your_next_turn
""")

table("spell.style.cost.grim", "Grim spell costs", """
Cost You lose Hit Points equal to twice the spell's rank. This can't be reduced or prevented.
Cost You are drained 1 until your next daily preparations. Casting it while drained raises the value by 1.
Cost You are frightened 1 after casting it, and you can't reduce it below 1 until the end of your next turn.
Cost A creature you can see that you consider an ally takes damage equal to the spell's rank.
Cost Every living plant within 10 feet of you dies, and anyone who sees it knows you did it.
Cost You can't regain Hit Points from magic until the end of your next turn.
""")
table("spell.style.oddity", "Whimsical spell oddities (harmless extras)", """
Each creature the spell affects smells faintly of fresh bread for an hour.
The spell plays a short, slightly triumphant fanfare when it is cast.
Everyone the spell affects hiccups once. This does nothing else.
The spell's area is briefly full of small, harmless bubbles.
A small paper bird folds itself out of the air, watches the spell happen, and leaves.
For a moment afterward, your hair is a completely different color.
The spell's targets each hear a polite cough from behind them.
""")
table("spell.style.cost.whimsy", "Whimsical spell quirks (mild costs)", """
You must say the spell's full name loudly to cast it, so it gains the auditory trait and can't be cast subtly.
After casting it, you can't stop humming until the end of your next turn, and you take a -1 circumstance penalty to Stealth while humming.
The spell leaves a trail of glitter from you to the target that lasts 10 minutes.
You must bow to the target as you cast it. This is part of the casting and has no other effect, except that people notice.
After you cast it, small birds follow you for an hour. They expect crumbs.
""")
table("spell.style.absurd", "Ridiculous spell effects (a line's tags: nw name word, th theme for its flavor, and rg range, tg targets, du duration, ar area, df defense)", """
A target must attempt a Will save. On a failure it becomes convinced it is a teapot for 1 round: it can't act except to say so and stand very still. On a critical failure this lasts 1 minute.|nw:Teapot_Conviction th:mental rg:30_feet tg:1_creature df:Will du:1_round
Every unattended object within range of 1 Bulk or less leaps up and dances for 1 minute. Creatures in the area treat it as difficult terrain.|nw:Dancing_Clutter th:general rg:30_feet du:1_minute
A target must attempt a Fortitude save. On a failure it becomes a goose for 1 round (use the statistics of a goose the GM picks; it keeps its own Hit Points). On a critical failure, 1 minute.|nw:Sudden_Geese th:general rg:30_feet tg:1_creature df:Fortitude du:1_round
You and up to five willing allies within range swap places with each other however you like. Nobody's equipment moves with them.|nw:Musical_Chairs th:travel rg:30_feet tg:you_and_up_to_5_willing_allies
For 1 minute, every door within range opens onto the door it is furthest from.|nw:Misleading_Doors th:travel rg:60_feet du:1_minute
A target must attempt a Will save. On a failure it can only move by skipping for 1 round, which makes its Speed half and makes it off-guard.|nw:Mandatory_Skipping th:general rg:30_feet tg:1_creature df:Will du:1_round
A rain of soft cheese falls in a 20-foot burst for 1 round. The area is difficult terrain until someone eats it.|nw:Rain_of_Soft_Cheese th:general rg:60_feet ar:burst-20 du:1_round
Gravity points sideways in a 20-foot burst for 1 round. Creatures in it fall 10 feet toward one side you choose and take 1d6 bludgeoning damage per spell rank.|nw:Sideways_Gravity th:force rg:60_feet ar:burst-20 du:1_round
You become the target's best friend for 1 minute (Will save negates). The target's actual friends become deeply suspicious of you.|nw:Best_Friends th:mental rg:30_feet tg:1_creature df:Will du:1_minute
Time runs backward for one target for 1 round (Will save negates): it must undo its last action, if that is possible.|nw:Rewound_Moments th:mental rg:30_feet tg:1_creature df:Will du:1_round
Each creature in a 15-foot burst hears its own name called by a deeply disappointed relative and must attempt a Will save. On a failure it is off-guard until the start of its next turn.|nw:Disappointed_Relatives th:mental rg:60_feet ar:burst-15 df:Will du:1_round
A thick, silent fog of drifting feathers fills a 20-foot burst for 1 minute. Creatures in it are concealed from creatures outside it, and sneeze whenever they make a Strike, which does nothing but make a mess.|nw:Feather_Fog th:air rg:60_feet ar:burst-20 du:1_minute
One creature within range is declared mayor of everything within 20 feet of it for 1 minute (Will save negates). Creatures in that area who don't spend an action to salute are slowed 1 for the round.|nw:Sudden_Mayor th:general rg:30_feet tg:1_creature df:Will du:1_minute
All footwear within a 20-foot burst swaps with the footwear of a random creature in the area for 1 minute. Each creature takes a -10-foot penalty to its Speed.|nw:Swapped_Shoes th:travel rg:60_feet ar:burst-20 du:1_minute
You and one creature within range swap voices for 1 minute (Will save negates). Each of you takes a -2 circumstance penalty to Diplomacy and Deception checks and can't Cast a Spell with a verbal component.|nw:Traded_Voices th:illusion rg:30_feet tg:1_creature df:Will du:1_minute
A harmless, carriage-sized moth appears within range, mistakes you for a lamp, and follows you for 1 minute. Hostile creatures that can see it must succeed at a Will save or be frightened 1.|nw:Giant_Moth th:light rg:30_feet df:Will du:1_minute
Each creature in a 20-foot burst must attempt a Will save. On a failure it feels an overwhelming need to tidy, and spends its next action straightening something nearby.|nw:Compulsory_Tidying th:general rg:60_feet ar:burst-20 df:Will du:1_round
One creature within range is convinced it has forgotten something important (Will save negates). For 1 round it takes a -2 circumstance penalty to attack rolls and Perception checks.|nw:Nagging_Doubt th:mental rg:30_feet tg:1_creature df:Will du:1_round
Each creature in a 15-foot burst must succeed at a Fortitude save or be deafened for 1 round. While deafened, it can hear only whispers about itself.|nw:Loud_Whispers th:sonic rg:60_feet ar:burst-15 df:Fortitude du:1_round
One creature of Medium size or smaller within range is lifted a foot off the ground and spun slowly for 1 round (Reflex save negates). While spinning it is off-guard and can't Stride.|nw:Gentle_Spinning th:air rg:30_feet tg:1_creature df:Reflex du:1_round
A small cloud forms above one creature within range and rains on it, and only it, for 1 minute. The creature gains resistance 2 to fire damage and a -1 status penalty to Stealth checks.|nw:Personal_Weather th:air rg:30_feet tg:1_creature du:1_minute
Each creature in a 20-foot emanation must succeed at a Will save or spend its next action telling the nearest creature a secret it was keeping.|nw:Compulsory_Confessions th:mental ar:emanation-20 df:Will du:1_round
You and up to two allies within range become indistinguishable from a party of traveling minstrels for 1 hour. Anyone who sees you assumes you are exactly that, and tips accordingly.|nw:Traveling_Minstrels th:illusion rg:30_feet tg:you_and_up_to_2_allies du:1_hour
One creature within range is certain it is lost for 1 minute (Will save negates). At the start of each of its turns it must Stride half its Speed in a random direction before doing anything else.|nw:Sudden_Lostness th:travel rg:30_feet tg:1_creature df:Will du:1_minute
""")

table("spell.style.limit", "Ridiculous spell limits (severe)", """
You can cast it only once per week.
Casting it takes a DC 11 flat check. On a failure, it affects you instead.
You can cast it only while standing on one foot, which makes you off-guard until your next turn.
You can cast it only if you have eaten cheese in the last hour.
The first time you cast it each day it works. After that, roll a d6: on a 1 to 3, nothing happens and the slot is spent anyway.
It works only if you sing the whole incantation, which takes 3 actions no matter what the spell says.
You can cast it only on a Tuesday, and the spell decides what counts as Tuesday.
""")
table("spell.style.cost.severe", "Ridiculous spell drawbacks (severe)", """
After you cast it, you are stupefied 2 for 1 minute and can only speak in rhyme.
After you cast it, you glow brightly for 1 hour. You can't Hide, and you shed bright light in a 20-foot radius.
Each cast permanently turns one coin you carry into a button.
After you cast it, a goose appears and follows you for a day. It can't be harmed, only negotiated with.
You forget the spell's name after casting it, and need 10 minutes with your notes to remember it.
After you cast it, everyone within a mile learns your name and what you just did.
""")


# ============================================================ names that say what the item does
# make_name uses these tables (item.name.head, and item.name.head.<culture>) whenever an item has a headline: the thing it is
# really about. Every pattern here contains @head, so the name always says what the item does, in plain words.
#   @head   a worn or held item's main ability, as a plain word (its spell: Light, Detect Magic; a skill: Athletics; a sense:
#           Darkvision; Speed; Fire Resistance); a runic weapon's or armor's rune (Frostwake); and, in the Ridiculous
#           style, the absurd ability's own name word (nw:... on the item.style.absurd lines)
#   @stem   in the Ridiculous style, the item's real ability, so the name carries both: "Hat of Light and Reversed Gravity"
#   @odd    a Whimsical item's oddity, by its name word (nw:... on the item.style.oddity lines)
# The strange part of a Weird, Light, or Grim name is a short flourish added at the end of about a third of them (see
# item.name.flourish.weird and .light; Grim uses the epithet tables): "Hat of Light, Probably". The name stays clear and the
# strangeness goes in the quirk and the look. The tags a pattern asks for (nm:absurd, nm:odd, nm:purpose...) work as in
# item.name. Change any of this in Edit Tables.
HEAD_PATTERNS = """
# worn and held: always the headline
{@form} of {@head}||8|it:worn/it:held nm:head
{item.cu.@C@.adj} {@form} of {@head}||8|it:worn/it:held nm:head
{@maker} {@form} of {@head}||3|it:worn/it:held nm:head mk:named
{@purpose} {@form} of {@head}||2|it:worn/it:held nm:head nm:purpose
{@place} {@form} of {@head}||2|it:worn/it:held nm:head nm:place
{@owner} {@form} of {@head}||2|it:worn/it:held nm:head nm:owner
Sir {item.cu.@C@.adj} {@form} of {@head}|t:light|2|it:worn/it:held nm:head
Little {@form} of {@head}|t:light|2|it:worn/it:held nm:head
# worn and held, Ridiculous: the real ability and the absurd one
{@form} of {@stem} and {@head}||6|it:worn/it:held nm:absurd
{item.cu.@C@.adj} {@form} of {@stem} and {@head}||6|it:worn/it:held nm:absurd
{@maker} {@form} of {@stem} and {@head}||2|it:worn/it:held nm:absurd mk:named
# worn and held, Whimsical: the real ability and the oddity
{@form} of {@head} and {@odd}||6|it:worn/it:held nm:odd
{item.cu.@C@.adj} {@form} of {@head} and {@odd}||6|it:worn/it:held nm:odd
{@maker} {@form} of {@head} and {@odd}||2|it:worn/it:held nm:odd mk:named
# weapons: a rune's name word; or the weapon's own name and its absurd ability (Ridiculous)
{@head}||5|it:weapon nm:head
{@head}, the {@base}||3|it:weapon nm:head
{@maker} {@head}||2|it:weapon nm:head mk:named
{item.cu.@C@.adj} {@head}||2|it:weapon nm:head
{@purpose} {@head}||2|it:weapon nm:head nm:purpose
Little {@head}|t:light|2|it:weapon nm:head
Sir {@head}|t:light|2|it:weapon nm:head
{item.cu.@C@.wpn}, the {@base} of {@head}||5|it:weapon nm:absurd
{@fxwpn}, the {@base} of {@head}||4|it:weapon nm:absurd
{@maker} {item.cu.@C@.wpn}, the {@base} of {@head}||2|it:weapon nm:absurd mk:named
# armor: the same
{@head}||5|it:armor nm:head
{@head}, the {@base}||3|it:armor nm:head
{@maker} {@head}||2|it:armor nm:head mk:named
{item.cu.@C@.adj} {@head}||2|it:armor nm:head
{@purpose} {@head}||2|it:armor nm:head nm:purpose
Good Old {@head}|t:light|2|it:armor nm:head
{item.cu.@C@.arm}, the {@base} of {@head}||5|it:armor nm:absurd
{@fxarm}, the {@base} of {@head}||4|it:armor nm:absurd
{@maker} {item.cu.@C@.arm}, the {@base} of {@head}||2|it:armor nm:absurd mk:named
# wands, scrolls, potions, devices, and staves (Ridiculous): the spell, and the absurd ability
{@kind} of {@spell} and {@head}||5|it:wand/it:scroll/it:potion/it:device nm:absurd
{item.cu.@C@.adj} {@kind} of {@spell} and {@head}||5|it:wand/it:scroll/it:potion/it:device nm:absurd
{@kind} of {@head}, Formerly {@spell}||4|it:wand/it:scroll/it:potion/it:device nm:absurd
{@maker} {@kind} of {@spell} and {@head}||2|it:wand/it:scroll/it:potion/it:device nm:absurd mk:named
{item.cu.@C@.adj} {@kind} of {@head} and Mostly {@spell}|t:weird|2|it:wand/it:scroll/it:potion/it:device nm:absurd
"""
table("item.name.head", "Item name patterns that say what the item does (no culture). Variables: @head @stem @odd @form @base @kind @spell @maker @purpose @place @owner @fxwpn @fxarm",
      HEAD_PATTERNS.replace("{item.cu.@C@.adj}", "{item.adj}").replace("{item.cu.@C@.wpn}", "{item.weapon.a}{item.weapon.b}")
      .replace("{item.cu.@C@.arm}", "{item.armor.a}{item.armor.b}"))
for _key in CULTURE_INFO:
    table(f"item.name.head.{_key}", f"Item name patterns that say what the item does, {CULTURE_INFO[_key]['label']} style",
          HEAD_PATTERNS.replace("@C@", _key))
table("item.name.flourish.weird", "Weird name flourishes (a short ending added to about a third of Weird names)", """
Probably
More or Less
Mostly
Allegedly
Supposedly
Technically
Sort Of
Possibly
In Theory
Usually
Reportedly
Within Reason
""")
table("item.name.flourish.light", "Light name flourishes (a short ending added to about a third of Light names)", """
Cheerfully
Lightly Used
Gladly
Happily
With Gusto
Warmly
Gently
Mostly Harmless
""")
table("item.grim.name.absurd", "Grimoire name patterns, Ridiculous style: the book's theme and its absurd ability (variables: @owner @ownerfirst @book @adj @thing @head)", """
{@owner} {@book} of {@head}||4|nm:owner
{@owner} {@book} of {@thing} and {@head}||3|nm:owner
The {@adj} {@book} of {@head}||4
{@book} of {@thing} and {@head}||4
The {@book} of {@head} and {@thing}||3
{@owner} Mostly Correct Notes on {@head}|t:light|3|nm:owner
Notes on {@head}, Probably|t:weird|3
{@head} for the Recently Exploded|t:weird|3
The Last {@book} of {@head}|t:grim|3
{@owner} Confession of {@head}|t:grim|2|nm:owner
""")


# ============================================================ spell names and flavor
# Spell names. A damage, hex, or ward spell is named for its theme (item.grim.theme.<theme>.adj and .thing, above) and its shape
# (spell.noun.*). A utility or Ridiculous spell is named for what it does: its effect line carries a name word (nw:Soft_Cheese)
# and spell.name.head patterns put it in the name, so "Rain of Soft Cheese" really is the cheese spell.
table("spell.name.head.adj", "Spell names: small adjectives for utility and Ridiculous spells", """
Minor
Careful
Passing
Handy
Tidy
Quiet
Polite
Steady
Quick
Gentle
""")
table("spell.name.head", "Spell name patterns for utility and Ridiculous spells (variables: @head @adj @first)", """
{@head}||6
{@adj} {@head}||2
{@first}'s {@head}||2
{@first}'s {@adj} {@head}||1
Mildly Helpful {@head}|t:light|3
{@first}'s Helpful {@head}|t:light|2
{@head}, Technically|t:weird|3
Absolutely Reasonable {@head}|t:weird|3
{@first}'s Inadvisable {@head}|t:weird|3
The Last {@head}|t:grim|2
{@first}'s Final {@head}|t:grim|2
""")

# Spell flavor. Not rules: what a spell is like to cast and to watch. A spell's flavor is built from four things:
#   spell.flavor.<theme>      what it smells, tastes, sounds, and feels like to cast, how the effect looks, and what is left
#                             afterward (lines are tagged by their needs: fv:smell, fv:taste, fv:sound, fv:feel, fv:look, fv:after)
#   spell.flavor.general      the same for any theme, with lines for the Grim, Whimsical, and Ridiculous styles (tagged t:...)
#   spell.flavor.cast / .look / .after   sentence frames that put two of those senses, the look, and the aftermath into words
#   spell.flavor.effect       sentences written for one utility or Ridiculous effect (needs nw:...), so its flavor fits it
#   spell.flavor.detail       an extra sentence for about a third of spells
# Smells and tastes are nouns, sounds and looks are noun phrases, feels are noun phrases that follow "feels", and afters are
# clauses that follow "Afterward,". Add your own lines in Edit Tables.
SPELL_FLAVOR = {
    "fire": {
        "smell": ["scorched sugar", "hot pennies", "a struck match", "singed hair and cedar smoke", "bread crust just past golden",
                  "warm stone after a bonfire", "pine sap spitting in a hearth"],
        "taste": ["ash", "burnt honey", "hot iron", "cinnamon that bites back", "smoke and orange peel"],
        "sound": ["a log settling in a hearth", "dry kindling catching with a crackle", "a forge bellows heaving somewhere out of sight",
                  "paper curling in a flame", "a low roar like a chimney drawing", "embers popping like tiny knuckles"],
        "feel": ["a flush of dry heat behind the eyes", "warmth pooling in the palms", "a prickle along the forearms like standing too close to a stove",
                 "sweat springing up at the hairline", "an itch of heat in every knuckle"],
        "look": ["a flock of ember-petals that curl open and blacken as they fall", "a sheet of orange silk caught in a wind of its own making",
                 "a field of tiny hearths all lighting at once", "a flower of molten glass blooming in fast motion",
                 "a thousand matches struck in a single breath", "a dragon's yawn made of lamplight", "a red-gold curtain drawn across the air"],
        "after": ["the air stays warm for a minute and nearby candles lean toward the spot", "a ring of pale ash settles and keeps its shape even in a breeze",
                  "everyone present is suddenly hungry for toast", "the smell of smoke clings to clothing until the next rain",
                  "frost on the nearest windowpane melts into a perfect thumbprint", "the shadows in the area stay a shade too orange for an hour"]},
    "cold": {
        "smell": ["snow before it falls", "a cellar in midwinter", "cold iron and peppermint", "wet slate", "a frozen pond at dawn", "breath on a cold window"],
        "taste": ["peppermint and tin", "frosted iron", "cold milk", "snowmelt with a hint of pine"],
        "sound": ["ice creaking on a lake", "a thin glassy chime like a spoon on a goblet", "the squeak of boots in deep snow",
                  "frost crackling across a windowpane", "a wind whistling between two stones", "breath hissing through teeth"],
        "feel": ["a bright cold behind the teeth", "fingertips going numb and then tingling", "a shiver that starts at the nape and runs down the spine",
                 "the hair on the arms lifting", "a clean ache in the sinuses like a bite of ice cream"],
        "look": ["a spray of glittering needles that hang in the air before they fall", "a hundred glass feathers shattering in slow motion",
                 "a pale blue bloom of frost-ferns unfurling across nothing", "a wave of white lace stitched in an instant",
                 "a silent avalanche of snowflakes thrown sideways", "the breath of a giant on a winter morning", "a mirror of ice that forgets to be a mirror"],
        "after": ["a rime of frost clings to everything in the area for ten minutes", "breath steams in the air even on a hot day",
                  "every metal object nearby feels cold enough to hurt for a moment", "nearby water ripples once and goes still",
                  "the grass in the area stays stiff and silver until the sun reaches it", "someone nearby is suddenly sure they left a window open"]},
    "electricity": {
        "smell": ["ozone and rain", "hot copper", "a lightning-struck tree", "a room full of candles just blown out", "scorched dust on a lamp", "static and wet stone"],
        "taste": ["tin and lemon", "old coins", "sour copper", "salt and sparks", "sharp metal"],
        "sound": ["a thin whine like a wet finger on glass", "the rip of heavy canvas tearing", "thunder rolling a long way off",
                  "a hornet trapped in a jar", "a snap like a whip crack", "a hum that rises until the teeth buzz"],
        "feel": ["every hair standing on end", "a tingle running from the fingertips to the elbows", "a tasteless jolt behind the breastbone",
                 "the skin of the hands crawling", "a faint tugging in the fillings of the teeth"],
        "look": ["a web of white forks spreading across nothing", "a flock of blue-white birds that vanish when they land",
                 "a pulled thread of daylight, brighter than it should be", "a branching river drawn in light and running uphill",
                 "a handful of living sparks thrown like seed", "the afterimage of lightning that has not happened yet", "a tangle of silver wire that crackles as it unspools"],
        "after": ["loose hair and fine dust drift toward the spot for a minute", "small metal objects nearby are faintly warm and a little magnetic",
                  "every lamp in the area flickers once", "the smell of rain lingers though the sky is clear",
                  "the nearest cat is extremely offended", "a faint blue glow clings to doorknobs and buckles until someone touches them"]},
    "acid": {
        "smell": ["lemon rind and rusted nails", "a freshly cut green apple", "vinegar on hot metal", "pickling brine", "the inside of a copper kettle", "sour wine"],
        "taste": ["lemon peel", "old copper coins", "sour apple", "copper and pepper", "vinegar and rust"],
        "sound": ["a long hiss like wet sand poured on a griddle", "bubbling like a stew a little too eager", "the slow fizz of a drink left open too long",
                  "a sizzle and a soft pop", "a dry rasp like a file on slate"],
        "feel": ["a sour pucker in the cheeks", "a tingle in the gums", "a fine itch along the fingertips as if sand were rubbing them",
                 "a sharp tang that runs up behind the nose", "a briefly slick feeling on the palms"],
        "look": ["a pour of green-gold syrup that steams where it lands", "a lace of tiny bubbles eating its own pattern into the air",
                 "a rain of glittering dewdrops, each with a hungry little shimmer", "a fan of yellow-green mist that curls like cooling breath",
                 "a splash of liquid glass that drips upward", "the sheen on a beetle's back, unrolled like a rug", "a thin ribbon of lime-colored smoke winding around its target"],
        "after": ["the ground in the area is pitted with tiny, perfectly round dimples", "every metal object nearby is a little duller than before",
                  "a thin yellow haze hangs for a minute and then curls away", "flies avoid the spot for the rest of the day",
                  "the smell of vinegar clings to the air until the next breeze", "a nearby bucket of water has gone slightly cloudy"]},
    "force": {
        "smell": ["nothing at all, which is somehow noticeable", "the clean air of an unlit room", "chalk dust and cold stone", "a drawer of new linens",
                  "pressed paper", "the faint air of a held breath"],
        "taste": ["pennies", "cold water", "nothing, and then a tooth-aching sweetness", "chalk", "clean water with a hint of tin"],
        "sound": ["a deep, soft thump like a heavy door shutting in another room", "a hollow bell struck inside a pillow", "air pushed out of a bellows",
                  "the pop of ears when a mountain road drops", "a single note of a very large string, plucked once"],
        "feel": ["a pressure on the eardrums", "a gentle shove behind the shoulder blades", "a hollow where the stomach used to be",
                 "the sensation of stepping onto a stair that isn't there", "a tightness across the chest like a held breath"],
        "look": ["a ripple in the air, as if a stone had dropped into still water", "a pane of faintly shimmering glass that has no edges",
                 "a hand made of clear, bent air", "a series of ghostly rings that rush outward and vanish", "a bruise-colored shimmer around its target",
                 "a great invisible fist, visible only by the dust it shoves", "a net of straight light that fills in as it falls"],
        "after": ["loose dust and small stones in the area settle in neat rings", "the air feels dense and polite for a moment",
                  "every hanging lantern nearby swings once in the same direction", "a leaf drifts upward and is not seen again",
                  "the nearest door swings open a hand's width and stays there", "the words spoken in the next minute sound slightly muffled"]},
    "spirit": {
        "smell": ["lilies and old candle wax", "incense in a cold chapel", "rain on a graveyard path", "a pressed flower in an old book",
                  "a bridal veil stored in cedar", "warm bread and wet wool"],
        "taste": ["communion wine", "honey and salt", "well water", "clove and candle smoke", "sweet tea gone cold"],
        "sound": ["a choir of distant voices singing one held note", "a whisper of leaves where there are no trees", "a bell rung underwater",
                  "a hushed murmur like many people praying", "a long soft sigh that seems to come from the walls", "a child's laugh a long way off"],
        "feel": ["a hand resting briefly on the shoulder", "the sense of being watched kindly", "a warmth that begins in the chest and spreads",
                 "the hair on the neck lifting in a cold draft", "a quiet like standing in an empty church"],
        "look": ["a procession of pale, translucent figures that bow and dissolve", "a flock of pale moths made of candle-light",
                 "a column of drifting white petals with faces in them", "a ribbon of silver-white smoke shaped like praying hands",
                 "a lantern held by a hand that is not there", "a slow, solemn dawn rising inside a mist", "a crowd of long shadows standing where no one stands"],
        "after": ["the nearest candles burn straight and still for a minute", "a ring of tiny white flowers opens in the dirt and closes by morning",
                  "the animals in the area are quiet and watchful for a while", "a faint bell tone hangs in the air and slowly fades",
                  "people nearby speak in lowered voices without noticing", "a dusting of salt-white light clings to the ground and fades like breath on glass"]},
    "void": {
        "smell": ["a cellar closed for a century", "cold ashes", "wet earth and old paper", "a snuffed candle", "the inside of a long-shut coffin", "dust and rust"],
        "taste": ["ash and iron", "cold tea", "dust", "copper pennies", "stale water"],
        "sound": ["a hollow sigh like wind through an empty well", "the creak of a very old door", "a distant dripping that never quite repeats",
                  "a bell cracked down the middle", "the rustle of dry paper", "a silence so complete the ears ring"],
        "feel": ["a chill that has weight", "a faint ache in old injuries", "a hollowing behind the ribs", "a creeping numbness that starts at the fingers",
                 "the sense of a long staircase going down"],
        "look": ["a spill of black ink that rises instead of falling", "a ring of grey moths that crumble as they fly",
                 "a pool of starless dark that is deeper than the ground beneath it", "a ribbon of pale, ragged mist that sinks into the floor",
                 "the shadow of a bird flying over where there is no bird", "a pressed-flower wreath that withers as it opens", "a long slow exhale made visible, grey and cold"],
        "after": ["the plants in the area droop and take a day to recover", "the light in the area seems thinner for a few minutes",
                  "small insects scatter and do not return until morning", "every shadow nearby leans away from its owner",
                  "a faint smell of old stone clings to anyone who was close", "the nearest candle gutters and has to be relit"]},
    "sonic": {
        "smell": ["hot brass and rosin", "a wet drum skin", "a cathedral after the organ stops", "sawdust and varnish", "cold stone and incense", "a freshly struck bell"],
        "taste": ["tin and cloves", "silver spoons", "metal and sweetness", "brass", "sharp mint"],
        "sound": ["a bell struck once, very hard, and rung until it breaks", "a thunderclap in a stone chapel", "a thousand glasses singing at one pitch",
                  "a choir of cracked trumpets", "a drum heard through the floorboards", "a whistle too high for dogs and too sharp for people"],
        "feel": ["a hum in the jaw and the breastbone", "the teeth buzzing in the gums", "a pressure rattling the ribcage",
                 "a tingling that starts in the ears and ends in the toes", "a numbness like standing too close to a bell tower"],
        "look": ["a ripple of bent air spreading in perfect rings", "a fan of silver arcs, each one a struck wine glass", "a wave of shimmering lines, the way heat shimmers over a road",
                 "a ringing cloud of tiny, vibrating dots", "a spiral of bright thread unwinding from a spool", "a series of sharp, pale-blue crescents fanning out",
                 "a drum-skin of light stretched across the air and struck"],
        "after": ["loose windows and cups in the area hum for a moment", "birds nearby go quiet and then all take off at once",
                  "a faint ringing hangs in everyone's ears for a minute", "the echo comes back a half-second late, and a little different",
                  "nearby water shivers into perfect concentric rings", "dust and small crumbs dance in a circle on the nearest table"]},
    "mental": {
        "smell": ["a library at night", "sealed letters", "the inside of a wardrobe", "warm tea and chalk dust", "old perfume and pressed leaves", "new paper and lamp oil"],
        "taste": ["peppermint and static", "lemon and chalk", "strong tea", "a pinch of salt on warm bread", "clean, cold water"],
        "sound": ["a faint, rising murmur like a distant crowd", "a single piano note held a long time", "pages turning in an empty room",
                  "a whisper that stops when you try to hear it", "a gentle chime like a spoon on a cup", "a hum that seems to come from inside the skull"],
        "feel": ["a bright pressure behind the eyes", "a gentle tug on the thoughts, like a hand on a sleeve", "a wave of drowsy calm",
                 "a prickle at the scalp", "the odd feeling of knowing the next word"],
        "look": ["a pale ribbon of light threading between its targets' eyes", "a swarm of silver motes drifting toward the ears",
                 "a slow ripple that makes everything seem half a step farther away", "an open eye drawn in the air that closes as it fades",
                 "a gentle, shimmering halo that bends around the head", "a spiral of soft colors turning and turning", "a mist of dim stars gathering around the brow"],
        "after": ["the people nearby lose their train of thought for a heartbeat", "a faint ringing hangs in the ears for a few breaths",
                  "the next dream anyone has is unusually vivid", "nearby conversation stalls and then resumes as if nothing happened",
                  "every clock in earshot seems to tick a little too slowly", "the targets blink slowly and look around as if waking"]},
    "poison": {
        "smell": ["green apples and bitter almonds", "crushed nightshade leaves", "a damp cellar of mushrooms", "sour milk and vinegar",
                  "a chemist's shop at closing time", "wet moss and old pennies"],
        "taste": ["bitter almonds", "copper and cloves", "a sour green tang", "tarnished silver", "thin soap"],
        "sound": ["a thin wet hiss like air leaving a bladder", "a slow drip into a stone basin", "a faint, papery rustle like a snake under dry leaves",
                  "a low bubbling mutter", "a sticky sound like boots pulling out of mud"],
        "feel": ["a bitter warmth in the throat", "a slow crawl across the skin like many tiny feet", "a faint nausea that gathers and fades",
                 "a prickle at the corners of the mouth", "a sense of the room tilting slightly"],
        "look": ["a drifting cloud of pale green smoke with a sweet shine", "a splash of oily color that leaves rainbows on the air",
                 "a thin mist that curls into the shape of a hooded snake", "a drizzle of glistening droplets that never quite hit the ground",
                 "the colors of a bruise spreading through water", "a vine of green mist climbing the air", "a haze of yellow-green spores glittering in a sunbeam"],
        "after": ["flowers in the area close and refuse to open until morning", "small animals give the spot a very wide berth",
                  "the water in a nearby bucket smells faintly of almonds", "a sour taste clings to anyone who was close",
                  "flies circle the spot and then leave", "a faint green sheen lingers on leaves and fabric"]},
    "fear": {
        "smell": ["cold sweat", "a snuffed candle in a locked room", "wet earth under a door", "damp wool and tallow", "the breath of an old well", "iron and old fear"],
        "taste": ["bile and pennies", "cold metal", "dry ash", "blood from a bitten tongue", "sour terror"],
        "sound": ["footsteps on the stairs of an empty house", "a child's laugh from the wrong direction", "a heartbeat that isn't yours",
                  "a door creaking open in a room with no door", "breathing very close to the ear", "a long, low note that seems to hold its breath"],
        "feel": ["gooseflesh rising from the wrists to the shoulders", "a cold finger tracing the spine", "a lurch like missing the last step",
                 "the certainty of being watched from behind", "a tightness in the chest that is not quite pain"],
        "look": ["a tall, thin shadow that stands where nothing casts it", "a smear of darkness shaped like a crawling hand",
                 "a pair of pale eyes opening in the air and blinking out", "a wave of cold grey cloud with teeth in it",
                 "the outline of a door that opens inward onto nothing", "a swarm of tiny black moths gathering into a face", "a crowd of long shadows leaning in a little too far"],
        "after": ["the animals in the area refuse to enter it for the rest of the day", "anyone who looked at it keeps glancing over a shoulder",
                  "every shadow nearby seems too long for an hour", "a lingering chill hangs in the air, though nothing is cold",
                  "the nearest dog is under a table and will not be coaxed out", "people nearby laugh a little too loudly and a little too long"]},
    "light": {
        "smell": ["warm linen and hot dust", "honeyed candle wax", "a sun-baked wall", "sweet hay and sunlight", "lamp oil and oranges", "clean cotton drying in the sun"],
        "taste": ["honey and lemon", "warm milk", "sugared petals", "sweet bread", "sunlit water"],
        "sound": ["a clear bell note rising and rising", "a low shimmer like a struck cymbal", "a thin glassy chime", "the soft rustle of a banner unfurling",
                  "a choir far away singing something cheerful", "the hush of a lamp being lit"],
        "feel": ["warmth spreading across the face like morning sun", "a lightness in the chest", "the eyes watering from a brightness that doesn't hurt",
                 "a pleasant tingling in the fingertips", "a feeling of being gently, cheerfully looked at"],
        "look": ["a fan of golden threads spooling out of the air", "a drift of white-gold petals that glow as they land", "a dawn rising in a single heartbeat",
                 "a flock of bright, silent birds that scatter into sparks", "a cut gem held up to the sun, enormous and spinning",
                 "a stained-glass window made of light, shattering softly", "a lantern as large as a house, burning without a flame"],
        "after": ["shadows in the area are sharp and short for a minute", "flowers in the area turn toward the spot like sunflowers",
                  "everyone present blinks and sees a green afterimage", "a warm, honey-colored glow clings to the nearest wall",
                  "small insects gather in a happy cloud", "the nearest candles seem brighter and stay that way until they are lit again"]},
    "illusion": {
        "smell": ["greasepaint and powder", "a theater after the show", "burnt sugar and rosewater", "the inside of a trunk of costumes", "paint and lamp smoke", "warm velvet"],
        "taste": ["honey and mint", "rosewater", "sugar-glazed petals", "sweet smoke", "sherbet"],
        "sound": ["a faint, half-heard music", "a curtain rising", "applause somewhere behind a wall", "a whisper of silk", "a stage whisper that is too clear",
                  "glass beads shaken gently in a hand"],
        "feel": ["a tilt of the world a quarter inch to the left", "a tingle at the edge of vision", "the sense of stepping onto a stage",
                 "a dreamy, buttery warmth around the eyes", "a prickle like many people looking at once"],
        "look": ["a gauze curtain of colored mist that draws aside to show something that is not there", "a painted backdrop unrolling across the air",
                 "a shoal of bright fish made of glitter swimming through open air", "a hall of mirrors with only one reflection",
                 "a soap bubble the size of a house that pops into smaller scenes", "a shimmer of heat over a road, with a shape inside it", "a paper lantern that opens like a flower"],
        "after": ["for a moment, anyone who saw it can't say what color it was", "a faint glitter hangs in the air and slowly sinks",
                  "bystanders disagree afterward about what they saw", "the nearest mirror shows something a little off for a minute",
                  "a brief smell of greasepaint hangs about the caster", "the spot seems slightly larger than it ought to be until someone looks away"]},
    "earth": {
        "smell": ["wet clay and iron", "a freshly turned field", "cold stone and moss", "a mine shaft after rain", "warm brick and mortar", "crushed gravel and sap"],
        "taste": ["grit and salt", "iron and clay", "wet stone", "mineral water", "warm bread with sand in it"],
        "sound": ["a deep grinding like millstones", "gravel shifting under a heavy boot", "a distant rumble like a cart on a bridge", "a crack like a split log",
                  "the groan of a timber taking too much weight", "a slow, patient scrape of stone on stone"],
        "feel": ["a heaviness settling into the knees", "a tremble that starts in the soles of the feet", "a taste of dust at the back of the throat",
                 "the knuckles aching like cold stone", "a slow, solid hum in the bones"],
        "look": ["a wave of broken stone rolling outward like surf", "a fist of packed earth rising from the ground", "a spray of bright crystal splinters flung like confetti",
                 "a field of tiny pillars growing like a crop of quartz", "a scatter of clay beads rolling in perfect lines", "a hillside shrugging in its sleep",
                 "a great slow-moving hand of sand and root"],
        "after": ["the ground in the area is cracked in a pattern like a spider's web", "a few small stones hum faintly for a minute",
                  "the nearest puddle has gone perfectly still", "the smell of rain on dirt hangs in the air",
                  "loose gravel settles into rings around the spot", "a patch of grass in the area is a little taller than the rest"]},
    "air": {
        "smell": ["rain on a hot road", "clean laundry on a line", "cut grass and cold wind", "the top of a mountain", "wet leaves and woodsmoke", "salt and open sky"],
        "taste": ["cold water", "mint and rain", "clean air with a hint of snow", "sea salt", "honeydew"],
        "sound": ["a high rushing like a river overhead", "a whistle in the eaves", "sails snapping in a stiff wind", "a flock of birds taking off at once",
                  "a long soft sigh from nowhere", "the creak of a weathervane turning"],
        "feel": ["the hair lifting from the neck", "a lightness in the heels", "a cool breeze pouring down the collar", "the stomach swooping on a swing",
                 "a tug at the sleeves like a hand pulling the cloth"],
        "look": ["a spiral of leaves lifted from nowhere", "a ribbon of silver mist that corkscrews across the sky", "a flock of pale feathers that fall upward",
                 "a smooth wave of rippling air with dust swirling inside it", "a great invisible sheet billowing and snapping", "a hand of cloud that opens and closes",
                 "a rush of loose paper and petals racing in a straight line"],
        "after": ["hats and scarves in the area are a little crooked", "a few loose feathers drift down for a full minute",
                  "the nearest weathervane spins once and points at the caster", "the air smells of rain even if none follows",
                  "every candle in the area leans in the same direction", "small leaves arrange themselves in a spiral on the ground"]},
    "travel": {
        "smell": ["a road after rain", "the inside of a mail coach", "wet canvas and horse", "spices from a far-off market", "salt and tar", "hot cobblestones and cinnamon"],
        "taste": ["salt and bread crust", "road dust and mint", "cold tea from a flask", "far-off market spices", "old coins"],
        "sound": ["a coach wheel rattling away over a bridge", "a ship's bell tolling in a harbor that isn't there", "a gate swinging on its hinges",
                  "footsteps going somewhere without hurry", "a ticking like a pocket watch"],
        "feel": ["a tug at the navel like a rope being pulled", "a feeling of having forgotten something at home", "a faint lurch like a coach starting",
                 "the pleasant dizziness of standing at a crossroads", "a swooping in the stomach like a wave"],
        "look": ["a door that opens in the air and closes behind the traveler", "a thin silver thread stretching from one place to another",
                 "a handful of road dust that settles into a map", "a quick fold in the world like a letter being creased", "a trail of glowing footprints that fade behind",
                 "a pair of invisible hands drawing a curtain", "a shimmer where distance forgets itself"],
        "after": ["the caster's boots are covered in dust from somewhere far away", "a faint smell of a different place lingers for a minute",
                  "the nearest compass spins and then settles on the caster", "every small object nearby has slid a little to the left",
                  "a few coins nearby are somehow warm", "the sense of being slightly late for something lingers until supper"]},
}
# What any spell can be like, and the lines for the Grim (t:grim), Whimsical (t:light), and Ridiculous (t:weird) styles.
SPELL_FLAVOR["general"] = {
    "smell": ["warm bread and woodsmoke", "clean rain", "a freshly opened book", "old coins and lamp oil", "chalk dust and candle wax", "a stable in the morning"],
    "taste": ["copper and honey", "salt and lemon", "mint and iron", "cold tea", "faint sweetness"],
    "sound": ["a distant bell", "a low hum like a kettle beginning to sing", "a soft rustle like pages turning", "a faint chime", "the pop of a cork somewhere far away",
              "a sound like a deep breath let out slowly"],
    "feel": ["a tingle in the fingertips", "a warmth behind the breastbone", "a brief dizziness like standing up too fast", "a prickle at the back of the neck",
             "a pleasant weight in the hands"],
    "look": ["a swirl of colored smoke that folds in on itself", "a bright ribbon unrolling across the air", "a shower of tiny glowing motes that wink out one by one",
             "a ripple through the air like a pebble in a pond", "a flicker of light that hangs for a heartbeat", "a drift of translucent petals", "a quick fan of pale sparks"],
    "after": ["the air smells faintly of rain for a minute", "nearby objects settle with a small, satisfied clink", "a few motes of light drift down and go out",
              "everyone nearby feels briefly, inexplicably pleased", "a faint chime hangs in the air", "the shadows in the area seem a little more relaxed"]}
SPELL_FLAVOR_TONE = {
    "grim": {
        "smell": ["cold candle wax and something sweet gone off", "a damp cellar and old iron", "ashes in a grate", "funeral lilies"],
        "taste": ["ash and cold iron", "blood from a bitten tongue", "stale water"],
        "sound": ["a distant bell tolling slowly", "the creak of a gallows rope", "a single raven's call", "breath that isn't your own"],
        "feel": ["a cold weight settling on the shoulders", "the ache of an old wound", "a slow drain, like blood leaving the face"],
        "look": ["a smear of black across the air like a handprint", "a slow, ragged shadow crawling outward", "a bruise-purple bloom opening in the dark"],
        "after": ["a hush settles over the area and nobody can say why", "the smell of grave-dirt lingers for a minute", "the caster's hands stay cold for an hour"]},
    "light": {
        "smell": ["warm cinnamon buns", "fresh-cut grass and jam", "a bakery on a Sunday", "lavender soap"],
        "taste": ["strawberry jam", "warm butter", "birthday cake"],
        "sound": ["a tiny fanfare", "a chorus of delighted hiccups", "the pop of a champagne cork", "a slide whistle going up"],
        "feel": ["a giggle bubbling up the throat", "a warm, fuzzy feeling like a hug from a stranger", "a tickle at the back of the knees"],
        "look": ["a shower of confetti with opinions", "a flock of tiny, cheerful birds made of glitter", "a soap bubble that wobbles and then pops into rainbows"],
        "after": ["a handful of confetti drifts down for a full minute", "the nearest dog wags its tail without explanation", "everyone nearby has the first line of a song stuck in their head"]},
    "weird": {
        "smell": ["a library that has been rained on by mistake", "hot toast and thunderstorms", "warm cheese and violin rosin", "an attic full of clocks"],
        "taste": ["purple, somehow", "the color of a Tuesday", "pennies and strawberry cream"],
        "sound": ["a trombone being politely reasoned with", "a flock of hinges", "a goose clearing its throat", "a crowd applauding a decision"],
        "feel": ["the knees briefly believing they are elbows", "a tingle like being addressed by name from a great height", "every hair swapping places with its neighbor"],
        "look": ["a parade of small, serious umbrellas", "a cloud that is clearly three smaller clouds in a coat", "a curtain rising on a stage with no one on it"],
        "after": ["someone nearby apologizes to a chair", "the nearest clock gains a minute and refuses to give it back", "a faint smell of toast lingers until the next sneeze"]},
}
for _theme, _by in SPELL_FLAVOR.items():
    _lines = [f"{x}|||fv:{k}" for k, items in _by.items() for x in items]
    if _theme == "general":
        _tone_tag = {"grim": "t:grim", "light": "t:light", "weird": "t:weird"}
        _lines += [f"{x}|{_tone_tag[t]}||fv:{k}" for t, d in SPELL_FLAVOR_TONE.items() for k, items in d.items() for x in items]
    table(f"spell.flavor.{_theme}", f"Spell flavor, {_theme}: what casting it smells, tastes, sounds, and feels like, how the effect looks, and what is left afterward",
          "\n".join(_lines))

table("spell.flavor.cast", "Spell flavor: the casting, as a sentence (two senses; needs fv:smell, fv:taste, fv:sound, or fv:feel)", """
Casting it fills the air with the smell of {@smell} and leaves a taste of {@taste} on the caster's tongue.|||fv:smell fv:taste
The caster smells {@smell} as the last word is spoken, and tastes {@taste} for a few breaths afterward.|||fv:smell fv:taste
A smell of {@smell} rises first, then a taste of {@taste} at the back of the throat.|||fv:smell fv:taste
A smell of {@smell} gathers around the caster, and {@sound} follows the words.|||fv:smell fv:sound
The casting sounds like {@sound}, and for a moment the air smells of {@smell}.|||fv:smell fv:sound
{^@sound} comes with the words, and the air smells of {@smell}.|||fv:smell fv:sound
The caster smells {@smell} and feels {@feel}.|||fv:smell fv:feel
Those standing close smell {@smell}, while the caster feels {@feel}.|||fv:smell fv:feel
A smell of {@smell} hangs in the air as the caster feels {@feel}.|||fv:smell fv:feel
The caster tastes {@taste} while {@sound} rolls out of nowhere.|||fv:taste fv:sound
{^@sound} marks the casting, and a taste of {@taste} lingers.|||fv:taste fv:sound
The words are followed by {@sound} and a taste of {@taste}.|||fv:taste fv:sound
The caster feels {@feel} and tastes {@taste} until the spell settles.|||fv:taste fv:feel
A taste of {@taste} floods the mouth as the caster feels {@feel}.|||fv:taste fv:feel
Casting it leaves the caster with {@feel}, and a taste of {@taste}.|||fv:taste fv:feel
The caster feels {@feel} as {@sound} rolls out of nowhere.|||fv:sound fv:feel
{^@sound} fills the space around the caster, along with {@feel}.|||fv:sound fv:feel
The caster feels {@feel}, and then comes {@sound}.|||fv:sound fv:feel
""")
table("spell.flavor.look", "Spell flavor: how the effect looks, as a sentence (needs sh:area, sh:bolt, sh:hex, sh:ward, or sh:utility)", """
Where it takes hold, it looks like {@look}.|||sh:area
The burst spreads outward as {@look}.|||sh:area
It opens across the ground like {@look}.|||sh:area
Seen from above, the area looks like {@look}.|||sh:area
In flight it looks like {@look}.|||sh:bolt
It crosses the distance as {@look}.|||sh:bolt
Anyone watching sees {@look} race out from the caster's hand.|||sh:bolt
On the target it shows as {@look}.|||sh:hex
The mark that forms looks like {@look}.|||sh:hex
The curse settles over the target as {@look}.|||sh:hex
The ward settles in the air as {@look}.|||sh:ward
Around the target it hangs as {@look}.|||sh:ward
It wraps the target in {@look}.|||sh:ward
It resolves into {@look}.|||sh:utility/sh:absurd
The working looks like {@look}.|||sh:utility/sh:absurd
Anyone watching sees {@look}.|||sh:utility/sh:absurd
""")
table("spell.flavor.after", "Spell flavor: what is left afterward, as a sentence", """
Afterward, {@after}.
Moments later, {@after}.
Once it fades, {@after}.
For a little while after, {@after}.
""")
table("spell.flavor.detail", "Spell flavor: an extra sentence for about a third of spells", """
Observers rarely agree on its color.
Anyone who has seen it before knows it by the smell alone.
It is quieter than it looks.
Older casters say it never looks quite the same twice.
It leaves no mark, though everyone is certain it should have.
Children and animals always notice it first.
The effect seems to hesitate before it begins, as if considering the target.
It is considered rude to describe it to someone who has not seen it.
Casters who learn it young say it feels like remembering something.
Nobody has ever managed to cast it the same way twice.
The first time anyone sees it, they laugh, and it is never clear why.|t:light
It makes a small, pleased noise when it works.|t:light
It has been known to blush.|t:light
Every witness remembers it a little more dramatically than it was.|t:light
Those who study it say it is more concerned with itself than with its target.|t:grim
It is said to take something small from the caster each time, and never to give it back.|t:grim
Even the people who use it prefer not to watch.|t:grim
Nobody has ever been able to say what it wants.|t:weird
Scholars are divided on whether it is a spell or an opinion.|t:weird
It has been banned from three towns and one particularly sensitive tavern.|t:weird
""")

table("spell.flavor.effect", "Spell flavor written for one utility or Ridiculous effect (needs nw:its name word, and fv:cast, fv:look, or fv:after)", """
The caster smells steeped black tea and hears a polite whistle from nowhere.|||nw:Teapot_Conviction fv:cast
The target's posture goes strangely spout-and-handle, and a faint cloud of steam rises from its ears.|||nw:Teapot_Conviction fv:look
Afterward the target remembers nothing except a strong urge to be poured.|||nw:Teapot_Conviction fv:after
A tune nobody is humming starts up, and the caster's feet tap on their own.|||nw:Dancing_Clutter fv:cast
Every loose button, spoon, and quill hops up and begins a spirited, entirely unrehearsed reel.|||nw:Dancing_Clutter fv:look
For hours afterward, small objects in the area turn up a few inches from where they were left.|||nw:Dancing_Clutter fv:after
The caster tastes pond water and hears a single, thoughtful honk.|||nw:Sudden_Geese fv:cast
The target's coat thickens into soft white feathers, its nose lengthens, and it hisses with total conviction.|||nw:Sudden_Geese fv:look
A few white feathers drift down and refuse to be swept away until sunset.|||nw:Sudden_Geese fv:after
A bright little tune plays from somewhere above, and everyone in range feels the urge to look for a seat.|||nw:Musical_Chairs fv:cast
Each pair of people blurs into a flurry of pointing fingers and gasps, and everyone lands somewhere different, slightly out of breath.|||nw:Musical_Chairs fv:look
Everyone is certain that whoever ended up where they were standing was cheating.|||nw:Musical_Chairs fv:after
The caster smells fresh paint and hears a polite knock from every direction.|||nw:Misleading_Doors fv:cast
Handles turn, hinges sigh, and each door opens on the wrong room with perfect confidence.|||nw:Misleading_Doors fv:look
Nobody agrees afterward which door they came in by.|||nw:Misleading_Doors fv:after
The caster tastes lemon and hears a very small drumroll.|||nw:Mandatory_Skipping fv:cast
The target's legs hop and swing in a jaunty rhythm, and its arms begin to swing along to a tune it did not choose.|||nw:Mandatory_Skipping fv:look
The target is out of breath and quietly furious, and cannot remember what it was angry about.|||nw:Mandatory_Skipping fv:after
The caster smells warm rind and hears something between a drumroll and a squelch.|||nw:Rain_of_Soft_Cheese fv:cast
Pale gold curds fall in slow, round blobs, as if the sky had briefly mistaken itself for a pantry.|||nw:Rain_of_Soft_Cheese fv:look
Rats from three streets away arrive in a tidy line and are very polite about it.|||nw:Rain_of_Soft_Cheese fv:after
The caster's stomach tips to one side and the horizon lists like a ship.|||nw:Sideways_Gravity fv:cast
Dust, coins, and creatures slide across the area in the same direction, and a bucket takes a long, slow arc.|||nw:Sideways_Gravity fv:look
Everyone feels slightly off-balance until they have had something to eat.|||nw:Sideways_Gravity fv:after
The caster tastes warm cocoa and hears a gentle, welcoming chord.|||nw:Best_Friends fv:cast
The target's guard drops, its eyes go wide and shining, and it takes a step forward with an open, delighted face.|||nw:Best_Friends fv:look
The target insists on writing the caster a letter every week, and none of them ever arrive.|||nw:Best_Friends fv:after
The caster smells the last thing they ate and hears a clock tick backward.|||nw:Rewound_Moments fv:cast
The target's last gesture unspools in reverse, like a film running the wrong way, and it looks faintly embarrassed.|||nw:Rewound_Moments fv:look
Everyone remembers the last few seconds in a slightly different order.|||nw:Rewound_Moments fv:after
The caster smells boiled cabbage and hears a long, weary sigh from far away.|||nw:Disappointed_Relatives fv:cast
Every creature in the burst winces, as if its name had been spoken in exactly the wrong tone.|||nw:Disappointed_Relatives fv:look
Everyone vaguely remembers that they should call their mother.|||nw:Disappointed_Relatives fv:after
The caster tastes pillow-stuffing and hears a soft, rising whump.|||nw:Feather_Fog fv:cast
Feathers pour into the air and hang in a thick, drifting cloud that makes everything look like the inside of a snow globe.|||nw:Feather_Fog fv:look
Feathers turn up in pockets and boots for weeks.|||nw:Feather_Fog fv:after
The caster smells printer's ink and hears distant, enthusiastic applause.|||nw:Sudden_Mayor fv:cast
The target's chest swells, a sash of civic importance appears from nowhere, and passersby instinctively stop to salute.|||nw:Sudden_Mayor fv:look
The target keeps correcting other people's grammar for an hour.|||nw:Sudden_Mayor fv:after
The caster smells leather polish and hears a brisk, many-footed shuffle.|||nw:Swapped_Shoes fv:cast
Boots and slippers pop off, spin through the air in a neat arc, and land on the wrong feet.|||nw:Swapped_Shoes fv:look
Everyone is quite sure their shoes have always been this uncomfortable.|||nw:Swapped_Shoes fv:after
The caster tastes their own words and hears a sound like two violins tuning.|||nw:Traded_Voices fv:cast
The target opens its mouth to answer and the caster's voice comes out, delivering a stunning retort the target did not choose.|||nw:Traded_Voices fv:look
Both of them discover they have been misquoting each other for years.|||nw:Traded_Voices fv:after
The caster smells lamp oil and hears the soft thump of enormous wings.|||nw:Giant_Moth fv:cast
A moth the size of a carriage glides in, dusty and gentle, and settles on the caster's shoulder to bask in their glow.|||nw:Giant_Moth fv:look
A fine silver dust sparkles on everything it touched, and the nearest lantern flickers in sympathy.|||nw:Giant_Moth fv:after
The thumb tingles and the spell goes quiet, as if listening.|||nw:Following_Object fv:cast
The object rises an inch, turns once as if checking itself, and settles in beside the caster like a patient dog.|||nw:Following_Object fv:look
It keeps drifting a little too close, bumping the caster's elbow when it wants attention.|||nw:Following_Object fv:after
Creases flatten themselves in a rolling wave, and a breath of sun-dried linen wafts out.|||nw:Tidy_Laundry fv:look
Everything smells like a clean spring day, and a sock turns up that nobody knew was missing.|||nw:Tidy_Laundry fv:after
The caster's thumb tingles, and a faint wet-slate cool leans like a divining rod toward the nearest water.|||nw:Water_Sense fv:look
The caster is thirsty, and strangely certain of it.|||nw:Water_Sense fv:after
The faint outline of the last key glows in the lock, every notch showing, like frost on a windowpane.|||nw:Remembered_Keys fv:look
The lock ticks twice, quietly pleased with itself.|||nw:Remembered_Keys fv:after
The door swings with the unhurried grace of a courtier showing someone out.|||nw:Obedient_Doors fv:look
The hinges give a small sigh of relief.|||nw:Obedient_Doors fv:after
A tiny flame no bigger than a thumbnail blooms in midair and hovers at the caster's shoulder, leaning toward whoever is speaking.|||nw:Candle_Companion fv:look
It gutters when someone tells a long story and flares when it is a good one.|||nw:Candle_Companion fv:after
Letters form one at a time in a neat, slightly smug hand, as if an invisible clerk were writing them out.|||nw:Distant_Writing fv:look
The ink-smell of a fresh page lingers, and the words fade from the edges inward.|||nw:Distant_Writing fv:after
A thin curl of steam or frost rises from the liquid, then settles, satisfied.|||nw:Right_Temperature fv:look
The liquid tastes exactly as it should, and not one degree more.|||nw:Right_Temperature fv:after
A faint tint passes over the creature like color through a glass: red for anger, blue for fear, gold for joy.|||nw:Honest_Moods fv:look
The caster feels a flicker of that mood for a moment, and then it fades.|||nw:Honest_Moods fv:after
A pleasing scent rises from the creature like a sachet being opened.|||nw:Borrowed_Scent fv:look
Dogs lose interest, and a passing cat looks personally insulted.|||nw:Borrowed_Scent fv:after
The straps go slack and the bundle bobs up as if held by a string.|||nw:Lighter_Loads fv:look
For an hour the caster walks with a spring in their step.|||nw:Lighter_Loads fv:after
A pocket of air gives a slow nod or a slow shake, with a faint breath of the coming weather.|||nw:Weather_Nods fv:look
The caster's knee, which has been right about the weather before, agrees.|||nw:Weather_Nods fv:after
A thin cord of pale light stretches between the two points and hums quietly like a tuned string.|||nw:Light_Rope fv:look
The rope shivers into drifting motes, and the smell of fresh hemp lingers.|||nw:Light_Rope fv:after
Hairline seams knit together from the edges inward, like frost closing over a pane.|||nw:Small_Repairs fv:look
The object is cleaner than before, with a faint smell of glue and baking.|||nw:Small_Repairs fv:after
A breeze rises out of the ground and spirals up past the shoulders, taking smoke and flies with it.|||nw:Handy_Breeze fv:look
Hats tilt, and the smell of cut grass drifts in from nowhere.|||nw:Handy_Breeze fv:after
The words leave the caster's mouth as faint ripples that travel in a straight line to the listener's ear.|||nw:Carrying_Voice fv:look
A bird in the nearest tree repeats the last word it heard.|||nw:Carrying_Voice fv:after
The color spreads across the cloth in a ripple, like dye poured into water, then sinks in.|||nw:Chosen_Colors fv:look
The new color seems oddly satisfied with itself, and the fabric smells of clean paint.|||nw:Chosen_Colors fv:after
A faint line of silver light points north from the caster's feet, then thins to nothing.|||nw:Plain_Directions fv:look
The caster knows, with strange confidence, what time it is and where the nearest bakery is not.|||nw:Plain_Directions fv:after
The caster smells beeswax polish and hears a brisk, disapproving tutting.|||nw:Compulsory_Tidying fv:cast
Boots are lined up, hats are squared, and every loose coin is stacked into an obsessive little tower.|||nw:Compulsory_Tidying fv:look
The area is spotless, and nobody in it is comfortable.|||nw:Compulsory_Tidying fv:after
The caster tastes something half-remembered and hears a faint, unplaceable jingle.|||nw:Nagging_Doubt fv:cast
The target pats its pockets, frowns at the sky, and starts to say something it cannot finish.|||nw:Nagging_Doubt fv:look
Hours later the target remembers what it forgot, and it was nothing at all.|||nw:Nagging_Doubt fv:after
The caster tastes a mouthful of secrets and hears every word they have ever muttered, played back at once.|||nw:Loud_Whispers fv:cast
The air ripples with a thousand hushed conversations, each at the volume of a trumpet.|||nw:Loud_Whispers fv:look
Everyone present is fairly sure somebody said something about them.|||nw:Loud_Whispers fv:after
The caster feels the world tilt a quarter turn and hears a small, cheerful music box.|||nw:Gentle_Spinning fv:cast
The target rises, turns lazily like a top, and tries very hard to look dignified about it.|||nw:Gentle_Spinning fv:look
The target is dizzy, and the nearest children are very impressed.|||nw:Gentle_Spinning fv:after
The caster smells rain on hot stone and hears a polite rumble overhead.|||nw:Personal_Weather fv:cast
A grey cloud the size of a hat appears above the target and rains steadily on its head and nowhere else.|||nw:Personal_Weather fv:look
The cloud lingers a moment, sulks, and drifts off to find another target.|||nw:Personal_Weather fv:after
The caster tastes salt and tears and hears a gentle, expectant hush.|||nw:Compulsory_Confessions fv:cast
Everyone in the area leans in, clears their throat, and begins confidently with the words 'I should probably mention'.|||nw:Compulsory_Confessions fv:look
The next hour of conversation is remarkably honest and deeply uncomfortable.|||nw:Compulsory_Confessions fv:after
The caster smells woodsmoke and cheap perfume and hears a distant, hopeful fiddle.|||nw:Traveling_Minstrels fv:cast
Lutes, feathered hats, and bells on the shoes appear on everyone in range, as if they had always been there.|||nw:Traveling_Minstrels fv:look
Someone in the crowd is certain they have heard the song before and cannot name it.|||nw:Traveling_Minstrels fv:after
The caster smells map paper and hears a distant, patient sigh.|||nw:Sudden_Lostness fv:cast
The target turns slowly on the spot, squints at the horizon, and sets off confidently in the wrong direction.|||nw:Sudden_Lostness fv:look
The target turns up an hour later in a nearby town and will not say how.|||nw:Sudden_Lostness fv:after
A thin whistle starts somewhere in the target's chest, and one arm crooks out like a handle.|||nw:Teapot_Conviction fv:look
The target is mortified, and slightly damp.|||nw:Teapot_Conviction fv:after
Spoons, buttons, and boots leap in time, bowing to each other as they pass.|||nw:Dancing_Clutter fv:look
A single sock keeps dancing for another hour, quite alone.|||nw:Dancing_Clutter fv:after
A tail of white feathers sprouts, the voice becomes a magnificent honk, and the target waddles with great authority.|||nw:Sudden_Geese fv:look
Everyone who saw it gives geese a respectful nod for a week.|||nw:Sudden_Geese fv:after
Hands grab hands, feet shuffle, and an invisible band strikes up as people swap places in a blur.|||nw:Musical_Chairs fv:look
Someone is sure they got there first and will not let it go.|||nw:Musical_Chairs fv:after
Latches click in a ripple, and every door opens a crack onto somewhere it had no business being.|||nw:Misleading_Doors fv:look
A broom closet is, for some reason, full of sunlight.|||nw:Misleading_Doors fv:after
The target's knees lift, its arms swing, and a cheerful whistle comes from nowhere in particular.|||nw:Mandatory_Skipping fv:look
The target's mood does not improve even a little, no matter how well it skipped.|||nw:Mandatory_Skipping fv:after
Curds and wheels of pale gold fall in a gentle, pungent rain, making soft little noises as they land.|||nw:Rain_of_Soft_Cheese fv:look
The smell of cheese lingers longer than the cheese, and then so does the cheese.|||nw:Rain_of_Soft_Cheese fv:after
Everything leans, then slides, and a dropped coin rolls up the nearest wall.|||nw:Sideways_Gravity fv:look
A faint, queasy sideways feeling stays with everyone until they next sit down.|||nw:Sideways_Gravity fv:after
The target breaks into a wide, honest grin and starts telling the caster about its day.|||nw:Best_Friends fv:look
The target hums the caster's favorite song for an hour, and does not know why.|||nw:Best_Friends fv:after
The target takes a step back, un-says its last sentence, and looks puzzled to find its mouth shut.|||nw:Rewound_Moments fv:look
The air has the faint feeling of an argument that has not happened yet.|||nw:Rewound_Moments fv:after
Heads dip, shoulders sag, and a dozen faces make the same small, guilty flinch.|||nw:Disappointed_Relatives fv:look
Several people write letters home that night.|||nw:Disappointed_Relatives fv:after
Feathers swirl in a slow, silent blizzard that muffles every sound and tickles every nose.|||nw:Feather_Fog fv:look
The nearest bird is deeply offended.|||nw:Feather_Fog fv:after
A sash, a hat, and a very large key appear on the target, and it begins to nod regally at passersby.|||nw:Sudden_Mayor fv:look
The target's first act in office is to declare a holiday, and a few people agree.|||nw:Sudden_Mayor fv:after
Every shoe in range pops off, swaps owners like marbles in a game, and finds someone a size too small.|||nw:Swapped_Shoes fv:look
People walk home in strange boots and tell no one.|||nw:Swapped_Shoes fv:after
The target opens its mouth and the caster's voice comes out, saying something far wittier than the target intended.|||nw:Traded_Voices fv:look
For a day afterward, the caster is fairly sure they are being quoted incorrectly.|||nw:Traded_Voices fv:after
A pale, dusty shape glides in out of the dark and hovers at the caster's shoulder like a very large, very patient lamplighter.|||nw:Giant_Moth fv:look
Someone's candle has been put out, and it is quietly offended.|||nw:Giant_Moth fv:after
""")

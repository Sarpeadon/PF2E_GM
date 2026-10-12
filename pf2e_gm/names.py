"""Names and ancestries for generated people. Standard library only.

Every ancestry maps to a naming style. Each style has given names, surnames, and epithets, and a name is built
from one of several patterns, so the same ancestry produces many different shapes of name.
"""
import random

ANCESTRIES = [
    "Human", "Dwarf", "Elf", "Gnome", "Goblin", "Halfling", "Leshy", "Orc", "Anadi", "Android", "Automaton",
    "Azarketi", "Catfolk", "Centaur", "Conrasu", "Fetchling", "Fleshwarp", "Ghoran", "Gnoll", "Goloma", "Grippli",
    "Hobgoblin", "Kashrishi", "Kitsune", "Kobold", "Lizardfolk", "Merfolk", "Minotaur", "Nagaji", "Poppet",
    "Ratfolk", "Shisk", "Shoony", "Skeleton", "Sprite", "Strix", "Tengu", "Vanara", "Vishkanya", "Yaksha",
    "Barathu", "Kasatha", "Lashunta", "Pahtra", "Shirren", "Skittermander", "Vesk", "Ysoki",
    "Arboreal", "Awakened Animal",
]
SMALL = {"gnome", "goblin", "halfling", "kobold", "ratfolk", "leshy", "ysoki", "skittermander", "shoony", "grippli",
         "poppet", "automaton", "awakened-animal"}      # Hallowmead: playable automatons and awakened animals are Small
TINY = {"sprite"}

BASE_WEIGHTS = {"Human": 30, "Dwarf": 10, "Elf": 7, "Gnome": 7, "Halfling": 9, "Goblin": 7, "Orc": 4, "Kobold": 3,
                "Hobgoblin": 2, "Catfolk": 2, "Leshy": 1.2, "Tengu": 1, "Kitsune": 1, "Lizardfolk": 1, "Ratfolk": 1.5,
                "Fleshwarp": 1, "Gnoll": 1, "Minotaur": 0.6, "Merfolk": 0.6}
DEFAULT_WEIGHT = 0.35
ENV_BOOST = {
    "underground": {"Dwarf": 4, "Goblin": 4, "Kobold": 4, "Gnome": 2, "Orc": 1.5, "Ratfolk": 3, "Fleshwarp": 2,
                    "Halfling": 0.5, "Elf": 0.4, "Human": 0.5},
    "wild": {"Elf": 2, "Leshy": 4, "Orc": 1.5, "Catfolk": 2, "Gnoll": 2, "Grippli": 4, "Human": 0.8},
    "water": {"Azarketi": 10, "Merfolk": 8, "Nagaji": 3, "Lizardfolk": 3, "Human": 0.7},
    "urban": {"Human": 1.3, "Halfling": 1.3, "Gnome": 1.2, "Tengu": 1.5},
}
ADJECTIVE = {"human": "human", "dwarf": "dwarven", "elf": "elven", "gnome": "gnomish", "goblin": "goblin",
             "halfling": "halfling", "orc": "orcish", "kobold": "kobold", "hobgoblin": "hobgoblin",
             "catfolk": "catfolk", "leshy": "leshy", "lizardfolk": "lizardfolk", "merfolk": "merfolk",
             "minotaur": "minotaur", "ratfolk": "ratfolk", "gnoll": "gnoll", "tengu": "tengu", "kitsune": "kitsune",
             "fleshwarp": "fleshwarp", "skeleton": "skeletal", "automaton": "automaton", "android": "android",
             "fetchling": "fetchling", "azarketi": "azarketi", "arboreal": "arboreal", "awakened animal": "awakened",
             "grippli": "grippli", "nagaji": "nagaji", "vesk": "vesk", "ysoki": "ysoki",
             "kasatha": "kasatha", "lashunta": "lashunta", "shirren": "shirren", "pahtra": "pahtra"}


def adjective(ancestry):
    """'Dwarf' -> 'dwarven'. Unknown (homebrew) ancestries are used as typed, lowercased."""
    return ADJECTIVE.get(str(ancestry).strip().lower(), str(ancestry).strip().lower())


def pick_ancestry(rng=None, env_tags=(), weights=None):
    """Weighted random ancestry. `weights` is your setting's own mix (it may include homebrew ancestries) and is
    used exactly as written. Without it, BASE_WEIGHTS is used and ENV_BOOST leans the mix toward the environment."""
    rng = rng or random.Random()
    base = dict(weights) if weights else {a: BASE_WEIGHTS.get(a, DEFAULT_WEIGHT) for a in ANCESTRIES}
    out = {}
    for a, w in base.items():
        if not weights:
            for env in env_tags:
                w *= ENV_BOOST.get(env, {}).get(a, 1.0)
        out[a] = max(0.0, w)
    names = list(out)
    total = sum(out.values())
    if total <= 0:
        return rng.choice(ANCESTRIES)
    return rng.choices(names, weights=[out[n] for n in names], k=1)[0]


# ---------- naming styles ----------
STYLES = {
    "human": dict(
        given="Alric Brenna Cadmus Dara Edrin Fenna Garrick Hollis Isolde Jorvan Kestra Lorcan Maren Nessa Orrin "
              "Perrin Quill Rosalind Sef Tamsin Ulric Vesna Wynn Yara Zane Bram Cora Dunstan Elspeth Fitch Gwen "
              "Hale Ines Joss Kit Lyra Mattis Nell Osric Pell Rue Sorrel Tobin Una Vaughn Willa Ysolde Aldous "
              "Berta Corin Dessa Emric Faye Gideon Hester Ivo Jenna Kasimir Lena".split(),
        surname="Ashford Blackwood Coldwater Hale Marsh Thorne Vance Wilder Crane Fenwick Gray Holloway Kettle "
                "Larkin Mercer Nightingale Oakes Pike Quarry Redfern Sutter Tanner Underhill Vickery Weaver "
                "Yarrow Barrow Copperfield Dyer Fletcher Gable Harrow Ingram Judd Lowry Mallory Nash Orchard "
                "Penhallow Rook Stanton Tolliver Wick".split(),
        epithet=["the Younger", "the Elder", "Two-Fingers", "Longstride", "the Quiet", "Redhand", "Half-Moon",
                 "the Lucky", "Ninepence", "the Honest", "Grayfell", "the Tall", "Sourmilk", "Candlewick",
                 "Brasscap", "the Late", "Fairweather", "Nailbiter"],
        place=["Graywick", "Hollowford", "Marrowmere", "Ashby", "Underbrook", "Stonebridge", "Lanternhill",
               "Saltmarsh", "Cold Harbor", "Millbrook"]),
    "dwarf": dict(
        given=[a + b for a in "Bal Dur Grim Thor Kar Bro Dag Hel Mor Ulz Gar Tor Bar Dol Fal Rur".split()
               for b in "in ak dun rek bek ra ett ul don ga rik mund".split()],
        surname="Stonebender Ironhide Deepdelver Ashbeard Coalheart Granitefist Lodewright Anvilborn Boulderback "
                "Cinderhelm Flintvein Gemcutter Hammerfall Marrowdeep Orebreaker Pickaxe Runeward Slatehand "
                "Tunnelwise Veinseeker".split(),
        epithet=["the Patient", "Redbeard", "Lantern-Eyes", "Three-Picks", "the Stubborn", "Deepfoot",
                 "Mugwhistle", "Grudgekeeper", "Quarrytongue", "the Steady"],
        place=["Deepmarrow", "Ironroot", "Underhall", "Gneiss Hold", "Cragmouth", "Lodestone"]),
    "elf": dict(
        given=[a + b for a in "Ae Ela Ilv Syl Thal Lia Mer Fae Cae Ny Vael Ith Sae Aran".split()
               for b in "rin nael wyn thar lith andra ion essa ril vae doril eth".split()],
        surname="Moonbrook Silverleaf Dawnwhisper Starfall Mistvale Duskwillow Thornweave Brightwater Ashglade "
                "Everlight Windsong Oakenveil Nightbloom Rainthistle Sunhollow".split(),
        epithet=["of the Long Memory", "Leafspeaker", "the Wanderer", "Quickwater", "Moonwatcher", "the Pale",
                 "Dewfoot", "Stormborn"],
        place=["Silverglade", "Aeldwood", "Mistfall", "Thornreach"]),
    "goblin": dict(
        given=[a + b for a in "Skr Krag Gob Nix Zig Grub Snik Rat Mug Fizz Bork Glim Hob Pik Snag Wort".split()
               for b in "itch gix nob zit ka bug snot gle rat wick tooth ik".split()],
        surname="Scraptooth Stonebender Rustgrin Mudpocket Gutterwick Ashsnout Candlefinger Dungheap Fizzbang "
                "Gnawbone Knucklebiter Lintpicker Moldwhisker Nightsoil Pocketwise Snotwhistle".split(),
        epithet=["the Clever", "Quickfingers", "Half-Ear", "Sparkpants", "the Loud", "Nine-Lives", "Bitesize",
                 "the Brave (Mostly)", "Burnt-Tail", "Stinkfoot"],
        place=["Scrap Hollow", "Muckwarren", "Rustgate", "the Heap"]),
    "orc": dict(
        given=[a + b for a in "Gor Ur Thak Mag Rok Shar Gru Kra Dur Zog Brak Ghor Mur Vol".split()
               for b in "ash gul nak rok tha mog rak zul ga dush".split()],
        surname="Bloodtusk Ironjaw Ashborn Skullsplitter Stormhowl Boneclaw Fireheart Grimhide Hornbreaker "
                "Mountainfist Sharpaxe Warbringer".split(),
        epithet=["the Unbroken", "Scarred", "Wolfbane", "Oathkeeper", "the Hungry", "Stonefist", "Ironvoice"],
        place=["Blackcrag", "Redmaw", "Thunderpeak"]),
    "halfling": dict(
        given="Pip Wil Tam Bel Fen Nim Rosa Cob Lil Merry Posy Perry Hob Daisy Sam Tilly Wick Bramble Dilly "
              "Finch Hattie Jory Lark Mabs Nib Opal Pimm Quince Rudd Tuck Wren".split(),
        surname="Underbough Thistledown Hearthfoot Quickwhistle Tealeaf Applewood Brandybrook Burrows Goodbarrel "
                "Greenbottle Hayfoot Longbottom Proudfoot Rushlight Sweetwater Tumbletoe".split(),
        epithet=["the Second", "Tinkerpot", "Bigpocket", "Merrilegs", "Peacemaker", "Fiddlesticks"],
        place=["Little Bramble", "Teapot Hill", "Cloverdown", "Wickerby"]),
    "gnome": dict(
        given=[a + b for a in "Fen Quin Bim Zan Nib Wiz Pof Gim Ori Tal Lum Dab".split()
               for b in "wick dle bo ra pip zibble nick ble sy mor".split()],
        surname="Quillgrass Fizzlewhistle Tinkerbell Gearwhisper Brightspark Copperkettle Dapplewing Glimmerpot "
                "Nettlethorn Oddsprocket Puddlejump Whirligig".split(),
        epithet=["the Curious", "Sparkfingers", "Inkblot", "the Distracted", "Threefold", "Bright-Eyes"],
        place=["Glimmerhollow", "Tinkers' Rest", "Puddlewick"]),
    "kobold": dict(
        given=[a + b for a in "Ik Zit Vrek Kez Sniv Tik Rax Yip Skrit Nik Gek Pyt".split()
               for b in "ik ak et a ix ir".split()],
        surname="Tunnelbiter Trapwise Cinderscale Clawsharp Dartwhistle Stonecrawl Rustscale Quickburrow "
                "Hissbright Gravelgut Chiselwise Mortarhand Plumbline Archwright Levelhead Keystone".split(),
        epithet=["Trapmaker", "the Small", "Dragon's Own", "Quiet-Claw", "Eggwatcher", "Nine-Traps"],
        place=["the Warrens", "Cinder Deep"]),
    "ratfolk": dict(
        given=[a + b for a in "Ves Tix Nib Rix Mil Pru Quil Sniv Fen Tor Ysk Dib".split()
               for b in "k ka it el a ik ra ix".split()],
        surname="Whiskerwise Softpaw Tailtwist Quietfoot Lockwhisker Routewise Chalkmark Sidestep Hushpaw Keyring "
                "Nimblewick Dimlantern Cornerwise Longtail".split(),
        epithet=["the Quiet", "Two-Routes", "Who Was Not There", "Softstep", "the Courier", "of the Third Route",
                 "Keyholder"],
        place=["the Hushwarrens", "the Lower Routes"]),
    "grippli": dict(
        given=[a + b for a in "Brak Ploo Quen Mirr Glop Fenn Ribb Tweel Splo Dree".split()
               for b in "a ik o ee wa ol".split()],
        surname="Stillpond Reedwater Lilyleap Mudcrest Dripcreek Tadpoolsong Fernbank Mistwhistle Bogwise "
                "Rippleback".split(),
        epithet=["the Patient", "Sluice-Keeper", "Wet-Footed", "Deepwater", "the Steady", "Who Listens to Water"],
        place=["Stillwater Hollow", "the Waterways"]),
    "leshy": dict(
        given="Mossa Bracken Thistle Fennel Sorrel Burdock Lichen Morel Truffle Yarrow Sedge Clover Hazel Rowan "
              "Alder Bramble Nettle Tansy Yew Spindle Fern Cress Moxie Puffball Chanterelle Ink-Cap Hollyhock Teasel "
              "Vetch Maple Sprout Burr Gorse Mullein Sundew Horsetail Linden Lungwort".split(),
        surname="Underroot Glowcap Barkhand Rootknot Deepgrowth Sporefall Loamfoot Twiggish Mycelwise "
                "Greenhollow".split(),
        epithet=["the Slow-Growing", "of the Long Root", "Who Remembers Rain", "the Sprouting", "Light-Hungry",
                 "Deep-Rooted"],
        place=["the Quiet Ring", "the Root Halls"],
        patterns=[("{given}", 45), ("{given} {surname}", 25), ("{given} {epithet}", 20), ("{given} of {place}", 10)]),
    "arboreal": dict(
        given="Oakhand Ashwyn Birchen Hollin Elmstead Larchwood Cedran Willowen Aspen Pinewick Alderon "
              "Beechwarden".split(),
        surname="Heartwood Barkwise Rootholder Longgrain Knotted Highcanopy".split(),
        epithet=["the Elder", "Slow-Speaker", "of the Third Ring", "Who Waits for Spring"],
        place=["the Quiet Ring"],
        patterns=[("{given}", 40), ("{given} {surname}", 30), ("{given} {epithet}", 25), ("{given} of {place}", 5)]),
    "construct": dict(
        given="Stitch Pip Rivet Tack Cog Bolt Patch Mend Gasket Sprocket Button Thimble Hinge Bracket Washer Latch "
              "Spool Rung Shim Brace Cotter Grommet Pinion Splint Darn Hem Seam Needle Clasp Lug Buckle Tuck Bobbin "
              "Stay Ferrule".split(),
        surname=["Mark Two", "Rewound", "Sewn-Twice", "Patched", "Salvage-Born", "Re-Stitched", "Third-Hand",
                 "Reseated"],
        epithet=["Who Remembers", "the Reassembled", "of Many Hands", "Still Ticking", "the Kept"],
        place=["the Mending", "the Workshop Rows"],
        patterns=[("{given}", 55), ("{given} {epithet}", 25), ("{given} {surname}", 12), ("{given} of {place}", 8)]),
    "awakened": dict(
        given="Nib Tuft Burr Whisk Sniff Dapple Thimble Clover Peep Scrabble Nutmeg Twitch Squeak Bristle Tansy Fidget "
              "Pocket Crumb Wren Mote Flint Pebble Snuffle Hop Skitter Bramble Thorn Nettle".split(),
        surname=["Firstwake", "Newly-Woken", "Quickthought", "Wide-Eyed", "Many-Questions"],
        epithet=["Who Asks Questions", "the Newly Woken", "Who Counts Things", "Who Cannot Stop Thinking",
                 "First of the Burrow"],
        place=["Firstlight", "the Glow"],
        patterns=[("{given}", 50), ("{given} {epithet}", 30), ("{given} {surname}", 12), ("{given} of {place}", 8)]),
    "scifi": dict(
        given=[a + b for a in "Kor Zev Tal Vex Ix Qua Ryx Sol Tor Xan Nyx Orv Dax Ulu".split()
               for b in "ix ara ok eth un ira osk ael ex ul".split()],
        surname="Vrask Kel-Varo Nine-Spire Orrin Tal-Mereth Solanis Dax-Rym Ulendra Brightstar Vask-Hael "
                "Orbital Hollowsun".split(),
        epithet=["of Clan Vrask", "Drift-Born", "the Navigator", "Void-Singer", "Stationborn"],
        place=["Absalom Reach", "Ring Seven", "the Drift"]),
}
STYLE_OF = {"dwarf": "dwarf", "elf": "elf", "goblin": "goblin", "hobgoblin": "goblin", "orc": "orc", "gnoll": "orc",
            "halfling": "halfling", "gnome": "gnome", "ratfolk": "ratfolk", "leshy": "leshy", "shoony": "halfling",
            "grippli": "grippli", "ysoki": "halfling", "skittermander": "gnome", "kobold": "kobold",
            "arboreal": "arboreal", "automaton": "construct", "poppet": "construct", "awakened animal": "awakened",
            "awakened-animal": "awakened",
            "vesk": "scifi", "kasatha": "scifi", "lashunta": "scifi", "shirren": "scifi", "pahtra": "scifi",
            "barathu": "scifi", "android": "scifi"}
PATTERNS = [("{given} {surname}", 58), ("{given} {epithet}", 22), ("{given}", 9), ("{given} of {place}", 7),
            ("{given} {surname} {epithet}", 4)]


# Names that belong to established characters. A generated name never uses them, so a random goblin is never
# "Kraggix" and a random kobold is never a Stonebender.
RESERVED_GIVEN = {"kraggix", "skritch", "vesk", "verdara", "stitch", "pip", "brakka", "ulzerett", "liza", "urist",
                  "orion", "malcior", "khazuk", "jorun", "greywing", "karak", "patch"}
RESERVED_SURNAME = {"scraptooth", "stonebender", "quickwhisker", "herkroft", "mossleap", "eremor", "palend", "veyndor",
                    "foretalon", "dourrunner", "deepcurrent", "verdantroot"}


def reserved(name):
    words = {w.strip(",.").lower() for w in str(name).split()}
    return bool(words & (RESERVED_GIVEN | RESERVED_SURNAME))


def make_name(ancestry="Human", rng=None, style=None):
    """A name for the ancestry. Homebrew ancestries use the human style unless `style` is given."""
    rng = rng or random.Random()
    key = style or STYLE_OF.get(str(ancestry).strip().lower(), "human")
    pool = STYLES.get(key, STYLES["human"])
    patterns = pool.get("patterns", PATTERNS)
    name = ""
    for _ in range(25):
        pattern = rng.choices([p for p, _ in patterns], weights=[w for _, w in patterns], k=1)[0]
        parts = {"given": rng.choice(pool["given"]), "surname": rng.choice(pool["surname"]),
                 "epithet": rng.choice(pool["epithet"]), "place": rng.choice(pool["place"])}
        name = pattern.format(**parts)
        if not reserved(name):
            break
    return name

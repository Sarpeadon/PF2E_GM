"""Hazards and afflictions for the GM Tools tab: underground hazards with a stat block built from the level tables, and curses,
diseases and poisons in the book format with a silly cure.

Numbers: DCs come from the DC by level table (quickref.py, gmtables.py). Hazard and affliction damage comes from the Area Damage
table in gmtables.py: the limited-use column for a hazard that goes off once, the unlimited-use column for one that acts every
round, and two levels lower when the effect also applies a condition (GM Core, Damage-Dealing Abilities). AC is the High AC for
the level. Hazard XP is in rules.py. Tuning, not book rules: the stage shapes of the afflictions, and "one stat is very hard
(+5)" on a hazard.

The wording tables (hazard.bp, hazard.clue, hazard.twist, aff.cure) are ordinary Story Forge tables, so Edit Tables changes them.
hazard.bp lists which blueprint below a hazard can be built from; a line's silliness (s2, s3) decides when it can come up.
"""
import random

from . import gmtools as gt
from .gmtables import area_damage, high_ac
from .rules import hazard_xp

TABLES = {}


def table(name, title, text):
    TABLES[name] = {"title": title, "entries": [ln.strip() for ln in text.strip().splitlines()
                                                if ln.strip() and not ln.strip().startswith("#")]}


table("hazard.bp", "Hazard blueprints (keys)", """
carts
mushroom_stairs
door|||s2
choir|||s2
lift|||s2
collapse
flood
crystal
darts
powder
tripwire
spores
bridge
net|||s2
gate||2|s3
glove||2|s3
hatstand||2|s3
""")

table("hazard.clue", "Hazard clues", """
an unusually well-fed rat is sitting very still
the dust on the floor has been swept in a suspiciously neat line
a faint smell of something sweet and wrong
a small pile of boots, left by someone who got away
a tin sign reading PLEASE USE THE OTHER ONE
a goblin has scratched DON'T into the wall, then, in different writing, DO
fresh scrapes on the walls at ankle height
a very old lantern, set down carefully and never retrieved
a mouse skeleton wearing a tiny hat|||s2
a neatly lettered notice that begins "Management accepts no responsibility"|||s2
a goat that will not walk past this spot|||s2
the echo here comes back a little late, and a little rude||2|s3
""")

table("hazard.twist", "Hazard twists", """
the hazard is polite and announces itself a moment before it goes off
the hazard resets itself, loudly, with a small flourish
a note nearby explains how to disable it, and is wrong
someone has put a very small chair next to it
the hazard has a custodian who will come to complain about the damage
the hazard stops if you say please, but only the first time|||s2
the hazard is, on closer inspection, a very elaborate way of locking a cupboard|||s2
it has been trapped since a prank that got out of hand, and the pranksters are still waiting for someone to fall in||2|s3
""")

table("aff.cure", "Affliction folk cures", """
a sincere apology to a goose
a night's sleep in a clean bed, with the window open
a good, long laugh at your own expense
three days of nothing but plain porridge
a bath in water that has been blessed by a very tired priest
holding hands with someone you dislike for an hour
a visit to the person who gave it to you, to say sorry
a dramatic reading of your own will|||s2
a slice of cheese, eaten in silence at midnight|||s2
an apology to the thing you stepped on||2|s3
a firm handshake with a ghost||2|s3
""")


# ================================================================================================ HAZARDS
# Each blueprint: kind (trap/environmental/haunt), mech (mechanical/magical/None), complex (True/False/None for either),
# settings, name, desc, trigger, disable skills, effect (save, dtype, condition, text), routine text, reset, extra.
BP = {
    "carts": dict(kind="trap", mech="mechanical", complex=True, tags={"tunnels", "ruin", "any"}, name="Runaway Mine Cart Line",
                  desc="A string of loose mine carts waits at the top of a slope. The brake lever is held by a rope that has seen better years.",
                  trigger="A creature steps on the rails or touches the brake lever.",
                  skills=["Thievery", "Crafting"], steps=3,
                  effect=("Reflex", "bludgeoning", "knocked prone", "The carts roar down the track. Each creature on the track must attempt a basic Reflex save; on a critical failure it is also knocked prone."),
                  routine="The carts rush through the room. Each creature in the track's path attempts a basic DC {save} Reflex save against {dmg} damage.",
                  reset="The carts must be hauled back up the slope and the brake rope retied (1 hour)."),
    "mushroom_stairs": dict(kind="environmental", mech=None, complex=False, tags={"tunnels", "fungus", "any"}, name="Staircase of Offended Mushrooms",
                  desc="Wide, damp steps covered in glossy mushrooms that release a slick cloud when stepped on, and have strong feelings about it.",
                  trigger="A creature steps on the stairs without wiping their feet.",
                  skills=["Nature", "Survival"], steps=1,
                  effect=("Reflex", "bludgeoning", "knocked prone", "The mushrooms burst in a spray of slick spores. The creature attempts a basic Reflex save; on a failure it also slides down the stairs and falls prone."),
                  reset="The mushrooms regrow in a day. They are not happy about it."),
    "door": dict(kind="trap", mech="mechanical", complex=False, tags={"ruin", "tunnels", "any"}, name="Self-Closing Door That Takes Offense",
                 desc="A heavy door fitted with a polite brass plate. It is a little too eager to close.",
                 trigger="A creature walks through without knocking.", skills=["Thievery", "Crafting"], steps=1,
                 effect=("Reflex", "bludgeoning", "knocked prone", "The door slams with a flat, offended clang. The creature attempts a basic Reflex save; on a failure it is also off-guard until the end of its next turn."),
                 reset="Reopens on its own after a minute, with an air of forgiveness."),
    "choir": dict(kind="haunt", mech=None, complex=True, tags={"tunnels", "fungus", "ruin", "any"}, name="Fungal Choir",
                  desc="A cluster of pale, bell-shaped mushrooms hums a soft, rising chord. The longer you listen, the more it sounds like your own name.",
                  trigger="A creature lingers for more than a breath within 30 feet.",
                  skills=["Occultism", "Performance"], steps=3,
                  effect=("Will", "mental", "stupefied 1", "The chorus swells. Each creature within 30 feet attempts a basic Will save; on a failure it is also stupefied 1 for 1 minute."),
                  routine="The choir sings a new verse. Each creature within 30 feet attempts a basic DC {save} Will save against {dmg} damage. On a failure the creature is stupefied 1 (or 2 on a critical failure) for 1 minute.",
                  reset="The choir takes a breath and begins again after 1 hour."),
    "lift": dict(kind="trap", mech="mechanical", complex=True, tags={"tunnels", "ruin", "any"}, name="Overly Helpful Lift",
                 desc="A rattling mine lift that wants to be useful. It tends to take people to the wrong level, then drop them off in a hurry.",
                 trigger="A creature steps on the lift platform.", skills=["Crafting", "Thievery"], steps=3,
                 effect=("Reflex", "bludgeoning", "knocked prone", "The lift lurches. Each creature on the platform attempts a basic Reflex save."),
                 routine="The lift rattles to a new level and stops short. Each creature on the platform attempts a basic DC {save} Reflex save against {dmg} damage from the sudden stop.",
                 reset="The lift can be restarted with a good oil and a better apology."),
    "collapse": dict(kind="environmental", mech=None, complex=False, tags={"tunnels", "ruin", "any"}, name="Weak Tunnel Section",
                     desc="Timber braces sag along a stretch of the tunnel, held up by dust and optimism.",
                     trigger="A loud noise, or a creature in the central span.", skills=["Survival", "Athletics"], steps=1,
                     effect=("Reflex", "bludgeoning", "immobilized", "The ceiling lets go. Creatures in the section attempt a basic Reflex save; on a failure they are also immobilized under the rubble until freed (Athletics against the Disable DC)."),
                     reset="Does not reset. Which is fine, because there is less tunnel to fall from now."),
    "flood": dict(kind="environmental", mech=None, complex=True, tags={"tunnels", "flooded", "any"}, name="Surging Culvert",
                  desc="A cracked pipe over a low gallery. Water drips, then does not.",
                  trigger="A creature disturbs the pipe, or the pipe feels like it.", skills=["Athletics", "Survival"], steps=3,
                  effect=("Fortitude", "bludgeoning", "knocked prone", "A wall of water surges in. Each creature attempts a basic Fortitude save; on a failure it is swept 10 feet."),
                  routine="The water surges higher. Each creature in the gallery attempts a basic DC {save} Fortitude save against {dmg} damage and is swept 10 feet on a failure.",
                  reset="The pipe must be sealed, and the gallery pumped out (several hours)."),
    "crystal": dict(kind="environmental", mech=None, complex=False, tags={"tunnels", "crystal", "ruin", "any"}, name="Crystal Bloom Burst",
                    desc="A cluster of glassy crystals hums at a pitch you feel in your teeth. It has been growing for years, and it is full.",
                    trigger="A creature touches it, or sings louder than a murmur.", skills=["Nature", "Athletics"], steps=1,
                    effect=("Reflex", "piercing", "dazzled", "The crystal shatters outward. Each creature within 10 feet attempts a basic Reflex save; on a failure it is also dazzled for 1 round."),
                    reset="Regrows over several weeks, slowly and smugly."),
    "darts": dict(kind="trap", mech="mechanical", complex=False, tags={"ruin", "tunnels", "any"}, name="Welcome Sign Dart Panel",
                  desc="A hand-painted WELCOME sign above a row of tiny holes. The paint is fresh, which is the suspicious part.",
                  trigger="A creature touches the sign or the door beneath it.", skills=["Thievery", "Crafting"], steps=1,
                  effect=("Reflex", "piercing", None, "Darts fire from the holes. The creature in the doorway attempts a basic Reflex save."),
                  reset="Reload the darts (1 minute). The sign needs touching up too."),
    "powder": dict(kind="trap", mech="mechanical", complex=False, tags={"ruin", "tunnels", "any"}, name="Sneeze Powder Trap",
                   desc="A pressure plate and a smear of fine, sweet-smelling powder around a covered vent.",
                   trigger="A creature steps on the pressure plate.", skills=["Thievery", "Crafting"], steps=1,
                   effect=("Fortitude", "poison", "sickened 1", "A puff of powder bursts from the vent. Each creature within 10 feet attempts a basic Fortitude save; on a failure it is also sickened 1 from the sneezing."),
                   reset="Refill the vent (10 minutes)."),
    "tripwire": dict(kind="trap", mech="mechanical", complex=False, tags={"ruin", "tunnels", "any"}, name="Tin Can Tripwire",
                     desc="A thin wire at ankle height, strung with tin cans and spoons. It is much more about the noise than the harm.",
                     trigger="A creature crosses the wire.", skills=["Thievery", "Perception"], steps=1,
                     effect=("Reflex", "bludgeoning", "alarm", "The cans clatter. Creatures within 120 feet notice the noise. The creature attempts a basic Reflex save against a falling bucket."),
                     reset="Restring the wire and reset the cans (1 minute)."),
    "spores": dict(kind="environmental", mech=None, complex=False, tags={"tunnels", "fungus", "any"}, name="Spore Puffball Cluster",
                   desc="A bulging patch of fungus the color of old milk. It breathes out slowly, then, when startled, all at once.",
                   trigger="A creature steps within 5 feet.", skills=["Nature", "Survival"], steps=1,
                   effect=("Fortitude", "poison", "sickened 1", "The puffballs burst in a choking cloud. Each creature within 10 feet attempts a basic Fortitude save; on a failure it is also sickened 1."),
                   reset="The puffballs regrow in a few days."),
    "bridge": dict(kind="environmental", mech=None, complex=False, tags={"tunnels", "ruin", "any"}, name="Rotting Rope Bridge",
                   desc="A bridge of old rope and older planks across a drop that does not report back.",
                   trigger="A creature in the middle of the span, or a second creature behind them.", skills=["Athletics", "Survival"], steps=1,
                   effect=("Reflex", "bludgeoning", "falling", "The planks give way. Creatures on the bridge attempt a basic Reflex save; on a failure they fall. On a success they catch themselves."),
                   reset="Does not reset. It has now given up on the entire idea."),
    "net": dict(kind="trap", mech="mechanical", complex=False, tags={"ruin", "tunnels", "any"}, name="Goblin Safety Net",
                desc="A pile of netting tucked into the ceiling and a hand-lettered sign that reads: FOR YOUR SAFETY. The sign is the trap.",
                trigger="A creature reads the sign.", skills=["Thievery", "Crafting"], steps=1,
                effect=("Reflex", None, "immobilized", "The net drops. The creature attempts a Reflex save; on a failure it is immobilized until freed (Athletics or Acrobatics against the Disable DC). Nearby creatures hear the bells."),
                reset="Rehang the net (10 minutes)."),
    "gate": dict(kind="haunt", mech=None, complex=True, tags={"ruin", "any"}, name="The Bureaucratic Gate",
                 desc="A stone arch with a ledger on a stand. The ledger wants forms, and the forms want forms.",
                 trigger="A creature attempts to pass through the arch.", skills=["Society", "Diplomacy", "Deception"], steps=3,
                 effect=("Will", "mental", "slowed 1", "A queue forms from nowhere. Each creature near the arch attempts a basic Will save; on a failure it is also slowed 1 for 1 round."),
                 routine="The ledger requests a form. Each creature within 20 feet attempts a basic DC {save} Will save against {dmg} damage and is slowed 1 for 1 round on a failure.",
                 reset="The ledger starts over. It has done this before."),
    "glove": dict(kind="trap", mech="mechanical", complex=False, tags={"ruin", "tunnels", "any"}, name="Spring-Loaded Boxing Glove",
                  desc="A hand-painted wall panel that reads PUSH. Behind it is a very large spring and a very large glove.",
                  trigger="A creature pushes the panel.", skills=["Thievery", "Crafting"], steps=1,
                  effect=("Reflex", "bludgeoning", "knocked prone", "The glove springs out. The creature attempts a basic Reflex save; on a failure it is also knocked 10 feet and prone."),
                  reset="Compress the spring (10 minutes, two people)."),
    "hatstand": dict(kind="haunt", mech=None, complex=False, tags={"ruin", "any"}, name="Haunted Hat Stand",
                     desc="A coat rack by the door. It greets every visitor by name and suggests, kindly, that they leave.",
                     trigger="A creature enters the room wearing a hat.", skills=["Religion", "Occultism", "Diplomacy"], steps=1,
                     effect=("Will", "mental", "frightened 1", "The coat rack turns, slowly, to face the intruder. The creature attempts a basic Will save; on a failure it is also frightened 1."),
                     reset="Resets after a quiet hour. It never forgets a face, or a hat."),
}

HAZARD_SETTINGS = ["Any", "Tunnels", "Fungus", "Crystal", "Flooded", "Ruin"]
HAZARD_OPTIONS = [
    gt.opt("kind", "Kind", "choice", "Any", ["Any", "Trap", "Environmental", "Haunt"], width=13),
    gt.opt("complexity", "Complexity", "choice", "Any", ["Any", "Simple", "Complex"], width=9),
    gt.opt("setting", "Setting", "choice", "Any", HAZARD_SETTINGS, width=10),
    gt.LEVEL_OPT,
    gt.opt("offset", "Hazard level vs party", "choice", "0", ["-2", "-1", "0", "+1", "+2", "+3"], width=5),
    gt.SILLY_OPT, gt.FLAVOR_OPT]


def _pick_bp(rl, params):
    pool = [t for t in rl.eligible("hazard.bp") if t in BP]
    out = []
    for key in pool:
        bp = BP[key]
        if params["kind"] != "Any" and bp["kind"] != params["kind"].lower():
            continue
        if params["complexity"] == "Simple" and bp["complex"]:
            continue
        if params["complexity"] == "Complex" and not bp["complex"]:
            continue
        s = params["setting"].lower()
        if s != "any" and s not in bp["tags"]:
            continue
        out.append(key)
    if not out:                       # relax the setting, then the kind
        out = [t for t in pool if params["kind"] == "Any" or BP[t]["kind"] == params["kind"].lower()]
    if not out:
        out = pool or list(BP)
    return rl.choice(out)


def _adjust(rng, picks=("normal", "normal", "hard", "easy")):
    return rng.choice(picks)


def build_hazard(rl, params):
    rng = rl.rng
    plevel = gt.clamp(params["level"], 1, 20)
    off = int(str(params["offset"]).replace("+", ""))
    level = gt.clamp(plevel + off, -1, 24)
    key = _pick_bp(rl, params)
    bp = BP[key]
    cx = bp["complex"] if params["complexity"] == "Any" or bp["complex"] is None else (params["complexity"] == "Complex")
    save_name, dtype, cond, effect_text = bp["effect"]
    standout = rng.choice(["stealth", "disable", "save"])         # tuning: one stat is very hard (+5)
    stealth = gt.dc(level, 5 if standout == "stealth" else _adjust(rng))
    disable = gt.dc(level, 5 if standout == "disable" else _adjust(rng, ("normal", "easy", "hard")))
    save = gt.dc(level, 5 if standout == "save" else _adjust(rng, ("normal", "normal", "hard")))
    skills = bp["skills"][:2]
    steps = bp["steps"] if cx else 1
    # damage: limited-use column for a one-shot trap, unlimited-use for a routine; two levels lower with a condition
    dmg_level = level - (2 if cond and cond not in ("alarm",) else 0)
    dice, avg = area_damage(dmg_level, limited=not cx) if dtype else ("", 0)
    if cx and dtype:
        dice, avg = area_damage(dmg_level - 1, limited=False)    # a single routine action is lighter than a 2-action ability
    dmg = f"{dice} {dtype}" if dtype else "no damage"
    traits = [bp["kind"].title()]
    if bp["mech"]:
        traits.append(bp["mech"].title())
    traits.append("Complex" if cx else "Simple")
    head = f"{bp['name']}   Hazard {level}"
    stealth_text = f"Stealth +{stealth - 10} (DC {stealth})" if cx else f"Stealth DC {stealth}"
    lines = [head, f"Traits: {', '.join(traits)}", stealth_text, f"Description: {bp['desc']}"]
    disable_bits = " or ".join(f"{s} DC {disable + (2 if i else 0)}" for i, s in enumerate(skills))
    lines.append(f"Disable: {disable_bits}" + (f" ({steps} successes)" if steps > 1 else ""))
    lines.append(f"AC {high_ac(level)} (high for level); saving throws: as needed. Hardness and HP: set from the Building Hazards table in GM Core.")
    lines.append(("Trigger: " if cx else "Reaction [reaction] Trigger: ") + bp["trigger"])
    sev = {"Reflex": "Reflex", "Fortitude": "Fortitude", "Will": "Will"}[save_name]
    eff = effect_text
    if dtype:
        eff = eff.replace("basic " + sev + " save", f"basic DC {save} {sev} save against {dmg} damage").replace(f"{dmg} damage damage", f"{dmg} damage")
        if "basic DC" not in eff:
            eff += f" (DC {save} basic {sev} save, {dmg})"
    else:
        eff += f" (DC {save} {sev} save)"
    if cx:                                   # a complex hazard's effect is only the start: it rolls initiative, then runs its routine
        first = effect_text.split(". ")[0].rstrip(".") + "."
        lines.append(f"Effect: {first} The hazard rolls initiative using its Stealth modifier.")
    else:
        lines.append(f"Effect: {eff}")
    if cx and bp.get("routine"):
        lines.append("Routine (1 action): " + bp["routine"].format(save=save, dmg=dmg))
    lines.append(f"Reset: {bp['reset']}")
    xp = hazard_xp(level, plevel, cx)
    lines.append(f"XP: {xp} XP for a party of level {plevel}" + ("" if xp else " (trivial)") + f" ({'complex' if cx else 'simple'} hazard).")
    block = "\n".join(lines)
    rows = [gt.row("Hazard", block, "block", level=level, complex=cx)]
    rows.append(gt.row("Clue the party can find", rl.roll("hazard.clue"), "clue", table="hazard.clue", fmt="{}", gm=False))
    rows.append(gt.row("Twist", rl.roll("hazard.twist"), "clue", table="hazard.twist", fmt="{}", gm=True))
    rows.append(gt.row("Design note", f"Damage comes from the GM Core Area Damage table ({'limited-use' if not cx else 'unlimited-use, one level lower for a single action'}"
                    f"{', two levels lower because of the condition' if cond and cond != 'alarm' else ''}). One statistic ({standout}) is set very hard (+5), "
                    "since most hazards have one extreme value.", "info", gm=True))
    return gt.result("hazards", f"Hazard: {bp['name']} (level {level})", rows, params)


def generate_hazards(params, rng=None):
    rng = rng or random.Random()
    rl = gt.Roller(rng, params["silly"], params["flavor"], params["level"])
    return build_hazard(rl, params)


TOOL_HAZARDS = {"key": "hazards", "label": "Hazards", "page_type": "Note", "options": HAZARD_OPTIONS, "generate": generate_hazards, "single": True,
                "intro": "Underground hazards with a stat block built from the level tables. Complex hazards get a routine."}


# ================================================================================================ AFFLICTIONS
# name, type, save, damage type (or None), (condition A, valued?), (condition B, valued?), stage flavors, climax, via
AFFLICTIONS = [
    ("Goose Fever", "disease", "Fortitude", None, ("sickened", True), ("stupefied", True),
     ["Your sneezes come out as small, startled geese. They leave.", "Honking is involuntary and the geese arrive in pairs.",
      "You waddle, you honk, and you cannot resist a pond."], "you become a goose for 1 hour", "a cough, a cold, a bad goose"),
    ("Sock Rot", "disease", "Fortitude", None, ("clumsy", True), ("sickened", True),
     ["One sock goes missing, and so does its partner.", "Your feet leave faint, mournful footprints.",
      "Every pair of socks within ten feet gives up and walks away."], "your boots stop fitting, on principle", "damp boots"),
    ("Mushroom Mumps", "disease", "Fortitude", None, ("enfeebled", True), ("clumsy", True),
     ["Your cheeks sprout very small, polite caps.", "The caps release a soft cloud whenever you speak.",
      "You are, for all useful purposes, a mushroom with opinions."], "you cannot leave the damp for a day", "a bad mushroom"),
    ("Bardic Itch", "disease", "Fortitude", None, ("stupefied", True), ("off-guard", False),
     ["You cannot stop humming a tune nobody has heard.", "Your hands drift into a rhythm on any surface.",
      "You break into verse, and you do not know the last line."], "you must finish the song to be heard again", "an overlong ballad"),
    ("The Wobbles", "disease", "Fortitude", None, ("clumsy", True), ("off-guard", False),
     ["Your knees feel agreeable, in the wrong way.", "Walking in a straight line is a conversation.",
      "Every step is a small negotiation with the floor."], "you cannot stand without help for an hour", "bad stairs"),
    ("Pun Plague", "disease", "Will", "mental", ("stupefied", True), ("off-guard", False),
     ["Every sentence tries to end in a pun.", "You cannot stop yourself from punning, and others cannot stop themselves from groaning.",
      "You can only communicate in puns, and you are very proud of that."], "you can only speak in puns for a day", "a bard, a bar, and a bad idea"),
    ("Curse of the Squeaky Voice", "curse", "Will", None, ("stupefied", True), ("frightened", True),
     ["Your voice squeaks whenever you tell a lie.", "Your voice squeaks, always, and everyone can hear you try to be serious.",
      "Your voice is a very small, very sincere whistle."], "you cannot speak above a whisper for a day", "a rude word to a statue"),
    ("Curse of Rightful Ownership", "curse", "Will", None, ("clumsy", True), ("stupefied", True),
     ["Anything you carry that does not belong to you begins to tug away.", "Your pack wanders in the night, back to where it came from.",
      "Everything you own wants to go home, and so does everything you do not."], "every item you hold tries to leave you", "a very small theft"),
    ("Curse of the Dutiful Echo", "curse", "Will", None, ("stupefied", True), ("off-guard", False),
     ["A small, polite voice repeats everything you say, a second later.", "The echo adds a helpful correction.",
      "The echo starts to say things you did not."], "the echo starts leading the conversation", "a shout into a well"),
    ("Curse of the Missing Left Shoe", "curse", "Will", None, ("clumsy", True), ("sickened", True),
     ["Your left shoe is missing each dawn, and returns before dusk, somewhat insulted.", "Your left shoe starts arriving wet.",
      "Your left shoe leaves, and returns with the right one's friends."], "you cannot wear shoes for a day", "a kick at a stranger's hat"),
    ("Giggle Dust", "poison", "Fortitude", "mental", ("off-guard", False), ("stupefied", True),
     ["You giggle at nothing, then at something.", "The giggling is contagious, and the object of it is you.",
      "You cannot stop laughing, and you cannot remember the joke."], "you laugh until you cannot stand", "a pinch on the nose"),
    ("Snore Berry Tincture", "poison", "Fortitude", None, ("slowed", True), ("fatigued", False),
     ["Your eyelids feel like very nice curtains.", "Your thoughts begin to sound like a lullaby.",
      "You are asleep on your feet, and your feet are happy."], "you fall into a deep, snoring sleep", "a sweet little bottle"),
    ("Spicy Tongue Venom", "poison", "Fortitude", "fire", ("sickened", True), ("clumsy", True),
     ["Your tongue tingles like a very small, very angry bonfire.", "You breathe small sparks, and everyone nearby decides to step back.",
      "Your mouth is the hottest thing in the room."], "you cannot taste anything for a week", "a dish too ambitious"),
    ("Sneeze Powder", "poison", "Fortitude", "poison", ("sickened", True), ("clumsy", True),
     ["Your nose twitches, then announces itself.", "You sneeze, and the sneeze has its own agenda.",
      "You cannot stop sneezing, and every sneeze is a surprise."], "you sneeze so hard you move 5 feet", "a puff of fine powder")]
AFF_TYPES = ["Any", "Curse", "Disease", "Poison"]
AFF_OPTIONS = [
    gt.opt("type", "Type", "choice", "Any", AFF_TYPES, width=9),
    gt.opt("severity", "Severity", "choice", "Standard", ["Nuisance", "Standard", "Nasty"], width=10),
    gt.opt("level", "Affliction level", "int", 3, width=5),
    gt.opt("count", "How many", "int", 3, width=4),
    gt.SILLY_OPT, gt.FLAVOR_OPT]
AFF_SEV = {"Nuisance": ("easy", 2), "Standard": ("normal", 3), "Nasty": ("hard", 4)}


def _cond_text(cond, valued, value):
    return f"{cond} {value}" if valued else cond


def build_affliction(rl, level, severity, kind, bp=None):
    rng = rl.rng
    if bp is None:
        pool = [a for a in AFFLICTIONS if kind == "Any" or a[1] == kind.lower()]
        bp = rng.choice(pool)
    name, typ, save, dtype, (ca, va), (cb, vb), flav, climax, via = bp
    adj, n_stages = AFF_SEV.get(severity, AFF_SEV["Standard"])
    dc = gt.dc(level, adj)
    save_name = save
    if typ == "poison":
        onset = rng.choice(["", "1 round", "1 minute"])
        maxdur = "6 rounds"
        interval = "1 round"
    elif typ == "disease":
        onset = rng.choice(["1 hour", "1d4 hours", "1 day"])
        maxdur = ""
        interval = "1 day"
    else:
        onset = rng.choice(["", "", "until the next sunrise"])
        maxdur = ""
        interval = "1 day"
    stages = []
    for i in range(1, n_stages + 1):
        conds = []
        if i == 1:
            conds.append(_cond_text(ca, va, 1))
        elif i == 2:
            conds.append(_cond_text(ca, va, 2 if n_stages > 2 else 1))
            if n_stages == 2:
                conds.append(_cond_text(cb, vb, 1))
        elif i == 3:
            conds += [_cond_text(ca, va, 2), _cond_text(cb, vb, 1)]
        else:
            conds += [_cond_text(ca, va, 3), _cond_text(cb, vb, 2)]
        dmg = ""
        if dtype and not (severity == "Nuisance" and i == 1):
            dice, avg = area_damage(level - 5 + i, limited=False)         # conditions apply: damage is lowered by two or more levels
            dmg = f"{dice} {dtype} damage and "
        text = f"{dmg}{' and '.join(conds)} ({interval})"
        stages.append((i, text))
    head = f"{name} ({typ}){'' if typ else ''}   Level {level}"
    parts = [f"Saving Throw DC {dc} {save_name}"]
    if onset:
        parts.append(f"Onset {onset}")
    if maxdur:
        parts.append(f"Maximum Duration {maxdur}")
    parts += [f"Stage {i} {t}" for i, t in stages]
    mech = "; ".join(parts) + "."
    cure_silly = rl.roll("aff.cure")
    rank = gt.clamp((level + 1) // 2, 1, 10)
    block = "\n".join([head, mech,
                       f"Spread by: {bp[8]}.",
                       f"Remove: counteract at rank {rank} (counteract level {level}), or {cure_silly}. The folk cure ends it only if the GM agrees it was sincere."])
    flavors = list(flav) + [gt.sentence(climax)]
    story = "\n".join(f"Stage {i}: {flavors[min(i - 1, len(flavors) - 1)]}" for i in range(1, n_stages + 1))
    return name, block, story, typ


def generate_afflictions(params, rng=None):
    rng = rng or random.Random()
    rl = gt.Roller(rng, params["silly"], params["flavor"], params["level"])
    level = gt.clamp(params["level"], 1, 20)
    count = gt.clamp(params["count"], 1, 6)
    pool = [a for a in AFFLICTIONS if params["type"] == "Any" or a[1] == params["type"].lower()]
    chosen = rng.sample(pool, min(count, len(pool)))
    while len(chosen) < count:
        chosen.append(rng.choice(pool))
    rows = []
    for bp in chosen:
        name, block, story, typ = build_affliction(rl, level, params["severity"], params["type"], bp)
        rows.append(gt.row(name, block, "block", player=story, tag="affliction"))
        rows.append(gt.row(f"{name}: what the players notice", story, "block", tag="flavor"))
    note = ("Damage comes from the GM Core Area Damage table (unlimited-use column), set below the affliction's level because each stage "
            "also applies a condition. Stage shapes are tuned here, not taken from a book.")
    rows.append(gt.row("Design note", note, "info", gm=True))
    return gt.result("afflictions", f"Afflictions: {params['severity'].lower()}, level {level}", rows, params)


TOOL_AFFLICTIONS = {"key": "afflictions", "label": "Afflictions", "page_type": "Note", "options": AFF_OPTIONS, "generate": generate_afflictions,
                    "intro": "Curses, diseases and poisons in the book format. The cure is silly; the numbers are not."}

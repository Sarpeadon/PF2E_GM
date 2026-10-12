"""Built-in content for the Downtime tab: a job board for Earn Income and tables of downtime events, and the wording the GM Tools
notice board and Quest Builder share (silly tasks, places, parcels, signs). Plain Story Forge
tables (text | tags | weight | needs | not; see storydata.py), so Edit Tables works on them.

A job's tags say how to use it:
    sk:crafting  sk:alcohol-lore  sk:performance ...   the skill it can be done with (more than one is fine; a skill ending
                                                       in -lore is a Lore: sk:alcohol-lore means Lore (Alcohol))
    tl:-1  tl:+1                                       its task level compared with the job board level you set (default 0)
    f:finders_keep                                     the Notebook faction or place it belongs to (page title in lowercase
                                                       with underscores); a job with no f: tag can be had anywhere
The skills named for each job are suggestions. Player Core leaves the choice of skill and the task level to the GM.
Lines tagged p:hallowmead are limited to the Hallowmead content pack.

The event tables paraphrase the downtime event ideas in GM Core, and the Treasure Vault (Remastered) crafting events. The
Treasure Vault prompts below were written from the event names; check the book for its official text.
"""
import re

TABLES = {}
NEED_PREFIX = ("q:", "kind:", "busy:", "size:", "c:")


def normalize(line):
    parts = [p.strip() for p in line.split("|")]
    text, tags, needs, weight = parts[0], [], [], ""
    for item in parts[1:]:
        for tok in item.split():
            if re.fullmatch(r"\d+(\.\d+)?", tok):
                weight = tok
            elif tok.startswith(NEED_PREFIX):
                needs.append(tok)
            else:
                tags.append(tok)
    out = [text, " ".join(tags), weight, " ".join(needs)]
    while len(out) > 1 and not out[-1]:
        out.pop()
    return "|".join(out)


def table(name, title, text):
    TABLES[name] = {"title": title,
                    "entries": [normalize(ln.strip()) for ln in text.strip().splitlines()
                                if ln.strip() and not ln.strip().startswith("#")]}


def slug(text):
    """A page title as it appears in an f: tag: 'Finders Keep' becomes finders_keep."""
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").lower().strip()).strip("_")


# ============================================================ the job board
table("dt.job", "Jobs for Earn Income (any settlement)", """
Haul and stack goods for a merchant|sk:athletics|tl:-1
Copy letters and keep a small shop's accounts|sk:society
Mend clothes and cloaks for a tailor|sk:crafting|tl:-1
Guard a market stall against light fingers|sk:intimidation sk:perception|tl:-1
Tutor a merchant's child in letters and sums|sk:society sk:diplomacy
Work the harvest on a farm|sk:nature sk:farming-lore|tl:-1
Shepherd a flock to a better pasture|sk:nature sk:survival|tl:-1
Cut and set stone for a mason|sk:crafting sk:athletics
Play for a wedding or a market-day crowd|sk:performance
Tell stories or recite verse for coin|sk:performance|tl:-1
Run errands and carry messages across town|sk:athletics sk:diplomacy|tl:-1
Tend the sick in a healer's house|sk:medicine
Brew and bottle for a local brewer|sk:alcohol-lore sk:crafting
Cook for a large household|sk:cooking-lore sk:crafting
Repair a cart or a wagon|sk:crafting sk:driving-lore|tl:-1
Forge nails, hinges, and horseshoes for a smith|sk:crafting
Appraise goods for a pawnbroker|sk:society sk:crafting|tl:1
Guide travelers along a difficult road|sk:survival|tl:1
Teach a class of apprentices|sk:society sk:diplomacy|tl:1
Draft and file legal papers for a clerk|sk:legal-lore sk:society|tl:1
Escort a merchant's caravan to the next town|sk:athletics sk:survival|tl:1
Paint a sign or decorate a shopfront|sk:crafting sk:art-lore|tl:-1
Heal and tend animals on a stable|sk:nature sk:medicine|tl:-1
Dig and shore up a cellar|sk:athletics sk:crafting|tl:-1
Sell goods in a busy square, loudly|sk:diplomacy sk:performance|tl:-1
Take a turn at the oars on a river barge|sk:athletics sk:boating-lore|tl:-1
Serve as a minor official's secretary|sk:society|tl:1
Copy a library's worn books by hand|sk:society sk:scribing-lore
Gather herbs and mosses for an apothecary|sk:nature sk:survival
Teach a rich family's children an instrument|sk:performance|tl:1
""")
table("dt.job.tavern", "Jobs at an inn or tavern", """
Tend the bar for the evening rush|sk:alcohol-lore
Cook for the supper trade|sk:cooking-lore sk:crafting
Wait tables and keep the mugs full|sk:diplomacy sk:alcohol-lore|tl:-1
Play and sing for the crowd|sk:performance
Keep the books and settle the nightly takings|sk:society sk:accounting-lore|tl:1
Throw out troublemakers and keep the peace|sk:athletics sk:intimidation
Haul barrels and kegs from the cellar|sk:athletics|tl:-1
Brew a batch in the back|sk:alcohol-lore sk:crafting
Repair the furniture, the roof, and the stairs|sk:crafting|tl:-1
Clean and change the beds and rooms|sk:crafting|tl:-1
Look after the horses and the stable yard|sk:nature sk:animal-lore|tl:-1
Greet the guests and settle the rooms|sk:diplomacy|tl:-1
Carry messages between guests and the town|sk:athletics sk:diplomacy|tl:-1
Look over the patrons and keep an eye out for trouble|sk:perception sk:society
""")

# ============================================================ events
table("dt.event.earn", "Downtime events: Earn Income (general)", """
A fussy client demands change after change, and each round costs a day.
An accident at the work site puts someone in danger, and the PC is the nearest help.
Something the PC is working on becomes a fad, and demand skyrockets overnight.
A visitor is impressed by the PC's work and offers a more lucrative job in a distant place.
Conditions at the job are awful, and the other workers ask the PC to confront the bosses with them.
The bosses are doing something illegal and try to bribe the PC to look the other way.
The PC returns one morning to find that someone has tampered with the day's work.
A rival hears about the PC's good pay and starts a rumor about their work.
The employer cannot pay this week, and offers a favor or a share of the goods instead.
A stranger watches the PC work for several days, then leaves without a word.
""")
table("dt.event.performance", "Downtime events: Earn Income (Performance)", """
The show is a hit, more performances are added, and the PC is run ragged.
A rival show across town draws away the audience.
A powerful noble pays for a special performance, and demands changes to the content.
A fellow performer does not show up, but the show must go on.
A heckler turns out to be a critic whose opinion can make or break a career.
An old song the PC plays reminds someone in the audience of a person they thought was gone.
""")
table("dt.event.craft", "Downtime events: Craft (GM Core)", """
A shipment of important materials is delayed, and the PC must find out why.
The PC creates something so fine that a collector or a museum takes notice.
The PC discovers a more efficient technique for working a material, and must decide whether to share it or keep it secret.
""")
table("dt.event.craft2", "Downtime events: Craft (Treasure Vault, Remastered; prompts written from the event names)", """
Annoying interloper: a nosy relative, gossipy friend, or finicky safety inspector will not leave the workshop, and cannot be thrown out.
Banned ingredient: something the work needs has been banned or restricted in this area, and the crafter must find a way around it.
Delicate components: the batch of parts is unusually fragile, and the work needs a slow and careful hand.
Formula contradiction: two sources for the same formula disagree, and one of them must be wrong.
Infestation: pests or vermin have gotten into the workshop or the materials.
Instability within: the work shows signs of an internal flaw that will show up later if not found now.
Mutation: something about the work has begun to change on its own.
Name dependence: the work is bound to a name or an identity, and changing it causes trouble.
Natural disaster: a storm, flood, or quake threatens the workshop and everything in it.
Otherworldly interference: something from beyond has noticed the work and wants a hand in it.
Overwhelming energy: the work is drawing or leaking a great deal of energy, and it has to go somewhere.
Planar convergence: for a moment, the workshop sits on a thin place between planes.
Resonant magic: the work hums with magic that echoes through everything nearby.
Spirit magnet: the work is attracting the attention of spirits, friendly or not.
Suspicious offer: a buyer offers far too much for the work, and will not say why.
Technical challenge: a difficult step needs a specialist, a tool the crafter does not have, or a leap of insight.
Unexpected flaw: something in the materials or the plan turns out to be wrong, and it only shows when the work is nearly done.
""")
table("dt.event.forgery", "Downtime events: Create a Forgery", """
The format for the paperwork the PC is imitating changes, and they must adjust.
The paperwork is spoiled by a freak accident, such as a leaky roof or a clumsy assistant knocking over the ink.
A mysterious benefactor offers the PC special tools or a source document, and hints at a favor to be asked later.
""")
table("dt.event.subsist", "Downtime events: Subsist", """
After a long time subsisting in one area, the PC finds an unknown berry or herb that could be the basis of a new medicine.
The PC finds signs that some large creature has been foraging in the same area, possibly a monster.
A local complains that the PC is taking from a spot they have long used.
A stranger in worse shape than the PC turns up and asks to share the camp.
""")
table("dt.event.trade", "Downtime events: Buy and Sell", """
The PC sells an item that interests members of a particular group, who start following them around.
A merchant sells the PC an item that turns out to be fraudulent.
A shop the PCs frequent is in trouble and about to go out of business without help.
Someone else offers a higher bid for an item the PC wants, leading to a negotiation, or to a job the PC must do to win the item.
""")
table("dt.event.retrain", "Downtime events: Retrain", """
The PC is injured in physical training.
Tapping into new magical powers brings a magical curse or an odd phenomenon.
A retraining instructor falls ill or goes missing.
Someone watches the PC retrain and asks to join them as they study or practice.
The PC's training comes to a halt until they can get a rare book or something similar.
""")
table("dt.event.general", "Downtime events: anything else", """
A letter arrives from someone the PC has not heard from in years, and it is not good news.
A rumor about the party reaches the settlement before they do, and it is not entirely wrong.
A neighbor asks a small favor that will turn out to be a larger one.
A festival or market day interrupts everything for a day, and the whole settlement turns out.
A stranger is asking around for one of the party, by description.
An old debt comes due, and the creditor is polite about it.
Bad weather closes the roads, and everyone who was meant to arrive is stuck elsewhere.
Someone the PC helped earlier turns up with a gift, or a need.
""")

def raw_table(name, title, text):
    """Like table(), but the lines are kept exactly as written. The GM Tools tables use the not and needs columns."""
    TABLES[name] = {"title": title, "entries": [ln.strip() for ln in text.strip().splitlines()
                                                if ln.strip() and not ln.strip().startswith("#")]}


# ============================================================ the GM Tools job board and the wording it shares
# The notice board (downtime.py) and the Quest Builder (session.py) draw on these. Two conventions, both in gmtools.py:
#   hm in the not column: a generic fantasy line, left out when the setting is Hallowmead
#   s2 / s3 in the needs column: a sillier line, used only at Standard or Ridiculous silliness
# Lines tagged pl:value carry a payload (a skill, a short name) that the tool reads back.
raw_table("deadline", "Deadlines", """
by sundown||||hm
by the end of the week||||hm
within three days||||hm
before the next toll||||hm
at dusk tomorrow||||hm
before the caravan leaves||||hm
in time for the harvest||||hm
before the trial||||hm
by market day||||hm
before the first snow||||hm
before the cheese turns|||s2|hm
before anyone checks|||s2|hm
before the soup gets cold|||s2|hm
before the chandelier gets back from its holiday||2|s3|hm
before the Underhallow Concord|p:hallowmead
before the next lamp-lighting|p:hallowmead
before the lift gets repaired|p:hallowmead
by the next shift change at the Crossings|p:hallowmead
by the time the tunnel is swept|p:hallowmead
""")

raw_table("place", "Places", """
the old mill||||hm
the crossroads inn||||hm
the marsh causeway||||hm
the town cellar||||hm
the east gate||||hm
the abandoned chapel||||hm
the river docks||||hm
the quarry road||||hm
the clock tower||||hm
the fish market||||hm
the burnt barn||||hm
the old mine lift|p:hallowmead
the flooded cistern|p:hallowmead
the third tunnel past the leaning cart|p:hallowmead
the kobold maintenance shaft|p:hallowmead
the fungus terraces|p:hallowmead
the crystal bloom corridor|p:hallowmead
the goblin midden|p:hallowmead
the dwarven pump house|p:hallowmead
the wobbling bridge|p:hallowmead
the drainage hall|p:hallowmead
the Crossings market|p:hallowmead
the lamp-lighters' stair|p:hallowmead
the salvage yard|p:hallowmead
""")

raw_table("parcel", "Parcels", """
a sealed crate
a locked box the size of a loaf
a parcel tied with eleven knots
a basket of eggs, each numbered
a jar that hums
a bundle of letters in three handwritings
a tin full of buttons, apparently important
a heavy sack that never stops moving|||s2
a cake, structurally unsound|||s2
a pot of soup that must stay warm|||s2
a lunch that has been promised to three people||2|s3
a sock stuffed with something that might be a sock||2|s3
""")

raw_table("passenger", "Passengers", """
a nervous accountant
a retired bridge troll
a goat with a signed letter
a very small, very rude noble
a mushroom farmer who is also, somehow, a priest
a retired sword
a crate of live hens
a person who insists they are not a person|||s2
a sleepwalking uncle|||s2
a talking turnip with a travel permit|||s2
a ghost who has paid for a seat||2|s3
an opinionated cart||2|s3
""")

raw_table("pest", "Pests", """
a nest of angry mine-rats
a sulking mushroom
a swarm of paper-eating beetles
a bat that has learned to knock
a wandering lamp
a bog toad that sings at the wrong pitch
a family of very organized cave crickets
a rival peddler
a cursed doorknob|||s2
an unlicensed ghost|||s2
a gelatinous cube of unknown ownership|||s2
a flock of boots that migrate||2|s3
a goblin with a megaphone||2|s3
""")

raw_table("lost.item", "Lost items", """
a left boot
a signet ring, probably
a map with a hole where the important part used to be
a prize ladle
a jar of sourdough starter older than the town
a tuning fork
a brass key to nothing in particular
a set of false teeth
a very good hat
a spoon with sentimental value|||s2
a lucky pebble (they will know it)|||s2
a pet rock, answers to Gerald|||s2
a chair that was last seen leaving||2|s3
a missing Tuesday||2|s3
""")

raw_table("lost.where", "Where it was lost", """
in the third tunnel on the left
near the old well
in the market, or possibly the market's basement
at the bottom of a very deep barrel
under a staircase that is not there any more
somewhere between here and the other thing
in the care of someone who will not give it back
in a place the owner will not describe, for reasons
inside something larger than it should be|||s2
in the stomach of an animal, which is not the one you would guess|||s2
at a funeral it was not invited to||2|s3
""")

raw_table("item.mundane", "Ordinary objects", """
a pair of boots
a ladle
a lantern
a coil of rope
a brass bell
a teapot
a ladder
a wheel of cheese
a rolled-up rug
a clock
a bucket with opinions|||s2
a perfectly good door|||s2
a decorative hat|||s2
a very sad harp|||s2
a frying pan with a reputation||2|s3
a hundred identical spoons||2|s3
""")

raw_table("countable", "Things to count", """
barrels
lamps
steps
loose bricks
mushrooms with faces
nails
cartwheels
spoons
unhappy chickens|||s2
doors that open to the same room|||s2
names on the wall of apologies||2|s3
""")

raw_table("trial.silly", "Trials and hearings", """
a trial about a stolen hat
a hearing about a very old fence
a dispute over a bridge's toll
a mediation between two feuding bakers
a tribunal concerning a missing goose
an inquiry into who ate the last pie
a duel of insults, officially sanctioned|||s2
the trial of a statue that is accused of looking at someone||2|s3
""")

raw_table("role.stand", "Roles to stand in for", """
the best man
the guest of honor
the groom's cousin
the judge's second chair
the bride's father
the town crier
the person who cuts the ribbon
a respected elder, in a good hat|||s2
the mascot|||s2
the corpse, in a play||2|s3
the other, shorter, corpse||2|s3
""")

raw_table("event.silly", "Events", """
a wedding
a funeral
a bake-off
a harvest festival
a lantern procession
a guild feast
a town meeting
a poetry slam
a naming ceremony
a mud-wrestling charity night|||s2
a rival's retirement party|||s2
a performance of a very long play|||s2
a conference on the theory of puddles||2|s3
""")

raw_table("contest.silly", "Contests", """
the big cheese-rolling race
a pie-eating contest
the tunnel marathon
a riddle tournament
an arm-wrestling match
a spelling bee
a shouting match
the Great Mushroom Weigh-In|||s2
a staring contest against a very patient wall|||s2
a hat-balancing duel|||s2
a quiet-whispering competition (loudly)||2|s3
""")

raw_table("team.silly", "Teams", """
the Rusty Spoons
the Lamp Brigade
the Third Shift
the Mildly Lucky
the Wobbling Bridge Irregulars
the Cheese Reserve
the Gentle Hammers
the Left Boots|||s2
the Almost Champions|||s2
Brenda||2|s3
""")

raw_table("custodian.silly", "Who is holding it", """
a customs clerk who hates everything
a goat that has taken a vow
a very old dwarf who falls asleep mid-sentence
an auction house
a bureaucrat with a stamp
a vault door that wants to be asked nicely|||s2
a retired dragon who runs a pawnshop|||s2
a committee, which has not met in a decade||2|s3
""")

raw_table("obstinate.being", "Obstinate beings", """
a donkey with firm beliefs
an old goblin sitting in the middle of the tunnel
a toll troll who has retired but not told anyone
a stubborn statue
a landlord with a legal argument
a mud-slick bog that dislikes being walked on|||s2
a sentient fog with a grudge|||s2
a very small door who feels it is large||2|s3
""")

raw_table("broken.thing", "Broken things", """
the big lantern
the town clock
the main lift
the sluice gate
the bridge
the pump
the dinner bell
the ceremonial chair
the mayor's lucky sword
the festival's one good cart
the oven of destiny|||s2
a fountain that now dispenses gravy|||s2
a monument that has started apologizing||2|s3
""")

raw_table("bad.actor", "Who needs an apology", """
a goblin who sold a crooked ladder
a ratfolk who lost a library book (in a fire)
a kobold who painted the wrong door
a nobleman who insulted the town goat
a travelling bard who rhymed 'orange'
the mayor, for unspecified reasons
the party's last employer|||s2
a ghost, for the thing it said at the wedding|||s2
a very small dragon in a very big hat||2|s3
""")

raw_table("deceased.silly", "Eulogy subjects", """
a beloved cheese
a pet that was never alive
a rival who is clearly going to outlive everyone
a famous fish
a hero who is just late
the town's tallest hat|||s2
a very old joke|||s2
the last surviving tree in the plaza, which is also the mayor||2|s3
""")

raw_table("nuisance.verb", "Nuisances", """
leaving boots on the stairs at night
moving the signposts
nibbling the town's cheese
whistling in the tunnels
stealing every third spoon
rearranging the market stalls
changing the wells' water to something fizzy|||s2
singing sea shanties underground|||s2
swapping the lanterns' oil for soup||2|s3
""")

raw_table("thing.big", "Big things", """
a grand piano
a statue
a bathtub
a wardrobe
a very large cheese
a tapestry the size of a barn
a cart that is bigger than its own load|||s2
a bell|||s2
a fully grown, cooperative tree||2|s3
""")

raw_table("disguise.silly", "Disguises", """
a plain white mask
a painted tin fox mask
a gilded stag mask
a beaked mask stuffed with dried herbs
a carved wooden owl mask
a tarnished silver mask with no mouth
a cloak that says GUARD on it
a false mustache, in a color that does not exist in nature|||s2
a cheese-wedge hat|||s2
a very convincing goat costume||2|s3
""")

raw_table("pupil.silly", "Pupils", """
the mayor's nephew
a bored guard
a shy ghost
a very old goblin who has never learned
a young ratfolk with great ambitions
a skeleton who has opinions
a goat|||s2
a cart horse who wants to be taken seriously|||s2
a committee of rocks||2|s3
""")

raw_table("skill.silly", "Skills to teach", """
read a map
swim, in a bucket
bake a pie
whistle through a flute
pick a lock politely
tell a lie convincingly
dance without being seen to dance
fall down stairs with grace|||s2
haggle in three languages at once|||s2
pretend to be a plant||2|s3
""")

raw_table("food.silly", "Foods to taste", """
the mayor's pie
a stew of undisclosed origin
cheese that has gone past forgiveness
a mushroom cake
a goblin's idea of fine dining
a jelly that watches you|||s2
a soup made entirely of leftovers|||s2
a roast, shaped like the cook's rival||2|s3
""")

raw_table("rumor.silly", "Rumors to disprove", """
that the bridge is haunted
that the mayor wears a wig
that the well is bottomless
that the cheese is alive
that a ghost runs the bakery
that the third tunnel leads nowhere
that the town was built on a very large hat||2|s3
""")

raw_table("creature.silly", "Creatures to owe a favor", """
a retired dragon
a very polite ghost
a talking mushroom
a goat with powers
a goblin in a cloak
a gelatinous something with a ledger
a mushroom elder
a chicken, but a legally important one|||s2
the lamp that sees all|||s2
an unusually helpful mimic||2|s3
""")

raw_table("job.task", "Job tasks", """
escort {a passenger} to {place}
clear {a pest} out of {place}
find {a lost.item} that was last seen {lost.where}
carry {a parcel} to {place} without opening it
count the {countable} in {place} and report the total (twice, in case the first is wrong)
guard {a parcel} overnight at {place}
repair {a broken.thing} before anyone notices it was broken
find out who has been {nuisance.verb}
testify at {a trial.silly} on someone else's behalf|||s2
stand in for {a role.stand} at {an event.silly}|||s2
win {a contest.silly} for {a team.silly}, which has not won since it was founded|||s2
retrieve {a item.mundane} from {a custodian.silly}|||s2
persuade {a obstinate.being} to move out of the way (they have been there nine years)|||s2
return {a item.mundane} to the person who lost it, who does not want it back|||s2
apologize, in person, on behalf of {a bad.actor}|||s2
take {a thing.big} across {place}, which has no door large enough|||s2
get {a pest} out of {a item.mundane} without hurting either|||s2
be seen at {a event.silly} wearing {a disguise.silly}|||s2
teach {a pupil.silly} how to {skill.silly} by the end of the week|||s2
taste-test {a food.silly} and announce that it is delicious, whatever the truth|||s2
deliver a eulogy for {a deceased.silly}, who is not dead yet||2|s3
judge {a contest.silly}, since all the judges have resigned||2|s3
prove that {a rumor.silly} is false (it is true)||2|s3
return a favor owed to {a creature.silly}, who will not say what the favor was||2|s3
""")

raw_table("job.why", "Real reasons (GM only)", """
wants the party out of the way for the evening
is trying to impress {faction.name}, who is not paying attention
is stalling for time while the real job is done elsewhere
needs it done by someone who cannot be traced back
is a rival's decoy, and does not know it
genuinely needs the help and is too proud to say so
is being quietly blackmailed by someone in the room
wants to frame a rival for how badly this goes
owes {a creature.silly} a favor and is delegating it|||s2
has bet {bet.silly} that it cannot be done|||s2
is testing whether the party can be trusted with something worse|||s2
is running the same job on three other crews and will pay only the fastest|||s2
has been told by a prophecy to hire strangers, and is annoyed about it||2|s3
is, technically, the intended victim||2|s3
""")

raw_table("job.catch", "Catches", """
the notice is two weeks old and someone has already done the job, badly
a rival crew has taken the same job and is on the way
the poster left out the part where {a pest} lives there
the poster has put up this notice in three other places at three different prices
the item is not quite what was described
the poster is not who they say they are
the deadline is real and the poster lied about everything else
the location has been flooded since the notice went up
the pay is real, but it is in the wrong currency|||s2
everyone involved is related, and they all hate each other|||s2
the poster is very sorry and will keep saying so|||s2
the job is exactly as described, and the description was written by a goblin||2|s3
the client has already spent the pay||2|s3
""")

raw_table("job.head", "Notice headlines", """
HELP WANTED
REWARD OFFERED
URGENT, DISCREET, MOSTLY LEGAL
NO QUESTIONS PLEASE
SEEKING THE BRAVE OR THE BROKE
WORK AVAILABLE FOR PERSONS OF SOME COURAGE
BRING YOUR OWN BUCKET|||s2
NOT DANGEROUS (MOSTLY)|||s2
DO NOT READ THIS NOTICE||2|s3
FOR THE ATTENTION OF WHOEVER READS THIS FIRST||2|s3
""")

raw_table("pay.silly", "Silly pay", """
a very good meal
a medal made from a spoon
free lodging, provided nobody asks about the third room
a map to something that is probably still there
a signed letter of recommendation, signed by a goat
a lifetime supply of pickles
the right to say you did it
a small boat, not currently in the water
a favor, to be called in at the worst moment
a cheese that is much older than it looks|||s2
a title that comes with immunity, from a country that has ended|||s2
a mild curse, removed in installments||2|s3
""")

raw_table("bet.silly", "Bets", """
a month's wages
a very good hat
a goat
their reputation
the deed to a small boat
a round of drinks for the entire inn
a pair of left boots
""")

raw_table("sign.goblin", "Notice sign-offs (goblin)", """
Signed, very important
No refunds, no questions, no looking at the goat
Reward paid on delivery, or shortly after, or in spirit
""")

raw_table("sign.kobold", "Notice sign-offs (kobold)", """
Please do not step on the signs
Safety inspected, mostly by me
Please keep the tunnel tidy on your way out
""")

raw_table("sign.ratfolk", "Notice sign-offs (ratfolk)", """
Fair prices, fair weights, mostly fair
Inquire within, and bring exact change
Honest scales, honest tails
""")

raw_table("sign.grippli", "Notice sign-offs (grippli)", """
Please keep your boots dry on the way in
Reed-pen notice, handle with a damp cloth
Come by the pond; mind the third stone
""")

raw_table("sign.leshy", "Notice sign-offs (leshy)", """
Sprouting hours: dawn to dusk
Slow replies, steady roots
Kindly do not water the notice
""")

raw_table("sign.automaton", "Notice sign-offs (automaton)", """
Request ID {#100-999}. Please take a number
Filed in triplicate, answered in due time
Processing time: some
""")

raw_table("sign.poppet", "Notice sign-offs (poppet)", """
Mended with care, please read gently
Stitched by hand; handle at the seams
""")

raw_table("sign.awakened_animal", "Notice sign-offs (awakened animal)", """
Scratched in with a claw, apologies for the handwriting
Left by a very small paw. Please look under the hay
""")

raw_table("sign.default", "Notice sign-offs (everyone else)", """
Inquire at the address below
Reply in person, with references if you have them
""")


# ============================================================ the Underhallow (limited to the hallowmead pack)
UNDERHALLOW = {
    "occupation": """
salvage crew boss|p:hallowmead
route runner|p:hallowmead
fungus farmer|p:hallowmead
apothecary|p:hallowmead
chandler|p:hallowmead
quartermaster|p:hallowmead
sexton|p:hallowmead
refuse sorter|p:hallowmead
puppeteer|p:hallowmead
guild clerk|p:hallowmead
jeweler|p:hallowmead
brewer|p:hallowmead
peddler|p:hallowmead
toll keeper|p:hallowmead
mine-cart mechanic|p:hallowmead
lamplighter|p:hallowmead
cartographer|p:hallowmead
cheesemonger|p:hallowmead
bridge warden|p:hallowmead
professional mourner|||s2
official taster|||s2
retired hero (self-appointed)|||s2
tunnel inspector, unlicensed|||s2
night-soil poet||2|s3
second-best sword polisher||2|s3
""",
    "dt.job": """
Sort a refuse chute's haul on the sorting floor|sk:crafting sk:society f:finders_keep p:hallowmead underground
Work a crane crew hauling scrap to the upper platforms|sk:athletics f:finders_keep p:hallowmead underground|1|tl:-1
Tinker a broken contraption back to life|sk:crafting f:finders_keep p:hallowmead underground tl:1
Rig and mend a rope bridge|sk:athletics sk:crafting f:finders_keep p:hallowmead underground
Appraise odd salvage for stallholders|sk:society sk:crafting f:finders_keep p:hallowmead underground
Cut and set stone for an arch|sk:crafting sk:masonry-lore f:the_grand_underhall p:hallowmead underground
Inspect a stretch of tunnel for weaknesses|sk:masonry-lore sk:survival f:the_grand_underhall p:hallowmead underground tl:1
Run a mine-cart freight line|sk:athletics sk:mining-lore f:the_grand_underhall p:hallowmead underground tl:-1
Paint a sign in careful handwriting|sk:crafting sk:art-lore f:the_grand_underhall p:hallowmead underground tl:-1
Copy and file records in the catacomb archives|sk:society sk:scribing-lore f:the_hushwarrens p:hallowmead underground
Carry a quiet message between settlements|sk:stealth sk:society f:the_hushwarrens p:hallowmead underground tl:1
Keep the ledgers straight for a trading house|sk:society sk:accounting-lore f:the_hushwarrens p:hallowmead underground tl:1
Mend a stilt platform over the water|sk:crafting sk:athletics f:stillwater_hollow p:hallowmead underground
Tend the sluices and channels|sk:nature sk:engineering-lore f:stillwater_hollow p:hallowmead underground
Ferry goods and passengers along the river|sk:athletics sk:boating-lore f:stillwater_hollow p:hallowmead underground tl:-1
Tend the fungal gardens and mushroom beds|sk:nature sk:farming-lore f:the_quiet_ring p:hallowmead underground
Gather glow-moss and luminous spores|sk:survival sk:nature f:the_quiet_ring p:hallowmead underground
Walk the root paths and watch for damage|sk:nature sk:survival f:the_quiet_ring p:hallowmead underground tl:-1
Repair a damaged limb or fitting in a repair hall|sk:crafting sk:medicine f:the_mending p:hallowmead underground tl:1
Sew and patch a poppet|sk:crafting sk:crafting-lore f:the_mending p:hallowmead underground
Run the workshop floor and sort what needs fixing first|sk:society sk:crafting f:the_mending p:hallowmead underground tl:1
Keep the records of who was repaired and what was kept|sk:society sk:scribing-lore f:the_mending p:hallowmead underground
Guide travelers between Karak's Everhold and the settlements|sk:survival f:firstlight p:hallowmead underground tl:1
Help newly awakened animals learn to speak and read|sk:diplomacy sk:society f:firstlight p:hallowmead underground tl:-1
Run a stall for a settlement at the Crossings|sk:diplomacy sk:society f:the_crossings p:hallowmead underground
Haul stalls and goods across the market|sk:athletics f:the_crossings p:hallowmead underground tl:-1
Keep the peace in the crowd on a market day|sk:intimidation sk:diplomacy f:the_crossings p:hallowmead underground tl:1
""",
    "dt.event.earn": """
A salvage haul lands on the PC's workbench with something unexpected in it|underground trade p:hallowmead
A kobold inspector wants to check the arch over the work site, and will not be hurried|underground craft p:hallowmead t:light
A courier asks the PC to carry a message, and will not say who it is from|underground mystery p:hallowmead
The river changes course a little, and the whole platform has to be shifted|underground nature water p:hallowmead
A leshy asks the PC to work around a root the settlement will not cut|underground nature p:hallowmead t:light
A visitor from the dungeon end asks very thoughtful questions about the work|underground monster mystery p:hallowmead t:light
""",
    "dt.event.craft": """
A refuse chute brings down exactly the part the PC was missing, and also a problem|underground treasure p:hallowmead
The PC's work is noticed by a kobold mason, who has opinions about the proportions|underground craft p:hallowmead t:light
A Mending repairer offers to trade a component for a favor|underground craft family p:hallowmead
""",
    "dt.event.trade": """
A goblin trader offers a bargain on something that was clearly thrown away yesterday|underground trade p:hallowmead t:light
A Hushwarrens broker wants an item without being seen to want it|underground mystery trade p:hallowmead
""",
}


def hallowmead_additions():
    """The Underhallow lines as {table name: [entries]}, in Story Forge form (each limited to the hallowmead pack)."""
    out = {}
    for name, text in UNDERHALLOW.items():
        lines = []
        for ln in text.strip().splitlines():
            ln = ln.strip()
            if ln:
                lines.append(normalize(ln))
        out[name] = lines
    return out


def job_slots():
    """What to read from a job entry's tags (used by downtime.jobs)."""
    return {"skill": "sk:", "level": "tl:", "place": "f:"}

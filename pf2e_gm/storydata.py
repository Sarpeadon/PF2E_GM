"""Built-in content for Story Forge. Every table is plain text, one entry per line:

    text | tags | weight | needs | not

Only the text is required. Tags are space separated (themes like crime or undead, environments like urban or
underground, k:npc / k:faction / k:group / k:creature for the kind of subject, pl for plural subjects).
Special tags: p:<pack> limits an entry to a content pack, t:<tone> to a tone (grim, light, weird), and
L3-8 to a party level range. needs lists tags that must already be in play (a/b means either), not lists tags
that must be absent. Lines starting with # are comments.

Edit these here or, better, use the table editor in the app, which saves your changes separately and never
touches this file.
"""
TABLES = {}
RECIPES = {}


def table(name, title, text):
    TABLES[name] = {"title": title,
                    "entries": [ln.strip() for ln in text.strip().splitlines()
                                if ln.strip() and not ln.strip().startswith("#")]}


# ============================================================ themes and settings
table("theme", "Story themes (what a story is about)", """
crime|crime|3
politics|politics|3
trade|trade|3
religion|religion|2
undead|undead|2
fey|fey|1.5
monster|monster|3
nature|nature|2
ruin|ruin|2
magic|magic|2
military|military|2
family|family|2
mystery|mystery|3
disease|disease|1.2
weather|weather|1.5
festival|festival|1.5
craft|craft|1.5
treasure|treasure|2
""")
table("env", "Environments", """
urban|urban|4
wild|wild|3
underground|underground|3
road|road|2
water|water|1.2
""")
table("env.dungeon", "Environments for dungeon scenes", """
underground|underground|6
wild|wild|1
urban|urban|1
""")
table("env.social", "Environments for social and downtime scenes", """
urban|urban|6
road|road|1
water|water|1
""")
table("env.travel", "Environments for travel scenes", """
wild|wild|4
road|road|4
underground|underground|3
water|water|2
""")

# ============================================================ people
table("occupation", "Occupations", """
cartwright|trade craft urban road
lamplighter|urban
ferryman|water trade
tanner|craft urban
chandler|craft trade
baker|trade urban family
innkeeper|trade urban road
barkeep|trade urban
brewer|craft trade
cooper|craft
miller|trade craft wild
miner|underground craft
gravedigger|undead religion urban
sexton|religion undead
acolyte|religion
hedge witch|magic nature wild
herbalist|nature craft
apothecary|trade magic disease
physician|disease urban
midwife|family
scribe|politics trade urban
clerk|politics urban
tax collector|politics urban
toll keeper|road trade
town crier|urban politics
watchman|military crime urban
bailiff|politics crime
jailer|crime
smuggler|crime trade water
fence|crime trade urban
pickpocket|crime urban
bounty hunter|crime wild
mercenary|military
caravan guard|military road
quartermaster|military trade
drover|road wild nature
shepherd|nature wild
gamekeeper|nature wild
trapper|nature wild
woodcutter|wild craft
charcoal burner|wild craft
fisher|water
bargeman|water trade
river pilot|water
dockhand|water urban
sailor|water
boatwright|water craft
smith|craft
farrier|craft road
locksmith|craft crime urban
glassblower|craft magic
jeweler|craft treasure trade
tailor|craft urban
dyer|craft urban
weaver|craft
potter|craft
stonemason|craft ruin underground
surveyor|ruin politics
cartographer|ruin treasure
antiquarian|ruin treasure magic
archivist|mystery politics
tutor|family
street preacher|religion urban
pilgrim|religion road
hermit|religion wild mystery
fortune teller|magic mystery festival
puppeteer|festival
minstrel|festival road
juggler|festival
actor|festival urban
courier|road trade
messenger|road politics
peddler|trade road
tinker|craft road
rat catcher|urban disease
night-soil collector|urban disease
undertaker|undead urban religion
alchemist|magic craft
hedge knight|military road
retired soldier|military
militia sergeant|military
deserter|military crime
beggar|urban
orphan|urban family
magistrate|politics crime
guild clerk|trade politics
lantern warden|underground urban p:underground
tunnel warden|underground military p:underground
cave guide|underground road p:underground
gem cutter|underground craft treasure p:underground
glow-moss harvester|underground nature p:underground
bone collector|underground undead p:underground
mushroom farmer|underground nature trade p:underground
salvager|treasure ruin underground p:underground
freight pilot|trade p:sf
dockside mechanic|craft p:sf
station medic|disease p:sf
comms operator|politics mystery p:sf
ship's cook|trade p:sf
""")
table("person.adj", "Short descriptors for a person", """
nervous
stubborn
cheerful
suspicious
soft-spoken
loud
weary
nosy
proud
shifty
patient
gruff
absent-minded
overly polite
sharp-eyed
soot-stained
well-fed
threadbare
one-eyed
limping
tattooed
freckled
silver-haired
scarred
sunburned
pale
broad-shouldered
wiry
elderly
young
brooding
devout
penniless
prosperous
perfumed
ink-stained
cautious
reckless
forgetful
superstitious
hard-bitten
well-travelled
newly arrived
long-suffering
eager
aloof
bright-eyed
tight-lipped
cheery
heavyset
""")
table("official", "Officials and authorities", """
the magistrate
the tax assessor
the harbor master
a visiting inspector
the captain of the watch
the guildmaster
the town reeve
a customs officer
the high priest
the royal cartographer
the granary warden
the coroner
the lamp-tax collector
the quartermaster
the council speaker
the chief physician
the sheriff
the master of the mint
""")

# ============================================================ goods, items, and small nouns
table("goods", "Trade goods", """
lamp oil
lantern glass
salt
iron nails
tallow candles
holy water
coffin nails
river clay
rope
blank parchment
dried herbs
cheap wine
mining powder
smoked fish
quicklime
leather
beeswax
tin plate
bone needles
fresh bread
copper wire
lump coal
spiced sausage
mulled cider
barley
hemp
glow-moss spores|p:underground
rock salt
tar
lye soap
dye
vinegar
""")
table("contraband", "Contraband", """
smoke-powder
forged seals
unlicensed spellbooks
glow-moss spores|underground
counterfeit coins
black-market elixirs
stolen relics
tomb-goods|ruin
poisoned wine
cursed trinkets|magic
banned scriptures|religion
untaxed brandy
caged messenger birds
unmarked ingots
stolen hounds
forged pardons
""")
table("docs", "Forgeable documents", """
toll passes
guild seals
pedigrees
wills
weights and measures
letters of credit
pilgrim tokens
lantern permits
writs of safe passage
birth records
""")
table("treasure.item", "Valuable objects", """
silver reliquary
ancestral sword
sealed ledger
jeweled music box
cracked scrying bowl
map case
stone key
sack of old coins
saint's finger bone
signet ring
iron-bound strongbox
ceremonial mask
bronze astrolabe
bejeweled dagger
pearl necklace
illuminated manuscript
carved ivory comb
silver lantern
ruby the size of a thumbnail
bundle of love letters
dwarven forge-hammer
cracked bell
sealed jar of something that hums
set of surveyor's tools
""")
table("relic", "Relics", """
saint's lantern
reliquary of a forgotten martyr
bell that has never been rung
cracked oracle-skull
fragment of a god's altar
chalice that is never empty
holy book with a missing page
ancient banner
bone staff
""")
table("crop", "Crops", """
barley
turnips
wheat
hops
grapes
mushrooms
apples
flax
beans
rye
oats
peppers
""")
table("weather.odd", "Odd weather", """
a green fog
hail the size of walnuts
a fog that smells of smoke
a warm wind from the deep
dry lightning
an unseasonal frost
snow in high summer
black rain
a silence so complete it hurts
a sudden, impossible thaw
a red sunset that lasts all night
rain that falls upward in the lamplight
""")
table("fey.guise", "Fey disguises", """
a wandering minstrel
a lost child
a gray cat
an old woman with too many keys
a traveling merchant of tiny things
a handsome stranger whose boots are free of mud
a dancer in last year's fashions
a ferryman who will not take coin
""")
table("smell", "Smells", """
burnt sugar
wet stone
tallow smoke
old bread
rotting fish
lamp oil
lavender and damp
iron and blood
mushrooms
""")
table("sound", "Sounds", """
a distant bell
dripping water
a slow, steady hammering
someone humming off-key
a chorus of coughs
a door that will not stay shut
wind in the rafters
crows
""")
table("landmark", "Landmarks", """
a statue with its head missing
the old well
a lightning-split oak
a shrine to a forgotten saint
a dry fountain
a tollhouse nobody mans
the broken clock tower
a milestone with the number scratched out
a great, leaning chimney
a wall of faded notices
""")
table("creature.generic", "Creatures (when no creature list is loaded)", """
something with too many teeth|monster t:grim
a pack of famished wolves|monster nature
a bear that has learned to open doors|nature monster t:light
an owlbear|monster nature
a swarm of carrion beetles|nature disease
a gaunt thing from the deep tunnels|monster underground t:grim
a troll with a toothache|monster t:light
a nest of giant spiders|monster nature underground
a young drake|monster
a wyvern|monster
a ghoul|undead t:grim
a restless ghost|undead
a wight in a stolen coat|undead
a will-o'-wisp|fey weird
a hag who runs the fish stall|fey monster t:weird
a pair of mated griffons|nature monster
a bog-lurker|nature water monster
a giant crab|water monster
a mimic that has learned to be a door|monster magic
a stone golem that has forgotten its orders|magic ruin
a basilisk|monster
a gibbering mouther|monster underground t:grim
""")

# ============================================================ names
table("name.adj", "Name words: adjectives", """
Ashen
Gilded
Hollow
Silent
Crimson
Gray
Iron
Lantern
Mossy
Salt
Black
Silver
Broken
Drowned
Burning
Pale
Hidden
Thorned
Sunken
Whispering
Cobalt
Amber
Rusted
Wandering
Lonely
Merry
Tarnished
Bitter
Golden
Smoking
""")
table("name.noun", "Name words: nouns", """
Ledger
Lantern
Key
Hand
Thorn
Chalice
Bell
Crown
Compass
Anvil
Wheel
Knot
Candle
Dagger
Quill
Mask
Hound
Raven
Stag
Serpent
Gate
Tide
Ember
Veil
Mirror
Loom
Scale
Reed
Hammer
Spindle
""")
table("name.collective", "Name words: groups", """
Company
Brotherhood
Syndicate
Circle
Compact
Order
League
Concord
Lodge
Fellowship
Covenant
Cabal
Consortium
Wardens
Guild
Society
Chorus
Assembly
""")
table("name.thing", "Name words: things", """
Long Dark
Broken Wheel
Ninth Door
Silver Tide
Last Lamp
Third Bridge
Open Hand
Sleeping Moon
Red Ledger
Hollow Oak
Seven Locks
Quiet Water
""")
table("name.owner", "Shopkeepers' first names", """
Tamsin
Hollis
Brenna
Osric
Mattis
Willa
Garrick
Nell
Fenna
Corin
Bram
Una
Pell
Dessa
Joss
Hester
""")
table("name.tavern.noun", "Tavern nouns", """
Ladle
Barrel
Goose
Pig
Kettle
Cart
Lamb
Plow
Anchor
Horn
Boot
Pipe
Rat
Cat
Fiddle
Bucket
""")
table("name.shop.type", "Shop types", """
chandlery
apothecary
curiosity shop
bindery
ironmongery
tannery
dye-works
bakehouse
tailor's
cobbler's
fishmonger's
cheesemonger's
reliquary
tinsmith's
""")
table("name.street.a", "Street names: first word", """
Candle
Tanner's
Salt
Cooper's
Lantern
Weaver's
Gallow
Chandler's
Mill
Bell
Cobble
Rope
Smith's
Tallow
Brewer's
Goose
Bishop's
Needle
Fishmonger's
Iron
Cinder
Glass
""")
table("name.street.b", "Street names: second word", """
Row
Lane
Steps
Wynd
Gate
Court
Alley
Walk
Close
Hill
Quay
""")
table("name.set.a", "Settlement names: first part", """
Gray
Ash
Hollow
Marrow
Stone
Salt
Cold
Mill
Thorn
Oak
Raven
Black
Iron
Moss
Lantern
Wick
""")
table("name.set.b", "Settlement names: second part", """
wick
ford
mere
haven
brook
bridge
hollow
stead
ton
by
field
gate
march
fall
reach
""")
table("street", "Streets", """
{name.street.a} {name.street.b}
""")
table("settlement.name", "Settlements", """
{name.set.a}{name.set.b}
""")
table("tavern.name", "Taverns", """
the {name.adj} {name.tavern.noun}||3
the {name.tavern.noun} and {name.tavern.noun}||2
the {name.noun} and {name.tavern.noun}||1
the {name.tavern.noun}'s Rest||1
""")
table("shop.name", "Shops", """
{name.owner}'s {name.shop.type}||3
the {name.adj} {name.noun} {name.shop.type}||1
""")
table("faction.name", "Faction names", """
the {name.adj} {name.noun}||3
the {name.adj} {name.collective}||3
the {name.noun} of the {name.thing}||2
the {name.collective} of the {name.thing}||2
the {settlement.name} {name.collective}||1.5
{name.adj} {name.noun} {name.collective}||1
""")
table("faction.kind", "Kinds of faction", """
smugglers' ring|crime trade
merchant guild|trade
temple order|religion
thieves' guild|crime urban
mercenary company|military
scholars' circle|mystery magic
farmers' cooperative|nature trade
hidden cult|religion crime
noble house|politics family
town militia|military urban
miners' union|craft underground
river-pilots' brotherhood|water trade
secret society|mystery politics
mage college|magic
hunters' lodge|nature wild
relic-hunters' consortium|ruin treasure
bardic college|festival
street gang|crime urban
pilgrim confraternity|religion road
hedge-witch coven|magic nature
clan of tunnel-dwellers|underground family p:underground
surgeons' guild|disease craft
alchemists' league|magic craft
undertakers' fellowship|undead religion
""")
table("faction.generic", "A faction (generated)", """
{faction.new}|k:faction
""")

# ============================================================ who
table("group", "Groups of people", """
a gang of {pl occupation}|k:group
{n:3-7} {person.adj} {pl occupation}|k:group pl
a family of {pl occupation}|family k:group
a company of {pl occupation} down on their luck|k:group
the {pl occupation} of {street}|trade k:group pl
a mob of angry {pl occupation}|k:group
a delegation of {pl occupation} from {settlement.name}|politics k:group
{n:2-4} {ancestry.adj} {pl occupation}|k:group pl
a crew of {pl occupation} with a grievance|k:group
the {pl occupation} of {settlement.name}|k:group pl
a traveling troupe of {pl occupation}|festival road k:group
a militia of {pl occupation}|military k:group
""")
table("who.odd", "Unusual subjects", """
a child who claims to remember the town before it was built|mystery fey weird k:npc
a stray dog that every shopkeeper feeds and none will claim|t:light k:creature
the ghost of {a occupation}|undead mystery k:npc
a talking raven that only speaks to strangers|fey magic t:weird k:creature
a traveling puppet troupe|festival road k:group
an itinerant judge on circuit|politics crime road k:npc
the new tax collector|politics urban k:npc
an old soldier who has not spoken since the war|military mystery k:npc
a mute pilgrim carrying a lantern that never goes out|religion mystery k:npc
a pair of identical twins no one can tell apart|family mystery k:npc pl
the town's oldest resident|family mystery k:npc
a hooded stranger who pays in antique coins|treasure mystery k:npc
a lantern spirit bound to the market square|magic undead t:weird k:creature
an apprentice who is far too good at the trade|craft magic k:npc
a famous bard who has not been seen in public for a year|festival k:npc
a living scarecrow|fey nature t:weird k:creature
an alchemist's runaway experiment|magic monster k:creature
a woman who sells umbrellas and only umbrellas|weather mystery k:npc
a cart that appears at crossroads at dusk|road mystery k:group
a priest who has lost their faith and found something else|religion mystery k:npc
the last surviving member of an old expedition|ruin treasure mystery k:npc
a tax-dodging noble in disguise|politics crime k:npc
an owl that delivers letters to the wrong people|mystery magic t:light k:creature
a one-man militia, who is also the only man|military t:light k:npc
""")
table("who", "Who (a rumor's subject)", """
{npc.named}|k:npc|6
{a person.adj} {ancestry.adj} {occupation}|k:npc|3
{campaign.npc}|k:npc|4
{campaign.faction}|k:faction|4
{faction.generic}|k:faction|3
{group}|k:group|3
{a creature}|k:creature monster nature undead|3
{who.odd}||2
""")
table("who.comp", "Who (a complication's source)", """
{group}|k:group|4
{npc.named}|k:npc|3
{a person.adj} {ancestry.adj} {occupation}|k:npc|3
{a creature}|k:creature monster nature undead|3
{campaign.faction}|k:faction|2
{faction.generic}|k:faction|2
{campaign.npc}|k:npc|2
{official}|politics k:npc|1
""")
table("who.patron", "Who (a patron asking for help)", """
{npc.named}|k:npc|6
{campaign.npc}|k:npc|4
{campaign.faction}|k:faction|3
{faction.generic}|k:faction|3
{a person.adj} {ancestry.adj} {occupation}|k:npc|2
{official}|politics k:npc|1
""")
table("who.faction", "Who (a faction making a move)", """
{campaign.faction}|k:faction|6
{faction.generic}|k:faction|3
""")
table("omen.who", "What an omen affects", """
the town's bells|pl
every {goods} in the market|pl
the {crop} fields|nature pl
a flock of ravens
the river|water
the stars over {settlement.name}|pl
the shrine's flame|religion
the town well
every lantern on {street}|pl
a comet
the livestock|nature pl
the dead of the old graveyard|undead pl
the clouds|weather pl
""")

# ============================================================ what (rumor events, by theme)
# Written as verb phrases that follow the subject: "{who} {what}". {has}/{is}/{was} agree with singular or plural.
table("what", "What (a rumor's event)", """
{what.crime}|crime|3||k:creature
{what.politics}|politics|3||k:creature
{what.trade}|trade|3||k:creature
{what.religion}|religion|3||k:creature
{what.undead}|undead|3
{what.fey}|fey|3||k:creature
{what.monster}|monster|3
{what.nature}|nature|3
{what.ruin}|ruin|3||k:creature
{what.magic}|magic|3||k:creature
{what.military}|military|3||k:creature
{what.family}|family|3||k:creature
{what.mystery}|mystery|3||k:creature
{what.disease}|disease|3||k:creature
{what.weather}|weather|3||k:creature
{what.festival}|festival|3||k:creature
{what.craft}|craft|3||k:creature
{what.treasure}|treasure|3||k:creature
{what.creature}||14|k:creature
{what.generic}||2|||k:creature
{what.generic.sf}|p:sf|2||k:creature
""")
table("what.creature", "Events starring a creature", """
{has} been spotted far from its usual haunt
{has} been seen carrying a skull and a lantern, in that order
{has} brought down a bridge, and then carefully rebuilt it
{has} taken up residence beneath a mill
{has} let a traveler go unharmed, and the traveler has not stopped talking about it
{has} been leaving gifts on doorsteps
{has} been herding sheep, in a way that suggests intelligence
{was} wounded by someone who insists it was an accident
{has} stopped hunting and started guarding
{has} learned to say a few words of Common
{has} been following one particular caravan
{has} been wearing something that is not its own
{has} been seen in the company of someone no one will name
{has} been hunting only at night, and only one kind of prey
""")
table("what.crime", "Crime events", """
{has} been selling forged {docs} out of the back of a shop
{was} seen paying off the night watch with {goods}
{has} been running {contraband} past {official}
{was} caught with {a treasure.item} that was reported stolen three towns away
{has} put out a quiet bounty on {a occupation} who knows too much
{has} been fleecing pilgrims with a rigged game of three cups|religion road
{has} been blackmailing {a occupation} with letters nobody was meant to read
{is} planning a heist on {a treasure.item} held by {official}|treasure
{was} robbed by someone who took the {goods} and left the coin
{has} gone to ground after informing on the wrong people|k:npc
{has} been running a protection racket that charges in {goods} instead of coin
{has} been paying debts with coins that turn to lead at dawn|magic fey
""")
table("what.politics", "Politics events", """
{has} been quietly buying votes ahead of the council meeting
{is} about to be exposed for skimming the {goods} tax
{has} secretly signed a treaty with a rival that no one else has seen
{was} offered a bribe by {official} and did not refuse it
{has} been spreading word that {official} is not who they claim to be
{has} written a petition that would shut down every {occupation} in town
{is} plotting to have {official} removed before the harvest
{has} found out who has been forging {docs}, and is selling the secret|crime
{has} accepted a post nobody else would take, and no one knows why
{has} claimed an old ruin as a private estate|ruin
{is} drafting a new law that exists mostly to hurt one family|family
{has} been seen leaving a meeting no one was told about
""")
table("what.trade", "Trade events", """
{has} cornered the market on {goods} just before a shortage
{has} a shipment of {goods} that never arrived and keeps insisting it did
{is} undercutting every {occupation} in the district, and no one can see how
{has} been buying up every barrel of {goods} for a buyer nobody has met
{was} swindled in a deal for {goods} and wants revenge|crime
{has} discovered a new route that cuts days off the journey, and is keeping quiet|road
{has} stopped selling {goods} entirely, and will not say why
{is} trading {goods} for something strange: bones, teeth, and old keys|mystery
{has} been rationing {goods} as though a siege is coming|military
{has} opened a stall selling suspiciously cheap {goods}|crime
{has} lost a whole caravan, cargo and guards, without a trace|road mystery
{is} paying double for {goods}, no questions asked
""")
table("what.religion", "Religion events", """
{has} been preaching that the end comes at the next new moon
{has} found {a relic}, and no two witnesses agree on where|treasure
{was} struck mute in the middle of the midnight rite
{has} been tending a shrine that no one else can find|mystery
{v:claim} to have been visited by a saint who wants something done
{has} desecrated a grave to make a point, or was framed for it|undead crime
{has} stopped aging since the last pilgrimage|magic mystery
{is} leading a procession to a place the temple has forbidden
{has} been healing the sick for free, and the temple is furious about it
{has} stolen the offerings, and the gods seem to be taking it personally|crime
{has} been seen speaking with an angel that no one else can see|mystery weird
{is} ringing a bell in the dead of night, and the bell has no tongue|undead weird
""")
table("what.undead", "Undead events", """
{was} seen walking the road three days after the burial|k:npc
{has} been seen leaving a crypt before dawn, and entering it again at dusk
{has} been leaving food at a grave every night, and it is being eaten
{was} found on a doorstep, cold and not at all dead|k:npc t:grim
{is} haunted by someone who keeps asking for a name|mystery
{has} dug up a grave that had been dug from the inside|t:grim
{has} a lantern that burns blue whenever the dead are near|magic
{has} been paying a gravedigger to dig more graves than there are bodies|crime t:grim
{has} been speaking with the dead and getting answers that are far too accurate|magic
{has} an assistant who never eats, sleeps, or blinks|magic k:npc
{has} stopped being able to cross running water|water mystery
{has} been recruited by something that sleeps beneath the churchyard|religion t:grim
""")
table("what.fey", "Fey events", """
{has} made a bargain, and the other party has come to collect
{was} led off the road by lights, and came back three years younger|k:npc
{has} stopped casting a shadow|weird
{has} been leaving cream and iron nails on the doorstep, and the cream is being taken
{has} received an invitation printed on a leaf, to a feast that starts at midnight
{has} won a game of riddles against something that does not lose
{has} been seen dancing in a ring with partners no one else can see
{has} traded away their name, and no one can remember it now|k:npc
{has} found a well that answers wishes, in the worst way|magic
{has} been speaking in rhymes since the last full moon|t:light
{has} befriended {fey.guise}, who turns out not to be what they seem
{has} planted a seed that sprouted overnight into something with a face|nature weird
""")
table("what.monster", "Monster events", """
{was} attacked by {a creature} and survived with a story nobody believes
{has} been feeding {a creature} in secret, and it is getting bolder
{has} tracked {a creature} to its den and is boasting about it
{has} found the tracks of {a creature} where there should be no tracks at all
{has} lost {n:2-6} head of livestock in a single night|nature
{has} been hired to hunt {a creature}, and has not come back
{has} claimed the bounty on {a creature}, but nobody has seen the body|crime
{has} befriended {a creature}, and the creature has befriended a few others
{was} dragged from their cart by something that left only claw marks and a single boot|road t:grim
{is} offering a reward for proof that {a creature} exists
{has} woken something by digging where they should not have|ruin
{has} learned that {a creature} is nesting beneath {street}|urban
""")
table("what.nature", "Nature events", """
{has} found a stand of trees that were not there last week|fey weird
{has} watched the {crop} wither overnight, though the neighboring field is untouched
{was} chased from the woods by something that did not make a sound|monster
{has} seen the river run backwards for an hour|water weird
{has} noticed that all the birds have left the valley|mystery
{has} been poisoned by water that tastes sweet|disease
{has} been herding animals that are not theirs, and the animals do not seem to mind
{is} the only one who can hear the forest talking|fey mystery
{has} tamed a creature of the wild that no one else can approach|monster
{has} found a sinkhole where the old well used to be|ruin underground
{has} burned a grove that had to be burned, and will not say why|crime
{has} been leaving offerings at a tree that is not on any map|religion fey
""")
table("what.ruin", "Ruin events", """
{has} found a sealed door beneath the cellar, and has been going down at night|underground
{has} been selling pieces of an old tomb to anyone who asks no questions|treasure crime
{has} bought a map to a place that should not exist|mystery
{has} cleared rubble from a collapsed gallery and found it had already been cleared, from the other side|underground
{has} been copying carvings from a wall that no one else can read|magic
{has} been digging beneath a ruined shrine, and the diggers have started sleepwalking|religion
{was} the last of an expedition that went down and did not come up|t:grim
{has} an ancient key and no idea what it opens|treasure
{has} a stone that hums whenever it is carried toward the old foundations|magic
{has} recovered {a relic} and is trying to find a buyer|treasure religion
{has} been mapping a ruin that is bigger on the inside than the outside|magic weird
{has} found a door that opens onto a different room each time|magic mystery weird
""")
table("what.magic", "Magic events", """
{has} been experimenting with something that makes every candle in the street gutter
{has} stolen a spellbook that is rumored to bite|crime
{has} woken up with a new talent and no memory of acquiring it|mystery
{has} an apprentice who is now more powerful than their master|craft
{has} been seen casting spells in a language no scholar recognizes|mystery
{was} caught in a wild surge that turned every {goods} in the shop to something else|trade t:light
{has} summoned something and lost control of the terms|monster t:grim
{has} a mirror that shows tomorrow's customers|trade weird
{has} sold a love charm to the wrong person|crime t:light
{has} an alchemical brew that can make anyone tell the truth, for an hour|crime politics
{has} been bottling storms|weather craft
{has} cast something over the whole district, and nobody has noticed except the cats|weird
""")
table("what.military", "Military events", """
{has} deserted, and taken the pay chest|crime
{has} been ordered to march on a town that has never given offense|politics
{is} recruiting by the barrel-load, with a bounty for every volunteer
{has} lost a whole patrol without finding a single body|mystery t:grim
{has} been seen meeting with an officer from the other side|politics crime
{has} been buying up {goods} like a siege is coming|trade
{was} given orders to close the roads, and will not say who gave them|road politics
{has} refused an order, and everyone is waiting to see what happens
{has} found an old fortification that is still, somehow, garrisoned|ruin mystery
{has} been drilling by night in a field where no one can see
{has} surrendered without a fight, and no one will say why
{has} been promoted three times in a month, and nobody can remember a single battle
""")
table("what.family", "Family events", """
{has} a child nobody knew about, who has just turned up with a letter|k:npc
{is} feuding with their sibling over an inheritance that may not exist|k:npc
{has} not been seen since the wedding, and no one will talk about the wedding|mystery
{has} been disowned for marrying someone from the wrong side of the river|k:npc
{is} hiding a relative in the attic who is supposed to be dead|mystery
{has} been told the family trade is cursed, and has decided to find out why|magic
{has} found a diary that tells a very different story of the family's fortune|treasure
{is} the last of the line, and the last hope of a family that owes everyone|k:npc
{has} sworn a family oath that is about to come due
{has} two spouses, in two towns, and a third in the planning|k:npc t:light
{has} been named in a will that three other people say is forged|crime
{has} taken in every orphan in the street, and the street is not sure how to feel
""")
table("what.mystery", "Mystery events", """
{has} vanished, leaving the door barred from the inside
{has} been receiving unsigned letters with a different coin in each
{v:keep} dreaming of the same stairway, and has begun to find it|magic
{was} found at the bottom of a well that has no water|t:grim
{has} been seen in two places at once, on the same night|magic
{has} an alibi that depends on a witness who died last year|crime undead
{has} been leaving chalk marks on doors, and those households have all had bad luck
{has} been asking questions about a death everybody agreed was natural|crime
{has} found a message in a bottle that was written in their own hand|magic weird
{has} been followed by someone whom nobody else can see|weird
{has} found a room in the house that was not there before|magic weird
{has} locked themselves in and will not come out, but the lights move about at night
""")
table("what.disease", "Disease events", """
{has} come down with the gray cough, and the healers are afraid
{has} been quarantined behind a locked door, and the neighbors have heard singing|t:grim
{has} found out that the well is fouled, and has said nothing|urban
{was} bitten by something and has been much too calm since|monster
{is} selling a cure that works for exactly one week|crime trade
{has} been burning sickbeds in the middle of the night|t:grim
{has} brought a sickness from the road that spreads when people sleep|road
{has} been feeding everyone from a stew pot that never empties, and the town has gone strangely quiet|weird
{has} blamed the plague on a neighbor, and a mob has started to listen|crime
{has} survived a plague that killed everyone around them, and is now being sought
{has} started a quarantine that the council did not order|politics
""")
table("what.weather", "Weather events", """
{was} caught out by {weather.odd}, and came back changed|k:npc
{has} been predicting storms days in advance, to the hour|magic
{has} watched {weather.odd} fall only on one street|urban weird
{v:claim} the weather is following them|k:npc weird
{has} lost the roof to a wind that no one else felt|weird
{has} seen the sky go dark at noon, and not for an eclipse|mystery
{has} taken shelter from the storm in a house that was not there yesterday|mystery weird
{has} been selling charms against {weather.odd}, and they seem to work|trade magic
{has} said the thaw is coming early, and a lot of people have bet on it|trade
{has} stopped a flood by doing something nobody understands|magic
""")
table("what.festival", "Festival events", """
{has} been chosen to lead the procession, and wants out
{has} been sabotaging preparations for the festival, one cart at a time|crime
{has} a mask for the festival that nobody remembers commissioning|mystery
{has} been caught selling tickets to a feast that is not being held|crime trade
{has} won the contest by a method that no judge can explain|magic
{has} sworn to expose a scandal at the festival's closing ceremony|politics
{has} written a play that tells the whole town's secrets|mystery
{has} hired every musician within thirty miles, leaving the rest of the town silent|trade
{has} been planning to run off during the fireworks|family
{has} vowed that this year the festival's king will not be crowned|politics
{has} found a costume that fits, and will not take it off|magic weird
{has} brought a performing troupe that the town swears it has seen before|mystery
""")
table("what.craft", "Craft events", """
{has} finished a masterwork that the commissioner refuses to collect
{has} been commissioned by a stranger to make something with no obvious purpose|mystery
{has} made a lock that cannot be picked, and a key that cannot be found
{has} been working in secret on a bell that is far too large for the tower
{has} lost the recipe that made the shop famous
{has} found that the new apprentice's work is better than their own
{has} been rejected by the guild for using a forbidden technique|trade
{has} made a blade that has never been cleaned and is never dirty|magic
{has} been making clocks that all strike a different hour|magic weird
{has} sworn to build a thing before the year turns, and the thing is looking back|magic weird
{has} been buying iron in quantities no honest smith would need|military crime
""")
table("what.treasure", "Treasure events", """
{has} stumbled onto a cache of old coins that are not quite legal tender
{is} selling maps to a hoard, each of them a little different|crime
{has} lost {a treasure.item} in a game of chance, and wants it back
{has} found {a treasure.item}, and has no idea what it is worth
{is} paying very well for {goods} and asking no questions|trade
{has} buried something in the garden and has not been seen since|mystery
{has} inherited a debt that comes with a very valuable deed|family
{has} a family heirloom that three separate parties have tried to steal|crime family
{has} found a stash left by someone who is still alive and looking for it|crime
{has} been offered a fortune for something worthless, and refuses to sell|mystery
{has} dug up a chest, and the chest has dug up them|monster magic t:light
""")
table("what.generic", "General events", """
{was} seen leaving at night with a heavy sack
{has} suddenly paid off every debt in town
{has} been asking after strangers who have not yet arrived
{has} not slept in days, and will not say why
{was} seen arguing with {a occupation} in the street
{has} locked the shop and gone, with the lamps still burning
{has} a new patron, and a new set of manners
{has} been unusually generous lately
{has} been carrying a letter that cannot be delivered
{has} left in a hurry, leaving everything behind
{has} started hiring people for work that nobody will describe
{has} been asking about the party, by description
""")
table("what.generic.sf", "General events (Starfinder)", """
{has} been seen docking a ship with no registry|p:sf
{has} sold a month of station air allowance to the wrong people|p:sf
{has} a cargo manifest that does not match the weight of the crates|p:sf
{has} woken from cold-sleep with a coordinate no chart contains|p:sf
{has} been rewriting the station's access logs after hours|p:sf
""")

# ============================================================ where
table("where", "Where (a place in your campaign, or a generated one)", """
{campaign.location}
""")
table("where.any", "Where (generated)", """
{where.urban}|urban|3
{where.wild}|wild|3
{where.underground}|underground|3
{where.road}|road|2
{where.water}|water|2
{where.station}|p:sf|2
""")
table("where.detail", "Place details (appended)", """
, beside {landmark}
, where the smell of {smell} is strongest
, within sound of {sound}
, just out of sight of {landmark}
, in plain view of everyone who chooses not to look
, with every door unlocked
, three streets from anywhere useful
, under a sky that does not look quite right
, a place the locals never mention
""")
table("where.urban", "Places in a settlement", """
in the back room of {tavern.name}{where.detail?30}
behind {shop.name} on {street}{where.detail?30}
in the cramped cellars under {street}{where.detail?30}
in a tannery yard off {street}
on {street}, in a house with all the shutters closed
at the fish market before dawn
in the temple's dormitory|religion
in the bell tower|religion
at the public well{where.detail?30}
in the lamp-lit stacks of the town archive|mystery politics
in the gatehouse|military
on the roof of the guildhall|trade politics
in the rows of the night market|trade crime
in the old sewers beneath the market|crime underground
at the crumbling almshouse|family
at a boarded-up bathhouse|mystery
in a room above {shop.name}
in the graveyard behind the chapel|undead religion
at the cattle yards on the edge of town|nature
in the quarantine ward|disease
in a debtors' prison|crime
in a derelict theater|festival mystery
in the lower docks|water crime
at {tavern.name}, in the corner no one sits in{where.detail?25}
on the town wall, at the changing of the guard|military
at the abandoned guildhall of the {name.noun} {name.collective}|trade mystery
""")
table("where.wild", "Places in the wilds", """
at a lonely crossroads marked with a cairn{where.detail?25}
in a drowned orchard|water nature
in the shadow of a lightning-struck oak|weather
in a woodland clearing where nothing grows|fey weird
beside a mill that stopped turning|craft
on a ridge above the old road|road
in a shepherd's hut on the high pasture|nature
in a hollow ringed with standing stones|fey ruin
at a hermit's cabin deep in the pines|religion mystery
in a bog where lights drift at dusk|fey undead
beside a waterfall with a cave behind it{where.detail?25}
in a cornfield that no one will harvest|nature
in a charcoal-burners' camp|craft
at the edge of a haunted wood|undead fey
in an abandoned logging camp|craft
at a hunter's lodge, shuttered for the winter|nature
on a barrow-covered hill|undead ruin
in a meadow where the flowers bloom in winter|fey weird
at a standing well in the middle of nowhere|mystery
in a ravine full of fog|weather
in a ruined watchtower on the ridge|military ruin
at a ford that never runs low|water
""")
table("where.underground", "Places underground", """
in a collapsed gallery|ruin
along a tunnel lit only by glow-moss
in a flooded cistern|water
at a fungus farm in a lamp-lit cavern|nature trade
in a dwarven waystation, long abandoned|ruin
beside an underground river|water
at a tollhouse where two tunnels meet|trade
in a vault behind a sealed door|treasure
in a cavern with a ceiling too high to see
in a mine that was closed after the third collapse|craft
at a market in a cavern where everything is sold by lantern-light|trade crime
in a drowned chapel beneath the old city|religion undead
in a bone-lined catacomb|undead
in a stalactite hall
in a shaft with no bottom that anyone has found|mystery
at a goblin scavengers' camp built into a cave mouth|crime trade
at a lamplighters' station, the last light before the deep{where.detail?20}
in a lichen forest, silent and glowing|nature
in a crystal cave humming faintly|magic
at a cross-tunnel with a very old, very polite guard post|military
in a ruined temple whose congregation went below and never came back|religion ruin
in a grotto with a lake as still as glass{where.detail?20}|water
""")
table("where.road", "Places on the road", """
at a toll bridge|trade
at a burned-out waystation|crime
at a roadside shrine with fresh offerings|religion
at a crossroads inn
in a caravan camp for the night|trade
on a switchback with a view of a long drop
at a ford swollen by rain|water weather
at a wayside well
at a gibbet where the body has gone|crime undead
along a causeway through the marsh|water
at a border post nobody mans anymore|military
at a ruined milestone|ruin
on a stretch of road everyone avoids at dusk|mystery
at the last inn before the pass|weather
in a drover's rest stop|nature
in a squatters' camp under the old bridge|crime
at a quarry that stopped working|craft
at a post house with all its horses missing|mystery
in a roadside market in a field|trade festival
on a mountain pass where the snow never melts|weather
""")
table("where.water", "Places on the water", """
on a river barge, at anchor|trade
at the ferry landing
aboard a ship held in quarantine|disease
at a lighthouse that no longer shines|mystery
on a stretch of river where the current reverses|weird
at a dockside warehouse|trade crime
on a flooded street, from the roof of a house|weather
in a fishing village, in the net loft
at a drowned bridge|ruin
on a salt marsh causeway at low tide
on a sandbar that only appears at midnight|mystery
at an island chapel|religion
in a boathouse on a still lake
at a lock and weir|craft
on a smuggler's skiff|crime
""")
table("where.station", "Places on a station or ship (Starfinder)", """
on the promenade deck of a trade station|p:sf
in a docking bay with a leaking seal|p:sf
in the hydroponics level|p:sf nature
in a cargo hold marked as medical supplies|p:sf crime
in a colony dome with a cracked seal|p:sf
in the engine room, where the noise hides everything|p:sf
""")

# ============================================================ when
table("when.past", "Times in the past", """
three nights ago
last market day
at dawn yesterday
{n:2-6} days ago
a fortnight ago
just before the last full moon
the night the bells rang by themselves|weird
during the first frost||1|winter/autumn
since midsummer||1|summer/autumn
at the turn of the tide|water
not an hour after sunset
last holy day
about a month back
sometime in the small hours
on the night of the storm|weather
the week the harvest failed||1|autumn/winter
after the last caravan left|trade
before anyone was awake
two winters ago, and again last week
at the stroke of midnight
this past season
since the thaw||1|spring
since the first snow||1|winter
""")
table("when.future", "Times in the future", """
by the end of the week
within {n:2-9} days
at the next new moon
before the first snow||1|autumn/winter
before {campaign.event}
the night after {campaign.event}
by harvest-time||1|summer/autumn
when the caravans return|trade
before the next toll is due|trade
once the roads open||1|winter/spring
at the next change of the guard|military
as soon as the river drops|water
at dusk tomorrow
as the festival begins|festival
""")
table("when.now", "Right now", """
right now
as we speak
even as you listen
at this very moment
tonight
this very hour
""")
table("when.recurring", "Repeating times", """
every new moon
every night at the same hour
each time the bells ring
on the last day of every month
every market day|trade
whenever it rains|weather
every time the lamps are lit
when the moon is dark
every seventh night
each time a stranger arrives
""")
table("when.deadline", "Deadlines", """
within {n:2-9} days
before the next new moon
by market day|trade
before {campaign.event}
before the tide turns|water
before the caravan leaves|trade road
by the end of the week
before the first snow||1|autumn/winter
by nightfall
before the trial|politics crime
in time for the harvest||1|summer/autumn
no later than the next toll|trade
""")
table("when.during", "Moments in a scene", """
just as you are about to leave
right when the plan seems to be working
at the worst possible moment
halfway through your task
as night falls
just after you let your guard down
when you stop to rest
the moment someone says all is well
while you are distracted
at the first sign of trouble
as the weather turns|weather
""")
table("when.event.generic", "Events (generated)", """
the next market day
the midsummer fair
the harvest festival
the founders' feast
the next full moon
the council vote
the changing of the guard
""")
table("when.rumor", "When (a rumor)", """
{when.past}||5
{when.recurring}||2
{when.future}||2
{when.now}||1
""")
table("when.comp", "When (a complication)", """
{when.during}||6
{when.now}||2
{when.future}||2
""")
table("when.hook", "When (a hook's deadline)", """
{when.deadline}||6
{when.future}||2
{when.now}||1
""")
table("when.move", "When (a faction's move)", """
{when.past}||3
{when.now}||3
{when.future}||3
{when.recurring}||1
""")

# ============================================================ why
table("why", "Why", """
{why.generic}||4
{why.crime}|crime|3
{why.politics}|politics|3
{why.trade}|trade|3
{why.religion}|religion|3
{why.undead}|undead|3
{why.fey}|fey|3
{why.monster}|monster|3
{why.nature}|nature|3
{why.ruin}|ruin|3
{why.magic}|magic|3
{why.military}|military|3
{why.family}|family|3
{why.mystery}|mystery|3
{why.disease}|disease|3
{why.weather}|weather|3
{why.festival}|festival|3
{why.craft}|craft|3
{why.treasure}|treasure|3
""")
table("why.comp.base", "Reasons behind a complication", """
because they want something from the party
because they were told to by someone they fear
because they honestly think they are helping
because they have mistaken the party for someone else
because they are afraid of what happens if they do not
because they are being paid to
because they are bored, and the party is interesting
because someone has told them a lie about the party
because they were here first
because they have nothing left to lose
because of an old grudge against someone who looks like the party
because they think it is a test
because they are hungry and out of options
because the alternative is a worse trouble
because the rules say they must
because someone is watching and they need to look busy
because it was the only plan they had
""")
table("why.comp", "Why (a complication)", """
{why.comp.base}||6
{why.crime}|crime|2
{why.politics}|politics|2
{why.trade}|trade|2
{why.religion}|religion|2
{why.undead}|undead|2
{why.fey}|fey|2
{why.monster}|monster|2
{why.nature}|nature|2
{why.ruin}|ruin|2
{why.magic}|magic|2
{why.military}|military|2
{why.family}|family|2
{why.mystery}|mystery|2
{why.disease}|disease|2
{why.weather}|weather|2
{why.festival}|festival|2
{why.craft}|craft|2
{why.treasure}|treasure|2
""")
table("why.generic", "Reasons (any story)", """
because of a debt to the wrong people
to settle an old score
hoping to prove a point to a rival
to protect someone who cannot protect themselves
after a letter arrived with news they cannot bear
because someone has been paying well for a blind eye
out of pure spite
to keep an old promise
because they believe no one else will do it
hoping to buy their way out of a worse situation
in order to hide something from a spouse
following a dream they cannot shake
after a bet made in a tavern, with an unreasonable stake
because a stranger promised them everything
to keep up appearances
to make sure a secret stays buried
because they have been told it is for the greater good
in a bid to win back a lost reputation
to get a head start on everyone else
because they simply cannot stop
hoping that no one connects it with them
out of fear of what will happen if they stop
to impress someone who is not even looking
after losing everything they had
to feed a family that has run out of options
because an old friend asked, and they could not say no
for reasons that make perfect sense to them and no one else
to find out whether the stories are true
because the alternative is worse
hoping the problem will solve itself
to cover up an embarrassing mistake
because they were told it would only take a day
to get revenge for something no one remembers
""")
table("why.crime", "Reasons: crime", """
to pay off a smuggling debt before the interest kills them
to frame a rival for the job
because a crime boss has promised protection in return
to clear their name before the watch closes in
to get out from under a debt before the collectors come back
because the watch is closing in and someone else should take the fall
""")
table("why.politics", "Reasons: politics", """
to swing a vote before the council meets
hoping for a title that comes with immunity
to keep a scandal out of the gossip mills
to undermine an official they despise
to be on the right side of the next council vote
because an old ally has changed sides and needs to be answered
""")
table("why.trade", "Reasons: trade", """
to corner the market before the prices turn
because a contract is about to expire
to ruin a competitor
because the caravan is due and the cargo is not
to settle a contract before a rival can undercut it
because a late shipment is about to ruin a good name
""")
table("why.religion", "Reasons: religion", """
because they have been told the gods demand it
to prove the faith before a skeptical congregation
in penance for a sin they will not name
because a prophecy points to this very week
to keep a vow made at the last holy day
because the temple has gone quiet and someone should ask why
""")
table("why.undead", "Reasons: undead", """
because they cannot bear to let go of someone they lost
to answer a voice that will not stop asking
because the dead have been very persuasive
to lay a restless spirit that has followed them for years
because something in the graveyard has begun to answer back
to give a dead friend the rest promised long ago
""")
table("why.fey", "Reasons: fey", """
to honor a bargain they do not remember making
because something old and polite has asked them to
to repay a kindness that was a trap
because they could not refuse a gift
to settle up with something that keeps very exact accounts
because a promise made at midsummer is about to fall due
""")
table("why.monster", "Reasons: monsters", """
because the beast has been taking what they love
to claim the bounty before someone else does
to prove it can be done
because it leaves them alone if they do
because the beast has started coming closer to the houses
to stop the neighbors from taking matters into their own hands
""")
table("why.nature", "Reasons: nature", """
to appease whatever lives in the woods
because the land is dying and nobody will listen
to save a harvest that is already lost
because the old ways say so
because the old signs say the season will turn badly
to repay a debt to the land that nobody else remembers
""")
table("why.ruin", "Reasons: ruins", """
to reach whatever lies below before anyone else does
because the carvings say it must be opened on a certain night
to prove an old theory that cost them their post
hoping the ruin will pay the debts
because someone else is already digging at the same site
to learn what was sealed there before it is opened by accident
""")
table("why.magic", "Reasons: magic", """
because the experiment was almost finished
to undo a spell that went badly wrong
hoping to be accepted by the college
because the spell demanded it
because a spell is slowly wearing off and the results will not be pretty
to keep a rival's apprentice from finishing a working first
""")
table("why.military", "Reasons: military", """
on orders they did not question
to avoid a court martial
because the pay has stopped and the sergeant is angry
to hold a line that someone forgot to tell them to leave
because the garrison is short-handed and nobody official will admit it
to avoid being posted somewhere worse
""")
table("why.family", "Reasons: family", """
to protect the family name
because blood is thicker than a witness statement
to win back a parent's approval
because the family curse is coming due
because a quarrel between relatives is about to become public
to keep a promise made to someone who can no longer ask
""")
table("why.mystery", "Reasons: mysteries", """
because something does not add up, and they cannot leave it alone
to find out who is writing the letters
because the answer is somewhere in the house
because someone finally asked the right question
because the same strange detail keeps turning up and nobody can explain it
to find out who has been watching the house
""")
table("why.disease", "Reasons: disease", """
to keep the sickness from spreading
because the cure costs more than they have
to hide the first signs from the neighbors
because the healers have stopped answering
to learn what a neighbor really died of
to keep the sickness out of the one household that cannot afford it
""")
table("why.weather", "Reasons: weather", """
to save the harvest from the coming storm
to get the caravans out before the pass closes
because the signs have never been wrong before
to sell charms before the rain
because the storms are no longer coming when the almanac says
to get everything under cover before the sky turns
""")
table("why.festival", "Reasons: festivals", """
to make this the best festival in living memory
to steal the show
because this is the only night everything is permitted
to settle a score under the cover of masks
to win a wager made at last year's celebration
because a rival has promised to ruin the evening
""")
table("why.craft", "Reasons: craft", """
to finish the masterwork before the guild inspection
because the commission pays better than the shop ever did
to prove a rival's technique is a fraud
because the thing they are making has started to want things
to prove the work is as good as the master's
because a commission cannot be late again
""")
table("why.treasure", "Reasons: treasure", """
to claim a hoard that has no heir
because the map is only good until the next full moon
to pay for something that is not for sale
because the rumor of gold has travelled further than the gold
because a fortune is only a fortune until the heirs hear of it
to buy back something sold in a hard winter
""")

# ============================================================ skills and small helpers
table("skill.any", "Skills", """
Acrobatics
Arcana
Athletics
Crafting
Deception
Diplomacy
Intimidation
Medicine
Nature
Occultism
Performance
Religion
Society
Stealth
Survival
Thievery
""")
table("skill.phys", "Physical skills", """
Athletics
Acrobatics
Stealth
Thievery
""")
table("skill.social", "Social skills", """
Diplomacy
Deception
Intimidation
Performance
Society
""")
table("skill.know", "Knowledge skills", """
Arcana
Nature
Occultism
Religion
Society
Crafting
Medicine
Survival
""")
table("spell.util", "Useful spells", """
a light cantrip
mage hand
grease
gust of wind
darkness
knock
silence
mending
ghost sound
unseen servant
""")

# ============================================================ rumor extras
table("rumor.knows", "How a rumor's teller knows", """
hears everything
knows everyone's business
claims to have seen it
heard it from someone who was there
was there and will not say more
is paid by someone to repeat it
repeats it to anyone who will listen
has a grudge against the person in question
has a good reason to lie
knows the real story but tells a different one
""")
table("rumor.source", "Who is telling the rumor", """
{a person.adj} {occupation} who {rumor.knows}|||3
a drunk {occupation} at {tavern.name}
a pair of children who were not supposed to be out
{campaign.npc}|k:npc|3
a letter slipped under the door, unsigned
a notice pinned to the board outside {tavern.name}
graffiti on the wall of the temple
a traveling tinker who sells news with the pots
the barber, who hears everything
a merchant's apprentice, in a hurry to be elsewhere
an old woman on a bench who has seen it all
a watchman off duty and in his cups
the town crier, who was told to say nothing and said it anyway
a pilgrim on the road, three towns away
a caravan guard who heard it at the last stop|road
a ferryman who heard it from a passenger who is now missing|water
two gossiping dyers across the street|urban
the cook of {tavern.name}, over a hot pan
an anonymous broadsheet, printed on bad paper|urban
a hedge witch who read it in the tea leaves|magic
a stable-boy who heard it through a keyhole
a fortune teller who swears she saw it in the cards|magic mystery
the gravedigger, who has nothing to do all day but listen|undead
a whisper passed along a line at the well
a traveling bard who has already turned it into a song|festival
a drunk who tells it differently every night
a tunnel warden who passes news from lamp to lamp|underground p:underground
a goblin scavenger who trades rumors for scrap|underground crime p:underground
""")
table("truth.proof", "How a true rumor can be proven", """
someone is already trying to silence the source
there is physical evidence within a day's walk
a second witness will say the same if asked politely
the person involved is about to make it obvious
it is on the verge of getting worse
the person who started it wants the truth to come out
a keen eye can confirm it with a quick look
the details match an old, forgotten record
""")
table("truth.twist", "Twists on a mostly true rumor", """
{@who.short} is acting under duress
the location is wrong by a street
it happened to someone else first
the motive is not what people think
it is already being handled, badly
someone else is paying for all of it
the timing is off by a week
it is part of a larger plan that nobody has seen
{@who.short} is not the one in charge
{@who.short} is trying to stop it, not start it
there is a witness no one has talked to
it is only the first step
""")
table("truth.half", "A half-true rumor", """
something did happen, but not what {@source} claims
the person is real, but this is not their doing
the place is right, and everything else is wrong
the story is true for someone else entirely
it will happen, but later than people say
it happened, but the victim is the one who started it
only the first half is true
the cause is real; the effect is not
""")
table("truth.escalation", "When a rumor understates the danger", """
it is the first sign of something much worse
the next incident will be larger
someone is counting on it being dismissed
the real danger is smaller, but the cover-up is not
it has already spread to the next town
the person behind it is just getting started
""")
table("truth.outdated", "When a rumor is out of date", """
it was resolved a few days ago, quietly
the person has moved on and the place is empty
it began as described, but the situation has changed
the situation reversed after a rival stepped in
it was true last season, and the details are all wrong now
it was settled with a payment that nobody will discuss
""")
table("truth.mixup", "What a garbled rumor got mixed up with", """
an entirely different {occupation}
a story from three towns over
a play that came through last year
two separate incidents that happened to share a street
a rumor spread on purpose to cover another
the town's oldest ghost story
""")
table("truth.planter", "Who planted a false rumor", """
{npc.named}||3
{campaign.faction}||3
a rival of {@who.short}||2
{faction.generic}||2
{campaign.npc}||2
""")
table("truth.planter.why", "Why a rumor was planted", """
to draw attention away from something else
to ruin {@who.short}'s standing
to see who reacts
to flush out one particular person
to make sure someone investigates the wrong place
to test whether the town can keep a secret
""")
table("truth.mistake", "How an honest mistake happened", """
a mis-heard conversation
a smudged letter
a drunk witness
two people with the same name
a misread omen
""")
table("rumor.truth", "How true the rumor is", """
Completely true, and {truth.proof}.||||16
Mostly true, but {truth.twist}.||||24
Half true: {truth.half}.||||18
Exaggerated. The real situation is smaller, but {truth.escalation}.||||12
Out of date: {truth.outdated}.||||8
Garbled. The details have been mixed up with {truth.mixup}.||||8
False, and planted on purpose by {truth.planter}, {truth.planter.why}.||||8
False, an honest mistake born of {truth.mistake}.||||6
""")
table("rumor.check", "How to check a rumor", """
Gather Information with Diplomacy {dc}; or Recall Knowledge ({skill.know}) {dc:hard} to tell the true from the false.
Ask around with Diplomacy or Society, {dc}. A critical success also reveals what the teller wants.
A quick look on the ground: {skill.any} {dc}. Failing by 5 or more points the party at the wrong lead.
Gather Information {dc}, or {skill.know} {dc:easy} if someone in the party knows the subject.
Investigate the source with Perception or Society, {dc}, and weigh how much to believe.
Pay for information ({gp:tiny}) and make a Diplomacy check at {dc:easy}.
""")
table("rumor.hook", "What the party can do about a rumor", """
Follow the source back to whoever told them.
Watch the place for a night and see who comes.
Confront the subject directly, and see what they give away.
Sell the rumor to someone who would pay for it.
Warn whoever is at risk, and be ready to be wrong.
Ask the local authorities, and notice who answers too quickly.
Bring it to {campaign.faction}, who will want to know.
Offer to look into it for a fee.
Ignore it, and watch to see if someone else acts first.
Spread a different story and see which version comes back.
Visit the place yourselves and find out what is actually there.
Find the one person who could prove it and persuade them to talk.
Trace where the money goes.
Take it to the temple, and see who is offended.
Use it as leverage against the person it concerns.
""")

# ============================================================ complications
table("what.comp", "What (a complication)", """
{what.c.travel}||3|scene:travel/scene:any
{what.c.dungeon}||3|scene:dungeon/scene:any
{what.c.social}||3|scene:social/scene:any
{what.c.downtime}||3|scene:downtime/scene:any
{what.c.any}||2
""")
table("what.c.travel", "Travel complications", """
{v:block} the way with a broken-down wagon and a very long argument
{is} offering a shortcut that is suspiciously well-lit
{is} demanding a toll that was not there yesterday|trade
{was} found by the roadside, injured, and clinging to a satchel|k:npc
{v:spook} the pack animals, and a whole day's supplies are scattered across the road
{is} following the party at a distance, and not very well
{has} washed out the ford, and the only way around is through someone's land|water
{v:camp} on the party's chosen site and will not leave
{v:offer} to guide the party for a price that is far too low
{is} racing the party to the same destination, and cheating
{v:leave} a warning cairn on the path, of the kind that means turn back|mystery
{has} hired the only available ferry for the entire week|water trade
""")
table("what.c.dungeon", "Dungeon complications", """
{has} been through here before, and left everything in a worse state
{is} resting in the next room, and will not be pleased to be woken
{v:set} a trap that goes off if anyone rushes
{has} sealed the way back, from the other side
{is} bargaining with something deeper in, and the party has just interrupted them
{v:collapse} the ceiling behind the party with a single clever move
{has} been here for years, and thinks the party are the intruders
{v:carry} a map of this place that is not accurate, and the party has seen it
{has} found the party's tracks and is already ahead of them
{is} guarding the only unlocked door, and will not be bribed
{v:flood} the lower passage, and the water is rising|water
{v:leave} lights burning, which means someone is still home
""")
table("what.c.social", "Social complications", """
{has} just found out that the party has been asking questions
{is} about to make a scene in the middle of the room
{has} mistaken the party for someone else entirely
{is} demanding a favor the party cannot refuse in public
{v:offer} the party a deal that comes with a catch they have not noticed
{is} flirting with the wrong person, and the right person is watching|k:npc t:light
{has} overheard something that could end the party's welcome
{is} insulted by something a party member said, or thinks so
{is} insisting the party settle a debt that is not theirs
{v:bring} an unexpected guest who changes the mood of the room
{is} about to be arrested, and will name the party as witnesses|crime
{has} planned a surprise, and it is not a pleasant one
""")
table("what.c.downtime", "Downtime complications", """
{v:turn} up with a very good reason to cancel the party's plans
{has} opened a shop across the road selling exactly what the party does|trade
{is} suing, or threatening to, over a misunderstanding|politics
{has} quietly raised the rent on everything the party owns|trade
{has} come down with a sickness that is going around|disease
{has} sent a letter that must be answered by the end of the week
{has} lost the party's belongings, and found them again, slightly changed
{has} given the party's name as a reference, without asking
{has} made the party an offer that sounds like an ordinary job
{v:arrive} to settle an old debt
{has} been spreading a story about the party that is not entirely wrong|k:npc
{v:pay} the party an unexpected visit, with an unexpected guest
""")
table("what.c.any", "General complications", """
{v:turn} up at the worst possible moment
{is} offering help that comes with strings attached
{has} mistaken the party for someone else
{has} a problem that is, inconveniently, also the party's problem
{is} very obviously lying, and very obviously not worth confronting
{has} stolen something the party needed within the hour
{v:arrive} with news that changes the plan
{has} a deadline that has just become the party's deadline
""")
table("comp.severity", "Severity of a complication", """
Minor: it costs time or small resources, and nobody is in danger. Handling it is a {dc:easy} check.||||5
Moderate: it costs real resources or puts someone at risk. Handling it is a {dc} check.||||4
Serious: it can sink the mission if handled badly. Expect a {dc:hard} check, or a fight.||||2
""")
table("comp.resolve", "Ways to resolve a complication", """
Persuade them with {skill.social} ({dc}), or pay them off for {gp:tiny}.
Out-think it with {skill.know} ({dc}). A critical success turns it to the party's advantage.
Muscle through with {skill.phys} ({dc:hard}). A failure costs a day or a point of equipment.
Sneak around with Stealth ({dc}), or Survival ({dc:hard}) in the wild.
Let it burn itself out. It takes {n:2-4} hours, and someone else may profit.
Use {spell.util}, which might help or just make the problem louder.
Hand it to {campaign.faction}, who would be glad of the chance.
Turn it into a distraction with {skill.any} ({dc}), then slip away.
Face it head-on. A fight fits here, at a Low or Moderate threat.
Wait for help to arrive: {n:2-4} hours, with a risk it arrives on the wrong side.
""")
table("comp.ifignored", "If a complication is ignored", """
It gets worse by the next scene.
Someone else deals with it, and expects a favor in return.
The party loses a day.
A rumor starts, and it is not kind.
It becomes a recurring problem.
The party's standing with {campaign.faction} suffers.
Nothing happens, which is itself a story.
It follows the party to the next town.
Someone gets hurt, and people remember who was nearby.
""")

# ============================================================ hooks
table("festival.which", "Festivals and gatherings", """
the harvest festival
the midsummer fair
the founders' feast
the lantern procession
the night market
the guild feast
the market-day fair
""")
table("mask.kind", "Masks", """
plain white mask
painted tin fox mask
gilded stag mask
mask of patched leather
pale porcelain mask with a cracked cheek
beaked mask stuffed with dried herbs
plain black half-mask
mask of woven reeds
carved wooden owl mask
tarnished silver mask with no mouth
""")
table("task", "What a patron wants done", """
{v:want} someone to recover {a treasure.item} before it is sold|treasure crime
{v:need} a trustworthy escort for {a person.adj} {occupation} who must not be seen|politics mystery
{v:want} proof that {official} has been taking bribes|politics crime
{v:want} the person behind the forged {docs} found, quietly|crime
{v:need} a message delivered to someone who does not want to be found|mystery
{v:want} a missing {occupation} found, alive if possible|mystery family
{v:hire} the party to guard a shipment of {goods} that is certain to be targeted|trade crime
{v:want} {a creature} dealt with before it kills again|monster
{v:ask} for a ruined shrine to be cleaned out, and for no questions about what is inside|religion ruin undead
{v:need} help getting a sick relative to a healer who will not come to them|family disease
{v:want} someone to quietly watch a rival, and report only what is useful|crime politics
{v:want} an old grave opened, and an old promise kept|undead family
{v:need} a road, bridge, or ford cleared of whatever has been troubling it|road monster nature
{v:want} the party to be seen at {festival.which} wearing {a mask.kind}|festival crime
{v:ask} for a map to be completed, promising the rest will pay for itself|ruin treasure
{v:want} a stolen ledger returned before anyone reads it|crime trade
{v:need} a debt collected from someone who has gone to ground|crime trade
{v:want} a spell broken before it spreads|magic disease
{v:want} the party to testify at a trial, and to say the right things|politics crime
{v:need} a rare ingredient fetched from somewhere dangerous|magic craft nature
{v:want} someone to take their place at a meeting and not be recognized|politics mystery
{v:ask} the party to stand watch over a place for one night, and not go inside|mystery undead
{v:need} the border crossed with something that is not on the manifest|crime military
{v:want} a prisoner rescued before sentence is carried out|military politics
{v:want} a lost heirloom recovered from somewhere nobody will talk about|family treasure ruin
{v:need} a delivery made to a hermit who has not answered in months|religion mystery
{v:want} an inheritance dispute settled before blood is spilled|family politics
{v:want} someone to find out why the lamps keep going out|mystery magic underground
{v:ask} the party to escort a caravan through a stretch of road everyone avoids|trade road
{v:need} a rival's work sabotaged, delicately|craft crime
{v:want} a plague's source found before the quarantine is lifted|disease
{v:ask} for peace to be kept at a festival that is already at breaking point|festival politics
{v:want} an alliance sealed with a gift that must reach its destination intact|politics trade
{v:want} the truth behind a local legend, even if it ruins the legend|mystery ruin
{v:need} a lost expedition found, or at least its journals|ruin t:grim
""")
table("hook.reward", "Rewards", """
{gp:medium} up front and the rest on completion
{gp:small} and a favor owed
a minor magic item of the party's choosing, from the patron's stock|L1-8
the deed to a small property that comes with a problem
{gp:large}, but only if it is done quietly
introductions to people who matter
a rare book of lore that the patron cannot read
the patron's gratitude, which turns out to be worth quite a lot
free lodging for the rest of the season
a map to something valuable
an unused debt to be called in later
{gp:tiny} and a very good meal
""")
table("hook.twist", "Twists on a hook", """
The patron is not telling the whole truth.
The target is not what it seems.
Someone else has hired another group for the same job.
The job is a test.
The thing sought is already gone.
The patron will not survive to pay.
The real client is {npc.named}.
The task is a cover for a larger scheme.
The item is cursed in a way that only matters later.
The reward is real, but the debt attached to it is larger.
The person to be found does not want to be found.
The place is guarded by someone sympathetic.
Doing the job will anger {campaign.faction}.
The patron is being watched.
""")
table("hook.opposition", "Opposition to a hook", """
A rival party is after the same thing.
{campaign.faction} would rather it failed.
The local watch has already looked, and given up.
Someone inside the patron's household is working against them.
{npc.named} is determined to get there first.
A monster has moved into the place.
The weather is about to turn.
The authorities would be furious if they found out.
A better-funded group has already started.
Nobody, but the clock is the real enemy.
""")

# ============================================================ faction moves
table("fm.action", "Faction moves", """
{is} quietly buying up property
{is} recruiting from the other side of town
{has} begun demanding contributions from every shop|crime trade
{is} moving troops into position|military
{has} announced a new rule that happens to hurt only their rivals|politics
{is} sending envoys to a rival|politics
{has} made a pact with a rival, and told nobody|politics
{is} cutting off supplies|trade
{is} smuggling something sensitive past the watch|crime
{has} broken a treaty|politics military
{is} building a shrine, fort, or depot somewhere unexpected|religion military
{is} offering amnesty to anyone who turns in a rival|crime politics
{is} stirring up trouble in a neighboring district|crime
{is} hiring every capable sellsword in the region|military
{is} sponsoring a festival to win public favor|festival politics
{is} putting a price on the head of {a occupation}|crime
{has} found a way to turn a rival's money against them|trade
{is} courting the nobility|politics
{is} sending out scouts to find a lost thing|treasure ruin
{is} hiding evidence of a past crime|crime
{is} reorganizing from within, and the old guard are unhappy|politics
{has} suffered a theft and is searching every house|crime
{is} preparing for a succession dispute|family politics
{is} courting the party with a friendly face, or at least a convincing one
{is} spreading rumors about a rival|politics
{is} recalling every member to the city
{is} stockpiling {goods}|trade
{is} blockading a road|military road
{is} funding a dig at a famous ruin|ruin treasure
{is} quietly taking over the temple's charity work|religion
""")
table("fm.signs", "Signs of a faction's move", """
Clues: {n:2-4} people have been seen in the same unusual coat.
Clues: prices for {goods} are up, with no explanation.
Clues: a symbol is turning up on doors.
Clues: the usual faces are missing from {tavern.name}.
Clues: a stranger has been asking for work.
Clues: the watch are suddenly looking the other way.
Clues: a shipment has been delayed.
Clues: someone is buying a great deal of paper.
Clues: the smell of {smell} is coming from a building that should be empty.
Clues: couriers are running between two places that never used to talk.
""")
table("fm.counter", "What else is going on", """
A rival is already planning a response.
{campaign.faction} is watching with interest.
An ally of the faction disapproves, quietly.
If left alone, it comes to a head in {n:2-6} weeks.
The local authorities have not noticed yet.
Someone inside is leaking details.
The move will fail unless someone gets involved.
It could go either way, depending on who the party talks to first.
""")

# ============================================================ omens
table("omen.what", "What an omen does", """
{has} started to act strangely, to the confusion of everyone nearby
{is} behaving exactly as it did on the night before the last disaster
{has} turned an unnatural color overnight
{was} found in the wrong place at dawn
{has} gone completely silent
{v:repeat} the same pattern every night at the same hour
{has} begun to attract crowds, and offerings
{is} getting stronger, and no one can say why
{has} stopped, in a way that feels worse than before
{v:point} the same direction every time, toward whatever lies {where.any}
""")
table("omen.reading", "How locals read an omen", """
Folk say it is a warning from {campaign.faction}'s patron.
The temple calls it a blessing.
The superstitious are already leaving.
Farmers say it means an early winter.||1|autumn
Scholars say it is a natural phenomenon, and are not sure.
Children have invented a game about it.
Peddlers are selling charms against it.
The authorities deny it ever happened.
""")
table("omen.truth", "What is actually behind an omen", """
It is a symptom of something moving {where.any}.
It is a message, and someone in particular is meant to read it.
It is harmless, and it will end within the week.
It is the work of {npc.named}, who is very proud of it.
It is the first sign of {faction.generic} preparing something.
It is a side effect of an old ward weakening.
It is a trap meant to bring investigators to one place.
It has happened before, in the records, each time just before something terrible.
""")

# ============================================================ reputation suggestions
table("rep.favor.minor", "Minor favors (1 Reputation Point)", """
deliver a letter or small package
return a lost item
speak well of the group in public
buy their goods at a fair price
share a useful rumor
help move a heavy load
""")
table("rep.favor.moderate", "Moderate favors (2 Reputation Points)", """
clear out a nuisance threatening a route
find a missing member
recover a stolen shipment
help end a strike or small siege
win a dispute on their behalf
provide an alibi
""")
table("rep.favor.major", "Major favors (5 Reputation Points)", """
complete a quest that changes the group's fortunes
defeat a major rival or monster that threatens them
save a leader's life
expose a traitor in their ranks
recover a sacred or defining object
end a long feud
""")
table("rep.disservice.minor", "Minor disservices (-1 Reputation Point)", """
insult a member in public
break a small law in their territory
refuse a reasonable request
underpay or cheat an agent
gossip about them
damage minor property
""")
table("rep.disservice.moderate", "Moderate disservices (-2 Reputation Points)", """
interfere with their business
shelter a rival
free a prisoner they hold
publicly humiliate a leader
violate one of their tenets
steal from them
""")
table("rep.disservice.major", "Major disservices (-5 or more Reputation Points)", """
thwart their central plan
kill a respected member
betray their trust
destroy a sacred object
side openly with their worst enemy
expose a secret that ruins them
""")

# ============================================================ NPC traits
# Each axis is independent, so a personality is several unrelated picks rather than one stock "type".
table("npc.demeanor", "NPC temperament", """
gruff but fair
nervous and chatty
warm and welcoming
suspicious of strangers
proud
world-weary
cheerfully greedy
quietly devout
blunt to a fault
theatrical
meticulous
distracted, always half-listening
eager to please
cold and formal
sarcastic
endlessly curious
stoic
playful
melancholy
boastful
shy until the talk turns to their trade
calm in a crisis and a mess otherwise
fiercely loyal
quick to anger and quicker to apologize
dryly funny
paranoid
sentimental
mischievous
disciplined
easygoing
intense
tender-hearted behind a hard shell
pragmatic
idealistic
gossipy
weary but kind
restless
unnervingly polite
superstitious
defiant
patient to the point of maddening
bright and talkative
haunted
smug
gentle
rough-edged
conspiratorial
dignified
flustered
unflappable
""")
table("npc.demeanor.mod", "Conditions on a temperament", """
except when hungry
until someone mentions their family
unless money is involved
but mellows after a drink
but only in the morning
and gets worse around officials
though it all falls apart when they are lied to
but is fiercely protective of the young
except around the dead
but will help anyone who asks twice
until the lamps go out
though only with strangers
unless it rains
and always has been
though nobody has seen them truly angry
until a debt is mentioned
but is a different person after midnight
""")
table("npc.voice", "How they speak", """
speaks in a low rumble, rarely above a murmur
talks fast and trails off mid-sentence
has a voice like gravel in a bucket
speaks very formally, even to children
mumbles into their collar
laughs before the end of every sentence
never raises their voice, and never needs to
uses long words slightly wrong
ends every statement like a question
speaks in proverbs, mostly invented
whispers the important parts
sings the words they ought to say
speaks as if reading a script
hisses their s's through a missing tooth
drawls each word as if paid by the syllable
answers questions with questions
stammers only when telling the truth
has a clipped, military cadence
breaks into another language when upset
calls everyone by an odd nickname
speaks entirely in understatement
narrates their own actions aloud
punctuates sentences with a dry cough
has a lilting accent from somewhere upriver
swears creatively and without malice
addresses everyone as friend, and means none of it
""")
table("npc.mannerism", "Body language", """
taps three times before touching anything
never sits with their back to a door
straightens whatever is nearest
cracks their knuckles when thinking
avoids eye contact, then stares too long
keeps one hand on a coin purse
hums old work songs
talks to their tools
chews dried roots constantly
counts things under their breath
wipes their hands on their clothes without stopping
always seems to be listening to something else
touches a lucky charm at every lie
smooths their hair when nervous
leans in too close
grips the nearest table when angry
fiddles with a ring
keeps looking at the exit
bows slightly at every greeting
sniffs everything before touching it
paces when thinking
rocks on their heels
laughs silently, shoulders shaking
cleans their nails with a small knife
stands very, very still when frightened
""")
table("npc.quirk", "Habits and oddities", """
collects buttons
quotes scripture slightly wrong
keeps a tally of every favor owed
always smells faintly of smoke
names every animal they meet
speaks in the third person when nervous
sketches everyone they talk to
carries a small bell and rings it before entering rooms
keeps a pet that is not what it seems
eats only things that are red
refuses to cross water on a Thursday
reads other people's mail and apologizes afterward
plants something wherever they stay
collects teeth
keeps a lucky stone that is clearly just a pebble
saves string
writes everything in a tiny notebook
keeps bees
leaves a coin at every shrine
is never without a flask of something unlabeled
wears a ribbon for every person they have buried
is convinced a particular dog is following them
talks to the dead as though they were in the room
trades in secrets and gives change in rumors
knows exactly how many steps it takes to anywhere
forgets names and remembers debts
cannot pass a lamp without checking the wick
keeps a second set of clothes hidden in every town
only ever eats standing up
believes every stranger is a long-lost relative
whistles when lying
sleeps in a different place every night
""")
table("npc.appearance", "Distinctive features", """
a missing finger, and a story for each of the others
a scar through one eyebrow
braided hair threaded with fishing hooks
ink-stained fingertips
eyes of two different colors
a limp they hide well
very long, very clean fingernails
a sunburn peeling in strips
guild tattoos across the knuckles
silver-streaked hair they dye badly
freckles like spilled pepper
a jaw like a closed door
enormous hands that move gently
a tooth capped in brass
a birthmark shaped like a half moon
ears pierced a dozen times
hair the color of old straw
sunken cheeks and bright eyes
the dark circles of someone who does not sleep
a nose broken more than once
a bald head tattooed with a map
hands stained green from herbs
a halo of frizzy hair
a prominent, unfashionable beard
a voice-box scar they cover with a scarf
one eye cloudy and the other very sharp
a hunched back and a straight gaze
soot permanently worked into the skin
a laugh line deeper than any other
""")
table("npc.appearance.construct", "Distinctive features: automatons", """
a mismatched forearm from an older model, in a different shade of white
enamel chipped to dark metal at one shoulder, and never repainted
one eye lens glowing a slightly different blue from the other
a keepsake plate from someone they could not save, worn openly
a neat row of tiny repair marks along one arm
a visible adapter where two incompatible joints were joined
an old rounded shoulder plate that does not match the other
a smooth blank faceplate polished by years of being wiped with the same cloth
leather braces and cloth wraps holding one limb in place
a knee joint far too big for the rest of the leg
a torso core that glows softly brighter when they are interested
elongated fingers that never quite stop moving
""")
table("npc.appearance.poppet", "Distinctive features: poppets", """
a patched cloth arm in a different color from the other
button eyes of two slightly different sizes
visible stitches along one seam, tidy and careful
a replacement ear sewn on from a different doll
a faded scarf, mended many times
wooden joints worn smooth, with one limb newer than the rest
a tuft of stuffing that is forever escaping at the elbow
a ribbon someone once tied on that nobody has removed
embroidered details that have been re-stitched in a new thread
a spare button sewn on, just in case
""")
table("npc.appearance.plant", "Distinctive features: leshys and arboreals", """
bark that splits into a spiral along one arm
moss growing thickest at the shoulders
small flowers that open only in dim light
leaves that change color with their mood
roots that curl around their ankles when they stand still
a branch grown crooked from an old injury
glowing green eyes that dim when they are tired
a cluster of small mushrooms on one shoulder
a living branch added in memory of someone
fungal shelves along the back that glow faintly
a seed pod that rattles when they laugh
a new shoot at the elbow that they are very careful about
""")
table("npc.appearance.animal", "Distinctive features: awakened animals", """
fur that stands on end whenever they think hard
whiskers that twitch just before they ask a question
a tiny scarf, tied very seriously
eyes that look slightly too thoughtful for the face
a notched ear from before they woke up
a pouch of small objects whose meaning they are still sorting out
hand gestures copied from the first people they met
a tail that gives away exactly how they feel
a patch of fur worn bare where a pack once rubbed
a habit of stopping mid-step to consider something
""")
table("npc.clothing", "What they wear", """
a long coat with too many pockets
a patched cloak the color of old tea
an apron over good clothes
a hat too fine for their station
boots mended so often they are mostly stitches
a scarf in guild colors
mismatched gloves
a leather jerkin polished by years of use
a surprisingly clean white shirt
a lantern-oil-stained smock
robes patched with different cloths
a tabard that does not quite fit
work clothes that smell of smoke and tallow
a ring on every finger
a holy symbol worn like jewelry
a collar of rare fur in the wrong season
a hooded coat they never lower
a heavy apron with a sewn-in set of tools
""")
table("npc.goal", "What they want (completes: Wants to ...)", """
pay off a dangerous debt
protect a younger sibling
earn a place in a guild
find a missing friend
get rich before winter
prove a rival wrong
atone for an old mistake
keep a secret buried
rise in their faction's ranks
map somewhere no one has gone
be left alone
recover a stolen heirloom
open a shop of their own
find out what happened to their parents
win a contest everyone thinks they will lose
see the sea before they die
get out of this town
make peace with an estranged child
build something that will outlast them
find the person who ruined them
learn a trade they were told they were too old for
marry well
get a message to someone across the border
finish a work no one else will read
hold on to a position they no longer deserve
clear a name that was never theirs to lose
bring back something from below
protect a place from change
find a cure for a sick relative
be remembered
convince the town of something no one believes
outlive a rival
find an honest day's work
recover {a treasure.item} that was taken from their family
repay a debt to {faction.generic}
get revenge on {npc.named}
find {a occupation} who owes them a favor
keep {npc.named} from learning the truth
win a place in {faction.generic}
see {npc.named} brought to justice
make sure {a creature} is never seen near {settlement.name} again
be buried in {settlement.name}, which means getting there first
open a branch of the family business in {settlement.name}
learn to read before they die
bring {a relic} home
finally sell {goods} to someone who will pay properly
get out from under {faction.generic}
stay one step ahead of {npc.named}
convince {official} to listen
give {a occupation} left behind a proper burial
outbid {npc.named} for {a treasure.item}
become {official}, or at least be taken for them
warn {settlement.name} about something no one there will believe
trade up from {goods} to something with real money in it
clear the debts of {a occupation} they wronged
""")
table("npc.goal.why", "Why they want it", """
because of an oath made at a deathbed
after being humiliated in public
because someone is depending on them
since the alternative is going hungry
because they were promised it long ago
out of simple stubbornness
because a prophecy said they could not
since an old rival has just gotten there first
because they cannot forgive themselves
since someone is watching and they cannot back down
because they have nothing left to lose
after a stranger showed them it was possible
""")
table("npc.flaw", "Flaws", """
cannot resist a bargain
holds a grudge for decades
is terrible with money
cannot keep a secret that is not their own
trusts anyone who flatters them
lies out of habit, even when the truth would do
is too proud to ask for help
drinks to forget, and forgets to stop
is lazy until threatened
gambles, and always thinks the next hand is the one
dithers until the decision is made for them
is quick to blame others
overestimates their own cleverness
is jealous of anyone more successful
cannot leave a puzzle alone
refuses to admit when they are wrong
is deeply superstitious
is a hopeless romantic
talks too much when nervous
avoids conflict until it explodes
hoards everything, useful or not
is shamelessly vain
panics under pressure
""")
table("npc.virtue", "Virtues", """
generous beyond sense
keeps every promise
unfailingly honest
brave when it counts
patient with children and the dying
forgives easily
loyal past the point of reason
fair to a fault
has a gift for putting people at ease
never turns away someone in need
always does the dull, necessary thing
stands by their word even when it costs them
remembers every kindness
listens, truly
unafraid to say sorry
""")
table("npc.fear", "Fears", """
being forgotten
deep water
the dark below
fire
their own temper
debt collectors
being found out
dying alone
the watch
growing old
a particular person from their past
being buried alive
crowds
failure
silence
heights
the dead
""")
table("npc.secret", "Secrets (completes: Secret: is / has ...)", """
works as an informant for a rival faction
is not who they claim to be
owes money to the wrong people
witnessed a crime and said nothing
is hiding someone in their home
is slowly being blackmailed
has a forbidden relic
deserted a military post
is secretly very wealthy
has forged their credentials
is the child of someone notorious
keeps a second family in another town
has been ill for months and told no one
is secretly writing a very bad epic
knows where something valuable is buried
once betrayed someone who trusted them completely
has something hidden in the cellar
pays a ghost to keep quiet
is working against their own faction
has a debt to something that is not human
has a letter that would ruin an important person
is waiting for someone to arrive
holds a pardon they have never used
was once a criminal, and a good one
is the last person to have seen a missing neighbor
takes bribes from both sides
has no secret worth noting
is far older than they look
has lost their nerve and is pretending otherwise
owes {faction.generic} a favor they cannot refuse
is secretly in love with {npc.named}
has been selling information to {faction.generic}
knows that {npc.named} is not who they say they are
stole {a treasure.item} years ago and never sold it
was responsible for a death in {settlement.name} that was blamed on {a creature}
has been paying {official} to look the other way
is writing to {npc.named} under a false name
has a signed confession they have never used
keeps a large stock of {goods} hidden against a day when it will be worth more
once fled {settlement.name} under a different name
is sheltering {a occupation} the watch is looking for
hears the voice of someone who died in {settlement.name}
has promised {faction.generic} something they cannot deliver
has a stash of {contraband} behind a false wall
""")
table("npc.bond", "Ties to other people", """
owes their life to {a occupation} they have never repaid
has a sibling in {settlement.name} who writes every month
has an old rival who is now a friend
is raising someone else's child
has a mentor in {faction.generic}
is related to half the town
has an ex who runs the best competitor
swears by a local saint no one else has heard of
is a regular at {tavern.name}
once served under a captain they still write to
has a debt to {faction.generic}
is the only friend of {npc.named}
lost a close friend to {a creature}
""")
table("npc.belief", "Beliefs and opinions (shown after: Believes)", """
that the old ways are best
that the deep tunnels are cursed
that the river is alive
that the new magistrate is a fraud
that all gold is cursed
that the town is built on something old and angry
that dreams are letters
that the dead can be bribed
in a private religion of one
that magic is a trick, unless they can see it work
that the festival is a cover for something
that nothing good comes from {settlement.name}
that every stranger is either a thief or a saint, and it takes a week to tell
that luck is a debt, and the bill always comes
""")
table("npc.attitude", "Starting attitude toward strangers", """
Helpful|attitude:helpful|1
Friendly|attitude:friendly|3
Indifferent|attitude:indifferent|6
Unfriendly|attitude:unfriendly|2
Hostile|attitude:hostile|0.6
""")
table("npc.attitude.why", "Why they feel that way about strangers", """
they are in a good mood, and a bit lonely
they have been burned by travelers before
a stranger paid their debts once
they are busy and want to be left to it
they like anyone who respects their trade
they are afraid of what strangers bring
they are curious, and short on good conversation
they have been told to be wary of newcomers
they are expecting someone, and the party might be them
they had a bad week and it shows
""")
table("npc.knows", "What they know (shown after: Knows)", """
where a missing {occupation} was last seen
which door in {tavern.name} stays unlocked
that {a creature} has been seen near the road
who is really behind the price hikes|trade
every smuggler on the river, but will not say unless pressed|crime
where the key to the old cellar is kept
an old tunnel that is not on any map|underground
what happened at the graveyard, though they do not understand it|undead
where a map no one else seems to own can be found|ruin
a secret about the current magistrate|politics
who has been paying the watch|crime
the real reason {faction.generic} left town
the person everybody is looking for, and where they are staying
what the strange sound at night really is
a plan they overheard and did not like
""")
table("npc.catchphrase", "A phrase they repeat", """
"Mind the step."
"Well, that's a fine how-do-you-do."
"Trust me, I'm nearly always right."
"It was like that when I got here."
"Never trust a smiling goblin."
"I'll believe it when I see it, and then I'll doubt it."
"Fortune favors the prepared, and the very lucky."
"It's not the weight, it's the principle."
"I know a man who knows a man."
"That's not my department."
"Nobody ever asks the cook."
"Rain by midnight, mark me."
"Everything has a price, and I'm usually the one paying it."
"We'll not speak of that."
"Every candle is a clock."
"I've seen worse, and I've seen better, but mostly I've seen both."
""")
table("npc.backstory", "Where they came from", """
was a courier for a faction that no longer exists
grew up in the shadow of the mine, and left it
was a soldier until the war ended
ran away from the family business
was raised by someone not related to them
lost a fortune on a single hand of cards
was apprenticed to a master who vanished
survived something nobody else did
spent years in prison for a crime they did not commit
was a hero for one afternoon, long ago
came here to escape something they will not name
inherited the shop from a stranger
was a priest, once
sailed for ten years and does not talk about it
was born in this town and has never left
""")
# Role-specific lines about what they are doing right now. npcgen looks for npc.job.<role slug> first.
table("npc.job.generic", "What they are doing now (any role)", """
is waiting for someone who is late
is in the middle of an errand that has gone on too long
is nursing a grievance over a recent slight
is counting coins and not liking the total
is on their way somewhere, but is willing to be delayed for the right reason
is trying to look busier than they are
""")
table("npc.job.guard", "Guard: right now", """
is three hours into a shift that was meant to end at noon
has been told to watch for a thief matching no one's description
has strong opinions about the new toll
is quietly collecting a bribe fund for a rainy day
judges every traveler by their boots
was posted here as punishment and is determined to prove they deserve better
""")
table("npc.job.soldier", "Soldier: right now", """
is waiting for orders that are overdue
is mending armor and muttering about the quartermaster
has just been told the war is over, and does not believe it
is training recruits who have no talent for it
is writing a letter home they cannot finish
""")
table("npc.job.bandit", "Bandit: right now", """
is counting the take and finding it short
is watching the road for something worth the risk
is trying to persuade the gang to try something new
is nursing an injury and a grudge
is waiting for a signal that is late
""")
table("npc.job.thief_scavenger", "Thief or scavenger: right now", """
is sorting a haul they cannot quite explain
is casing the place and pretending to browse
has found something that might be very valuable, or very cursed
is trying to fence something before the owner notices it is missing
is hiding from someone they owe
""")
table("npc.job.hunter_scout", "Hunter or scout: right now", """
is following a trail that does not make sense
has come back from the woods with fewer companions than they left with
is reading tracks, and does not like them
is selling pelts at prices that do not add up
is waiting for a better moment to share what they have seen
""")
table("npc.job.merchant", "Merchant: right now", """
is haggling over a price that was settled yesterday
is trying to offload stock before it spoils
is waiting on a shipment that is, by now, very late
has a rival across the street and wants them ruined
has just bought something they now suspect they should not have
""")
table("npc.job.noble", "Noble: right now", """
is entertaining guests they do not much like
is hiding a scandal under a very lavish party
is looking for someone to do a delicate job
is waiting to hear whether an inheritance has cleared
is courting favor with someone far below their station
""")
table("npc.job.acolyte_priest", "Priest: right now", """
is preparing a sermon they have not yet worked out
is tending the sick and running out of herbs
is quarrelling with the temple over a matter of doctrine
is awaiting a sign, and starting to doubt there will be one
is quietly collecting alms for a cause they will not name
""")
table("npc.job.cultist", "Cultist: right now", """
is preparing a rite that must be finished by the next moon
is quietly recruiting from the congregation next door
is looking for a missing piece of a ritual
is rehearsing a story to tell if questioned
is waiting for a sign from something that is late
""")
table("npc.job.mage", "Mage: right now", """
is in the middle of a delicate working and resents the interruption
is searching for a missing component, and willing to pay
is correcting a spell that did not behave as written
is waiting for a letter from a rival at the college
is hiding something in a cloth that hums
""")
table("npc.job.scholar_sage", "Scholar: right now", """
is chasing a citation across three libraries
has just found an error in a famous text and is thrilled
is writing a paper that will make an enemy
is looking for a translator for a text nobody can read
is deeply, happily lost in a footnote
""")
table("npc.job.healer", "Healer: right now", """
is up to their elbows in a stubborn case
is running low on supplies and out of patience
is treating a patient who is not what they claim to be
is worried about a sickness that is spreading
is trying to sleep, and failing
""")
table("npc.job.entertainer", "Entertainer: right now", """
is rehearsing a new act that is not going well
is trying to recover a stolen instrument
is performing for a crowd that has stopped listening
is wooing a patron with more money than taste
is waiting for a debt to be paid, or a debtor to be found
""")
table("npc.job.artisan_smith", "Artisan: right now", """
is finishing a commission that is overdue
is cursing a supplier who delivered the wrong stock
is teaching an apprentice with limited success
is working in secret on something for no one
is turning away a customer they do not like
""")
table("npc.job.commoner", "Commoner: right now", """
is on their way to market and in no hurry
is arguing with a neighbor over a fence
is trying to work out how to pay this month's rent
is watching the street and noting every passer-by
is carrying a message for someone else
""")
table("npc.job.innkeeper", "Innkeeper: right now", """
is pouring a drink for the same patron for the third hour
is arguing with a supplier about the quality of the barley
is watching a table of strangers with open suspicion
is trying to throw out someone who owes a month's rent
has a room that is not available and will not say why
""")
table("npc.job.sailor_ferryman", "Sailor or ferryman: right now", """
is waiting for the tide, or a passenger who is overdue
is mending nets and eavesdropping on every passer-by
is trying to sell a story about something seen at sea
is dodging a customs inspector with a smile
is carrying something that is not on the manifest
""")
table("npc.job.miner_laborer", "Miner or laborer: right now", """
is sore, tired, and one more shift from a breaking point
is counting the days to payday and finding it far
is cutting a deal with someone who wants a tunnel kept quiet
is holding on to something dug out of the wrong place
is trying to organize a work stoppage
""")
table("npc.job.farmer_herder", "Farmer or herder: right now", """
is watching the sky and calculating a very bad year
is hunting a missing animal and finding odd tracks
is arguing with a neighbor over a boundary stone
is hoping a loan will arrive before the harvest
is nervous about something in the fields at night
""")
table("npc.job.alchemist", "Alchemist: right now", """
is on a cusp of a breakthrough and a disaster, in roughly equal measure
is searching for a rare ingredient and not asking where it comes from
is quietly selling something that is not on the license
is counting the cost of a batch that went wrong
has found a formula in a book that should not have survived
""")
table("npc.job.spy_informant", "Spy or informant: right now", """
is waiting for a contact who is late
is memorising a conversation they should not have overheard
is trying to decide which side to sell to
is carrying a message they have not opened
is being watched, and pretending not to notice
""")
table("npc.job.guide_ranger", "Guide or ranger: right now", """
is waiting for a client who has already been to a rival
is cursing a map that is wrong
is picking over supplies for a trip they do not like the look of
is reading the weather and not smiling
is leading a group that cannot be told what they are walking into
""")

table("omen.why", "Causes behind an omen", """
because something old is waking
because an old ward is failing
because someone broke a promise to something that does not forget
because the season is turning early
because a spell went wrong a long way from here
because the dead are restless
because a god is paying attention
because a rival is testing a new ward
because something has changed beneath the town
""")

# ============================================================ recipes
def _slots(who="who", what="what", where="where", when="when.rumor", why="why", strict_why=False):
    """The five main slots. strict_why makes the Why take only entries that share a theme with the What (or no theme at
    all), so the reason fits the event. Hooks use it."""
    why_slot = {"key": "why", "label": "Why", "table": why}
    if strict_why:
        why_slot["strict_anchor"] = True
    return [{"key": "who", "label": "Who", "table": who}, {"key": "what", "label": "What", "table": what},
            {"key": "where", "label": "Where", "table": where}, {"key": "when", "label": "When", "table": when},
            why_slot]


RECIPES["rumor"] = {
    "title": "Rumor", "page_type": "Rumor", "status": "unheard", "threat": None,
    "slots": _slots(),
    "extras": [{"key": "source", "label": "Heard from", "table": "rumor.source"},
               {"key": "truth", "label": "The truth", "table": "rumor.truth"},
               {"key": "check", "label": "To confirm", "table": "rumor.check"},
               {"key": "hook", "label": "What the party can do", "table": "rumor.hook"},
               {"key": "rep", "label": "Reputation", "table": "rep.effects"}],
    "compose": ["{@where}, {@when}: {@who} {@what}, {@why}. The word comes from {@source}.",
                "{@when}, {@where}: {@who} {@what}, {@why}. It comes from {@source}.",
                "{@where}, {@when}, {@who} {@what}, {@why}. The word comes from {@source}.",
                "According to {@source}, {@who} {@what}, {@why}. The rumor places it {@where}, {@when}.",
                "Word is that {@who} {@what}, {@why}. The rumor places it {@where}, {@when}. It comes from {@source}."],
    "title_template": "{@who.short} {@what.short}",
}
RECIPES["complication"] = {
    "title": "Complication", "page_type": "Complication", "status": "pending", "threat": ["Low", "Moderate", "Moderate"],
    "slots": _slots(who="who.comp", what="what.comp", when="when.comp", why="why.comp"),
    "extras": [{"key": "severity", "label": "Severity", "table": "comp.severity"},
               {"key": "resolve", "label": "A way out", "table": "comp.resolve"},
               {"key": "resolve2", "label": "Another way out", "table": "comp.resolve", "distinct": ["resolve"]},
               {"key": "ifignored", "label": "If ignored", "table": "comp.ifignored"},
               {"key": "rep", "label": "Reputation", "table": "rep.effects", "chance": 50}],
    "compose": ["{@when}, {@where}: {@who} {@what}, {@why}.",
                "{@where}, {@when}: {@who} {@what}, {@why}.",
                "{@when}, {@who} {@what}. It happens {@where}, and the reason is simple: {@why}."],
    "title_template": "{@who.short} {@what.short}",
}
RECIPES["hook"] = {
    "title": "Hook", "page_type": "Hook", "status": "open", "threat": ["Low", "Moderate", "Severe"],
    "slots": _slots(who="who.patron", what="task", when="when.hook", strict_why=True),
    "extras": [{"key": "reward", "label": "Reward", "table": "hook.reward"},
               {"key": "twist", "label": "Twist", "table": "hook.twist"},
               {"key": "opposition", "label": "Opposition", "table": "hook.opposition"},
               {"key": "rep", "label": "Reputation", "table": "rep.effects"}],
    "compose": ["{@who} {@what}, {@why}. The job is {@where}. The deadline: {@when}.",
                "{@when}, {@who} {@what}, {@why}. The job is {@where}.",
                "{@why}, {@who} {@what}. The job is {@where}. The deadline: {@when}."],
    "title_template": "{@who.short} {@what.short}",
}
RECIPES["faction_move"] = {
    "title": "Faction move", "page_type": "Event", "status": "upcoming", "threat": None,
    "slots": _slots(who="who.faction", what="fm.action", when="when.move"),
    "extras": [{"key": "signs", "label": "Signs", "table": "fm.signs"},
               {"key": "counter", "label": "Also going on", "table": "fm.counter"},
               {"key": "rep", "label": "Reputation", "table": "rep.effects"}],
    "compose": ["{@when}, {@where}: {@who} {@what}, {@why}.",
                "{@where}, {@when}: {@who} {@what}, {@why}.",
                "{@where}, {@when}, {@who} {@what}, {@why}."],
    "title_template": "{@who.short} {@what.short}",
}
RECIPES["omen"] = {
    "title": "Omen", "page_type": "Event", "status": "upcoming", "threat": None,
    "slots": _slots(who="omen.who", what="omen.what", when="when.rumor", why="omen.why"),
    "extras": [{"key": "reading", "label": "What people say", "table": "omen.reading"},
               {"key": "truth", "label": "The truth", "table": "omen.truth"},
               {"key": "hook", "label": "What the party can do", "table": "rumor.hook"}],
    "compose": ["{@when}, {@where}: {@who} {@what}, {@why}.",
                "{@where}, {@when}: {@who} {@what}, {@why}.",
                "{@where}, {@when}, {@who} {@what}, {@why}."],
    "title_template": "{@who.short} {@what.short}",
}


# ============================================================ GM Tools: influence, quests and recaps
# The wording for npcgen.generate_influence, and session.py's Quest Builder and Session Recap. hm in the not column marks a generic
# fantasy line (left out for Hallowmead); s2 and s3 in the needs column mark sillier lines (see gmtools.py).
table("adjective.person", "Personality adjectives", """
gruff
cheery
nosy
suspicious
overly polite
dramatic
tired
sticky
boastful
shy
pedantic
superstitious
penniless
ambitious
absent-minded
perfumed
long-suffering
brooding
reckless
very damp|||s2
alarmingly cheerful|||s2
dressed for a different job|||s2
visibly composing a limerick||2|s3
""")

table("influence.trait", "Influence: descriptors", """
famous muffin critic
retired town crier
local landlord, mostly absent
unofficial mayor
beloved toll keeper
careful quartermaster
town gossip, professional
guild treasurer with a grudge
keeper of the key, and the other key
caretaker of the old lamps
a goat's closest friend|||s2
self-declared expert on everything|||s2
mushroom tycoon, small scale|||s2
collector of apologies||2|s3
the person everyone defers to without remembering why||2|s3
""")

table("influence.weakness", "Influence: weaknesses", """
is soothed by flattery about their handiwork|pl:Diplomacy
collects spoons, and would trade nearly anything for a rare one|pl:Crafting
cannot resist a good story told well|pl:Performance
is secretly terrified of the dark, and of anyone who notices|pl:Intimidation
longs to be recognized as an artist|pl:Society
wants to be told their goat is handsome|pl:Deception
cannot refuse a favor if it is asked in front of others|pl:Society
wants very badly to leave town, and no one knows|pl:Diplomacy
dreams of being a minstrel, and is not good at it|pl:Performance
is proud of an old family recipe|pl:Crafting
believes in luck, and will not decide anything on a bad day|pl:Religion
keeps a rare mushroom and will talk about it for hours|2|pl:Nature
has a feud with a neighbor and would love a witness|2|pl:Society
believes the party is lucky, for no good reason|2|pl:Deception
adores a particular, obscure card game|3|pl:Society
trusts anyone who is willing to eat their soup|3|pl:Diplomacy
""")

table("influence.resist", "Influence: resistances", """
bristles at any mention of their ex-partner|pl:Diplomacy
finds flattery inane and says so|pl:Diplomacy
dislikes wizards, on principle|pl:Occultism
will not be rushed, and notices when they are|pl:Intimidation
distrusts anyone who smiles too much|pl:Deception
holds a grudge against the party's faction|pl:Society
gets defensive about the town's one failed festival|pl:Performance
does not like being asked about their past|pl:Diplomacy
cannot stand loud voices|pl:Intimidation
has a private rule about never lying to a stranger, and tests it|pl:Deception
is deeply suspicious of anyone who offers cheese|2|pl:Diplomacy
believes all bards are secret tax collectors|2|pl:Performance
refuses to make decisions before breakfast, and it is never breakfast|3|pl:Society
""")

table("influence.bias", "Influence: biases", """
likes ratfolk, and tells them so
distrusts goblins who are too polite
respects anyone who has fixed something with their own hands
dislikes people who show up in armor to a negotiation
thinks kobolds are underestimated, and says so often
cannot abide being spoken to in a rhyme|||s2
has always wanted to meet a hero, and is quietly disappointed by each one|||s2
believes the best deals are made standing up, while eating||2|s3
""")

table("influence.agenda", "Influence: hidden agendas (GM only)", """
needs something done and cannot ask directly
is waiting on a letter and is short-tempered because of it
wants the party to take the fall for a mistake
is stalling for someone who is on the way
is trying to keep a small secret that has become a very large one
has already promised the same favor to someone else
is quietly planning to leave town tonight|||s2
is being watched by someone in the room, and knows it|||s2
has accidentally become the town's most important person, and hates it||2|s3
""")

table("influence.penalty", "Influence: penalties for failing", """
tells everyone in town the party were rude
refuses to speak to the party again, even in an emergency
quietly raises prices for them, forever
sends a very formal letter of complaint to the party's faction
sets the town goat on them, in a manner of speaking
makes a remark so cutting that the party must rest before the next scene|||s2
becomes loudly and permanently hurt|||s2
leaves, and takes the key with them||2|s3
""")

table("influence.benefit.1", "Influence: benefits (first threshold)", """
agrees to hear the party out without calling for the watch
shares a small, useful rumor
gives the party directions to someone who matters
offers a drink and a seat, which is more than most get
admits that the problem exists
lets the party in the back door|||s2
""")

table("influence.benefit.2", "Influence: benefits (middle threshold)", """
reveals a secret that is helpful and a little embarrassing
introduces the party to someone important
offers a discount, or the use of a tool or cart
agrees to put in a good word
offers a small loan, to be repaid as a story|||s2
agrees to look the other way for an evening|||s2
""")

table("influence.benefit.3", "Influence: benefits (top threshold)", """
does the favor the party came for, and asks that nobody talk about it
becomes a lasting ally, to the point of showing up when called
hands over the key, the map, or the proof
publicly takes the party's side
gives the party a title that comes with immunity from a country that has ended|||s2
gives the party a goat, which comes with duties||2|s3
""")

table("influence.quirk", "Influence: appearance and habits", """
speaks in a very soft voice, and notices when others do not
always carries a small tin of mints
wears three hats at once, for reasons
has a very loud laugh that no one has ever heard on purpose
keeps a notebook of other people's mistakes
smells faintly of woodsmoke and mushrooms
is always eating something small
taps a rhythm on every surface|||s2
wears a tiny medal for something nobody remembers|||s2
speaks to their hat, and listens to its replies||2|s3
""")

table("quest.title", "Quest titles", """
The Great {^thing.short} Caper
Please Mind the {^thing.short}
A Very Reasonable Heist
Seven {^thing.plural} and a Funeral
Nobody Asked About {^thing.plural}
The Case of the Missing {^thing.short}
Nothing Happened in {place.short}
Whose {^thing.short} Is This?
The Quiet Business of {^thing.plural}
{^thing.short}, Rented by the Hour|||s2
The Goat Did It|||s2
Too Many {^thing.plural}|||s2
The Mayor's Left Boot||2|s3
Everybody Loves {^thing.plural}||2|s3
""")

table("thing.short", "Quest nouns", """
lantern
ladder
cheese
spoon
bucket
bell
mushroom
cart
hat
sock
key
goat
""")

table("thing.plural", "Quest nouns (plural)", """
lanterns
ladders
cheeses
spoons
buckets
bells
mushrooms
carts
hats
socks
keys
goats
""")

table("place.short", "Quest places (short, Hallowmead)", """
the Third Tunnel|p:hallowmead
the Crossings|p:hallowmead
the Salvage Yard|p:hallowmead
the Mushroom Terraces|p:hallowmead
the Old Lift|p:hallowmead
the Old Mill||||hm
the Marsh Road||||hm
the Cellar||||hm
the Docks||||hm
the Chapel||||hm
""")

table("quest.scene.social", "Scenes: social", """
persuade {obstinate.being} to cooperate, in front of an audience
get a straight answer out of {a creature.silly}, who answers every question with a question
negotiate with two sides who want the same thing for opposite reasons
calm a crowd that has already decided who is guilty
convince {a custodian.silly} that the party has the right paperwork
win over the room at {a event.silly} without being asked to leave|||s2
interview {a creature.silly} while pretending to be someone else|||s2
lie to {a custodian.silly} about something small, then something larger||2|s3
""")

table("quest.scene.explore", "Scenes: exploration", """
follow a trail of {countable} that gets weirder as it goes
search {place} for the one thing that does not belong
find a way across {place} that is not the way everyone says
map the part of {place} that the old map did not bother with
keep {a passenger} out of trouble while crossing {place}
track down {a lost.item} through {place}, with a witness who keeps changing the story|||s2
cross {place} while something cheerful follows at a respectful distance|||s2
find out why {place} has gone suspiciously quiet||2|s3
""")

table("quest.scene.puzzle", "Scenes: puzzle", """
work out which of four nearly identical {thing.plural} is the real one
decode a message written by someone who clearly hated being understood
repair {a broken.thing} with the parts at hand (the instructions are in a different language)
find the order in which the doors must be opened
read a map where every landmark has been renamed by a committee
solve a riddle whose author has since changed the answer|||s2
discover who is lying, when everyone lies about a different thing|||s2
work out what a talking {thing.short} wants, since it only speaks in questions||2|s3
""")

table("quest.scene.chase", "Scenes: chase", """
catch {a pest}, which has run off with {a lost.item}
keep up with a runaway cart on a downhill track
slip through a crowd while a guard follows, loudly
beat a rival crew to {place} by any route
rescue {a passenger} who has wandered off, and is not at all lost|||s2
outrun a stampede of {thing.plural}, in a very narrow corridor|||s2
chase a goat across {place}, which knows the town better than you||2|s3
""")

table("quest.complication", "Quest complications", """
a rival crew arrives with the same job
the weather turns, and so does the mood
the person who hired the party is nowhere to be found
a local official insists on inspecting the work
the party's route has been blocked, politely, by a committee
the one thing the party needs has just been sold to someone else
the deadline moves up, and nobody says why
someone has been spreading a rumor about the party that is not entirely wrong|||s2
the client's relatives turn up and each want a different outcome|||s2
the whole thing is accidentally recorded in a very public ledger|||s2
a goat joins the party. There is no explanation||2|s3
""")

table("quest.twist", "Quest twists", """
the client has been the target of the job all along
the item was never lost; it was moved on purpose
the culprit is someone the party likes
the rival crew was hired by the same person
the thing the party was told to stop is the only thing keeping something worse away
the job was done last week; the client forgot
the "villain" is a very tired {occupation} who wants an apology|||s2
the "monster" is the client's pet, escaped, and extremely embarrassed|||s2
the entire town knew, and was waiting for the party to find out||2|s3
""")

table("quest.ending.good", "Endings: success", """
word gets around: the party is trusted a little more in the Underhallow
the client pays in full, and in person, with only mild resentment
a small, strange honor is awarded, with a ceremony that lasts too long
someone important now owes the party a favor
""")

table("quest.ending.mixed", "Endings: partial", """
the job is done, but at a cost nobody planned for
the client is satisfied; someone else is not
the party gets paid, and also a complaint
the problem is solved today and will come back as a different problem later
""")

table("quest.ending.bad", "Endings: failure", """
the party gets paid in goodwill, which is not currency
a rival takes the credit; the party takes the blame
the client leaves town, and the job gets worse without them
the party's name becomes a minor local joke
""")

table("quest.monster.minion", "Encounter concepts: minions", """
a swarm of mine rats in tiny hats
mine-cart gremlins
a gang of over-eager mushroom shufflers
hired thugs who are, privately, afraid of their boss
vermin with a union
""")

table("quest.monster.standard", "Encounter concepts: standard", """
a rival crew's best fighter
a very large, very confused beast
a possessed lamp and its escort
a guardian that has not been told the job is over
a goblin with a megaphone and a plan|||s2
""")

table("quest.monster.boss", "Encounter concepts: boss", """
the rival crew's boss, in a good coat
a very old guardian, awakened and grumpy
an ooze that has learned to read|||s2
a chandelier, hungry and in charge||2|s3
a mimic that has opened a shop||2|s3
""")

table("quest.hook.silly", "Quest openings", """
A notice on the board, in three different handwritings, each correcting the last
A tearful relative at the door, who will not say who died
A hat that appears on the bench at the inn, with a note
A small child with a very serious contract
A goat with a note tied to its collar
""")

table("recap.open.epic", "Recap openings: epic narrator", """
Previously, in the Underhallow
When last we left our heroes
Gather round, friends, and hear what befell the party
""")

table("recap.open.gossip", "Recap openings: gossiping goblin", """
Right, so you will not believe this
Come closer, I have the news, all of it, and some of it is true
Word at the market is that
""")

table("recap.open.innkeeper", "Recap openings: tired innkeeper", """
So, long night, they tell me, and here is what I heard
Same as always, only louder. Here is how it went
You missed a good one, so I will say it slowly
""")

table("recap.open.notary", "Recap openings: overly formal notary", """
In the matter of the party's recent activities, the following is entered into the record
For the official record, with apologies for any inconvenience
As witnessed, as recorded, and as signed
""")

table("recap.link.epic", "Recap connectors: epic", """
Then
And so
Soon after
Before long
At last
""")

table("recap.link.gossip", "Recap connectors: gossip", """
And then, get this
Meanwhile, and this is the good part
Naturally
Because why not
You will like this one
""")

table("recap.link.innkeeper", "Recap connectors: innkeeper", """
After that
Then
Somewhere in there
Later
Next
""")

table("recap.link.notary", "Recap connectors: notary", """
Further
Additionally
Subsequently
Of note
Also recorded
""")

table("recap.close.epic", "Recap closings: epic", """
And so the tale continues, as tales do.
What comes next, only the tunnels know.
""")

table("recap.close.gossip", "Recap closings: gossip", """
That is all I know, and some of it I made up.
So that is where things stand. Do not repeat this.
""")

table("recap.close.innkeeper", "Recap closings: innkeeper", """
That is the lot. More soup?
Anyway, that is how it stands. Tip the staff.
""")

table("recap.close.notary", "Recap closings: notary", """
This concludes the entry. Please initial each page.
Signed, with reservation, and in triplicate.
""")

table("recap.award", "Session awards", """
The Sir Reginald Trophy for Most Avoidable Death, Narrowly Avoided
The Golden Spoon for Best Use of a Spoon
The Bucket Prize for Most Dramatic Entrance
The Quiet Cheese Medal for Strategic Silence
The Left Boot Award for Excellent Footwork
The Plain Paper Ribbon for Most Convincing Lie
The Dented Helm for Bravery Under a Very Low Door
The Honorary Goat for Unwarranted Confidence|||s2
The Moss Medal for Least Likely to Be Noticed, Still Present|||s2
The Lifetime Achievement Award in Falling Down Stairs, Early||2|s3
""")

"""Built-in content for the Inn and Tavern generator. Plain Story Forge tables (one entry per line:
    text | tags | weight | needs | not
see storydata.py for the full format), so every table here can be edited, switched off, or added to in Edit Tables.

The generator puts these facts in play as tags, so an entry can ask for them with `needs`:
    kind:inn  kind:tavern  kind:alehouse  kind:roadhouse  kind:taproom        what sort of place it is
    q:squalid  q:common  q:good  q:fine                                       how well it is kept
    size:small  size:medium  size:large                                       how big it is
    busy:quiet  busy:normal  busy:packed                                      how full it is tonight
    c:goblin  c:kobold  c:ratfolk  c:grippli  c:leshy  c:mender  c:awakened   who runs it (Underhallow content only)
Lines tagged p:hallowmead are the Underhallow flavor and are limited to the Hallowmead content pack; the Inns tab's
"Setting flavor" slider limits how often they appear. Nothing here states canon: it is color for a place, not history.
"""

import re

TABLES = {}
NEED_PREFIX = ("q:", "kind:", "busy:", "size:", "c:")      # facts about the place, which an entry may require


def normalize(line):
    """Shorthand for writing the tables below: after the text, any number of '|' parts, each holding space separated
    tokens. A number is the weight; q:, kind:, busy:, size:, and c: tokens are requirements (needs); everything else is
    a tag. This returns the entry in Story Forge's own 'text | tags | weight | needs' form."""
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


# ============================================================ names
table("tav.name.a", "Inn names: adjectives", """
Gilded
Drowned
Sleeping
Crooked
Merry
Weary
Honest
Salty
Lucky
Rusty
Laughing
Wandering
Gray
Red
Black
Silver
Golden
Broken
Hollow
Quiet
Brazen
Blind
Prancing
Humble
Smoking
Thirsty
Patient
Leaning
Lonely
Cheerful
Stubborn
Bitter
Warm
Painted
Dancing
Crimson
Old
Little
Lucky
Burning
""")
table("tav.name.creature", "Inn names: creatures", """
Goose
Pig
Lamb
Stag
Raven
Cat
Rat
Fox
Heron
Badger
Owl
Hound
Mule
Hare
Crow
Dragon
Eel
Toad
Bear
Wolf
Ox
Swan
Magpie
Boar
Hen
Otter
Moth
Newt
Cricket
Bat
""")
table("tav.name.thing", "Inn names: things", """
Anvil
Kettle
Barrel
Lantern
Cart
Plow
Anchor
Horn
Boot
Pipe
Fiddle
Bucket
Ladle
Key
Bell
Crown
Cup
Wheel
Candle
Barrow
Spindle
Hearth
Tankard
Compass
Mill
Bridge
Gate
Bowl
Cask
Lamp
""")
table("tav.name.house", "Inn names: what the owner's name is attached to", """
Rest
Hearth
Table
Larder
Corner
Board
Lantern
Welcome
Cellar
Kitchen
""")
table("tav.name", "Names of inns and taverns", """
The {tav.name.a} {tav.name.creature}||6
The {tav.name.a} {tav.name.thing}||5
The {tav.name.creature} and {tav.name.thing}||3
The {tav.name.thing} and {tav.name.creature}||2
The {tav.name.creature}'s Rest||2
The {tav.name.creature}'s Head||1
{name.owner}'s {tav.name.house}||3
{name.owner}'s Place||1
The {tav.name.a} {tav.name.creature} Inn||3|kind:inn
The {tav.name.thing} Inn||2|kind:inn
The {tav.name.a} {tav.name.thing} Alehouse||3|kind:alehouse
The {tav.name.creature} Tap||2|kind:alehouse/kind:taproom
The {tav.name.a} {tav.name.thing} Tap||2|kind:taproom
The {tav.name.thing} Roadhouse||3|kind:roadhouse
The Last {tav.name.thing}||2|kind:roadhouse
The First {tav.name.thing}||1|kind:roadhouse
The {tav.name.a} {tav.name.creature} Tavern||2|kind:tavern
The {tav.name.thing} and Crown||1|q:good/q:fine
The Grand {tav.name.thing}||1.5|q:fine
The {tav.name.a} {tav.name.thing}, such as it is||0.4|q:squalid
""")

# ============================================================ the look and feel
table("tav.look", "How the place looks", """
A low room of dark beams and smoke-stained plaster, with a fire that is never allowed to go out.
Long tables scarred by years of knives and mugs fill a room that smells of cooking.
A tall, noisy room with a gallery above, where guests lean on the rail to watch the floor.
A cramped place with more furniture than floor, so everyone sits closer than they planned.
Whitewashed walls hung with faded banners, and a bar polished to a shine by a century of elbows.
A single big room with a hearth at each end and a crooked staircase between them.
Shuttered windows, thick candles, and a back corner that is always dimmer than it should be.
Rough stone walls sweat in the heat, and the benches are worn into the shape of the people who sit on them.
A converted warehouse, still stacked with barrels along one wall and all the cheerier for it.|urban water
A snug, many-cornered house of little rooms, each with its own fire and its own regulars.
Everything is slightly crooked: the floor, the sign, the stairs, and the barkeep's smile.
The ceiling is hung with copper pans, old tools, and gifts from grateful travelers.
A bare plank bar, a few stools, and a keg on a rack. Nothing else has been added in years.
A half-timbered house leaning toward the road, with a lantern on a pole that has never once been put out.|road urban
Barrel-vaulted cellars turned into a drinking hall, where every sound is louder than it should be.
The walls are crowded with carved names, and a new one is added every few weeks.
A common room with a floor of packed earth, strewn with fresh rushes that nobody quite trusts.
A narrow place stretched along a canal, with benches that face the water and not the bar.|water urban
The windows are glazed with bottle glass in a dozen colors, throwing a stained light across the tables.|urban road
A clean, well-run room with brass on the walls and a house cat who inspects everyone.
Dark, damp, and friendly, with a stone floor sunk a little from the weight of generations of boots.
A grand room with a gilded bar and chairs that match, and prices that match the chairs.|q:fine
Paneled in dark wood, with deep chairs, a library corner, and a staff that has been taught to be invisible.|q:fine
A bright hall of polished floors and linen napkins, with a quartet tuning in the corner.|q:fine
Even the stairs have carpet, and the lamps are trimmed so evenly that someone must do it on a schedule.|q:fine
Warm, well-kept, and well-lit, with good chairs and a waitress who knows the menu by heart.|q:good
A good house, if a plain one, with clean linen, honest portions, and a proper bar.|q:good
A busy, well-run room where the kitchen door never stops swinging.|q:good
The floor is sticky, the walls are dark with years of smoke, and the one window has been boarded over.|q:squalid
A bare, cold room with a bucket in the corner that is better not to ask about.|q:squalid
The tables wobble, the benches are splintered, and a layer of sawdust is doing its best on the floor.|q:squalid
Part of the roof has fallen in, and the part that remains is being propped up by a very old pillar.|q:squalid
A converted stable, with the stalls turned into booths and the manger still on the wall.|kind:roadhouse
A long yard of benches and trestles outside a wide, low house, with wagons parked in rows.|kind:roadhouse|road
A roadside house with a sturdy gate, a deep porch, and a hitching rail worn smooth.|kind:roadhouse|road
Built on stilts over the water, with a deck for drinking and a trapdoor in the floor for fishing.|water
Moored hulls tied together and planked over, so the whole place sways when the tide turns.|water
A dockside cellar with a low ceiling, a fish-stained floor, and a rope for every wall.|water
A single, loud room with a stage at one end and benches that all face it.|festival
Lit by stolen lamps, hung with the trophies of a dozen unlucky regulars, and no one will say where they came from.|crime
Hidden behind a shop front, with a password at the door and a second one at the bar.|crime|mystery
A place of carved columns and low arches, where the stone itself seems to mutter back.|underground
Cave walls hung with lamps and tapestries, and a bar cut straight out of the rock.|underground
A hollowed chamber lit by glow-moss in lanterns, with benches carved from the cave floor.|underground
Pale fungal light seeps in from the walls, and nobody bothers with candles.|underground|t:weird
Stalactites hang over the bar, and someone has hung a mug from every one of them.|underground|t:light
A hall of salvaged furniture, none of it matching, all of it well loved.|underground|c:goblin|p:hallowmead
A dim, close place built into a cellar, with a back wall that is just a little too new.|mystery|t:weird
Every table is a different kind of wood, and the story behind each is told for a price.|trade|t:light
A great fireplace you could roast an ox in, and a smell that suggests someone has.|t:light
""")
table("tav.smell", "How the place smells", """
Woodsmoke and spilled ale hang in the air, with something frying beneath them.
The room smells of wet wool, pipe smoke, and old bread.
Hot bread and roasting meat hit you at the door, and you are suddenly very hungry.
Sour beer, damp straw, and a hint of something unwashed.|q:squalid
The place smells of beeswax, clean linen, and good coffee.|q:good/q:fine
A thick, sweet smell of cider and spices lingers in the air.
Tallow smoke, old rushes, and the sharp tang of vinegar.
Fresh sawdust, hops, and boiled cabbage, in about equal parts.
The fish is not fresh, and everyone knows it, and everyone eats it anyway.|water|q:squalid
Salt, tar, and the smell of the tide, even a long way from the water.|water
Horse and leather and boiled coffee, as in every roadhouse that ever was.|road
Earth, stone, and the faint sweetness of cave mushrooms.|underground
Wet stone and the mineral tang of a deep cellar.|underground
Roasted barley, peat smoke, and something that might be a very old cheese.
A sharp whiff of cheap spirits, which someone has tried to cover with herbs.|q:squalid
Cut herbs, fresh bread, and the faint sourness of the cellar below.|q:common/q:good
Lamp oil and a delicate hint of something floral.|q:fine
Hot iron and charcoal drift in from the smithy next door.|craft
Candle smoke and the dusty smell of old books.|mystery
The air is thick with pipe smoke, and a faint trace of something sweeter.|crime
""")
table("tav.sound", "How the place sounds", """
A constant murmur of talk, the clink of mugs, and a log shifting in the fire.
Someone is arguing about money in the corner, and has been for an hour.
A dog barks twice, then thinks better of it.
Dice rattle on a table and are followed by a groan.
The crowd laughs at a joke the bartender has told every night for a year.|t:light
A creaky stair, a slamming door, and a tray hitting the floor in the kitchen.
Boots on wood, and now and then the scrape of a chair.
Rain drums on the roof, so that everyone speaks a little louder.|weather urban road wild water
Hushed voices and low laughter, as if someone is sleeping nearby.|busy:quiet
A roar of voices and a tin whistle that nobody can hear.|busy:packed
A tuneless fiddle is being played by someone who loves it.|q:squalid/q:common
A choir of off-key drinkers, led by one man who is very sure of the words.|busy:packed|t:light
Water drips somewhere in the walls, in a slow count.|underground
Footsteps echo down some unseen passage, and the barkeep pretends not to hear them.|underground|mystery
Waves slap the pilings, and the whole room rocks gently in time.|water
Wagons creak in the yard, and a driver is cursing a horse.|road|kind:roadhouse
A clock ticks, and everyone seems to hear it.|q:good/q:fine
A string quartet is working through something polite and very slow.|q:fine
Chains rattle faintly behind the bar, and nobody asks why.|crime|t:grim
The same hymn is sung by someone at the next table, over and over, softly.|religion
""")
table("tav.crowd", "Who is in tonight", """
A handful of regulars nurse their drinks and watch the door.|busy:quiet
Hardly anyone is here, and the staff are cleaning glasses out of boredom.|busy:quiet
A pair of strangers share a table and a silence, and neither has touched the food.|busy:quiet|mystery
A comfortable half-full room: locals at the bar, travelers at the tables, and a game of cards in the back.|busy:normal
A mix of tradespeople off shift, a few travelers, and a table of very serious drinkers.|busy:normal
The room is lively but not loud, with talk spilling over from table to table.|busy:normal
Packed to the walls with people shouting for drinks and hardly a seat to be had.|busy:packed
A crowd has come for the entertainment, and the staff are running to keep up.|busy:packed|festival
Every table is taken, and a line of people is waiting by the door.|busy:packed
A party of mercenaries has taken the best table and the loudest voice.|military
A guild delegation is holding a meeting at the back, and nobody else is welcome there.|trade|politics
A band of pilgrims are sharing a loaf and a tune, and have made friends with the barkeep.|religion|road
A table of off-duty watchmen eyes every newcomer, in a friendly way, mostly.|crime|military
A group of miners straight off the shift, still gray with dust and very thirsty.|craft|underground
Caravan drivers swap stories of the road at the long table, with a map spread between them.|road|trade
A noble in a plain cloak pretends not to be noticed, and everyone pretends not to notice.|politics|mystery
A table of scholars argues cheerfully over a single page of notes.|mystery|magic
A gang of dockhands is playing a loud and violent game with a ball and a bucket.|water
Fishers with nets across their knees are mending them while they drink.|water
Farmers in for market day lean over their drinks and talk about the weather.|nature|trade|urban road
A quiet table of hooded figures leaves as soon as anyone looks at them.|crime|mystery|t:grim
Children are underfoot, a dog is under a table, and the whole place has the feel of a family kitchen.|family|t:light
A pair of drunks is singing in two entirely different keys.|t:light
Two tables are not speaking, and the staff are carefully serving them from opposite sides.|crime|politics
A lone drinker at the bar has been there since morning and shows no sign of leaving.
""")
table("tav.decor", "What hangs on the walls", """
A stuffed fish with a surprisingly lifelike glare.
A collection of cracked tankards, each with a name painted on it.
A row of hooks for hats, with a few that have not been claimed in years.
A map of the region, stained with ring after ring of mug-marks.
A wall of crude portraits of regulars, drawn by a customer who could not pay.
A battered shield bearing a coat of arms no one recognizes.
A framed menu from the opening day, with prices that make the regulars sigh.
A pair of crossed oars, a harpoon, and a sign that says: DO NOT TOUCH.|water
A worn banner from a campaign that ended long ago.|military
A rack of walking sticks left behind by pilgrims who never came back for them.|religion|road
A shelf of carved bottles that glow faintly at night.|magic|t:weird
A skull on a hook that is somehow always dressed for the season.|t:light|undead
A taxidermied boar wearing a tiny crown.|t:light
Rows of iron nails, each one hammered in to mark a wager that was settled.|crime
A great mounted antler rack with a dozen hats hanging from it.|nature
Pressed flowers in frames, a different one for each year.|nature|family
Painted tiles with a scene from a local legend, slightly different on each one.|mystery
A wooden sign above the bar that reads: WE DO NOT SERVE ANYONE WHO MENTIONS THE WAR.|military|t:light
A great clock that has not been right in living memory.|t:light
Tapestries of faded hunting scenes, with the hunters all cut out and replaced with newer figures.|politics
Brass lamps and glass globes in every window, each one a different color.|q:good/q:fine
A gallery of oil paintings of the founder's family, all of whom look faintly disappointed.|q:fine
Cheap prints tacked to the wall with whatever was handy.|q:squalid
Hooks for weapons by the door, with a sign asking you to hang yours before you drink.
A great pair of jugs from a distant land, filled with dried flowers.
""")
table("tav.entertainment", "The entertainment", """
A fiddler and a drummer play for tips and meals, and are better than the room deserves.
A traveling storyteller holds a table spellbound with a tale about a stolen crown.
A sing-along begins every night at the same hour, and woe to anyone who refuses to join.
A pair of regulars arm-wrestle for a drink every evening, and have for years.
A knife-thrower performs on the back wall, and the barkeep prices the damage into the beer.
A bard recites verses about the regulars, who are not always flattered.|t:light
A shouted game of riddles, with the winner drinking free.|t:light
Dice, cards, and a corner full of men who take them far too seriously.|crime
A puppet show on a table, with a voice that is clearly the owner's.|t:light|festival
A blind harper plays slow airs and takes requests for coin.|q:good/q:fine
A string trio in the corner plays polite music and is paid not to be noticed.|q:fine
A fire-eater sets the whole room cheering, and the barkeep nervously eyes the ceiling.|festival|q:common/q:good
A traveling juggler is working a table for pennies and getting very few.|q:common|road
A boisterous dart game has run for three years, and the score is not close.|t:light
Quiet card games for small stakes, run by a dealer with a very honest face.|q:good|trade
A comic who insults the audience, to enormous applause.|t:light
A singer with a voice that makes the room go quiet in all the right places.|q:good/q:fine
A drum circle that starts at midnight and does not stop until the last customer goes.|busy:packed
A teller of tales who is rumored to be a cursed prince, or at least to have been.|mystery|fey
A table of chess players, and a crowd who bet on every move.|politics|mystery
A wrestling ring has been set up in the yard, and the fights are quite popular.|military|busy:packed
""")

# ============================================================ rules, problems, secrets, history
table("tav.rule", "House rules", """
Weapons are left at the door, where the keeper hangs them on pegs and gives out numbered tags.
No hats at the bar, and no talking shop at the long table.
Fighting means a ban, and the keeper has a very long list of people who learned that the hard way.
Whoever breaks a mug pays for it, and whoever breaks a table pays for the whole evening.
The last round is called at midnight, and the keeper means it.
You do not sit in the chair by the fire, which belongs to a regular who is not currently here.
Dice are fine, cards are fine, but anyone caught cheating will find out how heavy the keeper's hands are.
No one carries a naked blade past the door.
No bills are run after the second drink.
All songs are welcome, but all verses will be sung.
Debts are called in on the first of the month, with the keeper's own interest.
The keeper does not take sides in an argument, and neither does anyone who wants to stay.
Everyone washes their own mug at the end of the night, and the keeper checks.|t:light
Strangers buy the first round for the table that welcomes them.|t:light
The cat is not to be moved from its chair.|t:light
Anyone who mentions the old feud buys everyone a drink.|politics|t:light
No magic is cast on the premises, and the keeper has a charm that rings if it is.|magic
No coin from a certain minting will be accepted, and the keeper will not say why.|politics|mystery
Prayers before meals are optional, but the keeper looks hard at anyone who skips.|religion
No one touches the locked door at the back, and no one asks.|mystery|crime
Guests of the house leave their boots at the door and wear the slippers provided.|q:good/q:fine
Everyone gives a name at the door, and the keeper does not ask if it is true.|crime
Rooms are paid in advance, and the keeper will not hold a key for a promise.|q:common|kind:inn/kind:roadhouse
Guests are not allowed on the roof, and no one will tell you why.|mystery|kind:inn
Horses are stabled around the back, and nobody is allowed to take the gray one.|road|kind:roadhouse
Anyone who has to ask the price cannot afford the evening.|q:fine
The staff are not to be touched, tipped excessively, or proposed to.|q:good/q:fine
Quiet is kept after the bells, and complaints are settled by the keeper with a rolling pin.|family|t:light
A bell by the door rings when anyone enters armed, and the keeper will not look up.|military|crime
""")
table("tav.problem", "A problem the place has right now", """
A guest has not left their room in three days, and meals keep going up and coming down untouched.|mystery
The cellar has flooded, and the barkeep is hoping nobody asks for the good wine.|weather|water
A creditor has been seen outside twice this week, and the keeper has stopped answering the door.|crime|trade
The cook has quit without notice, and the soup has been the same soup for four days.|t:light
A regular has not come in for a month, and no one will say what happened to him.|mystery
The roof is leaking in three places, and the keeper has stopped pretending it is not.
Rats have gotten into the pantry, and the keeper is paying a bounty for each one.|disease|t:light
A rival house across the road is undercutting every price, and their cook has a suspicious talent.|trade|crime
The watch has been asking about a guest, and the keeper has been asked to say nothing.|crime|politics
A guest complains of noises in the walls at night, and the staff have stopped sleeping.|mystery|undead
The well has gone brackish, and the ale has begun to taste of it.|disease|nature
A beloved house cat has gone missing, and half the regulars are out looking.|family|t:light
The sign has been stolen twice this month, and it is getting harder to replace.|crime|t:light
A traveling healer has set up in the back room and the owner is not sure whether to charge or thank her.|disease
The owner's cousin is making a claim on the place, and a lawyer has been hovering for a week.|family|politics
A band of rowdy mercenaries has taken three rooms and is not paying.|military|crime
A shipment of casks has not arrived, and the next one is a week late.|trade|road
Someone has been drinking the best brandy and replacing it with tea.|crime|t:light
A noble's heir has left behind a trunk, and the keeper is afraid to open it.|politics|mystery
A cold spot in the common room has frightened off the regulars, and the owner is considering a priest.|undead|religion
The owner owes a great deal of money to someone who is visiting this week.|crime|trade
A guest left without paying, taking a very odd souvenir.|crime|t:light
Something has been stealing eggs from the henhouse, and the footprints are not a fox's.|monster|nature
A bard has been writing songs about the owner, and they are getting too close to the truth.|mystery|festival
The inspector is due, and the kitchen is in no state to be seen.|politics|t:light
A feud between two staff members has spread to the regulars, and the tables are choosing sides.|family|t:light
A pair of travelers have disappeared from their room, leaving their bags and a half-eaten supper.|mystery|t:grim
The stable has been cursed, or the horses think so, and no one will go in at night.|undead|road
The ale has been going off, and no one can say why. The brewer is blaming the barrels.|craft|t:light
A leaking pipe has soaked the best linen, and the owner is out of both money and sheets.|craft|q:good/q:fine
A regular has been picking fights with strangers, and the keeper suspects he is being paid to.|crime|politics
The kitchen fire has been put out three times this week and nobody has been near it.|magic|mystery
A hush has fallen on the village, and the inn is where the quiet is worst.|mystery|t:grim
A wedding party has booked every room, and the groom has not been seen since the night before.|family|mystery
The owner has been receiving anonymous letters offering to buy the place for a price too good to be true.|crime|trade|politics
A suspicious fire destroyed the neighboring stable, and the watch have begun to look at the inn.|crime|politics
""")
table("tav.secret", "A secret about the place", """
There is a hidden cellar below the cellar, and it is not empty.|mystery
The owner has been selling the cheapest ale as the best and keeping the difference.|crime|t:light
A back room is used for illicit meetings once a week, and the owner is paid to look away.|crime|politics
A passage under the floor connects to the building next door, and the staff use it to avoid the tax collector.|crime|trade
The owner is a retired adventurer, and a very good reason is why they quit.|mystery
A guest who died here years ago is still sometimes seen at the corner table.|undead|t:weird
The place is a front for something much older, and the owner may or may not know.|mystery|magic
Every third barrel is filled with something that is not ale.|crime
A set of ledgers records favors owed by half the village, and the owner never forgets a debt.|politics|trade
The house cat is a very old thing in a very small shape, and it is judging everyone.|fey|magic|t:light
The owner pays a regular fee to someone in the shadows, and is afraid to stop.|crime
The oldest regular is the real owner, and only keeps up appearances for reasons of his own.|mystery
The well in the yard is deeper than it should be, and something is lowered into it every month.|mystery|monster
A guest room has no window, and the owner never rents it out.|mystery|t:grim
The soup has been simmering without a break for sixty years, and nobody dares stop it.|t:light|magic
A cult meets here on the first of the month, and the owner has been invited to join.|religion|crime
The sign was painted by a famous artist, who is now very embarrassed about it.|t:light
The building was a prison once, and a cell door is still in the cellar.|crime|military
A tunnel from the cellar leads to a very old ruin, and the owner has been mapping it.|ruin|underground
The place is a safe house, and the owner has hidden more than a few people in the attic.|crime|politics|mystery
A guest left a locked chest as payment, and the owner has never been brave enough to open it.|treasure|mystery
The owner keeps a list of everyone who passes through, and passes it on to someone.|politics|crime
An old curse hangs on the place, and the staff tolerate small mishaps rather than ask why.|magic|undead
The best wine in the cellar is not wine at all, and the owner will not say what it is.|mystery|t:weird
A second set of books is kept in a hollow beam, and the real profits are very different.|crime|trade
The hearth is older than the building, and the stones are warm even when the fire is out.|magic|mystery
One of the staff is working undercover for the watch, and is not very good at it.|crime|politics|t:light
A friendly regular is actually a spy, and tonight is the night he reports.|politics|crime
The owner's recipe came from a stranger who paid in secrets, and a few of them are still being kept.|mystery
A door in the back opens on a different place on the third Tuesday of the month.|magic|t:weird
""")
table("tav.history", "A bit of history", """
The place was founded by a retired soldier who never wanted to leave the barracks.|military
It started as a single table in a farmer's kitchen and grew a room at a time.|family
The building was a granary, then a chapel, then a granary again, then this.
A famous fight here ended a feud, or began one. The accounts differ.|politics
The sign was won in a card game by a man who then had no place to hang it.|t:light
A caravan master built it in a single winter to have somewhere to stay while the pass was closed.|road|trade
The original owner vanished, and the place was passed from keeper to keeper by a series of unlikely accidents.|mystery
The inn has burned down twice and been rebuilt in the same spot both times.
It was built over a spring that never freezes, and the hearth is said to be lucky.|nature
A well-known poet wrote half of a famous ballad here, and the other half was written by someone who could not pay.|festival|t:light
It was once the only house in the district that would take anyone, and the habit stuck.|family
Legend says a hero once drank here before a great battle, and the stool is still kept for him.|military|t:light
Smugglers built the cellars, and the keeper has never found all of them.|crime|water
The walls were part of a larger fort, and the old arrow slits are now very drafty windows.|military
It was a customs house until the road moved, and the old scales still hang above the bar.|trade|road
The first keeper's recipes are still used, and they are not as secret as the family pretends.|family|craft|t:light
A plague emptied the house once, and it was reopened by someone who did not scare easily.|disease
It has changed hands eight times in thirty years, and every owner swore it was cursed.|mystery|t:light
Pilgrims have stopped here for generations, and the walls are full of their scratched prayers.|religion|road
A mine collapse filled the cellars with the dead, and the barrels are still stacked on top.|undead|craft|t:grim
Dwarves carved the cellar long before the house above it, and no one has found where it leads.|ruin|underground
It was once the toll house on a bridge that is no longer there.|road|water
A famous trial was held in its common room when the courthouse burned.|politics|crime
The old stable was a chapel, and nobody has gotten around to deconsecrating it.|religion|road
A recent fire gutted the upper floors, and the owner has been rebuilding with whatever turned up.
""")
table("tav.room.quirk", "A quirk of a room", """
The window looks out on the stable yard, and the dawn arrives with a rooster.
The bed is too short, and the keeper has a plank to add to it.
A draft whistles through the wall at a particular angle, and nobody has found the crack.
The door sticks in wet weather and must be shouldered open.
The floor tilts toward one corner, and a marble placed down will always roll there.
A brass bell by the bed rings the kitchen, if anyone is awake to answer it.
The fireplace smokes whenever the wind is from the east.
The chamber pot is a family heirloom, and the keeper wants it back.
A previous guest carved a name into the headboard, and has been cursing the room since.
The wall is thin, and the room next door has a very enthusiastic snorer.
The mattress is stuffed with something that smells of lavender.
The only chair has three legs and a very good view.
A hook on the wall holds a single, forgotten glove.
A thick rug hides a trapdoor that is locked, and nobody has the key.
It faces the street, and the noise is constant but friendly.
It has a private balcony, which is more of a ledge.
The latch only works from the inside, and the keeper knows a trick to work it from the outside.
A tiny shrine is tucked in a corner, and no one is sure who it was for.
There is a smell of old pipe smoke that no scrubbing has ever removed.
The window frame is painted with a very bad portrait of the founder.
It is the warmest room in the house, thanks to the chimney, and the most expensive.
Someone has painted the ceiling with stars, and a few have been added by the guests.
The washbasin is chipped, but the water is hot.
The curtains do not close, and the moon shines straight on the bed.
The door has three locks, and the keeper will only give you two keys.|q:common/q:good
The bed has a canopy and a small fortune in linens, and the keeper makes sure you notice.|q:fine
A small writing desk, a lamp, and a very good view of the garden.|q:good/q:fine
It has a lock, a bolt, and a shelf for the weapons you are not supposed to bring in.
""")
table("tav.patron.why", "Why a patron is here tonight", """
Waiting out a flooded road, and not enjoying it.|weather
Meeting someone who is late, and growing nervous.|mystery
Spending a windfall as quickly as possible.|treasure
Drinking to forget something that happened this morning.|family mystery
Celebrating a promotion, and being very loud about it.|trade politics
Hiding from a creditor in the one place he is never looked for.|crime trade
Looking for a job, and not finding one.|trade craft
Waiting for a caravan that is already a day overdue.|trade
Passing through with a heavy sack that they never put down.|treasure crime
Visiting an old friend who has not shown up.|family mystery
Trying to sell something, to anyone, at any price.|trade treasure
Scouting the place for a guild, and not very subtly.|trade politics
Here every night out of habit, and no longer remembers why.
Recovering from an injury and hoping the healer comes soon.|disease
Spending the last of their coin on one decent meal.
Dreading a letter that arrived this morning and has not been opened.|family mystery
Looking for someone, and asking carefully about everyone.|mystery crime
Rehearsing a speech under their breath.|politics festival
Here to win back a debt, in a game they have lost before.|crime treasure
Fleeing something that has not caught up yet.|crime mystery
On a first date, and horribly nervous.|family
In town for a wedding, and already tired of the relatives.|family festival
Waiting for the weather to turn so they can finally leave.|weather
Delivering a message to someone who is not here.|mystery politics
Dreaming of a better life, and drinking toward it.
Here to meet a stranger whose description they have been given.|mystery crime
Taking a rest after a long walk, and pretending it was not that long.
Following up on a rumor that brought them a great distance.|mystery
""")

# ============================================================ menus (prices come from the Player Core services table)
table("tav.menu.ale", "Beer, ale, and cider by the mug", """
House brown ale
Dark stout
Pale small beer
Hard cider
Honey mead
Amber ale
Barley beer
Spiced cider
Ginger beer
Perry
Black porter
Wheat ale
Hopped lager
Heather ale
Old strong ale
Applejack and water
Cold smoked beer
Rose-hip cider
Thick oat stout
Malted milk stout
Mint beer
Light summer ale
Winter warmer
Cellar-cold pale
""")
table("tav.menu.hot", "Hot drinks by the pot", """
Black tea
Mint tea
Roasted-barley coffee
Mulled cider
Hot spiced milk
Honeyed chamomile
Ginger tea
Strong black coffee
Cocoa with a pinch of salt
Fennel and anise tea
Hibiscus tea
""")
table("tav.menu.wine", "Wine by the bottle", """
Red house wine
Dry white
Plum wine
Blackberry wine
Rosé from an unnamed hillside
Sweet pear wine
Spiced red
Young green wine
Elderflower wine
Orchard wine
Honeyed white
Peppery red
""")
table("tav.menu.finewine", "Fine wine by the bottle", """
Reserve red, aged in oak
Vintage white from a good year
Sparkling wine
Late-harvest dessert wine
Cherry-cask red
Cellar-aged rosé
Ice wine
Old amber port
Golden sweet wine
Reserve white, bottled at the estate
""")
table("tav.menu.poor", "Poor meals", """
Thin barley gruel
Crusts and dripping
Boiled turnip
Onion broth
Cold porridge with a spoon of lard
Day-old bread and rind
Bean soup, mostly water
Boiled cabbage
Gruel with a few bits of bacon
Bread and a bowl of whatever is left
Pickled cabbage and a heel of rye
Stale loaf and rendered fat
Oat mush
Boiled egg and a crust
Watery lentils
Last night's stew, thinned out
Dumplings in clear broth
Toast with scraped butter
Dry biscuit and onion
Boiled potato, salted
""")
table("tav.menu.square", "Square meals", """
Mutton stew with bread
Fish pie with peas
Sausages and mash
Roast chicken leg with beans
Beef and barley soup with a crust
Meat pie with gravy
Pork and apple pie
Cheese, bread, and pickled onion
Ham hock with cabbage
Eel stew
Fried herring with potatoes
Shepherd's pie
Bacon and bean pottage
Lentil stew with dumplings
Baked trout with new potatoes
Roast pork with crackling
Egg and leek tart
Oxtail broth with bread
Chicken and mushroom pie
Cottage pie
Rabbit stew
Boiled beef with horseradish
Sausage roll with pickles
Venison pasty
Cabbage rolls stuffed with rice
""")
table("tav.menu.fine", "Fine dining", """
Glazed duck with plum sauce
Venison in red wine with root vegetables
Roast pheasant with chestnut stuffing
Saffron rice with a poached fish
Lamb shank braised in herbs
Pie of wild mushrooms and goose
Sea bass in butter and lemon
Truffled pork loin
Roasted quail with candied figs
Beef wellington with a sharp sauce
Honeyed ham with cloves
Seared scallops with leeks
Roast swan with berry sauce
Wild boar with apple and sage
A full course of soup, fish, game, and a sweet
Poached salmon with dill
Pheasant pie with a crust that crackles
Rack of lamb with mint
Glazed carrots, rare beef, and a very old sauce
A cheese board with a different wine for each wedge
""")
table("tav.menu.special", "A house specialty (tags name its price tier: cat:ale, cat:hot, cat:wine, cat:finewine, cat:poor, cat:square, cat:fine)", """
The House Pie: a fat pie of whatever the cook was proud of that morning|cat:square|2
Grandmother's Stew, which the cook swears is the original recipe|cat:square|2
Fire Ale, a spiced dark ale served warm in a stone mug|cat:ale|2
The Sunday Roast, with all the trimmings and a very large Yorkshire pudding|cat:square|1.5
The Keeper's Broth, thin, hot, and said to cure everything|cat:poor|1.5|q:squalid/q:common
Blackbird Bread, a dense loaf of seeds and honey that is somehow always warm|cat:poor|1
Honey-Smoke Mead, brewed out the back with bees the owner will not name|cat:ale|1.5|t:light
The Traveler's Dram, small, strong, and served in a cup shaped like a boot|cat:ale|1.5|road
Founder's Reserve, a wine made from the cellar's oldest cask|cat:finewine|2|q:good/q:fine
The Duck of the Day, which is whatever duck the keeper could get|cat:fine|2|q:good/q:fine
The Midnight Kettle, a tea of dark herbs that keeps drinkers awake for exactly one more hour|cat:hot|1.5
The Dragon's Breath, a pepper stew that regulars attempt and visitors regret|cat:square|1.5|t:light
Sailor's Pot, a thick fish stew with the bones still in|cat:square|1.5|water
Cider of the Hearth, a thick cider mulled for hours on the stove|cat:hot|1.5
Cheesemonger's Plate, with five cheeses of the owner's own making|cat:square|1
The Reeve's Pie, once a punishment, now a delicacy|cat:square|1|politics|t:light
Beggar's Delight, a sweet bun filled with whatever jam was cheapest|cat:poor|1|t:light
The Hangman's Draught, a rough spirit in a tankard that bears no label|cat:ale|1|crime|t:grim
The Pilgrim's Plate, fish, bread, and a clear soup, served in silence|cat:square|1|religion
Spirits of the Cellar, an unlabeled bottle only some customers are offered|cat:wine|1|mystery
""")

# ============================================================ the Underhallow flavor (limited to the hallowmead pack)
UNDERHALLOW = {
    "tav.name.a": """
Salvaged|underground c:goblin p:hallowmead|2|c:goblin
Patched|underground c:mender p:hallowmead|2|c:mender
Spare|underground c:mender p:hallowmead|1.5|c:mender
Level|underground c:kobold p:hallowmead|2|c:kobold
Sunken|underground c:grippli p:hallowmead|2|c:grippli
Mossy|underground c:leshy p:hallowmead|2|c:leshy
Quiet|underground c:ratfolk p:hallowmead|2|c:ratfolk
Teal|underground c:awakened p:hallowmead|1.5|c:awakened
Lamplit|underground p:hallowmead|2
Deep|underground p:hallowmead|1.5
""",
    "tav.name.thing": """
Refuse Chute|underground c:goblin p:hallowmead|2|c:goblin
Scrap Crane|underground c:goblin p:hallowmead|1.5|c:goblin
Arch|underground c:kobold p:hallowmead|2|c:kobold
Chisel|underground c:kobold p:hallowmead|1.5|c:kobold
Cart Rail|underground c:kobold p:hallowmead|1|c:kobold
Ledger|underground c:ratfolk p:hallowmead|1.5|c:ratfolk
Lamp Hook|underground c:ratfolk p:hallowmead|1|c:ratfolk
Sluice|underground c:grippli p:hallowmead|2|c:grippli
Stilt|underground c:grippli p:hallowmead|1.5|c:grippli
Root|underground c:leshy p:hallowmead|2|c:leshy
Glow-Pod|underground c:leshy p:hallowmead|1.5|c:leshy
Mended Cup|underground c:mender p:hallowmead|2|c:mender
Button|underground c:mender p:hallowmead|1.5|c:mender
Stitch|underground c:mender p:hallowmead|1|c:mender
Pink Mushroom|underground c:awakened p:hallowmead|1.5|c:awakened
Waystone|underground p:hallowmead|1.5
Crystal Spire|underground trade p:hallowmead|1
""",
    "tav.look": """
Furniture assembled from everything the surface threw away, none of it matching and all of it well loved.|underground c:goblin p:hallowmead|3|c:goblin
Scrap chandeliers hang from the rafters, strung with bottle glass that throws colored light across the floor.|underground c:goblin p:hallowmead|2|c:goblin
Rope bridges link a gallery of booths above the main floor, and the whole place sways a little when it fills.|underground c:goblin p:hallowmead|2|c:goblin
Fine stonework from floor to roof: arches, columns, and a bar carved so exactly that it gleams.|underground c:kobold p:hallowmead|3|c:kobold
A hand-lettered sign over the door reads ROCK IS GOOD, in the careful letters of a very proud sign painter.|underground c:kobold t:light p:hallowmead|2|c:kobold
A single mine-cart rail runs along the wall, and orders arrive on a little cart that is always slightly late.|underground c:kobold t:light p:hallowmead|2|c:kobold
A sewer-level cellar lit by low lamps, with velvet curtains, a gold-painted chair, and a ledger on every shelf.|underground c:ratfolk p:hallowmead|3|c:ratfolk
Heavy curtains and low lamps keep the corners dark, and the floor is swept so quietly that no one hears the sweeper.|underground c:ratfolk mystery p:hallowmead|2|c:ratfolk
A platform on stilts over an underground stream, with leaf-shaped awnings and a trapdoor for dropping a line.|underground c:grippli water p:hallowmead|3|c:grippli
Water runs in a channel along the middle of the floor, and the tables are arranged on either side.|underground c:grippli water p:hallowmead|2|c:grippli
Seats grown from living roots, a canopy of mushroom caps, and a floor of soft moss that never feels damp.|underground c:leshy nature p:hallowmead|3|c:leshy
There is no fire and no lantern, only luminous pods that glow a little brighter when someone laughs.|underground c:leshy nature t:weird p:hallowmead|2|c:leshy
A long workshop floor turned into a taproom, with a blue glow in the lamps and mismatched stools patched to match.|underground c:mender craft p:hallowmead|3|c:mender
Poppet-scale furniture sits beside automaton-scale stools, and the bar has two heights.|underground c:mender t:light p:hallowmead|2|c:mender
A den cut into the rock, warm with golden light, with tiny stairs and a bar sized for the paws that use it.|underground c:awakened t:light p:hallowmead|3|c:awakened
Neon-pink and teal light spills from crystal formations in the walls, and the whole place looks slightly too bright.|underground c:awakened magic p:hallowmead|2|c:awakened
A great cavern with a ceiling too high to see, and a bar built at the one spot where the echo behaves.|underground p:hallowmead|2
Every faction has left its mark here: a goblin skull banner, a kobold arch, a ratfolk lamp, a grippli awning, a leshy root.|underground trade festival p:hallowmead|1.5
""",
    "tav.smell": """
Salt, rust, and frying scrap-bread.|underground c:goblin p:hallowmead|2|c:goblin
Hot stone, chalk dust, and a pot of something with a lot of garlic.|underground c:kobold p:hallowmead|2|c:kobold
Old paper, candle wax, and strong tea.|underground c:ratfolk p:hallowmead|2|c:ratfolk
Wet stone, cold river water, and fresh reeds.|underground c:grippli water p:hallowmead|2|c:grippli
Damp earth, mushrooms, and the sweet, green smell of growing things.|underground c:leshy nature p:hallowmead|2|c:leshy
Machine oil, warm cloth, and a very faint metallic tang.|underground c:mender craft p:hallowmead|2|c:mender
Warm fur, nuts, and sweet berries.|underground c:awakened t:light p:hallowmead|2|c:awakened
Cave mushrooms, lamp oil, and the cool smell of deep stone.|underground p:hallowmead|2
""",
    "tav.sound": """
A crane clanks in the distance, and now and then something heavy lands with a crash.|underground c:goblin p:hallowmead|2|c:goblin
The rhythmic tap of a chisel somewhere, and a cheerful voice counting under its breath.|underground c:kobold p:hallowmead|2|c:kobold
Soft, hurried footsteps and the whisper of paper.|underground c:ratfolk mystery p:hallowmead|2|c:ratfolk
The rush of a waterfall and the plink of drops on a leaf awning.|underground c:grippli water p:hallowmead|2|c:grippli
The faint creak of roots settling and the rustle of leaves in a breeze that cannot be there.|underground c:leshy nature p:hallowmead|2|c:leshy
A steady click of tools and a low mechanical hum under the music.|underground c:mender craft p:hallowmead|2|c:mender
The pad and scratch of many small feet on the stone.|underground c:awakened t:light p:hallowmead|2|c:awakened
Dripping water, distant echoes, and the occasional far-off rumble that no one mentions.|underground p:hallowmead|2
""",
    "tav.crowd": """
A salvage crew straight off the sorting floor, arguing about who found the best thing.|underground c:goblin trade p:hallowmead|2|c:goblin
A pair of kobold masons share a stone table and a very detailed argument about an arch.|underground c:kobold craft p:hallowmead|2|c:kobold
Couriers come and go in a steady trickle, none of them stopping at the bar for long.|underground c:ratfolk mystery p:hallowmead|2|c:ratfolk
Waterway wardens lean on the rail with mugs, watching the current as if it might say something.|underground c:grippli water p:hallowmead|2|c:grippli
Leshys tend a small plot of mushrooms between the tables, and regulars pick as they pass.|underground c:leshy nature t:light p:hallowmead|2|c:leshy
Menders and half-repaired customers share a long table, trading advice and spare parts.|underground c:mender craft p:hallowmead|2|c:mender
A group of newly awakened animals practice reading the menu aloud, slowly and with great pride.|underground c:awakened t:light p:hallowmead|2|c:awakened
Representatives of three different settlements are pretending not to be eavesdropping on each other.|underground politics trade p:hallowmead|2
A market-day crowd from the Crossings fills the place, loud with haggling and good cheer.|underground trade festival busy:packed p:hallowmead|2
""",
    "tav.rule": """
No one throws anything down the refuse chute without checking it first, and the keeper has a basket of rejects.|underground c:goblin t:light p:hallowmead|2|c:goblin
Everyone leaves their mugs on the tray, and the tray goes back to the kitchen where the keeper can see.|underground c:goblin p:hallowmead|1|c:goblin
No one touches the arches. The kobold who built them is watching.|underground c:kobold t:light p:hallowmead|2|c:kobold
Nobody is allowed to say what the stonework looks like, only how it feels.|underground c:kobold t:light p:hallowmead|1|c:kobold
Names are given at the door, and the keeper writes them in a book that is never shown.|underground c:ratfolk mystery p:hallowmead|2|c:ratfolk
No loud voices after the first bell, and no mention of the surface by name.|underground c:ratfolk mystery p:hallowmead|1|c:ratfolk
Shoes off on the platform, and mind the gap by the rail.|underground c:grippli water p:hallowmead|2|c:grippli
Nothing is thrown in the water, ever, and the keeper has a net for those who forget.|underground c:grippli water p:hallowmead|1|c:grippli
No flame past the door, and no cutting of anything that has roots.|underground c:leshy nature p:hallowmead|2|c:leshy
Customers who damage the furniture are expected to help repair it, and will be taught how.|underground c:mender craft p:hallowmead|2|c:mender
Nothing is turned away, and nothing is wasted, and the keeper will explain this in detail.|underground c:mender family p:hallowmead|1|c:mender
Every customer is asked a question before they are served, and the answer is not graded.|underground c:awakened mystery t:light p:hallowmead|2|c:awakened
No one is allowed to bring a weapon past the arch, and no one is allowed to take one out.|underground military politics p:hallowmead|1.5
""",
    "tav.problem": """
A salvage haul has come in with something stuck in it that is making a noise, and the whole crew has gone quiet.|underground c:goblin mystery t:weird p:hallowmead|2|c:goblin
The keeper traded a barrel of ale for a pile of salvage, and the pile has started to move.|underground c:goblin t:light p:hallowmead|1.5|c:goblin
A kobold inspector has declared an arch unsafe, and the roof is being propped up by every customer's goodwill.|underground c:kobold craft t:light p:hallowmead|2|c:kobold
A crack has appeared in the best column, and nobody wants to be the one to say.|underground c:kobold craft p:hallowmead|2|c:kobold
A courier has not come back from her run, and the keeper keeps setting a place for her.|underground c:ratfolk mystery p:hallowmead|2|c:ratfolk
A regular has been selling information to someone from the surface, and the keeper knows.|underground c:ratfolk politics crime p:hallowmead|2|c:ratfolk
The water level has dropped by a handspan this week, and no one will say why.|underground c:grippli water mystery p:hallowmead|2|c:grippli
Something large has been seen in the current, and the staff have started fishing with a longer line.|underground c:grippli water monster p:hallowmead|1.5|c:grippli
A root has pushed through the floor and is growing toward the bar, and the leshys will not let anyone cut it.|underground c:leshy nature p:hallowmead|2|c:leshy
A leshy regular has gone silent and keeps looking at the same wall.|underground c:leshy mystery p:hallowmead|1.5|c:leshy
The spare-parts bin is empty, and three regulars are waiting for repairs.|underground c:mender craft p:hallowmead|2|c:mender
A new arrival from the surface refuses to say where they were thrown away from, and the menders are patient.|underground c:mender family mystery p:hallowmead|2|c:mender
A visitor wandered in from the dungeon end and has been asking very thoughtful questions of the staff for a week.|underground c:awakened mystery t:light p:hallowmead|2|c:awakened
A new species of fungus is growing on the walls, and nobody has decided whether to eat it.|underground nature t:light p:hallowmead|1.5
Three settlements have each sent a representative, and none of them will sit next to the others.|underground politics t:light p:hallowmead|2
The lamp oil has run short, and everyone is pretending the dark is a style choice.|underground trade t:light p:hallowmead|1.5
""",
    "tav.secret": """
The chute behind the bar leads somewhere much deeper than anyone has admitted.|underground c:goblin mystery p:hallowmead|1.5|c:goblin
A treasure that fell down the chute years ago is hidden in the false bottom of a barrel.|underground c:goblin treasure p:hallowmead|1.5|c:goblin
One of the arches is not load-bearing, and the owner has been paid to say it is.|underground c:kobold crime craft p:hallowmead|1.5|c:kobold
The cellar has a kobold-built door that no one is allowed to open, and the kobolds who built it will not say why.|underground c:kobold mystery p:hallowmead|1.5|c:kobold
A table in the back is a drop for messages between the Hushwarrens and someone on the surface.|underground c:ratfolk politics crime p:hallowmead|2|c:ratfolk
The ledger behind the bar records what happened during a plague, and the owner is waiting for the right moment.|underground c:ratfolk politics mystery p:hallowmead|1.5|c:ratfolk
The deep water below the platform has been disturbed on certain nights, and the owner keeps a record.|underground c:grippli water monster p:hallowmead|1.5|c:grippli
One of the seats is a young leshy that is slowly waking up, and no one has told it.|underground c:leshy nature magic t:light p:hallowmead|1.5|c:leshy
The keeper has a drawer of keepsake parts from every regular who could not be fixed, and visits it often.|underground c:mender family p:hallowmead|1.5|c:mender
One of the staff is an awakened creature who has not told anyone how new they are.|underground c:awakened t:light p:hallowmead|1.5|c:awakened
A back room has been used for meetings between faction envoys, and the owner has quietly learned a great deal.|underground politics mystery p:hallowmead|1.5
""",
    "tav.history": """
It was built from salvage the surface threw away, one piece at a time, and the owner can tell you where each came from.|underground c:goblin p:hallowmead|2|c:goblin
It started as a kobold workmen's canteen, and the masons never quite let go of it.|underground c:kobold craft p:hallowmead|2|c:kobold
It was founded by ratfolk after the plague blame, as a place where the records could be kept in plain sight.|underground c:ratfolk politics p:hallowmead|1.5|c:ratfolk
The grippli built it where the river first reached them, and the first table is still there.|underground c:grippli water p:hallowmead|2|c:grippli
It was grown, not built, over many seasons, and the leshys can tell you which branches are the oldest.|underground c:leshy nature p:hallowmead|2|c:leshy
It began as a repair bench where anyone could bring something broken, and the tavern grew around it.|underground c:mender craft family p:hallowmead|2|c:mender
It was one of the first places in the Underhallow where all kinds of folk shared a table.|underground trade family p:hallowmead|1.5
""",
    "tav.decor": """
Spare parts and old tools hung as ornaments, each with a tag naming where it was found.|underground craft p:hallowmead|2|c:goblin/c:mender
A scale model of a tunnel arch, left unfinished, and kept under glass.|underground c:kobold craft p:hallowmead|1.5|c:kobold
A pale mark, discreetly scratched at the corner of the bar, that regulars know to look for.|underground c:ratfolk mystery p:hallowmead|1.5|c:ratfolk
Hanging woven mats, a net of dried reeds, and a hook for every catch.|underground c:grippli water p:hallowmead|1.5|c:grippli
Pressed leaves and spore prints framed on the wall, each labeled in a very careful hand.|underground c:leshy nature p:hallowmead|1.5|c:leshy
Banners from several Underhallow settlements, hung side by side, each slightly overlapping the next.|underground trade politics p:hallowmead|2
""",
    "tav.entertainment": """
A goblin band plays on pots, pans, and a very serious bass drum made of a barrel.|underground c:goblin t:light festival p:hallowmead|2|c:goblin
A kobold stonecutter hums a work song, and the whole room slowly joins in.|underground c:kobold t:light p:hallowmead|1.5|c:kobold
A quiet reader reads aloud from a ledger of old rumors, and the audience pays for each.|underground c:ratfolk mystery p:hallowmead|1.5|c:ratfolk
A grippli singer performs from the rail over the water, and the echoes carry the verses.|underground c:grippli water p:hallowmead|1.5|c:grippli
A choir of leshys hum together, and the glow-pods pulse to the beat.|underground c:leshy nature t:weird p:hallowmead|1.5|c:leshy
A poppet storyteller shares the tale behind every patch on her cloak, and each is better than the last.|underground c:mender family p:hallowmead|2|c:mender
An awakened parrot tells jokes in several voices, and is only sometimes understood.|underground c:awakened t:light p:hallowmead|1.5|c:awakened
A mixed troupe from different settlements trade turns, and everyone is slightly amazed they get along.|underground festival trade p:hallowmead|1.5
""",
    "tav.menu.ale": """
Refuse-chute ale, which the goblins insist is a vintage|underground c:goblin t:light p:hallowmead|2|c:goblin
Salvage stout|underground c:goblin p:hallowmead|1.5|c:goblin
Keystone lager|underground c:kobold p:hallowmead|1.5|c:kobold
Mason's brown|underground c:kobold p:hallowmead|1.5|c:kobold
Hushwarren pale|underground c:ratfolk p:hallowmead|1.5|c:ratfolk
Reed-water beer|underground c:grippli water p:hallowmead|1.5|c:grippli
Glow-moss ale|underground c:leshy nature t:weird p:hallowmead|1.5|c:leshy
Fungus stout|underground c:leshy nature p:hallowmead|1.5|c:leshy
Mender's mild|underground c:mender p:hallowmead|1.5|c:mender
Cave-cellar ale|underground p:hallowmead|2
Mushroom beer|underground p:hallowmead|1.5
""",
    "tav.menu.hot": """
Glow-moss tea|underground c:leshy nature t:weird p:hallowmead|2|c:leshy
Cave-mushroom broth tea|underground p:hallowmead|1.5
Salvaged-bean coffee|underground c:goblin t:light p:hallowmead|1.5|c:goblin
Warm root tea|underground c:leshy nature p:hallowmead|1.5|c:leshy
Mender's tea, sweet and strong|underground c:mender p:hallowmead|1.5|c:mender
""",
    "tav.menu.wine": """
Cave-fruit wine|underground p:hallowmead|2
Fungus wine, an acquired taste|underground c:leshy t:weird p:hallowmead|1.5|c:leshy
Berry wine from a leshy garden|underground c:leshy nature p:hallowmead|1.5|c:leshy
Surface wine, smuggled and overpriced|underground c:ratfolk crime p:hallowmead|1.5|c:ratfolk
""",
    "tav.menu.poor": """
Fungus gruel|underground p:hallowmead|2
Boiled cave tubers|underground p:hallowmead|2
Scrap-bread and rendered fat|underground c:goblin p:hallowmead|2|c:goblin
Moss broth|underground c:leshy nature p:hallowmead|1.5|c:leshy
Mushroom mash on a stone plate|underground p:hallowmead|1.5
Crusts from the surface, boiled soft|underground c:goblin p:hallowmead|1|c:goblin
""",
    "tav.menu.square": """
Fungus stew with bread|underground p:hallowmead|3
Cave-mushroom pie|underground p:hallowmead|3
Fried blind fish with cave greens|underground c:grippli water p:hallowmead|2|c:grippli
Stuffed cap mushrooms with roasted roots|underground c:leshy nature p:hallowmead|2|c:leshy
Salvage stew, whatever came down the chute that morning|underground c:goblin t:light p:hallowmead|2|c:goblin
Stone-baked flatbread with crumbly cheese|underground c:kobold p:hallowmead|2|c:kobold
Eel and reed pie|underground c:grippli water p:hallowmead|1.5|c:grippli
Honeyed grubs and flatbread|underground c:awakened t:light p:hallowmead|1.5|c:awakened
A small plate of everything the kitchen could mend into a meal|underground c:mender p:hallowmead|1.5|c:mender
""",
    "tav.menu.fine": """
A tasting of every settlement's best dish, one small plate at a time|underground trade festival p:hallowmead|2
Roasted glow-cap with root vegetables in a mushroom reduction|underground c:leshy nature p:hallowmead|1.5|c:leshy
Stuffed blind trout with wild herbs|underground c:grippli water p:hallowmead|1.5|c:grippli
Honeyed cave-fruit tart with spiced cream|underground p:hallowmead|1.5
""",
    "tav.menu.special": """
Scrap Soup, thick with tubers and a mystery bone, served in a hubcap|cat:poor underground c:goblin t:light p:hallowmead|2|c:goblin
Keystone Pie, a stone-baked pie with a crust as hard as an arch|cat:square underground c:kobold t:light p:hallowmead|2|c:kobold
The Quiet Cup, a tea served to anyone who wants to talk about nothing|cat:hot underground c:ratfolk mystery p:hallowmead|1.5|c:ratfolk
River Lager, brewed with water drawn from the stream under the floor|cat:ale underground c:grippli water p:hallowmead|2|c:grippli
Glowcap Ale, which gives the drinker a faint green shine|cat:ale underground c:leshy t:weird p:hallowmead|2|c:leshy
Repair Stew, a recipe that changes depending on what the cook had to mend that morning|cat:square underground c:mender t:light p:hallowmead|2|c:mender
Wake-Up Tea, a bracing brew for the newly awakened and the very tired|cat:hot underground c:awakened t:light p:hallowmead|2|c:awakened
The Crossings Platter, a little of everything and a lot of arguments over who is better at what|cat:square underground trade festival p:hallowmead|1.5
""",
    "tav.room.quirk": """
A tiny window cut into the rock, with a glow-lamp where the sun would be.|underground p:hallowmead|2
The bed is a stone shelf with a thick mat, and the ceiling is just low enough to remind you.|underground p:hallowmead|2
Water trickles down one wall in a channel and drains neatly into a groove in the floor.|underground c:grippli water p:hallowmead|2|c:grippli
The floor is moss, soft and a little warm, and the bed is a grown hollow in the wall.|underground c:leshy nature p:hallowmead|2|c:leshy
A salvaged mirror, a mismatched chair, and a blanket made of someone else's coat.|underground c:goblin p:hallowmead|2|c:goblin
The walls are smooth and perfect, and the door is a little too well made.|underground c:kobold craft p:hallowmead|2|c:kobold
The key is on a loop of string, and the keeper will watch you tie it to your belt.|underground c:ratfolk mystery p:hallowmead|2|c:ratfolk
The bed has been mended many times, and every patch has a small tag with a name.|underground c:mender p:hallowmead|2|c:mender
""",
    "tav.patron.why": """
A salvage runner with a sack of something that is probably worth a lot and probably not what she thinks.|underground c:goblin trade p:hallowmead|1.5
Waiting for a delivery that was supposed to come by mine cart.|underground c:kobold trade p:hallowmead|1.5
A courier between settlements, drinking one drink slowly before the next run.|underground c:ratfolk mystery p:hallowmead|1.5
In from the underground river with a story about something large in the current.|underground c:grippli water monster p:hallowmead|1.5
A leshy gardener with a sack of seedlings, asking whether anyone has seen a particular root.|underground c:leshy nature t:light p:hallowmead|1.5
Taking a break from a workshop shift and complaining about the parts supply.|underground c:mender craft p:hallowmead|1.5
Newly awakened and still working out what a drink is for.|underground c:awakened t:light p:hallowmead|1.5
Traveling between the Crossings and a distant settlement and not enjoying the walk.|underground road p:hallowmead|1.5
In from the dungeon end, wanting to see the settlement before going back.|underground monster p:hallowmead|1
""",
}


# A patron's hook. It reads like the Story tab's Hook, with three differences: the patron is named without their description
# (the People list shows it right beside), the job is not said to be at the inn (the patron is at the inn, the job is
# elsewhere), and the reason is held to the request's theme (strict_anchor). Hidden, so it is not in the Story tab's list.
RECIPES = {
    "inn_hook": {
        "title": "Hook", "page_type": "Hook", "status": "open", "threat": ["Low", "Moderate", "Severe"], "hidden": True,
        "slots": [{"key": "who", "label": "Who", "table": "who.patron"},
                  {"key": "what", "label": "What", "table": "task"},
                  {"key": "where", "label": "Met at", "table": "where"},
                  {"key": "when", "label": "When", "table": "when.hook"},
                  {"key": "why", "label": "Why", "table": "why", "strict_anchor": True}],
        "extras": [{"key": "reward", "label": "Reward", "table": "hook.reward"},
                   {"key": "twist", "label": "Twist", "table": "hook.twist"},
                   {"key": "opposition", "label": "Opposition", "table": "hook.opposition"},
                   {"key": "rep", "label": "Reputation", "table": "rep.effects"}],
        "compose": ["{@who} {@what}, {@why}. The deadline: {@when}. The pay: {@reward}.",
                    "{@when}, {@who} {@what}, {@why}. The pay: {@reward}.",
                    "{@who} {@what}, {@why}. Time is short: {@when}. The pay: {@reward}."],
        "title_template": "{@who.short} {@what.short}",
    },
}
def hallowmead_additions():
    """The Underhallow lines as {table name: [entries]}; every line is limited to the hallowmead pack by its p: tag."""
    return {name: [ln.strip() for ln in text.strip().splitlines() if ln.strip() and not ln.strip().startswith("#")]
            for name, text in UNDERHALLOW.items()}

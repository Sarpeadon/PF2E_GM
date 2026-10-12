"""The Hallowmead and Underhallow setting, ready to load into the Notebook, the NPC generator, and Story Forge.

Canon pages are written from the master setting bible (Hallowmead_Setting_Bible_Master 6.docx, master edition
July 2026). Each page names the bible section it came from. Material that came from our chats and is not in the bible
(the annual events, the King's Turnip quest, and some art-direction notes) is labeled PROPOSED or marked as chat
material, so it can never be mistaken for canon.

Canon labels on every page:

  ESTABLISHED   in the bible. Parts the bible marks LOCKED are called out in the page text.
  PROPOSED      from our brainstorming chats, not in the bible. Not canon.
  TBD           an open question in the bible. Nothing is invented to fill it.

Information boundary: pages tagged gm-only hold material the bible marks GM-ONLY. Story Forge never draws on them.
Court members whose pages carry a secret (Orion, Liza, Malcior) are usable in stories, but their secrets live only in the
page text, and a page's `avoid` list stops a story from drifting into its secret's theme (Malcior never meets undead
events, for example).

Loading is safe to repeat. Missing pages are added, pages from an earlier import that you have not edited are brought up
to date (keeping their reputation, status, and links), pages you edited are left alone, and your ancestry mix is replaced
only if you say so.
"""
import copy
import datetime
import hashlib
import re
import uuid

SEED = "hallowmead"
REV = 2
BIBLE = "Setting Bible"
CANON_LABELS = ("ESTABLISHED", "PROPOSED", "TBD")

# Relative weights for who lives in the Underhallow. The bible lists the playable ancestries but gives no numbers, so these
# are a starting guess: goblins and kobolds are the largest settlements, leshys are capped by the bible's population
# limit, and awakened animals are few. Change them in Setting Demographics.
DEMOGRAPHICS = {
    "Goblin": 20, "Kobold": 18, "Ratfolk": 12, "Automaton": 10, "Grippli": 9, "Leshy": 7, "Arboreal": 7,
    "Poppet": 6, "Awakened Animal": 6,
}
# What the first version of this import set, so an upgrade can tell it from a mix you chose yourself.
V1_DEMOGRAPHICS = {"Goblin": 20, "Kobold": 18, "Ratfolk": 12, "Leshy": 12, "Grippli": 10, "Automaton": 8,
                   "Awakened Animal": 7, "Arboreal": 5, "Poppet": 4, "Human": 5, "Dwarf": 2}


def body_hash(text):
    return hashlib.sha1(str(text).strip().encode("utf-8")).hexdigest()[:12]


def _page(ptype, title, body, canon, source, status="", tags=(), **extra):
    body = body.strip()
    p = {"id": uuid.uuid4().hex[:10], "title": title, "type": ptype, "status": status, "tags": list(tags),
         "body": body, "created": datetime.date.today().isoformat(), "canon": canon, "source": source,
         "seed": SEED, "rev": REV, "seed_hash": body_hash(body)}
    p.update(extra)
    return p


def _faction(title, kind, body, source, tags, **extra):
    from . import reputation
    return _page("Faction", title, body, "ESTABLISHED", source, status="neutral", tags=tags, kind=kind,
                 rep=reputation.new_rep(0), goals=[], rivals=[], **extra)


def _npc(title, role, ancestry, body, source, tags, canon="ESTABLISHED", **extra):
    return _page("NPC", title, body, canon, source, status="alive", tags=tags, ancestry=ancestry, role=role, **extra)


def _place(title, kind, body, source, tags, preps, canon="ESTABLISHED", **extra):
    return _page("Location", title, body, canon, source, tags=tags, kind=kind, preps=preps, **extra)


def S(section):
    return f"{BIBLE}: {section}"


CHATS = "Proposed in our chats; not in the setting bible"


def build_pages():
    """Fresh page dicts for the whole setting. Titles are unique and every [[link]] points at another page here."""
    P = []

    # ------------------------------------------------------------------ factions
    P.append(_faction(
        "Finders Keep", "goblin scavenger settlement",
        "Finders Keep is the goblin settlement, built directly beneath Hallowmead's refuse chutes, so that everything "
        "the surface throws away falls into goblin hands. It is a chaotic, colorful, multi-tiered settlement in a massive "
        "tall-ceilinged cavern, built entirely from repurposed surface refuse, with scrap towers, rope bridges, cranes, "
        "and sorting platforms. Goblins are brilliant tinkerers and improvised engineers, every single thing they own is "
        "something someone else did not want, and they are natural trade partners of the kobolds. Their emotional hook is "
        "worth: proving that discarded things still have value.\n\n"
        "Leader: [[Kraggix Scraptooth]], Chief of Finders Keep.\n\n"
        "Banner (visual canon): rust-red cloth with patched repairs and a ragged lower hem, bearing a large off-white skull "
        "with uneven eye sockets, a triangular nose cavity, and elongated dripping lower teeth. Crude, proud, and "
        "goblin-made, flat on the cloth, and it reads as scrap-built goblin ingenuity. Faction colors are rust red, dirty "
        "green, and faded yellow.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners"),
        ["underground", "trade", "craft", "treasure"]))
    P.append(_faction(
        "The Grand Underhall", "kobold mason settlement",
        "The Grand Underhall is the kobold settlement and the central connecting infrastructure hub of the Underhallow, "
        "with the finest stonework there: carved columns, arched ceilings, gothic-style architecture, dragon head carvings "
        "on the facades, and mine cart rails for logistics. Signs in childlike handwriting such as \"WE DIG BIG HOLE\" and "
        "\"ROCK IS GOOD!\" show kobold pride on full display. The kobolds were the original architects of the livable "
        "Underhallow, dug the first tunnels, and still maintain the infrastructure for every faction, so every faction's "
        "home exists because a kobold built it. They have the best mental map of the tunnels and quiet economic leverage, "
        "and Ulzerett cannot unite the factions without their buy-in. Their emotional hook is being the foundation "
        "everyone stands on and nobody acknowledges.\n\n"
        "Leader: [[Skritch Stonebender]], Master Mason.\n\n"
        "Banner (the dragon-question-mark silhouette is LOCKED CANON): deep red or brick-red cloth bearing a white "
        "dragon-shaped question mark, with the dragon's head forming the upper curve, the neck forming the body, and the "
        "tail curling inward as the hook. It reads as proud builders asking what lies deeper. Faction colors are warm "
        "stone tones with subtle gold accents.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners"),
        ["underground", "craft", "politics"]))
    P.append(_faction(
        "The Hushwarrens", "ratfolk settlement",
        "The Hushwarrens is the ratfolk settlement, built in abandoned catacombs and lower sewer levels near the surface, "
        "with three visible layers: surface streets, active sewers, and catacomb warrens, reached through the North Ward, "
        "the Merchant District, and the South Ward. It is understated and hard to find from outside, though the ratfolk "
        "love money and status symbols and keep a golden throne, velvet curtains, and bookshelves stuffed with records "
        "(with comic signs like \"SHINY THINGS VERY IMPORTANT\"). The ratfolk were blamed for a plague that swept "
        "Hallowmead's lower districts two generations ago and were driven underground by mobs. They keep meticulous "
        "records proving what actually happened, operate covertly on the surface, and serve as the Underhallow's "
        "connection to surface information and goods. Their emotional hook is injustice they can prove and no one will "
        "hear.\n\n"
        "Leader: [[Vesk Quickwhisker]], Warden and Guildmaster.\n\n"
        "Banner (visual canon): charcoal-black, gray-purple, or desaturated blue-black cloth bearing a pale broken "
        "crescent above a central downward fang or dagger-like mark with two smaller lower points. It is a sign noticed "
        "only after learning to look for it, must resemble the symbol on Vesk's cloak and banner, and is never a route "
        "map, node network, or circuitry. Faction colors are charcoal, deep blue, and muted purple.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners"),
        ["underground", "mystery", "trade", "crime"]))
    P.append(_faction(
        "Stillwater Hollow", "grippli settlement",
        "Stillwater Hollow is the grippli settlement, built along and around the underground river the grippli followed "
        "down from the surface, with platforms on stilts over water, cascading waterfalls and pools, and organic "
        "amphibious architecture of leaf-like awnings and natural curves in a blue-green palette. The grippli once lived "
        "in a river delta near what became Hallowmead, and followed the receding water underground when the city diverted "
        "waterways for irrigation, sanitation, and industry. They could not go deeper because they ran into something "
        "terrible, likely an aboleth or similar aberration, so they settled in the upper Underhallow as the safest place "
        "between two dangers, and they are the only faction who knows firsthand how bad the deep gets. Water from "
        "Stillwater flows toward the Quiet Ring. Their emotional hook is slow erasure from above, terror from below, and "
        "no safe direction.\n\n"
        "Leader: [[Brakka Mossleap]], Elder.\n\n"
        "Banner (visual canon): teal and blue-green cloth bearing a pale flowing water-current made of loose brush-like "
        "strokes with small droplets, reading as flow around obstacles rather than through them.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners"),
        ["underground", "nature", "mystery"]))
    P.append(_faction(
        "The Quiet Ring", "leshy and arboreal settlement",
        "The Quiet Ring is an immense underground forest, a biome rather than a garden, where nothing was built and "
        "everything was grown: living root walls, fungal shelf platforms, mushroom canopy shelters, and moss floors lit "
        "by glowing mushrooms, luminous spore pods, and phosphorescent pools (there are no lanterns and no fire). An "
        "ancient druidic circle of standing stones sits at the center beside a massive central tree that is the heart of "
        "the settlement, and the water of Stillwater Hollow flows through or connects to it. Root and fungus leshys live "
        "here as equals with arboreals, who see each other as family. The leshys were created by a forgotten druidic "
        "circle for unknown purposes and there is a fixed limit to how many can exist, so every leshy death is a "
        "potentially permanent loss and the community is cautious and risk-averse; arboreals are naturally occurring and "
        "can reproduce, which partly solves the problem. The leshys feel sympathy for the automatons of the Mending. "
        "Their emotional hook is survival and kinship, and a community that cannot replenish itself.\n\n"
        "Leader: [[Verdara]], Thornmother and Warden of New Roots.\n\n"
        "Banner (visual canon): deep moss-green cloth bearing a pale living root-circle with interwoven roots, overlaps, "
        "irregular thickness, and an incomplete loop. It must feel alive, growing, and interconnected rather than "
        "skeletal. Faction colors are greens, pinks, and purples with organic bioluminescence.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners"),
        ["underground", "nature", "magic"]))
    P.append(_faction(
        "The Mending", "automaton and poppet settlement",
        "The Mending is the combined community of discarded automatons and defective poppets, named for what they do: fix "
        "each other. It is a vast, flat, sprawling cavern, mostly one level, with a wide open workshop floor, large "
        "workshop complexes, barrel-vaulted repair halls, domed structures, cranes, water wheels, and forge areas, in a "
        "fantasy-industrial style that is not steampunk. A Corebound blue glow runs through archways, windows, "
        "lampposts, and embedded panels, and a central spire made from salvaged Corebound technology is the heart and "
        "landmark of the settlement; a softer, warmer poppet corner has colorful tent canopies. Automatons whose bodies "
        "cannot be repaired are honored by having their salvageable parts reused in others, so repaired automatons "
        "often visibly carry mismatched components from many community members, which is culturally accepted and "
        "considered honorable. Poppets are traditional cloth-and-wood dolls with visible repairs, patches, stitches, and "
        "replacement buttons, and should read as beloved repaired toys rather than miniature automatons. The automatons "
        "were built by Liza Herkroft's workshop and dumped in the Underhallow when defective, and every automaton has a "
        "rejection story. Their emotional hooks are being rejected and discarded, and being built to be loved and "
        "thrown away when imperfect.\n\n"
        "Leader: [[Stitch]], First Repaired, with [[Pip]] as Storykeeper.\n\n"
        "Banner (visual canon): sapphire-blue cloth bearing a broken repair-circle surrounding a central node, with "
        "intentionally irregular spacing and repaired segments. It reads as many damaged parts functioning together and "
        "is never a gear, machine diagram, UI symbol, or technological interface.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners"),
        ["underground", "craft", "family"]))
    P.append(_faction(
        "Firstlight", "awakened animal territory",
        "Firstlight is a relatively small underground biome named for the first moment of awareness, and the most "
        "magic-saturated zone in the Underhallow. It is bioluminescent in neon pinks, glowing teals, vivid purples, and "
        "hot magentas, with mutated plant life that is recognizable but wrong in color and scale, giant glowing mushroom "
        "trees with purple flat-caps, blue and purple crystal formations, and waterfalls cascading into glowing teal "
        "pools. The awakened animals live in dens carved into the rock walls with warm golden light and tiny stairs: "
        "there are no formal structures, no market stalls, and no civilization. They are transient animals that "
        "wandered into the magic-saturated zones and were awakened to full sapience, with no shared grievance with the "
        "surface and no community history, which makes them the hardest faction for Ulzerett to motivate. Firstlight "
        "sits between the main settlements and [[Karak's Everhold]] (and [[The Descent]]), and every creature traveling "
        "between the dungeon and "
        "the Underhallow must pass through it, receiving a nudge of critical thinking and comprehension on the way. "
        "Their emotional hook is being suddenly aware and still figuring out what thinking and identity even mean.\n\n"
        "Leader: still to be decided (the bible lists the Firstlight representative as TBD).\n\n"
        "Banner (visual canon): ochre, muted gold, or warm yellow cloth bearing a pale branching awareness mark with a "
        "vertical center and upward-reaching divisions, representing awakening and emerging thought. It is never "
        "wheat, grain, crops, religion, or animal forms. The bible says the sigil is rarely formalized.",
        S("Faction Settlements; Playable Races & Factions; Canon Faction Banners; Leaders TBD"),
        ["underground", "magic", "nature", "mystery"]))

    # ------------------------------------------------------------------ faction leaders
    P.append(_npc(
        "Kraggix Scraptooth", "Chief of Finders Keep", "Goblin",
        "Kraggix Scraptooth is the goblin chief of [[Finders Keep]], a boisterous, proud scavenger leader who lives the "
        "philosophy that everything has value if you can use it. He is loud, theatrical, and deeply proud of his people, "
        "and known for outrageous scrap-built gear and lucky finds.\n\n"
        "Signature look (bible): scrap-built armor, goggles pushed up on the forehead, one piece of recovered Corebound "
        "equipment that he proudly displays, a red cape, and a skull motif.\n\n"
        "From our art chats (not in the bible): in the field-journal sketches he is shown working on a dangerously "
        "improvised contraption that is visibly about to fail while he stays unaware of it.",
        S("Established Faction Leaders"), ["underground", "craft", "treasure"]))
    P.append(_npc(
        "Skritch Stonebender", "Master Mason of the Grand Underhall", "Kobold",
        "Skritch Stonebender is the kobold Master Mason of [[The Grand Underhall]], an energetic, obsessive builder who "
        "treats stonework as art and engineering combined and is constantly working, chiseling, refining, and improving. "
        "He is excitable, passionate, and proud of kobold craftsmanship.\n\n"
        "Signature look (bible): mason's clothes, a blue cloak, a chisel and mallet, and always mid-task on a stone "
        "block.\n\n"
        "From our art chats (not in the bible): small, red-scaled, and silly in the specific way of an obsessive "
        "perfectionist who crouches inches from immaculate stonework to correct a flaw nobody else can see.",
        S("Established Faction Leaders"), ["underground", "craft"]))
    P.append(_npc(
        "Vesk Quickwhisker", "Guildmaster of the Hushwarrens", "Ratfolk",
        "Vesk Quickwhisker is the Warden and Guildmaster of [[The Hushwarrens]], a refined covert broker and infiltrator "
        "who moves between the surface and the Underhallow unseen and maintains networks of routes, secrecy, and "
        "information. Vesk wears practical clothing with subtle status symbols, and is quiet, controlled, and "
        "calculating, respected rather than feared.\n\n"
        "Signature look (bible): climbing a wall at night with the tail wrapped around the handle of a tail blade, in "
        "refined dark muted tones. The Hushwarrens symbol on Vesk's cloak and banner is the visual reference for the "
        "faction banner.",
        S("Established Faction Leaders"), ["underground", "mystery", "trade"]))
    P.append(_npc(
        "Brakka Mossleap", "Elder of Stillwater Hollow", "Grippli",
        "Brakka Mossleap is the Elder of [[Stillwater Hollow]], a calm, contemplative water-shaper who guides the "
        "community through ritual and quiet wisdom and uses water magic to sustain and shape the settlement. Brakka is "
        "serene, patient, and deeply connected to flow and balance.\n\n"
        "Signature look (bible): crouched at the river's edge pulling water from the stream with one hand and holding a "
        "staff with the other, in blue-green robes, with no ears.",
        S("Established Faction Leaders"), ["underground", "nature", "magic"]))
    P.append(_npc(
        "Verdara", "Thornmother of the Quiet Ring", "Arboreal",
        "Verdara is the Thornmother and Warden of New Roots, the female arboreal leader of [[The Quiet Ring]] and the "
        "fiercely protective matriarch of the leshy spirits. She views every leshy spirit as irreplaceable because "
        "leshys cannot naturally replenish their numbers, regards the arboreals as the older siblings and the leshys as "
        "the children, and remembers every leshy's first words, first bloom, first mistakes, and death. When a leshy "
        "dies she adds a living branch to her own body in remembrance. She is patient, not gentle: she will spend "
        "weeks listening and become a weapon in an instant if a leshy is threatened.\n\n"
        "Signature look (bible): a tall, graceful body of living wood, bark, roots, vines, moss, and small flowers, with "
        "a narrow carved-bark face and glowing green eyes, digitigrade root-claw legs, a crown of living antler-like "
        "branches bearing leaves, flowers, and preserved memorial twigs, four additional living branch-limbs, an "
        "emerald heartwood core with drifting spirit-lights, a living bow, and a large living wooden sword. Her visual "
        "theme is shelter: \"Nothing under my protection is expendable.\"",
        S("Established Faction Leaders"), ["underground", "nature", "magic", "family"]))
    P.append(_npc(
        "Stitch", "First Repaired of the Mending", "Automaton",
        "Stitch is the automaton First Repaired and leader of [[The Mending]], leader not by appointment but because "
        "everyone goes to Stitch when something is broken. He was one of the earliest discarded automatons to survive in "
        "the Underhallow, and he is not the strongest, wisest, or most charismatic, but the one who stayed and never "
        "stopped repairing others. He is focused, patient, gentle through action, and quietly authoritative. In "
        "Pathfinder 2E he is an Inventor, and his gear and prosthetics are expressed through a custom innovation that is "
        "built, broken, and rebuilt over time.\n\n"
        "Signature look (bible): a Prototype-model automaton silhouette that is subtly uncanny, slightly too tall and "
        "narrow, with elongated limbs and very long articulated fingers, patched and irregular rather than smooth, and "
        "carrying mismatched limbs and plates from many automaton generations and keepsake parts from former community "
        "members, with a blank faceplate and two glowing blue eyes. His signature gear is the Archive Arm (LOCKED CANON, "
        "replacing the retired Founder's Wrench): an intentionally oversized prosthetic that houses his tools, which must "
        "always appear on the same side in every view. He also has a collapsible shield that folds out of the forearm of "
        "his non-Archive arm. His visual theme is repair: \"Nothing is beyond repair.\"",
        S("Established Faction Leaders"), ["underground", "craft", "family"]))
    P.append(_npc(
        "Pip", "Storykeeper of the Mending", "Poppet",
        "Pip is the poppet Storykeeper of [[The Mending]], the named companion and close counterpart of [[Stitch]], and "
        "represents the poppet half of the community as Stitch represents the automaton half. She is a recurring "
        "character in her own right, not a servant, mascot, or assistant. Pip keeps the community's records: who was "
        "repaired, whose parts were preserved, and the stories behind every repair. She is attentive, practical, busy, "
        "careful, warm, and charmingly fussy.\n\n"
        "Signature look (bible): a traditional cloth-and-wood doll with a stitched fabric head, visible seams, patched "
        "limbs, button or bead eyes, a small muted blue scarf or sash, and a satchel of ledgers and repair notes. She "
        "must read as a traditional doll, never as a miniature automaton: no enamel-coated metal plating and no "
        "glowing automaton eyes. Together Stitch and Pip embody \"Repair and Remembrance.\"",
        S("Established Faction Leaders"), ["underground", "mystery", "family"]))

    # ------------------------------------------------------------------ the royal court
    P.append(_npc(
        "Urist Eremor", "Grand Lord of Hallowmead", "Human",
        "Urist Eremor is the Grand Lord of [[Hallowmead]], a human in his mid-fifties with dark hair, two distinct gray "
        "streaks, and blue eyes. He inherited rule by bloodline, not merit, and is arrogant and self-centered. He plays "
        "an ignorant facade for the masses while his eyes belie it, publicly maintains traditions and customs, and "
        "presents an image of strength, stability, and generosity. He lets Malcior Veyndor's raids and kidnappings "
        "continue to keep the Lord Sage quiet, and sees Liza Herkroft as a useful toolmaker and nothing more.",
        S("The Royal Court"), ["politics", "military"]))
    P.append(_npc(
        "Orion Palend", "Lord Commander of Hallowmead", "Human",
        "Orion Palend is the Lord Commander of Hallowmead's militia, a human in appearance, in his mid-fifties and a "
        "little older than Urist, with a moderate soldier's build. He is publicly feared for bold leadership and "
        "unbreakable resolve and known for daring tactics and unwavering discipline. Everyone knows that he does not "
        "age or die: a Seer told him he was \"cursed with life until a destined moment,\" and the curse framing shuts "
        "down curiosity, so people pity, revere, and fear him rather than question how it works. He has no scars, and "
        "keeps his own visibly battered, personally repaired armor and weapons. He organizes expeditions into the "
        "Underhallow at the request of the Lord Sage and the order of the Grand Lord, and he is the likely leader of "
        "the force that arrives in Phase 2.\n\n"
        "GM ONLY: Orion is an Immortal, unknown to everyone but himself, and has been in this world for thousands of "
        "years, far longer than Ulzerett. His recklessness comes from exhaustion as much as bravery, and part of him "
        "tests whether each fight is the destined moment. Orion and Ulzerett are not aware of each other, and Orion's "
        "specific mission is TBD.",
        S("The Royal Court; Campaign Structure"), ["politics", "military", "mystery"]))
    P.append(_npc(
        "Liza Herkroft", "Lady Artificer of Hallowmead", "Elf",
        "Liza Herkroft is Hallowmead's Lady Artificer, an adult elf with a muscular but feminine build from working heavy "
        "tools daily, usually in craftsman clothing with grease on her hands and cheek. She is a publicly respected "
        "engineer and innovator known for diligence, skill, and practical solutions, always working in her workshop, "
        "which also produces poppets as toys for children. She creates the city's automatons and arms: the military uses "
        "Corebound weapons derived from her work, while the City Guard uses light civic Corebound-style armor but "
        "ordinary weapons. She does not consider her automatons or poppets to be alive, and does not consider the "
        "technology magical, but an engineered material and energy system she is learning to control. She is quietly "
        "confident that the Underhallow expeditions uncovered something not natural to the world, and keeps that to "
        "herself. Her personal maker's mark (LOCKED CANON) is a tall vertical symbol of a single continuous knot with "
        "matching upper and lower loops and a detached almond-shaped eye, hidden where only another craftsperson would "
        "look.\n\n"
        "GM ONLY: Liza does not know about the Immortals. The technology she recovered from an underground tomb is the "
        "only thing that can permanently kill an Immortal, which makes her unknowingly the most important person in "
        "the setting. The phrase \"Immortal tech\" is GM-facing only and must never appear in public-facing or in-world "
        "text; publicly it is Corebound equipment.",
        S("The Royal Court; Core Lore: The Immortals; Liza Herkroft Personal Maker's Mark"),
        ["craft", "politics", "magic"]))
    P.append(_npc(
        "Malcior Veyndor", "Lord Sage of Hallowmead", "Human",
        "Malcior Veyndor is the Lord Sage, a human who looks to be in his seventies though his voice is that of a man "
        "in his thirties. He is publicly the advisor on history, law, and the arcane, keeper of the city's archives, "
        "and the voice of wisdom, pictured as a kindly scholar among books, candlelight, quill, and parchment. He "
        "counsels the Grand Lord on matters seen and unseen, and is distrustful of Liza.\n\n"
        "GM ONLY: Malcior is secretly a necromancer who practices deep within the city bordering on the Underhallow, and "
        "is responsible for the raids and kidnappings that Urist allows. He believes Urist is leading his people blindly "
        "into oblivion and that Liza has uncovered a new form of magic she refuses to discuss. If he ever learned about "
        "Immortal regeneration he would do anything to obtain it.",
        S("The Royal Court"), ["politics", "magic", "mystery"], avoid=["undead"]))
    P.append(_npc(
        "Ulzerett", "Hidden Blue Dragon Immortal", "Dragon",
        "GM ONLY. Ulzerett is a Blue Dragon Immortal with sapphire and steel-blue scales, electric azure veins, and "
        "stormlight eyes, roughly 50 to 60 feet long in dragon form. In his humanoid dragonborn form he is tall and "
        "draconic in practical traveler's clothes (a dark charcoal cloak and brown leather), and looks like a leader, "
        "not a villain or a saint. He has been in this world a few hundred years, arrived with a team of Immortals whom "
        "he tricked and sealed in his ambition, and has a deep scar on his left shoulder inflicted by Immortal-derived "
        "technology that never fully healed. He is quietly building the Underhallow alliance to overthrow Hallowmead and "
        "frames it as liberation, but his true motives are hidden even from the player characters, and the specific "
        "reason beyond ambition is TBD.\n\n"
        "Constraints: he is one being, and if knocked unconscious he could be sealed forever. Hallowmead's military "
        "carries Corebound weapons that can permanently kill him, he cannot enter Hallowmead himself, and so he sends "
        "the player characters. He needs Liza either turned, controlled, or removed, because everything she deciphers "
        "is a potential death sentence for him.\n\n"
        "His Underhallow persona (a canon decision made after the bible's July 2026 edition): a single persona, a "
        "dwarven field historian, mechanically a Magus with the Archaeologist archetype. The persona's name has not "
        "been set. The bible's list of seven separate disguised advisers (Khazuk, Skritch Foretalon, Vesk Dourrunner, "
        "Jorun Deepcurrent, Elder Verdantroot, Unit Z-17 \"Patch,\" and Greywing) predates that decision and should be "
        "treated as superseded; update the bible when you next edit it. Either way the persona is separate from the "
        "real faction leaders, who do not know.",
        S("Ulzerett; Core Lore: The Immortals") + "; persona decision from our chats (2026-07-24)",
        ["gm-only", "mystery", "politics"], canon="ESTABLISHED"))

    # ------------------------------------------------------------------ places
    P.append(_place(
        "Hallowmead", "surface city",
        "Hallowmead is a wealthy, orderly, prosperous, well-governed surface city that is hierarchical and authoritarian "
        "beneath the polish. It is ruled by [[Urist Eremor]], with [[Orion Palend]] commanding the militia, [[Liza "
        "Herkroft]] building its arms and automatons, and [[Malcior Veyndor]] advising on history and the arcane. Its "
        "colors are crimson and gold. Its buildings are cream-colored stone with sparse clean seams, red tiled roofs, and "
        "arched windows and doors, along clean cobblestone streets with controlled civic greenery, and it is not "
        "steampunk, industrial Victorian, or whimsical. Its people are the standard surface peoples (humans, elves, "
        "dwarves, halflings, gnomes, aasimar, tieflings, orcs), and Underhallow peoples are not shown in ordinary "
        "surface crowd scenes. It treats the Underhallow's inhabitants as pests, raids and extracts resources from "
        "beneath it, and erases their culture, and everything it throws away falls down the refuse chutes to Finders "
        "Keep. Its official sigil (LOCKED CANON) is a gold circular emblem containing a vertically symmetrical "
        "multi-spired fortress on crimson, and its civic banner (LOCKED CANON, Variant H) shows crimson cloth, a gold "
        "ring, and a gold fortress whose dominant central tower extends above the top of the ring.",
        S("The Surface: Hallowmead; The Royal Court; Visual Style Guide"),
        ["politics", "military", "trade"], ["near", "just outside", "beneath"]))
    P.append(_place(
        "The Underhallow", "region",
        "The Underhallow is a vast underground network of tunnels, caverns, and chambers beneath Hallowmead, home to the "
        "downtrodden and discarded. Some areas are miles apart, so traveling between settlements is a real journey, and "
        "the kobolds built and maintain the infrastructure connecting everything. Its seven factions are [[Finders "
        "Keep]], [[The Grand Underhall]], [[The Hushwarrens]], [[Stillwater Hollow]], [[The Quiet Ring]], [[The "
        "Mending]], and [[Firstlight]], who meet at [[The Crossings]]. It is caught between three forces working "
        "through deception, and the first phase of the campaign is light, scrappy, and whimsical, building camaraderie "
        "between factions that do not naturally trust one another.\n\n"
        "Routes (bible connection graph): the Hushwarrens link to Finders Keep and the Grand Underhall, and Finders Keep "
        "links to the Grand Underhall and Stillwater Hollow. The Grand Underhall, the Mending, and Stillwater Hollow "
        "each link to the Crossings, Stillwater Hollow also links to the Quiet Ring, and the Quiet Ring and the "
        "Crossings both link to Firstlight. Firstlight is the only way to [[Karak's Everhold]] or [[The Descent]]. The "
        "surface's only connection is Orion's Ingress, down to [[Crown's Post]].\n\n"
        "Points of interest: Waystone Nook (between the Glimmer and the Mending), Echo Junction (on the path from "
        "Firstlight to Karak's Everhold), Old Miner's Rest (between the Quiet Ring and Firstlight), Lost Cart Passage (a "
        "long-abandoned mining route with broken carts still in place), and the Breathing Deep.",
        S("The Underhallow: Geography & Locations"), ["underground"], ["somewhere in", "deep in", "in"]))
    P.append(_place(
        "The Crossings", "common market and gathering space",
        "The Crossings is where all factions meet and the heart of the Underhallow: a massive open central plaza with a "
        "crystal spire landmark, where every faction has brought a piece of its home. There are goblin scrap stalls with "
        "skull banners and smoke, kobold stonework throughout, bioluminescent mushrooms and a living tree from the Quiet "
        "Ring, the blue Corebound glow of the Mending, colorful poppet market areas, and water features from "
        "Stillwater. Faction banners mark territory and trade areas, and tunnel entrances around the edges lead to each "
        "settlement.\n\n"
        "The proposed annual events in this Notebook are set here.",
        S("Faction Settlements: The Crossings"), ["underground", "trade", "festival", "politics"],
        ["at", "at", "near", "just outside"]))
    P.append(_place(
        "Orion's Ingress", "surface entry point",
        "Orion's Ingress is the primary entry point for Hallowmead military expeditions into the Underhallow. It sits on "
        "the surface, touching it directly, with a massive crane and lift system that lowers troops and supplies down. "
        "It is isolated from all faction settlements and has a single connection down to [[Crown's Post]].",
        S("Surface-Controlled Areas"), ["military", "politics"], ["at", "near", "just outside"]))
    P.append(_place(
        "Crown's Post", "Hallowmead military outpost",
        "Crown's Post is Hallowmead's underground military fortress and maintenance outpost, built and maintained by the "
        "military in robust, formal stonework, with banners showing the official sigil, a gold tower on crimson. The "
        "Underhallow's residents use the name for the surface occupation, with some contempt. It has a central, elevated "
        "Command Hall, a training yard, barracks, a gatehouse and bottleneck chokepoints, watch posts, staging caves, "
        "refining works and ore processing for minerals from [[The Glimmer]], supplies and an armory, and storage "
        "vaults. It connects upward to [[Orion's Ingress]] and outward to The Glimmer and the [[Ancient Ruins]].",
        S("Surface-Controlled Areas: Crown's Post"), ["military", "politics", "trade"],
        ["at", "near", "just outside"]))
    P.append(_place(
        "The Glimmer", "crystal caverns",
        "The Glimmer is a massive crystal cavern with purple and violet crystals erupting from the walls and ceiling, "
        "heavily guarded and mined by Hallowmead as the source of raw minerals for the refining works at [[Crown's "
        "Post]]. The bible's connection graph also links it to the Mending through Waystone Nook, while the Glimmer's own "
        "entry says it connects only to Crown's Post; the bible flags this as unresolved.",
        S("Surface-Controlled Areas: The Glimmer; Editorial Consistency Checks"), ["military", "trade", "magic"],
        ["near", "in", "just outside"]))
    P.append(_place(
        "Ancient Ruins", "restricted ruins",
        "The Ancient Ruins are a restricted site reached through [[Crown's Post]], where the surface controls access. "
        "Liza Herkroft's expeditions recovered the technology there that she has been studying and building into "
        "Corebound equipment.\n\n"
        "GM ONLY: it is an Immortal tomb and technology site.",
        S("Surface-Controlled Areas: Ancient Ruins"), ["ruin", "military", "mystery"],
        ["near", "just outside"], the=True))
    P.append(_place(
        "Karak's Everhold", "abandoned dwarven dungeon",
        "Karak's Everhold is an abandoned dwarven dungeon at the far end of the Underhallow, reached on foot only through "
        "[[Firstlight]]. It predates Hallowmead. The dwarves dug too deep and broke through into areas of [[The "
        "Descent]], and a battle lasting roughly a generation followed, until the younger dwarves decided constant "
        "conflict was not worth it and left with their valuables. The elders extracted a vow that they would return one "
        "day to reclaim it, which could happen at any time but is not a primary plot point. Abandoned dwarven "
        "architecture, traps, and infrastructure remain, inhabited by dungeon creatures, some of which crawl up through "
        "the breach from the Descent. The most common creatures to pass through Firstlight and be uplifted are mimics, "
        "slimes, and doppelgangers. If the dwarves return they will find the Underhallow's factions depending on spaces "
        "near their old territory, which poses a moral dilemma: do the downtrodden, who know displacement, displace "
        "someone else?",
        S("Karak's Everhold; Uplifted Dungeon Creatures"), ["ruin", "monster", "treasure", "underground"],
        ["in", "at", "deep in"]))
    P.append(_place(
        "The Descent", "passage to the deep",
        "The Descent is the deepest known passage leading further underground, where an aboleth or similar aberration "
        "lurks, the thing the grippli fled from. It connects to [[Firstlight]] and, through the dwarven breach, to "
        "[[Karak's Everhold]]. No one goes there willingly, and its color identity is dark, deep, and oppressive.",
        S("Faction Settlements: The Descent; Three-Layer Threat Structure"), ["monster", "mystery", "underground"],
        ["near", "at the edge of"]))

    # ------------------------------------------------------------------ proposed annual events and a quest
    note = "PROPOSED, not yet canon, and not in the setting bible. "
    P.append(_page(
        "Event", "The Great Reclamation",
        note + "Once each year the refuse flow from above reaches its peak after a major surface festival. The goblins "
        "of [[Finders Keep]] treat the occasion as a harvest festival, a sporting event, and a religious holiday at "
        "once, and the haul can be large enough to affect trade across the Underhallow for months. Contests include "
        "fastest salvage crew, most valuable discovery, strangest discovery, best rebuilt invention, and a What Is "
        "This Thing? competition in which contestants try to identify objects nobody understands.\n\n"
        "The draft recommended canonizing this one first.",
        "PROPOSED", CHATS + " (annual events brainstorm, 2026-09-25)", status="upcoming",
        tags=["festival", "trade", "treasure", "underground"], when="once a year, after a major surface festival"))
    P.append(_page(
        "Event", "Founders' Day",
        note + "Possibly the most important holiday in the Underhallow. It honors the kobolds of [[The Grand "
        "Underhall]] who built the tunnel network, and the idea that communities must build things together if they "
        "intend to survive underground.",
        "PROPOSED", CHATS + " (annual events brainstorm; the draft text was cut off)", status="upcoming",
        tags=["festival", "craft", "family", "underground"], when="once a year"))
    P.append(_page(
        "Event", "The Underhallow Concord",
        note + "The largest annual gathering, held at [[The Crossings]], where every settlement sends "
        "representatives. Its public purpose is celebration, trade, and friendly competition; its quiet purpose is "
        "maintaining the fragile relationships that keep the Underhallow working. The Concord is the one time each "
        "year when grudges are supposed to be set aside, and its main attraction is the Sevenfold Challenge, a "
        "friendly competition built so that no faction dominates every category, including the Great Recovery, a "
        "scavenger hunt through abandoned tunnels.\n\n"
        "The draft's hook: every faction traditionally sends one champion, but this year a mixed-faction team is "
        "being tried, and the player characters are the experiment.",
        "PROPOSED", CHATS + " (annual events brainstorm, 2026-09-25)", status="upcoming",
        tags=["festival", "politics", "trade", "underground"], when="once a year, at the Crossings"))
    P.append(_page(
        "Event", "The Great Burden",
        note + "An annual period in which the whole Underhallow works together on maintenance it cannot survive "
        "without: tunnels collapse, waterways shift, bridges rot, fungal infestations spread, crystal growth blocks "
        "roads, ancient dwarven structures become unstable, and monster incursions increase near remote passages. It "
        "is part maintenance project, part trade summit, part social event. If a faction refuses to take part, "
        "everyone remembers. [[Finders Keep]] brings salvage crews and materials, and [[The Mending]] serves as the "
        "primary repair corps, with [[Stitch]] overseeing major efforts and [[Pip]] documenting completed work.\n\n"
        "This overlaps with the Concord and the Festival of Found Things; the drafts were alternatives.",
        "PROPOSED", CHATS + " (annual events brainstorm, 2026-09-25)", status="upcoming",
        tags=["festival", "craft", "politics", "underground"], when="once a year"))
    P.append(_page(
        "Event", "The Festival of Found Things",
        note + "An annual celebration of the idea that nothing discarded is worthless. Its origin is that every "
        "faction survived because somebody shared something they could have kept: goblins shared salvage, kobolds "
        "shared tunnels, grippli shared water, ratfolk shared information, leshys shared food and shelter, "
        "automatons shared repairs, and awakened animals shared discoveries. Every faction enters a team, built so "
        "that crafters, scouts, traders, performers, and problem-solvers can all contribute.\n\n"
        "This overlaps with the Concord and the Great Burden; the drafts were alternatives.",
        "PROPOSED", CHATS + " (annual events brainstorm, 2026-09-25)", status="upcoming",
        tags=["festival", "family", "trade", "underground"], when="once a year"))
    P.append(_page(
        "Quest", "The King's Turnip",
        note + "Every year the settlements compete for the title of Finest Crop in the Underhallow. The entry from "
        "[[The Quiet Ring]], a gigantic bioluminescent root vegetable called The King, walks off on its own. Roots "
        "still connect it to the earth, and tracks show it slowly dragged itself into a forgotten section of tunnels "
        "beneath [[The Crossings]]. Root leshys accidentally awakened it with experimental magic, and now it thinks "
        "it is escaping execution. The search is absurd and escalating, nobody is trying to kill anyone, and the "
        "festival is falling apart around the mystery. Players can solve it through roleplay, tracking, or "
        "encounters with tunnel wildlife.",
        "PROPOSED", CHATS + " (introductory quest brainstorm, 2026-09-25)", status="rumored",
        tags=["nature", "mystery", "festival", "underground"]))

    # ------------------------------------------------------------------ notes
    P.append(_page(
        "Note", "Corebound equipment (public face)",
        "Corebound equipment is the public, in-world name for the technology Liza Herkroft recovered, and the word "
        "\"Immortal\" is not associated with it by the public, the court, the military, or the Underhallow factions. "
        "Avoid calling it \"Immortal tech\" in public-facing notes, dialogue, or art prompts. Its material identity is "
        "LOCKED CANON: dark iron or steel framework and plates with a smooth matte warm-white, porcelain-like painted or "
        "enameled finish (warm, not sterile blue-white), a deep sapphire or electric-blue glow from internal cores, "
        "veins, seams, or nodes, and plates that dent, bend, or shear like metal rather than shattering like pottery. It "
        "should read as fantasy-first, ancient and advanced at once, slightly wrong in proportion, clean and minimal, and "
        "never steampunk, circuitry, brass, or pipes.\n\n"
        "Distribution: the military is the primary user of Corebound weapons and equipment, the City Guard uses light "
        "civic Corebound-style armor but ordinary non-Corebound weapons (spear, short sword, wooden round shield, light "
        "crossbow), and the public sees automatons and poppets as useful constructs or toys. Automaton faces are smooth "
        "warm-white enamel-coated metal with only two simple glowing blue eyes, and no nose, mouth, lips, cheek lines, "
        "or expression.",
        "ESTABLISHED", S("Corebound Equipment; The Surface: Hallowmead (Automatons on the Surface)"),
        tags=["craft", "magic"]))
    P.append(_page(
        "Note", "The Immortals (GM only)",
        "GM ONLY. The Immortals come from a coalition in a different reality, which in its far future developed a "
        "technology with broad uses that, applied with specific techniques, can create nigh-immortal beings. The "
        "coalition shared it among its members to find other planes, times, and realities to pilfer resources. Only "
        "weapons made from Immortal-derived technology can cause permanent damage to an Immortal. All other damage, "
        "including unconsciousness, dismemberment, and beheading, triggers regeneration over hours to days while the "
        "Immortal is comatose, and on waking it is as if they were never injured. An Immortal rendered unconscious by "
        "conventional means can be sealed, bound, or trapped indefinitely, but not killed.\n\n"
        "The consequence: Liza Herkroft's Corebound weapons, used mainly by Hallowmead's military, are the only things in "
        "this world that can permanently kill an Immortal, and neither Liza nor the military knows it. Ulzerett "
        "understands enough to see the military as a direct existential threat. Known Immortals are [[Ulzerett]] and "
        "[[Orion Palend]], who are not aware of each other.",
        "ESTABLISHED", S("Core Lore: The Immortals"), tags=["gm-only", "magic", "mystery"]))
    P.append(_page(
        "Note", "Campaign structure and threats (GM only)",
        "GM ONLY. Phase 1, Small-Time Troublemakers: the player characters start in the Underhallow, each belonging to a "
        "faction, on silly quests and low-stakes sabotage missions. There is no penalty for being overt; they are "
        "supposed to be noticed. The tone is light and fun, and they unknowingly escalate surface tensions exactly as "
        "Ulzerett intends. Phase 2, The Hammer Falls: their success provokes Hallowmead into sending a large raiding "
        "force, likely led by Orion Palend, the tone shifts hard, and Ulzerett uses shapeshifting to appear to each "
        "faction and convince them to unite. Phase 3, The Revolution: a united front pushes back and takes the fight to "
        "the surface, and Ulzerett gets what he actually wants, which is the military dismantled or scattered, Liza's "
        "technology disrupted or captured, and himself installed as the invisible power behind the new order.\n\n"
        "Three threats work through deception and no faction is fully aware of any of them. From above, Hallowmead "
        "raids, erases culture, and extracts resources from Crown's Post, armed with weapons that can kill Immortals "
        "without knowing it. From within, Ulzerett uses shapeshifting disguises and the downtrodden as shield and "
        "tool. From below, the Descent sends doppelganger sleeper agents who do not know what they are, and creatures "
        "crawl up through Karak's Everhold under the direction of an unknown intelligence.",
        "ESTABLISHED", S("Campaign Structure; Three-Layer Threat Structure"), tags=["gm-only", "politics", "mystery"]))
    P.append(_page(
        "Note", "Open questions (TBD)",
        "These are unresolved in the bible, and nothing here is invented to answer them. Core narrative: Ulzerett's "
        "motivation beyond wanting to rule, Orion's specific mission and how the two purposes intertwine, the identity "
        "and current status of the Seer who told Orion he was cursed with life, the source of the Underhallow's "
        "magic-saturated zones, details on the other sealed Immortals, and the original purpose of the druidic circle "
        "that created the leshys. The Descent: the controlling intelligence (an aboleth, a sealed Immortal connection, or "
        "something older), how many doppelganger sleeper agents are embedded, and what triggers their activation. "
        "Karak's Everhold: the dwarven clan's current location and status. Campaign: post-revolution direction and "
        "faction-specific Phase 1 quest ideas. Art: the Firstlight awakened-animal leader.\n\n"
        "The bible's editorial checks flag two more: whether the Glimmer connects to the Mending, and the Firstlight "
        "leader.",
        "TBD", S("Open Questions / TBD; Editorial Consistency Checks"), tags=["mystery"]))
    P.append(_page(
        "Note", "Hallowmead setting import notes",
        "These pages were written from the master setting bible, and each names the section it came from. Pages marked "
        "PROPOSED came from our chats and are not in the bible: the five annual events (they overlap, because the drafts "
        "were alternatives) and the King's Turnip quest. A few art-direction details from our chats are marked as such on "
        "the leader pages.\n\n"
        "Information boundary: pages tagged gm-only (Ulzerett, The Immortals, Campaign structure and threats) are never "
        "used by Story Forge. The Royal Court pages carry secrets in their text, but generated stories only ever use a "
        "page's name and title, and each secret page lists the themes it must never meet (Malcior never meets undead "
        "events).\n\n"
        "One conflict for you to resolve: the bible's July 2026 edition lists seven separate disguised advisers for "
        "Ulzerett, but a later decision made it a single dwarven field historian persona. The Ulzerett page follows the "
        "later decision.\n\n"
        "Left out on purpose: the visual-art rules, the prompt library, and the playable-ancestry restrictions (automatons "
        "Small only, poppets and awakened animals with approval, uplifted mimics, slimes, and doppelgangers with approval), "
        "which belong in your bible rather than a Notebook page.",
        "ESTABLISHED", "Import summary", tags=["underground"]))
    return P


# ---------------------------------------------------------------------------------------------- loading
def _by_title(pages):
    return {str(p.get("title", "")).strip().lower(): p for p in pages}


RENAMED = {"urist": "Urist Eremor", "brakka": "Brakka Mossleap"}        # titles used by the first version of this import


def _edited(page):
    h = page.get("seed_hash")
    return bool(h) and body_hash(page.get("body", "")) != h


def plan(notebook, current_weights=None):
    """What loading would do, without changing anything."""
    have = _by_title(notebook)
    new, updates, edited, current = [], [], [], []
    for np_ in build_pages():
        key = np_["title"].lower()
        old = have.get(key)
        if old is None:
            old_title = next((o for o, n in RENAMED.items() if n.lower() == key and o in have), None)
            old = have.get(old_title) if old_title else None
        if old is None:
            new.append(np_)
        elif old.get("seed") != SEED:
            current.append(np_["title"])                  # a page of yours with this title: never touched
        elif old.get("rev", 1) >= REV:
            current.append(np_["title"])
        elif _edited(old):
            edited.append(np_["title"])
        else:
            updates.append(np_["title"])
    by_type = {}
    for p in new:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
    cur = {k: float(v) for k, v in (current_weights or {}).items()}
    mine = bool(cur) and cur != {k: float(v) for k, v in V1_DEMOGRAPHICS.items()}
    return {"new_pages": new, "updates": updates, "edited": edited, "skipped": current, "by_type": by_type,
            "set_demographics": (not cur) or cur == {k: float(v) for k, v in V1_DEMOGRAPHICS.items()},
            "differs": mine and cur != {k: float(v) for k, v in DEMOGRAPHICS.items()}}


def _rename_links(notebook, old, new):
    from . import notebook as nbk
    pat = re.compile(r"\[\[" + re.escape(old) + r"(\|[^\]]+)?\]\]", re.IGNORECASE)
    for p in notebook:
        p["body"] = pat.sub(lambda m: f"[[{new}{m.group(1) or ''}]]", p.get("body") or "")
    return nbk


def apply(notebook, config, replace_demographics=False):
    """Add missing Hallowmead pages to `notebook` (a list, changed in place), bring unedited pages from an earlier import
    up to date, and set the ancestry mix in `config`. Pages you edited and pages of your own are never changed.

    Updated pages keep their id, status, reputation, goals, and rivals, so links and standing survive. The ancestry mix is
    set when it is empty or is the one the first import chose; otherwise it is kept unless replace_demographics is true.
    Returns a report dict."""
    current = config.get("ancestry_weights") or {}
    p = plan(notebook, current)
    have = _by_title(notebook)
    updated = []
    for np_ in build_pages():
        key = np_["title"].lower()
        if np_["title"] in p["updates"]:
            old = have.get(key)
            if old is None:
                old_title = next(o for o, n in RENAMED.items() if n.lower() == key)
                old = have[old_title]
                _rename_links(notebook, old["title"], np_["title"])
                old["title"] = np_["title"]
            keep = {k: old[k] for k in ("id", "status", "created") if k in old}
            if old.get("type") == "Faction":
                keep["rep"] = old.get("rep") or np_.get("rep")
                keep["goals"] = old.get("goals") or np_.get("goals", [])
                keep["rivals"] = old.get("rivals") or np_.get("rivals", [])
            for k in [k for k in old if k not in ("id", "title")]:
                if k not in ("status", "created", "rep", "goals", "rivals", "pc", "pathbuilder_id", "story"):
                    del old[k]
            old.update({k: v for k, v in np_.items() if k not in ("id", "title", "status", "created", "rep", "goals", "rivals")})
            old.update(keep)
            updated.append(np_["title"])
    notebook.extend(p["new_pages"])
    demo = "kept"
    if p["set_demographics"] or replace_demographics:
        demo = "set" if not current else "replaced"
        config["ancestry_weights"] = {k: float(v) for k, v in DEMOGRAPHICS.items()}
    config.update(hallowmead_loaded=True, hallowmead_offered=True, hallowmead_pack=True, hallowmead_rev=REV)
    return {"added": [x["title"] for x in p["new_pages"]], "updated": updated, "edited": p["edited"],
            "by_type": p["by_type"], "skipped": p["skipped"], "demographics": demo}


# ---------------------------------------------------------------------------------------------- story content
# Entries for Story Forge tables, in the same "text | tags | weight | needs | not" form as storydata.py. Every line is
# limited to the "hallowmead" content pack (p:hallowmead), so the Story tab's Hallowmead checkbox turns them all off at
# once. They draw on the bible's places and emotional hooks, and stay neutral about which faction the subject belongs to,
# because Who is rolled separately.
TABLE_ADDITIONS = {
    "occupation": """
salvage crew boss|trade craft treasure underground p:hallowmead|2
refuse sorter|trade craft underground p:hallowmead|2
scrap tinkerer|craft treasure underground p:hallowmead|2
tunnel mason|craft underground p:hallowmead|2
arch inspector|craft politics underground p:hallowmead|1.5
mine-cart rail keeper|craft trade underground p:hallowmead|1.5
sign painter|craft festival underground p:hallowmead t:light|1
route runner|trade mystery underground p:hallowmead|2
record keeper|mystery trade underground p:hallowmead|1.5
surface infiltrator|crime mystery underground p:hallowmead|1.5
waterway warden|nature craft underground p:hallowmead|2
sluice keeper|nature craft underground p:hallowmead|1.5
root gardener|nature craft underground p:hallowmead|2
fungus farmer|nature trade underground p:hallowmead|2
herb healer|nature disease underground p:hallowmead|2
mender|craft family underground p:hallowmead|2
storykeeper|mystery family underground p:hallowmead|1.5
lift tender|craft underground p:hallowmead|1.5
frontier scout|nature mystery underground p:hallowmead|1.5
crystal gatherer|magic treasure underground p:hallowmead|1.5
""",
    "where.underground": """
at the Crossings, beneath the crystal spire|trade politics festival underground p:hallowmead|4
in the salvage yards of Finders Keep, under the refuse chutes|trade craft treasure underground p:hallowmead|2
along a tunnel arch the Grand Underhall keeps spotless|craft underground p:hallowmead|2
in the sewer-level corridors near the Hushwarrens|mystery crime underground p:hallowmead|2
on a stilt platform at Stillwater Hollow|nature craft underground p:hallowmead|2
in the glow-lit root halls of the Quiet Ring|nature magic underground p:hallowmead|2
in a Mending workshop crowded with half-repaired tools|craft family underground p:hallowmead|2
beside the glowing teal pools of Firstlight|magic nature mystery underground p:hallowmead|2
at Waystone Nook, on the way to the Mending|road craft underground p:hallowmead|1.5
at Echo Junction, on the path toward Karak's Everhold|mystery monster underground p:hallowmead|1.5
at Old Miner's Rest, between the Quiet Ring and Firstlight|road nature underground p:hallowmead|1.5
along the Lost Cart Passage, where the broken carts still sit|road ruin mystery underground p:hallowmead|1.5
in the shadow of Crown's Post, where Hallowmead's banners hang|military politics underground p:hallowmead|1.5
in the empty halls of Karak's Everhold|ruin monster treasure underground p:hallowmead|1.5
""",
    "what.trade": """
{has} been trading salvage for repairs, and both sides think they got the better deal|trade craft underground p:hallowmead t:light
{has} cornered the market on a whole refuse chute's worth of lamp glass|trade treasure underground p:hallowmead
""",
    "what.craft": """
{has} rebuilt something from Hallowmead's refuse that nobody can name, and it hums|craft treasure mystery underground p:hallowmead t:light
{has} insisted that a tunnel arch needs one more adjustment, and will not say what is wrong with it|craft underground p:hallowmead t:light
{has} repaired a tool so well that its owner now suspects it is a different tool|craft underground p:hallowmead t:light
{has} handed a salvaged part to a repairer, and made sure everyone knew whose it was|craft family underground p:hallowmead
""",
    "what.mystery": """
{has} been seeing a pale mark on walls that nobody in the Hushwarrens will admit to making|mystery underground p:hallowmead
{has} found a message chalked in a style no ratfolk will claim|mystery underground p:hallowmead
""",
    "what.nature": """
{has} noticed a new gap in the root circle of the Quiet Ring, and nobody planted it|nature mystery underground p:hallowmead
{has} found that a pool in the waterways has started to run the wrong way|nature mystery underground p:hallowmead
""",
    "what.magic": """
{has} brought back something from Firstlight that glows whenever an awakened animal looks at it|magic mystery underground p:hallowmead
""",
    "what.politics": """
{has} learned where Hallowmead's next raid will land, and is trying to decide whom to tell|politics military underground p:hallowmead t:grim
""",
    "what.military": """
{has} seen a lift at Orion's Ingress lowering more troops than the usual patrol|military politics underground p:hallowmead t:grim
{has} been watching Crown's Post, and counting the carts that go in and out|military mystery underground p:hallowmead
""",
    "what.family": """
{has} been reunited at the Crossings with kin from another settlement after years apart|family festival underground p:hallowmead t:light
""",
    "what.festival": """
{has} entered a team in the festival made of one member from every kind of Underhallow folk, and nobody agrees who is in charge|festival politics underground p:hallowmead t:light
""",
    "what.creature": """
{has} wandered up from Karak's Everhold and past Firstlight, and now asks very thoughtful questions|monster mystery underground p:hallowmead t:light
""",
    "rumor.source": """
a goblin salvage runner with something to sell|trade underground p:hallowmead
a Hushwarrens courier who was not supposed to be seen|mystery underground p:hallowmead
a kobold mason, checking the same arch for the third time|craft underground p:hallowmead t:light
a grippli waterway warden, leaning on a sluice gate|nature underground p:hallowmead
a poppet storykeeper who remembers everything|mystery family underground p:hallowmead
an awakened mouse who heard it from a friend who heard it from the wall|underground p:hallowmead t:light
a root leshy tending the fungus beds, who hears things from the soil|nature underground p:hallowmead t:light
a sign in childlike handwriting that someone corrected overnight|craft underground p:hallowmead t:light
""",
    "task": """
{v:want} a lost shipment of salvage found before it is sold twice|trade treasure underground p:hallowmead
{v:need} a tunnel arch inspected and passed by someone the kobolds will accept|craft politics underground p:hallowmead t:light
{v:ask} for a message carried across three settlements without anyone reading it|mystery trade underground p:hallowmead
{v:need} a failing sluice repaired before the water finds a new path|nature craft underground p:hallowmead
{v:want} a rare crystal fetched from near the Glimmer without Hallowmead's guards noticing|magic treasure military underground p:hallowmead
{v:need} a festival team assembled with one member from every settlement, and no one will volunteer|festival politics underground p:hallowmead t:light
{v:ask} for an old mine route cleared of the carts that were left behind|ruin craft underground p:hallowmead
""",
    "fm.action": """
{is} sending salvage crews to a new refuse chute|trade underground p:hallowmead
{is} quietly rerouting couriers away from the Crossings|mystery trade underground p:hallowmead
{has} announced a new tunnel inspection schedule, and everyone dreads it|craft politics underground p:hallowmead t:light
{is} recruiting for the festival team, and promising more than it can deliver|festival politics underground p:hallowmead t:light
""",
    "omen.who": """
the refuse chutes|trade underground pl p:hallowmead
the crystal spire at the Crossings|festival magic underground p:hallowmead
the root circle of the Quiet Ring|nature magic underground p:hallowmead
the waterways of Stillwater Hollow|nature underground pl p:hallowmead
the glow at the edge of Firstlight|magic nature underground p:hallowmead
the blue glow of the Mending's central spire|craft magic underground p:hallowmead
""",
    "npc.bond": """
has kin in another Underhallow settlement and writes to them through Hushwarrens couriers|underground p:hallowmead
owes the Mending a favor for a repair that saved something dear|craft family underground p:hallowmead
once carried salvage for Finders Keep and still has opinions about the pay|trade underground p:hallowmead
carries a part from a friend the Mending could not save|craft family underground p:hallowmead
""",
    "npc.backstory": """
was born in the Underhallow and has never seen the surface|underground p:hallowmead
climbed to the surface for a day and came back with a story nobody believed|mystery underground p:hallowmead
was raised by whoever reached them first after Hallowmead threw them away|family underground p:hallowmead
grew up hearing that the ratfolk were blamed for a plague they did not cause|underground p:hallowmead
followed the water down with the grippli and remembers what lay deeper|nature underground p:hallowmead
was thrown out by the surface workshops as defective, and found a place that fixes things|craft underground p:hallowmead
""",
    "npc.goal": """
see the surface once, and come back to tell it|mystery underground p:hallowmead
earn a place on the festival team|festival underground p:hallowmead
find out who keeps repairing things in the dark|craft mystery underground p:hallowmead
prove that something thrown away still has value|trade craft underground p:hallowmead
get the other settlements to admit who built their homes|craft politics underground p:hallowmead
keep one more leshy from being lost|nature family underground p:hallowmead
find a place that is safe from both above and below|underground p:hallowmead
work out what thinking and being someone actually mean|mystery underground p:hallowmead t:light
""",
    "npc.knows": """
which tunnel arches the Grand Underhall has quietly stopped trusting|craft underground p:hallowmead
which refuse chute pays best this season|trade treasure underground p:hallowmead
a Hushwarrens route that avoids the Crossings|mystery underground p:hallowmead
what the grippli will not say about the deep|mystery monster underground p:hallowmead
""",
    "npc.fear": """
whatever the grippli fled from in the deep|monster underground p:hallowmead
Hallowmead's raiders coming through Crown's Post|military underground p:hallowmead
""",
}


def table_additions():
    """The entries above as clean lines: {table name: [shorthand entry, ...]}."""
    return {name: [ln.strip() for ln in text.strip().splitlines() if ln.strip() and not ln.strip().startswith("#")]
            for name, text in TABLE_ADDITIONS.items()}


def clone_pages():
    return copy.deepcopy(build_pages())

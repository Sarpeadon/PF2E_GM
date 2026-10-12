# PF2e GM Tool

Local desktop app for encounter generation, creature stat blocks, and treasure tracking.
Python 3.10+ with Tkinter. No extra packages.

## Setup
1. Run `python main.py`
2. Party & Data tab: click **Download / Update Data**. The app finds the newest `pf2e-x.y.z` release on
   GitHub, streams the source archive, keeps only the `packs/` data and the English language files (trait descriptions), and builds the index and stat block
   database. The first run takes a few minutes. Only the data files are saved (`user_data/pf2e_data/`).
3. Import your players' Pathbuilder JSON exports (Pathbuilder menu: Export > Export JSON), or add PCs manually.

**Updates:** "Check on startup" compares your installed release to the latest and shows the result on the
Party & Data tab. Updating only happens when you click the button. Downloads go to a staging folder and replace
your data only after they finish, so a failed download leaves the old data in place. Custom content, party,
and ledger files are never touched.

**Starfinder:** Excluded by default (by pack folder name and publication title). Tick "Include Starfinder"
before downloading if you want it.

**Advanced:** You can still point the app at a local folder (e.g. your own git clone) and index it.

## Party size
Default party size is 5 (`DEFAULT_PARTY_SIZE` in `pf2e_gm/rules.py`). Party size is set on the Party & Data tab and
is independent of how many PCs are on the roster. It drives: encounter budgets (per-PC adjustment from GM Core),
treasure (GM Core Different Party Sizes: per extra PC, +1 permanent item of party level or +1, +2 consumables,
+Currency per Additional PC), ledger targets, and XP awards (always the amount for a group of four, so a 100 XP
fight for 5 PCs awards 80).

## Where data lives
On Windows the downloaded rules data and indexes go to `%LOCALAPPDATA%\pf2e_gm_tool` so OneDrive doesn't sync
~30,000 files. Your own content stays in `user_data` beside the app. Older installs are moved automatically on
first launch. Set the `PF2E_GM_CACHE` environment variable to use another folder.

## Tabs
- **Party & Data**: Download/update rules data. Import Pathbuilder JSON: name, level, and a computed
  Perception, HP, and AC (item bonuses aren't included, so double-click a PC to correct values).
- **Encounters**: Dropdown filters for **Region**, **Theme**, **Creature type**, **Family** (with counts), **Book/source**, and **Size**, plus include/exclude trait pickers. **Grouping** controls how cohesive an encounter is: Any mix, Prefer related creatures, or Related only (same family trait or same book). **Related Creatures** lists what belongs with the selected creature and why; **Build Around Selected** generates encounters anchored on it. Pathfinder stat blocks have no habitat field, so "related" means shared family traits or the same adventure/book (large general bestiaries count for little).
- **Encounters (budget)**: GM Core XP budgets (Trivial to Extreme, adjusted for party size). Filters for rarity, traits,
  name/source, custom only, and **Include Elite/Weak variants** (lets creatures one level outside the range
  appear as Elite or Weak versions). Select a creature row and use **Make Elite / Make Weak / Make Normal**;
  XP, HP, AC, and warnings update. **Send Encounter to Combat** loads it into the tracker.
- **Stat blocks**: Full stat block with clickable rules (blue text), Elite/Weak applied, and a
  **Recall Knowledge** line: DC (level plus rarity), skills from the creature's traits, and suggestions for what a
  success reveals (weaknesses, lowest save, immunities/resistances, notable abilities).
- **Combat**: Initiative (creatures roll d20 + Perception; on ties creatures go first), HP with Damage/Heal,
  conditions with values, and effective AC (frightened/sickened/clumsy take the highest status penalty;
  off-guard from grabbed, prone, restrained, paralyzed, unconscious). **Next Turn** automates:
  frightened drops by 1 at end of turn; persistent damage reminder with DC 15 flat check; stunned removes actions
  and counts down at start of turn; slowed, quickened, and dying reminders. PCs at 0 HP become dying (plus
  wounded); healing clears dying and adds wounded. Creatures at 0 HP are marked defeated and skipped.
  Double-click a condition for its rules. Combat state saves automatically and survives restarts.
- **Hazards**: Encounters tab **Hazards** dropdown (none / simple / complex / any), **Hazard type** (trap, haunt,
  environmental...), and **Max hazards**. Simple hazards use the simple-hazard XP table; complex hazards use creature
  XP. When hazards are on, about half the options include one. Hazard stat blocks show Stealth (with DC), Disable,
  defenses, hardness/HP/BT, reactions, routine, and reset. Complex hazards roll initiative with Stealth in Combat.
- **Duplicate to Custom**: copies the selected stat block (including Elite/Weak if applied) into the creature editor
  as "Name (copy)" so you can reskin it. Strikes, spells, abilities, IWR, saves, and senses all carry over.
- **Custom Content > Spells**: build spells (type, rank, traditions, traits, cast, range, area, targets, defense,
  duration, damage, heightening, description). Custom spells are clickable on your creatures and get the same
  "Cast by" heightening section as official spells. A custom spell with the same name as an official one wins.
- **Custom Content > Abilities**: an abilities library. Insert any entry into a creature from the editor's Ability
  picker. Creature abilities now live in their own box, one per line: `Name [1|2|3|R|F] (traits): text`.
- **Sessions**: save generated encounters to a session (**Save to Session**), add session and encounter notes,
  **Plan Level Treasure Across Encounters** (splits the level's package by encounter XP, using the Treasure tab's
  filters), **Send to Combat**, and **Mark Complete** (awards XP scaled to a four-PC party and moves that
  encounter's treasure into the ledger; **Reopen** undoes it). Party XP and **Level Up Party** sit at the top.
- **Quick Ref** (F1): DC lookup by level or spell rank with difficulty and rarity adjustments, plus DCs by level,
  simple DCs, adjustments, encounter budgets for your party size, creature/hazard XP, degrees of success, and
  advancement.
- **Treasure**: Party Treasure by Level packages, rerolls, single rolls, item rules panel, and a ledger.
- **Custom Content**: every field is an editable dropdown (pick a suggestion or type your own). Suggestions come from the downloaded data. Builders add Strikes, spells (grouped by entry and rank), and abilities (inserted with rules text when known). **Regions** sub-tab: define regions by traits, families, types, books, and specific creatures (listed creatures are picked more often); starter regions are trait-based approximations you can edit or delete. **Test at Party Level** shows what fits.
- **Custom Content > Creatures**: Full stat block editor (Perception, senses, saves, IWR, speed, Strikes, spells,
  abilities). **Suggest Stats from Level** fills values from the GM Core creature-building tables by tier
  (Extreme/High/Moderate/Low). **Preview** shows the finished stat block. Custom creatures work with Elite/Weak,
  Recall Knowledge, and the combat tracker like official ones.

## Data files (`user_data/`)
`pf2e_data/` (downloaded rules data), `foundry_index.json`, `creature_details.sqlite` (stat blocks and rules glossary),
`party.json`, `combat.json`, `custom_creatures.json`, `custom_items.json`, `ledger.json`, `config.json`.

## Rules tables
`pf2e_gm/rules.py` (XP, treasure) and `pf2e_gm/gmtables.py` (creature building, Elite/Weak, Recall Knowledge DCs,
trait-to-skill table) were entered by hand from GM Core. Spot-check them against your book; each is a simple
table keyed by level, so corrections are one-line edits.

## Tests
`python -m pytest tests`

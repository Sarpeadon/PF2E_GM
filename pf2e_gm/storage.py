"""Persistent user data: config, party, custom content, treasure ledger."""
import json
import os
import shutil
from pathlib import Path

from .models import Creature, Item

DATA_DIR = Path(__file__).resolve().parent.parent / "user_data"
DATA_DIR.mkdir(exist_ok=True)


def _cache_dir():
    """Downloaded rules data (about 30,000 files) and the indexes it builds are kept out of the app folder
    on Windows, under %LOCALAPPDATA%, so OneDrive doesn't sync or lock them. Your own content
    (custom creatures, sessions, ledger...) stays in user_data next to the app, where OneDrive backs it up.
    Set PF2E_GM_CACHE to override."""
    override = os.environ.get("PF2E_GM_CACHE")
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local:
        return Path(local) / "pf2e_gm_tool"
    return DATA_DIR


CACHE_DIR = _cache_dir()
CACHE_DIR.mkdir(parents=True, exist_ok=True)

INDEX = CACHE_DIR / "foundry_index.json"
PF2E_DATA = CACHE_DIR / "pf2e_data"
DETAILS = CACHE_DIR / "creature_details.sqlite"
FILES = {
    "config": DATA_DIR / "config.json",
    "party": DATA_DIR / "party.json",
    "creatures": DATA_DIR / "custom_creatures.json",
    "items": DATA_DIR / "custom_items.json",
    "ledger": DATA_DIR / "ledger.json",
    "combat": DATA_DIR / "combat.json",
    "regions": DATA_DIR / "regions.json",
    "spells": DATA_DIR / "custom_spells.json",
    "abilities": DATA_DIR / "custom_abilities.json",
    "sessions": DATA_DIR / "sessions.json",
    "notebook": DATA_DIR / "notebook.json",
    "story_tables": DATA_DIR / "story_tables.json",     # your edits to the Story Forge tables and story types
    "magic_items": DATA_DIR / "magic_items.json",       # items you saved from the Magic Items tab
    "downtime": DATA_DIR / "downtime.json",             # projects, funds, and the downtime log
    "templates": DATA_DIR / "custom_templates.json",    # creature templates you made yourself
    "party_loot": DATA_DIR / "party_loot.json",         # what the party owns and who carries it (Party Loot)
}
VOCAB = CACHE_DIR / "vocab.json"
CACHE_NAMES = ("pf2e_data", "foundry_index.json", "creature_details.sqlite", "vocab.json")


def migrate_cache():
    """Move rules data from an older user_data folder into the cache folder. Returns moved names.
    Failures are skipped (the data can always be re-downloaded)."""
    moved = []
    if CACHE_DIR.resolve() == DATA_DIR.resolve():
        return moved
    for name in CACHE_NAMES:
        old, new = DATA_DIR / name, CACHE_DIR / name
        if old.exists() and not new.exists():
            try:
                shutil.move(str(old), str(new))
                moved.append(name)
            except OSError:
                continue
    for leftover in ("pf2e_data_staging", "pf2e_data_old"):
        shutil.rmtree(DATA_DIR / leftover, ignore_errors=True)
    return moved
DEFAULTS = {"config": {}, "party": [], "creatures": [], "items": [], "ledger": [], "combat": {}, "regions": None,
            "spells": [], "abilities": [], "sessions": [], "notebook": [], "story_tables": {},
            "magic_items": [], "downtime": {}, "templates": [], "party_loot": {}}


def load(key):
    p = FILES[key]
    if not p.exists():
        if key == "regions":
            from .groups import STARTER_REGIONS
            return json.loads(json.dumps(STARTER_REGIONS))
        return json.loads(json.dumps(DEFAULTS[key]))
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(key, data):
    tmp = FILES[key].with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(FILES[key])


def load_custom_creatures():
    return [Creature(**{**d, "custom": True}) for d in load("creatures")]


def load_custom_items():
    return [Item(**{**d, "custom": True}) for d in load("items")]


def save_custom_creatures(cs):
    save("creatures", [c.to_dict() for c in cs])


def save_custom_items(items):
    save("items", [i.to_dict() for i in items])

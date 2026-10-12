"""Loading Foundry pf2e compendium data, custom content, and Pathbuilder exports."""
import json
import os
import re
from pathlib import Path

from .models import Creature, Item
from .statblock import DetailsDB, build_details, build_hazard_details, build_rule, trait_rules

PHYSICAL_TYPES = {"weapon", "armor", "shield", "equipment", "consumable", "backpack", "ammo"}
MAGIC_TRAITS = {"magical", "arcane", "divine", "occult", "primal", "alchemical", "invested", "rune"}


def _get(d, *path, default=None):
    for key in path:
        if not isinstance(d, dict) or key not in d:
            return default
        d = d[key]
    return d


COIN_GP = {"pp": 10, "gp": 1, "sp": 0.1, "cp": 0.01}
PRICE_STR = re.compile(r"([\d,.]+)\s*(pp|gp|sp|cp|credits?|cr|upb)\b", re.IGNORECASE)


def _num(v):
    try:
        return float(str(v).replace(",", "")) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


def parse_price(price):
    """(gp, credits) from Foundry price data. Handles coin dicts with string values, a 'per' bundle size,
    Starfinder credits/UPB, and legacy strings like '5 sp' or '120 credits'."""
    per = 1
    if isinstance(price, dict) and isinstance(price.get("value"), (dict, str)):
        per = max(1, int(_num(price.get("per")) or 1))
        price = price["value"]
    gp = credits = 0.0
    if isinstance(price, dict):
        for coin, mult in COIN_GP.items():
            gp += _num(price.get(coin)) * mult
        credits = _num(price.get("credits")) + _num(price.get("upb")) + _num(price.get("cr"))
    elif isinstance(price, str):
        for amount, unit in PRICE_STR.findall(price):
            unit = unit.lower()
            if unit in COIN_GP:
                gp += _num(amount) * COIN_GP[unit]
            else:
                credits += _num(amount)
    return round(gp / per, 2), round(credits / per, 2)


def _price_gp(price):
    return parse_price(price)[0]


def _source(sysd):
    return (_get(sysd, "publication", "title") or _get(sysd, "details", "publication", "title")
            or _get(sysd, "source", "value") or _get(sysd, "details", "source", "value") or "")


def _iter_docs(root: Path):
    """Yield (document, path) from a Foundry pf2e checkout (per-file JSON or legacy .db NDJSON)."""
    for dirpath, _, files in os.walk(root):
        if "node_modules" in dirpath or "/.git" in dirpath:
            continue
        for fn in files:
            p = Path(dirpath) / fn
            try:
                if fn.endswith(".json") and not fn.startswith("_"):
                    with open(p, encoding="utf-8") as f:
                        doc = json.load(f)
                    if isinstance(doc, dict):
                        yield doc, p
                elif fn.endswith(".db"):
                    with open(p, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                yield json.loads(line), p
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                continue


def parse_creature(doc):
    if doc.get("type") != "npc" or "name" not in doc:
        return None
    s = doc.get("system", {})
    level = _get(s, "details", "level", "value")
    if not isinstance(level, int):
        return None
    return Creature(
        name=doc["name"], level=level,
        rarity=_get(s, "traits", "rarity", default="common") or "common",
        traits=list(_get(s, "traits", "value", default=[]) or []),
        size=_get(s, "traits", "size", "value", default="") or "",
        hp=_get(s, "attributes", "hp", "max"), ac=_get(s, "attributes", "ac", "value"),
        source=_source(s),
    )


def parse_hazard(doc):
    if doc.get("type") != "hazard" or "name" not in doc:
        return None
    s = doc.get("system", {})
    level = _get(s, "details", "level", "value")
    if not isinstance(level, int):
        return None
    traits = list(_get(s, "traits", "value", default=[]) or [])
    return Creature(
        name=doc["name"], level=level,
        rarity=_get(s, "traits", "rarity", default="common") or "common",
        traits=traits, hp=_get(s, "attributes", "hp", "max"), ac=_get(s, "attributes", "ac", "value"),
        source=_source(s), kind="hazard",
        complex=bool(_get(s, "details", "isComplex")) or "complex" in traits,
    )


def parse_item(doc):
    t = doc.get("type")
    if t not in PHYSICAL_TYPES or "name" not in doc:
        return None
    s = doc.get("system", {})
    level = _get(s, "level", "value")
    if not isinstance(level, int):
        return None
    traits = list(_get(s, "traits", "value", default=[]) or [])
    consumable = t in ("consumable", "ammo") or "consumable" in traits
    raw = _get(s, "price")
    if not isinstance(raw, dict) or "value" not in raw:
        raw = {"value": raw}
    gp, credits = parse_price(raw)
    return Item(
        name=doc["name"], level=level,
        rarity=_get(s, "traits", "rarity", default="common") or "common",
        traits=traits, item_type=t, price_gp=gp, price_credits=credits,
        consumable=consumable, magical=bool(MAGIC_TRAITS & set(traits)) or "tech" in traits, source=_source(s),
    )


SF_PATH = re.compile(r"(^|[\\/_\-.])(sf2e|starfinder)([\\/_\-.]|$)", re.IGNORECASE)


def _is_starfinder(doc, path=None, root=None):
    """Starfinder if the file sits under packs/sf2e (the repo keeps PF and SF packs side by side) or its
    publication is a Starfinder book."""
    if path is not None:
        try:
            rel = str(Path(path).relative_to(root)) if root else str(path)
        except ValueError:
            rel = str(path)
        if SF_PATH.search(rel):
            return True
    return "starfinder" in _source(doc.get("system", {})).lower()


def _lang_dir(root):
    for cand in (root / "lang", root / "static" / "lang", root.parent / "lang", root.parent / "static" / "lang"):
        if cand.is_dir():
            return cand
    return None


def load_foundry(root, progress=None, include_starfinder=True, details_out=None, rules_out=None):
    """Scan a local copy of github.com/foundryvtt/pf2e (the packs folder or repo root).

    If details_out is a list, (uid, stat block dict) pairs are appended to it.
    If rules_out is a list, rules glossary rows (conditions, spells, actions, feats, items, traits) are appended.
    """
    root = Path(root)
    lang = _lang_dir(root)
    if rules_out is not None and lang:
        rules_out.extend(trait_rules(lang))
    if (root / "packs").is_dir():
        root = root / "packs"
    creatures, items, seen_c, seen_i = [], [], set(), set()
    for n, (doc, path) in enumerate(_iter_docs(root)):
        if progress and n % 2000 == 0:
            progress(f"Indexing... {n} documents read")
        sf = _is_starfinder(doc, path, root)
        if sf and not include_starfinder:
            continue
        system = "sf" if sf else "pf"
        c = parse_creature(doc) or parse_hazard(doc)
        if c:
            c.system = system
            if c.uid not in seen_c:
                seen_c.add(c.uid); creatures.append(c)
                if details_out is not None:
                    try:
                        details_out.append((c.uid, build_hazard_details(doc) if c.is_hazard
                                            else build_details(doc)))
                    except Exception:  # one odd stat block should never break indexing
                        pass
                    else:
                        details_out[-1][1]["system"] = system
            continue
        if rules_out is not None:
            try:
                r = build_rule(doc)
                if r:
                    r[3]["system"] = system
                    rules_out.append(r)
            except Exception:
                pass
        i = parse_item(doc)
        if i:
            i.system = system
        if i and i.uid not in seen_i:
            seen_i.add(i.uid); items.append(i)
    return creatures, items


def save_index(path, creatures, items, source_path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"source_path": str(source_path),
                   "creatures": [c.to_dict() for c in creatures],
                   "items": [i.to_dict() for i in items]}, f)


# Starfinder 2e books whose titles don't all contain "Starfinder".
SF_BOOKS = ("starfinder", "alien core", "galactic ancestries", "tales from the vast", "rescue on raxil",
            "guilt of the grave world", "absalom station", "hellfire dispatches", "sfs ", "field test")
SF_TRAITS = {"analog", "tech"}


def looks_starfinder(x):
    """Fallback for indexes built before items were tagged by game system (or with untagged entries)."""
    src = (getattr(x, "source", "") or "").lower()
    if any(b in src for b in SF_BOOKS):
        return True
    traits = {str(t).lower() for t in getattr(x, "traits", []) or []}
    return bool(traits & SF_TRAITS) and "pathfinder" not in src


def load_index(path):
    """Load the summary index. Entries with no system tag, or Pathfinder-tagged entries from a Starfinder
    book, are re-tagged as Starfinder so the Pathfinder/Starfinder toggle filters them correctly."""
    if not Path(path).exists():
        return [], [], ""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    cs = [Creature(**c) for c in d.get("creatures", [])]
    its = [Item(**i) for i in d.get("items", [])]
    for x in cs + its:
        if x.system != "sf" and looks_starfinder(x):
            x.system = "sf"
    return cs, its, d.get("source_path", "")


def build_index(root, index_path, details_path, include_starfinder=True, progress=None):
    """Scan, then write the summary index and the stat block database."""
    details, rules = [], []
    cs, its = load_foundry(root, progress, include_starfinder, details_out=details, rules_out=rules)
    if progress:
        progress(f"Saving {len(details)} stat blocks and {len(rules)} rules entries...")
    DetailsDB(details_path).write_all(details, rules)
    save_index(index_path, cs, its, root)
    return cs, its


def load_pathbuilder(path):
    """Return (name, level) from a Pathbuilder 2e JSON export."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    build = d.get("build", d)
    return build.get("name", Path(path).stem), int(build.get("level", 1))


def load_pathbuilder_full(path):
    """Party entry from a Pathbuilder 2e JSON export: name, level, and best-effort perception/hp/ac.

    Perception and HP are computed from the build (attribute + proficiency + level); item bonuses
    are not included, so treat them as close and edit if needed. AC uses Pathbuilder's own total.
    """
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return parse_pathbuilder(d, Path(path).stem)


def parse_pathbuilder(d, fallback_name="PC"):
    b = d.get("build", d)
    level = int(b.get("level", 1) or 1)
    pc = {"name": b.get("name") or fallback_name, "level": level}

    def mod(score):
        try:
            return (int(score) - 10) // 2
        except (TypeError, ValueError):
            return None
    ab = b.get("abilities", {}) or {}
    wis, con = mod(ab.get("wis")), mod(ab.get("con"))
    prof = (b.get("proficiencies") or {}).get("perception")
    if wis is not None and isinstance(prof, int):
        pc["perception"] = wis + prof + (level if prof > 0 else 0)
    at = b.get("attributes") or {}
    if con is not None and "classhp" in at:
        pc["hp"] = int(at.get("ancestryhp", 0) or 0) + int(at.get("bonushp", 0) or 0) + \
            (int(at.get("classhp", 0) or 0) + int(at.get("bonushpPerLevel", 0) or 0) + con) * level
    ac = (b.get("acTotal") or {}).get("acTotal")
    if isinstance(ac, int):
        pc["ac"] = ac
    return pc

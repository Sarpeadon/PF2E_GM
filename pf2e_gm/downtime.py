"""Downtime: Earn Income, Craft, projects, funds, cost of living, and downtime events.

Rules come from Player Core (remastered) and GM Core, with the older Core Rulebook crafting rules available as a choice.
This module has no windows in it; the Downtime tab (gui.py) is a thin layer over these functions.

Money is kept in copper pieces (integers) so nothing drifts: 100 cp = 1 gp. The old gp-based functions (earn_income, craft,
degree, level_dc, spell_dc) are still here and unchanged.

What is and isn't from a book:
  * The Income Earned table, the Craft activity, and the Cost of Living table are Player Core and GM Core.
  * The skill a job uses, a job's task level, and a downtime event's frequency are the GM's call in Player Core; the job
    board and event tables are a convenience, and every one of them can be edited in Edit Tables.
The notice board at the end of this file (GM Tools tab) draws on the same job table as Earn Income, so a job you add in
Edit Tables turns up in both.
"""
import datetime
import math
import random
import re
import uuid

from .gmtables import DC_BY_LEVEL, RARITY_DC
from . import gmtools as gt

# task level: (failure, trained, expert, master, legendary) in gp per day. Player Core, Table 4-2: Income Earned.
EARN_INCOME = {
    0: (0.01, 0.05, 0.05, 0.05, 0.05), 1: (0.02, 0.2, 0.2, 0.2, 0.2), 2: (0.04, 0.3, 0.3, 0.3, 0.3),
    3: (0.08, 0.5, 0.5, 0.5, 0.5), 4: (0.1, 0.7, 0.8, 0.8, 0.8), 5: (0.2, 0.9, 1, 1, 1),
    6: (0.3, 1.5, 2, 2, 2), 7: (0.4, 2, 2.5, 2.5, 2.5), 8: (0.5, 2.5, 3, 3, 3), 9: (0.6, 3, 4, 4, 4),
    10: (0.7, 4, 5, 6, 6), 11: (0.8, 5, 6, 8, 8), 12: (0.9, 6, 8, 10, 10), 13: (1, 7, 10, 15, 15),
    14: (1.5, 8, 15, 20, 20), 15: (2, 10, 20, 28, 28), 16: (2.5, 13, 25, 36, 40), 17: (3, 15, 30, 45, 55),
    18: (4, 20, 45, 70, 90), 19: (6, 30, 60, 100, 130), 20: (8, 40, 75, 150, 200),
}
EARN_20_CRIT = (None, 50, 90, 175, 300)          # critical success on a level 20 task
PROFS = ["Trained", "Expert", "Master", "Legendary"]
RANKS = ["Untrained"] + PROFS
RANK_BY_NUMBER = {0: "Untrained", 2: "Trained", 4: "Expert", 6: "Master", 8: "Legendary"}
RESULTS = ["Critical success", "Success", "Failure", "Critical failure"]
LEARN_SPELL_COST = {0: 1, 1: 2, 2: 6, 3: 16, 4: 36, 5: 70, 6: 140, 7: 300, 8: 650, 9: 1500, 10: 7000}
RARITIES = ["common", "uncommon", "rare", "unique"]

# GM Core, Cost of Living: copper pieces per week, month, and year.
COST_OF_LIVING = {
    "Subsistence": {"week": 40, "month": 200, "year": 2400},
    "Comfortable": {"week": 100, "month": 400, "year": 5200},
    "Fine": {"week": 3000, "month": 13000, "year": 160000},
    "Extravagant": {"week": 10000, "month": 43000, "year": 520000},
}
LIVING_NOTE = "You can attempt to Subsist using Society or Survival for free."

RULESETS = {
    "remaster": {"label": "Player Core (remaster)", "setup_formula": 1, "setup_none": 2, "master_at": 9, "legendary_at": 17,
                 "formula_required": False},
    "legacy": {"label": "Core Rulebook (older)", "setup_formula": 4, "setup_none": 4, "master_at": 9, "legendary_at": 16,
               "formula_required": True},
}
MAGIC_TRAITS = {"magical", "arcane", "divine", "occult", "primal", "invested", "rune", "wand", "scroll", "staff",
                "talisman", "potion", "spellheart"}

ACTIVITIES = ["Earn Income", "Earn Income (Performance)", "Craft", "Create a Forgery", "Subsist", "Buy and Sell Items",
              "Retrain", "Anything else"]
EVENT_TABLES = {"Earn Income": ["dt.event.earn"], "Earn Income (Performance)": ["dt.event.performance"],
                "Craft": ["dt.event.craft", "dt.event.craft2"], "Create a Forgery": ["dt.event.forgery"],
                "Subsist": ["dt.event.subsist"], "Buy and Sell Items": ["dt.event.trade"], "Retrain": ["dt.event.retrain"],
                "Anything else": ["dt.event.general"]}
PROJECT_KINDS = {"craft": "Craft", "custom": "Project"}


# ------------------------------------------------------------------------------------------------ money
def to_cp(gp):
    return int(round(float(gp or 0) * 100))


def coin_text(cp):
    """'5 cp', '2 sp', '1 gp, 5 sp', '12 gp', '1,200 gp': coins the way the books write them."""
    cp = int(cp)
    if cp == 0:
        return "0 cp"
    sign = "-" if cp < 0 else ""
    cp = abs(cp)
    gp, rest = divmod(cp, 100)
    sp, c = divmod(rest, 10)
    bits = []
    if gp:
        bits.append(f"{gp:,} gp")
    if sp:
        bits.append(f"{sp} sp")
    if c:
        bits.append(f"{c} cp")
    return sign + ", ".join(bits)


_COIN_CP = {"pp": 1000, "gp": 100, "sp": 10, "cp": 1}
_COIN = re.compile(r"(\d+(?:\.\d+)?)\s*(pp|gp|sp|cp)?")


def parse_coins(text, default="gp"):
    """Copper from what a person types: '5 gp 3 sp', '12gp', '1.5 gp', '40 cp', '-2 sp', or a bare number (taken as default
    coins). Raises ValueError for anything else."""
    s = str(text or "").strip().lower().replace(",", "")
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("+-").strip()
    if not s:
        raise ValueError("Enter an amount, such as 5 gp 3 sp.")
    found = _COIN.findall(s)
    if not found or _COIN.sub("", s).strip():
        raise ValueError(f"Can't read '{text}' as money. Try something like 5 gp 3 sp.")
    return sign * sum(int(round(float(n) * _COIN_CP[u or default])) for n, u in found)


def pc_money_cp(pc):
    """The coins on a Pathbuilder character, in copper."""
    m = (pc or {}).get("money") or {}
    return int(m.get("pp", 0) or 0) * 1000 + int(m.get("gp", 0) or 0) * 100 + int(m.get("sp", 0) or 0) * 10 + int(m.get("cp", 0) or 0)


# ------------------------------------------------------------------------------------------------ DCs and results (unchanged)
def level_dc(level, rarity="common"):
    return DC_BY_LEVEL[max(-1, min(25, int(level)))] + RARITY_DC.get(rarity, 0)


def spell_dc(rank, rarity="common"):
    level = 1 if int(rank) <= 1 else 2 * int(rank) - 1
    return level_dc(level, rarity)


def income_per_day(task_level, prof, result):
    """gp per day for one Earn Income result."""
    task_level = max(0, min(20, int(task_level)))
    col = PROFS.index(prof) + 1
    if result == "Critical failure":
        return 0.0
    if result == "Failure":
        return EARN_INCOME[task_level][0]
    if result == "Critical success":
        if task_level == 20:
            return float(EARN_20_CRIT[col])
        return float(EARN_INCOME[task_level + 1][col])
    return float(EARN_INCOME[task_level][col])


def earn_income(task_level, prof, result, days=1):
    per = income_per_day(task_level, prof, result)
    return {"dc": level_dc(task_level), "per_day": per, "days": days, "total": round(per * days, 2)}


def degree(total, dc, nat=None):
    d = 3 if total >= dc + 10 else 2 if total >= dc else 0 if total <= dc - 10 else 1
    if nat == 20:
        d = min(3, d + 1)
    elif nat == 1:
        d = max(0, d - 1)
    return ["Critical failure", "Failure", "Success", "Critical success"][d]


def roll_check(mod, dc, rng=None, nat=None, extra=0):
    """One d20 check: {nat, mod, extra, total, dc, degree}. Pass nat to use a die someone already rolled."""
    rng = rng or random.Random()
    nat = rng.randint(1, 20) if nat is None else int(nat)
    total = nat + int(mod) + int(extra)
    return {"nat": nat, "mod": int(mod), "extra": int(extra), "total": total, "dc": int(dc), "degree": degree(total, dc, nat)}


def check_text(r):
    ex = f" {r['extra']:+d}" if r.get("extra") else ""
    return f"d20 {r['nat']} {r['mod']:+d}{ex} = {r['total']} vs DC {r['dc']}: {r['degree']}"


def rank_name(value):
    """'Trained' from 2, 'trained', 'T', or 'Trained' itself; 'Untrained' when it isn't recognized."""
    if isinstance(value, (int, float)):
        return RANK_BY_NUMBER.get(int(value), "Untrained")
    v = str(value or "").strip().lower()
    for r in RANKS:
        if v == r.lower() or v == r[0].lower():
            return r
    return "Untrained"


def rank_at_least(rank, minimum):
    return RANKS.index(rank_name(rank)) >= RANKS.index(rank_name(minimum))


# ------------------------------------------------------------------------------------------------ skills and characters
def parse_skill(text):
    """('lore', 'Alcohol') for 'alcohol-lore', 'Alcohol Lore', or 'Lore (Alcohol)'; ('skill', 'Crafting') otherwise."""
    s = str(text or "").strip()
    m = re.fullmatch(r"(?i)lore\s*\((.+)\)", s)
    if m:
        return "lore", m.group(1).strip().title()
    m = re.fullmatch(r"(?i)(.+?)[\s_-]+lore", s)
    if m:
        return "lore", m.group(1).replace("-", " ").replace("_", " ").strip().title()
    return "skill", s.replace("-", " ").replace("_", " ").strip().title()


def skill_label(text):
    """How a skill reads at the table: 'Crafting', 'Alcohol Lore'."""
    kind, name = parse_skill(text)
    return f"{name} Lore" if kind == "lore" else name


def pc_skill_key(text):
    """The key a Pathbuilder character stores the skill under: 'Crafting', 'Lore (Alcohol)'."""
    kind, name = parse_skill(text)
    return f"Lore ({name})" if kind == "lore" else name


def pc_skill(pc, skill):
    """What a character has in a skill: {mod, rank, label, trained}. mod is None when the character has no data for it; rank
    is None when the export isn't saved with the character (older imports)."""
    key = pc_skill_key(skill)
    kind, name = parse_skill(skill)
    skills = {str(k).lower(): v for k, v in ((pc or {}).get("skills") or {}).items()}
    mod = skills.get(key.lower())
    raw = (pc or {}).get("raw") or {}
    rank = None
    if isinstance(raw, dict) and raw:
        if kind == "lore":
            for lore in raw.get("lores") or []:
                if isinstance(lore, (list, tuple)) and len(lore) >= 2 and str(lore[0]).strip().lower() == name.lower():
                    rank = rank_name(lore[1])
            rank = rank or "Untrained"
        else:
            rank = rank_name((raw.get("proficiencies") or {}).get(name.lower(), 0))
    if mod is None and kind == "lore":
        intm = ((pc or {}).get("mods") or {}).get("int")
        if intm is not None:
            mod = intm                                                  # an untrained Lore is just the Int modifier
    return {"mod": mod, "rank": rank, "label": skill_label(skill), "trained": rank is not None and rank != "Untrained"}


def pc_feats(pc):
    return {str(f.get("name", "")).strip().lower() for f in ((pc or {}).get("feats") or []) if isinstance(f, dict)}


def norm_name(text):
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


def pc_formulas(pc):
    """Every formula name a character knows, normalized for matching."""
    out = set()
    for f in (pc or {}).get("formulas") or []:
        for name in (f.get("known") or []) if isinstance(f, dict) else []:
            out.add(norm_name(name))
    return out


def pc_knows_formula(pc, item_name):
    """True or False from the character's formulas; None when the character has none recorded at all."""
    known = pc_formulas(pc)
    if not known:
        return None
    return norm_name(item_name) in known


# ------------------------------------------------------------------------------------------------ the job board
def _tag_values(entry, prefix):
    return [t[len(prefix):] for t in entry.get("tags", []) if t.startswith(prefix)]


def jobs(registry, place=None, base_level=1, packs=None, tavern=False):
    """Jobs for Earn Income from the job tables: [{id, text, skills, level, place, table}]. place is a Notebook page title (or None
    for anywhere); a job tagged for a place is offered only there, and jobs tagged for none are offered everywhere. tavern
    adds the inn and tavern jobs. base_level is the job board level: each job's tl: tag moves it up or down from there."""
    from .downdata import slug
    want = slug(place) if place else None
    allowed = set(packs) if packs else None
    out, seen = [], set()
    for table in ["dt.job"] + (["dt.job.tavern"] if tavern else []):
        if not registry.has(table):
            continue
        for e in registry.entries(table):
            if e.get("off") or (allowed is not None and e["pack"] not in allowed):
                continue
            where = _tag_values(e, "f:")
            if (where and want not in where) or (want is None and where):
                continue
            key = (e["t"], tuple(where))
            if key in seen:
                continue
            seen.add(key)
            lvl = int(base_level) + sum(int(v) for v in _tag_values(e, "tl:") if re.fullmatch(r"[+-]?\d+", v))
            out.append({"id": e["id"], "text": e["t"], "skills": _tag_values(e, "sk:") or ["crafting"],
                        "level": max(0, min(20, lvl)), "place": where[0] if where else None, "table": table})
    out.sort(key=lambda j: (j["place"] is None, j["level"], j["text"]))
    return out


def best_skill(pc, job):
    """The job skill this character does best: (skill slug, pc_skill info), preferring trained skills, then the higher
    modifier. Falls back to the job's first skill when the character has no data."""
    best = None
    for sk in job["skills"]:
        info = pc_skill(pc, sk)
        score = (info["trained"], info["mod"] if info["mod"] is not None else -99)
        if best is None or score > best[0]:
            best = (score, sk, info)
    return best[1], best[2]


def earn_result(task_level, prof, result, days=1):
    """An Earn Income result in copper: {dc, per_day_cp, days, total_cp, text}. The Income Earned table has no column for an
    untrained character, so prof must be Trained or better."""
    prof = rank_name(prof)
    if prof == "Untrained":
        raise ValueError("The Income Earned table has no column for an untrained character.")
    task_level = max(0, min(20, int(task_level)))
    days = max(1, int(days))
    per = to_cp(income_per_day(task_level, prof, result))
    notes = {"Critical success": "Paid at one task level higher.", "Success": "",
             "Failure": "Paid the bare minimum; the GM will likely cut the job short.",
             "Critical failure": "Nothing earned, and the job is lost. The PC's reputation suffers."}
    text = f"{result}: {coin_text(per)} a day" + (f", {coin_text(per * days)} for {days} days" if days > 1 else "") + ". " + notes.get(result, "")
    return {"dc": level_dc(task_level), "per_day_cp": per, "days": days, "total_cp": per * days, "text": text.strip()}


# ------------------------------------------------------------------------------------------------ the store
def new_store():
    return {"version": 1, "projects": [], "purses": {}, "log": [], "settings": {"ruleset": "remaster", "event_chance": 25}}


PROJECT_STATUSES = ("setup", "working", "paused", "done", "failed", "abandoned")


def _fix_project(p):
    """A project with every field the tab reads, so one odd entry in a saved file can't break the tab. Returns None for
    something that isn't a project at all."""
    if not isinstance(p, dict):
        return None
    p.setdefault("id", uuid.uuid4().hex[:10])
    if p.get("kind") not in PROJECT_KINDS:
        p["kind"] = "custom"
    if p.get("status") not in PROJECT_STATUSES:
        p["status"] = "working"
    base = {"title": "(untitled project)", "owner": "", "days_done": 0, "notes": "", "created": _now(), "spent_cp": 0}
    if p["kind"] == "craft":
        base.update(total_cp=0, upfront_cp=0, remaining_cp=0, per_day_cp=0, setup_days=1, dc=0, degree="", ruin_cp=0, prof="Trained",
                    crafter_level=1, ruleset="remaster", has_formula=False)
    else:
        base.update(days_needed=1, cost_cp=0, paid_cp=0, dc=None)
    for k, v in base.items():
        if k not in p or p[k] is None and k != "dc":
            p[k] = v
    if not isinstance(p.get("log"), list):
        p["log"] = []
    if p["kind"] == "craft":
        if p["ruleset"] not in RULESETS:
            p["ruleset"] = "remaster"
        if p["prof"] not in PROFS:
            p["prof"] = "Trained"
        if not isinstance(p.get("item"), dict):
            p["item"] = {"name": p["title"], "level": 0, "price_gp": 0.0, "rarity": "common", "qty": 1}
        for k, v in (("name", p["title"]), ("level", 0), ("price_gp", 0.0), ("rarity", "common"), ("qty", 1)):
            p["item"].setdefault(k, v)
    return p


def ensure_store(store):
    """Fill in anything an older or empty store is missing, in place, and return it. Projects are repaired, not dropped."""
    if not isinstance(store, dict):
        store = {}
    base = new_store()
    for k, v in base.items():
        if not isinstance(store.get(k), type(v)):
            store[k] = v
    for k, v in base["settings"].items():
        store["settings"].setdefault(k, v)
    store["projects"] = [q for q in (_fix_project(p) for p in store["projects"]) if q is not None]
    for who, pu in list(store["purses"].items()):
        if not isinstance(pu, dict):
            del store["purses"][who]
            continue
        pu["cp"] = int(pu.get("cp", 0)) if isinstance(pu.get("cp", 0), (int, float)) else 0
        if not isinstance(pu.get("log"), list):
            pu["log"] = []
    return store


def _now(date=None):
    return date or datetime.date.today().isoformat()


def log_line(store, text, who="", date=None):
    store["log"].append({"date": _now(date), "who": who, "text": text})
    del store["log"][:-500]


# ------------------------------------------------------------------------------------------------ funds
def purse(store, who):
    return store["purses"].setdefault(who, {"cp": 0, "log": []})


def purse_balance(store, who):
    """What a character has. Looking never creates a purse; only spending or earning does."""
    return int((store["purses"].get(who) or {}).get("cp", 0))


def purse_add(store, who, cp, reason, date=None):
    """Add (or, with a negative amount, spend) copper. Returns the new log entry. The balance may go below zero: the tab
    shows it in red so the GM can decide what that means."""
    p = purse(store, who)
    p["cp"] += int(cp)
    e = {"id": uuid.uuid4().hex[:8], "date": _now(date), "cp": int(cp), "reason": str(reason), "balance_cp": p["cp"]}
    p["log"].append(e)
    return e


def purse_set(store, who, cp, reason="Set by hand", date=None):
    p = purse(store, who)
    return purse_add(store, who, int(cp) - p["cp"], reason, date)


def purse_undo(store, who):
    """Take back the latest entry. Returns it, or None."""
    p = purse(store, who)
    if not p["log"]:
        return None
    e = p["log"].pop()
    p["cp"] -= e["cp"]
    return e


def cost_of_living(standard, unit="week", count=1):
    """Copper owed for living at a standard for a number of weeks, months, or years (GM Core, Cost of Living)."""
    table = COST_OF_LIVING[standard]
    if unit not in table:
        raise ValueError("unit must be week, month, or year")
    return table[unit] * max(0, int(count))


# ------------------------------------------------------------------------------------------------ crafting
def craft_dc(item_level, rarity="common"):
    return level_dc(item_level, rarity)


def _setup_days(ruleset, has_formula):
    r = RULESETS[ruleset]
    return r["setup_formula"] if has_formula else r["setup_none"]


def craft_requirements(item, crafter_level, crafting_rank=None, feats=(), has_formula=None, ruleset="remaster"):
    """Whether a character can Craft an item, as a list of {kind, ok, text}. ok is True, False, or None (the book leaves it to
    the GM or the table). item: {name, level, price_gp, rarity, traits}. crafting_rank is None when the character's rank
    isn't known."""
    rs = RULESETS[ruleset]
    feats = {str(f).lower() for f in feats}
    traits = {str(t).lower() for t in item.get("traits") or []}
    lvl = int(item.get("level") or 0)
    out = []
    out.append({"kind": "level", "ok": lvl <= int(crafter_level),
                "text": (f"The item is level {lvl}, within a level {crafter_level} crafter's reach."
                         if lvl <= int(crafter_level) else
                         f"The item is level {lvl}, above a level {crafter_level} crafter. Craft needs an item of your level or lower.")})
    need = "Legendary" if lvl >= rs["legendary_at"] else "Master" if lvl >= rs["master_at"] else "Trained"
    if crafting_rank is None:
        out.append({"kind": "rank", "ok": None, "text": f"Needs {need} in Crafting (this character's rank isn't on file)."})
    else:
        ok = rank_at_least(crafting_rank, need)
        out.append({"kind": "rank", "ok": ok, "text": (f"Crafting is {rank_name(crafting_rank)}, enough for a level {lvl} item." if ok
                                                       else f"Needs {need} in Crafting for a level {lvl} item; this character is {rank_name(crafting_rank)}.")})
    for trait, feat in (("alchemical", "Alchemical Crafting"), ("snare", "Snare Crafting")):
        if trait in traits:
            have = feat.lower() in feats
            out.append({"kind": "feat", "ok": have, "text": (f"Has {feat}." if have else f"Needs the {feat} skill feat.")})
    if (traits & MAGIC_TRAITS) and "alchemical" not in traits:
        have = "magical crafting" in feats
        out.append({"kind": "feat", "ok": have, "text": ("Has Magical Crafting." if have else "Needs the Magical Crafting skill feat.")})
    rar = str(item.get("rarity") or "common").lower()
    if rar != "common":
        out.append({"kind": "rarity", "ok": None, "text": f"The item is {rar}: the crafter needs special access to it (the GM's call)."})
    if rs["formula_required"]:
        out.append({"kind": "formula", "ok": bool(has_formula) if has_formula is not None else None,
                    "text": ("Has the formula." if has_formula else "Needs the item's formula (Core Rulebook).")})
    else:
        out.append({"kind": "formula", "ok": None, "text": ("Has the formula: the check comes after 1 day of setup." if has_formula
                                                           else "No formula: the check comes after 2 days of setup.")})
    out.append({"kind": "tools", "ok": None, "text": "Needs a set of tools and, in many cases, a workshop. Raw materials worth at least half the price."})
    if not item.get("price_gp"):
        out.append({"kind": "price", "ok": False, "text": "The item has no price, so there is nothing to work out."})
    return out


def craft_blockers(reqs):
    """The requirements a character definitely fails."""
    return [r["text"] for r in reqs if r["ok"] is False]


def craft_plan(item, crafter_level, prof, ruleset="remaster", has_formula=False, qty=1):
    """Numbers for crafting an item: DC, setup days, price, raw materials, and what an extra day of work saves for each
    degree of success. Money is in copper."""
    prof = rank_name(prof)
    if prof == "Untrained":
        raise ValueError("Crafting needs at least Trained in Crafting.")
    qty = max(1, int(qty))
    total = to_cp(item.get("price_gp")) * qty
    upfront = (total + 1) // 2                                              # at least half the price, in raw materials
    lvl = max(0, min(20, int(crafter_level)))
    ok_gp = income_per_day(lvl, prof, "Success")
    crit = (income_per_day(lvl + 1, prof, "Success") if lvl < 20 else float(EARN_20_CRIT[PROFS.index(prof) + 1]))
    per_s, per_c = to_cp(ok_gp), to_cp(crit)
    remaining = total - upfront

    def finish(per):
        return int(math.ceil(remaining / per)) if per else None
    return {"dc": craft_dc(item.get("level") or 0, item.get("rarity") or "common"), "ruleset": ruleset,
            "setup_days": _setup_days(ruleset, has_formula), "qty": qty, "total_cp": total, "upfront_cp": upfront,
            "remaining_cp": remaining, "per_day_success_cp": per_s, "per_day_crit_cp": per_c,
            "days_to_finish_success": finish(per_s), "days_to_finish_crit": finish(per_c),
            "ruin_cp": int(math.ceil(upfront * 0.10))}


def craft_summary(plan):
    return (f"DC {plan['dc']}. Price {coin_text(plan['total_cp'])}; raw materials worth {coin_text(plan['upfront_cp'])} at the start, "
            f"after {plan['setup_days']} day{'s' if plan['setup_days'] != 1 else ''} of setup. On a success each extra day of work "
            f"cuts what is left to pay ({coin_text(plan['remaining_cp'])}) by {coin_text(plan['per_day_success_cp'])}"
            + (f", about {plan['days_to_finish_success']} days to finish for free" if plan["days_to_finish_success"] else "")
            + f"; on a critical success by {coin_text(plan['per_day_crit_cp'])}"
            + (f", about {plan['days_to_finish_crit']} days" if plan["days_to_finish_crit"] else "")
            + f". A failure keeps the materials; a critical failure ruins {coin_text(plan['ruin_cp'])} of them.")


# ------------------------------------------------------------------------------------------------ projects
def _project(kind, owner, title, **extra):
    p = {"id": uuid.uuid4().hex[:10], "kind": kind, "title": title, "owner": owner or "", "status": "setup", "days_done": 0,
         "notes": "", "log": [], "created": _now(), "spent_cp": 0}
    p.update(extra)
    return p


def _note(p, text, days=0, date=None):
    p["log"].append({"date": _now(date), "text": text, "days": int(days)})


def add_note(p, text, date=None):
    """Add a line to a project's history."""
    _note(p, str(text), 0, date)


def start_craft(store, owner, item, crafter_level, prof, qty=1, ruleset="remaster", has_formula=False, date=None):
    """A new Craft project, waiting for its Crafting check. Nothing is charged yet."""
    plan = craft_plan(item, crafter_level, prof, ruleset, has_formula, qty)
    name = item.get("name", "an item")
    p = _project("craft", owner, f"{name}" + (f" x{plan['qty']}" if plan["qty"] > 1 else ""), ruleset=ruleset,
                 item={"name": name, "level": int(item.get("level") or 0), "price_gp": float(item.get("price_gp") or 0),
                       "rarity": item.get("rarity", "common"), "qty": plan["qty"]},
                 crafter_level=int(crafter_level), prof=rank_name(prof), has_formula=bool(has_formula), dc=plan["dc"],
                 setup_days=plan["setup_days"], total_cp=plan["total_cp"], upfront_cp=plan["upfront_cp"],
                 remaining_cp=plan["total_cp"] - plan["upfront_cp"], per_day_cp=0, degree="", ruin_cp=plan["ruin_cp"])
    _note(p, f"Started. DC {plan['dc']}, {plan['setup_days']} day{'s' if plan['setup_days'] != 1 else ''} of setup, "
             f"{coin_text(plan['upfront_cp'])} in raw materials.", 0, date)
    store["projects"].append(p)
    return p


def start_custom(store, owner, title, days_needed, cost_cp=0, dc=None, notes="", date=None):
    """A project the GM sets the terms of (retraining, research, building something, a long job)."""
    p = _project("custom", owner, title, days_needed=max(1, int(days_needed)), cost_cp=max(0, int(cost_cp)), paid_cp=0,
                 dc=dc, notes=notes)
    p["status"] = "working"
    _note(p, f"Started: {p['days_needed']} days" + (f", {coin_text(cost_cp)}" if cost_cp else "") + ".", 0, date)
    store["projects"].append(p)
    return p


def _need(p, *statuses):
    if p["status"] not in statuses:
        raise ValueError(f"'{p['title']}' is {p['status']}; this needs it to be {' or '.join(statuses)}.")


def record_check(p, result, total=None, nat=None, date=None):
    """The Crafting check that ends setup. Returns {charge_cp, text}: what the crafter pays now (the raw materials, on a
    success; a tenth of them ruined on a critical failure)."""
    _need(p, "setup")
    if p["kind"] != "craft":
        raise ValueError("Only a Craft project has a Crafting check.")
    if result not in RESULTS:
        raise ValueError("result must be one of " + ", ".join(RESULTS))
    p["degree"] = result
    p["days_done"] += p["setup_days"]
    how = f" ({total} vs DC {p['dc']})" if total is not None else ""
    if result in ("Success", "Critical success"):
        lvl = p["crafter_level"] + (1 if result == "Critical success" else 0)
        p["per_day_cp"] = (to_cp(income_per_day(min(lvl, 20), p["prof"], "Success")) if lvl <= 20
                           else to_cp(EARN_20_CRIT[PROFS.index(p["prof"]) + 1]))
        if result == "Critical success" and p["crafter_level"] >= 20:
            p["per_day_cp"] = to_cp(EARN_20_CRIT[PROFS.index(p["prof"]) + 1])
        p["spent_cp"] += p["upfront_cp"]
        p["status"] = "working"
        text = (f"{result}{how}. Raw materials worth {coin_text(p['upfront_cp'])} are used. Each extra day of work cuts what "
                f"is left to pay ({coin_text(p['remaining_cp'])}) by {coin_text(p['per_day_cp'])}.")
        _note(p, text, p["setup_days"], date)
        return {"charge_cp": p["upfront_cp"], "text": text}
    charge = 0
    if result == "Critical failure":
        charge = p["ruin_cp"]
        p["spent_cp"] += charge
    p["status"] = "failed"
    text = (f"{result}{how}. The item is not made. " + (f"{coin_text(charge)} of the materials are ruined; the rest can be salvaged. "
                                                        if charge else "The materials can be salvaged at full value. ") + "Starting again means starting over.")
    _note(p, text, p["setup_days"], date)
    return {"charge_cp": charge, "text": text}


def work_days(p, n=1, date=None):
    """Spend days on a project. Craft: each day cuts what is left to pay by the project's daily amount, and the project is
    done when nothing is left. Custom: each day moves it toward its days needed. Returns {days_used, done, remaining_cp}."""
    _need(p, "working")
    n = max(1, int(n))
    used = 0
    for _ in range(n):
        if p["kind"] == "craft":
            if p["remaining_cp"] <= 0:
                break
            p["remaining_cp"] = max(0, p["remaining_cp"] - p["per_day_cp"])
            p["days_done"] += 1
            used += 1
            if p["remaining_cp"] <= 0:
                break
        else:
            if p["days_done"] >= p["days_needed"]:
                break
            p["days_done"] += 1
            used += 1
            if p["days_done"] >= p["days_needed"]:
                break
    done = (p["remaining_cp"] <= 0) if p["kind"] == "craft" else (p["days_done"] >= p["days_needed"])
    if done:
        p["status"] = "done"
    left = p["remaining_cp"] if p["kind"] == "craft" else max(0, p["days_needed"] - p["days_done"])
    _note(p, (f"Worked {used} day{'s' if used != 1 else ''}. " + ("Finished." if done else
           (f"{coin_text(left)} still to pay." if p["kind"] == "craft" else f"{left} days to go."))), used, date)
    return {"days_used": used, "done": done, "remaining_cp": left if p["kind"] == "craft" else 0}


def pay_remaining(p, date=None):
    """Craft: pay what is left in raw materials and finish the item now. Returns the copper paid."""
    _need(p, "working")
    if p["kind"] != "craft":
        raise ValueError("Only a Craft project has materials left to pay.")
    cost = p["remaining_cp"]
    p["spent_cp"] += cost
    p["remaining_cp"] = 0
    p["status"] = "done"
    _note(p, f"Paid the remaining {coin_text(cost)} in materials and finished the item.", 0, date)
    return cost


def pay_toward(p, cp, date=None):
    """Custom: record money paid toward the project's cost."""
    if p["kind"] != "custom":
        raise ValueError("Only a custom project tracks a cost.")
    p["paid_cp"] += int(cp)
    _note(p, f"Paid {coin_text(cp)}.", 0, date)
    return p["paid_cp"]


def pause(p, date=None):
    _need(p, "setup", "working")
    p["resume_to"] = p["status"]
    p["status"] = "paused"
    _note(p, "Paused. It can be picked up where it left off.", 0, date)


def resume(p, date=None):
    _need(p, "paused")
    p["status"] = p.pop("resume_to", "working")
    _note(p, "Resumed.", 0, date)


def abandon(p, date=None):
    if p["status"] in ("done", "failed", "abandoned"):
        raise ValueError(f"'{p['title']}' is already {p['status']}.")
    p["status"] = "abandoned"
    _note(p, "Abandoned.", 0, date)


def project_progress(p):
    """A short phrase for a project's state."""
    st = p["status"]
    if p["kind"] == "craft":
        if st == "setup":
            return f"setting up, check after {p['setup_days']} day{'s' if p['setup_days'] != 1 else ''}"
        if st in ("working", "paused"):
            return f"{st}, {coin_text(p['remaining_cp'])} left to pay, {p['days_done']} days in"
        return f"{st}, {p['days_done']} days"
    return f"{st}, day {p['days_done']} of {p['days_needed']}"


def project_text(p):
    """A full description of a project for the details pane."""
    lines = [f"{p['title']}  ({PROJECT_KINDS.get(p['kind'], 'Project')}, {p['status']})", f"Owner: {p['owner'] or '(none)'}"]
    if p["kind"] == "craft":
        it = p["item"]
        lines += [f"Item: {it['name']}, level {it['level']}, {coin_text(to_cp(it['price_gp']))} each" + (f", {it['qty']} of them" if it["qty"] > 1 else ""),
                  f"Rules: {RULESETS[p['ruleset']]['label']}. DC {p['dc']}. {p['setup_days']} days of setup.",
                  f"Price {coin_text(p['total_cp'])}. Materials used so far: {coin_text(p['spent_cp'])}. Left to pay: {coin_text(p['remaining_cp'])}."]
        if p["degree"]:
            lines.append(f"Crafting check: {p['degree']}. Each extra day cuts {coin_text(p['per_day_cp'])}.")
    else:
        lines += [f"{p['days_done']} of {p['days_needed']} days done."]
        if p.get("cost_cp"):
            lines.append(f"Cost {coin_text(p['cost_cp'])}; paid {coin_text(p['paid_cp'])}.")
        if p.get("dc") is not None:
            lines.append(f"DC {p['dc']}.")
    if p.get("notes"):
        lines.append("Notes: " + p["notes"])
    lines += ["", "History"] + [f"  {e['date']}: {e['text']}" for e in p["log"]]
    return "\n".join(lines)


def projects_for(store, owner=None, active_only=False):
    out = [p for p in store["projects"] if owner is None or p["owner"] == owner]
    if active_only:
        out = [p for p in out if p["status"] in ("setup", "working", "paused")]
    return out


def delete_project(store, pid):
    n = len(store["projects"])
    store["projects"] = [p for p in store["projects"] if p["id"] != pid]
    return n != len(store["projects"])


# ------------------------------------------------------------------------------------------------ events
def _ctx(registry, rng, **settings):
    from . import storygen as sg
    gen = sg.Generator(registry, campaign=sg.Campaign(), history=sg.History(strength=0.25, decay=0.85, recent=8), rng=rng)
    st = {"themes": list(settings.get("themes") or []), "env": settings.get("env") or "any", "tone": settings.get("tone") or "any",
          "level": int(settings.get("level") or 1), "focus": 0.3, "use_campaign": 0.0, "packs": settings.get("packs"),
          "pack_share": settings.get("pack_share")}
    return sg.Ctx(gen, st, set(settings.get("tags") or ()))


def roll_event(registry, activity="Anything else", rng=None, **settings):
    """A downtime event for an activity: {activity, table, text}. Crafting uses GM Core's three events 3 times in 20 and the
    Treasure Vault list the other 17. How often events happen at all is the GM's call (GM Core), so this only picks one."""
    rng = rng or random.Random()
    tables = EVENT_TABLES.get(activity) or EVENT_TABLES["Anything else"]
    ctx = _ctx(registry, rng, **settings)
    if activity == "Craft" and len(tables) == 2:
        table = tables[0] if rng.random() < 3 / 20 else tables[1]
    else:
        table = rng.choice(tables)
    if not registry.has(table):
        return {"activity": activity, "table": table, "text": ""}
    return {"activity": activity, "table": table, "text": re.sub(r"\s+", " ", ctx.roll(table).text).strip()}


def event_happens(rng=None, chance=25):
    """Whether an event happens this week at the chance the GM chose (a percentage). A convenience, not a book rule."""
    return (rng or random.Random()).randint(1, 100) <= max(0, min(100, int(chance)))


# ------------------------------------------------------------------------------------------------ the older craft() (kept as it was)
def craft(item_price, item_level, crafter_level, prof, result, rarity="common", setup_days=4, batch=1):
    """Crafting cost/time (Craft activity). Returns a dict with cost now, remaining, and days to finish free.
    Success: pay the remaining half to finish, or keep working; each extra day reduces the remaining cost by
    your Earn Income amount (crafter level, proficiency). Critical success uses crafter level + 1.
    Failure: you can keep the raw materials (no loss) but must start over. Critical failure: lose 10%.
    """
    total = round(float(item_price) * max(1, batch), 2)
    upfront = round(total / 2, 2)
    out = {"dc": level_dc(item_level, rarity), "total": total, "upfront": upfront, "setup_days": setup_days}
    if result in ("Success", "Critical success"):
        lvl = int(crafter_level) + (1 if result == "Critical success" else 0)
        lvl = min(lvl, 20)
        per = income_per_day(lvl, prof, "Success") if lvl <= 20 else 0
        if result == "Critical success" and int(crafter_level) >= 20:
            per = income_per_day(20, prof, "Critical success")
        out.update(remaining=upfront, reduce_per_day=per,
                   extra_days=(int(-(-upfront // per)) if per else None),
                   note="Pay the remaining half now, or spend extra days to reduce it.")
    elif result == "Failure":
        out.update(remaining=None, note="Not made. You can recover the raw materials and try again.")
    else:
        out.update(remaining=None, lost=round(upfront * 0.1, 2),
                   note="Not made, and 10% of the raw materials are ruined.")
    return out


# ------------------------------------------------------------------------------------------------ the notice board
# A board of notices for the GM Tools tab. Each notice is a task, a poster, a deadline, pay, and a catch. The task is either a
# real job from the Earn Income job table (with its skills and task level) or a silly one from the job.task table; the
# Silliness setting says how often it is which.
REAL_JOB_SHARE = {1: 0.7, 2: 0.45, 3: 0.2}
BOARD_OPTIONS = [
    gt.opt("where", "Notice board at", "choice", "", [], free=True, width=34, hint="blank = chosen for you", source="board"),
    gt.opt("count", "Notices", "int", 6, width=4), gt.LEVEL_OPT, gt.SIZE_OPT, gt.SILLY_OPT, gt.FLAVOR_OPT]


def make_notice(rl, level, size, idx, pool):
    """One notice as a result row. pool is what jobs() offers at this board (it may be empty)."""
    from . import names
    from .loot import currency_for
    rng = rl.rng
    anc = gt.pick_ancestry(rng, rl.flavor)
    name = names.make_name(anc, rng)
    occ = rl.roll("occupation")
    earn = ""
    if pool and rng.random() < REAL_JOB_SHARE.get(rl.dial, 0.45):
        job = rng.choice(pool)
        task = gt.lower_first(job["text"])
        jl = gt.clamp(job["level"], 1, 20)
        earn = "Earn Income: " + " or ".join(skill_label(x) for x in job["skills"]) + f", task level {job['level']}."
    else:
        task = rl.roll("job.task")
        jl = gt.clamp(level + rl.choice([-1, 0, 0, 1]), 1, 20)
    why, catch, head, deadline = rl.roll("job.why"), rl.roll("job.catch"), rl.roll("job.head"), rl.roll("deadline")
    offset = jl - level
    share = rng.uniform(0.08, 0.2) * currency_for(gt.clamp(level, 1, 20), size) * (1.0 + 0.15 * offset)
    cash = gt.money(max(0.5, share))
    silly = rl.roll("pay.silly")
    mode = rng.random()
    if rl.dial >= 3 and mode < 0.3:
        pay = f"{silly} and {gt.money(max(0.1, share * 0.2))}"
    elif rl.dial >= 2 and mode < 0.55:
        pay = f"{cash} and {silly}"
    else:
        pay = cash
    table = "sign." + anc.lower().replace(" ", "_")
    sign = rl.roll(table) if rl.has(table) else rl.roll("sign.default")
    who = f"{name}, {gt.article(anc.lower())} {anc.lower()} {occ}"
    gm = [head, f"Posted by: {who}", f"Task: {task}", f"Deadline: {deadline}", f"Pay: {pay}",
          f"Level {jl} job: the main obstacle is around DC {gt.dc(jl)} (standard DC for level {jl})."]
    if earn:
        gm.append(earn)
    gm += [f"Real reason: the poster {why}.", f"The catch: {catch}."]
    player = [head, f"{name}, {occ}, seeks capable persons to {task}.", f"Deadline: {deadline}.", f"Pay: {pay}.", sign]
    short = task if len(task) < 46 else task[:43].rstrip() + "..."
    return gt.row(f"{idx}. {name}: {short}", "\n".join(gm), "block", player="\n".join(player), level=jl, tag="job")


def generate_board(params, rng=None):
    rng = rng or random.Random()
    level, size = gt.clamp(params["level"], 1, 20), params["size"]
    rl = gt.Roller(rng, params["silly"], params["flavor"], level)
    where = params["where"].strip() or ("the Crossings notice board" if rl.flavor == "hallowmead" else "the village notice board")
    place = re.sub(r"(?i)\s*notice board$", "", where).strip() or None
    pool = jobs(rl.reg, place, level, rl.packs)
    rows = [make_notice(rl, level, size, i + 1, pool) for i in range(gt.clamp(params["count"], 1, 14))]
    return gt.result("jobs", f"Job board: {where}", rows, params)


TOOL_JOBS = {"key": "jobs", "label": "Job Board", "options": BOARD_OPTIONS, "generate": generate_board, "multi": True,
             "page_type": "Hook",
             "intro": "A board of notices. The GM view shows the real reason and the catch; the Player view is the notice itself. "
                      "Tasks come from the same job table as Earn Income, so jobs tied to a place turn up on that place's board."}

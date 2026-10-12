"""Session planner: saved encounters, treasure split across encounters, and XP tracking. Also the two GM Tools that plan and
close a session: the Quest Builder (a whole quest: a job, scenes, a hazard, an influence NPC, an encounter budget spent exactly,
and rewards) and the Session Recap (session notes turned into a player recap in a voice, with the secrets kept apart).
"""
import datetime
import random
import re
import uuid

from . import gmtools as gt
from . import hazards
from .downtime import jobs, make_notice
from .encounter import quest_fight
from .loot import currency_for, generate_level, item_text, permanent_text, weird_item
from .npcgen import generate_influence

XP_PER_LEVEL = 1000


def new_session(name, level, notes=""):
    return {"id": uuid.uuid4().hex[:8], "name": name, "level": level, "notes": notes,
            "date": datetime.date.today().isoformat(), "encounters": []}


def new_entry(enc_dict, name="", notes=""):
    """Wrap a saved encounter (encounter_to_dict) as a session entry."""
    e = dict(enc_dict)
    e.update({"id": uuid.uuid4().hex[:8], "name": name or enc_dict.get("name") or "Encounter",
              "notes": notes, "treasure": [], "status": "planned", "xp_awarded": 0})
    return e


def award_for(enc_xp, party_size):
    """XP each PC earns. GM Core: the budget grows with party size but the award is always the amount
    for a group of four, so scale the encounter's XP by 4 / party size (a 100 XP fight for 5 PCs awards 80)."""
    if party_size <= 0:
        return enc_xp
    return int(round(enc_xp * 4 / party_size))


def split_treasure(entries, bundle):
    """Distribute a LootBundle across encounter entries, weighted by encounter XP.

    Bigger fights get more of the loot. Items are dealt out largest-value first to whichever
    encounter currently has the lowest share relative to its XP weight. Currency is split by weight.
    Returns {entry id: [treasure rows]}.
    """
    live = [e for e in entries if e.get("status") != "done"]
    if not live:
        return {}
    weight = {e["id"]: max(1, e.get("xp", 0)) for e in live}
    total_w = sum(weight.values())
    share = {eid: 0.0 for eid in weight}
    out = {eid: [] for eid in weight}
    items = [("permanent", i) for i in bundle.permanent] + [("consumable", i) for i in bundle.consumables]
    items.sort(key=lambda x: -(x[1].price_gp or 0))
    for kind, it in items:
        eid = min(weight, key=lambda k: (share[k] / weight[k], -weight[k]))
        out[eid].append({"kind": kind, "name": it.name, "level": it.level, "value_gp": it.price_gp,
                         "custom": it.custom})
        share[eid] += max(1.0, it.price_gp or 0)
    remaining = round(bundle.currency, 2)
    ids = list(weight)
    for n, eid in enumerate(ids):
        amt = remaining if n == len(ids) - 1 else round(bundle.currency * weight[eid] / total_w)
        remaining = round(remaining - amt, 2)
        if amt:
            out[eid].append({"kind": "currency", "name": "Currency", "level": None, "value_gp": amt})
    return out


def plan_treasure(entries, items, level, party_size, seed=None, avoid=()):
    """Generate a level's treasure package and split it across planned encounters."""
    bundle = generate_level(items, level, party_size, seed=seed, avoid=avoid)
    return split_treasure(entries, bundle), bundle.notes


def complete(entry, party_size, ledger, level, today=None):
    """Mark an encounter done: award XP and move its treasure into the ledger. Returns XP awarded."""
    if entry.get("status") == "done":
        return 0
    xp = award_for(entry.get("xp", 0), party_size)
    entry["status"] = "done"
    entry["xp_awarded"] = xp
    today = today or datetime.date.today().isoformat()
    for t in entry.get("treasure", []):
        ledger.append({"level": level, "kind": t["kind"], "name": t["name"], "value_gp": t.get("value_gp", 0),
                       "date": today, "session_entry": entry["id"]})
    return xp


def reopen(entry, ledger):
    """Undo complete(): remove its ledger rows. Returns XP to subtract."""
    if entry.get("status") != "done":
        return 0
    ledger[:] = [r for r in ledger if r.get("session_entry") != entry["id"]]
    xp = entry.get("xp_awarded", 0)
    entry["status"] = "planned"
    entry["xp_awarded"] = 0
    return xp


def xp_progress(total_xp):
    """(levels gained, xp into current level)."""
    return total_xp // XP_PER_LEVEL, total_xp % XP_PER_LEVEL


# ================================================================================================ QUEST BUILDER AND RECAP
# Tuning, not book rules: how much of a level's currency a quest pays (half, three quarters, or all of it, by length). The
# quest.* and recap.* tables (storydata.py) hold the wording.
LENGTHS = {"One-shot (3 scenes)": 3, "Short (4 scenes)": 4, "Full (5 scenes)": 5}
QUEST_OPTIONS = [
    gt.opt("faction", "Client's faction", "choice", "", [], free=True, width=18, hint="blank = none", source="faction"),
    gt.LEVEL_OPT, gt.SIZE_OPT,
    gt.opt("threat", "Fight threat", "choice", "Moderate", ["Low", "Moderate", "Severe"], width=9),
    gt.opt("length", "Length", "choice", "One-shot (3 scenes)", list(LENGTHS), width=18),
    gt.opt("hazard", "Include a hazard", "check", True), gt.opt("social", "Include an influence scene", "check", True),
    gt.opt("reward", "Silly reward", "choice", "Maybe", ["Never", "Maybe", "Always"], width=8),
    gt.SILLY_OPT, gt.FLAVOR_OPT]


# ------------------------------------------------------------------------------------------------ quest
def generate_quest(params, rng=None):
    rng = rng or random.Random()
    rl = gt.Roller(rng, params["silly"], params["flavor"], params.get("level", 1))
    level, size = gt.clamp(params["level"], 1, 20), params["size"]
    n = LENGTHS.get(params["length"], 3)
    title = rl.roll("quest.title")
    rows = [gt.row("Opening", rl.roll("quest.hook.silly"), "flavor", table="quest.hook.silly", fmt="{}")]
    faction = params["faction"].strip()
    job = make_notice(rl, level, size, 1, jobs(rl.reg, faction or None, level, rl.packs))
    hook = job["text"] + (f"\nBacked by: {faction}." if faction else "")
    rows.append(gt.row("The job", hook, "block", player=job["player"] + (f"\nBacked by: {faction}." if faction else ""), tag="job"))
    rows.append(gt.row("Twist", gt.sentence(rl.roll("quest.twist")), "flavor", gm=True, table="quest.twist", fmt="{}"))
    # scenes: the order runs from talking to fighting
    middle = ["explore", "puzzle", "chase"]
    seq = []
    if params["social"]:
        seq.append("social")
    pool = [m for m in middle]
    rng.shuffle(pool)
    while len(seq) < n - 2 - (1 if params["hazard"] else 0):
        seq.append(pool.pop() if pool else rng.choice(middle))
    if params["hazard"]:
        seq.append("hazard")
    seq = seq[:max(0, n - 1)]
    seq.append("combat")
    while len(seq) < n:
        seq.insert(1, rng.choice(middle))
    xp_note = []
    for i, kind in enumerate(seq, 1):
        if kind == "combat":
            text, xp = quest_fight(rl, level, size, params["threat"])
            rows.append(gt.row(f"Scene {i}: fight", text, "block", tag="encounter"))
            xp_note.append(f"fight {xp} XP")
        elif kind == "hazard":
            hz = hazards.build_hazard(rl, {"kind": "Any", "complexity": "Simple", "setting": "Any", "level": level, "offset": "0",
                                   "silly": params["silly"], "flavor": params["flavor"]})
            rows.append(gt.row(f"Scene {i}: hazard", hz["rows"][0]["text"], "block", tag="hazard"))
            xp_note.append("hazard " + hz["rows"][0]["text"].split("XP: ")[1].split(" XP")[0] + " XP")
        elif kind == "social":
            inf = generate_influence({"name": "", "ancestry": "", "occupation": "", "level": level, "size": size, "rounds": 6,
                                      "thresholds": "3", "silly": params["silly"], "flavor": params["flavor"]}, rng)
            body = "\n".join(f"{r['label']}: {r['text']}" for r in inf["rows"] if r["label"] != "Rules reminder")
            rows.append(gt.row(f"Scene {i}: talk ({inf['title'].replace('Influence: ', '')})", body, "block", tag="influence"))
        else:
            rows.append(gt.row(f"Scene {i}: {kind}", gt.sentence(rl.roll("quest.scene." + kind)), "scene", table="quest.scene." + kind, fmt="{}"))
    rows.append(gt.row("Complication", gt.sentence(rl.roll("quest.complication")), "flavor", table="quest.complication", fmt="{}"))
    # reward
    frac = {3: 0.5, 4: 0.75, 5: 1.0}[n]
    coin = currency_for(level, size) * frac
    rwd = [f"Coin: about {gt.money(coin)} (a share of the level {level} party currency).",
           f"Items: the treasure table suggests {permanent_text(level)} per level of play, so one item here is a fair share."]
    show = {"Never": False, "Always": True}.get(params["reward"], rng.random() < 0.55)
    rows.append(gt.row("Reward", "\n".join(rwd), "block", tag="reward"))
    if show:
        d = weird_item(rl, level)
        rows.append(gt.row("Silly reward: " + d["name"], item_text(d), "block", item=d, tag="item"))
    for tag, label in (("good", "If it goes well"), ("mixed", "If it goes halfway"), ("bad", "If it goes badly")):
        rows.append(gt.row(label, gt.sentence(rl.roll("quest.ending." + tag)), "flavor", gm=True, table="quest.ending." + tag, fmt="{}"))
    rows.append(gt.row("Plan the XP", "; ".join(xp_note) + ". Encounter and hazard XP follow the GM Core tables; add accomplishment XP as you see fit.", "info", gm=True))
    return gt.result("quest", f"Quest: {title}", rows, params)


TOOL_QUEST = {"key": "quest", "label": "Quest Builder", "page_type": "Quest", "options": QUEST_OPTIONS, "generate": generate_quest,
              "intro": "A whole quest: a job, scenes, a hazard, an influence NPC, an encounter budget spent exactly, and rewards."}


# ------------------------------------------------------------------------------------------------ session recap
STYLES = {"Epic narrator": "epic", "Gossiping goblin": "gossip", "Tired innkeeper": "innkeeper", "Overly formal notary": "notary"}
RECAP_OPTIONS = [
    gt.opt("title", "Session title", "text", "", width=30),
    gt.opt("number", "Session", "int", 1, width=4),
    gt.opt("style", "Voice", "choice", "Epic narrator", list(STYLES), width=20),
    gt.opt("players", "Player characters", "text", "", width=36, hint="comma separated, used for the awards"),
    gt.opt("notes", "Session notes", "multiline", "", hint="One event per line, as a short sentence. Start a line with [gm], [thread], [loot], [quote] or [npc]; plain lines are what the players know."),
    gt.SILLY_OPT, gt.FLAVOR_OPT]
TAG_RE = re.compile(r"^\s*(?:\[(gm|thread|loot|quote|npc)\]|(gm|thread|loot|quote|npc)\s*:)\s*(.*)$", re.I)


def parse_notes(text):
    out = {"event": [], "gm": [], "thread": [], "loot": [], "quote": [], "npc": []}
    for line in str(text or "").splitlines():
        if not line.strip():
            continue
        m = TAG_RE.match(line)
        if m:
            out[(m.group(1) or m.group(2)).lower()].append(m.group(3).strip())
        else:
            out["event"].append(line.strip().lstrip("-*").strip())
    return out


def generate_recap(params, rng=None):
    rng = rng or random.Random()
    rl = gt.Roller(rng, params["silly"], params["flavor"], params.get("level", 1))
    st = STYLES.get(params["style"], "epic")
    notes = parse_notes(params["notes"] + "\n" + str(params.get("extra", "")))
    title = params["title"].strip() or f"Session {params['number']}"
    rows = []
    if not any(notes.values()):
        rows.append(gt.row("Nothing to recap yet", "Add your session notes, one event per line. Start a line with [gm], [thread], [loot], [quote] or [npc].", "info"))
        return gt.result("recap", f"Recap: {title}", rows, params)
    opening = rl.roll("recap.open." + st)
    lines = [opening + ":"]
    events = notes["event"] + [f"The party met {n}" for n in notes["npc"]]
    for i, ev in enumerate(events):
        ev = ev.rstrip(".!? ")
        if st == "notary":
            lines.append(f"Item {i + 1}: {ev[:1].upper() + ev[1:]}.")
        elif i == 0:
            lines.append(gt.sentence(ev))
        else:                                    # "Then: ..." works for any event, whether it is a full sentence or a fragment
            lines.append(f"{rl.roll('recap.link.' + st)}: {ev[:1].upper() + ev[1:]}.")
    lines.append(rl.roll("recap.close." + st))
    rows.append(gt.row("Previously", " ".join(lines[:1]) + "\n" + "\n".join(lines[1:]), "block", tag="recap"))
    if notes["loot"]:
        rows.append(gt.row("Loot", "\n".join("- " + gt.sentence(x).rstrip(".") for x in notes["loot"]), "block", tag="loot"))
    if notes["quote"]:
        rows.append(gt.row("Quotes of the night", "\n".join(f'- "{q.strip(chr(34))}"' for q in notes["quote"]), "block", tag="quote"))
    pcs = [p.strip() for p in str(params["players"]).split(",") if p.strip()]
    awards = []
    pool = list(pcs)
    rng.shuffle(pool)
    for i in range(min(max(len(pcs), 1), 3)):
        who = pool[i] if i < len(pool) else "the party"
        awards.append(f"{rl.roll('recap.award')} goes to {who}")
    rows.append(gt.row("Awards", "\n".join("- " + a for a in awards), "block", tag="awards"))
    if notes["thread"]:
        rows.append(gt.row("Loose threads", "\n".join("- " + gt.sentence(t) for t in notes["thread"]), "block", gm=True, tag="threads"))
    if notes["gm"]:
        rows.append(gt.row("GM only: what the players do not know", "\n".join("- " + gt.sentence(g) for g in notes["gm"]), "block", gm=True, tag="gm"))
    prep = ["Decide what each loose thread does before next session."] if notes["thread"] else []
    prep += ["Update NPC attitudes and any faction standing that changed.", "Hand out the loot and XP listed above.",
             "Pick one thing from the recap to pay off early next session."]
    rows.append(gt.row("Prep checklist", "\n".join("- " + p for p in prep), "block", gm=True, tag="prep"))
    return gt.result("recap", f"Recap: {title}", rows, params)


TOOL_RECAP = {"key": "recap", "label": "Session Recap", "page_type": "Note", "options": RECAP_OPTIONS, "generate": generate_recap, "single": True,
              "intro": "Turn session notes into a player recap in a voice, plus a GM-only list of loose threads. Keeps what players know apart from secrets."}

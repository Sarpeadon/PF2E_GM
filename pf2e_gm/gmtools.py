"""Shared pieces for the GM Tools generators: job board, salvage and wares, hazards, afflictions, influence, quest builder, recap.

Each generator lives with the part of the app it belongs to (downtime.py, loot.py, hazards.py, npcgen.py, session.py). They
all build a result with row() and result(), so every tool looks the same: a GM view, a Player view, copy, and a Notebook page.

Wording comes from ordinary Story Forge tables, so Edit Tables changes it. Rules numbers come from gmtables.py, rules.py and
quickref.py; nothing is copied here. Two Story Forge conventions are used to keep one table for both settings and all three
silliness levels:

  * Setting. "Hallowmead" turns on the hallowmead content pack and the tag hm. Lines for generic fantasy carry "not hm", so
    they drop out in Hallowmead; Hallowmead lines carry p:hallowmead, so they drop out everywhere else.
  * Silliness. Mild uses the plain lines. Standard also uses lines whose needs say s2. Ridiculous also uses the s3 lines, which
    are weighted to come up more often.
  * A line's payload (what an old "text=>payload" line carried) is a tag written pl:value, with underscores for spaces.
"""
import random
import re

from . import storygen as sg

SILLY_LEVELS = ["Mild", "Standard", "Ridiculous"]
FLAVORS = ["Hallowmead", "Generic fantasy"]


def silly_dial(label):
    return {"mild": 1, "standard": 2, "ridiculous": 3}.get(str(label).strip().lower(), 2)


def flavor_key(label):
    return "hallowmead" if str(label).lower().startswith("hallow") else "generic"


def clamp(n, lo, hi):
    return max(lo, min(hi, n))


# ------------------------------------------------------------------------------------------------ what the app lends us
_REGISTRY = None
_WEIGHTS = None                                    # callable returning your campaign's ancestry mix, or None
_HISTORY = sg.History(strength=0.25, decay=0.85, recent=8)


def configure(registry=None, ancestry_weights=None):
    """The app calls this once: the Story Forge registry (so your Edit Tables changes apply) and your ancestry mix."""
    global _REGISTRY, _WEIGHTS
    if registry is not None:
        _REGISTRY = registry
    if ancestry_weights is not None:
        _WEIGHTS = ancestry_weights


def registry():
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = sg.default_registry()
    return _REGISTRY


def pick_ancestry(rng, flavor="Hallowmead"):
    """An ancestry from your campaign's mix, as names.py spells it ('Goblin', 'Awakened Animal')."""
    from . import names
    weights = _WEIGHTS() if callable(_WEIGHTS) else None
    if flavor_key(flavor) == "hallowmead":
        from .hallowmead import DEMOGRAPHICS
        return names.pick_ancestry(rng, (), weights or DEMOGRAPHICS)
    return names.pick_ancestry(rng, (), None)


def ancestry_choices(flavor="Hallowmead"):
    from . import names
    first = []
    if flavor_key(flavor) == "hallowmead":
        from .hallowmead import DEMOGRAPHICS
        first = list(DEMOGRAPHICS)
    return first + [a for a in names.ANCESTRIES if a not in first]


# ------------------------------------------------------------------------------------------------ text helpers
def article(word):
    return sg.article(str(word).strip())


def sentence(text):
    t = str(text).strip()
    if not t:
        return t
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else t + "."


def lower_first(text):
    t = str(text)
    return t[:1].lower() + t[1:] if t and not t[:2].isupper() else t


def dc(level, adjust="normal"):
    """The DC for a level, plus a named adjustment ('easy', 'hard', 'very hard'...) or a plain number."""
    from .quickref import dc_for
    if isinstance(adjust, int):
        return dc_for(level) + adjust
    return dc_for(level, str(adjust).capitalize())


def money(gp):
    """A price as the books write coins, rounded the way a price is: whole gp for big sums, nearest sp for small ones."""
    from .downtime import coin_text
    cp = int(round(float(gp) * 100))
    if cp >= 2000:
        cp = int(round(cp / 100)) * 100
    elif cp >= 100:
        cp = int(round(cp / 10)) * 10
    return coin_text(cp)


# ------------------------------------------------------------------------------------------------ rolling tables
class Roller:
    """Rolls Story Forge tables for one generation. It carries the silliness dial and the setting, so a table's lines are
    chosen the same way in every tool, and repeats are avoided across generations."""

    def __init__(self, rng=None, silly="Standard", flavor="Hallowmead", level=1, reg=None):
        self.rng = rng or random.Random()
        self.dial = silly_dial(silly)
        self.flavor = flavor_key(flavor)
        self.reg = reg or registry()
        tags = {"hm"} if self.flavor == "hallowmead" else set()
        if self.dial >= 2:
            tags.add("s2")
        if self.dial >= 3:
            tags.add("s3")
        self.packs = ["core"] + (["hallowmead"] if self.flavor == "hallowmead" else [])
        _HISTORY.tick()
        gen = sg.Generator(self.reg, campaign=sg.Campaign(), history=_HISTORY, rng=self.rng)
        self.ctx = sg.Ctx(gen, {"packs": self.packs, "level": int(level), "focus": 0.3, "use_campaign": 0.0}, tags)

    def has(self, table):
        return self.reg.has(table)

    def roll(self, table):
        return self.ctx.roll(table).text

    def payload(self, table):
        """(text, payload) for a line that carries a pl:value tag."""
        r = self.ctx.roll(table)
        pay = next((t[3:].replace("_", " ") for t in sorted(r.tags) if t.startswith("pl:")), "")
        return r.text, pay

    def eligible(self, table):
        """The lines of a table that the dial, the setting and the packs allow right now."""
        return [e["t"] for e in self.reg.entries(table) if self.ctx.weight(e) > 0]

    def choice(self, seq):
        return self.rng.choice(list(seq))

    def chance(self, p):
        return self.rng.random() < p


# ------------------------------------------------------------------------------------------------ options (what each tool asks)
def opt(key, label, kind, default=None, values=None, free=False, width=14, hint="", source=""):
    """One input on a tool tab. kind: choice, int, text, check, multiline. source names a list the app fills in from the
    Notebook and the setting (see choice_values)."""
    return {"key": key, "label": label, "type": kind, "default": default, "values": values or [], "free": free,
            "width": width, "hint": hint, "source": source}


SILLY_OPT = opt("silly", "Silliness", "choice", "Standard", SILLY_LEVELS, width=11)
FLAVOR_OPT = opt("flavor", "Setting", "choice", "Hallowmead", FLAVORS, width=15)
LEVEL_OPT = opt("level", "Party level", "int", 1, width=5)
SIZE_OPT = opt("size", "Party size", "int", 5, width=5)


def merge_params(spec_options, given):
    """Fill in defaults for every option the caller left out, and coerce numbers."""
    out = {}
    for o in spec_options:
        v = (given or {}).get(o["key"], o["default"])
        if o["type"] == "int":
            try:
                v = int(v)
            except (TypeError, ValueError):
                v = int(o["default"] or 0)
        elif o["type"] == "check":
            v = bool(v)
        out[o["key"]] = v
    for k, v in (given or {}).items():              # keep extras such as the recap's imported lines
        out.setdefault(k, v)
    return out


def _page_noun(title):
    t = str(title).strip()
    return "the " + t[4:] if t.lower().startswith("the ") else t


def choice_values(source, flavor="Hallowmead", pages=None, reg=None):
    """The dropdown list for an option with a source. pages is the Notebook (a list of page dicts) or None. 'board' and 'place'
    values are noun phrases, because the tools put them straight into titles ('Job board: the Crossings notice board')."""
    reg = reg or registry()
    fk = flavor_key(flavor)
    packs = ["core"] + (["hallowmead"] if fk == "hallowmead" else [])

    def lines(table):
        out = []
        for e in reg.entries(table):
            if e.get("off") or e["pack"] not in packs or "{" in e["t"] or (fk == "hallowmead" and "hm" in e["not"]):
                continue
            out.append(e["t"])
        return out

    def seen(seq):
        done, out = set(), []
        for item in seq:
            item = str(item).strip()
            if item and item.lower() not in done:
                done.add(item.lower())
                out.append(item)
        return out

    places = [_page_noun(p["title"]) for p in pages or [] if isinstance(p, dict) and p.get("title")
              and p.get("type") in ("Location", "Faction") and "gm-only" not in (p.get("tags") or [])]
    if source == "board":
        default = "the Crossings notice board" if fk == "hallowmead" else "the village notice board"
        return seen([default] + [f"{x} notice board" for x in places]
                    + [f"{x} notice board" for x in lines("place") if x.lower().startswith("the ") and len(x) <= 32])
    if source == "place":
        return seen(lines("salvage.where") + places)
    if source == "ancestry":
        return ancestry_choices(flavor)
    if source == "occupation":
        return seen(lines("occupation"))
    if source == "faction":
        return seen([str(p["title"]).strip() for p in pages or [] if isinstance(p, dict) and p.get("type") == "Faction"
                     and p.get("title") and "gm-only" not in (p.get("tags") or [])])
    return []


# ------------------------------------------------------------------------------------------------ results
def row(label, text, kind="", gm=False, player=None, **extra):
    """One line of a result. gm=True hides it from the player view. player is alternate text for the player view."""
    d = {"label": label, "text": text, "kind": kind, "gm": bool(gm), "player": player, "locked": False}
    d.update(extra)
    return d


def result(tool, title, rows, params=None, **extra):
    d = {"tool": tool, "title": title, "rows": rows, "params": dict(params or {})}
    d.update(extra)
    return d


def _view(res, audience):
    if audience == "gm":
        return res["rows"]
    return [dict(r, text=(r["player"] if r.get("player") is not None else r["text"])) for r in res["rows"] if not r.get("gm")]


def render_text(res, audience="gm"):
    """Plain text for the detail box and for copying. audience is 'gm' or 'player'."""
    lines = [res["title"]]
    for r in _view(res, audience):
        if r.get("kind") == "block":
            if lines and lines[-1] != "":
                lines.append("")
            lines += [r["label"], r["text"], ""]
        elif r["label"]:
            lines.append(f"{r['label']}: {r['text']}")
        else:
            lines.append(r["text"])
    return "\n".join(lines).strip()


def render_markdown(res, audience="gm"):
    lines = [f"## {res['title']}", ""]
    for r in _view(res, audience):
        tag = " (GM only)" if r.get("gm") and audience == "gm" else ""
        if r.get("kind") == "block":
            lines += [f"### {r['label']}{tag}", "", r["text"].replace("\n", "  \n"), ""]
        elif r["label"]:
            lines.append(f"- **{r['label']}{tag}:** {r['text']}")
        else:
            lines.append(r["text"])
    return "\n".join(lines).strip() + "\n"


# ------------------------------------------------------------------------------------------------ the tools
def specs():
    """Every tool, in tab order. Imported here so the generator modules can import this one."""
    from . import downtime, hazards, loot, npcgen, session
    return [downtime.TOOL_JOBS, loot.TOOL_SALVAGE, hazards.TOOL_AFFLICTIONS, hazards.TOOL_HAZARDS, npcgen.TOOL_INFLUENCE,
            session.TOOL_QUEST, session.TOOL_RECAP]


def spec(tool):
    return next(s for s in specs() if s["key"] == tool)


def generate(tool, params, rng=None):
    s = spec(tool)
    return s["generate"](merge_params(s["options"], params), rng or random.Random())


def reroll_row(res, index, rng=None):
    """Replace one row of a result with a fresh one. Rows that name a table roll it again. Block rows are rebuilt by running the
    whole tool again and taking a row of the same kind, so the neighbors stay put. Returns True when something changed."""
    rng = rng or random.Random()
    s = spec(res["tool"])
    params = merge_params(s["options"], res.get("params"))
    old = res["rows"][index]
    if old.get("table"):
        rl = Roller(rng, params.get("silly", "Standard"), params.get("flavor", "Hallowmead"), params.get("level", 1))
        res["rows"][index] = dict(old, text=old.get("fmt", "{}").format(rl.roll(old["table"])), locked=old.get("locked", False))
        return True
    for _ in range(12):
        fresh = s["generate"](params, rng)
        cands = [r for r in fresh["rows"] if r.get("tag") == old.get("tag") and r.get("kind") == old.get("kind")
                 and (old.get("tag") in ("job", "item", "encounter", "hazard", "influence", "affliction", "find")
                      or r["label"].split(":")[0] == old["label"].split(":")[0])]
        if not cands and old.get("kind", "").startswith("find"):
            cands = [r for r in fresh["rows"] if r.get("kind") == old.get("kind")]
        if cands:
            new = dict(rng.choice(cands))
            if old.get("tag") == "job" and re.match(r"^\d+\. ", old["label"]) and re.match(r"^\d+\. ", new["label"]):
                new["label"] = old["label"].split(".")[0] + "." + new["label"].split(".", 1)[1]
            elif old.get("tag") in ("job", "encounter", "hazard", "influence", "item") and ":" not in old["label"]:
                new["label"] = old["label"]
            new["locked"] = old.get("locked", False)
            res["rows"][index] = new
            return True
    return False

"""Stat blocks and rules entries built from Foundry pf2e documents, with clickable references.

Text is stored with inline link markers:  \x01label\x1fref\x02
A ref is "<kind>:<value>", for example:
    uuid:<foundry id>|<label>    from @UUID enrichers in descriptions
    trait:<slug>                 trait descriptions (from Foundry's language files)
    name:<text>                  any rules entry by name (conditions, abilities, senses...)
    item:/spell:/feat:<name>     name lookup that prefers that kind
    self:<ability name>          jump to an ability in the same stat block
render() returns [(text, style, ref)] segments; the GUI decides which refs are clickable.
"""
import html
import json
import math
import re
import sqlite3
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

ACTION_GLYPH = {"1": "[1]", "2": "[2]", "3": "[3]", "reaction": "[R]", "free": "[F]"}
PHYSICAL = {"weapon", "armor", "shield", "equipment", "consumable", "backpack", "ammo", "treasure"}
KIND_PRIO = {"condition": 0, "action": 1, "spell": 2, "trait": 3, "feat": 4, "item": 5, "ancestry": 6}

LS, SEP, LE = "\x01", "\x1f", "\x02"
MARK = re.compile("\x01([^\x1f\x02]*)\x1f([^\x02]*)\x02")
CAST_SEP = "||cast:"

# Conditions that get auto-linked in plain text even when the source didn't tag them.
CONDITIONS = ["off-guard", "flat-footed", "persistent damage", "blinded", "clumsy", "concealed", "confused",
              "controlled", "dazzled", "deafened", "doomed", "drained", "dying", "encumbered", "enfeebled",
              "fascinated", "fatigued", "fleeing", "frightened", "grabbed", "hidden", "immobilized",
              "invisible", "paralyzed", "petrified", "prone", "quickened", "restrained", "sickened", "slowed",
              "stunned", "stupefied", "unconscious", "undetected", "unnoticed", "wounded"]
COND_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in CONDITIONS) + r")\b", re.IGNORECASE)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def link(label, ref):
    return f"{LS}{label}{SEP}{ref}{LE}"


def strip_links(s):
    return MARK.sub(lambda m: m.group(1), s or "")


def _titleize(slug):
    return str(slug).replace("-", " ").replace("_", " ").strip().title()


# ---------- text cleanup ----------
# GM Core "DCs by level": the standard-difficulty DC for a level (used where Foundry's data says 'a DC based on your level')
DC_BY_LEVEL = {-1: 13, 0: 14, 1: 15, 2: 16, 3: 18, 4: 19, 5: 20, 6: 22, 7: 23, 8: 24, 9: 26, 10: 27, 11: 28, 12: 30, 13: 31,
               14: 32, 15: 34, 16: 35, 17: 36, 18: 38, 19: 39, 20: 40, 21: 42, 22: 44, 23: 46, 24: 48, 25: 50}
_LEVEL_FORMULA = re.compile(r"^\s*(?:resolve\(\s*)?@(?:self|actor)\.(?:system\.details\.)?level(?:\.value)?\s*\)?\s*$", re.I)
# a value Foundry computes from the character: @self.level, @actor.level, @item.level, @actor.abilities.int.mod ...
FORMULA_REF = re.compile(r"@(?:self|actor|item)\.[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", re.I)       # never swallows a trailing period
_DC_LEVEL = re.compile(r"\bDC (?:resolve\(\s*@(?:self|actor)\.(?:system\.details\.)?level(?:\.value)?\s*\)"
                       r"|@(?:self|actor)\.(?:system\.details\.)?level(?:\.value)?)", re.I)


def dc_for_level(level):
    try:
        return DC_BY_LEVEL[max(-1, min(25, int(level)))]
    except (TypeError, ValueError):
        return None


def resolve_refs(text, level=None):
    """Replace Foundry's computed values in rules text with something a person can read.

    'DC @self.level' (Foundry's 'a standard-difficulty DC for your level') becomes the GM Core DC for the character's
    level when it is known, otherwise 'DC for your level'. Any other reference to the character's level becomes the
    level itself (or 'your level'), an item's level or rank becomes plain words, and an ability modifier names the
    ability. Nothing starting with @ is ever left in the text."""
    if not text or "@" not in text:
        return text or ""
    dc = dc_for_level(level)
    t = _DC_LEVEL.sub(lambda m: f"DC {dc}" if dc is not None else "level-based DC", text)

    def other(m):
        ref = m.group(0).lower()
        if re.search(r"\.(?:details\.)?level(?:\.value)?$", ref) and ref.startswith(("@self.", "@actor.")):
            return str(level) if level is not None else "your level"
        if ref.startswith("@item.") and ref.endswith(".level"):
            return "the item's level"
        if ref.endswith(".rank") or ".rank" in ref:
            return "the spell's rank"
        ab = re.search(r"abilities\.(str|dex|con|int|wis|cha)\.mod", ref)
        if ab:
            return f"your {ab.group(1).title()} modifier"
        return "a value from the character sheet"
    return FORMULA_REF.sub(other, t)


ENRICHER = re.compile(r"@(\w+)\[((?:[^\[\]]|\[[^\[\]]*\])*)\](?:\{([^}]*)\})?")
INLINE_ROLL = re.compile(r"\[\[/\w+ ([^\]]*?)(?: #[^\]]*)?\]\](?:\{([^}]*)\})?")


def _enricher(m, links):
    kind, body, label = m.group(1), m.group(2), m.group(3)
    if kind in ("UUID", "Compendium"):
        seg = body.rsplit(".", 1)[-1]
        lab = label or seg
        return link(lab, f"uuid:{seg}|{lab}") if links else lab
    if label:
        return label
    params = body.split("|")
    if kind == "Check":
        check = _titleize(params[0].split(":")[-1])
        dc = next((p.split(":", 1)[1] for p in params[1:] if p.startswith("dc:")), "")
        if dc and not dc.strip().lstrip("-").isdigit():
            # a formula, not a number: a level-based DC is kept as a token the stat block resolves for the character;
            # anything else is left out so the text reads "Attempt a Crafting check" instead of showing code
            dc = "@self.level" if _LEVEL_FORMULA.match(dc) else ""
        basic = any(p in ("basic", "basic:true") for p in params[1:])
        return f"{'DC ' + dc + ' ' if dc else ''}{'basic ' if basic else ''}{check}".strip()
    if kind == "Damage":
        expr = re.sub(r"\[([a-z,]+)\]", lambda x: " " + x.group(1).replace(",", " "), params[0])
        return expr.replace("(", "").replace(")", "")
    if kind == "Template":
        shape = dist = ""
        for p in params:
            k, _, v = p.partition(":")
            if k in ("type", "shape"):
                shape = v
            elif k == "distance":
                dist = v
            elif not v and k.lower() in ("burst", "cone", "line", "emanation"):
                shape = k
        return f"{dist}-foot {shape}".strip("- ")
    return params[0]


class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "hr", "li", "h1", "h2", "h3", "h4", "tr", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.out.append("\n• ")
        elif tag == "hr":
            self.out.append("\n---\n")
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK and tag != "li":
            self.out.append("\n")

    def handle_data(self, data):
        self.out.append(data)


def clean_text(raw, links=True):
    if not raw:
        return ""
    s = ENRICHER.sub(lambda m: _enricher(m, links), raw)
    s = INLINE_ROLL.sub(lambda m: m.group(2) or m.group(1), s)
    p = _Text()
    p.feed(s)
    text = html.unescape("".join(p.out))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------- creature extraction ----------
def _g(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def _sign(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    return f"+{n}" if n >= 0 else str(n)


def _iwr(entries, with_value=True):
    """[(display, ref)]"""
    out = []
    for e in entries or []:
        if isinstance(e, str):
            out.append((_titleize(e), f"name:{e}")); continue
        slug = e.get("type", "")
        v = e.get("value")
        exc = e.get("exceptions") or []
        s = f"{_titleize(slug)} {v}" if with_value and v is not None else _titleize(slug)
        if exc:
            names = [_titleize(x if isinstance(x, str) else x.get("label", x.get("type", ""))) for x in exc]
            s += f" (except {', '.join(names)})"
        out.append((s, f"name:{slug}"))
    return out


def _speeds(s):
    parts = []
    mv = _g(s, "movement", "speeds")
    if isinstance(mv, dict):
        for k, v in mv.items():
            val = v.get("value") if isinstance(v, dict) else v
            if val:
                parts.append(f"{val} feet" if k == "land" else f"{k} {val} feet")
        return ", ".join(parts)
    sp = _g(s, "attributes", "speed", default={}) or {}
    if sp.get("value"):
        parts.append(f"{sp['value']} feet")
    for o in sp.get("otherSpeeds", []) or []:
        parts.append(f"{o.get('type', o.get('label', ''))} {o.get('value')} feet")
    if sp.get("details"):
        parts.append(sp["details"])
    return ", ".join(parts)


def _senses(s):
    """[(display, ref)]"""
    sen = _g(s, "perception", "senses")
    if isinstance(sen, list):
        out = []
        for x in sen:
            t = _titleize(x.get("type", ""))
            extra = ""
            if x.get("acuity") and x["acuity"] != "precise":
                extra += f" ({x['acuity']})"
            if x.get("range"):
                extra += f" {x['range']} feet"
            out.append((t + extra, f"name:{x.get('type', '')}"))
        return out
    legacy = _g(s, "traits", "senses", "value", default="") or ""
    return [(legacy, None)] if legacy else []


def _source_id(it):
    src = _g(it, "_stats", "compendiumSource") or _g(it, "flags", "core", "sourceId") or ""
    return src.rsplit(".", 1)[-1] if src else ""


def _strike(it):
    s = it.get("system", {})
    dmg = [f"{r.get('damage', '')} {r.get('damageType', '')}".strip()
           for r in (_g(s, "damageRolls", default={}) or {}).values()]
    traits = _g(s, "traits", "value", default=[]) or []
    ranged = any(t.startswith(("range", "thrown")) for t in traits) or _g(s, "weaponType", "value") == "ranged"
    return {"name": it["name"], "bonus": _sign(_g(s, "bonus", "value", default=0)), "traits": traits,
            "damage": dmg, "effects": _g(s, "attackEffects", "value", default=[]) or [],
            "kind": "Ranged" if ranged else "Melee"}


def _action(it):
    s = it.get("system", {})
    at = _g(s, "actionType", "value", default="passive")
    glyph = "" if at == "passive" else (ACTION_GLYPH.get(at) or ACTION_GLYPH.get(str(_g(s, "actions", "value", default="")), ""))
    return {
        "name": it["name"], "glyph": glyph, "traits": _g(s, "traits", "value", default=[]) or [],
        "category": s.get("category") or ("defensive" if at in ("reaction", "free") else "offensive" if at == "action" else "interaction"),
        "text": clean_text(_g(s, "description", "value", default="")),
    }


def _spells(items):
    entries = {}
    for it in items:
        if it.get("type") == "spellcastingEntry":
            s = it.get("system", {})
            entries[it.get("_id")] = {"name": it["name"], "dc": _g(s, "spelldc", "dc"),
                                      "attack": _g(s, "spelldc", "value"), "ranks": {}}
    for it in items:
        if it.get("type") != "spell":
            continue
        s = it.get("system", {})
        e = entries.get(_g(s, "location", "value"))
        if not e:
            continue
        traits = _g(s, "traits", "value", default=[]) or []
        rank = _g(s, "location", "heightenedLevel") or _g(s, "level", "value", default=1)
        key = "Cantrips" if "cantrip" in traits else ("Rituals" if s.get("ritual") else f"Rank {rank}")
        uses = _g(s, "location", "uses", "max")
        suffix = f" (x{uses})" if uses and uses > 1 else ""
        sid = _source_id(it)
        ref = f"uuid:{sid}|{it['name']}" if sid else f"spell:{it['name']}"
        e["ranks"].setdefault(key, []).append([it["name"], ref, suffix])

    def order(k):
        return (2, 0) if k == "Cantrips" else (3, 0) if k == "Rituals" else (1, -int(k.split()[1]))
    out = []
    for e in entries.values():
        if not e["ranks"]:
            continue
        bits = ([f"DC {e['dc']}"] if e["dc"] else []) + ([f"attack {_sign(e['attack'])}"] if e["attack"] else [])
        head = e["name"] + (" " + ", ".join(bits) if bits else "")
        ranks = [[k, sorted(v)] for k, v in sorted(e["ranks"].items(), key=lambda kv: order(kv[0]))]
        out.append({"head": head, "ranks": ranks})
    return out


def build_details(doc):
    s = doc.get("system", {})
    items = doc.get("items", []) or []
    perc = _g(s, "perception", "mod")
    if perc is None:
        perc = _g(s, "attributes", "perception", "value")
    langs = _g(s, "details", "languages", "value") or _g(s, "traits", "languages", "value") or []
    skills = []
    sk = s.get("skills")
    if isinstance(sk, dict):
        skills = [f"{_titleize(k)} {_sign(v.get('base', v.get('value')))}" for k, v in sorted(sk.items()) if isinstance(v, dict)]
    skills += [f"{it['name']} {_sign(_g(it, 'system', 'mod', 'value'))}" for it in items if it.get("type") == "lore"]
    abil = s.get("abilities", {}) or {}
    hp = _g(s, "attributes", "hp", default={}) or {}
    return {
        "name": doc.get("name", ""),
        "level": _g(s, "details", "level", "value"),
        "rarity": _g(s, "traits", "rarity", default="common"),
        "size": _g(s, "traits", "size", "value", default=""),
        "traits": _g(s, "traits", "value", default=[]) or [],
        "source": _g(s, "details", "publication", "title") or _g(s, "publication", "title") or _g(s, "details", "source", "value") or "",
        "blurb": clean_text(_g(s, "details", "blurb", default="")),
        "perception": _sign(perc) if perc is not None else "",
        "senses": _senses(s),
        "languages": ", ".join(_titleize(x) for x in langs) if isinstance(langs, list) else str(langs),
        "skills": ", ".join(skills),
        "abilities": ", ".join(f"{k.title()} {_sign(_g(abil, k, 'mod'))}" for k in ("str", "dex", "con", "int", "wis", "cha") if k in abil),
        "gear": [it["name"] for it in items if it.get("type") in PHYSICAL],
        "ac": _g(s, "attributes", "ac", "value"),
        "saves": ", ".join(f"{n} {_sign(_g(s, 'saves', k, 'value'))}" for k, n in
                           (("fortitude", "Fort"), ("reflex", "Ref"), ("will", "Will")) if _g(s, "saves", k) is not None),
        "hp": hp.get("max"),
        "hp_details": hp.get("details", ""),
        "immunities": _iwr(_g(s, "attributes", "immunities"), with_value=False),
        "weaknesses": _iwr(_g(s, "attributes", "weaknesses")),
        "resistances": _iwr(_g(s, "attributes", "resistances")),
        "speed": _speeds(s),
        "strikes": [_strike(it) for it in items if it.get("type") == "melee"],
        "spells": _spells(items),
        "actions": [_action(it) for it in items if it.get("type") == "action"],
        "description": clean_text(_g(s, "details", "publicNotes", default="")),
    }


def build_hazard_details(doc):
    """Stat block data for a Foundry hazard."""
    s = doc.get("system", {})
    items = doc.get("items", []) or []
    traits = _g(s, "traits", "value", default=[]) or []
    stealth = _g(s, "attributes", "stealth", "value")
    hp = _g(s, "attributes", "hp", default={}) or {}
    hardness = _g(s, "attributes", "hardness")
    if isinstance(hardness, dict):
        hardness = hardness.get("value")
    return {
        "kind": "hazard",
        "name": doc.get("name", ""),
        "level": _g(s, "details", "level", "value"),
        "rarity": _g(s, "traits", "rarity", default="common"),
        "traits": traits,
        "complex": bool(_g(s, "details", "isComplex")) or "complex" in traits,
        "source": _g(s, "details", "publication", "title") or _g(s, "publication", "title") or "",
        "stealth": stealth,
        "stealth_details": clean_text(_g(s, "attributes", "stealth", "details", default="")),
        "description": clean_text(_g(s, "details", "description", default="")),
        "disable": clean_text(_g(s, "details", "disable", default="")),
        "routine": clean_text(_g(s, "details", "routine", default="")),
        "reset": clean_text(_g(s, "details", "reset", default="")),
        "ac": _g(s, "attributes", "ac", "value"),
        "saves": ", ".join(f"{n} {_sign(_g(s, 'saves', k, 'value'))}" for k, n in
                           (("fortitude", "Fort"), ("reflex", "Ref"), ("will", "Will"))
                           if _g(s, "saves", k, "value") is not None),
        "hardness": hardness,
        "hp": hp.get("max"),
        "bt": hp.get("brokenThreshold"),
        "immunities": _iwr(_g(s, "attributes", "immunities"), with_value=False),
        "weaknesses": _iwr(_g(s, "attributes", "weaknesses")),
        "resistances": _iwr(_g(s, "attributes", "resistances")),
        "strikes": [_strike(it) for it in items if it.get("type") == "melee"],
        "actions": [_action(it) for it in items if it.get("type") == "action"],
    }


def _custom_strikes(text):
    """One Strike per line:  Name | +15 | 2d6+6 piercing, 1d6 fire | traits | effects"""
    out = []
    for line in (text or "").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if not parts or not parts[0]:
            continue
        parts += [""] * (5 - len(parts))
        name, bonus, dmg, traits, effects = parts[:5]
        tr = [t.strip() for t in traits.split(",") if t.strip()]
        if bonus and bonus[0] not in "+-":
            bonus = "+" + bonus
        out.append({"name": name, "bonus": bonus or "?", "traits": tr,
                    "damage": [x.strip() for x in dmg.split(",") if x.strip()],
                    "effects": [e.strip() for e in effects.split(",") if e.strip()],
                    "kind": "Ranged" if any(t.lower().startswith(("range", "thrown")) for t in tr) else "Melee"})
    return out


def _custom_spells(text):
    """One casting entry per line:  Primal Innate Spells DC 20, attack +12; Rank 2: Entangle; Cantrips: Tangle Vine"""
    out = []
    for line in (text or "").splitlines():
        parts = [p.strip() for p in line.split(";") if p.strip()]
        if not parts:
            continue
        ranks = []
        for p in parts[1:]:
            label, _, names = p.partition(":")
            spells = []
            for n in names.split(","):
                n = n.strip()
                if not n:
                    continue
                m = re.match(r"^(.*?)\s*(\(x\d+\))$", n)
                nm, suffix = (m.group(1), " " + m.group(2)) if m else (n, "")
                spells.append([nm, f"spell:{nm}", suffix])
            ranks.append([label.strip(), spells])
        out.append({"head": parts[0], "ranks": ranks})
    return out


def _pairs(text):
    """'scent (imprecise) 30 feet, fire 5' -> [(display, 'name:scent'), (display, 'name:fire')]"""
    out = []
    for t in (text or "").split(","):
        t = t.strip()
        if not t:
            continue
        key = re.sub(r"\s*(\([^)]*\)|\b\d+\b|\bfeet\b)", " ", t)
        out.append((t, f"name:{' '.join(key.split()) or t}"))
    return out


def custom_details(c):
    st = c.stats or {}

    def sign(k):
        v = st.get(k)
        return _sign(v) if v not in (None, "") else None
    saves = [f"{n} {sign(k)}" for k, n in (("fort", "Fort"), ("ref", "Ref"), ("will", "Will")) if sign(k)]
    return {
        "name": c.name, "level": c.level, "rarity": c.rarity, "size": c.size, "traits": c.traits,
        "source": c.source, "ac": c.ac, "hp": c.hp,
        "perception": sign("perception") or "",
        "senses": _pairs(st.get("senses")),
        "languages": st.get("languages", ""),
        "skills": st.get("skills", ""),
        "saves": ", ".join(saves),
        "immunities": _pairs(st.get("immunities")),
        "weaknesses": _pairs(st.get("weaknesses")),
        "resistances": _pairs(st.get("resistances")),
        "speed": st.get("speed", ""),
        "gear": [g.strip() for g in str(st.get("gear") or "").splitlines() if g.strip()],   # one item per line (names may hold commas)
        "trappings": [g.strip() for g in str(st.get("trappings") or "").splitlines() if g.strip()],
        "strikes": _custom_strikes(st.get("strikes")),
        "spells": _custom_spells(st.get("spells")),
        "actions": parse_abilities(st.get("abilities")),
        "description": c.notes,
    }


ABIL_RE = re.compile(r"^\s*([^:\[\(\n]+?)\s*(\[(?:1|2|3|R|F)\])?\s*(?:\(([^)]*)\))?\s*:\s*(.*)$")


def parse_abilities(text):
    """One ability per line:  Name [2] (trait, trait): rules text
    [1]/[2]/[3] = actions (offensive), [R]/[F] = reaction/free (defensive), no glyph = passive."""
    out = []
    for line in (text or "").splitlines():
        m = ABIL_RE.match(line)
        if not m:
            if out and line.strip():               # continuation line
                out[-1]["text"] += "\n" + line.strip()
            continue
        name, glyph, traits, body = m.groups()
        cat = "defensive" if glyph in ("[R]", "[F]") else "offensive" if glyph else "interaction"
        out.append({"name": name.strip(), "glyph": glyph or "", "category": cat, "text": body.strip(),
                    "traits": [t.strip() for t in (traits or "").split(",") if t.strip()]})
    return out


def ability_line(a):
    """Inverse of parse_abilities for one ability dict."""
    head = a["name"] + (f" {a['glyph']}" if a.get("glyph") else "")
    if a.get("traits"):
        head += f" ({', '.join(a['traits'])})"
    return f"{head}: {strip_links(a.get('text', '')).replace(chr(10), ' ').strip()}"


def details_to_custom(d, name=None, source="Hallowmead"):
    """Turn any stat block dict (official or custom) into editable custom-creature fields.

    Returns kwargs for models.Creature (custom=True). Used by Duplicate to Custom.
    """
    def names(pairs):
        return ", ".join(p[0] if isinstance(p, (list, tuple)) else str(p) for p in (pairs or []))

    def save(key):
        m = re.search(key + r" ([+-]\d+)", d.get("saves") or "")
        return int(m.group(1)) if m else None
    strikes = []
    for st in d.get("strikes") or []:
        if isinstance(st, dict):
            strikes.append(" | ".join([st["name"], st.get("bonus", ""), ", ".join(st.get("damage") or []),
                                       ", ".join(st.get("traits") or []),
                                       ", ".join(_titleize(e) for e in st.get("effects") or [])]))
    spells = []
    for sp in d.get("spells") or []:
        if isinstance(sp, dict):
            parts = [sp["head"]] + [f"{rank}: " + ", ".join(nm + suf for nm, _, suf in lst) for rank, lst in sp["ranks"]]
            spells.append("; ".join(parts))
    per = str(d.get("perception") or "").strip()
    stats = {
        "perception": int(per) if re.fullmatch(r"[+-]?\d+", per) else None,
        "senses": names(d.get("senses")), "languages": d.get("languages", ""), "skills": d.get("skills", ""),
        "fort": save("Fort"), "ref": save("Ref"), "will": save("Will"),
        "immunities": names(d.get("immunities")), "weaknesses": names(d.get("weaknesses")),
        "resistances": names(d.get("resistances")), "speed": d.get("speed", ""),
        "strikes": "\n".join(strikes), "spells": "\n".join(spells),
        "abilities": "\n".join(ability_line(a) for a in d.get("actions") or []),
        "trappings": "\n".join(d.get("trappings") or []),
    }
    stats = {k: v for k, v in stats.items() if v not in (None, "")}
    desc = strip_links(d.get("description") or "")
    return dict(name=name or d["name"], level=d.get("level") or 0, rarity=d.get("rarity") or "common",
                traits=list(d.get("traits") or []), size=d.get("size") or "", hp=d.get("hp"), ac=d.get("ac"),
                source=source, notes=desc, custom=True, stats=stats)


# ---------- rules entries (conditions, spells, actions, feats, items, traits) ----------
def _price(p):
    if not isinstance(p, dict):
        return ""
    return ", ".join(f"{p[k]} {k}" for k in ("pp", "gp", "sp", "cp") if p.get(k))


def _spell_damage(s):
    """[[key, formula, type]] from a spell's system.damage."""
    out = []
    dmg = s.get("damage")
    if isinstance(dmg, dict):
        for k, v in dmg.items():
            if isinstance(v, dict) and v.get("formula"):
                out.append([k, str(v["formula"]), v.get("type") or v.get("damageType") or ""])
    return out


def _spell_heightening(s):
    h = s.get("heightening")
    if not isinstance(h, dict):
        return None
    if h.get("type") == "interval":
        dmg = {k: str(v) for k, v in (h.get("damage") or {}).items() if v}
        return {"type": "interval", "interval": int(h.get("interval") or 1), "damage": dmg}
    if h.get("type") == "fixed":
        levels = {}
        for rank, data in (h.get("levels") or {}).items():
            d = (data or {}).get("damage") or {}
            d = d.get("value", d) if isinstance(d, dict) else {}
            forms = {k: str(v.get("formula")) for k, v in d.items() if isinstance(v, dict) and v.get("formula")}
            try:
                levels[int(rank)] = forms
            except ValueError:
                continue
        return {"type": "fixed", "levels": levels}
    return None


def build_rule(doc):
    """Return (id, norm name, kind, data) for a rules document, or None."""
    t, name = doc.get("type"), doc.get("name")
    kind = {"condition": "condition", "spell": "spell", "action": "action", "feat": "feat",
            "ancestry": "ancestry"}.get(t) \
        or ("item" if t in PHYSICAL else None)
    if not kind or not name:
        return None
    s = doc.get("system", {})
    traits = _g(s, "traits", "value", default=[]) or []
    lvl = _g(s, "level", "value")
    meta, glyph = [], ""
    extra = {}
    if kind == "spell":
        header = ("Cantrip" if "cantrip" in traits else "Focus" if "focus" in traits else "Spell") + f" {lvl}"
        cast = str(_g(s, "time", "value", default="") or "")
        glyph = ACTION_GLYPH.get(cast, "")
        if cast and not glyph:
            meta.append(["Cast", cast])
        if _g(s, "range", "value"):
            meta.append(["Range", _g(s, "range", "value")])
        area = s.get("area")
        if isinstance(area, dict) and area.get("value"):
            meta.append(["Area", f"{area['value']}-foot {area.get('type', '')}".strip()])
        if _g(s, "target", "value"):
            meta.append(["Targets", _g(s, "target", "value")])
        save = _g(s, "defense", "save") or {}
        if save.get("statistic"):
            meta.append(["Defense", ("basic " if save.get("basic") else "") + _titleize(save["statistic"])])
        elif _g(s, "defense", "passive", "statistic"):
            meta.append(["Defense", _g(s, "defense", "passive", "statistic").upper()])
        dur = _g(s, "duration", "value")
        if dur:
            meta.append(["Duration", ("sustained up to " if _g(s, "duration", "sustained") else "") + dur])
        extra = {"spell_rank": lvl if isinstance(lvl, int) else None, "cantrip": "cantrip" in traits,
                 "traditions": [str(t).lower() for t in (_g(s, "traits", "traditions", default=[]) or [])],
                 "ritual": bool(s.get("ritual")),
                 "damage": _spell_damage(s), "heightening": _spell_heightening(s)}
    elif kind == "feat":
        header = f"Feat {lvl}" if lvl is not None else "Feat"
        pre = [p.get("value") for p in _g(s, "prerequisites", "value", default=[]) or [] if isinstance(p, dict)]
        if pre:
            meta.append(["Prerequisites", ", ".join(x for x in pre if x)])
        at = _g(s, "actionType", "value")
        glyph = "" if at in (None, "passive") else ACTION_GLYPH.get(at) or ACTION_GLYPH.get(str(_g(s, "actions", "value", default="")), "")
    elif kind == "item":
        header = f"Item {lvl}" if lvl is not None else "Item"
        if _price(_g(s, "price", "value")):
            meta.append(["Price", _price(_g(s, "price", "value"))])
        bulk = _g(s, "bulk", "value", default=_g(s, "weight", "value"))
        if bulk is not None:
            meta.append(["Bulk", "L" if bulk in (0.1, "L") else "-" if bulk in (0, "-", "") else str(bulk)])
        if _g(s, "usage", "value"):
            meta.append(["Usage", _titleize(_g(s, "usage", "value"))])
        if t == "weapon":
            dmg = s.get("damage") if isinstance(s.get("damage"), dict) else {}
            if dmg.get("die"):
                meta.append(["Damage", f"{dmg.get('dice', 1)}{dmg['die']} {dmg.get('damageType', '')}".strip()])
            rng = s.get("range")
            if isinstance(rng, (int, float)) and rng:
                meta.append(["Range", f"{int(rng)} feet"])
            if s.get("group"):
                meta.append(["Group", _titleize(s["group"])])
            splash = s.get("splashDamage")
            pers = dmg.get("persistent")
            extra = {"weapon_range": int(rng) if isinstance(rng, (int, float)) and rng else None,
                     "weapon_damage": {"dice": dmg.get("dice"), "die": dmg.get("die"),
                                       "type": dmg.get("damageType") or "",
                                       "persistent": pers if isinstance(pers, dict) else None,
                                       "splash": (splash.get("value") if isinstance(splash, dict) else splash)
                                       if isinstance(splash, (dict, int)) and splash else None}}
    elif kind == "action":
        header = "Action"
        at = _g(s, "actionType", "value")
        glyph = "" if at in (None, "passive") else ACTION_GLYPH.get(at) or ACTION_GLYPH.get(str(_g(s, "actions", "value", default="")), "")
    elif kind == "ancestry":
        header = "Ancestry"
        for label, val in (("Hit Points", s.get("hp")), ("Size", _titleize(_g(s, "size", default="") or "")),
                           ("Speed", f"{s.get('speed')} feet" if s.get("speed") else "")):
            if val:
                meta.append([label, val])
    else:
        header = "Condition"
    data = {"name": name, "kind": kind, "header": header, "glyph": glyph, "traits": traits,
            "rarity": _g(s, "traits", "rarity", default="common"),
            "source": _g(s, "publication", "title") or _g(s, "source", "value") or "",
            "meta": meta, "text": clean_text(_g(s, "description", "value", default=""))}
    data.update(extra)
    return doc.get("_id") or f"{kind}:{norm(name)}", norm(name), kind, data


def _walk_traits(d):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _walk_traits(v)
        elif isinstance(v, str) and k.startswith("TraitDescription") and len(k) > 16:
            yield k[16:], v


def trait_rules(lang_dir):
    """Trait descriptions from Foundry's English language files."""
    out = []
    lang_dir = Path(lang_dir)
    if not lang_dir.is_dir():
        return out
    for p in sorted(lang_dir.glob("*.json")):   # later files (e.g. re-en.json) override earlier ones
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        for key, text in _walk_traits(d):
            display = re.sub(r"(?<!^)(?=[A-Z])", " ", key)
            data = {"name": display, "kind": "trait", "header": "Trait", "glyph": "", "traits": [],
                    "rarity": "common", "source": "", "meta": [], "text": clean_text(text)}
            out.append((f"trait:{norm(key)}", norm(key), "trait", data))
    return out


# ---------- spell casting context and heightening ----------
def _cast_rank(rank_label, creature_level):
    label = str(rank_label or "")
    if label.lower().startswith("cantrip"):
        try:
            return max(1, math.ceil(int(creature_level) / 2))
        except (TypeError, ValueError):
            return None
    m = re.search(r"(\d+)", label)
    return int(m.group(1)) if m else None


def cast_context(d, head, rank_label, suffix):
    ctx = {"by": d.get("name", "")}
    rank = _cast_rank(rank_label, d.get("level"))
    if rank:
        ctx["rank"] = str(rank)
    if str(rank_label).lower().startswith("cantrip"):
        ctx["cantrip"] = "1"
    m = re.search(r"\bDC (\d+)", head or "")
    if m:
        ctx["dc"] = m.group(1)
    m = re.search(r"\battack ([+-]\d+)", head or "")
    if m:
        ctx["atk"] = m.group(1)
    m = re.search(r"x(\d+)", suffix or "") or re.search(r"(\d+)/day", suffix or "")
    if m:
        ctx["uses"] = m.group(1)
    entry = re.sub(r"\s*DC \d+.*$", "", head or "").strip()
    if entry:
        ctx["entry"] = entry
    return ctx


def cast_ref(ref, ctx):
    return ref + CAST_SEP + urllib.parse.urlencode(ctx)


class CastRef(int):
    """A rules rowid that carries casting context (so history and Back keep it)."""
    def __new__(cls, rowid, ctx):
        obj = super().__new__(cls, rowid)
        obj.ctx = ctx
        return obj


HEIGHT_RE = re.compile(r"^Heightened \((?:\+(\d+)|(\d+)(?:st|nd|rd|th))\)\s*(.*)$")


def split_heightened(text):
    base, entries = [], []
    for line in (text or "").split("\n"):
        m = HEIGHT_RE.match(strip_links(line).strip())
        if m:
            body = re.sub(r"^\s*Heightened \([^)]*\)\s*", "", line.strip())
            entries.append(("interval", int(m.group(1)), body) if m.group(1) else ("fixed", int(m.group(2)), body))
        else:
            base.append(line)
    while base and base[-1].strip() in ("", "---"):
        base.pop()
    return "\n".join(base), entries


DICE = re.compile(r"^(\d+)d(\d+)(.*)$")


def _add_dice(base, inc, times):
    mb, mi = DICE.match(base.strip()), DICE.match(inc.strip())
    if mb and mi and mb.group(2) == mi.group(2) and not mi.group(3).strip():
        return f"{int(mb.group(1)) + int(mi.group(1)) * times}d{mb.group(2)}{mb.group(3)}"
    return f"{base} + {times} x {inc}"


def heightened_damage(e, rank):
    base_rank = e.get("spell_rank")
    dmg = e.get("damage") or []
    h = e.get("heightening") or {}
    if not dmg or base_rank is None or rank is None or rank <= base_rank or not h:
        return []
    out = []
    if h.get("type") == "interval" and h.get("damage"):
        steps = (rank - base_rank) // max(1, h.get("interval", 1))
        if steps < 1:
            return []
        for key, formula, typ in dmg:
            inc = h["damage"].get(key)
            out.append((_add_dice(formula, inc, steps) if inc else formula, typ))
    elif h.get("type") == "fixed":
        best = None
        for lvl, forms in (h.get("levels") or {}).items():
            lvl = int(lvl)
            if lvl <= rank and forms and (best is None or lvl > best[0]):
                best = (lvl, forms)
        if not best:
            return []
        for key, formula, typ in dmg:
            out.append((best[1].get(key, formula), typ))
    return out


def _base_rank(e):
    if e.get("spell_rank") is not None:
        return e["spell_rank"]
    m = re.search(r"(\d+)\s*$", e.get("header", ""))
    return int(m.group(1)) if m else None


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------- rendering ----------
SIGNED_ITEM = re.compile(r"([^,;]+?)\s+([+-]\d+)(?=\s*(?:[,;]|$))")


def _shift_first(expr, delta):
    """Shift the flat modifier of the first damage expression: '2d6+6 piercing' -> '2d6+8 piercing'."""
    m = re.match(r"^(\d+d\d+)([+-]\d+)?", expr or "")
    if not m or not delta:
        return expr
    mod = int(m.group(2) or 0) + delta
    return m.group(1) + (f"+{mod}" if mod > 0 else str(mod) if mod < 0 else "") + expr[m.end():]


SAVE_KEYS = {"fort": "fortitude", "fortitude": "fortitude", "ref": "reflex", "reflex": "reflex", "will": "will"}


class _Out:
    def __init__(self, who="", conds=None, adj=None, bonuses=None, riders=None):
        self.segs = []
        self.bonuses = bonuses or []  # combatant bonus/penalty effects (cover, shield, bless...)
        self.riders = riders or []    # extra damage that can be switched on (sneak attack, precision...)
        self.who = who            # name used in roll results ("Ghoul Stalker: Stealth check ...")
        self.conds = conds or {}  # combatant conditions: rolls and numbers include their penalties
        self.adj = adj            # ("Elite", +2) / ("Weak", -2): shown separately in breakdowns
        self.level = None         # the creature's or character's level, for values Foundry computes from it

    def components(self, shown, source, kind, stat="", ranged=False, finesse=False, extra=()):
        """Breakdown of a check/attack/DC whose stat block value is `shown` (Elite/Weak already included).
        Returns (total, [(label, value)])."""
        from .combat import condition_mods
        comps = []
        if self.adj and self.adj[1]:
            comps += [(source, shown - self.adj[1]), self.adj]
        else:
            comps.append((source, shown))
        comps += list(extra)
        comps += condition_mods(self.conds, kind, stat, ranged, finesse, bonuses=self.bonuses)
        return sum(v for _, v in comps), comps

    def check(self, text_name, shown, kind, stat="", style="body", source=None, roll_label=None):
        total, comps = self.components(shown, source or text_name or kind.title(), kind, stat)
        self.roll(f"{text_name + ' ' if text_name else ''}{total:+d}", "check", roll_label or text_name or kind.title(),
                  f"{total:+d}", style, mods=comps)
        return total

    def roll(self, text, kind, label, expr, style="body", traits=(), mods=None, dmg=None, dmg_mods=None):
        """Add clickable text that rolls when clicked."""
        from .dice import make_ref
        self.add(text, style, make_ref(kind, label, expr, self.who, traits, mods, dmg, dmg_mods))

    def signed_list(self, text, style="body", kind="check", group="skill"):
        """'Athletics +11, Stealth +13' or 'Fort +11, Ref +14' -> each 'Name +N' is a clickable check,
        adjusted for conditions. group: 'skill' or 'save'."""
        pos = 0
        for m in SIGNED_ITEM.finditer(text or ""):
            lead = len(m.group(1)) - len(m.group(1).lstrip())
            self.add(text[pos:m.start() + lead], style)
            name = m.group(1).strip()
            if group == "save":
                stat, ckind = SAVE_KEYS.get(name.lower(), name.lower()), "save"
            else:
                stat, ckind = name.lower(), "skill"
            self.check(name, int(m.group(2)), ckind, stat, style)
            pos = m.end()
        self.add((text or "")[pos:], style)

    def damage(self, text, label="", style="body", traits=(), mods=None):
        self.roll(text, "damage", label, text, style, traits, mods=mods)

    def add(self, text, style="body", ref=None):
        if text:
            self.segs.append((text, style, ref))

    def rich(self, text, style="body", exclude=""):
        """Text with link markers; conditions in plain spans are auto-linked."""
        text = re.sub(r"(?m)^---$", "\u2500" * 24, resolve_refs(text, self.level))     # computed values and separators
        pos = 0
        for m in MARK.finditer(text or ""):
            self._auto(text[pos:m.start()], style, exclude)
            self.add(m.group(1), style, m.group(2))
            pos = m.end()
        self._auto((text or "")[pos:], style, exclude)

    def _auto(self, plain, style, exclude):
        """Auto-link conditions (rules) and dice expressions (rolls) in plain text."""
        from .dice import TEXT_DICE
        hits = [(m.start(), m.end(), "cond", m.group(1)) for m in COND_RE.finditer(plain)
                if norm(m.group(1)) != exclude]
        hits += [(m.start(), m.end(), "dice", m.group(0)) for m in TEXT_DICE.finditer(plain)]
        hits.sort()
        pos = 0
        for start, end, kind, text in hits:
            if start < pos:
                continue
            self.add(plain[pos:start], style)
            if kind == "cond":
                self.add(text, style, f"name:{text.lower()}")
            else:
                self.damage(text, "", style)
            pos = end
        self.add(plain[pos:], style)

    def links(self, pairs, style="body", sep=", "):
        for i, (text, ref) in enumerate(pairs):
            if i:
                self.add(sep, style)
            self.add(text, style, ref)


def _trait_line(o, rarity, size, traits):
    tr = []
    if rarity not in (None, "", "common"):
        tr.append((rarity.upper(), f"trait:{rarity}"))
    if size:
        tr.append((_titleize(size).upper(), f"trait:{size}"))
    tr += [(_titleize(t).upper(), f"trait:{t}") for t in traits]
    if tr:
        o.links(tr, "trait", sep="  ")
        o.add("\n", "trait")


def _paren_traits(o, traits, style="label"):
    if traits:
        o.add(" (", style)
        o.links([(t.replace("-", " "), f"trait:{t}") for t in traits], style)
        o.add(")", style)


RULE = "─" * 60 + "\n"


def _defense_line(o, d):
    from .combat import condition_mods
    ac = ""
    if d.get("ac") is not None:
        m = condition_mods(o.conds, "ac", bonuses=o.bonuses)
        eff = d["ac"] + sum(v for _, v in m)
        ac = f"AC {eff}" + (f" (base {d['ac']}; " + ", ".join(f"{l} {v:+d}" for l, v in m) + ")" if m else "")
    if not ac and not d.get("saves"):
        return
    o.add(ac, "label")
    if d.get("saves"):
        o.add("; " if ac else "", "label")
        o.signed_list(d["saves"], "label", group="save")
    o.add("\n", "label")


def _weapon_type(st):
    """Damage type of a Strike's first damage entry: '2d6+6 piercing' -> 'piercing'."""
    first = ((st.get("damage") or [""])[0] or "").strip()
    m = re.match(r"^\s*(?:\d*d\d+|\d+)(?:\s*[+-]\s*(?:\d*d\d+|\d+))*\s+([a-z]+)", first, re.IGNORECASE)
    return m.group(1).lower() if m else (st.get("dtype") or "")


def _conditions_note(o):
    active = [r for r in o.riders if r.get("active")]
    if active:
        from .combat import RIDER_APPLIES
        names = {v: k for k, v in RIDER_APPLIES.items()}
        o.add("Extra damage on: " + ", ".join(
            f"{r.get('label', 'Rider')} ({r.get('dice', '')}{' precision' if r.get('precision', True) else ' ' + r.get('dtype', '')}"
            f", {names.get(r.get('applies', 'any'), 'any Strike').lower()})" for r in active) + "\n", "warn")
    if o.bonuses:
        o.add("Bonuses/penalties: " + ", ".join(
            f"{b['label']} {int(b['value']):+d} {b['type']} to {b['applies']}"
            + (f" ({b['rounds']} rd)" if b.get("rounds") else "") for b in o.bonuses) + "\n", "warn")
    if not o.conds:
        return
    from .combat import condition_mods
    names = ", ".join(f"{k} {v}" if isinstance(v, int) else (f"persistent {v}" if k.startswith("persistent") else k)
                      for k, v in sorted(o.conds.items()))
    affects = any(condition_mods(o.conds, k, s, bonuses=o.bonuses) for k, s in (("attack", ""), ("ac", ""), ("save", "fortitude"),
                                                              ("save", "reflex"), ("save", "will"), ("perception", ""),
                                                              ("damage", ""), ("skill", "athletics"),
                                                              ("skill", "stealth"), ("skill", "arcana")))
    o.add(f"Conditions: {names}\n", "warn")
    if affects:
        o.add("Numbers and rolls below include their penalties (only the worst status penalty applies). "
              "Click any green number to see the breakdown.\n", "warn")


def _shift_text_dcs(o, text):
    """Lower 'DC N' in ability text by condition penalties to the creature's DCs (frightened, sickened)."""
    from .combat import condition_mods
    delta = sum(v for _, v in condition_mods(o.conds, "dc", bonuses=o.bonuses))
    if not delta:
        return text
    return re.sub(r"\bDC (\d+)", lambda m: f"DC {int(m.group(1)) + delta}", text or "")


# Words that start a line of rules text ("Requirements ...", "Critical Success ...").
HEADER_LABELS = ("Requirements", "Requirement", "Frequency", "Trigger", "Cost", "Prerequisites", "Prerequisite", "Access",
                 "Duration", "Range", "Area", "Targets", "Target", "Saving Throw")
OTHER_LABELS = ("Effect", "Special")
OUTCOME_LABELS = ("Critical Success", "Success", "Failure", "Critical Failure")
_ALL_LABELS = sorted(HEADER_LABELS + OTHER_LABELS + OUTCOME_LABELS, key=len, reverse=True)
LABEL_LINE = re.compile(r"^(" + "|".join(re.escape(x) for x in _ALL_LABELS) + r")(?=\s|$)")
_HEAD_SPLIT = re.compile(r"(?<=[.;])\s+(?=(?:" + "|".join(re.escape(x) for x in HEADER_LABELS + ("Effect",)) + r")\b)")


def ability_lines(text, level=None):
    """Rules text as readable lines: [(kind, label, text)]. kind is 'head' (Requirements, Frequency, Trigger, Cost...),
    'lab' (Effect, Special), 'out' (a degree of success), or 'body' (an ordinary paragraph). Separators are dropped,
    values Foundry computes are resolved for the given level, and a header line such as
    'Frequency once per day; Trigger You are hit' is split into one line per label."""
    t = resolve_refs(text, level)
    out = []
    for raw in re.split(r"\n+", t):
        ln = raw.strip()
        if not ln or re.fullmatch(r"[-\u2500]{3,}", ln):
            continue
        m = LABEL_LINE.match(ln)
        if m and m.group(1) in HEADER_LABELS + ("Effect",):
            pieces = [x.strip().rstrip(";").strip() for x in _HEAD_SPLIT.split(ln) if x.strip()]
        else:
            pieces = [ln]
        for piece in pieces:
            m = LABEL_LINE.match(piece)
            if not m:
                out.append(("body", "", piece))
                continue
            lab = m.group(1)
            kind = "out" if lab in OUTCOME_LABELS else "lab" if lab in OTHER_LABELS else "head"
            out.append((kind, lab, piece[m.end():].strip()))
    return out


def ability_body(o, text, compact=False):
    """Draw an ability's rules text: header labels in bold on their own lines, the description as paragraphs, and each
    degree of success indented. compact keeps only the header lines (frequency, requirements, trigger, cost)."""
    for kind, lab, rest in ability_lines(_shift_text_dcs(o, resolve_refs(text, o.level)), o.level):
        if compact and kind != "head":
            continue
        if kind == "out":
            o.add(lab + " ", "indlabel"); o.rich(rest, "ind")
        elif kind in ("head", "lab"):
            o.add(lab + (" " if rest else ""), "label"); o.rich(rest)
        else:
            o.rich(rest, "para")
        o.add("\n")


def _pc_abilities(o, actions, own, compact=False):
    """Every action, reaction, and free action a character has from feats and class features, in one section: one-,
    two-, and three-action abilities first, then reactions and free actions. Each has its name and traits on one line,
    then its text laid out by ability_body()."""
    if not actions:
        return
    rank = {"[1]": 0, "[2]": 1, "[3]": 2, "[R]": 3, "[F]": 4}
    ordered = sorted(actions, key=lambda a: rank.get(a.get("glyph") or "", 5))
    o.add(RULE, "rule")
    o.add("Actions and Reactions\n", "head")
    if compact:
        o.add("Showing requirements, frequency, and cost only. Tick 'Show full text of feats and actions' below the page for the rest.\n", "warn")
    for a in ordered:
        o.add(a["name"], "anchor", a["name"])
        o.add(a["name"] + (f" {a['glyph']}" if a.get("glyph") else ""), "abil")
        _paren_traits(o, a.get("traits") or [])
        o.add("\n")
        ability_body(o, a.get("text") or "", compact)


def render_hazard(d, who=None, conds=None, bonuses=None):
    o = _Out(who or d.get("name", ""), conds, bonuses=bonuses)
    o.add(d["name"], "title")
    o.add(f"    Hazard {d.get('level', '?')}\n", "head")
    traits = list(d.get("traits", []))
    if d.get("complex") and "complex" not in traits:
        traits.append("complex")
    _trait_line(o, d.get("rarity"), "", traits)
    if d.get("source"):
        o.add("Source ", "label"); o.add(d["source"] + "\n")
    _conditions_note(o)
    if d.get("stealth") is not None:
        o.add("Stealth ", "label")
        o.check("", int(d["stealth"]), "skill", "stealth", source="Stealth", roll_label="Stealth (initiative)")
        o.add(f" (DC {int(d['stealth']) + 10})"
              + (f" {strip_links(d['stealth_details'])}" if d.get("stealth_details") else "") + "\n")
    for label, key in (("Description", "description"), ("Disable", "disable")):
        if d.get(key):
            o.add(label + " ", "label"); o.rich(d[key]); o.add("\n")
    o.add(RULE, "rule")
    _defense_line(o, d)
    hp_bits = []
    if d.get("hardness") is not None:
        hp_bits.append(f"Hardness {d['hardness']}")
    if d.get("hp") is not None:
        hp_bits.append(f"HP {d['hp']}" + (f" (BT {d['bt']})" if d.get("bt") else ""))
    if hp_bits or d.get("immunities") or d.get("weaknesses") or d.get("resistances"):
        o.add(", ".join(hp_bits), "label")
        for label, key in (("Immunities", "immunities"), ("Weaknesses", "weaknesses"), ("Resistances", "resistances")):
            if d.get(key):
                o.add(f"; {label} ", "label"); o.links(d[key])
        o.add("\n")
    for a in d.get("actions", []) or []:
        o.add(a["name"] + (f" {a['glyph']}" if a["glyph"] else ""), "label")
        _paren_traits(o, a["traits"])
        o.add(" ", "label"); o.rich(a.get("text") or ""); o.add("\n")
    if d.get("routine"):
        o.add("Routine ", "label"); o.rich(d["routine"]); o.add("\n")
    for st in d.get("strikes", []) or []:
        _strike_line(o, st)
    if d.get("reset"):
        o.add("Reset ", "label"); o.rich(d["reset"]); o.add("\n")
    if d.get("complex"):
        o.add("\nComplex hazard: rolls initiative with Stealth and acts on its routine each round.\n", "muted")
    return o.segs


def _strike_line(o, st, own=None):
    from .dice import map_steps
    own = own or {}
    o.add(f"{st['kind']} [1] ", "label")
    o.add(f"{st['name']} ")
    from .combat import condition_mods, rider_applies, rider_text
    traits = st.get("traits") or []
    ranged = st.get("kind") == "Ranged"
    finesse = any(t.lower() == "finesse" for t in traits)
    # damage: base expression (without Elite/Weak) plus flat modifiers, so rolls show each source
    dmg_text = " plus ".join(st.get("damage") or [])
    dmg_mods = []
    if dmg_text:
        delta = o.adj[1] if o.adj else 0
        base_dmg = _shift_first(dmg_text, -delta)
        if delta:
            dmg_mods.append(o.adj)
        dmg_mods += condition_mods(o.conds, "damage", ranged=ranged, finesse=finesse, bonuses=o.bonuses)
        shown_dmg = _shift_first(base_dmg, sum(v for _, v in dmg_mods))
        extra = [t for t in (rider_text(r, _weapon_type(st)) for r in o.riders
                             if r.get("active") and rider_applies(r, traits, ranged)) if t]
        if extra:                      # switched-on riders add their own damage entry to every roll
            tail = "".join(f" plus {t}" for t in extra)
            base_dmg += tail
            shown_dmg += tail
    bonus = str(st.get("bonus", ""))
    if re.fullmatch(r"[+-]\d+", bonus):
        b = int(bonus)
        m1, m2 = map_steps(traits)
        for i, (extra, lab, style) in enumerate((((), st["name"], "body"),
                                                 ((("MAP (2nd attack)", -m1),), f"{st['name']} (2nd attack)", "muted"),
                                                 ((("MAP (3rd+ attack)", -m2),), f"{st['name']} (3rd+ attack)", "muted"))):
            total, comps = o.components(b, "Strike", "attack", ranged=ranged, finesse=finesse, extra=extra)
            if i == 1:
                o.add(" [", "muted")
            elif i == 2:
                o.add("/", "muted")
            o.roll(f"{total:+d}", "attack", lab, f"{total:+d}", style, traits, mods=comps,
                   dmg=base_dmg if dmg_text else None, dmg_mods=dmg_mods)
        o.add("]", "muted")
    else:
        o.add(bonus)
    _paren_traits(o, st["traits"], "body")
    if dmg_text:
        o.add(", Damage ")
        o.roll(shown_dmg, "damage", st["name"], base_dmg, "body", traits, mods=dmg_mods)
    if st.get("note"):
        o.add(("; " if dmg_text else ", ") + st["note"], "muted")
    if st.get("effects"):
        o.add(" plus ")
        o.links([(_titleize(e), f"self:{own[norm(e)]}" if norm(e) in own else f"name:{e}") for e in st["effects"]])
    o.add("\n")


def render(d, who=None, conds=None, bonuses=None, riders=None):
    """Stat block segments. who: name used in roll results. conds: combatant conditions, applied to
    every number and roll (and listed at the top). riders: extra damage switched on for this combatant."""
    if d.get("kind") == "hazard":
        return render_hazard(d, who, conds, bonuses)
    from .adjust import recall_knowledge
    adj = (d["adjust_label"], d["adjust_delta"]) if d.get("adjust_delta") else None
    o = _Out(who or d.get("name", ""), conds, adj, bonuses, riders)
    o.level = d.get("level")
    actions = d.get("actions", []) or []
    own = {norm(a["name"]): a["name"] for a in actions}
    is_pc = d.get("kind") == "pc"

    o.add(d["name"], "title")
    o.add(f"    {'PC' if d.get('kind') == 'pc' else 'Creature'} {d.get('level', '?')}\n", "head")
    _trait_line(o, d.get("rarity"), d.get("size"), d.get("traits", []))
    if d.get("source"):
        o.add("Source ", "label"); o.add(d["source"] + "\n")
    if d.get("blurb"):
        o.rich(d["blurb"]); o.add("\n")
    if d.get("adjust_note"):
        o.add(d["adjust_note"] + "\n", "warn")
    _conditions_note(o)
    rk = recall_knowledge(d) if d.get("kind") != "pc" else None
    if rk:
        o.add("Recall Knowledge ", "label")
        skills = ", ".join(rk["skills"]) if rk["skills"] else "GM's choice of skill"
        o.add(f"DC {rk['dc']} ({skills}; an applicable Lore is easier)\n", "muted")
        for r in rk["reveal"]:
            o.add(f"  • {r}\n", "muted")
    o.add("\n")
    senses = d.get("senses") or []
    if isinstance(senses, str):
        senses = [(senses, None)]
    if d.get("perception") or senses:
        o.add("Perception ", "label")
        per = str(d.get("perception", "") or "")
        if re.fullmatch(r"[+-]\d+", per.strip()):
            o.check("", int(per), "perception", source="Perception", roll_label="Perception")
        else:
            o.add(per)
        if senses:
            o.add("; " if d.get("perception") else "")
            o.links(senses)
        o.add("\n")
    if d.get("languages"):
        o.add("Languages ", "label"); o.add(d["languages"] + "\n")
    if d.get("skills"):
        o.add("Skills ", "label"); o.signed_list(d["skills"]); o.add("\n")
    if d.get("abilities"):
        o.add(d["abilities"] + "\n")
    gear = d.get("gear") or []
    if isinstance(gear, str):
        gear = [g.strip() for g in gear.split(",") if g.strip()]
    if gear:
        o.add("Items ", "label"); o.links([(g, f"item:{g}") for g in gear]); o.add("\n")
    if d.get("trappings"):                          # everyday things (food, tools, keepsakes): plain text, nothing to look up
        o.add("Carries ", "label"); o.add("; ".join(d["trappings"]) + "\n")
    o.add(RULE, "rule")

    _defense_line(o, d)
    if d.get("hp") is not None:
        o.add(f"HP {d['hp']}" + (f", {d['hp_details']}" if d.get("hp_details") else ""), "label")
        for label, key in (("Immunities", "immunities"), ("Weaknesses", "weaknesses"), ("Resistances", "resistances")):
            vals = d.get(key) or []
            if isinstance(vals, str):
                vals = [(vals, None)]
            if vals:
                o.add(f"; {label} ", "label"); o.links(vals)
        o.add("\n")

    def ability_block(cat):
        for a in [a for a in actions if a["category"] == cat]:
            o.add(a["name"], "anchor", a["name"])
            o.add(a["name"] + (f" {a['glyph']}" if a["glyph"] else ""), "label")
            _paren_traits(o, a["traits"])
            o.add(" ", "label")
            o.rich(_shift_text_dcs(o, a.get("text") or ""))
            o.add("\n")

    if not is_pc:
        ability_block("interaction")
        ability_block("defensive")
    o.add(RULE, "rule")
    if d.get("speed"):
        o.add("Speed ", "label"); o.add(d["speed"] + "\n")
    for st in d.get("strikes", []) or []:
        if isinstance(st, (list, tuple)):          # older index format
            o.add(f"{st[0]} [1] ", "label"); o.add(st[1] + "\n"); continue
        _strike_line(o, st, own)
    for sp in d.get("spells", []) or []:
        if isinstance(sp, str):
            o.add("Spells: ", "label"); o.add(sp + "\n"); continue
        o.add("Spells: ", "label")
        head = sp["head"]
        from .combat import condition_mods
        dc_mods = condition_mods(o.conds, "spell_dc", bonuses=o.bonuses)
        if dc_mods:
            head = re.sub(r"\bDC (\d+)", lambda m: f"DC {int(m.group(1)) + sum(v for _, v in dc_mods)}", head)
        m = re.search(r"attack ([+-]\d+)", head)
        if m:
            total, comps = o.components(int(m.group(1)), "Spell attack", "spell_attack")
            head = head[:m.start()] + f"attack {total:+d}" + head[m.end():]
            m = re.search(r"attack ([+-]\d+)", head)
            o.add(head[:m.start()])
            o.roll(m.group(0), "attack", "Spell", m.group(1), mods=comps)
            o.add(head[m.end():])
        else:
            o.add(head)
        sp = dict(sp, head=head)
        for rank, spells in sp["ranks"]:
            o.add(f"; {rank}: ")
            for i, (nm, ref, suffix) in enumerate(spells):
                o.add(", " if i else "")
                o.add(nm, "body", cast_ref(ref, cast_context(d, sp["head"], rank, suffix)))
                o.add(suffix)
        o.add("\n")
    if is_pc:
        _pc_abilities(o, actions, own, bool(d.get("compact_actions")))
        _pc_sections(o, d)
    else:
        ability_block("offensive")
    if d.get("description"):
        o.add(RULE, "rule")
        o.add("Description\n", "label")
        o.rich(d["description"]); o.add("\n")
    return o.segs


def _feat_text_sections(o, x):
    """Description of each feat and class feature, plus a note about names with no rules text."""
    texts = x.get("feat_text") or []
    if texts:
        o.add(RULE, "rule")
        o.add("Feat and Feature Descriptions\n", "head")
        for f in texts:
            o.add(f["name"], "label", f"feat:{f['name'].split(' (')[0]}")
            if f.get("glyph"):
                o.add(f" {f['glyph']}", "label")
            meta = " | ".join(m for m in (f.get("type"), f"level {f['level']}" if f.get("level") else "") if m)
            if meta:
                o.add(f"  {meta}", "muted")
            _paren_traits(o, f.get("traits") or [])
            o.add("\n")
            if f.get("text"):
                ability_body(o, f["text"])
            else:
                o.add("No description.\n", "muted")
            o.add("\n")
    missing = x.get("missing_text") or []
    if x.get("has_lookup") and missing:
        shown = ", ".join(missing[:8]) + (f", and {len(missing) - 8} more" if len(missing) > 8 else "")
        if not x.get("feat_text_count"):
            o.add("No feat or feature text is loaded. Download / Update Data on Party & Data to get descriptions.\n",
                  "warn")
        else:
            o.add(f"No rules text found in your data for {len(missing)}: {shown}. "
                  "Their names may differ from Pathbuilder's.\n", "warn")


def _coins(m):
    return ", ".join(f"{m[k]} {k}" for k in ("pp", "gp", "sp", "cp") if m.get(k))


def _pc_sections(o, d):
    """Feats, class features, equipment, armor, formulas, rituals, familiars, and money for PCs/NPCs."""
    x = d.get("pc_extra") or {}
    if x.get("feats") or x.get("specials"):
        o.add(RULE, "rule")
        o.add("Feats and Features\n", "head")
        for typ, items in x.get("feats", []):
            plural = typ in ("Heritage", "Background") or typ.endswith("s")
            o.add(f"{typ}: " if plural else f"{typ}s: ", "label")
            for i, f in enumerate(items):
                o.add(", " if i else "")
                label = f["name"] + (f" ({f['choice']})" if f.get("choice") else "")
                o.add(label, "body", f"feat:{f['name']}")
                if f.get("level"):
                    o.add(f" L{f['level']}", "muted")
            o.add("\n")
        if x.get("specials"):
            o.add("Class features: ", "label")
            o.links([(n, f"feat:{n}") for n in x["specials"]])
            o.add("\n")
    _feat_text_sections(o, x)
    if x.get("armor") or x.get("equipment") or x.get("money") or x.get("weapons"):
        o.add(RULE, "rule")
        o.add("Equipment\n", "head")
        if x.get("weapons"):
            o.add("Weapons: ", "label")
            for i, w in enumerate(x["weapons"]):
                o.add(", " if i else "")
                o.add(w["name"], "body", f"item:{w.get('base') or w['name']}")
            o.add("\n")
        if x.get("armor"):
            o.add("Armor: ", "label")
            for i, a in enumerate(x["armor"]):
                o.add(", " if i else "")
                o.add(a["name"], "body", f"item:{a.get('base') or a['name']}")
                o.add(" (worn)" if a.get("worn") else "", "muted")
            o.add("\n")
        eq = x.get("equipment", [])
        worn = [e for e in eq if e.get("invested")]
        groups = {}
        for e in eq:
            if not e.get("invested"):
                groups.setdefault(e.get("container") or "", []).append(e)
        if worn:
            o.add("Invested: ", "label")
            o.links([(e["name"] + (f" x{e['qty']}" if e.get("qty", 1) > 1 else ""), f"item:{e['name']}") for e in worn])
            o.add("\n")
        for cont, items in groups.items():
            o.add(f"{cont}: " if cont else "Carried: ", "label")
            o.links([(e["name"] + (f" x{e['qty']}" if e.get("qty", 1) > 1 else ""), f"item:{e['name']}") for e in items])
            o.add("\n")
        if x.get("money"):
            o.add("Money: ", "label"); o.add(_coins(x["money"]) + "\n")
    if x.get("formulas") or x.get("rituals"):
        o.add(RULE, "rule")
        for f in x.get("formulas", []):
            o.add(f"Formulas ({f['type']}): ", "label")
            o.links([(n, f"item:{n}") for n in f["known"]])
            o.add("\n")
        if x.get("rituals"):
            o.add("Rituals: ", "label"); o.links([(n, f"spell:{n}") for n in x["rituals"]]); o.add("\n")
    for pet in x.get("pets", []):
        o.add(RULE, "rule")
        o.add(f"{pet['kind']}: ", "label")
        o.add((pet["name"] or "(unnamed)") + (f" ({pet['specific']})" if pet.get("specific") else "") + "\n")
        if pet.get("abilities"):
            o.add("  Abilities: ", "label"); o.links([(n, f"name:{n}") for n in pet["abilities"]]); o.add("\n")
        if pet.get("equipment"):
            o.add("  Equipment: ", "label"); o.links([(n, f"item:{n}") for n in pet["equipment"]]); o.add("\n")


def _render_cast(o, e, ctx):
    base_rank = _base_rank(e)
    try:
        rank = int(ctx.get("rank")) if ctx.get("rank") else None
    except ValueError:
        rank = None
    o.add(f"Cast by {ctx.get('by', 'creature')}" + (f" ({ctx['entry']})" if ctx.get("entry") else "") + "\n", "head")
    bits = []
    if rank is not None:
        if base_rank is not None and rank > base_rank:
            bits.append(f"Rank {rank} (heightened from {base_rank})")
        else:
            bits.append(f"Rank {rank}" + (" (cantrip, auto-heightened)" if ctx.get("cantrip") else ""))
    if ctx.get("dc"):
        bits.append(f"DC {ctx['dc']}")
    if ctx.get("atk"):
        bits.append(f"spell attack {ctx['atk']}")
    if ctx.get("uses"):
        bits.append(f"{ctx['uses']}/day")
    if bits:
        o.add("; ".join(bits) + "\n", "label")
    dmg = heightened_damage(e, rank)
    if dmg:
        o.add("Damage at this rank ", "label")
        o.damage(" plus ".join(f"{f} {t}".strip() for f, t in dmg), e["name"])
        o.add("\n")
    if ctx.get("atk"):
        o.add("Spell attack ", "label")
        o.roll(ctx["atk"], "attack", e["name"], ctx["atk"])
        o.add("\n")
    _, entries = split_heightened(e.get("text"))
    if rank is None or base_rank is None or not entries:
        if entries and rank is None:
            o.add("Cast rank unknown; see Heightened entries below.\n", "muted")
        return
    applied = []
    for kind, n, body in entries:
        if kind == "interval":
            times = (rank - base_rank) // n
            if times >= 1:
                applied.append((f"Heightened (+{n}) applied {times} time{'s' if times > 1 else ''}: ", body))
        elif n <= rank:
            applied.append((f"Heightened ({_ordinal(n)}): ", body))
    if applied:
        o.add(f"Heightened effects at rank {rank}\n", "label")
        for label, body in applied:
            o.add("  • " + label, "label")
            o.rich(body, exclude=norm(e["name"]))
            o.add("\n")
    elif rank > base_rank:
        o.add("No heightened entries apply at this rank.\n", "muted")
    else:
        o.add("Cast at base rank; no heightening.\n", "muted")


def render_entry(e, who=None):
    o = _Out(who or (e.get("cast") or {}).get("by", ""))
    o.add(e["name"] + (f" {e['glyph']}" if e.get("glyph") else ""), "title")
    o.add(f"    {e.get('header', '')}\n", "head")
    _trait_line(o, e.get("rarity"), "", e.get("traits", []))
    if e.get("source"):
        o.add("Source ", "label"); o.add(e["source"] + "\n")
    for label, val in e.get("meta", []):
        o.add(f"{label} ", "label"); o.add(f"{val}\n")
    if e.get("cast"):
        o.add(RULE, "rule")
        _render_cast(o, e, e["cast"])
    o.add(RULE, "rule")
    if e.get("flavor"):                                     # a custom spell's flavor: what it is like, not what it does
        o.add(e["flavor"] + "\n\n", "flavor")
    o.rich(e.get("text") or "No description.", exclude=norm(e["name"]))
    o.add("\n")
    return o.segs


def custom_item_entry(it):
    meta = [["Price", f"{it.price_gp:g} gp"], ["Type", "Consumable" if it.consumable else "Permanent"]]
    return {"name": it.name, "kind": "item", "header": f"Item {it.level}", "traits": it.traits,
            "rarity": it.rarity, "source": it.source, "meta": meta, "text": it.notes}


def render_text(segs_or_details):
    segs = segs_or_details if isinstance(segs_or_details, list) else render(segs_or_details)
    return "".join(t for t, style, _ in segs if style != "anchor")


# ---------- storage ----------
class DetailsDB:
    """SQLite store: creature stat blocks plus the rules glossary."""

    def __init__(self, path):
        self.path = str(path)
        self._con = None
        self._cache = {}
        self._custom = {}          # negative rowid -> entry dict (custom spells and abilities)
        self._custom_names = {}    # (norm name, kind) -> negative rowid

    def set_custom_rules(self, entries):
        """Register custom spells/abilities. They take priority over official entries with the same name."""
        self._custom, self._custom_names = {}, {}
        for i, e in enumerate(entries, 1):
            rid = -i
            self._custom[rid] = e
            self._custom_names[(norm(e["name"]), e["kind"])] = rid
        self._cache = {}

    def write_all(self, creature_rows, rule_rows=()):
        con = sqlite3.connect(self.path)
        try:
            con.execute("DROP TABLE IF EXISTS creatures")
            con.execute("DROP TABLE IF EXISTS rules")
            con.execute("CREATE TABLE creatures (uid TEXT PRIMARY KEY, data TEXT)")
            con.execute("CREATE TABLE rules (id TEXT PRIMARY KEY, norm TEXT, kind TEXT, prio INT, data TEXT)")
            con.execute("CREATE INDEX rules_norm ON rules(norm)")
            con.executemany("INSERT OR REPLACE INTO creatures VALUES (?, ?)", ((u, json.dumps(d)) for u, d in creature_rows))
            # Pathfinder entries win name lookups over Starfinder entries with the same name
            # (e.g. shared conditions); links by Foundry ID still go to the exact entry.
            con.executemany("INSERT OR REPLACE INTO rules VALUES (?, ?, ?, ?, ?)",
                            ((i, n, k, KIND_PRIO.get(k, 9) * 2 + (1 if d.get("system") == "sf" else 0),
                              json.dumps(d)) for i, n, k, d in rule_rows))
            con.commit()
        finally:
            con.close()

    def reset(self):
        if self._con:
            self._con.close()
        self._con, self._cache = None, {}

    def _q(self, sql, args):
        try:
            if self._con is None:
                self._con = sqlite3.connect(self.path, check_same_thread=False)
            return self._con.execute(sql, args).fetchone()
        except sqlite3.Error:
            return None

    def get(self, uid):
        row = self._q("SELECT data FROM creatures WHERE uid = ?", (uid,))
        return json.loads(row[0]) if row else None

    def iter_creatures(self):
        """Yield every stored stat block (for building dropdown vocabularies)."""
        try:
            con = sqlite3.connect(self.path)
            try:
                for (data,) in con.execute("SELECT data FROM creatures"):
                    try:
                        yield json.loads(data)
                    except ValueError:
                        continue
            finally:
                con.close()
        except sqlite3.Error:
            return

    def spell_pool(self):
        """Every spell in the rules data as a short dict for grimoires: name, rank, traditions, traits, rarity, cantrip,
        focus, ritual, system. Indexes built before traditions were stored give an empty traditions list."""
        try:
            con = sqlite3.connect(self.path)
            try:
                rows = con.execute("SELECT data FROM rules WHERE kind = 'spell'").fetchall()
            finally:
                con.close()
        except sqlite3.Error:
            return []
        out = []
        for (data,) in rows:
            try:
                e = json.loads(data)
            except ValueError:
                continue
            traits = [str(t).lower() for t in e.get("traits") or []]
            rank = e.get("spell_rank")
            if not isinstance(rank, int):
                m = re.search(r"(\d+)\s*$", e.get("header", ""))
                rank = int(m.group(1)) if m else None
            if rank is None:
                continue
            out.append({"name": e.get("name", ""), "rank": 0 if "cantrip" in traits else rank, "traits": traits,
                        "traditions": list(e.get("traditions") or []), "rarity": e.get("rarity") or "common",
                        "cantrip": "cantrip" in traits, "focus": "focus" in traits, "ritual": bool(e.get("ritual")),
                        "system": e.get("system", "pf")})
        return out

    def rule_names(self, kind):
        try:
            con = sqlite3.connect(self.path)
            try:
                rows = con.execute("SELECT data FROM rules WHERE kind = ?", (kind,)).fetchall()
            finally:
                con.close()
        except sqlite3.Error:
            rows = []
        names = {e["name"] for e in self._custom.values() if e.get("kind") == kind}
        for (data,) in rows:
            try:
                names.add(json.loads(data)["name"])
            except (ValueError, KeyError):
                continue
        return sorted(names)

    # --- rules lookup ---
    def _by_id(self, i):
        row = self._q("SELECT rowid FROM rules WHERE id = ?", (i,))
        return row[0] if row else None

    def _by_name(self, name, kind=None):
        n = norm(name)
        if not n:
            return None
        for k in ([kind] if kind else ["spell", "action"]):
            if (n, k) in self._custom_names:
                return self._custom_names[(n, k)]
        if kind:
            row = self._q("SELECT rowid FROM rules WHERE norm = ? AND kind = ? ORDER BY prio LIMIT 1", (n, kind))
        else:
            row = self._q("SELECT rowid FROM rules WHERE norm = ? ORDER BY prio LIMIT 1", (n,))
        return row[0] if row else None

    def _by_trait(self, slug):
        tokens = [t for t in re.split(r"[-_ ]", str(slug)) if t]
        for i in range(len(tokens), 0, -1):     # deadly-d10 -> deadly, reach-10 -> reach
            r = self._by_id("trait:" + norm("".join(tokens[:i])))
            if r:
                return r
        return None

    def resolve(self, ref):
        """Return a rules rowid for a ref, or None. Spell refs with casting context return a CastRef."""
        if ref in self._cache:
            return self._cache[ref]
        base, _, ctx_text = ref.partition(CAST_SEP)
        kind, _, val = base.partition(":")
        r = None
        if kind == "uuid":
            seg, _, lab = val.partition("|")
            r = self._by_id(seg) or self._by_name(lab) or self._by_name(seg)
        elif kind == "trait":
            r = self._by_trait(val) or self._by_name(val)
        elif kind in KIND_PRIO:
            r = self._by_name(val, kind) or self._by_name(val)
        elif kind == "name":
            r = self._by_name(val) or self._by_trait(val)
        if r and ctx_text:
            r = CastRef(r, dict(urllib.parse.parse_qsl(ctx_text)))
        self._cache[ref] = r
        return r

    def rule(self, rowid):
        if int(rowid) < 0:
            e = self._custom.get(int(rowid))
            e = json.loads(json.dumps(e)) if e else None
        else:
            row = self._q("SELECT data FROM rules WHERE rowid = ?", (int(rowid),))
            e = json.loads(row[0]) if row else None
        if not e:
            return None
        ctx = getattr(rowid, "ctx", None)
        if ctx and e.get("kind") == "spell":
            e["cast"] = ctx
        return e

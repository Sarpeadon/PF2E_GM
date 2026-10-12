"""Story Forge: a modular, table-driven generator for rumors, complications, hooks, faction moves, and NPC traits.

Nothing here is content. All wording lives in tables (storydata.py plus your own edits), so you can change what
gets generated without touching code.

How it fits together
  * A TABLE is a weighted list of entries. An entry is a template such as
        "{has} been buying up every {goods}|trade crime|2"
    Text in braces is replaced when the entry is picked: {goods} rolls the table called "goods", {a occupation}
    adds a/an, {pl occupation} pluralizes, {@who} reuses an earlier slot, {has}/{is}/{was} agree with the
    subject, {dc:hard} / {gp:medium} / {lvl} scale to party level, {#2-6} rolls a number, {n:2-6} a number word,
    {table?40} includes it 40% of the time, {^table} capitalizes, {@x=table} rolls and remembers as @x.
  * TAGS steer coherence. Entries carry theme tags (crime, undead, trade...). Once a theme is in play, entries
    that share it are far more likely and unrelated ones less so ("focus" sets how strongly). An entry can also
    require tags (needs), forbid them (not), or be limited to a tone, a party level range, or a content pack.
  * A RECIPE (rumor, complication, hook, faction_move, ...) lists the slots to fill: Who, What, Where, When, Why,
    plus extras such as the rumor's source and truth. Each slot can be locked, edited, or rerolled on its own.
    A slot may set "strict_anchor": true. When the story has an anchor (the themes its event brought in), that slot then
    only takes entries that share one of those themes, or entries with no theme at all. The Why of a hook uses it, so a
    patron's reason fits what they ask for.
  * Providers are the few things tables can't do: a named NPC with an ancestry, and pulling factions, NPCs,
    locations, events, and creatures out of your campaign so stories involve your own world.
  * A History remembers what was just used and makes repeats unlikely, so repeated rolls feel different.

Your changes (extra entries, edited or disabled built-ins, new tables, recipe overrides) are saved to
user_data/story_tables.json and merged over the built-ins every time.
"""
import copy
import hashlib
import json
import random
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass, field

try:
    from . import names as _names
except ImportError:                      # running this file directly: python storygen.py rumor 3
    import names as _names

THEMES = ["crime", "politics", "trade", "religion", "undead", "fey", "monster", "nature", "ruin", "magic",
          "military", "family", "mystery", "disease", "weather", "festival", "craft", "treasure"]
THEME_SET = frozenset(["crime", "politics", "trade", "religion", "undead", "fey", "monster", "nature", "ruin", "magic",
                      "military", "family", "mystery", "disease", "weather", "festival", "craft", "treasure"])
ENVS = ["urban", "wild", "underground", "road", "water"]
SEASONS = ["spring", "summer", "autumn", "winter"]
TONES = ["grim", "light", "weird"]
PACKS = ["core", "underground", "hallowmead", "sf"]
DEFAULT_PACKS = ["core", "underground", "hallowmead"]
DEFAULT_FLAVOR = 0.35         # setting (Hallowmead) lines take about a third of a story's weight by default
MAX_DEPTH = 9

TOKEN = re.compile(r"\{([^{}]+)\}")
SCENE_ENV = {"travel": "env.travel", "dungeon": "env.dungeon", "social": "env.social", "downtime": "env.social"}
DC_BY_LEVEL = {-1: 13, 0: 14, 1: 15, 2: 16, 3: 18, 4: 19, 5: 20, 6: 22, 7: 23, 8: 24, 9: 26, 10: 27, 11: 28,
               12: 30, 13: 31, 14: 32, 15: 34, 16: 35, 17: 36, 18: 38, 19: 39, 20: 40, 21: 42, 22: 44, 23: 46,
               24: 48, 25: 50}
DC_ADJ = {"trivial": -5, "easy": -2, "normal": 0, "hard": 2, "very hard": 5, "extreme": 10}
# Party currency per level (GM Core treasure table); story rewards are fractions of it.
CURRENCY_BY_LEVEL = {1: 40, 2: 70, 3: 120, 4: 200, 5: 320, 6: 500, 7: 720, 8: 1000, 9: 1400, 10: 2000, 11: 2800,
                     12: 4000, 13: 6000, 14: 9000, 15: 13000, 16: 20000, 17: 30000, 18: 48000, 19: 80000,
                     20: 140000}
GP_FRACTION = {"tiny": 0.04, "small": 0.12, "medium": 0.25, "large": 0.5, "huge": 1.0}
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
                "twelve"]

THEME_TO_TRAITS = {"undead": ["undead"], "fey": ["fey"], "nature": ["animal", "beast", "plant", "fungus"],
                   "monster": ["beast", "aberration", "dragon", "giant", "ooze"],
                   "magic": ["construct", "elemental"], "crime": ["humanoid"], "military": ["humanoid"],
                   "politics": ["humanoid"], "ruin": ["undead", "construct"], "disease": ["fungus", "ooze", "undead"],
                   "religion": ["celestial", "fiend", "undead"], "weather": ["elemental"]}
KEYWORD_THEMES = {
    "crime": "thie smuggl bandit crimin gang fence outlaw black market assassin", "trade": "merchant guild trade "
    "caravan market shop broker coin bank", "religion": "temple church priest cult shrine faith god saint order",
    "undead": "undead ghoul ghost grave crypt necro skelet", "fey": "fey fairy sprite hag",
    "monster": "monster beast dragon lair hunt", "nature": "druid forest wild grove farm herd river",
    "ruin": "ruin dig excavat ancient tomb vault delve archae", "magic": "wizard mage arcane spell academy magic "
    "alchem", "military": "army guard militia soldier mercenar watch garrison war", "politics": "council noble "
    "lord court mayor senate tax crown law", "family": "family clan house kin", "mystery": "secret spy mystery "
    "hidden", "disease": "plague sick disease hospice", "craft": "smith craft artisan forge"}


# ---------------------------------------------------------------------------------------------- text helpers
AN_EXCEPT = ("hour", "honest", "honor", "honour", "heir")
A_EXCEPT = ("uni", "use", "usu", "uti", "one", "once", "eu", "ubiq", "uk", "ura")
DETERMINERS = ("a ", "an ", "the ", "some ", "any ", "no ", "this ", "that ", "my ", "his ", "her ", "their ",
               "our ", "your ", "its ", "every ", "each ", "several ", "many ", "two ", "three ", "four ",
               "five ", "six ", "seven ", "eight ", "nine ", "ten ", "half ", "both ")


def article(word):
    w = word.strip().lower()
    if not w:
        return "a"
    if w.startswith(AN_EXCEPT):
        return "an"
    if w.startswith(A_EXCEPT):
        return "a"
    return "an" if w[0] in "aeiou" else "a"


def has_determiner(text):
    t = text.lstrip().lower()
    return t.startswith(DETERMINERS) or t[:1].isdigit() or t.startswith("[[")


IRREGULAR_PLURALS = {"man": "men", "woman": "women", "wife": "wives", "thief": "thieves", "knife": "knives",
                     "child": "children", "ox": "oxen", "goose": "geese", "mouse": "mice", "tooth": "teeth",
                     "foot": "feet", "wolf": "wolves", "elf": "elves", "dwarf": "dwarves", "leaf": "leaves",
                     "half": "halves", "calf": "calves", "loaf": "loaves"}


def pluralize(phrase):
    p = phrase.rstrip()
    if not p:
        return p
    head, sep, last = p.rpartition(" ")
    if "-" in last and not last.endswith("-"):
        h2, _, l2 = last.rpartition("-")
        return (head + sep if head else "") + h2 + "-" + pluralize(l2)
    low = last.lower()
    if low in IRREGULAR_PLURALS:
        new = IRREGULAR_PLURALS[low]
        new = new.capitalize() if last[:1].isupper() else new
    elif low.endswith("man") and len(low) > 3:
        new = last[:-3] + "men"
    elif low.endswith(("s", "x", "z", "ch", "sh")):
        new = last + "es"
    elif low.endswith("y") and len(low) > 1 and low[-2] not in "aeiou":
        new = last[:-1] + "ies"
    else:
        new = last + "s"
    return (head + sep if head else "") + new


def third_person(verb, plural):
    if plural:
        return verb
    v = verb
    if v.endswith(("s", "x", "z", "ch", "sh", "o")):
        return v + "es"
    if v.endswith("y") and len(v) > 1 and v[-2] not in "aeiou":
        return v[:-1] + "ies"
    return v + "s"


def cap(text):
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
        if ch == "[":
            continue
    return text


def _fix_articles(text):
    def sub(m):
        art, word = m.group(1), m.group(2)
        right = article(word)
        if art.lower() == right:
            return m.group(0)
        return (right.capitalize() if art[0].isupper() else right) + " " + word
    return re.sub(r"\b([Aa]n?) ([A-Za-z][\w'-]*)", sub, text)


def tidy(text):
    """Clean spacing and punctuation, fix a/an, capitalize sentence starts, and end with punctuation."""
    s = re.sub(r"\s+", " ", str(text)).strip()
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"([,;:])\s*([,.;:!?])", r"\2", s)
    s = re.sub(r",{2,}", ",", s)
    s = re.sub(r"\.{2,}", ".", s)
    s = _fix_articles(s)
    s = re.sub(r"([.!?]\s+)(\[\[)?([a-z])", lambda m: m.group(1) + (m.group(2) or "") + m.group(3).upper(), s)
    s = cap(s)
    if s and s[-1] not in ".!?\"')]":
        s += "."
    return s


SHORT_WORDS = {"who": 6, "what": 13}
TRAILING_STOP = {"a", "an", "the", "of", "and", "or", "to", "in", "at", "on", "by", "with", "for", "from", "every",
                 "each", "that", "who", "which", "into", "than", "as", "is", "are", "was", "were", "has", "have",
                 "had", "been", "but", "so", "if", "when", "while", "where", "their", "its", "his", "her", "my",
                 "your", "our", "this", "these", "those", "any", "no", "not", "all", "some", "down", "up", "out", "off"}


KEEP_AUX = re.compile(r"^\s*(has|have|had|is|are|was|were)\b", re.IGNORECASE)


def short_for(key, text):
    """The short form of a slot, as {@key.short}. What a story's event is keeps its leading has/is/was so a title reads as
    a sentence ('Finders Keep has given away a salvaged part'), not 'Finders Keep given away a salvaged part'."""
    return short_phrase(text, SHORT_WORDS.get(key, 6), keep_aux=(key == "what"))


def short_phrase(text, words=6, keep_aux=False):
    """A short noun phrase from a slot: drop leading articles, prepositions, and auxiliaries (unless keep_aux). A
    leading name ('Brokk Ironhide, a gruff dwarven cartwright') is reduced to the name."""
    aux = KEEP_AUX.match(str(text or "")) if keep_aux else None
    text = re.sub(r"\s*\([^)]*\)", "", str(text)).strip()          # "Brokk Ironhide (a gruff cartwright)" -> name
    if aux:                                                            # a clause that ends on "that is" isn't finished yet
        bits = [b.strip() for b in re.split(r"[,;:]", text)]
        head = bits[0]
        for nxt in bits[1:]:
            last = head.split()[-1].lower() if head.split() else ""
            if last in TRAILING_STOP or (last.endswith("ly") and len(last) > 4):
                head += " " + nxt
            else:
                break
        text = head.strip()
    else:
        text = re.split(r"[,;:]", text)[0].strip()                     # stop at the first clause break
    if not aux:                                                              # and before a relative clause
        text = re.split(r"\s+(?:who|that|which|whose)\s+", text)[0].strip() or text
    if aux:
        t = str(text).strip()
    else:
        t = re.sub(r"^\s*(the|a|an|in|at|on|by|beside|near|under|beneath|behind|within|inside|outside|along|"
                   r"has|have|had|been|is|are|was|were|being|to|from)\s+", "", str(text).strip(), flags=re.I)
        t = re.sub(r"^\s*(the|a|an|been|being|to)\s+", "", t, flags=re.I)
    if aux:                                             # a second clause ("..., and will not leave") isn't title material
        t = re.split(r"\s+and\s+(?:will|would|won't|cannot|can't|is|are|was|were|has|have|then|now)\b", t, maxsplit=1)[0]
    parts = t.split()
    cut = parts[:words]
    if aux and len(cut) < len(parts):                   # cut by length: don't leave "for using" or "and" hanging
        while len(cut) > 3 and (cut[-1].lower().strip(",.;:") in TRAILING_STOP
                                or (cut[-1].lower().endswith("ing") and cut[-2].lower() in TRAILING_STOP)):
            cut.pop()
    while len(cut) > 2 and cut[-1].lower().strip(",.;:") in TRAILING_STOP and len(cut) < len(parts):
        cut.pop()                                       # don't end a short title on "and", "of", "every"...
    if aux and len(cut) < 2:                            # "has" alone says nothing: fall back to the plain form
        return short_phrase(text, words)
    return " ".join(cut).rstrip(",.;:")


# ---------------------------------------------------------------------------------------------- entries
def entry_id(text):
    return hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:8]


def _tokens(s):
    return [t for t in re.split(r"[\s,]+", str(s or "").strip()) if t]


def parse_entry(spec, base_id=None):
    """Normalize an entry from shorthand 'text|tags|weight|needs|not' or from a dict.

    tags: space separated. Special tags: p:<pack>, t:<tone>, L<min>-<max> (party level range).
    needs: space separated, all required; 'a/b' means a or b. not: space separated, none may be present.
    """
    if isinstance(spec, dict):
        e = dict(spec)
        e.setdefault("t", "")
    else:
        parts = [p.strip() for p in str(spec).split("|")]
        e = {"t": parts[0]}
        if len(parts) > 1:
            e["tags"] = _tokens(parts[1])
        if len(parts) > 2 and parts[2]:
            try:
                e["w"] = float(parts[2])
            except ValueError:
                pass
        if len(parts) > 3:
            e["needs"] = _tokens(parts[3])
        if len(parts) > 4:
            e["not"] = _tokens(parts[4])
    tags, tone, pack, lvl = [], list(e.get("tone") or []), e.get("pack", "core"), e.get("lvl")
    for t in e.get("tags") or []:
        if t.startswith("p:"):
            pack = t[2:]
        elif t.startswith("t:"):
            tone.append(t[2:])
        elif re.fullmatch(r"L-?\d+-\d+", t):
            lo, hi = re.fullmatch(r"L(-?\d+)-(\d+)", t).groups()
            lvl = [int(lo), int(hi)]
        else:
            tags.append(t)
    e["tags"], e["tone"], e["pack"], e["lvl"] = tags, tone, pack, lvl
    e["w"] = float(e.get("w", 1.0))
    e["needs"], e["not"] = list(e.get("needs") or []), list(e.get("not") or [])
    e["id"] = e.get("id") or base_id or entry_id(e["t"])
    # A routing entry is just a pointer to another table, e.g. "{what.crime}". It chooses a topic rather than
    # saying anything, so repeat-avoidance applies to the entries it leads to, not to the pointer.
    e["route"] = bool(re.fullmatch(r"\{[A-Za-z0-9_.]+(\?\d+)?\}", e["t"].strip()))
    return e


# ---------------------------------------------------------------------------------------------- registry
class Registry:
    """Built-in tables and recipes with your edits layered on top."""

    def __init__(self, tables=None, recipes=None, user=None):
        builtin = tables is None
        if tables is None or recipes is None:
            try:
                from . import storydata as data
            except ImportError:
                import storydata as data
            tables = data.TABLES if tables is None else tables
            recipes = data.RECIPES if recipes is None else recipes
        self.base = {}
        for name, spec in tables.items():
            self.base[name] = self._load_table(name, spec)
        if builtin:
            self._add_setting_pack()
            recipes = self._add_item_pack(recipes)
            recipes = self._add_extra_packs(recipes)
        self.base_recipes = copy.deepcopy(recipes)
        self.user = {"version": 1, "packs": None, "tables": {}, "new_tables": {}, "recipes": {}}
        if user:
            self.load_dict(user)
        self._cache = {}

    @staticmethod
    def _load_table(name, spec):
        ents, seen = [], {}
        for raw in spec["entries"]:
            e = parse_entry(raw)
            n = seen.get(e["id"], 0)              # duplicate text in one table keeps distinct ids
            seen[e["id"]] = n + 1
            if n:
                e["id"] = f"{e['id']}_{n}"
            ents.append(e)
        return {"title": spec.get("title", name), "entries": ents}

    def _merge_lines(self, name, lines):
        table = self.base.setdefault(name, {"title": name, "entries": []})
        have = {e["id"] for e in table["entries"]}
        for raw in lines:
            e = parse_entry(raw)
            if e["id"] in have:
                continue
            have.add(e["id"])
            table["entries"].append(e)

    def _add_item_pack(self, recipes):
        """Fold in the Magic Item Generator's flavor tables and its hidden item_lore story type, plus the
        Hallowmead additions (limited to the hallowmead content pack). Returns the recipes to use."""
        try:
            from . import itemdata as idata
        except ImportError:
            try:
                import itemdata as idata
            except ImportError:
                return recipes
        for name, spec in idata.TABLES.items():
            if name not in self.base:
                self.base[name] = self._load_table(name, spec)
        for name, lines in idata.hallowmead_additions().items():
            self._merge_lines(name, lines)
        out = dict(recipes)
        for kind, rec in idata.RECIPES.items():
            out.setdefault(kind, rec)
        return out

    EXTRA_PACKS = ("tavdata", "downdata", "hazards")   # the Inns tab's tables, the Downtime tab's job board and events, and the hazard tables

    def _add_extra_packs(self, recipes):
        """Fold in the tables of the modules listed in EXTRA_PACKS: each may define TABLES, hallowmead_additions(), and
        RECIPES. A module that isn't there is skipped, so older installs keep working."""
        import importlib
        out = dict(recipes)
        for modname in self.EXTRA_PACKS:
            try:
                mod = importlib.import_module("." + modname, __package__) if __package__ else importlib.import_module(modname)
            except ImportError:
                continue
            for name, spec in getattr(mod, "TABLES", {}).items():
                if name not in self.base:
                    self.base[name] = self._load_table(name, spec)
            extra = getattr(mod, "hallowmead_additions", None)
            for name, lines in (extra() if extra else {}).items():
                self._merge_lines(name, lines)
            for kind, rec in getattr(mod, "RECIPES", {}).items():
                out.setdefault(kind, rec)
        return out

    def _add_setting_pack(self):
        """Fold in the Hallowmead content pack. Every entry is limited to the 'hallowmead' pack, so the pack's
        checkbox on the Story tab switches all of it on or off."""
        try:
            from . import hallowmead as hm
        except ImportError:
            try:
                import hallowmead as hm
            except ImportError:
                return
        for name, lines in hm.table_additions().items():
            table = self.base.setdefault(name, {"title": name, "entries": []})
            have = {e["id"] for e in table["entries"]}
            for raw in lines:
                e = parse_entry(raw)
                if e["id"] in have:
                    continue
                have.add(e["id"])
                table["entries"].append(e)

    # ----- lookup
    def names(self):
        return sorted(set(self.base) | set(self.user["new_tables"]))

    def has(self, name):
        return name in self.base or name in self.user["new_tables"]

    def title(self, name):
        if name in self.user["new_tables"]:
            return self.user["new_tables"][name].get("title", name)
        return self.base.get(name, {}).get("title", name)

    def is_user_table(self, name):
        return name in self.user["new_tables"]

    def entries(self, name):
        """Merged entries for a table (built-ins with edits and disables applied, plus your additions)."""
        if name in self._cache:
            return self._cache[name]
        out = []
        if name in self.user["new_tables"]:
            for i, raw in enumerate(self.user["new_tables"][name].get("entries", [])):
                e = parse_entry(raw, base_id=raw.get("id") if isinstance(raw, dict) else None)
                e["user"] = True
                out.append(e)
        elif name in self.base:
            ov = self.user["tables"].get(name, {})
            edits, disabled, weights = ov.get("edit", {}), set(ov.get("disable", [])), ov.get("weights", {})
            for e in self.base[name]["entries"]:
                e = copy.deepcopy(e)
                if e["id"] in edits:
                    merged = {**e, **edits[e["id"]]}
                    e = parse_entry(merged, base_id=e["id"])
                    e["edited"] = True
                if e["id"] in weights:
                    e["w"] = float(weights[e["id"]])
                e["off"] = e["id"] in disabled
                out.append(e)
            for raw in ov.get("add", []):
                e = parse_entry(raw, base_id=raw.get("id") if isinstance(raw, dict) else None)
                e["user"] = True
                e["off"] = e["id"] in disabled
                out.append(e)
        self._cache[name] = out
        return out

    def packs(self):
        p = self.user.get("packs")
        return list(p) if p else list(DEFAULT_PACKS)

    def recipe(self, kind):
        if kind in self.user["recipes"]:
            return copy.deepcopy(self.user["recipes"][kind])
        return copy.deepcopy(self.base_recipes[kind])

    def recipe_names(self):
        return sorted(set(self.base_recipes) | set(self.user["recipes"]))

    def visible_recipe_names(self):
        """Story types to offer in the Story tab (hidden ones, like an item's history, are used by other tools)."""
        return [k for k in self.recipe_names() if not self.recipe(k).get("hidden")]

    # ----- editing (all persisted by save())
    def _touch(self, name=None):
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(name, None)

    def _ov(self, name):
        return self.user["tables"].setdefault(name, {"add": [], "edit": {}, "disable": [], "weights": {}})

    def add_entry(self, table, spec):
        e = parse_entry(spec)
        if table in self.user["new_tables"]:
            e["id"] = e["id"] if e["id"] not in {x["id"] for x in self.entries(table)} else \
                entry_id(e["t"] + str(len(self.entries(table))))
            raw = {k: e[k] for k in ("id", "t", "w", "needs", "not", "pack", "lvl", "tone")}
            raw["tags"] = e["tags"]
            self.user["new_tables"][table]["entries"].append(raw)
        elif table in self.base:
            if e["id"] in {x["id"] for x in self.entries(table)}:
                e["id"] = entry_id(e["t"] + str(len(self.entries(table))))
            raw = {k: e[k] for k in ("id", "t", "w", "needs", "not", "pack", "lvl", "tone")}
            raw["tags"] = e["tags"]
            self._ov(table)["add"].append(raw)
        else:
            raise KeyError(table)
        self._touch(table)
        return e["id"]

    def edit_entry(self, table, eid, **fields):
        """Change fields of any entry. Built-ins keep their id so the edit survives updates."""
        fields = {k: v for k, v in fields.items() if k in ("t", "w", "tags", "needs", "not", "pack", "lvl", "tone")}
        if table in self.user["new_tables"]:
            for raw in self.user["new_tables"][table]["entries"]:
                if raw.get("id") == eid:
                    raw.update(fields)
        else:
            ov = self._ov(table)
            added = next((r for r in ov["add"] if r.get("id") == eid), None)
            if added is not None:
                added.update(fields)
            else:
                ov["edit"].setdefault(eid, {}).update(fields)
        self._touch(table)

    def set_enabled(self, table, eid, on=True):
        ov = self._ov(table)
        if on and eid in ov["disable"]:
            ov["disable"].remove(eid)
        if not on and eid not in ov["disable"]:
            ov["disable"].append(eid)
        self._touch(table)

    def remove_entry(self, table, eid):
        """Delete one of your own entries (built-ins can only be disabled)."""
        if table in self.user["new_tables"]:
            lst = self.user["new_tables"][table]["entries"]
            lst[:] = [r for r in lst if r.get("id") != eid]
        else:
            ov = self._ov(table)
            ov["add"] = [r for r in ov["add"] if r.get("id") != eid]
        self._touch(table)

    def reset_entry(self, table, eid):
        ov = self.user["tables"].get(table)
        if ov:
            ov["edit"].pop(eid, None)
            ov["weights"].pop(eid, None)
            if eid in ov["disable"]:
                ov["disable"].remove(eid)
        self._touch(table)

    def new_table(self, name, title=""):
        if self.has(name):
            raise ValueError(f"A table called '{name}' already exists.")
        if not re.fullmatch(r"[a-z0-9_.]+", name):
            raise ValueError("Use lowercase letters, digits, dots, and underscores for table names.")
        self.user["new_tables"][name] = {"title": title or name, "entries": []}
        self._touch()

    def delete_table(self, name):
        self.user["new_tables"].pop(name, None)
        self._touch()

    def set_recipe(self, kind, recipe):
        self.user["recipes"][kind] = copy.deepcopy(recipe)

    def reset_recipe(self, kind):
        self.user["recipes"].pop(kind, None)

    def set_packs(self, packs):
        self.user["packs"] = list(packs) if packs else None

    # ----- persistence
    def to_dict(self):
        return copy.deepcopy(self.user)

    def load_dict(self, d):
        base = {"version": 1, "packs": None, "tables": {}, "new_tables": {}, "recipes": {}}
        base.update({k: v for k, v in (d or {}).items() if k in base})
        self.user = base
        self._touch()

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.user, f, indent=1, ensure_ascii=False)

    def load(self, path):
        with open(path, encoding="utf-8") as f:
            self.load_dict(json.load(f))

    # ----- validation
    def validate(self):
        """Problems worth fixing: unknown table references, unbalanced braces, empty tables."""
        problems = []
        known = set(self.names()) | set(PROVIDERS)
        for name in self.names():
            ents = [e for e in self.entries(name) if not e.get("off")]
            if not ents:
                problems.append((name, "", "Every entry is disabled or the table is empty."))
            for e in self.entries(name):
                problems += [(name, e["id"], m) for m in check_template(e["t"], known)]
        for kind in self.recipe_names():
            r = self.recipe(kind)
            for s in r.get("slots", []) + r.get("extras", []):
                if s.get("table") and s["table"] not in known:
                    problems.append((f"recipe:{kind}", s["key"], f"Slot table '{s['table']}' doesn't exist."))
            for t in r.get("compose", []) + [r.get("title", "")]:
                problems += [(f"recipe:{kind}", "", m) for m in check_template(t, known, allow_vars=True)]
        return problems


def check_template(template, known_tables, allow_vars=False):
    out = []
    if template.count("{") != template.count("}"):
        out.append(f"Unbalanced braces in: {template[:60]}")
    for tok in TOKEN.findall(template):
        p = parse_token(tok)
        if p["mode"] == "table" and p["table"] not in known_tables:
            out.append(f"Unknown table '{p['table']}' in: {template[:60]}")
        if p["mode"] == "unknown":
            out.append(f"Can't read {{{tok}}}")
    return out


# ---------------------------------------------------------------------------------------------- tokens
AGREE = {"is": ("is", "are"), "was": ("was", "were"), "has": ("has", "have"), "does": ("does", "do")}


def parse_token(tok):
    t = tok.strip()
    d = {"mode": "unknown", "raw": tok, "cap": False, "art": None, "plural": False, "chance": None, "bind": None}
    if t.startswith("^"):
        d["cap"], t = True, t[1:].strip()
    m = re.match(r"^(a|an|the)\s+(.+)$", t)
    if m:
        d["art"], t = ("the" if m.group(1) == "the" else "a"), m.group(2).strip()
    m = re.match(r"^(pl|plural)\s+(.+)$", t)
    if m:
        d["plural"], t = True, m.group(2).strip()
    if t.startswith("@"):
        body = t[1:]
        if "=" in body:
            name, _, tab = body.partition("=")
            d["bind"] = name.strip()
            t = tab.strip()
        else:
            d.update(mode="var", var=body.strip())
            return d
    m = re.fullmatch(r"#(-?\d+)-(-?\d+)", t)
    if m:
        d.update(mode="num", lo=int(m.group(1)), hi=int(m.group(2)))
        return d
    m = re.fullmatch(r"n:(\d+)-(\d+)", t)
    if m:
        d.update(mode="numword", lo=int(m.group(1)), hi=int(m.group(2)))
        return d
    if t in AGREE:
        d.update(mode="agree", word=t)
        return d
    if t.startswith("v:") and len(t) > 2:
        d.update(mode="verb", verb=t[2:].strip())
        return d
    if t == "dc" or t.startswith("dc:"):
        d.update(mode="dc", adj=t[3:].strip() if t.startswith("dc:") else "normal")
        return d
    m = re.fullmatch(r"lvl([+-]\d+)?", t)
    if m:
        d.update(mode="lvl", off=int(m.group(1) or 0))
        return d
    if t.startswith("gp:"):
        d.update(mode="gp", size=t[3:].strip())
        return d
    if t.startswith("ctx:"):
        d.update(mode="ctx", key=t[4:].strip())
        return d
    m = re.fullmatch(r"([A-Za-z0-9_.]+)(?:\?(\d+))?", t)
    if m:
        d.update(mode="table", table=m.group(1), chance=int(m.group(2)) if m.group(2) else None)
    return d


# ---------------------------------------------------------------------------------------------- campaign
def infer_tags(*texts):
    """Theme tags guessed from words in names, notes, and tags (so your own factions steer the stories)."""
    blob = " ".join(str(t or "") for t in texts).lower()
    out = set()
    for theme, words in KEYWORD_THEMES.items():
        # each keyword must start a word, so "war" matches "warden" but "of" or "gang" can't match mid-word
        if any(re.search(r"\b" + re.escape(w), blob) for w in words.split() if len(w) >= 3):
            out.add(theme)
    return sorted(out)


@dataclass
class Campaign:
    """Everything the generator can draw on from your own world."""
    level: int = 1
    party_size: int = 5
    factions: list = field(default_factory=list)       # {"title","tags","kind","goals","points","tier","rivals"}
    npcs: list = field(default_factory=list)           # {"title","role","ancestry","tags"}
    locations: list = field(default_factory=list)      # {"title","kind","tags"}
    events: list = field(default_factory=list)         # {"title","when","tags"}
    quests: list = field(default_factory=list)         # {"title","tags"}
    creatures: list = field(default_factory=list)      # {"name","level","traits"}
    ancestry_weights: dict = field(default_factory=dict)
    season: str = ""
    party: list = field(default_factory=list)

    @classmethod
    def from_pages(cls, pages, party=None, creatures=None, level=None, party_size=None):
        c = cls(level=int(level or 1), party_size=int(party_size or 5), party=list(party or []),
                creatures=list(creatures or []))
        for p in pages or []:
            typ, title = p.get("type", ""), p.get("title", "")
            if not title:
                continue
            tags = [t.lower() for t in p.get("tags", [])]
            if "gm-only" in tags:
                continue                      # secrets never feed a generated story
            body = p.get("body", "")
            tags = sorted(set(tags) | set(infer_tags(title, " ".join(tags), p.get("kind", ""), p.get("role", ""),
                                                      body[:400])))
            if typ == "Faction":
                rep = p.get("rep") or {}
                c.factions.append({"title": title, "tags": tags, "kind": p.get("kind", ""),
                                   "avoid": [a for a in (p.get("avoid") or []) if isinstance(a, str)],
                                   "goals": p.get("goals") or [], "points": rep.get("points", 0),
                                   "rivals": p.get("rivals") or [], "status": p.get("status", "")})
            elif typ == "NPC" and p.get("status", "alive") != "dead":
                c.npcs.append({"title": title, "role": p.get("role", ""), "ancestry": p.get("ancestry", ""),
                               "tags": tags, "avoid": [a for a in (p.get("avoid") or []) if isinstance(a, str)]})
            elif typ == "Location":
                c.locations.append({"title": title, "kind": p.get("kind", ""), "tags": tags, "the": bool(p.get("the")),
                                    "preps": [x for x in (p.get("preps") or []) if isinstance(x, str) and x.strip()]})
            elif typ == "Event" and p.get("status", "upcoming") != "happened":
                c.events.append({"title": title, "when": p.get("when", ""), "tags": tags})
            elif typ == "Quest" and p.get("status", "active") in ("rumored", "active", ""):
                c.quests.append({"title": title, "tags": tags})
        return c

    def counts(self):
        return {"factions": len(self.factions), "npcs": len(self.npcs), "locations": len(self.locations),
                "events": len(self.events), "quests": len(self.quests), "creatures": len(self.creatures)}


# ---------------------------------------------------------------------------------------------- history
class History:
    """Remembers recent picks so the same entries aren't chosen again and again. With recent > 0 it also keeps the last
    few picks of each table, and a table won't hand them out again while it has enough other entries to choose from."""

    def __init__(self, strength=0.4, decay=0.75, recent=0):
        self.score, self.strength, self.decay = {}, strength, decay
        self.recent_n, self.recent = int(recent), {}

    def note(self, table, key):
        if self.recent_n > 0:
            lst = self.recent.setdefault(table, [])
            lst.append(key)
            del lst[:-max(self.recent_n, 1)]

    def recent_ids(self, table, k):
        return set(self.recent.get(table, [])[-k:]) if (self.recent_n > 0 and k > 0) else set()

    def tick(self):
        for k in list(self.score):
            self.score[k] *= self.decay
            if self.score[k] < 0.05:
                del self.score[k]

    def use(self, key):
        self.score[key] = self.score.get(key, 0.0) + 1.0

    def factor(self, key):
        s = self.score.get(key, 0.0)
        return self.strength ** min(s, 3.0) if s else 1.0


# ---------------------------------------------------------------------------------------------- results
@dataclass
class Rolled:
    text: str = ""
    tags: set = field(default_factory=set)
    entities: list = field(default_factory=list)
    entry: str = ""


@dataclass
class Slot:
    key: str
    label: str
    text: str = ""
    table: str = ""
    extra: bool = False
    locked: bool = False
    edited: bool = False
    tags: list = field(default_factory=list)
    entities: list = field(default_factory=list)
    entry: str = ""

    def display(self):
        return cap(self.text)


@dataclass
class Story:
    kind: str
    title_prefix: str = ""
    settings: dict = field(default_factory=dict)
    slots: OrderedDict = field(default_factory=OrderedDict)
    summary: str = ""
    summary_edited: bool = False
    title: str = ""
    title_edited: bool = False
    rep: list = field(default_factory=list)
    encounter: dict = field(default_factory=dict)
    page_type: str = "Note"
    status: str = ""
    themes: list = field(default_factory=list)
    env: str = ""
    problems: list = field(default_factory=list)

    @property
    def entities(self):
        seen, out = set(), []
        for s in self.slots.values():
            for e in s.entities:
                key = (e.get("type"), e.get("title"))
                if key not in seen and e.get("title"):
                    seen.add(key)
                    out.append(e)
        return out

    def main(self):
        return [s for s in self.slots.values() if not s.extra]

    def extras(self):
        return [s for s in self.slots.values() if s.extra and s.text]

    def to_dict(self):
        return {"kind": self.kind, "title_prefix": self.title_prefix, "settings": self.settings,
                "slots": [vars_of(s) for s in self.slots.values()], "summary": self.summary,
                "summary_edited": self.summary_edited, "title": self.title, "title_edited": self.title_edited,
                "rep": self.rep,
                "encounter": self.encounter, "page_type": self.page_type, "status": self.status,
                "themes": self.themes, "env": self.env}

    @classmethod
    def from_dict(cls, d):
        s = cls(kind=d.get("kind", "rumor"), title_prefix=d.get("title_prefix", ""), settings=d.get("settings", {}),
                summary=d.get("summary", ""), summary_edited=d.get("summary_edited", False), title=d.get("title", ""),
                title_edited=d.get("title_edited", False),
                rep=d.get("rep", []), encounter=d.get("encounter", {}), page_type=d.get("page_type", "Note"),
                status=d.get("status", ""), themes=d.get("themes", []), env=d.get("env", ""))
        for sd in d.get("slots", []):
            slot = Slot(**{k: sd[k] for k in Slot.__dataclass_fields__ if k in sd})
            s.slots[slot.key] = slot
        return s

    def plain(self):
        """The whole story as readable text."""
        lines = [self.title, ""]
        for sl in self.main():
            lines.append(f"{sl.label}: {sl.display()}")
        for sl in self.extras():
            lines.append(f"{sl.label}: {sl.display()}")
        lines += ["", self.summary]
        return "\n".join(lines)

    def to_page(self, link_generated=False):
        """Fields for a notebook page. Campaign entities become [[links]]; generated NPCs too if asked."""
        def link(text):
            for e in self.entities:
                if e.get("campaign") or link_generated:
                    t = e["title"]
                    if not t or f"[[{t}" in text:
                        continue
                    m = re.search(re.escape(t), text, re.IGNORECASE)
                    if m:
                        shown = m.group(0)
                        text = text[:m.start()] + (f"[[{t}]]" if shown == t else f"[[{t}|{shown}]]") + text[m.end():]
            return text
        lines = []
        for sl in self.main():
            lines.append(f"{sl.label}: {link(sl.display())}")
        extras = [f"{sl.label}: {link(sl.display())}" for sl in self.extras()]
        body = "\n".join(lines)
        if extras:
            body += "\n\n" + "\n".join(extras)
        body += f"\n\nSummary: {link(self.summary)}"
        tags = [t for t in self.themes] + ([self.env] if self.env else [])
        return {"title": self.title, "type": self.page_type, "status": self.status, "tags": tags, "body": body,
                "story": self.to_dict()}


def vars_of(slot):
    return {k: getattr(slot, k) for k in Slot.__dataclass_fields__}


# ---------------------------------------------------------------------------------------------- context
class Ctx:
    """State for one generation: tags in play, remembered values, and the rolling logic."""

    def __init__(self, gen, settings, base_tags=()):
        self.gen = gen
        self.reg = gen.registry
        self.rng = gen.rng
        self.campaign = gen.campaign
        self.settings = settings
        self.tags = set(base_tags)
        self.themes = set(settings.get("themes") or [])
        self.envs = {settings["env"]} if settings.get("env") and settings["env"] != "any" else set()
        self.tone = settings.get("tone", "any")
        self.level = int(settings.get("level", gen.campaign.level))
        self.focus = float(settings.get("focus", 0.6))
        self.packs = set(settings.get("packs") or gen.registry.packs())
        self.use_campaign = float(settings.get("use_campaign", 0.5))
        share = settings.get("pack_share")                            # None = no limit on how often flavor packs appear
        self.pack_share = None if share is None else max(0.0, min(0.95, float(share)))
        self.flavor_packs = set(settings.get("flavor_packs") or ["hallowmead"])
        self.anchor = set()                                           # themes the story's event brought in (see anchor_slot)
        self.strict_anchor = False                                    # True while rolling a slot marked "strict_anchor"
        self.tone_strict = float(settings.get("tone_strict", 1.0))     # 1.0 = stories behave as they always did
        self.tone_loose = float(settings.get("tone_loose", 1.0))
        self.vars = {}
        self.plural = False
        self.depth = 0
        self.problems = []
        self.slot_tags = set()
        self.slot_entities = []
        self.used_titles = set()          # campaign people, places, and factions this story already mentions
        self.meta = {}
        self.theme_bias = Counter()
        self.table_bias = {}

    # ----- weighting
    def weight(self, e):
        if e.get("off") or e["pack"] not in self.packs:
            return 0.0
        if e["tone"] and self.tone != "any" and self.tone not in e["tone"]:
            return 0.0
        if e["lvl"] and not (e["lvl"][0] <= self.level <= e["lvl"][1]):
            return 0.0
        tags = self.tags
        for need in e["needs"]:
            if not any(x in tags for x in need.split("/")):
                return 0.0
        for bad in e["not"]:
            if bad in tags:
                return 0.0
        w = e["w"]
        if any(("avoid:" + t) in tags for t in e["tags"]):
            return 0.0                                  # the subject's page says this theme would reveal a secret
        if self.tone != "any" and self.tone in e["tone"]:
            w *= 2.5
        if self.tone != "any" and not e["tone"]:
            w *= self.tone_strict                           # with a tone chosen, entries with no tone count for less
        elif self.tone == "any" and e["tone"]:
            w *= self.tone_loose                            # with no tone chosen, tone-specific entries count for less
        etags = set(e["tags"])
        f = self.focus
        boost, pen = 1 + 60 * f * f, (1 - f) ** 3
        et = etags & THEME_SET
        if self.themes and et:
            if et & self.themes:
                w *= boost                                   # the theme you asked for (or that was rolled)
            elif et & (self.tags & THEME_SET):
                w *= 1 + 0.03 * (boost - 1)                  # a theme that earlier slots happened to bring in
            else:
                w *= pen
        if self.anchor and et:                                # the reason should follow the event, not the whole theme list
            if et & self.anchor:
                w *= 3.0
            elif self.strict_anchor:
                return 0.0                                  # a strict slot (a hook's motive) never takes another theme's entry
            elif et & self.themes:
                w *= 0.35
        ev = etags & set(ENVS)
        if self.envs and ev:
            if self.pack_share is not None and e["pack"] in self.flavor_packs:
                w *= 1.0 if ev & self.envs else 0.12      # setting lines are all "underground": no extra boost for that
            else:
                w *= 6.0 if ev & self.envs else 0.12
        if e["id"] in self.table_bias:
            w *= self.table_bias[e["id"]]
        return w if e.get("route") else w * self.gen.history.factor(e["id"])

    def _share_adjust(self, cands):
        """Hold the setting's own lines (the flavor packs) to a chosen share of a table's weight, so a small pool of
        setting lines can't crowd out everything else. No effect unless pack_share is set."""
        if self.pack_share is None:
            return cands
        flavor = [(e, w) for e, w in cands if e["pack"] in self.flavor_packs]
        core = [(e, w) for e, w in cands if e["pack"] not in self.flavor_packs]
        if not flavor or not core:
            return cands
        if self.pack_share <= 0:
            return core
        scale = (self.pack_share / (1 - self.pack_share)) * sum(w for _, w in core) / sum(w for _, w in flavor)
        return core + [(e, w * scale) for e, w in flavor]

    def _drop_recent(self, name, cands):
        """Leave out what this table gave out most recently, as long as plenty of other entries remain."""
        hist = self.gen.history
        k = min(hist.recent_n, len(cands) // 2)
        recent = hist.recent_ids(name, k)
        if not recent:
            return cands
        kept = [(e, w) for e, w in cands if e.get("route") or e["id"] not in recent]
        return kept if len(kept) >= 3 else cands

    # ----- rolling
    def roll(self, name, bind=None):
        if self.depth > MAX_DEPTH:
            self.problems.append(("depth", name))
            return Rolled("")
        if name in PROVIDERS and not self.reg.has(name):
            self.depth += 1
            r = PROVIDERS[name](self, name)
            self.depth -= 1
            self._take(r)
            return r
        if not self.reg.has(name):
            self.problems.append(("unknown", name))
            return Rolled(f"[?{name}]")
        entries = self.reg.entries(name)
        cands = [(e, w) for e in entries if (w := self.weight(e)) > 0]
        if not cands:                                    # relax needs/tone/level but respect disabled, packs, and secrets
            cands = [(e, 1.0) for e in entries if not e.get("off") and e["pack"] in self.packs
                     and not any(("avoid:" + t) in self.tags for t in e["tags"])]
        if not cands:
            self.problems.append(("empty", name))
            return Rolled("")
        cands = self._drop_recent(name, self._share_adjust(cands))
        e = self.rng.choices([c[0] for c in cands], weights=[c[1] for c in cands], k=1)[0]
        if not e.get("route"):
            self.gen.history.use(e["id"])
            self.gen.history.note(name, e["id"])
        self.depth += 1
        text = self.render(e["t"])
        self.depth -= 1
        r = Rolled(text, set(e["tags"]), [], e["id"])
        self._take(r)
        return r

    def _take(self, r):
        self.tags |= r.tags
        self.slot_tags |= r.tags
        self.slot_entities.extend(r.entities)

    def render(self, template):
        return TOKEN.sub(lambda m: self.token(m.group(1)), template)

    def token(self, tok):
        p = parse_token(tok)
        mode = p["mode"]
        out = ""
        if mode == "var":
            out = str(self.vars.get(p["var"], ""))
            if out == "" and p["var"] not in self.vars:
                self.problems.append(("var", p["var"]))
        elif mode == "num":
            out = str(self.rng.randint(min(p["lo"], p["hi"]), max(p["lo"], p["hi"])))
        elif mode == "numword":
            n = self.rng.randint(p["lo"], p["hi"])
            out = NUMBER_WORDS[n] if n < len(NUMBER_WORDS) else str(n)
        elif mode == "agree":
            out = AGREE[p["word"]][1 if self.plural else 0]
        elif mode == "verb":
            out = third_person(p["verb"], self.plural)
        elif mode == "dc":
            out = f"DC {self.dc(p['adj'])}"
        elif mode == "lvl":
            out = str(self.level + p["off"])
        elif mode == "gp":
            out = self.gp(p["size"])
        elif mode == "ctx":
            out = self.context_value(p["key"])
        elif mode == "table":
            if p["chance"] is not None and self.rng.randint(1, 100) > p["chance"]:
                return ""
            r = self.roll(p["table"])
            out = r.text
            if p["bind"]:
                self.vars[p["bind"]] = out
        else:
            self.problems.append(("token", tok))
            return f"[?{tok}]"
        if p["plural"]:
            out = pluralize(out)
        if p["art"] and out:
            if p["art"] == "a":
                out = out if has_determiner(out) else f"{article(out)} {out}"
            else:
                out = out if out.lower().startswith("the ") else f"the {out}"
        if p["cap"]:
            out = cap(out)
        return out

    def dc(self, adj="normal"):
        base = DC_BY_LEVEL.get(max(-1, min(25, self.level)), 20)
        return base + DC_ADJ.get(adj, 0)

    def gp(self, size):
        lvl = max(1, min(20, self.level))
        raw = CURRENCY_BY_LEVEL[lvl] * GP_FRACTION.get(size, 0.25)
        step = 5 if raw < 100 else 10 if raw < 1000 else 50 if raw < 10000 else 500
        n = max(step, int(round(raw / step) * step))
        return f"about {n:,} gp"

    def context_value(self, key):
        if key == "season":
            return self.settings.get("season") or ""
        if key == "theme":
            return (self.settings.get("themes") or [""])[0]
        if key == "env":
            return self.settings.get("env", "")
        if key == "level":
            return str(self.level)
        return ""

    def begin_slot(self):
        self.slot_tags = set()
        self.slot_entities = []


# ---------------------------------------------------------------------------------------------- providers
def _choose_campaign(ctx, items, key="title"):
    """Pick one campaign item, favoring ones whose tags match the story's themes and haven't just been used."""
    if not items:
        return None
    ws = []
    for it in items:
        overlap = len(set(it.get("tags", [])) & (ctx.themes | ctx.envs))
        w = (1 + 2.5 * overlap) * ctx.gen.history.factor("campaign:" + str(it.get(key, "")))
        ws.append(max(0.01, w))
    it = ctx.rng.choices(items, weights=ws, k=1)[0]
    ctx.gen.history.use("campaign:" + str(it.get(key, "")))
    return it


def _unused(ctx, items, key="title"):
    """Campaign items the story hasn't used yet, so a faction isn't both the patron and the opposition. Items whose
    page lists themes to avoid (a secret they must never meet) are skipped when the story is about such a theme."""
    return [i for i in items if (i.get(key) or "") not in ctx.used_titles
            and not (set(i.get("avoid") or []) & ctx.themes)]


def role_phrase(role):
    """A page's role as it reads after a name: 'Chief of Finders Keep' becomes 'the chief of Finders Keep', 'Guard 4'
    becomes 'a guard', and 'merchant' becomes 'a merchant'. Only the title is lowercased, never the place after 'of'."""
    r = re.sub(r"\s+\d+$", "", str(role or "").strip())
    if not r:
        return ""
    head, sep, tail = r.partition(" of ")
    low = head.lower() if (sep or r[:1].isupper()) else head
    if sep and head[:1].isupper():
        return f"the {low} of {tail}"
    return f"{article(low)} {low}" + (f" of {tail}" if sep else "")


LOCATION_PREPS = ["at", "at", "in", "near", "just outside", "behind"]


def inline_name(title):
    """A page title as it reads mid-sentence: 'The Lantern Market' becomes 'the Lantern Market'."""
    return re.sub(r"^The\s+", "the ", str(title).strip())


def _from_campaign(listname, etype, fallback):
    def provider(ctx, name):
        items = _unused(ctx, getattr(ctx.campaign, listname), "title" if listname != "creatures" else "name")
        if items and ctx.rng.random() < ctx.use_campaign:
            it = _choose_campaign(ctx, items, "title" if listname != "creatures" else "name")
            title = it.get("title") or it.get("name")
            tags = set(it.get("tags", [])) | ({"k:faction"} if etype == "Faction" else {"k:npc"} if etype == "NPC"
                                              else set())
            tags |= {"avoid:" + a for a in it.get("avoid") or []}
            text = inline_name(title)
            if it.get("the") and not text.lower().startswith("the "):
                text = "the " + text
            if etype == "NPC" and it.get("role"):
                text = f"{text} ({role_phrase(it['role'])})"
            if etype == "Location":                     # "where" reads as a place phrase: "at the Lantern Market"
                text = f"{ctx.rng.choice(it.get('preps') or LOCATION_PREPS)} {text}"
            ent = [{"type": etype, "title": title, "campaign": True}]
            return Rolled(text, tags, ent, "campaign")
        return ctx.roll(fallback)
    return provider


def _forced_ancestry(ctx):
    """An ancestry requested with an 'anc:<name>' tag (used by tools that need a maker of a given people)."""
    for t in sorted(ctx.tags):
        if t.startswith("anc:"):
            return t[4:].replace("_", " ").title()
    return ""


def _p_npc_named(ctx, name):
    ancestry = _forced_ancestry(ctx) or _names.pick_ancestry(ctx.rng, ctx.envs, ctx.campaign.ancestry_weights or None)
    nm = _names.make_name(ancestry, ctx.rng)
    occ = ctx.roll("occupation")
    trait = ctx.roll("person.adj").text
    tags = set(occ.tags) | {"k:npc"}
    adj = _names.adjective(ancestry)
    desc = f"{trait} {adj} {occ.text}".strip()
    text = f"{nm} ({article(desc)} {desc})"
    ent = [{"type": "NPC", "title": nm, "campaign": False, "ancestry": ancestry, "role": occ.text, "trait": trait}]
    return Rolled(text, tags, ent, "npc.named")


def _p_faction_new(ctx, name):
    nm = ctx.roll("faction.name")
    kind = ctx.roll("faction.kind")
    title = re.sub(r"^(the)\s+", "", nm.text.strip(), flags=re.I)
    text = f"{nm.text} ({article(kind.text)} {kind.text})" if ctx.rng.random() < 0.7 else nm.text
    ent = [{"type": "Faction", "title": title, "display": nm.text.strip(), "campaign": False, "kind": kind.text}]
    return Rolled(text, set(kind.tags) | {"k:faction"}, ent, "faction.new")


def _p_ancestry(ctx, name):
    a = _forced_ancestry(ctx) or _names.pick_ancestry(ctx.rng, ctx.envs, ctx.campaign.ancestry_weights or None)
    return Rolled(a.lower())


def _p_ancestry_adj(ctx, name):
    a = _forced_ancestry(ctx) or _names.pick_ancestry(ctx.rng, ctx.envs, ctx.campaign.ancestry_weights or None)
    return Rolled(_names.adjective(a))


def _p_creature(ctx, name):
    pool = ctx.campaign.creatures
    if pool:
        lo, hi = ctx.level - 2, ctx.level + 3
        want = set()
        for t in ctx.themes:
            want |= set(THEME_TO_TRAITS.get(t, []))
        ok = [c for c in pool if lo <= int(c.get("level", 0)) <= hi]
        themed = [c for c in ok if want & {str(t).lower() for t in c.get("traits", [])}] if want else []
        cands = themed or ok
        if cands:
            c = ctx.rng.choice(cands)
            ent = [{"type": "Creature", "title": c["name"], "campaign": False}]
            return Rolled(c["name"].lower(), {"k:creature"}, ent, "creature")
    r = ctx.roll("creature.generic")
    r.tags = set(r.tags) | {"k:creature"}
    return r


PROVIDERS = {
    "npc.named": _p_npc_named,
    "faction.new": _p_faction_new,
    "ancestry": _p_ancestry,
    "ancestry.adj": _p_ancestry_adj,
    "creature": _p_creature,
    "campaign.npc": _from_campaign("npcs", "NPC", "npc.named"),
    "campaign.faction": _from_campaign("factions", "Faction", "faction.generic"),
    "campaign.location": _from_campaign("locations", "Location", "where.any"),
    "campaign.event": _from_campaign("events", "Event", "when.event.generic"),
    "campaign.quest": _from_campaign("quests", "Quest", "task"),
}


def _rep_provider(ctx, name):
    """Reputation consequences for any faction in the story: helping and hindering."""
    facs = [e for s in ctx.gen._current_story_entities(ctx) for e in [s] if e.get("type") == "Faction"]
    if not facs:
        return Rolled("")
    f = facs[0].get("display") or facs[0]["title"]
    f_title = facs[0]["title"]
    kind = {"inn_hook": "hook"}.get(ctx.settings.get("kind", ""), ctx.settings.get("kind", ""))
    sizes = {"hook": [("minor", 3), ("moderate", 5), ("major", 2)],
             "faction_move": [("minor", 2), ("moderate", 5), ("major", 3)]}.get(kind, [("minor", 4), ("moderate", 4), ("major", 1)])
    help_size = ctx.rng.choices([s for s, _ in sizes], weights=[w for _, w in sizes], k=1)[0]
    harm_size = ctx.rng.choices(["minor", "moderate", "major"], weights=[4, 4, 1], k=1)[0]
    pts = {"minor": 1, "moderate": 2, "major": 5}
    ctx.meta["rep"] = [{"faction": f_title, "kind": "favor", "size": help_size, "points": pts[help_size],
                        "when": "helps"},
                       {"faction": f_title, "kind": "disservice", "size": harm_size, "points": -pts[harm_size],
                        "when": "hinders"}]

    def points(n):
        return f"{n} Reputation Point{'s' if n != 1 else ''}"
    return Rolled(f"Helping is {article(help_size)} {help_size} favor with {f} (+{points(pts[help_size])}). "
                  f"Hindering is {article(harm_size)} {harm_size} disservice (-{points(pts[harm_size])}).")


PROVIDERS["rep.effects"] = _rep_provider


# ---------------------------------------------------------------------------------------------- generator
def _seed_tags(settings):
    tags = set(settings.get("themes") or [])
    if settings.get("env") and settings["env"] != "any":
        tags.add(settings["env"])
    if settings.get("season"):
        tags.add(settings["season"])
    tags.add("scene:" + (settings.get("scene") or "any"))
    if settings.get("tone") and settings["tone"] != "any":
        tags.add("tone:" + settings["tone"])
    return tags


class Generator:
    def __init__(self, registry=None, campaign=None, history=None, rng=None):
        self.registry = registry or default_registry()
        self.campaign = campaign or Campaign()
        self.history = history or DEFAULT_HISTORY
        self.rng = rng or random.Random()
        self._story = None

    # ----- public
    def generate(self, kind, themes=None, env="any", tone="any", level=None, focus=0.6, scene="any",
                 use_campaign=0.5, season="", packs=None, seed=None, extra_tags=None, presets=None, pack_share=None,
                 anchor=None):
        """Roll a story. presets pins slots before anything else is rolled, e.g.
        {"who": {"text": "Gutterlight Guild", "tags": ["crime", "k:faction"], "entities": [...]}}: the story is
        then built around it (and takes its themes from the preset's tags unless you chose themes)."""
        if seed is not None:
            self.rng = random.Random(seed)
        self.history.tick()
        presets = {k: v for k, v in (presets or {}).items() if v and str(v.get("text", "")).strip()}
        if presets and not themes:
            themes = [t for v in presets.values() for t in v.get("tags", []) if t in THEME_SET][:2]
        recipe = self.registry.recipe(kind)
        settings = {"kind": kind, "themes": list(themes or []), "env": env, "tone": tone,
                    "level": int(level if level is not None else self.campaign.level), "focus": float(focus),
                    "scene": scene, "use_campaign": float(use_campaign),
                    "season": season or self.campaign.season or "", "packs": list(packs) if packs else None,
                    "extra_tags": list(extra_tags or []), "pack_share": pack_share, "anchor": anchor}
        story = Story(kind=kind, title_prefix=recipe.get("title", kind.title()), settings=settings,
                      page_type=recipe.get("page_type", "Note"), status=recipe.get("status", ""))
        ctx = Ctx(self, settings, _seed_tags(settings) | set(settings["extra_tags"]))
        ctx.presets = presets
        for v in presets.values():
            ctx.tags |= set(v.get("tags", []))
        self._prepare(ctx, story, recipe)
        self._fill(ctx, story, recipe, [s["key"] for s in recipe["slots"] + recipe.get("extras", [])])
        self._finish(ctx, story, recipe)
        return story

    def generate_batch(self, kind, n, tries=8, **kw):
        """n stories that differ from each other: no two share the same event ('what') or title, so pressing Generate
        never shows three copies of one idea. Falls back to repeats only if the tables really can't supply more."""
        out, whats, titles = [], set(), set()
        for _ in range(max(0, int(n))):
            story = None
            for _t in range(max(1, tries)):
                cand = self.generate(kind, **kw)
                key = re.sub(r"\s+", " ", cand.slots["what"].text.strip().lower()) if "what" in cand.slots else cand.summary
                if key not in whats and cand.title not in titles:
                    story = cand
                    break
                story = story or cand
            whats.add(re.sub(r"\s+", " ", story.slots["what"].text.strip().lower()) if "what" in story.slots else story.summary)
            titles.add(story.title)
            out.append(story)
        return out

    def reroll(self, story, keys=None, themes=None):
        """Reroll the given slots, or every slot that isn't locked or edited. Extras that depend on the main
        slots are rerolled when a main slot changes. Pass themes to change the theme and reroll unlocked slots."""
        recipe = self.registry.recipe(story.kind)
        all_defs = recipe["slots"] + recipe.get("extras", [])
        if themes is not None:
            story.settings["themes"] = list(themes)
            story.themes = list(themes)
        explicit = keys is not None
        main_keys = {d["key"] for d in recipe["slots"]}
        todo = []
        for d in all_defs:
            sl = story.slots.get(d["key"])
            if explicit:
                if d["key"] in keys:
                    todo.append(d["key"])
            elif sl is None or not (sl.locked or sl.edited):
                todo.append(d["key"])
        if explicit and set(keys) & main_keys:                      # derived extras follow their main slots
            for d in recipe.get("extras", []):
                sl = story.slots.get(d["key"])
                if d["key"] not in todo and sl is not None and not (sl.locked or sl.edited):
                    todo.append(d["key"])
        ctx = self._ctx_for(story, exclude=set(todo))
        story.problems = []
        self._fill(ctx, story, recipe, [d["key"] for d in all_defs if d["key"] in todo])
        self._finish(ctx, story, recipe)
        return story

    def recompose(self, story, force=False):
        if story.summary_edited and not force:
            return story
        recipe = self.registry.recipe(story.kind)
        ctx = self._ctx_for(story, exclude=set())
        self._compose(ctx, story, recipe)
        story.summary_edited = False
        return story

    def edit(self, story, key, text):
        """Replace a slot's text by hand (it then stays put when you reroll)."""
        sl = story.slots[key]
        sl.text, sl.edited = text.strip(), True
        sl.entities = [e for e in sl.entities if e.get("title") and e["title"] in sl.text]   # drop people you removed
        if "rep" in story.slots and not any(e.get("type") == "Faction" for e in story.entities):
            story.slots["rep"].text, story.rep = "", []                                     # no faction left to affect
        recipe = self.registry.recipe(story.kind)
        ctx = self._ctx_for(story, exclude=set())
        if not story.summary_edited:
            self._compose(ctx, story, recipe)
        return story

    def set_summary(self, story, text):
        story.summary, story.summary_edited = text.strip(), True
        return story

    def validate_settings(self, story):
        return story.problems

    # ----- internals
    def _prepare(self, ctx, story, recipe):
        s = ctx.settings
        if not s.get("season"):
            s["season"] = self.rng.choice(SEASONS)
        ctx.tags.add(s["season"])
        if not ctx.themes:
            bias = Counter()
            for group in (self.campaign.factions, self.campaign.npcs, self.campaign.locations):
                for it in group:
                    for t in it.get("tags", []):
                        bias[t] += 1
            ctx.table_bias = {}
            for e in self.registry.entries("theme"):
                t = e["tags"][0] if e["tags"] else e["t"]
                ctx.table_bias[e["id"]] = 1 + 0.35 * min(bias.get(t, 0), 6)
            chosen = [ctx.roll("theme")]
            ctx.table_bias = {}
            themes = [t for r in chosen for t in r.tags if t in THEMES][:1]
            if self.rng.random() < 0.35:
                r2 = ctx.roll("theme")
                themes += [t for t in r2.tags if t in THEMES and t not in themes][:1]
            ctx.themes = set(themes)
            s["themes"] = list(themes)
        ctx.tags |= ctx.themes
        if not ctx.envs:
            ew = recipe.get("env_table") or SCENE_ENV.get(s.get("scene", "any"), "env")
            r = ctx.roll(ew)
            env = next((t for t in r.tags if t in ENVS), "")
            if env:
                ctx.envs = {env}
                s["env"] = env
                ctx.tags.add(env)
        story.themes, story.env = list(s["themes"]), s.get("env", "")
        ctx.begin_slot()

    def _ctx_for(self, story, exclude):
        s = story.settings
        ctx = Ctx(self, s, _seed_tags(s) | set(s.get("extra_tags") or []))
        ctx.themes = set(s.get("themes") or [])
        ctx.tags |= ctx.themes
        if s.get("env") and s["env"] != "any":
            ctx.envs = {s["env"]}
            ctx.tags.add(s["env"])
        for key, sl in story.slots.items():
            ctx.vars[key] = sl.text
            ctx.vars[key + ".short"] = short_for(key, sl.text)
            if key not in exclude:
                ctx.tags |= set(sl.tags)
                ctx.used_titles |= {e.get("title") for e in sl.entities if e.get("campaign") and e.get("title")}
        akey = s.get("anchor")
        if akey and akey not in exclude and akey in story.slots:
            ctx.anchor = self._anchor_of(ctx, story.slots[akey])
        who = story.slots.get(self.registry.recipe(story.kind).get("subject", "who"))
        ctx.plural = bool(who and "pl" in who.tags)
        self._story = story
        return ctx

    @staticmethod
    def _anchor_of(ctx, slot):
        """The themes an event brought with it: the ones the story is about, else whatever themes it carries."""
        got = set(slot.tags) & THEME_SET
        return (got & ctx.themes) or got

    def _current_story_entities(self, ctx):
        ents = list(ctx.slot_entities)
        if self._story is not None:
            for sl in self._story.slots.values():
                ents += sl.entities
        ents += getattr(ctx, "_pending_entities", [])
        return ents

    def _fill(self, ctx, story, recipe, keys):
        defs = {d["key"]: dict(d, extra=(d not in recipe["slots"])) for d in recipe["slots"] + recipe.get("extras", [])}
        subject = recipe.get("subject", "who")
        self._story = story
        ctx._pending_entities = []
        if any(defs[k].get("table") == "rep.effects" for k in keys if k in defs):
            story.rep = []                                           # recomputed below from the current factions
        for d in recipe["slots"] + recipe.get("extras", []):
            key = d["key"]
            if key not in keys:
                continue
            ctx.begin_slot()
            ctx.strict_anchor = bool(d.get("strict_anchor"))      # set for the why of a hook, so the motive fits the request
            sl = story.slots.get(key) or Slot(key=key, label=d.get("label", key.title()), table=d.get("table", ""),
                                              extra=defs[key]["extra"])
            sl.label, sl.table, sl.extra = d.get("label", key.title()), d.get("table", ""), defs[key]["extra"]
            sl.edited = False
            preset = (getattr(ctx, "presets", None) or {}).get(key)
            if preset:
                sl.text = str(preset["text"]).strip()
                sl.tags = sorted(set(preset.get("tags", [])))
                sl.entities = [dict(e) for e in preset.get("entities", [])]
                sl.entry, sl.locked = "preset", True
            elif d.get("chance") is not None and self.rng.randint(1, 100) > d["chance"]:
                sl.text, sl.tags, sl.entities, sl.entry = "", [], [], ""
            else:
                r = ctx.roll(d["table"])
                for _ in range(5 if d.get("distinct") else 0):
                    if r.text.strip() not in {story.slots[k].text for k in d["distinct"] if k in story.slots}:
                        break
                    r = ctx.roll(d["table"])
                sl.text = re.sub(r"\s+", " ", r.text).strip()
                sl.tags = sorted(ctx.slot_tags)
                sl.entities = list(ctx.slot_entities)
                sl.entry = r.entry
            story.slots[key] = sl
            ctx.used_titles |= {e.get("title") for e in sl.entities if e.get("campaign") and e.get("title")}
            ctx.vars[key] = sl.text
            ctx.vars[key + ".short"] = short_for(key, sl.text)
            if key == ctx.settings.get("anchor") and not ctx.anchor:
                ctx.anchor = self._anchor_of(ctx, sl)
            ctx._pending_entities = list(ctx._pending_entities) + sl.entities
            if key == subject:
                ctx.plural = "pl" in sl.tags
        ctx.strict_anchor = False
        # keep recipe order
        ordered = OrderedDict()
        for d in recipe["slots"] + recipe.get("extras", []):
            if d["key"] in story.slots:
                ordered[d["key"]] = story.slots[d["key"]]
        story.slots = ordered
        story.problems += ctx.problems
        if "rep" in ctx.meta:
            story.rep = ctx.meta["rep"]

    def _compose(self, ctx, story, recipe):
        templates = recipe.get("compose") or ["{@who} {@what} {@where}, {@when}."]
        ctx.depth = 0
        tpl = self.rng.choice(templates)
        story.summary = tidy(ctx.render(tpl))
        story.summary_edited = False
        title_tpl = recipe.get("title_template", "{@what.short}")
        sep = recipe.get("title_sep", ": ")
        body = tidy(ctx.render(title_tpl)).rstrip(".")
        if not story.title_edited:                                  # a title you typed is never replaced
            story.title = f"{story.title_prefix}{sep}{body}" if story.title_prefix else body
        story.problems += ctx.problems

    def _finish(self, ctx, story, recipe):
        for sl in story.slots.values():
            ctx.vars[sl.key] = sl.text
            ctx.vars[sl.key + ".short"] = short_for(sl.key, sl.text)
        if not story.summary_edited:
            self._compose(ctx, story, recipe)
        story.encounter = encounter_hint(story, recipe, self.rng)
        if "rep" in ctx.meta:
            story.rep = ctx.meta["rep"]


def encounter_hint(story, recipe, rng):
    """Threat level and creature traits to hand to the encounter generator."""
    traits = []
    for t in story.themes:
        traits += THEME_TO_TRAITS.get(t, [])
    threat = recipe.get("threat")
    if threat is None:
        return {}
    if isinstance(threat, list):
        threat = rng.choice(threat)
    return {"threat": threat, "traits": sorted(set(traits)), "themes": list(story.themes), "env": story.env}


DEFAULT_HISTORY = History()
_DEFAULT_REGISTRY = None


def user_path():
    try:
        from . import storage
        return storage.FILES.get("story_tables") or storage.DATA_DIR / "story_tables.json"
    except Exception:
        return None


def default_registry(reload=False):
    """The shared registry: built-ins plus your saved edits."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None or reload:
        reg = Registry()
        p = user_path()
        try:
            if p is not None and p.exists():
                reg.load(p)
        except (OSError, ValueError):
            pass
        _DEFAULT_REGISTRY = reg
    return _DEFAULT_REGISTRY


def save_user_tables(registry=None):
    reg = registry or default_registry()
    p = user_path()
    if p is None:
        raise RuntimeError("No place to save: the app's data folder isn't available.")
    reg.save(p)
    return p


def roll_table(name, rng=None, tags=(), registry=None, **settings):
    """Roll one table by name (used for NPC traits and the table editor's Test Roll). Returns the text."""
    gen = Generator(registry=registry, history=History() if registry is not None else None, rng=rng)
    st = {"themes": [], "env": "any", "tone": settings.get("tone", "any"), "level": settings.get("level", 1),
          "focus": 0.6, "use_campaign": 0.0, "packs": settings.get("packs")}
    ctx = Ctx(gen, st, set(tags))
    return ctx.roll(name).text


def demo(argv=None):
    import sys
    argv = argv or sys.argv[1:]
    kind = argv[0] if argv else "rumor"
    n = int(argv[1]) if len(argv) > 1 else 3
    gen = Generator()
    for _ in range(n):
        st = gen.generate(kind, level=5)
        print(st.plain())
        print("-" * 60)


if __name__ == "__main__":
    demo()

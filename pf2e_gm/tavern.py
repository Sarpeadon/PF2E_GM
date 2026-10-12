"""Inn and tavern generator: a named place with its look, a priced menu and rooms, a proprietor, staff, and patrons who each
carry a rumor or a hook, and a few jobs for Earn Income.

All wording lives in tables (tavdata.py, editable in Edit Tables). This module decides what a place is made of, keeps the
numbers right, and turns a place into text and Notebook pages. A place is a plain dict, so it saves with a Notebook page and
reloads later; nothing here needs a window.

Prices come from the Player Core services table: a mug of ale 1 cp, a keg of ale 2 sp, a pot of tea or coffee 2 cp, a bottle of
wine 1 sp, a bottle of fine wine 1 gp; a poor meal 1 cp, a square meal 3 cp, fine dining 1 gp; floor space 3 cp, a bed 1 sp, a
private room (for 2) 8 sp, an extravagant suite (for 6) 10 gp; stabling 2 cp a day. Which of those a place offers, and how
many of each, depends on its quality and size; that mix is a design choice of this tool, not a rule. The Price adjust setting
scales every price for a dearer or cheaper district.
"""
import copy
import random
import re
import uuid

from . import downtime as dt
from . import names as _names
from . import storygen as sg

KINDS = {
    "tavern": {"label": "Tavern", "rooms": {"small": (0, 0), "medium": (0, 3), "large": (2, 5)}, "stable": 0.0, "floor": False, "drinks_only": False},
    "inn": {"label": "Inn", "rooms": {"small": (3, 5), "medium": (6, 10), "large": (11, 18)}, "stable": 0.4, "floor": True, "drinks_only": False},
    "alehouse": {"label": "Alehouse", "rooms": {"small": (0, 0), "medium": (0, 0), "large": (0, 2)}, "stable": 0.0, "floor": True, "drinks_only": True},
    "roadhouse": {"label": "Roadhouse", "rooms": {"small": (3, 5), "medium": (5, 9), "large": (9, 14)}, "stable": 1.0, "floor": True, "drinks_only": False},
    "taproom": {"label": "Taproom", "rooms": {"small": (0, 0), "medium": (0, 0), "large": (0, 0)}, "stable": 0.0, "floor": False, "drinks_only": True},
}
QUALITIES = ["squalid", "common", "good", "fine"]
SIZES = ["small", "medium", "large"]
BUSY = ["quiet", "normal", "packed"]
OCCUPANCY = {"quiet": 0.25, "normal": 0.55, "packed": 0.9}
ENVS = ["any", "urban", "wild", "underground", "road", "water"]

# price in copper, and what the line is sold by (Player Core services table)
CATEGORIES = {
    "ale": {"label": "Mug of ale", "kind": "drink", "per": "mug", "price_cp": 1, "table": "tav.menu.ale"},
    "keg": {"label": "Keg of ale", "kind": "drink", "per": "keg", "price_cp": 20, "table": ""},
    "hot": {"label": "Pot of tea or coffee", "kind": "drink", "per": "pot", "price_cp": 2, "table": "tav.menu.hot"},
    "wine": {"label": "Bottle of wine", "kind": "drink", "per": "bottle", "price_cp": 10, "table": "tav.menu.wine"},
    "finewine": {"label": "Bottle of fine wine", "kind": "drink", "per": "bottle", "price_cp": 100, "table": "tav.menu.finewine"},
    "poor": {"label": "Poor meal", "kind": "meal", "per": "meal", "price_cp": 1, "table": "tav.menu.poor"},
    "square": {"label": "Square meal", "kind": "meal", "per": "meal", "price_cp": 3, "table": "tav.menu.square"},
    "fine": {"label": "Fine dining", "kind": "meal", "per": "meal", "price_cp": 100, "table": "tav.menu.fine"},
}
MENU_ORDER = ["ale", "keg", "hot", "wine", "finewine", "poor", "square", "fine"]
# how many of each kind of line a place of this quality offers (min, max), before the size adjustment
MENU_MIX = {
    "squalid": {"ale": (2, 3), "poor": (2, 4), "square": (0, 1), "hot": (0, 1)},
    "common": {"ale": (3, 4), "hot": (1, 1), "wine": (1, 2), "poor": (1, 2), "square": (3, 4)},
    "good": {"ale": (3, 4), "hot": (1, 2), "wine": (2, 3), "finewine": (0, 1), "poor": (0, 1), "square": (3, 5), "fine": (0, 1)},
    "fine": {"ale": (2, 3), "hot": (1, 2), "wine": (2, 3), "finewine": (2, 4), "square": (1, 2), "fine": (3, 5)},
}
SIZE_MENU = {"small": -1, "medium": 0, "large": 1}
# Player Core services table: lodging per night
ROOM_TYPES = {                       # sleeps: how many people the book says it is for
    "floor": {"label": "Floor space", "price_cp": 3, "sleeps": 1},
    "bed": {"label": "Bed in a shared room", "price_cp": 10, "sleeps": 1},
    "private": {"label": "Private room (for 2)", "price_cp": 80, "sleeps": 2},
    "suite": {"label": "Extravagant suite (for 6)", "price_cp": 1000, "sleeps": 6},
}
STABLE_CP = 2
ROOM_MIX = {"squalid": {"bed": 5, "private": 1}, "common": {"bed": 3, "private": 5}, "good": {"private": 6, "suite": 1},
            "fine": {"private": 4, "suite": 3}}
PEOPLE = {"patrons": {"small": (4, 6), "medium": (6, 9), "large": (9, 13)},
          "staff": {"small": (1, 2), "medium": (2, 4), "large": (4, 6)}}
STAFF_ROLES = ["barkeep", "cook", "server", "cellarman", "bouncer", "chambermaid", "stable hand", "musician", "dishwasher", "host"]
TASK_LEVEL = {"squalid": 0, "common": 1, "good": 2, "fine": 3}

# who runs a place of a given Underhallow sort, and how to recognize one from a Notebook page
CULTURES = {
    "goblin": ("Goblin", ["goblin", "finders keep"]),
    "kobold": ("Kobold", ["kobold", "underhall"]),
    "ratfolk": ("Ratfolk", ["ratfolk", "hushwarren"]),
    "grippli": ("Grippli", ["grippli", "stillwater"]),
    "leshy": ("Leshy", ["leshy", "quiet ring", "arboreal"]),
    "mender": ("Automaton", ["automaton", "poppet", "mending"]),
    "awakened": ("Awakened Animal", ["awakened", "firstlight"]),
}
CULTURE_OF = {"goblin": "goblin", "kobold": "kobold", "ratfolk": "ratfolk", "grippli": "grippli", "leshy": "leshy", "arboreal": "leshy",
              "automaton": "mender", "poppet": "mender", "awakened animal": "awakened"}

FIELDS = [  # key, label, table, chance (a float, or a dict by quality), shown to players
    ("look", "Looks", "tav.look", 1.0, True),
    ("smell", "Smells", "tav.smell", 0.9, True),
    ("sound", "Sounds", "tav.sound", 0.9, True),
    ("decor", "On the walls", "tav.decor", 0.7, True),
    ("crowd", "Tonight's crowd", "tav.crowd", 1.0, True),
    ("entertainment", "Entertainment", "tav.entertainment", {"squalid": 0.25, "common": 0.5, "good": 0.65, "fine": 0.8}, True),
    ("rule", "House rule", "tav.rule", 0.85, True),
    ("problem", "The problem", "tav.problem", 0.85, False),
    ("secret", "The secret", "tav.secret", 0.6, False),
    ("history", "History", "tav.history", 0.6, False),
]
FIELD_BY_KEY = {f[0]: f for f in FIELDS}
HOOK_KINDS = [("rumor", 55), ("hook", 25), ("none", 20)]


def default_settings():
    return {"kind": "any", "quality": "any", "size": "any", "busy": "any", "env": "any", "tone": "any", "themes": [], "level": 1,
            "culture": "auto", "packs": ["core"], "flavor": None, "use_campaign": 0.0, "price_pct": 100, "patrons": None,
            "staff": None, "proprietor_level": None, "tie": None, "stories": True}


def infer_culture(*texts):
    """Which Underhallow people a Notebook page is about, from its title, kind, tags, and opening text; 'none' if unclear."""
    blob = " ".join(str(t or "") for t in texts).lower()
    for key, (_anc, words) in CULTURES.items():
        if any(w in blob for w in words):
            return key
    return "none"


def culture_of(ancestry):
    return CULTURE_OF.get(str(ancestry or "").strip().lower(), "none")
def themes_of(tags):
    """The story themes among a set of tags, in a steady order."""
    return sorted(t for t in tags if t in sg.THEME_SET)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")


def verb_a(word):
    return sg.article(word)                                  # "an inn", but "a one-eyed goblin" and "an hour"


def _clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _sentence(text):
    t = _clean(text)
    t = t[:1].upper() + t[1:]
    return t if not t or t[-1] in ".!?" else t + "."


def price_text(cp):
    return dt.coin_text(cp)


# ------------------------------------------------------------------------------------------------ the generator
class TavernGenerator:
    """Makes places and changes parts of them. Keeps a short memory of what it just used, so places differ from each other."""

    def __init__(self, registry=None, campaign=None, rng=None):
        self.registry = registry or sg.default_registry()
        self.campaign = campaign or sg.Campaign()
        self.rng = rng or random.Random()
        self.gen = sg.Generator(self.registry, campaign=self.campaign, history=sg.History(strength=0.25, decay=0.85, recent=12), rng=self.rng)

    # ----- plumbing
    def set_registry(self, registry):
        self.registry = self.gen.registry = registry

    def set_campaign(self, campaign):
        self.campaign = self.gen.campaign = campaign

    def _settings(self, kw):
        s = default_settings()
        s.update({k: v for k, v in kw.items() if k in s})
        s["kind"] = s["kind"] if s["kind"] in KINDS else "any"
        s["quality"] = s["quality"] if s["quality"] in QUALITIES else "any"
        s["size"] = s["size"] if s["size"] in SIZES else "any"
        s["busy"] = s["busy"] if s["busy"] in BUSY else "any"
        s["env"] = s["env"] if s["env"] in ENVS else "any"
        s["tone"] = s["tone"] if s["tone"] in ("any", "grim", "light", "weird") else "any"
        s["themes"] = [t for t in (s["themes"] or []) if t in sg.THEME_SET]
        s["level"] = max(1, min(20, int(s["level"] or 1)))
        s["packs"] = list(s["packs"] or ["core"])
        try:
            s["price_pct"] = max(10, min(1000, int(s["price_pct"])))
        except (TypeError, ValueError):
            s["price_pct"] = 100
        s["flavor"] = None if s["flavor"] is None or "hallowmead" not in s["packs"] else max(0.0, min(0.95, float(s["flavor"])))
        s["use_campaign"] = max(0.0, min(1.0, float(s["use_campaign"] or 0.0)))
        for k, lo, hi in (("patrons", 0, 30), ("staff", 0, 15), ("proprietor_level", -1, 20)):
            v = s[k]
            s[k] = None if v in (None, "") else max(lo, min(hi, int(v)))
        return s

    def _tags(self, s, place=None, culture=None):
        """The facts about a place that table entries can ask for with needs."""
        p = place or {}
        tags = set(s["themes"]) | {f"kind:{p.get('kind', 'tavern')}", f"q:{p.get('quality', 'common')}", f"size:{p.get('size', 'medium')}",
                                   f"busy:{p.get('busy', 'normal')}"}
        if s["env"] != "any":
            tags.add(s["env"])
        if s["tone"] != "any":
            tags.add("tone:" + s["tone"])
        c = culture if culture is not None else p.get("culture", "none")
        if c and c != "none":
            tags.add("c:" + c)
        return tags

    def _ctx(self, place, culture=None):
        s = place["settings"]
        self.gen.registry, self.gen.campaign = self.registry, self.campaign
        st = {"themes": list(place.get("themes") or s["themes"]), "env": s["env"], "tone": s["tone"], "level": s["level"], "focus": 0.35,
              "use_campaign": s["use_campaign"], "packs": s["packs"], "pack_share": s["flavor"]}
        return sg.Ctx(self.gen, st, self._tags(dict(s, themes=st["themes"]), place, culture))

    def _roll(self, place, table, culture=None, tags=()):
        ctx = self._ctx(place, culture)
        ctx.tags |= set(tags)
        if not self.registry.has(table):
            return sg.Rolled("")
        return ctx.roll(table)

    def _pick(self, weights):
        keys = list(weights)
        return self.rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]

    # ----- choosing what a place is
    def _choose(self, s, tie_culture):
        kind_w = {"urban": {"tavern": 4, "inn": 3, "alehouse": 2, "taproom": 1, "roadhouse": 0.3},
                  "road": {"roadhouse": 5, "inn": 3, "tavern": 2, "alehouse": 1},
                  "water": {"tavern": 4, "inn": 2, "alehouse": 2, "taproom": 0.5},
                  "underground": {"tavern": 4, "alehouse": 3, "inn": 2, "taproom": 1.5, "roadhouse": 1},
                  "wild": {"roadhouse": 3, "inn": 2, "tavern": 2, "alehouse": 1},
                  "any": {"tavern": 4, "inn": 3, "alehouse": 2, "roadhouse": 1.5, "taproom": 1}}[s["env"]]
        kind = s["kind"] if s["kind"] != "any" else self._pick(kind_w)
        qw = {"squalid": 0.15, "common": 0.5, "good": 0.27, "fine": 0.08}
        if KINDS[kind]["drinks_only"]:
            qw["fine"] *= 0.1
            qw["squalid"] *= 1.5
        if kind == "inn":
            qw["good"] *= 1.2
        quality = s["quality"] if s["quality"] != "any" else self._pick(qw)
        zw = {"small": 0.35, "medium": 0.45, "large": 0.2}
        if KINDS[kind]["drinks_only"]:
            zw["small"] *= 1.5
        size = s["size"] if s["size"] != "any" else self._pick(zw)
        busy = s["busy"] if s["busy"] != "any" else self._pick({"quiet": 0.3, "normal": 0.5, "packed": 0.2})
        if s["culture"] in CULTURES:
            culture = s["culture"]
        elif s["culture"] == "none":
            culture = "none"
        elif tie_culture and tie_culture != "none":
            culture = tie_culture
        elif "hallowmead" in s["packs"] and s["env"] == "underground" and self.rng.random() < 0.6:
            culture = self.rng.choice(list(CULTURES))
        else:
            culture = "none"
        themes = list(s["themes"])
        if not themes:
            tie = s.get("tie") or {}
            themes = [t for t in tie.get("tags", []) if t in sg.THEME_SET][:2]
        return kind, quality, size, busy, culture, themes

    # ----- making a place
    def generate(self, avoid_names=(), **kw):
        """A new place. Settings are the keys of default_settings(); anything left out is chosen for you."""
        s = self._settings(kw)
        self.gen.history.tick()
        tie = s.get("tie") or {}
        tie_culture = infer_culture(tie.get("title"), tie.get("kind"), " ".join(tie.get("tags", [])), tie.get("text"))
        kind, quality, size, busy, culture, themes = self._choose(s, tie_culture)
        place = {"id": uuid.uuid4().hex[:10], "version": 1, "name": "", "name_locked": False, "kind": kind, "quality": quality, "size": size,
                 "busy": busy, "culture": culture, "themes": themes, "env": s["env"], "tone": s["tone"], "settings": s, "fields": [],
                 "menu": [], "rooms": [], "proprietor": None, "staff": [], "patrons": [], "jobs": [], "tie": tie or None}
        if not themes:                                       # a place about something, so its lines hang together
            r = self._roll(place, "theme")
            place["themes"] = [t for t in r.tags if t in sg.THEME_SET][:1]
            if self.rng.random() < 0.35:
                r2 = self._roll(place, "theme")
                place["themes"] += [t for t in r2.tags if t in sg.THEME_SET and t not in place["themes"]][:1]
        self.make_name(place, avoid_names)
        self.make_fields(place)
        self.make_menu(place)
        self.make_rooms(place)
        self.make_people(place)
        self.make_jobs(place)
        return place

    def generate_batch(self, n, **kw):
        """n places that differ from each other: no two share a name."""
        out, names = [], set()
        for _ in range(max(0, int(n))):
            place = None
            for _t in range(6):
                cand = self.generate(avoid_names=names, **kw)
                if cand["name"].lower() not in names:
                    place = cand
                    break
                place = place or cand
            names.add(place["name"].lower())
            out.append(place)
        return out

    # ----- the name and the lines of text
    def make_name(self, place, avoid=()):
        if place.get("name_locked"):
            return place["name"]
        taken = {str(a).lower() for a in avoid}
        for _ in range(8):
            r = self._roll(place, "tav.name")
            name = _clean(r.text)
            if name and name.lower() not in taken:
                break
        place["name"] = name or "The Rest"
        return place["name"]

    def _field(self, place, key):
        _k, label, table, _chance, public = FIELD_BY_KEY[key]
        r = self._roll(place, table)
        return {"key": key, "label": label, "table": table, "text": _sentence(r.text), "locked": False, "edited": False, "public": public}

    def make_fields(self, place):
        keep = {f["key"]: f for f in place["fields"] if f["locked"] or f["edited"]}
        out = []
        for key, label, table, chance, public in FIELDS:
            if key in keep:
                out.append(keep[key])
                continue
            c = chance[place["quality"]] if isinstance(chance, dict) else chance
            if self.rng.random() > c:
                continue
            f = self._field(place, key)
            if f["text"]:
                out.append(f)
        place["fields"] = out
        return out

    def reroll_field(self, place, key):
        """New text for one line; adds it if the place didn't have it. Returns the line."""
        if key not in FIELD_BY_KEY:
            raise KeyError(key)
        new = self._field(place, key)
        for i, f in enumerate(place["fields"]):
            if f["key"] == key:
                place["fields"][i] = new
                return new
        place["fields"].append(new)
        place["fields"].sort(key=lambda f: [x[0] for x in FIELDS].index(f["key"]))
        return new

    def field(self, place, key):
        return next((f for f in place["fields"] if f["key"] == key), None)

    # ----- the menu
    def _menu_line(self, place, cat, taken):
        spec = CATEGORIES[cat]
        text = ""
        for _ in range(8):
            text = _clean(self._roll(place, spec["table"]).text)
            if text and text.lower() not in taken:
                break
        return self._line(place, cat, text or spec["label"])

    def _line(self, place, cat, name, special=False):
        base = CATEGORIES[cat]["price_cp"]
        return {"name": name, "cat": cat, "base_cp": base, "price_cp": self._price(place, base), "special": bool(special),
                "locked": False, "price_edited": False}

    @staticmethod
    def _price(place, base_cp):
        return max(1, int(round(base_cp * place["settings"]["price_pct"] / 100.0)))

    def make_menu(self, place):
        keep = [m for m in place["menu"] if m["locked"]]
        taken = {m["name"].lower() for m in keep}
        mix = dict(MENU_MIX[place["quality"]])
        if KINDS[place["kind"]]["drinks_only"]:
            mix = {k: v for k, v in mix.items() if k in ("ale", "hot", "wine", "poor", "square")}
            mix["square"] = (0, min(1, mix.get("square", (0, 0))[1]))
            mix["poor"] = (1, 2)
        bonus = SIZE_MENU[place["size"]]
        lines = []
        for cat in MENU_ORDER:
            if cat not in mix:
                continue
            lo, hi = mix[cat]
            n = self.rng.randint(lo, hi) + (bonus if hi > 0 else 0)
            n = max(1 if hi > 0 and lo > 0 else 0, min(n, 8))
            n = max(0, n - sum(1 for m in keep if m["cat"] == cat))
            for _ in range(n):
                line = self._menu_line(place, cat, taken)
                taken.add(line["name"].lower())
                lines.append(line)
        if self.rng.random() < (0.7 if place["quality"] != "squalid" else 0.3) and not any(m["special"] for m in keep):
            sp = self._special(place, taken)
            if sp:
                lines.append(sp)
        menu = keep + lines
        ale = next((m for m in menu if m["cat"] == "ale"), None)
        if ale and not any(m["cat"] == "keg" for m in menu):
            menu.append(self._line(place, "keg", f"Keg of {ale['name'][:1].lower() + ale['name'][1:]}"))
        menu.sort(key=lambda m: (MENU_ORDER.index(m["cat"]), m["special"]))
        place["menu"] = menu
        return menu

    def _special(self, place, taken):
        for _ in range(6):
            r = self._roll(place, "tav.menu.special")
            cat = next((t[4:] for t in sorted(r.tags) if t.startswith("cat:") and t[4:] in CATEGORIES), None)
            text = _clean(r.text)
            if cat and text and text.lower() not in taken:
                return self._line(place, cat, text, special=True)
        return None

    def reroll_menu_line(self, place, index):
        old = place["menu"][index]
        if old["cat"] == "keg":
            return old
        taken = {m["name"].lower() for i, m in enumerate(place["menu"]) if i != index}
        new = self._special(place, taken) if old["special"] else self._menu_line(place, old["cat"], taken)
        if new is None:
            return old
        if old["price_edited"]:
            new["price_cp"], new["price_edited"] = old["price_cp"], True
        place["menu"][index] = new
        return new

    def add_menu_line(self, place, cat):
        if cat not in CATEGORIES or cat == "keg":
            raise ValueError("Pick one of: " + ", ".join(c for c in MENU_ORDER if c != "keg"))
        line = self._menu_line(place, cat, {m["name"].lower() for m in place["menu"]})
        place["menu"].append(line)
        place["menu"].sort(key=lambda m: (MENU_ORDER.index(m["cat"]), m["special"]))
        return line

    def remove_menu_lines(self, place, indexes):
        drop = set(indexes)
        place["menu"] = [m for i, m in enumerate(place["menu"]) if i not in drop]

    def set_price_pct(self, place, pct):
        """Rescale every price that hasn't been set by hand, and every room and the stable."""
        place["settings"]["price_pct"] = max(10, min(1000, int(pct)))
        for m in place["menu"]:
            if not m["price_edited"]:
                m["price_cp"] = self._price(place, m["base_cp"])
        for r in place["rooms"]:
            if not r.get("price_edited"):
                r["price_cp"] = self._price(place, r["base_cp"])

    def set_menu_price(self, place, index, cp):
        m = place["menu"][index]
        m["price_cp"], m["price_edited"] = max(1, int(cp)), True

    # ----- the rooms
    def make_rooms(self, place):
        k = KINDS[place["kind"]]
        lo, hi = k["rooms"][place["size"]]
        n = self.rng.randint(lo, hi)
        occ = OCCUPANCY[place["busy"]]
        rooms = []
        mix = ROOM_MIX[place["quality"]]
        types = [self._pick(mix) for _ in range(n)]
        order = {"bed": 0, "private": 1, "suite": 2}
        counts = {}
        for t in sorted(types, key=lambda x: order[x]):
            counts[t] = counts.get(t, 0) + 1
            spec = ROOM_TYPES[t]
            cap = self.rng.randint(4, 8) if t == "bed" else 1            # capacity: how many of it there are to rent
            free = sum(1 for _ in range(cap) if self.rng.random() > occ)
            rooms.append({"id": uuid.uuid4().hex[:6], "label": (f"Shared room {counts[t]}" if t == "bed" else f"Room {len(rooms) + 1}" if t == "private"
                                                                else f"Suite {counts[t]}"), "type": t, "capacity": cap, "sleeps": spec["sleeps"],
                          "base_cp": spec["price_cp"], "price_cp": self._price(place, spec["price_cp"]), "free": free,
                          "quirk": _sentence(self._roll(place, "tav.room.quirk").text), "locked": False, "price_edited": False})
        if k["floor"]:
            cap = {"small": 6, "medium": 10, "large": 16}[place["size"]]
            rooms.append({"id": uuid.uuid4().hex[:6], "label": "Common room floor", "type": "floor", "capacity": cap, "sleeps": 1, "base_cp": 3,
                          "price_cp": self._price(place, 3), "free": sum(1 for _ in range(cap) if self.rng.random() > occ), "quirk": "",
                          "locked": False, "price_edited": False})
        if self.rng.random() < k["stable"]:
            cap = {"small": 3, "medium": 6, "large": 12}[place["size"]]
            rooms.append({"id": uuid.uuid4().hex[:6], "label": "Stabling", "type": "stable", "capacity": cap, "sleeps": 0, "base_cp": STABLE_CP,
                          "price_cp": self._price(place, STABLE_CP), "free": sum(1 for _ in range(cap) if self.rng.random() > occ),
                          "quirk": "", "locked": False, "price_edited": False})
        place["rooms"] = rooms
        return rooms

    def reroll_room_quirk(self, place, index):
        r = place["rooms"][index]
        if r["type"] in ("floor", "stable"):
            return r
        r["quirk"] = _sentence(self._roll(place, "tav.room.quirk").text)
        return r

    # ----- people
    def _ancestry(self, place, prefer=None):
        weights = dict(self.campaign.ancestry_weights or {})
        env = (place["settings"]["env"],) if place["settings"]["env"] != "any" else ()
        if prefer and self.rng.random() < 0.55:
            return prefer
        return _names.pick_ancestry(self.rng, env, weights or None)

    def _culture_ancestry(self, culture):
        if culture == "none" or culture not in CULTURES:
            return None
        anc = CULTURES[culture][0]
        return self.rng.choice(["Automaton", "Poppet"]) if culture == "mender" else anc

    def _detail(self, place, ancestry, culture):
        try:
            from . import npcgen
            look_table = npcgen._appearance_table(ancestry)
        except Exception:
            look_table = "npc.appearance"
        a = _clean(self._roll(place, "npc.demeanor", culture).text)
        b = _clean(self._roll(place, look_table, culture).text)
        c = _clean(self._roll(place, "npc.quirk", culture).text)
        parts = [a, self.rng.choice([b, c])] if self.rng.random() < 0.7 else [a, b, c]
        return _sentence("; ".join(x for x in parts if x))

    def _person(self, place, group, role, ancestry=None):
        ancestry = ancestry or self._ancestry(place, self._culture_ancestry(place["culture"]))
        culture = culture_of(ancestry)
        name = _names.make_name(ancestry, self.rng)
        trait = _clean(self._roll(place, "person.adj", culture).text)
        adj = _names.adjective(ancestry)
        themes = []
        if group == "patron":
            occ_r = self._roll(place, "occupation", culture)
            why_r = self._roll(place, "tav.patron.why", culture)
            occ, why = _clean(occ_r.text) or "traveler", _sentence(why_r.text)
            for t in themes_of(why_r.tags) + themes_of(occ_r.tags):      # what they are doing tonight, then their trade
                if t not in themes:
                    themes.append(t)
        else:
            occ, why = role, ""
        desc = f"{verb_a(trait or adj)} {trait} {adj} {occ}".replace("  ", " ")
        return {"id": uuid.uuid4().hex[:8], "name": name, "ancestry": ancestry, "role": occ, "desc": desc.strip(), "detail": self._detail(place, ancestry, culture),
                "why": why, "group": group, "locked": False, "hook": "none", "story": None, "summary": "", "themes": themes}

    def make_proprietor(self, place):
        from . import npcgen
        s = place["settings"]
        anc = self._ancestry(place, self._culture_ancestry(place["culture"]))
        lvl = s["proprietor_level"] if s["proprietor_level"] is not None else self.rng.choice([0, 1, 1, 2])
        try:
            c, p = npcgen.generate(anc, "Innkeeper", lvl, rng=self.rng, source="Inn generator", tone=s["tone"], env=None if s["env"] == "any" else s["env"],
                                   registry=self.registry, extras=2, gear="none", campaign=self.campaign)
            fields = [[a, b] for a, b in p.get("fields", [])]
            adj = _names.adjective(anc)
            person = {"id": uuid.uuid4().hex[:8], "name": c.name, "ancestry": anc, "role": "innkeeper", "level": lvl,
                      "desc": f"{verb_a(adj)} {adj} innkeeper", "detail": "", "why": "", "group": "proprietor",
                      "locked": False, "hook": "none", "story": None, "summary": "", "fields": fields, "creature": c.to_dict()}
            have = {label: text for label, text in fields}
            picks = [have[l] for l in ("Demeanor", "Looks", "Voice", "Mannerism", "Quirk") if have.get(l)][:2]
            person["detail"] = _sentence("; ".join(picks))
        except Exception as e:                                             # no NPC generator: still a person, and say why
            person = self._person(place, "proprietor", "innkeeper", anc)
            person.update(level=lvl, fields=[], creature=None)
            note = f"The proprietor has no stat block: the NPC generator failed ({type(e).__name__}: {e})."
            place.setdefault("notes", [])
            if note not in place["notes"]:
                place["notes"].append(note)
        return person

    def make_people(self, place):
        s = place["settings"]
        size = place["size"]
        kind = KINDS[place["kind"]]
        if not (place["proprietor"] and place["proprietor"]["locked"]):
            place["proprietor"] = self.make_proprietor(place)
        keep_staff = [p for p in place["staff"] if p["locked"]]
        n_staff = s["staff"] if s["staff"] is not None else self.rng.randint(*PEOPLE["staff"][size])
        roles = ["barkeep", "cook"] + STAFF_ROLES[2:]
        if place["kind"] == "roadhouse" or (place["kind"] == "inn" and self.rng.random() < 0.4):
            roles.insert(2, "stable hand")
        if kind["drinks_only"]:
            roles = [r for r in roles if r not in ("chambermaid", "stable hand", "cook")]
        if place["quality"] == "fine":
            roles.insert(2, "host")
        roles = list(dict.fromkeys(roles))
        have = {p["role"] for p in keep_staff}
        todo = [r for r in roles if r not in have]
        staff = list(keep_staff)
        while len(staff) < n_staff:
            role = todo.pop(0) if todo else self.rng.choice(roles)
            staff.append(self._person(place, "staff", role))
        place["staff"] = staff
        keep_pat = [p for p in place["patrons"] if p["locked"]]
        n_pat = s["patrons"] if s["patrons"] is not None else round(self.rng.randint(*PEOPLE["patrons"][size]) *
                                                                    {"quiet": 0.6, "normal": 1.0, "packed": 1.4}[place["busy"]])
        patrons = list(keep_pat)
        while len(patrons) < n_pat:
            p = self._person(place, "patron", "")
            if s["stories"]:
                self.make_hook(place, p)
            patrons.append(p)
        place["patrons"] = patrons
        return place["patrons"]

    def reroll_person(self, place, group, index):
        """New person in place (staff or patron); a new proprietor for group 'proprietor'."""
        if group == "proprietor":
            place["proprietor"] = self.make_proprietor(place)
            return place["proprietor"]
        lst = place["staff" if group == "staff" else "patrons"]
        old = lst[index]
        new = self._person(place, "staff" if group == "staff" else "patron", old["role"] if group == "staff" else "")
        if group == "patrons" and place["settings"]["stories"]:
            self.make_hook(place, new)
        lst[index] = new
        return new

    # ----- the rumors and hooks patrons carry
    def make_hook(self, place, person, kind=None):
        """Give a patron a rumor, a hook, or nothing (chosen at random unless kind is given)."""
        kind = kind or self._pick(dict(HOOK_KINDS))
        person["hook"], person["story"], person["summary"] = kind, None, ""
        if kind == "none":
            return person
        s = place["settings"]
        title = place["name"]
        where = {"text": f"at {sg.inline_name(title)}", "tags": sorted(set(place["themes"]) | {place["env"]} - {"any"}),
                 "entities": [{"type": "Location", "title": title, "campaign": True}]}
        who = person["name"]                                  # the People list shows the description right beside it
        ent = [{"type": "NPC", "title": person["name"], "campaign": False, "ancestry": person["ancestry"], "role": person["role"]}]
        themes = list(place["themes"])                        # the inn's themes first, then what the patron is doing and their trade
        for t in person.get("themes", []):
            if t not in themes and len(themes) < 3:
                themes.append(t)
        tags = ["k:npc"] + list(person.get("themes", []))
        presets = {"where": where}
        if kind == "rumor":
            presets["source"] = {"text": who, "tags": tags, "entities": ent}
        else:
            presets["who"] = {"text": who, "tags": tags, "entities": ent}
        recipe = "inn_hook" if kind == "hook" and "inn_hook" in self.registry.recipe_names() else kind
        self.gen.registry, self.gen.campaign = self.registry, self.campaign
        try:
            st = self.gen.generate(recipe, themes=themes, env=place["env"], tone=place["tone"], level=s["level"], focus=0.35,
                                   use_campaign=s["use_campaign"], packs=s["packs"], pack_share=s["flavor"], anchor="what", presets=presets)
        except Exception as e:
            person["hook"] = "none"
            place.setdefault("notes", []).append(f"A rumor or hook could not be made ({type(e).__name__}: {e}).")
            return person
        for _ in range(8):                                    # "hires the party ..., because they ..." reads as if the party is meant
            if not self._pronoun_clash(st):
                break
            self.gen.reroll(st, keys=["why"])
        person["story"], person["summary"] = st.to_dict(), st.summary
        return person
    @staticmethod
    def _pronoun_clash(story):
        """True when the request names the party and the reason says they/them/their, so it is unclear who is meant."""
        what, why = story.slots.get("what"), story.slots.get("why")
        return bool(what and why and "the party" in what.text.lower()
                    and re.search(r"\b(they|them|their|themselves)\b", why.text.lower()))

    # ----- Earn Income jobs
    def make_jobs(self, place):
        s = place["settings"]
        base = TASK_LEVEL[place["quality"]] + (1 if place["size"] == "large" else 0)
        tie = place.get("tie") or {}
        pool = dt.jobs(self.registry, tie.get("title"), base, s["packs"], tavern=True)
        mine = [j for j in pool if j.get("table") == "dt.job.tavern"]
        n = min(len(mine), self.rng.randint(3, 5))
        picks = self.rng.sample(mine, n) if mine else []
        place["jobs"] = [{"text": j["text"], "skills": j["skills"], "level": j["level"]} for j in picks]
        return place["jobs"]

    # ----- rerolling everything that isn't locked
    def reroll_unlocked(self, place):
        if not place.get("name_locked"):
            self.make_name(place)
        self.make_fields(place)
        self.make_menu(place)
        self.make_rooms(place)
        self.make_people(place)
        self.make_jobs(place)
        return place


# ------------------------------------------------------------------------------------------------ text
def kind_text(place):
    q = place["quality"]
    return f"{verb_a(q)} {q} {KINDS[place['kind']]['label'].lower()} of {place['size']} size"


def menu_line_text(m):
    spec = CATEGORIES[m["cat"]]
    tag = " (house special)" if m["special"] else ""
    return f"{m['name']}{tag}: {price_text(m['price_cp'])} a {spec['per']}"


def room_kind_text(r):
    """'private, sleeps 2' for a private room, 'extravagant suite, sleeps 6' for a suite; empty for the others."""
    return {"private": "private, sleeps 2", "suite": "extravagant suite, sleeps 6"}.get(r["type"], "")


def room_line_text(r):
    label = r["label"]
    if r["type"] == "stable":
        return f"{label}: {price_text(r['price_cp'])} a day per animal, {r['free']} of {r['capacity']} stalls free"
    if r["type"] in ("floor", "bed"):
        what = f"{price_text(r['price_cp'])} a night each, {r['free']} of {r['capacity']} spaces free"
    else:
        what = f"{price_text(r['price_cp'])} a night, " + ("free tonight" if r["free"] else "taken tonight")
    kind = f" ({room_kind_text(r)})" if room_kind_text(r) else ""
    return f"{label}{kind}: {what}" + (f". {r['quirk']}" if r.get("quirk") else "")


def person_line(p, links=False):
    name = f"[[{p['name']}]]" if links else p["name"]
    return f"{name} ({p['desc']}). {p['detail']}".strip()


def place_text(place, gm=True, links=False):
    """The place as plain text. gm=False leaves out what the players would not know: the problem, the secret, the history, the
    people's hooks, and the jobs."""
    out = [place["name"], kind_text(place)[:1].upper() + kind_text(place)[1:] + (f", {place['busy']} tonight" if place.get("busy") else "") + "."]
    flds = [f for f in place["fields"] if gm or f.get("public")]
    if flds:
        out.append("")
        for f in flds:
            out.append(f"{f['label']}: {f['text']}")
    if place["menu"]:
        out += ["", "Menu"] + [f"- {menu_line_text(m)}" for m in place["menu"]]
    if place["rooms"]:
        out += ["", "Lodging"] + [f"- {room_line_text(r)}" for r in place["rooms"]]
    if gm:
        prop = place.get("proprietor")
        people = []
        if prop:
            people.append(f"- Proprietor: {person_line(prop, links)}")
        people += [f"- {p['role'].capitalize()}: {person_line(p, links)}" for p in place["staff"]]
        if people:
            out += ["", "Staff"] + people
        if place["patrons"]:
            out += ["", "Patrons"]
            for p in place["patrons"]:
                bits = [f"- {person_line(p, links)}"]
                if p.get("why"):
                    bits.append(p["why"])
                if p.get("summary"):
                    bits.append(("Rumor: " if p["hook"] == "rumor" else "Hook: ") + p["summary"])
                out.append(" ".join(bits))
        if place["jobs"]:
            out += ["", "Work for Earn Income"]
            for j in place["jobs"]:
                skills = " or ".join(dt.skill_label(s) for s in j["skills"])
                out.append(f"- {j['text']} ({skills}, suggested task level {j['level']})")
    return "\n".join(out)


def place_markdown(place, gm=True):
    """The place as Markdown, for export."""
    lines = place_text(place, gm).split("\n")
    out = [f"# {lines[0]}", f"*{lines[1]}*"]
    for ln in lines[2:]:
        out.append(f"## {ln}" if ln in ("Menu", "Lodging", "Staff", "Patrons", "Work for Earn Income") else ln)
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------ the Notebook
def _people(place):
    prop = [place["proprietor"]] if place.get("proprietor") else []
    return prop + list(place["staff"]) + list(place["patrons"])


def place_to_pages(place, pages, make_people=True, make_stories=False):
    """Turn a place into Notebook pages. Nothing in `pages` is changed: the caller appends the returned pages.
    Returns {page, new, updated}: `page` is the place's Location page (the existing one, updated, when the place was saved
    before), `new` are pages to append, `updated` the existing pages that were changed. People get NPC pages that link to the
    place and are linked from it; the proprietor's page carries the full NPC stat block."""
    from . import notebook as nbk
    new, updated = [], []
    tavern_page = next((p for p in pages if (p.get("tavern") or {}).get("id") == place["id"]), None)
    kind = f"{place['quality']} {KINDS[place['kind']]['label'].lower()} ({place['size']})"
    tags = sorted(set(place.get("themes", [])) | ({place["env"]} if place.get("env") not in (None, "any") else set()) | {"trade"})
    if tavern_page is None:
        tavern_page = nbk.new_page(nbk.unique_title(pages, place["name"]), "Location", "", kind=kind, preps=["at", "in", "near"], tags=tags)
        new.append(tavern_page)
    else:
        tavern_page.update(kind=kind, tags=tags)
        updated.append(tavern_page)
    title = tavern_page["title"]
    all_pages = list(pages) + new
    if make_people:
        for p in _people(place):
            pg = next((x for x in all_pages if x.get("tavern_person") == p["id"]), None)
            body = _person_body(place, p, title)
            role = f"Innkeeper {p.get('level', 1)}" if p["group"] == "proprietor" else p["role"].capitalize()
            if pg is None:
                pg = nbk.new_page(nbk.unique_title(all_pages, p["name"]), "NPC", body, status="alive", tags=list(place.get("themes", [])),
                                  ancestry=p["ancestry"], role=role, tavern_person=p["id"])
                new.append(pg)
                all_pages.append(pg)
            else:
                pg.update(body=body, ancestry=p["ancestry"], role=role)
                if pg not in updated and pg not in new:
                    updated.append(pg)
            if p.get("creature"):
                pg["npc_stats"] = p["creature"]
            p["page_title"] = pg["title"]
    if make_stories:
        for p in place["patrons"]:
            if not p.get("story"):
                continue
            story = sg.Story.from_dict(p["story"])
            old = next((x for x in all_pages if x.get("tavern_story") == p["id"]), None)
            page, extra = nbk.story_to_pages(story, all_pages, None, False, old["id"] if old else None)
            page["tavern_story"] = p["id"]
            if p.get("page_title") and f"[[{p['page_title']}" not in page["body"]:
                page["body"] = page["body"].replace(p["name"], f"[[{p['page_title']}|{p['name']}]]", 1)
            if old is None:
                new.append(page)
                all_pages.append(page)
            elif old not in updated:
                updated.append(old)
    tavern_page["body"] = place_text(place, gm=True, links=make_people)
    if make_people:
        for p in _people(place):                                       # link to the page titles actually used
            if p.get("page_title") and p["page_title"] != p["name"]:
                tavern_page["body"] = tavern_page["body"].replace(f"[[{p['name']}]]", f"[[{p['page_title']}|{p['name']}]]")
    tavern_page["tavern"] = copy.deepcopy(place)
    return {"page": tavern_page, "new": new, "updated": updated}


def _person_body(place, p, title):
    lines = [f"{p['name']} is {p['desc']} at [[{title}]]" + (", the proprietor." if p["group"] == "proprietor" else ".")]
    if p.get("fields"):
        lines += [f"{label}: {text}" for label, text in p["fields"]]
    elif p.get("detail"):
        lines.append(p["detail"])
    if p.get("why"):
        lines.append("Here tonight: " + p["why"])
    if p.get("summary"):
        lines.append(("Rumor: " if p["hook"] == "rumor" else "Hook: ") + p["summary"])
    return "\n".join(lines)


def saved_places(pages):
    """Notebook pages that hold a saved place, newest data first: [(page, place dict)]."""
    return [(p, p["tavern"]) for p in pages if isinstance(p.get("tavern"), dict) and p["tavern"].get("settings")]

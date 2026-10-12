"""Pathbuilder 2e characters: import by export ID, full stat parsing, and PC stat blocks.

Pathbuilder's "Export JSON" uploads the character and gives a numeric ID. The same JSON is served at
JSON_URL. This address is not an official API (it's what importers such as Pathmuncher use), so it can
change or be blocked; file import still works when it is.

Numbers are computed from the build: attribute modifier + proficiency + level (when trained or better),
plus any item/other modifiers Pathbuilder lists in the export's "mods" section. AC and weapon attack
bonuses use Pathbuilder's own totals. Everything else in the export is kept too: feats, class features,
equipment (with containers), armor, weapons with runes, spellcasting (prepared lists, focus spells),
formulas, rituals, familiars, and money. Every section is read defensively: a missing or oddly shaped
section is skipped rather than breaking the import.
"""
import json
import re
import urllib.request

JSON_URL = "https://pathbuilder2e.com/json.php?id={id}"
PARSER_VERSION = 2     # raise this when parse() learns to read more, so stored characters can be rebuilt from their export
SKILLS = ["acrobatics", "arcana", "athletics", "crafting", "deception", "diplomacy", "intimidation", "medicine",
          "nature", "occultism", "performance", "religion", "society", "stealth", "survival", "thievery"]
SKILL_ATTR = {"acrobatics": "dex", "arcana": "int", "athletics": "str", "crafting": "int", "deception": "cha",
              "diplomacy": "cha", "intimidation": "cha", "medicine": "wis", "nature": "wis", "occultism": "int",
              "performance": "cha", "religion": "wis", "society": "int", "stealth": "dex", "survival": "wis",
              "thievery": "dex"}
SAVE_ATTR = {"fortitude": "con", "reflex": "dex", "will": "wis"}
DMG_TYPE = {"P": "piercing", "S": "slashing", "B": "bludgeoning"}
RANK = {0: "U", 2: "T", 4: "E", 6: "M", 8: "L"}


def parse_id(text):
    """Accept '123456', a pathbuilder URL with ?id=123456, or anything containing a 5+ digit number."""
    m = re.search(r"[?&]id=(\d+)", str(text)) or re.search(r"\b(\d{5,})\b", str(text))
    return m.group(1) if m else None


def fetch(pid, timeout=20):
    req = urllib.request.Request(JSON_URL.format(id=pid), headers={
        "User-Agent": "Mozilla/5.0 (pf2e-gm-tool)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
    try:
        d = json.loads(raw)
    except ValueError:
        raise RuntimeError("Pathbuilder didn't return character data (the site may be blocking automated "
                           "requests). Use Import Pathbuilder JSON with a downloaded file instead.")
    if isinstance(d, dict) and d.get("success") is False:
        raise RuntimeError(f"Pathbuilder has no character for ID {pid}. Re-export JSON in Pathbuilder.")
    return d


def _mod(score):
    try:
        return (int(score) - 10) // 2
    except (TypeError, ValueError):
        return 0


def _prof_bonus(prof, level):
    try:
        prof = int(prof or 0)
    except (TypeError, ValueError):
        prof = 0
    return prof + level if prof > 0 else 0


def _list(x):
    return x if isinstance(x, list) else []


def _txt(x):
    return str(x).strip() if x not in (None, False) else ""


def _int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


FEAT_ORDER = ["Ancestry Feat", "Heritage", "Ancestry Feature", "Background", "Awarded Feat", "Class Feat",
              "Class Feature", "Archetype Feat", "Skill Feat", "General Feat", "Bonus Feat", "Mythic Feat"]
SF_SKILL_ATTR = {"piloting": "dex", "computers": "int"}     # Starfinder skills: only listed once trained
SENSE_NAMES = {"darkvision", "greater darkvision", "low-light vision", "scent", "tremorsense", "lifesense",
               "echolocation", "wavesense", "thoughtsense", "motion sense", "see invisibility", "truesight"}
SIZE_WORDS = {"tiny", "small", "medium", "large", "huge", "gargantuan"}
UNSET = {"not set", "none", "n/a", ""}
RUNE_DAMAGE = {"flaming": "1d6 fire", "frost": "1d6 cold", "shock": "1d6 electricity", "corrosive": "1d6 acid",
               "thundering": "1d6 sonic", "greater flaming": "1d6 fire", "greater frost": "1d6 cold",
               "greater shock": "1d6 electricity", "greater corrosive": "1d6 acid",
               "greater thundering": "1d6 sonic"}
STRIKING = {"striking": 1, "greaterstriking": 2, "majorstriking": 3}
SIZES = {"tiny": "tiny", "small": "sm", "medium": "med", "large": "lg", "huge": "huge", "gargantuan": "grg"}


def _parse_feats(b):
    out = []
    for f in _list(b.get("feats")):
        if isinstance(f, (list, tuple)) and f and isinstance(f[0], str):
            out.append({"name": f[0].strip(), "choice": _txt(f[1]) if len(f) > 1 else "",
                        "type": _txt(f[2]) if len(f) > 2 and f[2] else "Feat",
                        "level": _int(f[3]) if len(f) > 3 else None, "source": _txt(f[4]) if len(f) > 4 else ""})
        elif isinstance(f, dict) and f.get("name"):
            out.append({"name": _txt(f["name"]), "choice": _txt(f.get("choice") or f.get("extra")),
                        "type": _txt(f.get("type")) or "Feat", "level": _int(f.get("level")),
                        "source": _txt(f.get("source"))})
    return out


def _parse_equipment(b):
    containers = {}
    ec = b.get("equipmentContainers")
    if isinstance(ec, dict):
        for cid, c in ec.items():
            name = c.get("containerName") if isinstance(c, dict) else c
            containers[str(cid)] = _txt(name)
    out = []
    for e in _list(b.get("equipment")):
        if isinstance(e, (list, tuple)) and e and isinstance(e[0], str):
            inv = _txt(e[2]).lower() if len(e) > 2 else ""
            out.append({"name": e[0].strip(), "qty": _int(e[1], 1) if len(e) > 1 else 1,
                        "invested": inv == "invested",
                        "container": containers.get(_txt(e[3]), "") if len(e) > 3 else ""})
        elif isinstance(e, dict) and e.get("name"):
            out.append({"name": _txt(e["name"]), "qty": _int(e.get("qty"), 1),
                        "invested": bool(e.get("invested")) or _txt(e.get("worn")).lower() == "invested",
                        "container": containers.get(_txt(e.get("container")), "")})
    return out


def _parse_armor(b):
    out = []
    for a in _list(b.get("armor")):
        if isinstance(a, dict) and a.get("name"):
            runes = [r for r in _list(a.get("runes")) if isinstance(r, str)]
            label = ([f"+{_int(a.get('pot'), 0)}"] if _int(a.get("pot"), 0) else [])
            if _txt(a.get("res")):
                label.append(_txt(a["res"]).lower())
            label += [r.lower() for r in runes]
            out.append({"name": _txt(a["name"]) + (f" ({', '.join(label)})" if label else ""),
                        "base": _txt(a["name"]),
                        "qty": _int(a.get("qty"), 1), "prof": _txt(a.get("prof")), "pot": _int(a.get("pot"), 0),
                        "res": _txt(a.get("res")), "worn": bool(a.get("worn")), "runes": runes})
    return out


def _parse_weapons(b):
    strikes = []
    for w in _list(b.get("weapons")):
        if not isinstance(w, dict) or not w.get("name"):
            continue
        die = _txt(w.get("die")) or "d4"
        striking = STRIKING.get(_txt(w.get("str")).replace(" ", "").lower(), 0)
        dice_n = 1 + striking
        bonus = _int(w.get("damageBonus"), 0)
        dtype = DMG_TYPE.get(_txt(w.get("damageType")).upper(), _txt(w.get("damageType")).lower())
        runes = [r for r in _list(w.get("runes")) if isinstance(r, str)]
        varies = die.lower() == "d0" or dtype == "varies"
        note = ""
        if varies:       # alchemical bombs and similar: the damage comes from the bomb or ammunition used
            parts, dtype = [], ""
            note = "Damage depends on the bomb used (see Formulas)" if "bomb" in _txt(w["name"]).lower() \
                else "Damage depends on the ammunition or item used"
        else:
            parts = [f"{dice_n}{die}" + (f"+{bonus}" if bonus > 0 else (str(bonus) if bonus < 0 else ""))
                     + (f" {dtype}" if dtype else "")]
            extra = [x for x in _list(w.get("extraDamage")) if isinstance(x, str) and x.strip()]
            if not extra:
                extra = [RUNE_DAMAGE[r.lower()] for r in runes if r.lower() in RUNE_DAMAGE]
            parts += [x.strip().lower() if i else x.strip() for i, x in enumerate(extra)]
        label = [f"+{_int(w.get('pot'), 0)}"] if _int(w.get("pot"), 0) else []
        label += [{1: "striking", 2: "greater striking", 3: "major striking"}[striking]] if striking else []
        label += [r.lower() for r in runes]
        strikes.append({"name": _txt(w["name"]) + (f" ({', '.join(label)})" if label else ""), "weapon": _txt(w["name"]),
                        "bonus": f"{_int(w.get('attack'), 0):+d}", "damage": parts, "traits": [], "effects": [],
                        "kind": "Melee", "dtype": dtype, "note": note, "runes": runes, "pot": _int(w.get("pot"), 0),
                        "mat": _txt(w.get("mat")), "prof": _txt(w.get("prof"))})
    return strikes


def _parse_spellcasting(b, mods, level, slots_out=None):
    """Spellcasting entries in the stat block spell format (head + [rank label, [names]]).

    slots_out (a list) receives one dict per entry for the resource tracker:
    {"entry", "kind", "innate", "per_day": {rank: n}, "prepared": {rank: [names]}, "known": {rank: [names]}}.
    """
    entries = []
    for sc in _list(b.get("spellCasters")):
        if not isinstance(sc, dict):
            continue
        ab = _txt(sc.get("ability")).lower()[:3]
        prof = _prof_bonus(sc.get("proficiency"), level)
        dc = 10 + mods.get(ab, 0) + prof
        trad = _txt(sc.get("magicTradition")).title()
        kind = _txt(sc.get("spellcastingType")).title() or "Spontaneous"
        if sc.get("innate"):
            kind = "Innate"
        name = _txt(sc.get("name"))
        title = " ".join(x for x in (trad, kind, "Spells") if x)
        if name and name.lower() not in title.lower():
            title = f"{name} ({title})"
        slots = _list(sc.get("perDay"))
        known = [x for x in _list(sc.get("spells")) if isinstance(x, dict)]
        prepared = [x for x in _list(sc.get("prepared")) if isinstance(x, dict) and _list(x.get("list"))]
        source = list(prepared)
        if prepared and not any(_int(g.get("spellLevel"), 0) == 0 for g in prepared):
            source += [g for g in known if _int(g.get("spellLevel"), 0) == 0]   # cantrips are always ready
        if not prepared:
            source = known
        ranks = []
        if slots_out is not None:
            slots_out.append({
                "entry": title, "kind": "innate" if sc.get("innate") else kind.lower(), "innate": bool(sc.get("innate")),
                "per_day": {i: _int(n, 0) for i, n in enumerate(slots) if i and _int(n, 0)},
                "prepared": {_int(g.get("spellLevel"), 0): [_txt(n) for n in _list(g.get("list")) if _txt(n)]
                             for g in prepared if _int(g.get("spellLevel"), 0)},
                "known": {_int(g.get("spellLevel"), 0): [_txt(n) for n in _list(g.get("list")) if _txt(n)]
                          for g in known if _int(g.get("spellLevel"), 0) and _list(g.get("list"))}})
        for grp in sorted(source, key=lambda g: _int(g.get("spellLevel"), 0)):
            names = [_txt(n) for n in _list(grp.get("list")) if _txt(n)]
            if not names:
                continue
            lv = _int(grp.get("spellLevel"), 0)
            label = "Cantrips" if lv == 0 else f"Rank {lv}"
            n_slots = _int(slots[lv]) if lv and lv < len(slots) else None
            suffix = ""
            if n_slots and sc.get("innate"):
                suffix = f" ({n_slots}/day)"          # innate: uses per day, shown beside each spell
            elif n_slots:
                label += f" ({n_slots} slot{'s' if n_slots != 1 else ''})"
            ranks.append([label, [[n, f"spell:{n}", suffix] for n in names]])
        if ranks:
            entries.append({"head": f"{title} DC {dc}, attack {dc - 10:+d}", "ranks": ranks})
    focus = b.get("focus")
    if isinstance(focus, dict):
        rank = max(1, (level + 1) // 2)
        for trad, abilities in focus.items():
            for abkey, f in (abilities or {}).items() if isinstance(abilities, dict) else []:
                if not isinstance(f, dict):
                    continue
                dc = 10 + _int(f.get("abilityBonus"), mods.get(abkey[:3], 0)) + _prof_bonus(f.get("proficiency"), level) \
                    + _int(f.get("itemBonus"), 0)
                ranks = []
                cants = [_txt(x) for x in _list(f.get("focusCantrips")) if _txt(x)]
                spells = [_txt(x) for x in _list(f.get("focusSpells")) if _txt(x)]
                if cants:
                    ranks.append(["Cantrips", [[n, f"spell:{n}", ""] for n in cants]])
                if spells:
                    ranks.append([f"Rank {rank}", [[n, f"spell:{n}", ""] for n in spells]])
                if ranks:
                    pts = _int(b.get("focusPoints"), 0)
                    entries.append({"head": f"{_txt(trad).title()} Focus Spells DC {dc}, attack {dc - 10:+d}"
                                    + (f", {pts} Focus Point{'s' if pts != 1 else ''}" if pts else ""),
                                    "ranks": ranks})
    return entries


def _split_commas(text):
    """Split on commas that aren't inside parentheses: 'fire 5, physical 5 (except silver, cold iron)'."""
    return [t.strip() for t in re.split(r",(?![^()]*\))", str(text or "")) if t.strip()]


def _norm_def(text):
    """'5 fire' -> 'fire 5'; strips stray whitespace."""
    t = " ".join(str(text).split())
    m = re.match(r"^(\d+)\s+(.+)$", t)
    return f"{m.group(2)} {m.group(1)}" if m else t


def _def_strings(raw):
    """Pathbuilder's resistance/weakness/immunity lists as strings. Accepts strings, [type, value] pairs
    (either order), and {'type', 'value'} dicts."""
    out = []
    for x in _list(raw):
        if isinstance(x, str):
            out.append(_norm_def(x))
        elif isinstance(x, (list, tuple)):
            out.append(_norm_def(" ".join(_txt(y) for y in x if y not in (None, ""))))
        elif isinstance(x, dict):
            t = _txt(x.get("type") or x.get("name"))
            v = _txt(x.get("value") or x.get("amount"))
            if t:
                out.append(f"{t} {v}".strip())
    return [t for t in out if t]


def def_pairs(strings):
    """[(display, 'name:slug')] for stat block rendering and combat IWR parsing."""
    out, seen = [], set()
    for t in strings:
        bare = re.sub(r"\s*\(.*?\)", "", t).strip()               # drop '(except silver)'
        slug = re.sub(r"\s+\d+$", "", bare).strip().lower().replace(" ", "-")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        out.append((t, f"name:{slug}"))
    return out


def unarmed_strike(mods, prof, level):
    """Fist: 1d4 bludgeoning, agile, finesse, nonlethal, unarmed. Attack uses Str or Dex (finesse); damage uses
    Str. Item bonuses and weapon specialization aren't included (the export doesn't list them for unarmed)."""
    atk = max(mods.get("str", 0), mods.get("dex", 0)) + _prof_bonus(prof.get("unarmed"), level)
    st = mods.get("str", 0)
    return {"name": "Fist", "weapon": "Fist", "bonus": f"{atk:+d}",
            "damage": [f"1d4{st:+d} bludgeoning" if st else "1d4 bludgeoning"],
            "traits": ["agile", "finesse", "nonlethal", "unarmed"], "effects": [], "kind": "Melee",
            "dtype": "bludgeoning", "note": "", "runes": [], "pot": 0, "mat": "", "prof": "unarmed",
            "unarmed": True}


DMG_WORDS = ("acid|cold|electricity|fire|force|mental|poison|sonic|bleed|vitality|void|spirit|bludgeoning|"
             "piercing|slashing|precision|persistent|splash|positive|negative")
BOMB_DMG = re.compile(r"(?<![\w.])(\d+d\d+(?:\s*[+-]\s*\d+)?|\d+)((?:\s+(?:" + DMG_WORDS + r"))+)", re.IGNORECASE)


def parse_bomb_text(text, structured=None):
    """Damage from a bomb's rules text: (direct, persistent, splash) like ('1d8 fire', '1d4 persistent fire',
    '1 fire'). Each is '' when absent. `structured` (the item's weapon_damage data, if the rules data has it) is
    used only when the text gives no direct damage."""
    from .statblock import strip_links
    direct = persistent = splash = ""
    for m in BOMB_DMG.finditer(strip_links(text or "")):
        amount = re.sub(r"\s+", "", m.group(1))
        words = m.group(2).lower().split()
        types = [w for w in words if w not in ("persistent", "splash", "precision")]
        tstr = " ".join(types)
        if "persistent" in words:
            persistent = persistent or f"{amount} persistent {tstr}".strip()
        elif "splash" in words:
            splash = splash or f"{amount} {tstr}".strip()
        else:
            direct = direct or f"{amount} {tstr}".strip()
    st = structured or {}
    if not direct and st.get("die"):
        direct = f"{st.get('dice') or 1}{st['die']} {st.get('type', '')}".strip()
    if not persistent and isinstance(st.get("persistent"), dict) and st["persistent"].get("faces"):
        p = st["persistent"]
        persistent = f"{p.get('number') or 1}d{p['faces']} persistent {p.get('type') or st.get('type', '')}".strip()
    if not splash and st.get("splash"):
        splash = f"{st['splash']} {st.get('type', '')}".strip()
    return direct, persistent, splash


def bomb_strikes(pc, lookup):
    """Each known bomb formula as a Strike. The attack uses the character's Alchemical Bomb bonus; damage comes
    from the bomb's rules text. Class bonuses to bomb damage or splash aren't included (add a Bonus / Penalty)."""
    if not lookup:
        return []
    base = next((x for x in pc.get("strikes", []) if "bomb" in (x.get("weapon") or "").lower()
                 and re.fullmatch(r"[+-]\d+", str(x.get("bonus", "")))), None)
    if not base:
        return []
    out, seen = [], set()
    for f in pc.get("formulas", []):
        for name in f.get("known", []):
            if name.lower() in seen:
                continue
            e = lookup(name, "item")
            traits = [t.lower() for t in (e or {}).get("traits", [])]
            if not e or "bomb" not in traits:
                continue
            seen.add(name.lower())
            direct, persistent, splash = parse_bomb_text(e.get("text", ""), e.get("weapon_damage"))
            dmg = [x for x in (direct, persistent) if x]
            if not dmg and not splash:
                continue
            tr = list(dict.fromkeys(["alchemical", "bomb"] + [t for t in traits if t in ("splash", "fire", "cold",
                                     "acid", "electricity", "poison", "sonic", "force", "mental", "vitality", "void")]))
            note = f"Splash {splash} (not doubled on a crit)" if splash else ""
            out.append({"name": name, "weapon": name, "bonus": base["bonus"], "damage": dmg, "traits": tr,
                        "effects": [], "kind": "Ranged", "dtype": (direct.split()[-1] if direct else ""),
                        "note": note, "runes": [], "pot": 0, "mat": "", "prof": base.get("prof", ""), "bomb": True})
    return out


def _parse_mods(b):
    """Item and other modifiers from the export's "mods" section: {'Stealth': [('Armor Check Penalty', -1)]}."""
    out = {}
    raw = b.get("mods")
    if isinstance(raw, dict):
        for stat, srcs in raw.items():
            if isinstance(srcs, dict):
                for src, val in srcs.items():
                    if isinstance(val, (int, float)) and not isinstance(val, bool) and int(val):
                        out.setdefault(_txt(stat), []).append((_txt(src), int(val)))
    return out


def parse(d, fallback_name="PC"):
    """Full character from a Pathbuilder export. Keeps the original keys (name, level, perception, hp, ac,
    saves, skills, strikes) and adds feats, specials, equipment, armor, spells, formulas, and more."""
    b = d.get("build") if isinstance(d, dict) and isinstance(d.get("build"), dict) else d
    if not isinstance(b, dict):
        b = {}
    level = _int(b.get("level"), 1) or 1
    ab = b.get("abilities", {}) or {}
    mods = {k: _mod(ab.get(k)) for k in ("str", "dex", "con", "int", "wis", "cha")}
    prof = b.get("proficiencies") or {}
    pc = {"name": b.get("name") or fallback_name, "level": level}
    for key in ("class", "ancestry", "heritage", "background", "deity", "alignment", "gender", "age"):
        if b.get(key) and _txt(b[key]).lower() not in UNSET:
            pc[key] = b[key]
    if b.get("dualClass"):
        pc["dual_class"] = b["dualClass"]
    size = SIZES.get(_txt(b.get("sizeName")).lower())
    if size:
        pc["size"] = size
    langs = [x for x in _list(b.get("languages")) if isinstance(x, str) and x.lower() != "none selected"]
    if langs:
        pc["languages"] = langs
    item_mods = _parse_mods(b)
    if item_mods:
        pc["item_mods"] = {k: [list(x) for x in v] for k, v in item_mods.items()}

    def bonus_for(stat):
        for key in (stat, stat.title(), stat.lower()):
            if key in item_mods:
                return sum(v for _, v in item_mods[key])
        return 0
    if ab:
        if "perception" in prof:
            pc["perception"] = mods["wis"] + _prof_bonus(prof.get("perception"), level) + bonus_for("Perception")
        pc["saves"] = {s: mods[a] + _prof_bonus(prof.get(s), level) + bonus_for(s.title())
                       for s, a in SAVE_ATTR.items() if s in prof}
        skills = {}
        for sk in SKILLS:
            if sk in prof:
                skills[sk.title()] = mods[SKILL_ATTR[sk]] + _prof_bonus(prof.get(sk), level) + bonus_for(sk.title())
        for sk, attr in SF_SKILL_ATTR.items():
            if _int(prof.get(sk), 0):
                skills[sk.title()] = mods[attr] + _prof_bonus(prof.get(sk), level) + bonus_for(sk.title())
        for lore in _list(b.get("lores")):
            if isinstance(lore, (list, tuple)) and len(lore) >= 2:
                skills[f"Lore ({lore[0]})"] = mods["int"] + _prof_bonus(lore[1], level) + bonus_for(f"{lore[0]}")
        pc["skills"] = skills
        pc["mods"] = dict(mods)
        cd = prof.get("classDC")
        if cd:
            pc["class_dc"] = 10 + mods.get(b.get("keyability") or "str", 0) + _prof_bonus(cd, level)
    at = b.get("attributes") or {}
    if ab and "classhp" in at:
        pc["hp"] = _int(at.get("ancestryhp"), 0) + _int(at.get("bonushp"), 0) + \
            (_int(at.get("classhp"), 0) + _int(at.get("bonushpPerLevel"), 0) + mods["con"]) * level
    if at.get("speed"):
        pc["speed"] = (_int(at.get("speed"), 0) or 0) + (_int(at.get("speedBonus"), 0) or 0)
    ac = (b.get("acTotal") or {}).get("acTotal")
    if isinstance(ac, int):
        pc["ac"] = ac
    strikes = _parse_weapons(b)
    if ab and not any((w.get("weapon") or "").lower() == "fist" for w in strikes):
        strikes.append(unarmed_strike(mods, prof, level))
    if strikes:
        pc["strikes"] = strikes
    pc["damage_types"] = sorted({s["dtype"] for s in strikes if s.get("dtype") and not s.get("unarmed")})
    feats = _parse_feats(b)
    if feats:
        pc["feats"] = feats
    feat_names = {f["name"].lower() for f in feats}
    specials, senses = [], []
    for x in _list(b.get("specials")):
        if not isinstance(x, str) or not x.strip():
            continue
        x = x.strip()
        low = x.lower()
        if low in SENSE_NAMES:
            senses.append(x)                     # Darkvision, Low-Light Vision... become senses
        elif low in SIZE_WORDS or low in feat_names or x in specials:
            continue                             # size, and features already listed as feats
        else:
            specials.append(x)
    if specials:
        pc["specials"] = specials
    if senses:
        pc["senses"] = senses
    equipment = _parse_equipment(b)
    if equipment:
        pc["equipment"] = equipment
    armor = _parse_armor(b)
    if armor:
        pc["armor"] = armor
    money = b.get("money")
    if isinstance(money, dict) and any(_int(v) for v in money.values()):
        pc["money"] = {k: _int(money.get(k), 0) for k in ("pp", "gp", "sp", "cp")}
    slots = []
    spells = _parse_spellcasting(b, mods, level, slots)
    if spells:
        pc["spells"] = spells
    if slots:
        pc["slots"] = slots
    fp = _int(b.get("focusPoints"), 0) or sum(_int(sc.get("focusPoints"), 0) or 0 for sc in _list(b.get("spellCasters"))
                                               if isinstance(sc, dict))
    if fp:
        pc["focus_points"] = min(3, fp)
    formulas = []
    for f in _list(b.get("formula")):
        if isinstance(f, dict) and _list(f.get("known")):
            formulas.append({"type": _txt(f.get("type")) or "Formulas",
                             "known": [_txt(k) for k in f["known"] if _txt(k)]})
    if formulas:
        pc["formulas"] = formulas
    rituals = [x.strip() for x in _list(b.get("rituals")) if isinstance(x, str) and x.strip()]
    if rituals:
        pc["rituals"] = rituals
    pets = []
    for key in ("familiars", "pets"):
        for f in _list(b.get(key)):
            if isinstance(f, dict):
                pets.append({"kind": _txt(f.get("type")) or ("Familiar" if key == "familiars" else "Companion"),
                             "name": _txt(f.get("name")), "specific": _txt(f.get("specific")),
                             "abilities": [_txt(x) for x in _list(f.get("abilities")) if _txt(x)],
                             "equipment": [_txt(x) for x in _list(f.get("equipment")) if _txt(x)]})
    if pets:
        pc["pets"] = pets
    for key in ("resistances", "weaknesses", "immunities"):
        vals = _def_strings(b.get(key))
        if vals:
            pc[key] = vals
    pc["pb_version"] = PARSER_VERSION
    pc["raw"] = b            # kept so a later version of this parser can rebuild the character without the network
    return pc


def is_stale(pc):
    """A character saved by an older importer: it has computed numbers (skills) but no Strikes at all. A current import
    always has at least a Fist, so this is never true for one."""
    return isinstance(pc, dict) and "skills" in pc and "strikes" not in pc


def needs_upgrade(pc):
    return is_stale(pc) or (isinstance(pc, dict) and isinstance(pc.get("raw"), dict)
                            and int(pc.get("pb_version") or 0) < PARSER_VERSION)


def rank(pc):
    """How complete a stored character is: (parser version, not stale). A less complete copy never replaces a more
    complete one of the same character."""
    return (int(pc.get("pb_version") or 0), 0 if is_stale(pc) else 1) if isinstance(pc, dict) else (-1, -1)


def upgrade(pc):
    """Rebuild a stored character with the current parser from the export saved with it. Returns a new dict (keeping its
    Pathbuilder ID and table state), or None when no export was saved."""
    raw = pc.get("raw") if isinstance(pc, dict) else None
    if not isinstance(raw, dict):
        return None
    new = parse(raw, pc.get("name") or "PC")
    for k in ("pathbuilder_id", "state"):
        if pc.get(k) and not new.get(k):
            new[k] = pc[k]
    return new


# ---------- stat block ----------
RANGED_NAMES = ("bow", "crossbow", "sling", "dart", "blowgun", "shuriken", "pistol", "rifle", "musket", "gun",
                "blaster", "needler", "arquebus", "javelin", "boomerang", "net launcher", "hand cannon", "bomb")
BOMB_TRAITS = ["alchemical", "bomb", "splash"]


def _entry_traits(lookup, name):
    e = lookup(name, "item") if lookup else None
    return (list(e.get("traits") or []), e) if e else ([], None)


def _is_ranged(name, traits, entry):
    low = (name or "").lower()
    if any(w in low for w in RANGED_NAMES):
        return True
    rng = (entry or {}).get("weapon_range")
    return bool(rng) and not any(t.startswith("thrown") for t in traits)


def _pc_actions(pc, lookup):
    """Feats and class features that cost actions, as stat block abilities (with their rules text)."""
    out, seen = [], set()
    if not lookup:
        return out
    names = [f["name"] for f in pc.get("feats", [])] + list(pc.get("specials", []))
    for nm in names:
        if nm.lower() in seen:
            continue
        seen.add(nm.lower())
        e = lookup(nm, "feat") or lookup(nm, "action")
        if e and e.get("glyph"):
            cat = "defensive" if e["glyph"] in ("[R]", "[F]") else "offensive"
            out.append({"name": e["name"], "glyph": e["glyph"], "traits": list(e.get("traits") or []),
                        "category": cat, "text": e.get("text", "")})
    return out


def _g(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return ""
        d = d.get(k, "")
    return d


def _feat_texts(pc, lookup, skip=()):
    """Rules text for every feat and class feature: ([entries], [names with no rules text]).

    Pathbuilder exports names only, so descriptions come from the downloaded rules data. Names that don't
    match an entry there (renamed or from a book not in the data) are reported instead of silently dropped.
    """
    found, missing, seen = [], [], set(n.lower() for n in skip)
    if not lookup:
        return found, missing
    items = [(f["name"], f.get("type") or "Feat", f.get("choice"), f.get("level")) for f in pc.get("feats", [])]
    items += [(n, "Class feature", "", None) for n in pc.get("specials", [])]
    for name, typ, choice, level in items:
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        e = lookup(name, "feat") or lookup(name, "action")
        if not e:
            missing.append(name)
            continue
        found.append({"name": name + (f" ({choice})" if choice else ""), "type": typ, "level": level,
                      "glyph": e.get("glyph", ""), "traits": list(e.get("traits") or []),
                      "text": e.get("text", "")})
    return found, missing


def pc_details(pc, lookup=None, with_text=False, compact_actions=False):
    """Stat block dict for a PC or imported NPC, so the normal renderer shows clickable checks, saves,
    Strikes (with weapon traits), spells, actions from feats, feats, equipment, and more.

    lookup(name, kind) -> rules entry dict or None, used for weapon traits and feat actions.
    with_text=True also lists the description of every feat and class feature (passive ones included)."""
    sv = pc.get("saves") or {}
    saves = ", ".join(f"{n} {sv[k]:+d}" for k, n in (("fortitude", "Fort"), ("reflex", "Ref"), ("will", "Will"))
                      if k in sv)
    skills = ", ".join(f"{k} {v:+d}" for k, v in sorted((pc.get("skills") or {}).items()))
    per = pc.get("perception")
    extra = []
    if pc.get("class_dc"):
        extra.append(f"Class DC {pc['class_dc']}")
    if pc.get("pathbuilder_id"):
        extra.append(f"Pathbuilder ID {pc['pathbuilder_id']}")
    state = pc.get("state") or {}
    strikes = []
    from .statblock import _custom_strikes
    manual = []
    for st in _custom_strikes(state.get("manual_strikes")):
        st["manual"] = True
        manual.append(st)
    for st in list(pc.get("strikes") or []) + bomb_strikes(pc, lookup) + manual:
        st = dict(st)
        if st.get("bomb") or st.get("manual"):          # built from our own data: keep its traits and kind
            strikes.append(st)
            continue
        traits, entry = _entry_traits(lookup, st.get("weapon") or st.get("name"))
        st["traits"] = traits or st.get("traits") or (BOMB_TRAITS if "bomb" in (st.get("weapon") or "").lower() else [])
        st["kind"] = "Ranged" if _is_ranged(st.get("weapon") or st.get("name"), st["traits"], entry) else "Melee"
        strikes.append(st)
    feats = {}
    for f in pc.get("feats", []):
        feats.setdefault(f.get("type") or "Feat", []).append(f)
    order = {t: i for i, t in enumerate(FEAT_ORDER)}
    feat_groups = [(t, sorted(items, key=lambda x: (x.get("level") or 0, x["name"])))
                   for t, items in sorted(feats.items(), key=lambda kv: (order.get(kv[0], 99), kv[0]))]
    blurb = " | ".join(x for x in (
        " ".join(y for y in (pc.get("ancestry"), f"({pc['heritage']})" if pc.get("heritage") else "") if y),
        f"Background: {pc['background']}" if pc.get("background") else "",
        f"Deity: {pc['deity']}" if pc.get("deity") and str(pc["deity"]).lower() != "not set" else "") if x)
    actions = _pc_actions(pc, lookup)
    feat_text, missing = _feat_texts(pc, lookup, skip=[a["name"] for a in actions]) if lookup else ([], [])
    notes = ["Saves and skills are computed from the build."]
    if pc.get("item_mods"):
        notes.append("Included modifiers from the export: " + "; ".join(
            f"{stat}: " + ", ".join(f"{src} {v:+d}" for src, v in srcs) for stat, srcs in pc["item_mods"].items()) + ".")
    else:
        notes[0] += " Item bonuses (runes, skill items) aren't included unless the export lists them."
    return {"kind": "pc", "name": pc["name"], "level": pc.get("level"), "traits": [], "rarity": "common",
            "size": pc.get("size", ""), "blurb": blurb,
            "senses": [(x, f"name:{x.lower()}") for x in pc.get("senses", [])],
            "source": (pc.get("class") or "PC") + (" | " + " | ".join(extra) if extra else ""),
            "perception": f"{per:+d}" if isinstance(per, int) else "", "skills": skills, "saves": saves,
            "languages": ", ".join(pc.get("languages") or []),
            "ac": pc.get("ac"), "hp": pc.get("hp"), "speed": f"{pc['speed']} feet" if pc.get("speed") else "",
            "strikes": strikes, "spells": pc.get("spells") or [], "actions": actions,
            "immunities": def_pairs(pc.get("immunities", []) + _split_commas(_g(state, "defenses", "immunities"))),
            "weaknesses": def_pairs(pc.get("weaknesses", []) + _split_commas(_g(state, "defenses", "weaknesses"))),
            "resistances": def_pairs(pc.get("resistances", []) + _split_commas(_g(state, "defenses", "resistances"))),
            "abilities": ", ".join(f"{k.title()} {v:+d}" for k, v in (pc.get("mods") or {}).items()),
            "compact_actions": bool(compact_actions),
            "pc_extra": {"feats": feat_groups, "specials": pc.get("specials", []),
                         "equipment": pc.get("equipment", []), "armor": pc.get("armor", []),
                         "weapons": [{"name": w["name"], "base": w.get("weapon") or w["name"]} for w in pc.get("strikes") or []
                                     if isinstance(w, dict) and w.get("name") and not w.get("unarmed") and not w.get("bomb")
                                     and "bomb" not in str(w.get("weapon") or "").lower()],
                         "money": pc.get("money", {}), "formulas": pc.get("formulas", []),
                         "rituals": pc.get("rituals", []), "pets": pc.get("pets", []),
                         "feat_text": feat_text if with_text else [], "feat_text_count": len(feat_text),
                         "missing_text": missing, "has_lookup": bool(lookup)},
            "description": " ".join(notes)}

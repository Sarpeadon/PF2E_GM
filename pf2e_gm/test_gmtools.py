"""Checks for the GM Tools generators (job board, salvage and wares, afflictions, hazards, influence, quest builder, recap),
plus magic item styles and names, staves, grimoires and their spellbooks, the spell generator, NPC trappings, Party Loot,
the PNG item cards, and spell flavor.
Run from the folder that contains pf2e_gm:   python -m pf2e_gm.test_gmtools"""
import json
import random
import re

from . import gmtables, gmtools as gt, names, rules
from . import storygen as sg


def check(res):
    assert res["rows"], "no rows"
    for r in res["rows"]:
        assert r["text"].strip(), ("empty row", r["label"])
        assert "{" not in r["text"] and "}" not in r["text"], ("unfilled slot", r["label"], r["text"][:80])
        assert "[?" not in r["text"], ("unknown table", r["label"], r["text"][:80])
        assert not re.search(r"\b(an a|a a|a an|an an)\b", r["text"]), ("article", r["label"])
    json.dumps(res)
    gt.render_text(res)
    gt.render_text(res, "player")
    gt.render_markdown(res)


def tables_ok():
    reg = sg.Registry()
    mine = ("job.", "sign.", "deadline", "place", "parcel", "passenger", "pest", "lost.", "peddler.", "salvage.", "hazard.", "aff.",
            "influence.", "quest.", "recap.", "pay.silly", "item.container", "item.weapon", "item.prefix", "item.tool", "item.condition",
            "item.reset", "item.side", "item.pitch", "item.price.extra")
    names = set(reg.names())
    bad = [(n, p) for n in names if n.startswith(mine) for e in reg.entries(n)
           for p in sg.check_template(e["t"], names, allow_vars=True)]
    assert not bad, bad[:5]
    for needed in ("occupation", "job.task", "hazard.bp", "quest.title", "recap.award", "influence.trait", "salvage.where"):
        assert reg.has(needed), needed


def numbers_ok():
    """Hazard numbers come from the app's own tables."""
    assert gmtables.high_ac(1) == gmtables.AC[1][1]
    for rel in range(-4, 5):
        assert rules.hazard_xp(5 + rel, 5, False) == rules.SIMPLE_HAZARD_XP[rel]
        assert rules.hazard_xp(5 + rel, 5, True) == rules.CREATURE_XP[rel]
    res = gt.generate("hazards", {"level": 1, "offset": "0"}, random.Random(3))
    assert f"AC {gmtables.high_ac(res['rows'][0]['level'])}" in res["rows"][0]["text"]
    fight = gt.generate("quest", {"level": 3, "size": 6, "threat": "Low", "length": "Full (5 scenes)"}, random.Random(2))
    text = " ".join(r["text"] for r in fight["rows"])
    assert f"of a {rules.xp_budget('Low', 6)} XP budget" in text, text[:300]


def names_ok():
    """Poster and NPC names come from names.py, so a name that belongs to an established character is never handed out."""
    rng = random.Random(5)
    seen = 0
    for _ in range(150):
        board = gt.generate("jobs", {"count": 8, "flavor": "Hallowmead"}, random.Random(rng.random()))
        for r in board["rows"]:
            who = re.search(r"Posted by: (.+?), (?:a|an) ", r["text"]).group(1)
            assert not names.reserved(who), who
            seen += 1
        inf = gt.generate("influence", {"flavor": "Hallowmead"}, random.Random(rng.random()))
        assert not names.reserved(inf["title"].split(": ", 1)[1]), inf["title"]
    assert seen


def settings_ok():
    """Generic fantasy never shows Hallowmead places; every dropdown has choices in both settings."""
    rng = random.Random(11)
    for _ in range(40):
        for key in ("jobs", "salvage"):
            res = gt.generate(key, {"flavor": "Generic fantasy", "level": rng.randint(1, 10)}, random.Random(rng.random()))
            blob = " ".join(r["text"] for r in res["rows"]) + res["title"]
            assert not re.search(r"Crossings|Underhallow|midden|kobold maintenance", blob), (key, blob[:200])
    for spec in gt.specs():
        for o in spec["options"]:
            if o.get("source"):
                for flavor in gt.FLAVORS:
                    vals = gt.choice_values(o["source"], flavor, None)
                    if o["source"] != "faction":                   # factions come from the Notebook
                        assert vals, (spec["key"], o["key"], flavor)
                    assert len(vals) == len({v.lower() for v in vals})


def items_ok(rounds=2):
    """Every item kind at every style: styled parts are present, nothing is left unfilled, and edits still work."""
    from . import itemgen
    gen = itemgen.ItemGenerator(sg.Registry(), rng=random.Random(3))
    for _ in range(rounds):
        for kind in itemgen.KINDS:
            for style in itemgen.STYLES:
                for lvl in (1, 6, 14):
                    it = gen.generate(kind=kind, level=lvl, style=style, packs=["core", "hallowmead"])
                    text = itemgen.card_text(it, gm=True)
                    assert "[?" not in text and "{" not in text, (kind, style, text[:200])
                    if style != "standard":
                        assert itemgen.part(it, "drawback"), (kind, style)
                    if style == "ridiculous":
                        assert itemgen.part(it, "absurd") and itemgen.part(it, "limit"), kind
                    if kind == "staff":
                        assert itemgen.part(it, "spells")["text"].startswith("Cantrip"), it["name"]
                    gen.reroll(it)
                    gen.rescale(it, min(20, lvl + 2))
                    itemgen.check_item(it)
                    json.dumps(it)


def trappings_ok(n=150):
    """Every NPC carries trappings, whatever its Equipment; constructs don't carry food; Hallowmead lines stay in their pack."""
    from . import npcgen
    reg, rng = sg.Registry(), random.Random(8)
    for i in range(n):
        anc = rng.choice(["Goblin", "Kobold", "Ratfolk", "Grippli", "Leshy", "Automaton", "Poppet", "Awakened Animal", "Human", "Dwarf"])
        packs = rng.choice([["core"], ["core", "hallowmead"]])
        c, p = npcgen.generate(anc, rng.choice(list(npcgen.ROLES)), rng.randint(0, 12), rng=random.Random(i),
                               gear=rng.choice(["None", "Light", "Standard"]), registry=reg,
                               style=rng.choice(["standard", "grim", "whimsical", "ridiculous"]), packs=packs)
        tr = c.stats.get("trappings", "")
        assert tr and "[?" not in tr and "{" not in tr, (anc, tr)
        if anc in ("Automaton", "Poppet"):
            assert not re.search(r"bread|cheese|pie|fish|grub|nuts|tubers", tr.splitlines()[1], re.I), tr   # the food line
        if "hallowmead" not in packs:
            assert not re.search(r"refuse chute|Mending|WE DIG|plague records", tr), tr


def grimoires_ok(n=120):
    """A grimoire holds spells of its own tradition and ranks, never focus spells or rituals, can hold custom spells, and is
    named for its owner when an NPC carries it."""
    from . import itemgen, npcgen, npckit, spellgen as SG
    rng = random.Random(4)
    data = [{"name": f"T{r}-{i}", "rank": r, "traits": [rng.choice(["fire", "mental", "healing", "cold"])],
             "traditions": rng.sample(SG.TRADITIONS, rng.randint(1, 2)), "rarity": "common", "cantrip": r == 0,
             "focus": i == 0, "ritual": i == 1, "system": "pf"} for r in range(11) for i in range(25)]
    SG.set_pool(data, [{"name": "My Spell", "rank": "1", "spell_kind": "Spell", "traditions": []}])
    try:
        by = {d["name"]: d for d in data}
        gen = itemgen.ItemGenerator(sg.Registry(), rng=random.Random(9))
        for i in range(n):
            it = gen.generate(kind="grimoire", level=rng.randint(1, 20), style=rng.choice(SG.STYLES))
            book = itemgen.part(it, "spells")["data"]["book"]
            for e in book["cantrips"] + [x for v in book["ranks"].values() for x in v]:
                d = by.get(e["name"])
                if d:
                    assert it["tradition"] in d["traditions"] and not d["focus"] and not d["ritual"], e
            assert "[?" not in itemgen.card_text(it, gm=True)
        reg = sg.Registry()
        for i in range(40):
            c, p = npcgen.generate("Human", "Mage", 9, rng=random.Random(i), gear="Well-equipped", registry=reg)
            for it in npckit.kit_items(p["kit"]):
                if it["kind"] == "grimoire":
                    assert it["owner"] == c.name
    finally:
        SG._POOL = None


def spells_ok(n=600):
    """Generated spells render as rules entries with nothing left unfilled, in every style, kind, and shape."""
    from . import library, spellgen as SG, statblock
    reg = sg.Registry()
    for i in range(n):
        rr = random.Random(i)
        sp = SG.generate_spell(rr.randint(1, 10), rr.choice(SG.STYLES), rr.choice(["any"] + SG.TRADITIONS),
                               rr.choice(["Spell", "Cantrip"]), rr, reg, shape=rr.choice(["any", "area", "bolt", "hex", "ward", "utility"]))
        text = statblock.render_text(statblock.render_entry(library.spell_entry(sp)))
        assert sp["name"] and "[?" not in text and "{" not in text, text[:200]
        json.dumps(sp)


def party_loot_ok():
    """Party Loot: stacking, moving, selling at a chosen rate, coins, and Pathbuilder gear hidden after a sale until the
    player updates Pathbuilder."""
    from . import partyloot as L
    s = L.ensure({})
    a = L.add(s, L.new_entry("Healing Potion", 2, value_gp=3, level=1))
    L.add(s, L.new_entry("Healing Potion", 1, value_gp=3, level=1))
    assert a["qty"] == 3 and len(s["items"]) == 1
    L.move(s, a["id"], "Ana", 1)
    assert sorted((e["holder"], e["qty"]) for e in s["items"]) == [("Ana", 1), (L.STASH, 2)]
    assert L.sell_amount_cp(3, 2, 50) == 300 and L.sell_amount_cp(650, 1, 25) == 16250
    assert L.parse_coins("2 gp, 5 sp and 3 cp") == 253 and L.parse_coins("12") == 1200 and L.coin_text(253) == "2 gp, 5 sp and 3 cp"
    L.dispose(s, a["id"], "sold", 2, 300, L.STASH)
    L.credit_stash(s, 300)
    assert s["coins_cp"] == 300 and [g["how"] for g in s["log"]] == ["moved", "sold", "coins"]
    pc = {"name": "Ana", "equipment": [{"name": "Torch", "qty": 5}], "strikes": [], "armor": []}
    row = L.pb_rows(pc, s)[0]
    L.pb_dispose(s, row, "used", 2)
    assert L.pb_rows(pc, s)[0]["qty"] == 3
    pc["equipment"][0]["qty"] = 3                      # the player removes them in Pathbuilder
    assert L.pb_rows(pc, s)[0]["qty"] == 3
    L.prune_pb(s, [pc])
    assert not s["pb_removed"]
    w = {"name": "Grul'k", "equipment": [], "armor": [{"name": "Leather Armor", "pot": 1, "res": "resilient", "runes": ["slick"]}],
         "strikes": [{"name": "Thundermace (+3, striking, hooked)", "weapon": "Thundermace", "pot": 3, "runes": ["hooked"]}]}
    rows = {r["name"]: r for r in L.pb_rows(w, L.ensure({}), lambda n: {"thundermace": 0.2, "leather armor": 2}.get(n.lower()))}
    mace = rows["Thundermace (+3, striking, hooked)"]
    assert mace["value_gp"] == 9000.2 and mace["unpriced"] == ["hooked"], mace       # +3 potency 8,935 + striking 65
    assert rows["Leather Armor"]["value_gp"] == 547                                  # 160 + 340 + 45 + 2
    json.dumps(s)


def _check_card(card, CR):
    """Render one card every way and check the pictures: right size and mode, transparent really is, repeatable, no stray braces."""
    blob = json.dumps(card)
    assert "{" not in blob.replace('{"', "").replace(', "', "") and "[?" not in blob, blob[:200]
    combos = (("white", "blank"), ("transparent", "center"), ("parchment", "doodles"))
    for size, dims in CR.SIZES.items():
        for bg, fill in combos:
            pages = CR.render(card, size, bg, fill)
            assert pages and len(pages) <= 7, (card["title"], size, len(pages))
            for pg in pages:
                assert pg.size == dims and pg.mode == ("RGBA" if bg == "transparent" else "RGB"), (pg.size, pg.mode)
            if bg == "transparent":
                assert pages[0].getpixel((1, 1))[3] == 0                   # nothing is drawn outside the ink
            if bg == "white":
                assert pages[0].getpixel((1, 1)) == (255, 255, 255)
    a, b = CR.render(card, "poker", "white", "doodles"), CR.render(card, "poker", "white", "doodles")
    assert [x.tobytes() for x in a] == [x.tobytes() for x in b], "the same card must draw the same way"


def cards_ok():
    """Every kind of item, in every style, becomes a card that renders at both sizes, on every background, with every way of
    handling unused space. Rules entries, Custom Content items, and plain things (a heel of bread) get cards too."""
    try:
        from . import cardrender as CR
    except ImportError:
        print("cards skipped: Pillow isn't installed (python -m pip install pillow)")
        return
    from . import itemgen
    gen = itemgen.ItemGenerator(sg.Registry(), rng=random.Random(12))
    rng = random.Random(6)
    for kind in itemgen.KINDS:
        for style in ("standard", "ridiculous"):
            it = gen.generate(kind=kind, level=rng.randint(2, 14), style=style, packs=["core", "hallowmead"])
            card = CR.card_from_magic_item(it)
            assert card["title"] == it["name"] and card["level"] == it["level"], kind
            _check_card(card, CR)
    entry = {"name": "Healing Potion (Minor)", "kind": "item", "header": "Item 1", "traits": ["consumable", "potion"],
             "rarity": "common", "meta": [["Price", "4 gp"], ["Bulk", "L"]], "text": "A warm red liquid.\nYou regain 1d8 Hit Points."}
    _check_card(CR.card_from_entry(entry), CR)
    _check_card(CR.card_from_entry(entry, "Healing Potion (x3)", ["**Value** 12 gp"], ["x3"], "12 gp"), CR)
    _check_card(CR.card_basic("Heel of bread", None, 0, 2, "Party stash", "Looted from Gob", "Slightly nibbled."), CR)
    _check_card(CR.card_from_entry(dict(entry, text="A very long description. " * 400)), CR)          # runs onto extra cards


def item_names_ok(n=600):
    """An item's name says what it does: worn and held items carry a word for their main ability, runic weapons and armor for
    their rune, and in the Ridiculous style every kind carries the absurd ability's name word. Absurd lines made for a weapon or
    an armor never turn up on another kind of item."""
    import collections
    from . import itemdata, itemgen
    reg = sg.Registry()
    # every built-in absurd ability and oddity has a name word (a line you add in Edit Tables may not; the name then uses the main ability)
    for table in ("item.style.absurd", "item.style.oddity"):
        missing = [e["t"][:50] for e in reg.entries(table) if not any(t.startswith("nw:") for t in e["tags"])]
        assert not missing, (table, missing)
    only = {k: {e["t"] for e in reg.entries("item.style.absurd") if k in e["needs"]} for k in ("it:weapon", "it:armor")}
    assert only["it:weapon"] and only["it:armor"]
    gen = itemgen.ItemGenerator(reg, rng=random.Random(21))
    cultures = ["none"] + list(itemdata.CULTURE_INFO)
    rng = random.Random(22)
    stray = collections.Counter()
    for i in range(n):
        kind, style = rng.choice(list(itemgen.KINDS)), rng.choice(list(itemgen.STYLES))
        it = gen.generate(kind=kind, level=rng.randint(1, 20), style=style, tone=rng.choice(["any", "grim", "light", "weird"]),
                          culture=rng.choice(cultures), packs=rng.choice([["core"], ["core", "hallowmead"]]))
        name = it["name"].lower()
        assert it["name"].strip() and "[?" not in name and "{" not in name, name
        head = it.get("name_head")
        if kind in ("worn", "held"):
            assert head and head.lower() in name, (it["name"], head)
        ab = itemgen.part(it, "absurd")
        if ab is not None:
            word = (ab.get("data") or {}).get("nw")
            assert word and word.lower() in name, (it["name"], word)
            for k, texts in only.items():
                if ab["text"] in texts and k != "it:" + kind:
                    stray[(k, kind)] += 1
        if i % 7 == 0 and ab is not None:                       # a rerolled absurd ability renames the item
            gen.reroll(it, ["absurd"])
            word = (itemgen.part(it, "absurd").get("data") or {}).get("nw")
            assert word and word.lower() in it["name"].lower(), (it["name"], word)
    assert not stray, stray


def spell_flavor_ok(n=900):
    """Generated spells have flavor (smell, sound, look, aftermath; not rules) that is complete sentences with nothing left unfilled;
    a utility or Ridiculous spell is named for what it does and fills its fields; effect-specific sentences are never mixed between
    effects; a batch has different names; flavor reaches the rules entry."""
    import re
    from . import library, spellgen as SG, statblock
    reg = sg.Registry()
    rng = random.Random(14)
    seen_flavor = set()
    for i in range(n):
        r = random.Random(i)
        style = r.choice(SG.STYLES)
        sp = SG.generate_spell(r.randint(1, 10), style, r.choice(["any"] + SG.TRADITIONS), r.choice(["Spell", "Cantrip"]), r, reg,
                               shape=r.choice(["any", "area", "bolt", "hex", "ward", "utility"]))
        f = sp["flavor"]
        assert f and "{" not in f and "}" not in f and "[?" not in f and "  " not in f, (sp["name"], f)
        sents = re.split(r"(?<=[.!?]) ", f)
        assert 2 <= len(sents) <= 5 and all(x[0].isupper() and x[-1] in ".!?" for x in sents), f
        assert f not in sp["description"], "flavor is not part of the rules text"
        seen_flavor.add(f)
        if sp["shape"] in ("absurd", "utility"):
            assert sp["range"] or sp["targets"] or sp["area_size"], (sp["name"], "an effect with no range, target, or area")
            line = sp["description"].splitlines()[0]
            word = next(t[3:] for table in ("spell.utility", "spell.style.absurd") for e in reg.entries(table) if e["t"] == line
                        for t in e["tags"] if t.startswith("nw:"))
            assert word.replace("_", " ").lower() in sp["name"].lower(), (sp["name"], word)       # named for what it does
        entry = library.spell_entry(sp)
        assert entry["flavor"] == f and f in statblock.render_text(statblock.render_entry(entry)), sp["name"]
    assert len(seen_flavor) > 0.9 * n, "flavor repeats too much"
    # every utility and Ridiculous effect has a name word and its own look and aftermath sentences; spells carry the word in their name
    need = {}
    for e in reg.entries("spell.flavor.effect"):
        word = next(t[3:] for t in e["needs"] if t.startswith("nw:"))
        need.setdefault(word, set()).add(next(t[3:] for t in e["needs"] if t.startswith("fv:")))
    for table in ("spell.utility", "spell.style.absurd"):
        for e in reg.entries(table):
            word = next((t[3:] for t in e["tags"] if t.startswith("nw:")), "")
            assert word and {"look", "after"} <= need.get(word, set()), (table, e["t"][:50], word)
    for i in range(80):
        r = random.Random(500 + i)
        sp = SG.generate_spell(3, r.choice(["ridiculous", "standard"]), "any", "Spell", r, reg, shape="utility")
        mine = {w for w, kinds in need.items() if any(x["t"] in sp["flavor"] for x in reg.entries("spell.flavor.effect")
                                                        if f"nw:{w}" in x["needs"])}
        assert len(mine) <= 1, (sp["name"], mine)
    # a batch: different names, none already yours, the number asked for
    batch = SG.generate_spells(10, "any", "ridiculous", "arcane", "Spell", rng, reg, avoid=["Sudden Geese"])
    names = [b["name"].lower() for b in batch]
    assert len(batch) == 10 and len(set(names)) == 10 and "sudden geese" not in names


def grimoire_spell_links_ok():
    """A grimoire's spells (and a staff's) are links: a spell from your data or one of yours opens its rules entry, a brand-new spell
    opens from the book. The new spell's flavor and rules are kept in the book."""
    from . import itemgen, spellgen as SG
    reg = sg.Registry()
    data = [{"name": f"T{r}-{i}", "rank": r, "traits": ["fire"], "traditions": ["arcane"], "rarity": "common", "cantrip": r == 0,
             "focus": False, "ritual": False, "system": "pf"} for r in range(7) for i in range(10)]
    SG.set_pool(data, [{"name": "My Flare", "rank": "1", "spell_kind": "Spell", "traditions": ["arcane"]}])
    try:
        gen = itemgen.ItemGenerator(reg, rng=random.Random(4))
        found_new = found_custom = False
        for i in range(120):
            it = gen.generate(kind="grimoire", level=rng_level(i), style=["standard", "grim", "whimsical", "ridiculous"][i % 4], tradition="arcane")
            refs = [r for _t, _s, r in itemgen.card_segments(it) if r]
            book = itemgen.part(it, "spells")["data"]["book"]
            names = [e["name"] for e in book["cantrips"]] + [e["name"] for v in book["ranks"].values() for e in v]
            assert len(refs) == len(names) and all(r.startswith(("spell:", "newspell:")) for r in refs), refs
            for g in itemgen.part(it, "spells")["data"]["generated"]:
                found_new = True
                assert "newspell:" + g["name"] in refs and g["flavor"] and g["description"], g
            found_custom = found_custom or "spell:My Flare" in refs
        assert found_new and found_custom
        st = gen.generate(kind="staff", level=9)
        assert [r for _t, _s, r in itemgen.card_segments(st) if r], "a staff's spells are links"
    finally:
        SG._POOL = None


def rng_level(i):
    return 3 + (i * 5) % 16


def main(rounds=300):
    party_loot_ok()
    items_ok()
    item_names_ok()
    cards_ok()
    grimoires_ok()
    spells_ok()
    spell_flavor_ok()
    grimoire_spell_links_ok()
    trappings_ok()
    tables_ok()
    numbers_ok()
    names_ok()
    settings_ok()
    rng = random.Random(7)
    made = 0
    for _ in range(rounds):
        base = dict(level=rng.randint(1, 20), size=rng.randint(2, 8), silly=rng.choice(gt.SILLY_LEVELS), flavor=rng.choice(gt.FLAVORS))
        for spec in gt.specs():
            params = dict(base)
            if spec["key"] == "recap":
                params.update(notes="The party met a goat\n[loot] a spoon\n[gm] the goat is the mayor\n[thread] who owns the boat",
                              players="Ana, Bo")
            res = gt.generate(spec["key"], params, random.Random(rng.random()))
            check(res)
            for i in range(len(res["rows"])):
                gt.reroll_row(res, i, rng)
            check(res)
            made += 1
    print(f"ok: {made} results from {len(gt.specs())} tools, all rows rerolled")


if __name__ == "__main__":
    main()

"""Checks that an item's name says what the item does (itemgen.make_name and the item.name.head tables in itemdata.py).
Run from the folder that contains pf2e_gm:   python -m pf2e_gm.test_itemnames
Set LORE = False to skip the generated histories (the names don't depend on them), which makes it quicker."""
import collections
import json
import random
import re

from . import itemdata, itemgen
from . import storygen as sg

LORE = True


def _gen(n=900, seed=31):
    """Yield n items across every kind, style, tone, culture, and pack, as (item, kind, style, tone)."""
    reg = sg.Registry()
    gen = itemgen.ItemGenerator(reg, rng=random.Random(seed))
    cultures = ["none"] + list(itemdata.CULTURE_INFO)
    rng = random.Random(seed + 1)
    for _ in range(n):
        kind, style = rng.choice(list(itemgen.KINDS)), rng.choice(list(itemgen.STYLES))
        tone = rng.choice(["any", "grim", "light", "weird"])
        it = gen.generate(kind=kind, level=rng.randint(1, 20), style=style, tone=tone, culture=rng.choice(cultures),
                          packs=rng.choice([["core"], ["core", "hallowmead"]]), lore=LORE)
        yield gen, it, kind, style, tone


def expected_word(effect):
    """The plain word an ability's name should carry, worked out from the ability itself (not from its head word)."""
    d = effect["data"]
    fx, opts = d.get("fx"), d.get("opts") or {}
    if fx in ("spell_day", "spell_cantrip"):
        return d["spell"]
    return {"skill": opts.get("skill"), "perception": "Perception", "speed": "Speed", "light": "Light",
            "resist": (opts.get("energy") or "").title(), "save_vs": (opts.get("trait") or "").title(),
            "fortune": opts.get("skill"),
            "sense": {"low-light vision": "Low-Light Vision", "darkvision": "Darkvision"}.get(opts.get("sense"), "Scent")}.get(fx, "")


def names_say_what_items_do(n=900):
    """A worn or held item's name carries a plain word for its main ability; a Whimsical one also its oddity; a Ridiculous one
    (any kind) its absurd ability; there are no long 'That <verb>' names; names are short; the flourish is a short ending on
    about a third of Weird, Light, and Grim names and never on a plain one."""
    lengths, flourish, total = [], collections.Counter(), collections.Counter()
    for gen, it, kind, style, tone in _gen(n):
        name = it["name"]
        assert name.strip() and "[?" not in name and "{" not in name, name
        lengths.append(len(name))
        if kind != "grimoire":
            assert not re.search(r" That (?!Wants to)", name), name
        if kind in ("worn", "held"):
            main = itemgen.main_effect(itemgen.effect_parts(it))
            word = expected_word(main)
            assert word and word.lower() in name.lower(), (name, word, main["data"].get("fx"))
            eff_tone = it["settings"]["tone"]
            total[eff_tone] += 1
            flourish[eff_tone] += "," in name
            odd = (itemgen.part(it, "oddity") or {}).get("data", {}).get("nw")
            if style == "whimsical" and odd:
                assert odd.lower() in name.lower(), (name, odd)
        ab = itemgen.part(it, "absurd")
        if ab is not None:
            word = (ab.get("data") or {}).get("nw")
            assert word and word.lower() in name.lower(), (name, word)
        json.dumps(it)
    assert sum(1 for l in lengths if l <= 46) >= 0.85 * len(lengths), "names are running long"
    assert max(lengths) <= 80, max(lengths)
    assert flourish["any"] == 0, "a plain name got a flourish"
    for tone in ("weird", "light", "grim"):
        if total[tone] >= 40:
            rate = flourish[tone] / total[tone]
            assert 0.15 <= rate <= 0.5, (tone, rate)


def word_lists_fit():
    """The words for what an item does don't contradict it (a light item is not named for the night)."""
    thing = itemdata.FX_NAME_WORDS["thing"]
    assert not any(w in " ".join(thing["light"].split("|")).lower() for w in ("night", "dark", "shade", "shadow")), thing["light"]
    for slot, by in itemdata.FX_NAME_WORDS.items():
        for tag, words in by.items():
            parts = words.split("|")
            assert len(parts) == len(set(parts)), (slot, tag)


def renames_follow_the_ability(n=120):
    """A rescale or reroll that changes a worn item's ability changes its name; an old item with no head word still names itself."""
    reg = sg.Registry()
    gen = itemgen.ItemGenerator(reg, rng=random.Random(8))
    moved = 0
    for i in range(n):
        it = gen.generate(kind="worn", level=5, lore=LORE, seed=i)
        before = itemgen.effect_heads(it)
        gen.rescale(it, 14)
        if itemgen.effect_heads(it) != before:
            moved += 1
            main = itemgen.main_effect(itemgen.effect_parts(it))
            assert main["data"]["head"].lower() in it["name"].lower(), (it["name"], main["data"]["head"])
        gen.reroll(it, ["effect1"])
        main = itemgen.main_effect(itemgen.effect_parts(it))
        assert main["data"]["head"].lower() in it["name"].lower(), (it["name"], main["data"]["head"])
    assert moved > 0
    it = gen.generate(kind="worn", level=6, lore=LORE)
    for p in itemgen.effect_parts(it):
        p["data"].pop("head", None)
    assert gen.make_name(it, force=True).strip()


def main():
    word_lists_fit()
    names_say_what_items_do()
    renames_follow_the_ability()
    print("ok: item names say what the items do")


if __name__ == "__main__":
    main()

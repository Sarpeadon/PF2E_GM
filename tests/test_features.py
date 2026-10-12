"""v7 features: hazards, duplicate to custom, custom spells/abilities, sessions, quick reference."""
from pathlib import Path

from pf2e_gm import data, session as sess
from pf2e_gm.encounter import (Encounter, encounter_from_dict, encounter_to_dict, filter_pool, generate,
                               make_variant)
from pf2e_gm.library import ability_entry, ability_to_line, custom_rule_entries, spell_entry
from pf2e_gm.loot import LootBundle
from pf2e_gm.models import Creature, Item
from pf2e_gm.quickref import dc_for, reference_segments, spell_rank_dc
from pf2e_gm.rules import xp_of
from pf2e_gm.statblock import (DetailsDB, custom_details, details_to_custom, parse_abilities, render,
                               render_entry, render_text)

FIX = Path(__file__).parent / "fixtures"


def load(tmp_path):
    db = tmp_path / "d.sqlite"
    cs, its = data.build_index(FIX, tmp_path / "i.json", db)
    return cs, its, DetailsDB(db)


# ---------- hazards ----------
def test_hazard_parse_xp_render(tmp_path):
    cs, _, db = load(tmp_path)
    pit = next(c for c in cs if c.name == "Hidden Pit")
    bones = next(c for c in cs if c.name == "Grasping Bones")
    assert pit.is_hazard and not pit.complex and bones.complex and pit.base_uid.startswith("H|")
    assert xp_of(pit, 3) == 8 and xp_of(pit, 1) == 16          # simple hazard table
    assert xp_of(bones, 5) == 40                                # complex = creature XP
    t = render_text(db.get(pit.base_uid))
    for s in ("Hidden Pit    Hazard 3", "Stealth +10 (DC 20) (trained)", "Disable DC 18 Thievery",
              "AC 18; Fort +9, Ref +5", "Hardness 9, HP 36 (BT 18); Immunities Critical Hits",
              "Pitfall [R]", "Reset Manual."):
        assert s in t, s
    tb = render_text(db.get(bones.base_uid))
    assert "Routine (1 action) The hands attack." in tb and "Melee [1] Claw +14, Damage 2d8+4 slashing" in tb
    assert "rolls initiative with Stealth" in tb
    assert make_variant(pit, "elite") is pit


def test_hazard_generation(tmp_path):
    cs, _, _ = load(tmp_path)
    assert not any(c.is_hazard for c in filter_pool(cs, 4))
    simple = filter_pool(cs, 4, hazards="simple")
    assert {c.name for c in simple if c.is_hazard} == {"Hidden Pit"}
    assert {c.name for c in filter_pool(cs, 4, hazards="both", hazard_traits=["haunt"]) if c.is_hazard} == {"Grasping Bones"}
    pool = filter_pool(cs, 4, hazards="both")
    encs = generate(pool, 4, 4, "Moderate", count=6, seed=5, max_hazards=1, cohesion="strict")
    assert encs
    for e in encs:
        hz = [c for c, n in e.groups if c.is_hazard]
        assert len(hz) <= 1 and all(n == 1 for c, n in e.groups if c.is_hazard)
        assert e.xp <= e.budget
    assert any(c.is_hazard for e in generate(pool, 4, 4, "Moderate", count=6, seed=1, max_hazards=1, attempts=900)
               for c, _ in e.groups)
    assert not any(c.is_hazard for e in generate(pool, 4, 4, "Moderate", count=6, seed=1, max_hazards=0)
                   for c, _ in e.groups)


# ---------- duplicate to custom ----------
def test_duplicate_round_trip(tmp_path):
    cs, _, db = load(tmp_path)
    g = next(c for c in cs if c.name == "Ghoul Stalker")
    kw = details_to_custom(db.get(g.base_uid), name="Bog Ghoul")
    c = Creature(**kw)
    assert c.custom and c.source == "Hallowmead" and c.stats["fort"] == 11 and c.stats["perception"] == 12
    t = render_text(custom_details(c))
    for s in ("Bog Ghoul    Creature 5", "Perception +12; Darkvision, Scent (imprecise) 30 feet",
              "AC 22; Fort +11, Ref +14, Will +12", "Weaknesses Vitality 5",
              "Melee [1] Jaws +15 (finesse), Damage 2d6+6 piercing plus Paralysis",
              "Occult Innate Spells DC 21, attack +13; Rank 3: Fear (x2); Cantrips: Daze",
              "Attack of Opportunity [R] Jaws only.", "Lunging Bite [2] Strides then Strikes.",
              "Paralysis (incapacitation, occult) Any living creature hit", "Recall Knowledge DC 20 (Religion"):
        assert s in t, s
    refs = {x: r for x, s, r in render(custom_details(c)) if r}
    assert refs["Paralysis"] == "self:Paralysis"                    # Strike effect jumps to own ability
    assert db.resolve(refs["Fear"])                                  # spell still clickable


def test_parse_abilities():
    a = parse_abilities("Spore Burst [2] (fungus, poison): Creatures in a 10-foot emanation are sickened 1.\n"
                        "  More text.\nThick Hide: Resistance applies.\nGrasping Root [R]: When hit, grab.")
    assert [x["name"] for x in a] == ["Spore Burst", "Thick Hide", "Grasping Root"]
    assert a[0]["glyph"] == "[2]" and a[0]["traits"] == ["fungus", "poison"] and "More text." in a[0]["text"]
    assert [x["category"] for x in a] == ["offensive", "interaction", "defensive"]


# ---------- custom spells / abilities ----------
def test_custom_spell_and_ability(tmp_path):
    _, _, db = load(tmp_path)
    sp = {"name": "Sporecloud", "spell_kind": "Spell", "rank": "2", "traditions": ["primal"], "traits": ["poison"],
          "cast": "2", "range": "30 feet", "area_size": "10", "area_type": "burst", "defense": "basic Fortitude",
          "damage": "3d6", "damage_type": "poison", "heighten_damage": "1d6", "heighten_interval": "1",
          "description": "Spores burst. Creatures that fail are sickened 1.",
          "heightened": "Heightened (+1) The damage increases by 1d6.\nHeightened (6th) Targets are also slowed 1."}
    ab = {"name": "Spore Burst", "glyph": "[2]", "traits": ["fungus"], "frequency": "once per minute",
          "text": "10-foot emanation; DC 20 basic Fortitude or sickened 1."}
    e = spell_entry(sp)
    assert e["header"] == "Spell 2" and e["glyph"] == "[2]" and "primal" in e["traits"]
    db.set_custom_rules(custom_rule_entries([sp], [ab]))
    assert "Sporecloud" in db.rule_names("spell") and "Spore Burst" in db.rule_names("action")
    caster = Creature("Mycelid", 9, custom=True, stats={"spells": "Primal Innate Spells DC 27, attack +19; Rank 5: Sporecloud (x2)"})
    refs = {x: r for x, s, r in render(custom_details(caster)) if r}
    t = render_text(render_entry(db.rule(db.resolve(refs["Sporecloud"]))))
    for s in ("Cast by Mycelid (Primal Innate Spells)", "Rank 5 (heightened from 2); DC 27; spell attack +19; 2/day",
              "Damage at this rank 6d6 poison", "Heightened (+1) applied 3 times", "Area 10-foot burst",
              "Defense basic Fortitude"):
        assert s in t, s
    assert "Heightened (6th)" not in t.split("Heightened effects")[1].split("────")[0]
    line = ability_to_line(ab)
    assert line == "Spore Burst [2] (fungus): Frequency once per minute; 10-foot emanation; DC 20 basic Fortitude or sickened 1."
    assert parse_abilities(line)[0]["glyph"] == "[2]"
    assert db.rule(db.resolve("action:Spore Burst"))["header"] == "Ability"
    assert render_text(render_entry(ability_entry(ab))).startswith("Spore Burst [2]")


# ---------- sessions ----------
def test_sessions(tmp_path):
    gob = Creature("Goblin", 1, hp=6, ac=16)
    enc = Encounter([(gob, 4)], 120, 80)
    d = encounter_to_dict(enc, threat="Severe")
    back = encounter_from_dict(d)
    assert back.groups[0][1] == 4 and back.groups[0][0].name == "Goblin"
    s = sess.new_session("Session 1", 2)
    big = sess.new_entry(d, name="Warren")
    small = sess.new_entry(encounter_to_dict(Encounter([(gob, 1)], 40, 80)), name="Sentry")
    s["encounters"] += [big, small]
    items = [Item(f"P{i}", 3, price_gp=60 - i) for i in range(4)] + [Item(f"C{i}", 2, consumable=True, price_gp=6) for i in range(6)]
    bundle = LootBundle(level=2, permanent=items[:4], consumables=items[4:], currency=70)
    split = sess.split_treasure(s["encounters"], bundle)
    got = {k: sum(t["value_gp"] for t in v) for k, v in split.items()}
    assert got[big["id"]] > got[small["id"]]                          # bigger fight, bigger share
    assert sum(len(v) for v in split.values()) == 12                  # 10 items + 2 currency rows
    assert sum(t["value_gp"] for v in split.values() for t in v if t["kind"] == "currency") == 70
    for e in s["encounters"]:
        e["treasure"] = split[e["id"]]
    ledger = []
    xp = sess.complete(big, 5, ledger, 2, today="2026-10-05")
    assert xp == 96 and big["status"] == "done" and len(ledger) == len(big["treasure"])
    assert sess.complete(big, 5, ledger, 2) == 0                      # no double award
    assert sess.split_treasure([big], bundle) == {}                   # done encounters get nothing new
    assert sess.reopen(big, ledger) == 96 and ledger == [] and big["status"] == "planned"
    assert sess.award_for(80, 4) == 80 and sess.xp_progress(1340) == (1, 340)


# ---------- quick reference ----------
def test_quickref():
    assert dc_for(5) == 20 and dc_for(5, "Hard") == 22 and dc_for(5, "Normal", "Rare") == 25
    assert dc_for(0, "Incredibly easy") == 4 and spell_rank_dc(3) == dc_for(5)
    text = "".join(t for t, s, r in reference_segments(5))
    assert "Encounter Budget (party of 5)" in text and "Moderate 100" in text and "Untrained 10" in text


# ---------- party size ----------
def test_party_of_five(tmp_path):
    from pf2e_gm.loot import extra_pc_items, generate_level, ledger_summary, targets
    from pf2e_gm.rules import DEFAULT_PARTY_SIZE, xp_budget
    assert DEFAULT_PARTY_SIZE == 5
    assert [xp_budget(t, 5) for t in ("Trivial", "Low", "Moderate", "Severe", "Extreme")] == [50, 80, 100, 150, 200]
    assert extra_pc_items(2, 5) == ([(3, 1)], [(3, 1), (2, 1)])
    assert extra_pc_items(2, 6) == ([(3, 1), (2, 1)], [(3, 2), (2, 2)])
    perm, cons = targets(2, 5)
    assert perm == [(3, 3), (2, 2)] and cons == [(3, 3), (2, 3), (1, 2)]
    assert targets(2, 3) == targets(2, 4)                                  # items not reduced below four
    _, its, _ = load(tmp_path)
    b = generate_level(its, 5, 5, seed=2)
    assert len(b.permanent) == 5 and len(b.consumables) == 8 and b.currency == 400
    assert len({i.name for i in b.permanent + b.consumables}) == 13       # no duplicates
    assert any("beyond four" in n for n in b.notes)
    s = ledger_summary([], 2, 5)
    assert s["permanent"] == (0, 5) and s["consumables"] == (0, 8) and s["currency"] == (0, 88) and s["value"] == (0, 375)
    assert sess.award_for(100, 5) == 80 and sess.award_for(150, 5) == 120   # award as for four PCs
    text = "".join(t for t, s, r in reference_segments())
    assert "party of 5" in text and "Moderate 100" in text and "add 1 permanent item" in text


def test_cache_dir(tmp_path, monkeypatch):
    import importlib
    from pf2e_gm import storage
    monkeypatch.setenv("PF2E_GM_CACHE", str(tmp_path / "cache"))
    st = importlib.reload(storage)
    try:
        assert st.PF2E_DATA == tmp_path / "cache" / "pf2e_data" and st.FILES["party"].parent == st.DATA_DIR
        old = st.DATA_DIR / "foundry_index.json"
        existed = old.exists()
        if not existed:
            old.write_text("{}")
            assert "foundry_index.json" in st.migrate_cache() and (tmp_path / "cache" / "foundry_index.json").exists()
    finally:
        monkeypatch.delenv("PF2E_GM_CACHE")
        importlib.reload(storage)

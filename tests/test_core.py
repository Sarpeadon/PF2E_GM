"""Core regression tests (index, encounters, treasure, stat blocks, Elite/Weak, combat)."""
import random
from pathlib import Path

from pf2e_gm import data
from pf2e_gm.adjust import apply_adjustment, recall_knowledge
from pf2e_gm.combat import CombatState
from pf2e_gm.encounter import filter_pool, generate, make_variant
from pf2e_gm.loot import filter_items, generate_level
from pf2e_gm.rules import xp_budget
from pf2e_gm.statblock import DetailsDB, render, render_entry, render_text

FIX = Path(__file__).parent / "fixtures"


def load(tmp_path):
    db = tmp_path / "d.sqlite"
    cs, its = data.build_index(FIX, tmp_path / "i.json", db)
    return cs, its, DetailsDB(db)


def test_index_and_pathbuilder(tmp_path):
    cs, its, _ = load(tmp_path)
    assert sum(not c.is_hazard for c in cs) == 61 and sum(c.is_hazard for c in cs) == 2 and len(its) == 300
    assert data.load_pathbuilder(FIX / "pathbuilder.json") == ("Ulzerett", 5)
    assert xp_budget("Severe", 5) == 150


def test_encounters_and_loot(tmp_path):
    cs, its, _ = load(tmp_path)
    encs = generate(filter_pool(cs, 5, {"common", "uncommon"}), 5, 4, "Moderate", seed=3)
    assert encs and all(e.xp <= e.budget for e in encs)
    assert not any(c.is_hazard for e in encs for c, _ in e.groups)       # hazards off by default
    b = generate_level(filter_items(its, {"common"}, True), 5, 4, seed=1)
    assert b.currency == 320 and len(b.permanent) == 4


def test_statblock_links_and_heightening(tmp_path):
    cs, _, db = load(tmp_path)
    g = next(c for c in cs if c.name == "Ghoul Stalker")
    d = db.get(g.base_uid)
    t = render_text(d)
    assert "Melee [1] Jaws +15 (finesse), Damage 2d6+6 piercing plus Paralysis" in t
    assert "Recall Knowledge DC 20 (Religion" in t
    refs = {x: r for x, s, r in render(d) if r}
    assert db.rule(db.resolve(refs["Paralyzed"]))["name"] == "Paralyzed"
    fear = render_text(render_entry(db.rule(db.resolve(refs["Fear"]))))
    assert "Rank 3 (heightened from 1); DC 21" in fear and "2/day" in fear
    e = apply_adjustment(d, "elite")
    assert e["hp"] == 95 and "Jaws +17" in render_text(e)
    assert recall_knowledge(e)["dc"] == 22


def test_combat_basics():
    cs = CombatState()
    g = cs.add("Ghoul", perception=12, hp=75, ac=22)
    pc = cs.add("Ulz", kind="pc", perception=11, hp=55, ac=22)
    cs.roll_initiative(random.Random(1)); cs.start()
    cs.set_condition(g.id, "frightened", 2); cs.set_condition(g.id, "off-guard")
    assert g.effective_ac()[0] == 18
    cs.damage(pc.id, 60)
    assert pc.conditions["dying"] == 1

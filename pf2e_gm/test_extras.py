"""Quick check for the GM extras. Run from the folder that contains pf2e_gm:   python -m pf2e_gm.test_extras"""
import json
import random
import re

from . import extras_core as core
from . import extras_tools as tools


def check(res):
    assert res["rows"], "no rows"
    for r in res["rows"]:
        assert r["text"].strip(), ("empty row", r["label"])
        assert "{" not in r["text"] and "}" not in r["text"], ("unfilled slot", r["label"])
        assert not re.search(r"\b(an a|a a|a an|an an)\b", r["text"]), ("article", r["label"])
    json.dumps(res)
    core.render_text(res)
    core.render_text(res, "player")
    core.render_markdown(res)


def main(rounds=400):
    rng = random.Random(7)
    made = 0
    for _ in range(rounds):
        base = dict(level=rng.randint(1, 20), size=rng.randint(2, 8), silly=rng.choice(core.SILLY_LEVELS),
                    flavor=rng.choice(core.FLAVORS))
        for spec in tools.SPECS:
            res = tools.generate(spec["key"], dict(base), random.Random(rng.random()))
            check(res)
            for i in range(len(res["rows"])):
                tools.reroll_row(res, i, rng)
            check(res)
            made += 1
    print(f"ok: {made} results from {len(tools.SPECS)} tools, all rows rerolled")


if __name__ == "__main__":
    main()

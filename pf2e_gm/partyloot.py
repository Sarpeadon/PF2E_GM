"""Party Loot: everything the party owns, and who is carrying it.

The loot list (user_data/party_loot.json) holds what the party has picked up through the app: treasure awarded on the
Treasure tab, items from the Magic Items tab and My Items, an NPC's gear (Loot This NPC), and anything you add by hand. An
entry keeps the whole item when it has one (a generated item, so a grimoire keeps its spells and card), or the name of an
item in your rules data, so its rules text can be shown. Each entry has a holder: one of the PCs, or the party stash.

Pathbuilder gear (each PC's equipment, armor, weapons, and coins as imported) is shown alongside, valued at the base item's
price plus its runes (fundamental runes from the rune tables in itemdata.py, property runes from those tables or your rules
data; a rune or special material with no price on file is listed in the value as unpriced), read from the party
list, so the tab really shows everything the party owns. It is never copied into the loot file, because a re-import from
Pathbuilder replaces it. When you sell or use up a Pathbuilder item here, the tab hides it until the player removes it in
Pathbuilder and you refresh the party; it then stops hiding it on its own (see pb_rows).

Selling pays whoever carried the item: a PC's sale goes into that character's funds (the Downtime tab's Funds, which the
app calls with dt.purse_add), and a sale from the party stash goes into the stash's coins. The sale rate is yours to set; the
default is 50%, the usual rate for selling an item (Player Core, Buying and Selling Items). Sold, used, lost, and given-away
items move to the history, which also records each coin movement.
"""
import copy
import datetime
import re
import uuid

STASH = "Party stash"
VERSION = 1
DEFAULT_RATE = 50                  # percent of an item's price paid when it is sold (Player Core: half price)
HOW = {"sold": "Sold", "used": "Used up", "lost": "Lost", "given": "Given away", "moved": "Moved", "coins": "Coins"}


def today():
    return datetime.date.today().isoformat()


def new_store():
    return {"version": VERSION, "items": [], "coins_cp": 0, "settings": {"sell_rate": DEFAULT_RATE}, "log": [],
            "pb_removed": []}


def ensure(store):
    """A loot store with every key, whatever an older file held."""
    s = store if isinstance(store, dict) else {}
    base = new_store()
    for k, v in base.items():
        s.setdefault(k, copy.deepcopy(v))
    s["settings"].setdefault("sell_rate", DEFAULT_RATE)
    for e in s["items"]:
        e.setdefault("qty", 1)
        e.setdefault("holder", STASH)
    return s


# ------------------------------------------------------------------------------------------------ money
def to_cp(gp):
    return int(round(float(gp or 0) * 100))


def coin_text(cp):
    """'12 gp, 3 sp and 4 cp', '-5 sp', '0 cp'."""
    cp = int(cp or 0)
    sign = "-" if cp < 0 else ""
    cp = abs(cp)
    gp, rest = divmod(cp, 100)
    sp, c = divmod(rest, 10)
    bits = [f"{gp:,} gp" if gp else "", f"{sp} sp" if sp else "", f"{c} cp" if c else ""]
    bits = [b for b in bits if b]
    if not bits:
        return "0 cp"
    text = bits[0] if len(bits) == 1 else ", ".join(bits[:-1]) + " and " + bits[-1]
    return sign + text


def parse_coins(text):
    """'5 gp 3 sp', '12', '2.5 gp', '40 sp' -> copper. A bare number is gold. Raises ValueError."""
    t = str(text or "").strip().lower().replace(",", "")
    if not t:
        raise ValueError("Type an amount, for example 5 gp or 3 sp.")
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        return to_cp(float(t))
    total, found = 0, False
    for n, unit in re.findall(r"(-?\d+(?:\.\d+)?)\s*(pp|gp|sp|cp)\b", t):
        total += round(float(n) * {"pp": 1000, "gp": 100, "sp": 10, "cp": 1}[unit])
        found = True
    if not found:
        raise ValueError(f"Can't read '{text}' as coins. Try 5 gp, 3 sp, or 2 gp 5 sp.")
    return int(total)


def money_cp(money):
    """Pathbuilder's money dict (pp, gp, sp, cp) in copper."""
    m = money or {}
    return sum(int(m.get(k) or 0) * v for k, v in (("pp", 1000), ("gp", 100), ("sp", 10), ("cp", 1)))


def sell_amount_cp(value_gp, qty=1, rate_pct=DEFAULT_RATE):
    return int(round(to_cp(value_gp) * max(0, int(qty)) * max(0.0, float(rate_pct)) / 100.0))


# ------------------------------------------------------------------------------------------------ entries
def new_entry(name, qty=1, holder=STASH, value_gp=0.0, level=None, kind="", source="", magic_item=None, notes="",
              rules_name="", custom=False):
    """One loot entry. value_gp is the price of one. magic_item is a generated item (a dict) kept whole. rules_name is the
    name of an item in your rules data, for its rules text. kind is permanent, consumable, or a short word of your own."""
    if magic_item is not None:
        magic_item = copy.deepcopy(magic_item)
        name = name or magic_item.get("name", "")
        value_gp = value_gp or float(magic_item.get("price_gp") or 0)
        level = level if level is not None else magic_item.get("level")
        kind = kind or ("consumable" if magic_item.get("consumable") else "permanent")
    return {"id": uuid.uuid4().hex[:10], "name": str(name).strip() or "Unnamed item", "qty": max(1, int(qty or 1)),
            "holder": holder or STASH, "value_gp": round(float(value_gp or 0), 2), "level": level, "kind": kind or "",
            "source": source, "date": today(), "notes": notes, "magic_item": magic_item, "rules_name": rules_name,
            "custom": bool(custom)}


def _stackable(a, b):
    return (a["magic_item"] is None and b["magic_item"] is None and a["name"].lower() == b["name"].lower()
            and a["holder"] == b["holder"] and abs(a["value_gp"] - b["value_gp"]) < 0.005 and a.get("notes", "") == b.get("notes", ""))


def add(store, entry):
    """Add an entry, stacking it onto an identical plain item the same holder already has. Returns the entry it ended in."""
    for e in store["items"]:
        if _stackable(e, entry):
            e["qty"] += entry["qty"]
            return e
    store["items"].append(entry)
    return entry


def find(store, entry_id):
    return next((e for e in store["items"] if e["id"] == entry_id), None)


def _log(store, how, name, qty=0, holder="", amount_cp=0, payee="", note=""):
    store["log"].append({"date": today(), "how": how, "name": name, "qty": qty, "holder": holder, "amount_cp": int(amount_cp),
                         "payee": payee, "note": note})
    del store["log"][:-500]


def take(store, entry_id, qty=None):
    """Remove qty (all by default) of an entry. Returns a copy of what was taken (qty set), or None."""
    e = find(store, entry_id)
    if e is None:
        return None
    qty = e["qty"] if qty is None else max(1, min(int(qty), e["qty"]))
    out = dict(e, qty=qty)
    e["qty"] -= qty
    if e["qty"] <= 0:
        store["items"].remove(e)
    return out


def dispose(store, entry_id, how, qty=None, amount_cp=0, payee="", note=""):
    """Sell, use up, lose, or give away qty of an entry. The money (amount_cp) is not paid here: the caller pays the payee
    (a PC's funds, or credit_stash for the party stash). Returns the entry as it was taken."""
    if how not in HOW:
        raise ValueError(f"Unknown way to remove an item: {how}")
    got = take(store, entry_id, qty)
    if got is not None:
        _log(store, how, got["name"], got["qty"], got["holder"], amount_cp, payee, note)
    return got


def move(store, entry_id, holder, qty=None):
    """Give qty of an entry to another holder (a PC or the party stash). Returns the entry it ended in."""
    e = find(store, entry_id)
    if e is None or holder == e["holder"]:
        return e
    got = take(store, entry_id, qty)
    got = dict(got, id=uuid.uuid4().hex[:10], holder=holder)
    _log(store, "moved", got["name"], got["qty"], e["holder"], 0, holder)
    return add(store, got)


def credit_stash(store, cp, note=""):
    store["coins_cp"] = int(store.get("coins_cp", 0)) + int(cp)
    _log(store, "coins", "Party stash coins", 0, STASH, cp, STASH, note)
    return store["coins_cp"]


def holders(store, party_names=()):
    """The party stash, the party, then anyone else still holding something (a PC who has left the party)."""
    out = [STASH] + sorted(party_names)
    for e in store["items"]:
        if e["holder"] not in out:
            out.append(e["holder"])
    return out


def total_value_gp(store, holder=None):
    return round(sum(e["value_gp"] * e["qty"] for e in store["items"] if holder is None or e["holder"] == holder), 2)


# ------------------------------------------------------------------------------------------------ Pathbuilder gear
def _base_name(name):
    """'Longsword (+1, striking)' -> 'Longsword'."""
    return re.sub(r"\s*\(.*\)\s*$", "", str(name)).strip()


def _data():
    try:
        from . import itemdata as D
    except ImportError:
        import itemdata as D
    return D


def _striking_tier(label):
    low = str(label).lower()
    if "major striking" in low:
        return 3
    if "greater striking" in low:
        return 2
    return 1 if "striking" in low else 0


def rune_value(kind, pot=0, striking=0, res="", runes=(), material="", price_of=None):
    """(gp, [unpriced names]) for the runes (and special material) on a weapon or armor. Fundamental runes come from the rune
    tables in itemdata.py; property runes from those tables, else your rules data by name (price_of)."""
    D = _data()
    gp, unknown = 0.0, []
    pot = int(pot or 0)
    if kind == "weapon":
        if pot in D.WEAPON_POTENCY:
            gp += D.WEAPON_POTENCY[pot][2]
        if int(striking or 0) in D.STRIKING:
            gp += D.STRIKING[int(striking)][2]
        table = D.WEAPON_RUNES
    else:
        if pot in D.ARMOR_POTENCY:
            gp += D.ARMOR_POTENCY[pot][2]
        tier = {"resilient": 1, "greater resilient": 2, "major resilient": 3,
                "greaterresilient": 2, "majorresilient": 3}.get(str(res or "").strip().lower(), 0)
        if tier:
            gp += D.RESILIENT[tier][2]
        table = D.ARMOR_RUNES
    by = {r["name"].lower(): r["price"] for r in table}
    for r in runes or ():
        name = str(r).strip()
        low = name.lower()
        if low in by:
            gp += by[low]
            continue
        found = None
        if price_of:
            for cand in (name, f"{name} rune", f"{name} (rune)"):
                found = price_of(cand)
                if found is not None:
                    break
        if found is None:
            unknown.append(name)
        else:
            gp += found
    if material:
        unknown.append(f"{material} (material)")
    return gp, unknown


def pb_items(pc):
    """A PC's gear as Pathbuilder exported it: [(label, qty, kind, base name, rune info)]. kind is equipment, armor, or
    weapon; rune info is a dict for rune_value(), or None."""
    out = []
    for e in pc.get("equipment") or []:
        if e.get("name"):
            label = e["name"] + (f" (in {e['container']})" if e.get("container") else "") + (" (invested)" if e.get("invested") else "")
            out.append((label, int(e.get("qty") or 1), "equipment", e["name"], None))
    for a in pc.get("armor") or []:
        if a.get("name"):
            label = a["name"] + (" (worn)" if a.get("worn") else "")
            runes = {"kind": "armor", "pot": a.get("pot") or 0, "res": a.get("res") or "", "runes": list(a.get("runes") or [])}
            out.append((label, int(a.get("qty") or 1), "armor", a.get("base") or a["name"], runes))
    seen = set()
    for w in pc.get("strikes") or []:
        if not isinstance(w, dict) or w.get("unarmed") or w.get("bomb") or w.get("manual"):
            continue
        base = w.get("weapon") or w.get("name")
        if not base or "bomb" in str(base).lower() or w["name"] in seen:
            continue
        seen.add(w["name"])
        runes = {"kind": "weapon", "pot": w.get("pot") or 0, "striking": w.get("striking", _striking_tier(w["name"])),
                 "runes": list(w.get("runes") or []), "material": w.get("mat") or ""}
        out.append((w["name"], 1, "weapon", base, runes))
    return out


def _removed_for(store, pc_name, name):
    return [r for r in store.get("pb_removed", []) if r["pc"] == pc_name and r["name"].lower() == name.lower()]


def pb_rows(pc, store, price_of=None):
    """Rows for a PC's Pathbuilder gear, less what you have sold or used here. price_of(name) -> gp or None.

    A removal remembers how many Pathbuilder listed at the time. Once the player takes the item out in Pathbuilder and you
    refresh, Pathbuilder lists fewer, and that many removals are dropped, so nothing is hidden twice."""
    rows = []
    for label, qty, kind, base, rinfo in pb_items(pc):
        hidden = 0
        for r in _removed_for(store, pc["name"], label):
            gone_in_pb = max(0, int(r["pb_qty"]) - qty)
            hidden += max(0, int(r["qty"]) - gone_in_pb)
        left = qty - hidden
        if left <= 0:
            continue
        price = price_of(_base_name(base)) if price_of else None
        rune_gp, unpriced = rune_value(price_of=price_of, **rinfo) if rinfo else (0.0, [])
        if price is None and rune_gp:
            unpriced = ["base item"] + unpriced
        rows.append({"id": f"pb|{pc['name']}|{label}", "name": label, "qty": left, "holder": pc["name"], "kind": kind,
                     "value_gp": round(float(price or 0) + rune_gp, 2), "base_gp": float(price or 0), "rune_gp": rune_gp,
                     "unpriced": unpriced, "priced": price is not None or bool(rune_gp), "source": "Pathbuilder",
                     "rules_name": _base_name(base), "pb": True, "pb_qty": qty})
    return rows


def pb_dispose(store, row, how, qty=1, amount_cp=0, payee="", note=""):
    """Sell or use up a Pathbuilder item here. It stays hidden until Pathbuilder lists fewer of it (see pb_rows)."""
    if how not in HOW:
        raise ValueError(f"Unknown way to remove an item: {how}")
    qty = max(1, min(int(qty), int(row["qty"])))
    store.setdefault("pb_removed", []).append({"pc": row["holder"], "name": row["name"], "qty": qty, "pb_qty": row["pb_qty"],
                                               "date": today()})
    _log(store, how, row["name"], qty, row["holder"], amount_cp, payee, "; ".join(x for x in (note.strip(), "Pathbuilder item") if x))
    return qty


def prune_pb(store, party):
    """Forget removals whose item Pathbuilder no longer lists at all (the player has updated the character)."""
    by = {pc["name"]: {it[0].lower(): it[1] for it in pb_items(pc)} for pc in party}
    keep = []
    for r in store.get("pb_removed", []):
        have = by.get(r["pc"], {}).get(r["name"].lower())
        if have is not None and have > int(r["pb_qty"]) - int(r["qty"]):
            keep.append(r)
    store["pb_removed"] = keep
    return store


# ------------------------------------------------------------------------------------------------ text
def entry_text(e):
    """One line for a copy or an export: '2 x Healing Potion (level 1, 3 gp each) - Party stash'."""
    bits = []
    if e.get("level") not in (None, ""):
        bits.append(f"level {e['level']}")
    if e.get("value_gp"):
        bits.append(f"{coin_text(to_cp(e['value_gp']))}{' each' if e['qty'] > 1 else ''}")
    return f"{e['qty']} x {e['name']}" + (f" ({', '.join(bits)})" if bits else "")


def inventory_text(store, party=(), price_of=None):
    """Everything the party owns, by holder, as plain text."""
    names = [pc["name"] for pc in party]
    lines = ["Party Loot", f"Party stash coins: {coin_text(store.get('coins_cp', 0))}", ""]
    for h in holders(store, names):
        own = [e for e in store["items"] if e["holder"] == h]
        pc = next((p for p in party if p["name"] == h), None)
        pbr = pb_rows(pc, store, price_of) if pc else []
        if not own and not pbr and h != STASH:
            continue
        lines.append(h)
        lines += [f"  {entry_text(e)}" for e in own]
        lines += [f"  {entry_text(r)} [Pathbuilder]" + (f" (not priced: {', '.join(r['unpriced'])})" if r.get("unpriced") else "")
                  for r in pbr]
        if pc and pc.get("money"):
            lines.append(f"  Coins (Pathbuilder): {coin_text(money_cp(pc['money']))}")
        if not own and not pbr:
            lines.append("  (nothing)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

"""Markdown export of encounters/sessions, and backup/restore of everything you've made."""
import datetime
import io
import json
import zipfile
from pathlib import Path

from .statblock import render_text

BACKUP_KEYS = ("config", "party", "creatures", "items", "ledger", "regions", "spells", "abilities", "sessions",
               "combat", "notebook", "story_tables", "magic_items", "downtime", "party_loot")


def statblock_md(d):
    """Plain stat block text as a fenced block (keeps line layout in any Markdown viewer)."""
    return "```\n" + render_text(d).rstrip() + "\n```"


def encounter_md(name, groups, details_for, xp=None, budget=None, threat="", notes="", treasure=()):
    """groups: [(Creature, count)]; details_for(creature) -> stat block dict or None."""
    out = [f"## {name}"]
    meta = []
    if threat:
        meta.append(threat)
    if xp is not None:
        meta.append(f"{xp}/{budget} XP" if budget else f"{xp} XP")
    if meta:
        out.append("*" + " | ".join(meta) + "*")
    out.append("")
    for c, n in groups:
        out.append(f"- {n} x {c.display_name} (level {c.level})")
    if notes:
        out += ["", "**Notes**", "", notes]
    if treasure:
        out += ["", "**Treasure**", ""]
        for t in treasure:
            out.append(f"- {t['name']} ({t['kind']}, {t.get('value_gp', 0):g} gp)")
    seen = set()
    for c, _ in groups:
        if c.uid in seen:
            continue
        seen.add(c.uid)
        d = details_for(c)
        if d:
            out += ["", f"### {d['name']}", "", statblock_md(d)]
    return "\n".join(out)


def session_md(sess, details_for):
    out = [f"# {sess['name']}", f"*Party level {sess.get('level', '?')} | {sess.get('date', '')}*", ""]
    if sess.get("notes"):
        out += [sess["notes"], ""]
    from .encounter import encounter_from_dict
    for e in sess.get("encounters", []):
        enc = encounter_from_dict(e)
        out.append(encounter_md(e["name"] + (" (done)" if e.get("status") == "done" else ""), enc.groups,
                                details_for, e.get("xp"), e.get("budget"), e.get("threat", ""),
                                e.get("notes", ""), e.get("treasure", [])))
        out.append("")
    return "\n".join(out)


def make_backup(storage, path):
    """Zip every user data file into one backup. Returns the list of included names."""
    included = []
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for key in BACKUP_KEYS:
            p = storage.FILES[key]
            if p.exists():
                z.write(p, p.name)
                included.append(p.name)
        z.writestr("backup_info.json", json.dumps({"created": datetime.datetime.now().isoformat(timespec="seconds"),
                                                   "files": included}))
    return included


def restore_backup(storage, path):
    """Restore files from a backup zip into user_data. Current files are kept as *.before-restore."""
    names = {storage.FILES[k].name: k for k in BACKUP_KEYS}
    restored = []
    with zipfile.ZipFile(path) as z:
        for member in z.namelist():
            key = names.get(Path(member).name)
            if not key:
                continue
            data = z.read(member)
            json.loads(data)                       # refuse anything that isn't valid JSON
            dest = storage.FILES[key]
            if dest.exists():
                dest.replace(dest.with_suffix(".before-restore"))
            dest.write_bytes(data)
            restored.append(dest.name)
    if not restored:
        raise RuntimeError("That file doesn't look like a PF2e GM Tool backup.")
    return restored

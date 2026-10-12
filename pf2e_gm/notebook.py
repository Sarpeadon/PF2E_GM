"""Campaign notebook: linked pages for NPCs, PCs, locations, factions, quests, and events.

Write [[Page Title]] (or [[Page Title|shown text]]) in a page body to link another page. A link whose
title isn't a page yet links to a matching creature or rules entry if there is one, otherwise it offers to
create the page. Conditions and dice in the text are clickable as everywhere else.
"""
import datetime
import re
import uuid

from . import reputation
from .statblock import _Out, link

PAGE_TYPES = ["NPC", "PC", "Location", "Faction", "Quest", "Rumor", "Complication", "Hook", "Event", "Item", "Note"]
STATUSES = {"NPC": ["alive", "dead", "missing", "ally", "enemy", "neutral"],
            "PC": ["active", "retired", "dead"],
            "Quest": ["rumored", "active", "complete", "failed", "abandoned"],
            "Faction": ["allied", "friendly", "neutral", "unfriendly", "hostile"],
            "Location": ["unexplored", "visited", "cleared"],
            "Rumor": ["unheard", "heard", "confirmed", "debunked", "resolved"],
            "Complication": ["pending", "used", "resolved", "ignored"],
            "Hook": ["open", "accepted", "complete", "failed", "dropped"],
            "Event": ["upcoming", "happened"]}
STORY_TYPES = ("Rumor", "Complication", "Hook")
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def new_page(title, ptype="Note", body="", **extra):
    p = {"id": uuid.uuid4().hex[:10], "title": title.strip() or "Untitled", "type": ptype, "status": "",
         "tags": [], "body": body, "created": datetime.date.today().isoformat()}
    p.update(extra)
    return p


def find(pages, title):
    t = (title or "").strip().lower()
    return next((p for p in pages if p["title"].strip().lower() == t), None)


def links_in(page):
    return [m.group(1).strip() for m in LINK.finditer(page.get("body") or "")]


def backlinks(pages, page):
    t = page["title"].strip().lower()
    return [p for p in pages if p is not page and any(x.lower() == t for x in links_in(p))]


def rename(pages, page, new_title):
    """Rename a page and update [[links]] to it in every other page."""
    old = page["title"]
    page["title"] = new_title.strip() or old

    def fix(m):
        if m.group(1).strip().lower() == old.strip().lower():
            return f"[[{page['title']}{'|' + m.group(2) if m.group(2) else ''}]]"
        return m.group(0)
    for p in pages:
        p["body"] = LINK.sub(fix, p.get("body") or "")


def _resolve_link(title, pages, creature_names, rules):
    p = find(pages, title)
    if p:
        return f"page:{p['id']}"
    if title.strip().lower() in creature_names:
        return f"creature:{title.strip()}"
    if rules is not None:
        for kind in ("name", "item", "spell"):
            ref = f"{kind}:{title.strip()}"
            if rules.resolve(ref):
                return ref
    return f"newpage:{title.strip()}"


def body_segments(page, pages, creature_names=(), rules=None, who=""):
    """Page body as clickable segments ([[links]], conditions, dice)."""
    names = {n.lower() for n in creature_names}

    def sub(m):
        title, shown = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
        return link(shown, _resolve_link(title, pages, names, rules))
    o = _Out(who)
    o.rich(LINK.sub(sub, page.get("body") or ""))
    return o.segs


def faction_segments(page):
    """Reputation summary for a faction page: standing, what it means, your notes, goals, rivals, recent log."""
    rp = reputation.ensure(page.get("rep"))
    pts = rp["points"]
    t = reputation.tier(pts)
    segs = [("Standing with the party ", "label", None), (f"{t} ({pts:+d})\n" if pts else f"{t} (0)\n", "body", None),
            (reputation.DESCRIPTION[t] + "\n", "muted", None),
            (reputation.rule_text(t) + "\n", "muted", None)]
    note = reputation.tier_note(rp)
    if note:
        segs += [(f"At {t}: ", "label", None), (note + "\n", "body", None)]
    if page.get("goals"):
        segs += [("Goals ", "label", None), ("; ".join(page["goals"]) + "\n", "body", None)]
    if page.get("rivals"):
        segs += [("Rivals ", "label", None), (", ".join(page["rivals"]) + "\n", "body", None)]
    if rp["log"]:
        segs.append(("Recent changes\n", "label", None))
        for e in rp["log"][-5:][::-1]:
            what = (f"{e.get('size', '')} {e.get('kind', '')}".strip() if e.get("kind") != "set" else "set by hand")
            tail = "no effect at this standing" if e.get("blocked") else f"{e.get('delta', 0):+d}"
            segs.append((f"  {e.get('date', '')}  {what}: {tail}, now {e.get('tier', '')} ({e.get('after', 0):+d})"
                         + (f"  {e['note']}" if e.get("note") else "") + "\n", "muted", None))
    return segs


def render_page(page, pages, creature_names=(), rules=None, statblock=None):
    """[(text, style, ref)] for a page: header, body, optional stat block segments, and backlinks."""
    segs = [(page["title"], "title", None),
            (f"    {page.get('type', 'Note')}" + (f" | {page['status']}" if page.get("status") else "") + "\n",
             "head", None)]
    if page.get("tags"):
        segs.append(("  ".join(t.upper() for t in page["tags"]) + "\n", "trait", None))
    for label, key in (("Ancestry", "ancestry"), ("Role", "role"), ("Class", "class"), ("Player", "player"),
                       ("Kind", "kind"), ("Canon", "canon"), ("Source", "source"), ("Pathbuilder ID", "pathbuilder_id")):
        if page.get(key):
            segs += [(f"{label} ", "label", None), (f"{page[key]}\n", "body", None)]
    if page.get("type") == "Faction":
        segs += faction_segments(page)
    segs.append(("\n", "body", None))
    segs += body_segments(page, pages, creature_names, rules, page["title"])
    segs.append(("\n", "body", None))
    if statblock:
        segs.append(("─" * 60 + "\n", "rule", None))
        segs += statblock
    bl = backlinks(pages, page)
    if bl:
        segs.append(("─" * 60 + "\n", "rule", None))
        segs.append(("Linked from: ", "label", None))
        for i, p in enumerate(bl):
            if i:
                segs.append((", ", "body", None))
            segs.append((p["title"], "body", f"page:{p['id']}"))
        segs.append(("\n", "body", None))
    return segs


def unique_title(pages, title):
    t, n = title, 2
    while find(pages, t):
        t, n = f"{title} ({n})", n + 1
    return t


def faction_pages(pages):
    return [p for p in pages if p.get("type") == "Faction"]


def new_faction(title, kind="", points=0, **extra):
    """A faction page with a reputation record (the party's standing starts at Ignored unless told otherwise)."""
    p = new_page(title, "Faction", extra.pop("body", ""), status=extra.pop("status", "neutral"), kind=kind,
                 rep=reputation.new_rep(points), goals=extra.pop("goals", []), rivals=extra.pop("rivals", []), **extra)
    return p


def ensure_rep(page):
    page["rep"] = reputation.ensure(page.get("rep"))
    return page["rep"]


def story_to_pages(story, pages, page_type=None, create_entities=True, existing_id=None):
    """Turn a generated story into notebook pages.

    Returns (page, new_pages). `page` is the story page (a new dict, or the existing page updated when
    existing_id is given); `new_pages` are stub pages for the people and factions the story invented. Nothing in
    `pages` is changed (apart from renaming links when an existing page's title changes); the caller appends. Campaign people and factions are [[linked]] by name; invented ones
    are linked only when their pages are created, so no link is ever dead.
    """
    new_pages, reuse = [], {}
    if create_entities:
        for e in story.entities:
            if e.get("campaign") or e.get("type") not in ("NPC", "Faction") or not e.get("title"):
                continue
            title = e["title"]
            if find(pages, title) or find(new_pages, title):
                reuse[title] = True                       # already a page by that name: just link to it
                continue
            if e["type"] == "Faction":
                pg = new_faction(title, kind=e.get("kind", ""), body=f"First appeared in: {story.title}")
            else:
                pg = new_page(title, "NPC", f"First appeared in: {story.title}", status="alive",
                              ancestry=e.get("ancestry", ""), role=str(e.get("role", "")).capitalize())
            new_pages.append(pg)
    data = story.to_page(link_generated=create_entities)
    # to_page links generated names whether or not they exist as pages; undo those that have no page
    if create_entities:
        have = {p["title"] for p in new_pages} | {p["title"] for p in pages}
        for e in story.entities:
            t = e.get("title")
            if t and not e.get("campaign") and t not in have:
                data["body"] = re.sub(r"\[\[" + re.escape(t) + r"(?:\|([^\]]+))?\]\]",
                                      lambda m: m.group(1) or t, data["body"])
    if page_type:
        data["type"] = page_type
    if existing_id:
        page = next((p for p in pages if p["id"] == existing_id), None)
        if page is not None:
            new_title = data["title"]
            if new_title != page["title"] and not find([p for p in pages if p is not page], new_title):
                rename(pages, page, new_title)               # also fixes [[links]] to it in other pages
            page.update(type=data["type"], tags=data["tags"], body=data["body"], story=data["story"])
            return page, new_pages
    page = new_page(unique_title(pages + new_pages, data["title"]), data["type"], data["body"], status=data["status"],
                    tags=data["tags"], story=data["story"])
    return page, new_pages

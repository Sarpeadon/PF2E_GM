"""Tkinter GUI for the PF2e GM Tool."""
import copy
import datetime
import json
import random
import re
import threading
import tkinter as tk
import urllib.parse
import uuid
import webbrowser
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import data, dice, storage, updater
from . import export as exporter
from . import pathbuilder as pb
from . import resources as rs
from .combat import DEGREES, HIT
from .partywarn import creature_warnings, encounter_warnings
from .shop import (MAX_COUNT as SHOP_MAX, SHOP_TYPES, SIZES as SHOP_SIZES, THEME_TAGS as SHOP_TAGS, add_more as shop_add_more,
                   build_shop, make_shop_name, remove_lines as shop_remove_lines, reroll_line as shop_reroll_line, shop_text,
                   theme_report, theme_report_text)
from .adjust import apply_adjustment
from .combat import (ALL_CONDITIONS, BONUS_PRESETS, BONUS_TARGETS, BONUS_TYPES, PERSISTENT, RIDER_APPLIES, VALUED,
                     CombatState, parse_iwr, sneak_attack_dice)
from .encounter import (COHESION, HAZARD_MODES, encounter_from_dict, encounter_to_dict, filter_pool, generate,
                        make_variant, recompute)
from .library import (AREA_TYPES, CAST_OPTIONS, DEFENSES, SPELL_KINDS, TRADITIONS, ability_entry, ability_to_line,
                      custom_rule_entries, find as lib_find, spell_entry)
from .quickref import ADJUSTMENTS, RARITY_ADJ, dc_for, reference_segments, spell_rank_dc
from . import session as sess
from . import downtime as dt
from . import tavern
from . import hallowmead
from . import itemdata
from . import itemgen
from . import gmtools
from . import names as nmod
from . import notebook as nbk
from . import npcgen
from . import npckit
from . import partyloot as ploot
from . import spellgen
from . import templates as tpl
from . import reputation
from . import storygen as sg
from .groups import THEMES, Affinity, general_sources, matches_spec, related
from .vocab import SIZE_CODE, SIZE_LABEL, build_vocab, cached_vocab, strip_count
from .tabs import TabbedPane
from .tpldialog import TemplateDialog
from .widgets import ANY, Combo, MultiField, ToolPanel
from .gmtables import HP_TIERS, SPELL_TIERS, TIERS4, TIERS5, suggest
from .loot import filter_items, generate_level, ledger_summary, pick
from .models import SYSTEM_MODES, SYSTEM_NAMES, Creature, Item, price_text, system_of
from .rules import DEFAULT_PARTY_SIZE, RARITIES, THREATS, TREASURE, creature_xp, xp_of
from .statblock import (DetailsDB, build_details, custom_details, custom_item_entry, details_to_custom, norm, render, render_entry,
                        render_text, strip_links)

SPELL_TRAITS = ["attack", "auditory", "cantrip", "concentrate", "manipulate", "acid", "air", "cold", "darkness",
                "death", "earth", "electricity", "emotion", "fear", "fire", "force", "fortune", "healing", "illusion",
                "incapacitation", "light", "linguistic", "mental", "misfortune", "poison", "polymorph", "scrying",
                "sleep", "sonic", "spirit", "summon", "teleportation", "visual", "vitality", "void", "water"]
ABILITY_TRAITS = ["arcane", "aura", "auditory", "concentrate", "divine", "emotion", "fear", "incapacitation",
                  "manipulate", "mental", "move", "occult", "olfactory", "poison", "primal", "visual", "fire",
                  "cold", "electricity", "acid", "sonic", "disease", "curse", "attack"]
AON_SEARCH = "https://2e.aonprd.com/Search.aspx?q={q}"


def _split(s):
    return [t.strip() for t in s.split(",") if t.strip()]


class RarityChecks(ttk.Frame):
    def __init__(self, master, default=("common", "uncommon")):
        super().__init__(master)
        self.vars = {}
        for r in RARITIES:
            v = tk.BooleanVar(value=r in default)
            ttk.Checkbutton(self, text=r.title(), variable=v).pack(side="left")
            self.vars[r] = v

    def get(self):
        return {r for r, v in self.vars.items() if v.get()}


class RichText(ttk.Frame):
    """Read-only, word-wrapped text with clickable rules links."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.text = tk.Text(self, wrap="word", padx=10, pady=8, relief="flat", cursor="arrow")
        sb = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        t = self.text
        t.tag_configure("title", font=("TkDefaultFont", 14, "bold"))
        t.tag_configure("head", font=("TkDefaultFont", 11, "bold"))
        t.tag_configure("trait", font=("TkDefaultFont", 8, "bold"), foreground="#5b1e1e", spacing1=4, spacing3=4)
        t.tag_configure("label", font=("TkDefaultFont", 10, "bold"))
        t.tag_configure("body", font=("TkDefaultFont", 10), lmargin2=12)
        t.tag_configure("abil", font=("TkDefaultFont", 10, "bold"), spacing1=12)                       # an ability's name line
        t.tag_configure("para", font=("TkDefaultFont", 10), spacing1=3)                                # a paragraph of rules text
        t.tag_configure("ind", font=("TkDefaultFont", 10), lmargin1=22, lmargin2=22)                   # a degree of success
        t.tag_configure("indlabel", font=("TkDefaultFont", 10, "bold"), lmargin1=22, lmargin2=22)
        t.tag_configure("rule", foreground="#999")
        t.tag_configure("mono", font=("TkFixedFont", 10), lmargin1=8, lmargin2=8)
        t.tag_configure("muted", font=("TkDefaultFont", 10), foreground="#666")
        t.tag_configure("warn", font=("TkDefaultFont", 9, "italic"), foreground="#9a5b00")
        t.tag_configure("flavor", font=("TkDefaultFont", 10, "italic"), foreground="#555")                # a spell's flavor text
        t.tag_configure("link", foreground="#1a5fb4", underline=True)
        t.tag_configure("rolllink", foreground="#1e7a34", underline=True)
        for tag in ("link", "rolllink"):
            t.tag_bind(tag, "<Enter>", lambda e: t.configure(cursor="hand2"))
            t.tag_bind(tag, "<Leave>", lambda e: t.configure(cursor="arrow"))

    def show_message(self, msg):
        self.show([(msg, "muted", None)])

    def show(self, segments):
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        for tag in t.tag_names():
            if tag.startswith("lnk"):
                t.tag_delete(tag)
        for m in t.mark_names():
            if m.startswith("a:"):
                t.mark_unset(m)
        n = 0
        for text, style, ref in segments:
            if style == "anchor":
                t.mark_set("a:" + norm(ref), "end-1c"); t.mark_gravity("a:" + norm(ref), "left")
                continue
            if ref and (ref.startswith(("self:", "roll:", "page:", "creature:", "newpage:", "newspell:"))
                        or self.app.rules.resolve(ref)):
                n += 1
                tag = f"lnk{n}"
                t.insert("end", text, (style, "rolllink" if ref.startswith("roll:") else "link", tag))
                t.tag_bind(tag, "<Button-1>", lambda e, r=ref: self.app.open_ref(r, self))
            else:
                t.insert("end", text, style)
        t.configure(state="disabled")
        t.yview_moveto(0)

    def jump(self, name):
        mark = "a:" + norm(name)
        if mark in self.text.mark_names():
            self.text.see(mark)
            self.text.tag_remove("sel", "1.0", "end")
            self.text.tag_add("sel", mark, f"{mark} lineend")


class DiceWindow(tk.Toplevel):
    """Roll history (newest on top) with a per-modifier breakdown, plus a box for typing any roll."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Dice")
        self.geometry("600x560")
        self.transient(app)            # always stays in front of the main GM Tool window
        bar = ttk.Frame(self); bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Roll").pack(side="left")
        self.expr = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.expr, width=24); e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self._roll_typed())
        ttk.Button(bar, text="Roll", command=self._roll_typed).pack(side="left")
        for q in ("d20", "d4", "d6", "d8", "d10", "d12"):
            ttk.Button(bar, text=q, width=4, command=lambda q=q: self.app.do_roll_expression(q)).pack(side="left", padx=1)
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="right")
        self.text = tk.Text(self, wrap="word", state="disabled", padx=8, pady=6, font=("TkDefaultFont", 10))
        t = self.text
        t.tag_configure("title", font=("TkDefaultFont", 11, "bold"))
        t.tag_configure("big", font=("TkDefaultFont", 18, "bold"), foreground="#1e7a34")
        t.tag_configure("big2", font=("TkDefaultFont", 11, "bold"), foreground="#1e7a34", spacing1=4)
        t.tag_configure("mono", font=("TkFixedFont", 10))
        t.tag_configure("monob", font=("TkFixedFont", 10, "bold"))
        t.tag_configure("crit", font=("TkDefaultFont", 11, "bold"), foreground="#9a1e1e")
        t.tag_configure("crithead", font=("TkDefaultFont", 11, "bold"), foreground="#9a1e1e", spacing1=6)
        t.tag_configure("hit", font=("TkDefaultFont", 12, "bold"), foreground="#1a5fb4")
        t.tag_configure("muted", foreground="#666")
        t.tag_configure("sep", foreground="#bbb")
        t.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        e.focus_set()

    def _roll_typed(self):
        if self.expr.get().strip():
            self.app.do_roll_expression(self.expr.get())

    def add(self, res, note=None):
        """Show a roll result at the top. note: optional (text, tag) placed right under the total."""
        segs = list(res.get("styled") or [(res["lines"][0] + "\n", "title")])
        if note:
            at = 2 if len(segs) >= 2 else len(segs)
            segs.insert(at, note)
        segs.append(("─" * 50 + "\n", "sep"))
        t = self.text
        t.configure(state="normal")
        for text, tag in reversed(segs):
            t.insert("1.0", text, tag)
        t.configure(state="disabled")
        t.yview_moveto(0)
        self.bring_to_front()

    def bring_to_front(self):
        self.deiconify()
        self.lift()
        try:                            # briefly topmost so it surfaces even if another app had focus
            self.attributes("-topmost", True)
            self.after(300, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass

    def clear(self):
        self.text.configure(state="normal"); self.text.delete("1.0", "end"); self.text.configure(state="disabled")

    def add_note(self, text, tag="muted"):
        self.text.configure(state="normal")
        self.text.insert("1.0", text + "\n", tag)
        self.text.configure(state="disabled")


class ResourcesWindow(tk.Toplevel):
    """Resource tracker for one character: spend, restore, rest, refocus, and your own counters."""

    def __init__(self, app, get_pc):
        super().__init__(app)
        self.app, self.get_pc = app, get_pc
        self.transient(app)
        self.geometry("640x540")
        top = ttk.Frame(self); top.pack(fill="x", padx=6, pady=(6, 2))
        for text, cmd in (("Use 1", self.use), ("Restore 1", self.restore), ("Set Max...", self.set_max),
                          ("Add Counter...", self.add_counter), ("Remove Counter", self.remove_counter)):
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)
        rest = ttk.Frame(self); rest.pack(fill="x", padx=6, pady=2)
        for text, cmd in (("Daily Preparations (refill)", self.rest), ("Refocus (+1 Focus Point)", self.refocus),
                          ("New Session (Hero Points to 1)", self.new_session)):
            ttk.Button(rest, text=text, command=cmd).pack(side="left", padx=2)
        self.tree = ttk.Treeview(self, columns=("cur", "max", "note"), show="tree headings")
        self.tree.heading("#0", text="Resource"); self.tree.column("#0", width=270)
        for col, t, w in (("cur", "Left", 50), ("max", "Max", 50), ("note", "Notes", 230)):
            self.tree.heading(col, text=t); self.tree.column(col, width=w)
        self.tree.tag_configure("empty", foreground="#a33")
        self.tree.tag_configure("group", font=("TkDefaultFont", 10, "bold"))
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.tree.bind("<Double-1>", lambda e: self.use())
        self.info = tk.StringVar()
        ttk.Label(self, textvariable=self.info, foreground="#555", wraplength=600).pack(anchor="w", padx=8, pady=(0, 6))
        self.refresh()

    def _pc(self):
        pc = self.get_pc()
        if pc is None:
            self.destroy()
        return pc

    def refresh(self):
        pc = self._pc()
        if pc is None:
            return
        self.title(f"Resources: {pc['name']}")
        keep = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        rows = rs.build(pc)
        for group in rs.GROUPS:
            items = [r for r in rows if r["group"] == group]
            if not items:
                continue
            gid = "g:" + group
            self.tree.insert("", "end", iid=gid, text=group, open=True, tags=("group",))
            for r in items:
                self.tree.insert(gid, "end", iid=r["key"], text=r["label"], values=(r["cur"], r["max"], r["note"]),
                                 tags=("empty",) if r["cur"] == 0 else ())
        for k in keep:
            if self.tree.exists(k):
                self.tree.selection_set(k)
        self.info.set(rs.summary(pc) + ("   |   Double-click a row to use one." if rows else ""))

    def _key(self):
        sel = self.tree.selection()
        return sel[0] if sel and not sel[0].startswith("g:") else None

    def _do(self, fn, *args):
        pc = self._pc()
        if pc is None:
            return
        ok, msg = fn(pc, *args)
        if ok:
            self.app._res_done(pc, msg)
        self.refresh()
        self.info.set(msg)                     # after refresh, so a "none left" message isn't wiped

    def use(self):
        k = self._key()
        if k:
            self._do(rs.spend, k)

    def restore(self):
        k = self._key()
        if k:
            self._do(rs.restore, k)

    def set_max(self):
        k, pc = self._key(), self._pc()
        row = rs.find(pc, k) if (k and pc) else None
        if not row:
            return
        n = self.app._ask_int("Set maximum", f"Maximum for {row['label']}", row["max"], self)
        if n is not None:
            rs.set_max(pc, k, n)
            self.app._pc_state_changed(pc)
            self.refresh()

    def add_counter(self):
        pc = self._pc()
        if pc is None:
            return
        win = tk.Toplevel(self); win.title("Add counter"); win.transient(self)
        name, mx, refresh = tk.StringVar(), tk.StringVar(value="1"), tk.StringVar(value="daily")
        for r_, (lab, w) in enumerate((("Name", ttk.Entry(win, textvariable=name, width=26)),
                                       ("Uses", ttk.Entry(win, textvariable=mx, width=6)),
                                       ("Refills", ttk.Combobox(win, textvariable=refresh, state="readonly", width=12,
                                                                values=["daily", "manual"])))):
            ttk.Label(win, text=lab).grid(row=r_, column=0, sticky="w", padx=8, pady=3); w.grid(row=r_, column=1, padx=8, sticky="w")

        def ok():
            n = self.app._int_or_none(mx.get())
            if name.get().strip() and n:
                rs.add_custom(pc, name.get(), n, refresh.get())
                self.app._pc_state_changed(pc)
                self.refresh()
                win.destroy()
        ttk.Button(win, text="Add", command=ok).grid(row=3, column=1, sticky="e", padx=8, pady=8)

    def remove_counter(self):
        k, pc = self._key(), self._pc()
        if k and pc and k.startswith("custom:"):
            rs.remove_custom(pc, k)
            self.app._pc_state_changed(pc)
            self.refresh()

    def rest(self):
        pc = self._pc()
        if pc is None:
            return
        n = rs.daily_rest(pc)
        self.app._res_done(pc, f"daily preparations: {n} resource{'s' if n != 1 else ''} refilled")
        self.refresh()

    def refocus(self):
        self._do(lambda pc: rs.refocus(pc))

    def new_session(self):
        pc = self._pc()
        if pc is not None:
            rs.new_session(pc)
            self.app._res_done(pc, "new session: Hero Points reset to 1")
            self.refresh()


def infer_page_tags(page):
    """Theme tags for a Notebook page: the ones you gave it plus what its name, role, and notes suggest."""
    tags = [t.lower() for t in page.get("tags", [])]
    return sorted(set(tags) | set(sg.infer_tags(page.get("title", ""), " ".join(tags), page.get("kind", ""),
                                                page.get("role", ""), (page.get("body") or "")[:400])))


TIER_COLORS = {"Hunted": "#b3262b", "Hated": "#d9602b", "Disliked": "#d99a2b", "Ignored": "#a8a8a8",
               "Liked": "#9bbf45", "Admired": "#53a33a", "Revered": "#1f7a3a"}


class ReputationBar(tk.Canvas):
    """The -50 to 50 reputation scale: seven colored tiers, a marker for the party's standing."""
    W, H = 660, 58

    def __init__(self, master):
        super().__init__(master, width=self.W, height=self.H, highlightthickness=0)
        self.points = 0
        self.draw()

    def _x(self, points):
        return int((points - reputation.MIN_POINTS) / (reputation.MAX_POINTS - reputation.MIN_POINTS + 1) * self.W)

    def set(self, points):
        self.points = reputation.clamp(points)
        self.draw()

    def draw(self):
        self.delete("all")
        for name, lo, hi, _, _ in reversed(reputation.TIERS):
            x0, x1 = self._x(lo), self._x(hi + 1)
            self.create_rectangle(x0, 16, x1, 38, fill=TIER_COLORS[name], outline="white")
            self.create_text((x0 + x1) // 2, 48, text=name, font=("TkDefaultFont", 8))
        x = self._x(self.points) + max(1, self._x(1) - self._x(0)) // 2
        self.create_polygon(x - 6, 2, x + 6, 2, x, 14, fill="#222222", outline="")
        self.create_line(x, 14, x, 40, fill="#222222", width=2)


class StoryTablesWindow(tk.Toplevel):
    """Edit the tables and story types Story Forge draws from. Every change is saved as you go to your own file;
    the built-in content is never touched, and any built-in entry can be reset."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.reg = app.story_registry
        self.title("Story tables")
        self.geometry("1180x720")
        self.transient(app)
        self.cur_table = None
        self.cur_entry = None
        nb = TabbedPane(self, level=2)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        tbl = ttk.Frame(nb); nb.add(tbl, text="Tables")
        rec = ttk.Frame(nb); nb.add(rec, text="Story types")
        self._build_tables(tbl)
        self._build_types(rec)
        self.status = tk.StringVar(value="Your changes save automatically. Built-in tables are never overwritten.")
        ttk.Label(self, textvariable=self.status, foreground="#555").pack(anchor="w", padx=10, pady=(0, 6))
        self._load_tables()

    # ------------------------------------------------------------------ tables
    def _build_tables(self, f):
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.tq = tk.StringVar()
        ttk.Entry(left, textvariable=self.tq).pack(fill="x", padx=2, pady=2)
        self.tq.trace_add("write", lambda *a: self._load_tables())
        self.ttree = ttk.Treeview(left, columns=("n",), show="tree headings", height=24)
        self.ttree.heading("#0", text="Table"); self.ttree.column("#0", width=230)
        self.ttree.heading("n", text="On / total"); self.ttree.column("n", width=70)
        self.ttree.tag_configure("mine", foreground="#1a5fb4")
        self.ttree.pack(fill="both", expand=True)
        self.ttree.bind("<<TreeviewSelect>>", lambda e: self._pick_table())
        bb = ttk.Frame(left); bb.pack(fill="x", pady=3)
        ttk.Button(bb, text="New Table...", command=self._new_table).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete Table", command=self._del_table).pack(side="left", padx=2)

        right = ttk.Frame(pane); pane.add(right, weight=4)
        self.thead = tk.StringVar(value="Pick a table on the left.")
        ttk.Label(right, textvariable=self.thead, font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        cols = ("tags", "w", "state")
        self.etree = ttk.Treeview(right, columns=cols, show="tree headings", height=11)
        self.etree.heading("#0", text="Entry"); self.etree.column("#0", width=520)
        for c, t, w in (("tags", "Tags and flags", 190), ("w", "Weight", 55), ("state", "State", 80)):
            self.etree.heading(c, text=t); self.etree.column(c, width=w)
        self.etree.tag_configure("off", foreground="#aaa")
        self.etree.tag_configure("mine", foreground="#1a5fb4")
        self.etree.tag_configure("edited", foreground="#9a5b00")
        self.etree.pack(fill="both", expand=True)
        self.etree.bind("<<TreeviewSelect>>", lambda e: self._pick_entry())
        bar = ttk.Frame(right); bar.pack(fill="x", pady=3)
        for text, cmd in (("Test Roll (8)", self._test_roll), ("Turn On / Off", self._toggle), ("Delete Mine", self._delete),
                          ("Reset to Built-in", self._reset), ("Check All Tables", self._validate),
                          ("Export My Edits...", self._export), ("Import Edits...", self._import)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=2)
        form = ttk.LabelFrame(right, text="Entry")
        form.pack(fill="x", pady=4)
        self.e_text = tk.Text(form, height=3, wrap="word"); self.e_text.pack(fill="x", padx=4, pady=3)
        grid = ttk.Frame(form); grid.pack(fill="x", padx=4)
        self.e_flags, self.e_weight, self.e_needs, self.e_not = (tk.StringVar() for _ in range(4))
        for r, (lab, var, w) in enumerate((("Tags and flags", self.e_flags, 46), ("Weight", self.e_weight, 8),
                                           ("Needs (all of)", self.e_needs, 30), ("Not (none of)", self.e_not, 30))):
            ttk.Label(grid, text=lab).grid(row=r // 2, column=(r % 2) * 2, sticky="w", padx=(0 if r % 2 == 0 else 14, 4), pady=2)
            ttk.Entry(grid, textvariable=var, width=w).grid(row=r // 2, column=(r % 2) * 2 + 1, sticky="w")
        ttk.Label(form, foreground="#666", wraplength=820, justify="left", text=(
            "Tags: themes (crime, undead, ruin...), environments (urban, wild, underground, road, water), k:npc / k:faction / "
            "k:group / k:creature for the kind of subject, pl for plural subjects, p:underground to limit to a content pack, "
            "t:grim to limit to a tone, L3-8 for a party level range. Needs lists tags that must already be in the story "
            "(a/b means either); Not lists tags that must be absent. In text: {table}, {a table}, {pl table}, {^table} "
            "capitalize, {@who} reuse a slot, {has} {is} {was} agree with the subject, {dc} {dc:hard} {gp:medium} {lvl} scale "
            "to party level, {#2-6} a number, {table?40} 40% of the time.")).pack(anchor="w", padx=4, pady=2)
        fb = ttk.Frame(form); fb.pack(fill="x", padx=4, pady=3)
        ttk.Button(fb, text="Save Changes to This Entry", command=self._save_entry).pack(side="left")
        ttk.Button(fb, text="Add as New Entry", command=self._add_entry).pack(side="left", padx=6)
        self.out = tk.Text(right, height=7, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        self.out.pack(fill="x", pady=(2, 0))

    def _say(self, text):
        self.out.configure(state="normal"); self.out.delete("1.0", "end"); self.out.insert("end", text)
        self.out.configure(state="disabled")

    def _changed(self, msg="Saved."):
        try:
            sg.save_user_tables(self.reg)
            self.status.set(msg)
        except Exception as e:
            self.status.set(f"Couldn't save: {e}")
        self.app._story_refresh_kinds()

    @staticmethod
    def _flags(e):
        bits = list(e.get("tags", []))
        if e.get("pack") and e["pack"] != "core":
            bits.append("p:" + e["pack"])
        bits += ["t:" + t for t in e.get("tone", [])]
        if e.get("lvl"):
            bits.append(f"L{e['lvl'][0]}-{e['lvl'][1]}")
        return " ".join(bits)

    def _load_tables(self):
        q = self.tq.get().strip().lower()
        sel = self.cur_table
        self.ttree.delete(*self.ttree.get_children())
        for name in self.reg.names():
            title = self.reg.title(name)
            if q and q not in name.lower() and q not in title.lower():
                continue
            ents = self.reg.entries(name)
            on = sum(1 for e in ents if not e.get("off"))
            edited = any(e.get("edited") or e.get("user") or e.get("off") for e in ents)
            self.ttree.insert("", "end", iid=name, text=f"{name}  {title if title != name else ''}".strip(),
                              values=(f"{on}/{len(ents)}",), tags=("mine",) if edited or self.reg.is_user_table(name) else ())
        if sel and self.ttree.exists(sel):
            self.ttree.selection_set(sel)

    def _pick_table(self):
        sel = self.ttree.selection()
        if not sel:
            return
        self.cur_table = sel[0]
        self.cur_entry = None
        self.thead.set(f"{self.cur_table}: {self.reg.title(self.cur_table)}")
        self._load_entries()

    def _load_entries(self):
        self.etree.delete(*self.etree.get_children())
        for e in self.reg.entries(self.cur_table):
            state = "off" if e.get("off") else "edited" if e.get("edited") else "mine" if e.get("user") else "on"
            tags = ("off",) if e.get("off") else ("mine",) if e.get("user") else ("edited",) if e.get("edited") else ()
            self.etree.insert("", "end", iid=e["id"], text=e["t"], values=(self._flags(e), f"{e['w']:g}", state), tags=tags)

    def _pick_entry(self):
        sel = self.etree.selection()
        if not sel or not self.cur_table:
            return
        e = next((x for x in self.reg.entries(self.cur_table) if x["id"] == sel[0]), None)
        if not e:
            return
        self.cur_entry = e
        self.e_text.delete("1.0", "end"); self.e_text.insert("1.0", e["t"])
        self.e_flags.set(self._flags(e)); self.e_weight.set(f"{e['w']:g}")
        self.e_needs.set(" ".join(e["needs"])); self.e_not.set(" ".join(e["not"]))

    def _form_entry(self):
        text = self.e_text.get("1.0", "end").strip()
        if not text:
            self._say("Type the entry's text first.")
            return None
        spec = sg.parse_entry(text + "|" + self.e_flags.get().strip().replace("|", " "))
        try:
            weight = float(self.e_weight.get() or 1)
        except ValueError:
            self._say("Weight must be a number.")
            return None
        return {"t": text, "tags": spec["tags"], "pack": spec["pack"], "tone": spec["tone"], "lvl": spec["lvl"],
                "w": weight, "needs": self.e_needs.get().split(), "not": self.e_not.get().split()}

    def _check_text(self, text):
        problems = sg.check_template(text, set(self.reg.names()) | set(sg.PROVIDERS))
        return problems

    def _save_entry(self):
        if not (self.cur_table and self.cur_entry):
            self._say("Select an entry to change, or use Add as New Entry.")
            return
        f = self._form_entry()
        if not f:
            return
        bad = self._check_text(f["t"])
        self.reg.edit_entry(self.cur_table, self.cur_entry["id"], **f)
        self._load_entries(); self._load_tables()
        self._changed("Entry saved." + (" Warning: " + "; ".join(bad) if bad else ""))
        if bad:
            self._say("Saved, but check this: " + "; ".join(bad))

    def _add_entry(self):
        if not self.cur_table:
            self._say("Pick a table first.")
            return
        f = self._form_entry()
        if not f:
            return
        bad = self._check_text(f["t"])
        self.reg.add_entry(self.cur_table, f)
        self._load_entries(); self._load_tables()
        self._changed("Entry added." + (" Warning: " + "; ".join(bad) if bad else ""))
        if bad:
            self._say("Added, but check this: " + "; ".join(bad))

    def _live_entry(self):
        """The selected entry as the registry has it now (the form may hold an older copy)."""
        if not (self.cur_table and self.cur_entry):
            return None
        return next((x for x in self.reg.entries(self.cur_table) if x["id"] == self.cur_entry["id"]), None)

    def _toggle(self):
        e = self._live_entry()
        if e is None:
            return
        turn_on = bool(e.get("off"))
        self.reg.set_enabled(self.cur_table, e["id"], turn_on)
        self._load_entries(); self._load_tables()
        if self.etree.exists(e["id"]):
            self.etree.selection_set(e["id"])
        self.cur_entry = self._live_entry()
        self._changed("Entry turned " + ("on." if turn_on else "off."))

    def _delete(self):
        if not (self.cur_table and self.cur_entry):
            return
        if not self.cur_entry.get("user"):
            self._say("Built-in entries can't be deleted. Turn them off instead.")
            return
        self.reg.remove_entry(self.cur_table, self.cur_entry["id"])
        self.cur_entry = None
        self._load_entries(); self._load_tables()
        self._changed("Entry deleted.")

    def _reset(self):
        if not (self.cur_table and self.cur_entry):
            return
        self.reg.reset_entry(self.cur_table, self.cur_entry["id"])
        self._load_entries(); self._load_tables()
        self._changed("Entry reset to the built-in version.")

    def _new_table(self):
        win = tk.Toplevel(self); win.title("New table"); win.transient(self)
        name, title = tk.StringVar(), tk.StringVar()
        for r, (lab, v, w) in enumerate((("Name (lowercase, dots ok)", name, 30), ("Title", title, 30))):
            ttk.Label(win, text=lab).grid(row=r, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(win, textvariable=v, width=w).grid(row=r, column=1, padx=8)
        msg = tk.StringVar(); ttk.Label(win, textvariable=msg, foreground="#a33").grid(row=2, column=0, columnspan=2)

        def ok():
            try:
                self.reg.new_table(name.get().strip(), title.get().strip())
            except ValueError as e:
                msg.set(str(e)); return
            win.destroy()
            self.cur_table = name.get().strip()
            self._load_tables()
            if self.ttree.exists(self.cur_table):
                self.ttree.selection_set(self.cur_table)
            self._changed(f"Table {self.cur_table} created. Reference it in other tables as {{{self.cur_table}}}.")
        ttk.Button(win, text="Create", command=ok).grid(row=3, column=1, sticky="e", padx=8, pady=8)

    def _del_table(self):
        if self.cur_table and self.reg.is_user_table(self.cur_table):
            if messagebox.askyesno("Delete table", f"Delete your table '{self.cur_table}'?", parent=self):
                self.reg.delete_table(self.cur_table)
                self.cur_table = None
                self.etree.delete(*self.etree.get_children())
                self._load_tables()
                self._changed("Table deleted.")
        else:
            self._say("Only tables you created can be deleted. Turn off entries in a built-in table instead.")

    def _test_roll(self):
        if not self.cur_table:
            return
        rng = random.Random()
        lines = []
        for _ in range(8):
            try:
                lines.append("- " + sg.roll_table(self.cur_table, rng, registry=self.reg))
            except Exception as e:
                lines.append(f"- error: {e}")
        self._say(f"8 rolls of {self.cur_table}:\n" + "\n".join(lines))

    def _validate(self):
        problems = self.reg.validate()
        if not problems:
            self._say("Every table and story type checks out: no unknown tables, unbalanced braces, or empty tables.")
        else:
            self._say(f"{len(problems)} problem(s):\n" + "\n".join(f"- {t} {i}: {m}" for t, i, m in problems[:25]))

    def _export(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="story_tables_export.json",
                                         filetypes=[("JSON", "*.json")], parent=self)
        if p:
            self.reg.save(p)
            self.status.set(f"Exported your edits to {p}.")

    def _import(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], parent=self)
        if not p:
            return
        if not messagebox.askyesno("Import", "Replace your current edits with this file? The built-in tables are not affected.",
                                   parent=self):
            return
        try:
            self.reg.load(p)
        except (OSError, ValueError) as e:
            messagebox.showerror("Import failed", str(e), parent=self); return
        self._changed("Edits imported.")
        self._load_tables()
        if self.cur_table and self.reg.has(self.cur_table):
            self._load_entries()

    # ------------------------------------------------------------------ story types
    def _build_types(self, f):
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.ktree = ttk.Treeview(left, show="tree", height=18); self.ktree.column("#0", width=220)
        self.ktree.pack(fill="both", expand=True)
        self.ktree.bind("<<TreeviewSelect>>", lambda e: self._pick_kind())
        bb = ttk.Frame(left); bb.pack(fill="x", pady=3)
        ttk.Button(bb, text="New Type...", command=self._new_kind).pack(side="left", padx=2)
        ttk.Button(bb, text="Reset to Built-in", command=self._reset_kind).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete", command=self._del_kind).pack(side="left", padx=2)
        right = ttk.Frame(pane); pane.add(right, weight=4)
        grid = ttk.Frame(right); grid.pack(fill="x", padx=4, pady=4)
        self.k_title, self.k_ptype, self.k_status, self.k_threat, self.k_tt = (tk.StringVar() for _ in range(5))
        for r, (lab, var, w) in enumerate((("Name shown", self.k_title, 24), ("Notebook page type", self.k_ptype, 16),
                                           ("Starting status", self.k_status, 16), ("Encounter threat (Low, Moderate...)", self.k_threat, 24),
                                           ("Title template", self.k_tt, 40))):
            ttk.Label(grid, text=lab).grid(row=r // 2, column=(r % 2) * 2, sticky="w", padx=(0 if r % 2 == 0 else 14, 4), pady=2)
            ttk.Entry(grid, textvariable=var, width=w).grid(row=r // 2, column=(r % 2) * 2 + 1, sticky="w")
        ttk.Label(right, text="Summary templates, one per line. Use {@who} {@what} {@where} {@when} {@why} and any other slot as "
                              "{@key}. One is picked at random each time.", foreground="#666").pack(anchor="w", padx=4)
        self.k_compose = tk.Text(right, height=5, wrap="word"); self.k_compose.pack(fill="x", padx=4, pady=2)
        ttk.Label(right, text="Slots (what the story is made of, in order). Extras follow the five main slots.",
                  foreground="#666").pack(anchor="w", padx=4, pady=(6, 0))
        self.stree = ttk.Treeview(right, columns=("label", "table", "chance", "kind"), show="tree headings", height=9)
        self.stree.heading("#0", text="Key"); self.stree.column("#0", width=110)
        for c, t, w in (("label", "Shown as", 150), ("table", "Draws from table", 200), ("chance", "Chance %", 70), ("kind", "Role", 70)):
            self.stree.heading(c, text=t); self.stree.column(c, width=w)
        self.stree.pack(fill="x", padx=4)
        self.stree.bind("<<TreeviewSelect>>", lambda e: self._pick_slot())
        sf = ttk.Frame(right); sf.pack(fill="x", padx=4, pady=4)
        self.s_key, self.s_label, self.s_table, self.s_chance = (tk.StringVar() for _ in range(4))
        self.s_extra = tk.BooleanVar()
        ttk.Label(sf, text="Key").grid(row=0, column=0); ttk.Entry(sf, textvariable=self.s_key, width=12).grid(row=0, column=1, padx=3)
        ttk.Label(sf, text="Shown as").grid(row=0, column=2); ttk.Entry(sf, textvariable=self.s_label, width=18).grid(row=0, column=3, padx=3)
        ttk.Label(sf, text="Table").grid(row=0, column=4)
        self.s_table_combo = ttk.Combobox(sf, textvariable=self.s_table, width=26); self.s_table_combo.grid(row=0, column=5, padx=3)
        ttk.Label(sf, text="Chance %").grid(row=0, column=6); ttk.Entry(sf, textvariable=self.s_chance, width=5).grid(row=0, column=7, padx=3)
        ttk.Checkbutton(sf, text="Extra", variable=self.s_extra).grid(row=0, column=8, padx=3)
        sb = ttk.Frame(right); sb.pack(fill="x", padx=4)
        for text, cmd in (("Apply Slot", self._apply_slot), ("Add Slot", self._add_slot), ("Remove Slot", self._remove_slot),
                          ("Move Up", lambda: self._move_slot(-1)), ("Move Down", lambda: self._move_slot(1))):
            ttk.Button(sb, text=text, command=cmd).pack(side="left", padx=2)
        ttk.Button(right, text="Save This Story Type", command=self._save_kind).pack(anchor="e", padx=4, pady=8)
        self.kind_slots = []
        self.cur_kind = None
        self._load_kinds()

    def _load_kinds(self):
        self.ktree.delete(*self.ktree.get_children())
        for k in self.reg.recipe_names():
            self.ktree.insert("", "end", iid=k, text=f"{self.reg.recipe(k).get('title', k)}   ({k})")
        self.s_table_combo["values"] = sorted(set(self.reg.names()) | set(sg.PROVIDERS))

    def _pick_kind(self):
        sel = self.ktree.selection()
        if not sel:
            return
        self.cur_kind = sel[0]
        r = self.reg.recipe(self.cur_kind)
        self.k_title.set(r.get("title", "")); self.k_ptype.set(r.get("page_type", "Note")); self.k_status.set(r.get("status", ""))
        th = r.get("threat")
        self.k_threat.set(", ".join(th) if isinstance(th, list) else (th or ""))
        self.k_tt.set(r.get("title_template", "{@what.short}"))
        self.k_compose.delete("1.0", "end"); self.k_compose.insert("1.0", "\n".join(r.get("compose", [])))
        self.kind_slots = [dict(d, extra=False) for d in r.get("slots", [])] + [dict(d, extra=True) for d in r.get("extras", [])]
        self._draw_slots()

    def _draw_slots(self, select=None):
        self.stree.delete(*self.stree.get_children())
        for i, d in enumerate(self.kind_slots):
            self.stree.insert("", "end", iid=str(i), text=d["key"],
                              values=(d.get("label", ""), d.get("table", ""), d.get("chance", ""), "extra" if d.get("extra") else "main"))
        if select is not None and self.stree.exists(str(select)):
            self.stree.selection_set(str(select))

    def _pick_slot(self):
        sel = self.stree.selection()
        if not sel:
            return
        d = self.kind_slots[int(sel[0])]
        self.s_key.set(d["key"]); self.s_label.set(d.get("label", "")); self.s_table.set(d.get("table", ""))
        self.s_chance.set(str(d.get("chance", ""))); self.s_extra.set(bool(d.get("extra")))

    def _slot_from_form(self):
        key = re.sub(r"[^a-z0-9_]", "", self.s_key.get().strip().lower())
        if not key or not self.s_table.get().strip():
            self._say("A slot needs a key (letters and numbers) and a table.")
            return None
        d = {"key": key, "label": self.s_label.get().strip() or key.title(), "table": self.s_table.get().strip(),
             "extra": self.s_extra.get()}
        ch = self.s_chance.get().strip()
        if ch.isdigit():
            d["chance"] = int(ch)
        return d

    def _apply_slot(self):
        sel = self.stree.selection()
        d = self._slot_from_form()
        if sel and d:
            self.kind_slots[int(sel[0])] = d
            self._draw_slots(sel[0])

    def _add_slot(self):
        d = self._slot_from_form()
        if d:
            self.kind_slots.append(d)
            self._draw_slots(len(self.kind_slots) - 1)

    def _remove_slot(self):
        sel = self.stree.selection()
        if sel:
            del self.kind_slots[int(sel[0])]
            self._draw_slots()

    def _move_slot(self, step):
        sel = self.stree.selection()
        if not sel:
            return
        i = int(sel[0]); j = i + step
        if 0 <= j < len(self.kind_slots):
            self.kind_slots[i], self.kind_slots[j] = self.kind_slots[j], self.kind_slots[i]
            self._draw_slots(j)

    def _save_kind(self):
        if not self.cur_kind:
            return
        mains = [{k: v for k, v in d.items() if k != "extra"} for d in self.kind_slots if not d.get("extra")]
        extras = [{k: v for k, v in d.items() if k != "extra"} for d in self.kind_slots if d.get("extra")]
        if {"who", "what", "where", "when", "why"} - {d["key"] for d in mains}:
            self._say("Keep the five main slots (who, what, where, when, why). Add your own as Extras.")
            return
        r = self.reg.recipe(self.cur_kind)
        r.update(title=self.k_title.get().strip() or self.cur_kind.title(), page_type=self.k_ptype.get().strip() or "Note",
                 status=self.k_status.get().strip(), title_template=self.k_tt.get().strip() or "{@what.short}",
                 slots=mains, extras=extras,
                 compose=[ln.strip() for ln in self.k_compose.get("1.0", "end").splitlines() if ln.strip()])
        th = [t.strip() for t in self.k_threat.get().split(",") if t.strip()]
        r["threat"] = (th if len(th) > 1 else th[0]) if th else None
        self.reg.set_recipe(self.cur_kind, r)
        bad = [m for t, i, m in self.reg.validate() if t == f"recipe:{self.cur_kind}"]
        self._load_kinds()
        self._changed("Story type saved." + (" Check: " + "; ".join(bad) if bad else ""))
        if bad:
            self._say("Saved, but check this: " + "; ".join(bad))

    def _new_kind(self):
        win = tk.Toplevel(self); win.title("New story type"); win.transient(self)
        key, title, base = tk.StringVar(), tk.StringVar(), tk.StringVar(value="rumor")
        for r, (lab, w) in enumerate((("Key (lowercase)", ttk.Entry(win, textvariable=key, width=20)),
                                      ("Name shown", ttk.Entry(win, textvariable=title, width=24)),
                                      ("Start from", ttk.Combobox(win, textvariable=base, values=self.reg.recipe_names(),
                                                                  state="readonly", width=18)))):
            ttk.Label(win, text=lab).grid(row=r, column=0, sticky="w", padx=8, pady=4); w.grid(row=r, column=1, padx=8)
        msg = tk.StringVar(); ttk.Label(win, textvariable=msg, foreground="#a33").grid(row=3, column=0, columnspan=2)

        def ok():
            k = re.sub(r"[^a-z0-9_]", "", key.get().strip().lower())
            if not k or k in self.reg.recipe_names():
                msg.set("Pick a new key using letters and numbers."); return
            r = self.reg.recipe(base.get() or "rumor")
            r["title"] = title.get().strip() or k.title()
            self.reg.set_recipe(k, r)
            win.destroy()
            self._load_kinds()
            self.ktree.selection_set(k)
            self._changed(f"Story type '{k}' created. It's now in the Story tab's type list.")
        ttk.Button(win, text="Create", command=ok).grid(row=4, column=1, sticky="e", padx=8, pady=8)

    def _reset_kind(self):
        if self.cur_kind:
            self.reg.reset_recipe(self.cur_kind)
            if self.cur_kind in self.reg.recipe_names():
                self._pick_kind()
            self._load_kinds()
            self._changed("Story type reset to the built-in version.")

    def _del_kind(self):
        if not self.cur_kind:
            return
        if self.cur_kind in self.reg.base_recipes:
            self._say("Built-in story types can't be deleted. Use Reset to Built-in to undo your changes.")
            return
        self.reg.reset_recipe(self.cur_kind)
        self.cur_kind = None
        self._load_kinds()
        self._changed("Story type deleted.")


class RulesWindow(tk.Toplevel):
    """Single reusable rules viewer with Back history."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Rules")
        self.geometry("580x620")
        bar = ttk.Frame(self); bar.pack(fill="x")
        self.back_btn = ttk.Button(bar, text="< Back", command=self.back, state="disabled")
        self.back_btn.pack(side="left", padx=2, pady=2)
        ttk.Button(bar, text="Search on Archives of Nethys", command=self._aon).pack(side="left", padx=2)
        self.view = RichText(self, app)
        self.view.pack(fill="both", expand=True)
        self.history = []

    def show(self, rowid, push=True):
        e = self.app.rules.rule(rowid)
        if not e:
            return
        if push:
            self.history.append(rowid)
        self.current = e
        self.title(f"Rules: {e['name']}")
        self.view.show(render_entry(e))
        self.back_btn.configure(state="normal" if len(self.history) > 1 else "disabled")
        self.deiconify(); self.lift()

    def back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.show(self.history[-1], push=False)

    def _aon(self):
        if getattr(self, "current", None):
            webbrowser.open(AON_SEARCH.format(q=urllib.parse.quote(self.current["name"])))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PF2e GM Tool")
        self.geometry("1300x780")
        try:                                   # titles of grouped boxes ("What do you need?") read as headings
            ttk.Style(self).configure("TLabelframe.Label", font=("TkDefaultFont", 10, "bold"), foreground="#2c5282")
        except Exception:
            pass
        self.config_data = storage.load("config")
        if self.config_data.get("defaults_version", 1) < 2:
            # One-time switch to the table's default party size (older versions saved 4 automatically).
            self.config_data["party_size"] = DEFAULT_PARTY_SIZE
            self.config_data["defaults_version"] = 2
            storage.save("config", self.config_data)
        self.cache_moved = storage.migrate_cache()
        self.party = storage.load("party")
        self.ledger = storage.load("ledger")
        self.party_loot = ploot.ensure(storage.load("party_loot"))
        self.f_creatures, self.f_items, self.index_src = data.load_index(storage.INDEX)
        self.c_creatures = storage.load_custom_creatures()
        self.c_items = storage.load_custom_items()
        self.details_db = DetailsDB(storage.DETAILS)
        self.rules = self.details_db
        self.rules_win = None
        self.dice_win = None
        self.last_damage = None
        self.combat_popouts = []
        self.res_wins = {}
        self.current_loot = []      # [(kind, Item or None, value)]
        self.enc_rows = {}          # tree iid -> (encounter index, group index)
        self.encs = []
        self.combat = CombatState.from_dict(storage.load("combat"))
        self.regions = storage.load("regions")
        self.lib_spells = storage.load("spells")
        self.lib_abilities = storage.load("abilities")
        self.sessions = storage.load("sessions")
        self.notebook = storage.load("notebook")
        self.my_templates = storage.load("templates")      # creature templates you made yourself
        self.story_registry = sg.default_registry()
        # recent=12: a table won't repeat what it gave out in roughly the last dozen stories while it has other choices
        self.story_gen = sg.Generator(self.story_registry, history=sg.History(strength=0.25, decay=0.85, recent=12),
                                      rng=random.Random())
        self._register_custom_rules()
        self.vocab = build_vocab(self.f_creatures, self.f_items, None)   # quick defaults; full list loads in background
        self.affinity = Affinity(general_sources(self.f_creatures))

        sysbar = ttk.Frame(self); sysbar.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Label(sysbar, text="Generate from:", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.sys_var = tk.StringVar(value=self.config_data.get("game_systems", "Pathfinder"))
        for name in SYSTEM_MODES:
            ttk.Radiobutton(sysbar, text=name, value=name, variable=self.sys_var,
                            command=self._systems_changed).pack(side="left", padx=6)
        self.sys_info = tk.StringVar()
        ttk.Label(sysbar, textvariable=self.sys_info, foreground="#777").pack(side="left", padx=10)
        ttk.Button(sysbar, text="Dice Roller", command=lambda: self._open_dice()).pack(side="right")
        self.last_roll = tk.StringVar(value="Green text in stat blocks rolls dice. Blue text opens rules.")
        ttk.Label(self, textvariable=self.last_roll, foreground="#1e7a34", anchor="w").pack(
            side="bottom", fill="x", padx=10, pady=(0, 4))

        self._refresh_spell_pool()
        nb = self.nb = TabbedPane(self, level=1)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        RUN, MAKE, CAMP, REF = "Run the game", "Make things", "Campaign", "Reference"
        self.tab_party = ttk.Frame(nb); nb.add(self.tab_party, text="Party & Data", group=RUN)
        self.tab_enc = ttk.Frame(nb); nb.add(self.tab_enc, text="Encounters", group=RUN)
        self.tab_combat = ttk.Frame(nb); nb.add(self.tab_combat, text="Combat", group=RUN)
        self.tab_loot = ttk.Frame(nb); nb.add(self.tab_loot, text="Treasure", group=RUN)
        self.tab_shop = ttk.Frame(nb); nb.add(self.tab_shop, text="Shops", group=RUN)
        self.tab_inn = ttk.Frame(nb); nb.add(self.tab_inn, text="Inns", group=RUN)
        self.tab_magic = ttk.Frame(nb); nb.add(self.tab_magic, text="Magic Items", group=MAKE)
        self.tab_custom = ttk.Frame(nb); nb.add(self.tab_custom, text="Custom Content", group=MAKE)
        self.tab_story = ttk.Frame(nb); nb.add(self.tab_story, text="Story", group=MAKE)
        self.tab_gm = ttk.Frame(nb); nb.add(self.tab_gm, text="GM Tools", group=MAKE)
        self.tab_notebook = ttk.Frame(nb); nb.add(self.tab_notebook, text="Notebook", group=CAMP)
        self.tab_factions = ttk.Frame(nb); nb.add(self.tab_factions, text="Factions", group=CAMP)
        self.tab_sessions = ttk.Frame(nb); nb.add(self.tab_sessions, text="Sessions", group=CAMP)
        self.tab_ref = ttk.Frame(nb); nb.add(self.tab_ref, text="Quick Ref", group=REF)
        nb.bind_keys(self)
        self._build_party()
        self._build_encounters()
        self._build_combat()
        self._build_loot()
        self._build_custom()
        self._build_sessions()
        self._build_quickref()
        self._build_shop()
        self._build_magic()
        self._build_inns()
        self._build_notebook()
        self._build_story()
        self._build_factions()
        self._build_gmtools()
        self.bind_all("<F1>", lambda e: self.nb.select(self.tab_ref))
        rebuilt = self._upgrade_stored_pcs()
        self._refresh_party()
        self._refresh_status()
        if rebuilt:
            self.status_var.set(f"Rebuilt {rebuilt} saved character{'s' if rebuilt != 1 else ''} with the newest importer.")
        self._refresh_ledger()
        self._refresh_regions()
        self._notebook_changed()
        self.after(900, self._offer_hallowmead)
        self._load_vocab_async()
        self._refresh_sys_info()
        if self.cache_moved:
            self.status_var.set("Moved downloaded rules data out of the app folder to "
                                f"{storage.CACHE_DIR} so OneDrive doesn't sync it.")

    # ---------- shared ----------
    def _register_custom_rules(self):
        self.details_db.set_custom_rules(custom_rule_entries(self.lib_spells, self.lib_abilities))

    def _refresh_spell_pool(self):
        """Grimoires fill their pages from the spells in your rules data and your custom spells."""
        try:
            data = self.details_db.spell_pool()
        except Exception:
            data = []
        spellgen.set_pool(data, self.lib_spells, tuple(sorted(self.systems())))

    @property
    def all_creatures(self):
        return self.f_creatures + self.c_creatures

    @property
    def all_items(self):
        return self.f_items + self.c_items

    def party_level(self):
        return int(self.pl_var.get())

    def systems(self):
        """Game systems the generators draw from: {"pf"}, {"sf"}, or both."""
        return SYSTEM_MODES.get(self.sys_var.get(), {"pf"})

    def in_systems(self, x):
        return system_of(x) in self.systems()

    def _systems_changed(self):
        self.config_data["game_systems"] = self.sys_var.get()
        storage.save("config", self.config_data)
        self._refresh_spell_pool()
        self._refresh_sys_info()

    def _refresh_sys_info(self):
        pf = sum(1 for c in self.all_creatures if system_of(c) == "pf")
        sf = sum(1 for c in self.all_creatures if system_of(c) == "sf")
        pfi = sum(1 for i in self.all_items if system_of(i) == "pf")
        sfi = sum(1 for i in self.all_items if system_of(i) == "sf")
        text = (f"Applies to encounters, treasure, sessions, and creature search.   "
                f"Indexed: Pathfinder {pf} creatures/hazards, {pfi} items | Starfinder {sf}, {sfi}")
        self.sys_info.set(text)

    def _missing_system_warning(self):
        """Message if the chosen system has no indexed content, else ''."""
        missing = [SYSTEM_NAMES[s] for s in sorted(self.systems())
                   if not any(system_of(c) == s for c in self.all_creatures)
                   and not any(system_of(i) == s for i in self.all_items)]
        if not missing:
            return ""
        if "Starfinder" in missing:
            return ("No Starfinder content in your data. On Party & Data, tick Include Starfinder and click "
                    "Download / Update Data.")
        return f"No {', '.join(missing)} content indexed yet. Use Download / Update Data on Party & Data."

    def party_size(self):
        return int(self.ps_var.get())

    def do_roll(self, ref):
        try:
            res = dice.roll(ref)
        except Exception as e:  # a malformed expression should never crash the app
            messagebox.showerror("Roll failed", str(e)); return
        self._show_roll(res)

    def do_roll_expression(self, text):
        try:
            res = dice.roll_expression(text)
        except Exception as e:
            messagebox.showerror("Roll failed", str(e)); return
        self._show_roll(res)

    def _show_roll(self, res):
        if self.dice_win is None or not self.dice_win.winfo_exists():
            self.dice_win = DiceWindow(self)
        summary = res["lines"][0]
        if res.get("kind") == "damage" and res.get("crit") is not None and "crit" not in summary:
            summary += f"  |  crit {res['crit']}"
        target = self._target() if hasattr(self, "target_var") else None
        note = None
        if res.get("kind") == "attack" and target is not None and res.get("total") is not None:
            if target.ac is None:
                summary += f"  |  {target.name} has no AC set"
                note = (f"{target.name} has no AC set\n", "muted")
            else:
                d, msg = self.combat.attack(target.id, res["total"], res.get("nat"))
                summary += msg
                note = (f"{HIT[d]}{msg.split(':', 1)[0].replace('  vs', ' vs')}\n", "crit" if d == 3 else "hit")
        if res.get("damage") is not None:
            self.last_damage = {"total": res["damage"], "crit_total": res.get("crit"),
                                "parts": res.get("damage_parts") or [(res["damage"], "")],
                                "crit_parts": res.get("crit_parts") or ([(res["crit"], "")] if res.get("crit") else []),
                                "persist": res.get("persist") or [], "label": res.get("title", "")}
            if hasattr(self, "apply_dmg_btn"):
                self.apply_info.set(f"Last damage {res['damage']}" +
                                    (f" (crit {res['crit']})" if res.get("crit") is not None else ""))
        self.dice_win.add(res, note)
        self.last_roll.set("Last roll: " + summary)
        if self.combat.round:                  # during a fight, rolls also go to the combat log
            if res.get("kind") != "attack" or target is None:
                self.combat._log(summary)
            else:
                self.combat._log(res["lines"][0])
            self._combat_changed()

    def _open_dice(self):
        if self.dice_win is None or not self.dice_win.winfo_exists():
            self.dice_win = DiceWindow(self)
        self.dice_win.bring_to_front()

    def open_ref(self, ref, source=None):
        if ref.startswith("roll:"):
            self.do_roll(ref); return
        if ref.startswith("page:"):
            self._open_page(ref[5:]); return
        if ref.startswith("newpage:"):
            title = ref[8:]
            if messagebox.askyesno("New page", f"Create a notebook page called '{title}'?"):
                self.nb.select(self.tab_notebook)
                self._new_page(title, "Note")
            return
        if ref.startswith("creature:"):
            name = ref[9:].lower()
            c = next((x for x in self.c_creatures if x.name.lower() == name), None) or \
                next((x for x in self.all_creatures if x.name.lower() == name), None)
            if c:
                self._popout_creature(c)
            return
        if ref.startswith("self:"):
            if source:
                source.jump(ref[5:])
            return
        if ref.startswith("newspell:"):
            self._open_generated_spell(ref[9:]); return
        rowid = self.rules.resolve(ref)
        if not rowid:
            return
        if self.rules_win is None or not self.rules_win.winfo_exists():
            self.rules_win = RulesWindow(self)
        self.rules_win.show(rowid)
        self.rules_win.lift()

    def _pb_lookup(self, name, kind):
        """Rules entry for a Pathbuilder name (weapon traits, feat actions), or None."""
        try:
            rid = self.rules.resolve(f"{kind}:{name}")
            e = self.rules.rule(rid) if rid else None
        except Exception:
            return None
        return e if e and e.get("kind") == kind else None

    def _pc_stat(self, pc, with_text=False, compact=False):
        return pb.pc_details(pc, lookup=self._pb_lookup, with_text=with_text, compact_actions=compact)

    def details_for(self, c):
        if c.custom:
            base = next((x for x in self.c_creatures if x.name == c.name), c)
            d = custom_details(base)
        else:
            d = self.details_db.get(c.base_uid)
        return apply_adjustment(d, c.adjust) if d else None

    # ---------- Party & Data ----------
    def _build_party(self):
        sub = TabbedPane(self.tab_party, level=2); sub.pack(fill="both", expand=True, padx=4, pady=4)
        f = ttk.Frame(sub); sub.add(f, text="Party and Data")
        lootpage = ttk.Frame(sub); sub.add(lootpage, text="Party Loot")
        self.party_sub, self.party_loot_page = sub, lootpage
        auto = ttk.LabelFrame(f, text="Rules data (Foundry pf2e, downloaded from GitHub releases)")
        auto.pack(fill="x", padx=8, pady=(8, 2))
        self.ver_var = tk.StringVar()
        ttk.Label(auto, textvariable=self.ver_var).pack(side="left", padx=6, pady=6)
        ttk.Button(auto, text="Download / Update Data", command=self._update_data).pack(side="left", padx=2)
        ttk.Button(auto, text="Check for Updates", command=lambda: self._check_updates(True)).pack(side="left", padx=2)
        self.sf_var = tk.BooleanVar(value=self.config_data.get("include_starfinder", True))
        ttk.Checkbutton(auto, text="Include Starfinder", variable=self.sf_var,
                        command=self._save_data_opts).pack(side="left", padx=8)
        self.autochk_var = tk.BooleanVar(value=self.config_data.get("check_on_startup", True))
        ttk.Checkbutton(auto, text="Check on startup", variable=self.autochk_var,
                        command=self._save_data_opts).pack(side="left")

        data_box = ttk.LabelFrame(f, text="Advanced: index a local folder instead")
        data_box.pack(fill="x", padx=8, pady=2)
        self.path_var = tk.StringVar(value=self.config_data.get("foundry_path", ""))
        ttk.Entry(data_box, textvariable=self.path_var, width=80).pack(side="left", padx=4, pady=6)
        ttk.Button(data_box, text="Browse", command=self._browse).pack(side="left")
        ttk.Button(data_box, text="Build / Rebuild Index",
                   command=lambda: self._run_index(self.path_var.get().strip())).pack(side="left", padx=4)
        self.status_var = tk.StringVar()
        ttk.Label(f, textvariable=self.status_var).pack(anchor="w", padx=10)
        self._refresh_version()
        if self.autochk_var.get():
            self.after(1500, lambda: self._check_updates(False))

        pbox = ttk.LabelFrame(f, text="Party")
        pbox.pack(fill="both", expand=True, padx=8, pady=8)
        pcols = ("name", "level", "perception", "hp", "ac")
        self.party_tree = ttk.Treeview(pbox, columns=pcols, show="headings", height=8)
        for c, t, w in zip(pcols, ("Character", "Level", "Perception", "Max HP", "AC"), (220, 60, 80, 70, 50)):
            self.party_tree.heading(c, text=t); self.party_tree.column(c, width=w, anchor="w" if c == "name" else "center")
        self.party_tree.bind("<Double-1>", lambda e: self._edit_selected_pc())
        self.party_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        btns = ttk.Frame(pbox); btns.pack(side="left", fill="y", padx=6)
        ttk.Button(btns, text="Import Pathbuilder JSON", command=self._import_pb).pack(fill="x", pady=2)
        ttk.Button(btns, text="Add by Pathbuilder ID", command=self._add_pb_id).pack(fill="x", pady=2)
        ttk.Button(btns, text="Refresh Party from Pathbuilder", command=self._refresh_pb).pack(fill="x", pady=2)
        ttk.Button(btns, text="Add Manually", command=self._add_pc).pack(fill="x", pady=2)
        ttk.Button(btns, text="Edit Selected", command=self._edit_selected_pc).pack(fill="x", pady=2)
        ttk.Button(btns, text="Remove Selected", command=self._remove_pc).pack(fill="x", pady=2)
        ttk.Button(btns, text="Resources...", command=self._party_resources).pack(fill="x", pady=2)
        ttk.Separator(btns).pack(fill="x", pady=8)
        ttk.Label(btns, text="Party level").pack(anchor="w")
        self.pl_var = tk.IntVar(value=self.config_data.get("party_level", 1))
        ttk.Spinbox(btns, from_=1, to=20, textvariable=self.pl_var, width=6).pack(anchor="w")
        ttk.Label(btns, text="Party size").pack(anchor="w", pady=(6, 0))
        self.ps_var = tk.IntVar(value=self.config_data.get("party_size", DEFAULT_PARTY_SIZE))
        ttk.Spinbox(btns, from_=1, to=10, textvariable=self.ps_var, width=6).pack(anchor="w")
        self.roster_var = tk.StringVar()
        ttk.Label(btns, textvariable=self.roster_var, foreground="#777", wraplength=150).pack(anchor="w")
        self.ps_var.trace_add("write", lambda *a: self._party_size_changed())
        ttk.Button(btns, text="Save Party Settings", command=self._save_party_cfg).pack(fill="x", pady=8)
        ttk.Separator(btns).pack(fill="x", pady=4)
        ttk.Button(btns, text="Back Up My Data...", command=self._backup).pack(fill="x", pady=2)
        ttk.Button(btns, text="Restore Backup...", command=self._restore).pack(fill="x", pady=2)
        self._build_party_loot(lootpage)

    def _save_data_opts(self):
        self.config_data["include_starfinder"] = self.sf_var.get()
        self.config_data["check_on_startup"] = self.autochk_var.get()
        storage.save("config", self.config_data)

    def _refresh_version(self, latest=None):
        tag = updater.installed_tag(storage.PF2E_DATA)
        text = f"Installed: {tag or 'none'}"
        if latest:
            text += f"   Latest: {latest}" + ("   (update available)" if latest != tag else "   (up to date)")
        self.ver_var.set(text)

    def _check_updates(self, interactive):
        def work():
            try:
                latest = updater.latest_pf2e_tag()
                self.after(0, self._refresh_version, latest)
                if interactive:
                    cur = updater.installed_tag(storage.PF2E_DATA)
                    msg = "You're up to date." if latest == cur else f"{latest} is available. Click Download / Update Data."
                    self.after(0, messagebox.showinfo, "Update check", msg)
            except Exception as e:
                if interactive:
                    self.after(0, messagebox.showerror, "Update check failed", str(e))
        threading.Thread(target=work, daemon=True).start()

    def _status(self, msg):
        self.after(0, self.status_var.set, msg)

    def _update_data(self):
        self.status_var.set("Checking latest release...")
        sf = self.sf_var.get()

        def work():
            try:
                tag = updater.download(storage.PF2E_DATA, include_starfinder=sf, progress=self._status)
                self._status(f"Downloaded {tag}. Building index...")
                cs, its = data.build_index(storage.PF2E_DATA, storage.INDEX, storage.DETAILS, sf, self._status)
                self.after(0, self._index_done, cs, its, str(storage.PF2E_DATA), None)
                self.after(0, self._refresh_version, tag)
            except Exception as e:
                self.after(0, self._index_done, None, None, "", e)
        threading.Thread(target=work, daemon=True).start()

    def _browse(self):
        p = filedialog.askdirectory(title="Select the pf2e repo or its packs folder")
        if p:
            self.path_var.set(p)

    def _run_index(self, path):
        if not path:
            messagebox.showwarning("No path", "Pick a folder first.")
            return
        self.status_var.set("Indexing... this can take a minute.")
        sf = self.sf_var.get()

        def work():
            try:
                cs, its = data.build_index(path, storage.INDEX, storage.DETAILS, sf, self._status)
                self.after(0, self._index_done, cs, its, path, None)
            except Exception as e:
                self.after(0, self._index_done, None, None, path, e)
        threading.Thread(target=work, daemon=True).start()

    def _index_done(self, cs, its, path, err):
        if err:
            messagebox.showerror("Data update failed", str(err)); self._refresh_status(); return
        self.f_creatures, self.f_items, self.index_src = cs, its, path
        self.details_db.reset()
        self._refresh_spell_pool()
        self.affinity = Affinity(general_sources(self.f_creatures))
        self._load_vocab_async()
        self._refresh_sys_info()
        if path != str(storage.PF2E_DATA):
            self.config_data["foundry_path"] = path
            storage.save("config", self.config_data)
        self._refresh_status()

    def _refresh_status(self):
        self.status_var.set(
            f"Foundry: {sum(1 for c in self.f_creatures if not c.is_hazard)} creatures, "
            f"{sum(1 for c in self.f_creatures if c.is_hazard)} hazards, {len(self.f_items)} items   |   "
            f"Custom: {len(self.c_creatures)} creatures, {len(self.c_items)} items")

    def _import_pb(self):
        for p in filedialog.askopenfilenames(filetypes=[("JSON", "*.json")]):
            try:
                with open(p, encoding="utf-8") as f:
                    pc = pb.parse(json.load(f), Path(p).stem)
            except Exception as e:
                messagebox.showerror("Import failed", f"{p}\n{e}"); continue
            self._merge_pc(pc)
        self._party_changed()

    def _merge_pc(self, pc):
        old = next((x for x in self.party if x["name"] == pc["name"]
                    or (pc.get("pathbuilder_id") and x.get("pathbuilder_id") == pc.get("pathbuilder_id"))), None)
        if old and old.get("pathbuilder_id") and not pc.get("pathbuilder_id"):
            pc["pathbuilder_id"] = old["pathbuilder_id"]
        if old and old.get("state") and not pc.get("state"):
            pc["state"] = old["state"]          # resources spent, riders, manual defenses and strikes survive a refresh
        self.party = [x for x in self.party if x is not old] + [pc]
        self._sync_pc_pages(pc)

    def _sync_pc_pages(self, pc):
        """A character's Notebook page holds its own copy. When the party copy is refreshed, bring the page up to date,
        but never replace a more complete copy with a less complete one."""
        pid, name, changed = pc.get("pathbuilder_id"), str(pc.get("name", "")).lower(), False
        for x in self.notebook:
            old = x.get("pc")
            if (x.get("type") in ("PC", "NPC") and isinstance(old, dict) and old is not pc
                    and ((pid and x.get("pathbuilder_id") == pid) or x["title"].lower() == name)
                    and pb.rank(pc) >= pb.rank(old)):
                new = dict(pc)
                if old.get("state") and not new.get("state"):
                    new["state"] = old["state"]
                x["pc"], changed = new, True
        if changed:
            storage.save("notebook", self.notebook)

    def _upgrade_stored_pcs(self):
        """Rebuild saved characters whose importer has since improved, from the export saved with each one. Returns how
        many were rebuilt."""
        n = 0
        pcs = list(self.party) + [p["pc"] for p in self.notebook if isinstance(p.get("pc"), dict)]
        for pc in pcs:
            if isinstance(pc.get("raw"), dict) and pb.needs_upgrade(pc):
                try:
                    new = pb.upgrade(pc)
                except Exception:
                    new = None
                if new:
                    pc.clear(); pc.update(new); n += 1
        if n:
            storage.save("party", self.party); storage.save("notebook", self.notebook)
        return n

    def _add_pb_id(self):
        win = tk.Toplevel(self); win.title("Add by Pathbuilder ID")
        ttk.Label(win, text="In Pathbuilder: Menu > Export > Export JSON. Paste the ID (or the link) here.\n"
                            "One per line to add several.", justify="left").pack(padx=8, pady=6, anchor="w")
        box = tk.Text(win, height=5, width=40); box.pack(padx=8)
        status = tk.StringVar(); ttk.Label(win, textvariable=status, foreground="#a33", wraplength=380).pack(padx=8)

        def go():
            ids = [pb.parse_id(l) for l in box.get("1.0", "end").splitlines() if l.strip()]
            ids = [i for i in ids if i]
            if not ids:
                status.set("No IDs found."); return
            status.set(f"Fetching {len(ids)}...")
            self._fetch_pcs(ids, done=lambda errs: (status.set("; ".join(errs)) if errs else win.destroy()))
        ttk.Button(win, text="Fetch", command=go).pack(pady=6)

    def _refresh_pb(self):
        ids = [pc["pathbuilder_id"] for pc in self.party if pc.get("pathbuilder_id")]
        if not ids:
            messagebox.showinfo("No IDs", "No party members have a Pathbuilder ID yet. Use Add by Pathbuilder ID."); return
        self.status_var.set(f"Refreshing {len(ids)} characters from Pathbuilder...")
        self._fetch_pcs(ids, done=lambda errs: (messagebox.showerror("Some refreshes failed", "\n".join(errs))
                                                 if errs else self.status_var.set("Party refreshed from Pathbuilder.")))

    def _fetch_pcs(self, ids, done):
        def work():
            got, errs = [], []
            for pid in ids:
                try:
                    pc = pb.parse(pb.fetch(pid))
                    pc["pathbuilder_id"] = pid
                    got.append(pc)
                except Exception as e:
                    errs.append(f"ID {pid}: {e}")
            self.after(0, finish, got, errs)

        def finish(got, errs):
            for pc in got:
                self._merge_pc(pc)
            if got:
                self._party_changed()
            done(errs)
        threading.Thread(target=work, daemon=True).start()

    def _pc_copies(self, pc):
        """Every stored copy of this character: party entry and notebook page data (matched by name)."""
        name = pc["name"].lower()
        out = [pc]
        for x in list(self.party) + [p["pc"] for p in self.notebook if p.get("pc")]:
            if x is not pc and x.get("name", "").lower() == name:
                out.append(x)
        return out

    def _pc_state_changed(self, pc):
        """Share one state dict between the party entry and the notebook page, then save both."""
        st = pc.setdefault("state", {})
        for x in self._pc_copies(pc):
            x["state"] = st
        storage.save("party", self.party)
        storage.save("notebook", self.notebook)

    @staticmethod
    def _has_feature(pc, name):
        n = name.lower()
        return any(f["name"].lower() == n for f in pc.get("feats", [])) or \
            any(str(x).lower() == n for x in pc.get("specials", []))

    def _setup_pc_combatant(self, comb, pc):
        """Defenses and riders for a character who has just entered combat."""
        try:
            comb.iwr = parse_iwr(self._pc_stat(pc))
        except Exception:
            comb.iwr = {}
        comb.riders = [dict(r) for r in (pc.get("state") or {}).get("riders", [])]
        if not comb.riders and self._has_feature(pc, "Sneak Attack"):
            comb.riders.append({"label": "Sneak Attack", "dice": f"{sneak_attack_dice(pc.get('level'))}d6",
                                "precision": True, "dtype": "", "applies": "sneak", "active": False})

    def _add_pc(self):
        self._edit_pc_dialog(None)

    def _backup(self):
        p = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Backup", "*.zip")],
                                         initialfile=f"pf2e_gm_backup_{datetime.date.today().isoformat()}.zip")
        if p:
            files = exporter.make_backup(storage, p)
            messagebox.showinfo("Backed up", f"Saved {len(files)} files to\n{p}")

    def _restore(self):
        p = filedialog.askopenfilename(filetypes=[("Backup", "*.zip")])
        if not p or not messagebox.askyesno("Restore", "Replace your current custom content, party, sessions, and "
                                            "ledger with this backup? Current files are kept as .before-restore."):
            return
        try:
            files = exporter.restore_backup(storage, p)
        except Exception as e:
            messagebox.showerror("Restore failed", str(e)); return
        messagebox.showinfo("Restored", f"Restored {len(files)} files. Restart the app to load them.")

    def _edit_selected_pc(self):
        sel = self.party_tree.selection()
        if sel:
            name = self.party_tree.item(sel[0], "values")[0]
            pc = next((x for x in self.party if x["name"] == name), None)
            if pc:
                self._edit_pc_dialog(pc)

    def _edit_pc_dialog(self, pc):
        win = tk.Toplevel(self); win.title("Edit character" if pc else "Add character")
        pc = pc or {"name": "", "level": self.pl_var.get()}
        fields = [("name", "Name"), ("level", "Level"), ("perception", "Perception mod"),
                  ("hp", "Max HP"), ("ac", "AC")]
        vars_ = {}
        for r, (k, label) in enumerate(fields):
            ttk.Label(win, text=label).grid(row=r, column=0, padx=4, pady=2, sticky="w")
            v = tk.StringVar(value="" if pc.get(k) is None else str(pc.get(k)))
            ttk.Entry(win, textvariable=v, width=24).grid(row=r, column=1, padx=4, pady=2)
            vars_[k] = v
        original = pc.get("name")
        st0 = pc.get("state") or {}
        dvars = {}
        for r2, (k, label) in enumerate((("immunities", "Extra immunities"), ("weaknesses", "Extra weaknesses"),
                                         ("resistances", "Extra resistances")), start=len(fields)):
            ttk.Label(win, text=label).grid(row=r2, column=0, padx=4, pady=2, sticky="w")
            dvars[k] = tk.StringVar(value=(st0.get("defenses") or {}).get(k, ""))
            ttk.Entry(win, textvariable=dvars[k], width=34).grid(row=r2, column=1, padx=4, pady=2)
        ttk.Label(win, text="Extra Strikes, one per line:\nName | +bonus | damage | traits",
                  justify="left").grid(row=len(fields) + 3, column=0, padx=4, pady=2, sticky="nw")
        ms_text = tk.Text(win, height=3, width=34)
        ms_text.insert("1.0", st0.get("manual_strikes", ""))
        ms_text.grid(row=len(fields) + 3, column=1, padx=4, pady=2)
        ttk.Label(win, text="Defenses like: fire 5, physical 5 (except silver). Added to Pathbuilder's own.",
                  foreground="#777").grid(row=len(fields) + 4, column=0, columnspan=2, padx=4, sticky="w")

        def ok():
            name = vars_["name"].get().strip()
            if not name:
                return
            new = {k: v for k, v in (pc or {}).items() if k not in ("name", "level", "perception", "hp", "ac", "raw")}
            state = dict(new.get("state") or {})
            state["defenses"] = {k: v.get().strip() for k, v in dvars.items()}
            state["manual_strikes"] = ms_text.get("1.0", "end").strip()
            new["state"] = state
            new.update({"name": name, "level": self._int_or_none(vars_["level"].get()) or 1})
            for k in ("perception", "hp", "ac"):
                val = self._int_or_none(vars_[k].get())
                if val is not None:
                    new[k] = val
            self.party = [x for x in self.party if x["name"] not in (original, name)] + [new]
            self._party_changed()
            win.destroy()
        ttk.Button(win, text="Save", command=ok).grid(row=len(fields) + 5, column=1, sticky="e", padx=4, pady=6)

    def _remove_pc(self):
        names = {self.party_tree.item(i, "values")[0] for i in self.party_tree.selection()}
        self.party = [pc for pc in self.party if pc["name"] not in names]
        self._party_changed()

    def _party_size_changed(self):
        try:
            size = self.party_size()
        except (tk.TclError, ValueError):
            return
        if size < 1:
            return
        self.config_data["party_size"] = size
        storage.save("config", self.config_data)
        self._gm_sync_party()
        if hasattr(self, "ledger_tree"):
            self._refresh_ledger()
        if hasattr(self, "roster_var"):
            self._refresh_party()
        if hasattr(self, "qr_view"):
            self._qr_calc()

    def _party_changed(self):
        storage.save("party", self.party)
        if self.party:
            levels = Counter(pc["level"] for pc in self.party)
            self.pl_var.set(levels.most_common(1)[0][0])
            if len(levels) > 1:
                messagebox.showinfo("Mixed levels",
                                    "Party has mixed levels. Party level set to the most common; adjust if needed.")
        self._save_party_cfg()
        self._refresh_party()

    def _save_party_cfg(self):
        self.config_data["party_level"] = self.party_level()
        self.config_data["party_size"] = self.party_size()
        storage.save("config", self.config_data)
        self._gm_sync_party()
        if hasattr(self, "loot_lvl"):
            self.loot_lvl.set(self.party_level())
            self._refresh_ledger()
        if hasattr(self, "xp_var"):
            self._refresh_xp()

    def _refresh_party(self):
        if hasattr(self, "pl_tree"):
            self._pl_refresh()
        if hasattr(self, "sc_def"):
            self._refresh_secret_party()
        if hasattr(self, "dt_pc"):
            self._dt_party_changed()
        n = len(self.party)
        self.roster_var.set(f"Roster: {n} PC{'s' if n != 1 else ''}. Party size is set separately"
                            + (" (they differ)." if n and n != self.party_size() else "."))
        self.party_tree.delete(*self.party_tree.get_children())
        for pc in sorted(self.party, key=lambda x: x["name"]):
            per = pc.get("perception")
            self.party_tree.insert("", "end", values=(pc["name"], pc["level"],
                                                      "" if per is None else f"{per:+d}",
                                                      pc.get("hp", ""), pc.get("ac", "")))

    # ---------- Party Loot ----------
    def _build_party_loot(self, f):
        """Everything the party owns: what the app has awarded or you have added, and each PC's Pathbuilder gear."""
        self.dt_store = dt.ensure_store(getattr(self, "dt_store", None) or storage.load("downtime"))
        st = self.party_loot["settings"]
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=(6, 2))
        self.pl_coins = tk.StringVar()
        ttk.Label(top, textvariable=self.pl_coins, font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(top, text="Add Coins...", command=lambda: self._pl_coins(1)).pack(side="left", padx=(12, 2))
        ttk.Button(top, text="Take Coins...", command=lambda: self._pl_coins(-1)).pack(side="left", padx=2)
        ttk.Label(top, text="Sell at").pack(side="left", padx=(16, 2))
        self.pl_rate = tk.StringVar(value=str(st.get("sell_rate", ploot.DEFAULT_RATE)))
        ttk.Spinbox(top, from_=0, to=200, increment=5, textvariable=self.pl_rate, width=5).pack(side="left")
        ttk.Label(top, text="% of price").pack(side="left", padx=(2, 0))
        self.pl_rate.trace_add("write", lambda *a: self._pl_rate_changed())
        self.pl_show_pb = tk.BooleanVar(value=st.get("show_pathbuilder", True))
        ttk.Checkbutton(top, text="Show Pathbuilder gear", variable=self.pl_show_pb,
                        command=self._pl_toggle_pb).pack(side="left", padx=12)
        bar = ttk.Frame(f); bar.pack(fill="x", padx=8, pady=2)
        for text, cmd in (("Add Item...", self._pl_add_dialog), ("Give To...", self._pl_give), ("Sell...", self._pl_sell),
                          ("Used Up", lambda: self._pl_remove("used")), ("Lost...", lambda: self._pl_remove("lost")),
                          ("Given Away...", lambda: self._pl_remove("given")),
                          ("Save Its New Spells", self._pl_save_spells), ("Make Card...", self._pl_card_make),
                          ("Copy List", self._pl_copy), ("Export...", self._pl_export)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=2)
        self.pl_info = tk.StringVar(value=(
            "Treasure you award, items from Magic Items and My Items, and an NPC's gear (Loot This NPC) land in the party "
            "stash. Give To hands an item to a PC. Selling pays whoever carried it: a PC's sale goes into their funds "
            "(Downtime, Funds), a stash sale into the stash coins. Pathbuilder gear is read from the party; change it in "
            "Pathbuilder. Its value is the base item plus its runes; +? means a rune or material has no price on file."))
        ttk.Label(f, textvariable=self.pl_info, foreground="#555", wraplength=1150, justify="left").pack(anchor="w", padx=10)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.PanedWindow(pane, orient="vertical"); pane.add(left, weight=3)
        tf = ttk.Frame(left); left.add(tf, weight=3)
        self.pl_tree = ttk.Treeview(tf, columns=("qty", "lvl", "value", "source", "date"), show="tree headings", height=16)
        self.pl_tree.heading("#0", text="Item"); self.pl_tree.column("#0", width=320)
        for c, t, w in (("qty", "Qty", 40), ("lvl", "Lvl", 40), ("value", "Value", 110), ("source", "Where from", 170),
                        ("date", "Date", 85)):
            self.pl_tree.heading(c, text=t); self.pl_tree.column(c, width=w, stretch=(c == "source"))
        self.pl_tree.tag_configure("holder", font=("TkDefaultFont", 10, "bold"))
        self.pl_tree.tag_configure("pb", foreground="#555")
        self.pl_tree.tag_configure("coins", foreground="#1e7a34")
        sb = ttk.Scrollbar(tf, command=self.pl_tree.yview); self.pl_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.pl_tree.pack(fill="both", expand=True)
        self.pl_tree.bind("<<TreeviewSelect>>", lambda e: self._pl_show())
        hf = ttk.LabelFrame(left, text="History (sold, used, lost, given away, moved, coins)"); left.add(hf, weight=1)
        self.pl_hist = ttk.Treeview(hf, columns=("what", "item", "who", "amount"), show="tree headings", height=6)
        self.pl_hist.heading("#0", text="Date"); self.pl_hist.column("#0", width=85)
        for c, t, w in (("what", "What", 80), ("item", "Item", 260), ("who", "Who", 200), ("amount", "Amount", 110)):
            self.pl_hist.heading(c, text=t); self.pl_hist.column(c, width=w)
        self.pl_hist.pack(fill="both", expand=True)
        self.pl_card = RichText(pane, self); pane.add(self.pl_card, weight=2)
        self.pl_card.show_message("Select an item to see its card or rules text.")
        self._pl_rows = {}
        self._pl_refresh()

    def _pl_save(self):
        storage.save("party_loot", self.party_loot)

    def _pl_changed(self):
        self._pl_save()
        if hasattr(self, "pl_tree"):
            self._pl_refresh()

    def _pl_rate(self):
        try:
            return max(0.0, float(self.pl_rate.get()))
        except (tk.TclError, ValueError, AttributeError):
            return float(self.party_loot["settings"].get("sell_rate", ploot.DEFAULT_RATE))

    def _pl_rate_changed(self):
        try:
            self.party_loot["settings"]["sell_rate"] = max(0.0, float(self.pl_rate.get()))
        except (tk.TclError, ValueError):
            return
        self._pl_save()

    def _pl_toggle_pb(self):
        self.party_loot["settings"]["show_pathbuilder"] = bool(self.pl_show_pb.get())
        self._pl_changed()

    def _pl_price(self, name):
        """The price in gp of an item in your data or Custom Content, by name, or None."""
        key = (len(self.f_items), len(self.c_items))
        if getattr(self, "_pl_price_key", None) != key:
            self._pl_price_map = {}
            for i in self.all_items:
                self._pl_price_map.setdefault(i.name.lower(), (i.price_gp, i.level))
            self._pl_price_key = key
        hit = self._pl_price_map.get(str(name or "").strip().lower())
        return hit[0] if hit else None

    def _pl_level(self, name):
        self._pl_price(name)
        hit = self._pl_price_map.get(str(name or "").strip().lower())
        return hit[1] if hit else None

    def _pl_funds(self, name):
        try:
            return dt.purse_balance(self.dt_store, name)
        except Exception:
            return None

    def _pl_refresh(self):
        if not hasattr(self, "pl_tree"):
            return
        store = self.party_loot
        ploot.prune_pb(store, self.party)
        keep = self.pl_tree.selection()
        self.pl_tree.delete(*self.pl_tree.get_children())
        self._pl_rows = {}
        self.pl_coins.set(f"Party stash coins: {ploot.coin_text(store.get('coins_cp', 0))}")
        names = [pc["name"] for pc in self.party]
        show_pb = self.pl_show_pb.get()
        for h in ploot.holders(store, names):
            pc = next((p for p in self.party if p["name"] == h), None)
            own = [e for e in store["items"] if e["holder"] == h]
            pbr = ploot.pb_rows(pc, store, self._pl_price) if (pc and show_pb) else []
            label = h
            if h == ploot.STASH:
                label += f"   ({ploot.coin_text(store.get('coins_cp', 0))} in coins)"
            else:
                funds = self._pl_funds(h)
                if funds is not None:
                    label += f"   (funds {ploot.coin_text(funds)})"
            worth = sum(e["value_gp"] * e["qty"] for e in own) + sum(r["value_gp"] * r["qty"] for r in pbr)
            hid = "h|" + h
            self.pl_tree.insert("", "end", iid=hid, text=label, open=True, tags=("holder",),
                                values=("", "", ploot.coin_text(ploot.to_cp(worth)) if worth else "", "", ""))
            for e in sorted(own, key=lambda x: x["name"].lower()):
                val = ploot.coin_text(ploot.to_cp(e["value_gp"])) + (" each" if e["qty"] > 1 else "") if e["value_gp"] else ""
                self.pl_tree.insert(hid, "end", iid=e["id"], text=e["name"],
                                    values=(e["qty"], "" if e.get("level") in (None, "") else e["level"], val,
                                            e.get("source", ""), e.get("date", "")))
            for r in pbr:
                val = (ploot.coin_text(ploot.to_cp(r["value_gp"])) + (" each" if r["qty"] > 1 else "")) if r["priced"] else "?"
                if r.get("unpriced"):
                    val += " +?"
                self.pl_tree.insert(hid, "end", iid=r["id"], text=r["name"], tags=("pb",),
                                    values=(r["qty"], "", val, "Pathbuilder", ""))
                self._pl_rows[r["id"]] = r
            if pc and show_pb and pc.get("money"):
                self.pl_tree.insert(hid, "end", iid="pbcoins|" + h, tags=("coins",),
                                    text=f"Coins (Pathbuilder): {ploot.coin_text(ploot.money_cp(pc['money']))}",
                                    values=("", "", "", "Pathbuilder", ""))
        for k in keep:
            if self.pl_tree.exists(k):
                self.pl_tree.selection_set(k)
        self.pl_hist.delete(*self.pl_hist.get_children())
        for i, g in enumerate(reversed(store["log"][-200:])):
            who = g.get("holder", "")
            if g.get("payee") and g["payee"] != who:
                who = f"{who} to {g['payee']}" if who else g["payee"]
            item = (f"{g['qty']} x {g['name']}" if g.get("qty") else g["name"]) + (f" ({g['note']})" if g.get("note") else "")
            amt = g.get("amount_cp") or 0
            self.pl_hist.insert("", "end", iid=str(i), text=g.get("date", ""),
                                values=(ploot.HOW.get(g["how"], g["how"]), item, who, ploot.coin_text(amt) if amt else ""))

    def _pl_selected(self):
        """("entry", loot entry), ("pb", Pathbuilder row), or (None, None)."""
        sel = self.pl_tree.selection()
        if not sel:
            return None, None
        iid = sel[0]
        if iid in self._pl_rows:
            return "pb", self._pl_rows[iid]
        e = ploot.find(self.party_loot, iid)
        return ("entry", e) if e else (None, None)

    def _pl_need(self):
        kind, r = self._pl_selected()
        if r is None:
            messagebox.showinfo("Select an item", "Select an item in the list first (not a person's name).")
        return kind, r

    def _pl_show(self):
        kind, r = self._pl_selected()
        if r is None:
            return
        if kind == "entry" and r.get("magic_item"):
            self.pl_card.show(itemgen.card_segments(r["magic_item"], gm=True)); return
        name = r.get("rules_name") or r["name"]
        rowid = self.rules.resolve(f"item:{name}") if name else None
        e = self.rules.rule(rowid) if rowid else None
        if e:
            segs = list(render_entry(e))
            if kind == "pb" and r.get("rune_gp"):                 # the rules text is the base item; say what the runes add
                note = (f"\nValue in Party Loot: {ploot.coin_text(ploot.to_cp(r['value_gp']))} = base "
                        f"{ploot.coin_text(ploot.to_cp(r.get('base_gp', 0)))} + runes {ploot.coin_text(ploot.to_cp(r['rune_gp']))}.")
                if r.get("unpriced"):
                    note += f" Not priced: {', '.join(r['unpriced'])}."
                segs = [(note.lstrip("\n") + "\n\n", "muted", None)] + segs
            self.pl_card.show(segs); return
        custom = next((i for i in self.c_items if i.name.lower() == str(name).lower()), None)
        if custom:
            self.pl_card.show(render_entry(custom_item_entry(custom))); return
        bits = [r["name"], f"Held by {r['holder']}", f"Quantity {r['qty']}"]
        if r.get("value_gp"):
            bits.append(f"Value {ploot.coin_text(ploot.to_cp(r['value_gp']))} each")
        if r.get("source"):
            bits.append(f"From: {r['source']}")
        if r.get("notes"):
            bits.append(r["notes"])
        self.pl_card.show_message("\n".join(bits) + "\n\nNo rules text for this item in your data.")

    def _pl_pay(self, payee, cp, reason):
        """Pay a sale to the party stash or a PC's funds."""
        if not cp:
            return
        if payee == ploot.STASH:
            self.party_loot["coins_cp"] = int(self.party_loot.get("coins_cp", 0)) + int(cp)
        else:
            dt.purse_add(self.dt_store, payee, int(cp), reason)
            self._dt_save()
            if hasattr(self, "df_tree"):
                self._dt_refresh_funds()
            if hasattr(self, "dt_info"):
                self._dt_pc_info()

    def _pl_holder_names(self):
        return ploot.holders(self.party_loot, [pc["name"] for pc in self.party])

    def _pl_sell(self):
        kind, r = self._pl_need()
        if r is None:
            return
        win = tk.Toplevel(self); win.title(f"Sell {r['name']}"); win.transient(self)
        qty = tk.StringVar(value="1" if r["qty"] > 1 else "1")
        rate = tk.StringVar(value=f"{self._pl_rate():g}")
        amount = tk.StringVar()
        payee = tk.StringVar(value=r["holder"])
        each = r.get("value_gp") or 0
        rows = (("How many", ttk.Spinbox(win, from_=1, to=max(1, r["qty"]), textvariable=qty, width=5)),
                ("Rate (% of price)", ttk.Spinbox(win, from_=0, to=200, increment=5, textvariable=rate, width=6)),
                ("Paid", ttk.Entry(win, textvariable=amount, width=22)),
                ("Paid to", ttk.Combobox(win, textvariable=payee, values=self._pl_holder_names(), state="readonly", width=22)))
        for i, (lab, w) in enumerate(rows):
            ttk.Label(win, text=lab).grid(row=i, column=0, sticky="w", padx=8, pady=3); w.grid(row=i, column=1, sticky="w", padx=8)
        note = (f"Price {ploot.coin_text(ploot.to_cp(each))} each." if each else
                "No price on file for this item, so type what it sold for.")
        ttk.Label(win, text=note + " Change the amount if you strike a different deal.", foreground="#777",
                  wraplength=320, justify="left").grid(row=len(rows), column=0, columnspan=2, padx=8, sticky="w")

        def recalc(*_):
            try:
                n, pct = max(1, int(qty.get())), float(rate.get())
            except (tk.TclError, ValueError):
                return
            amount.set(ploot.coin_text(ploot.sell_amount_cp(each, min(n, r["qty"]), pct)))
        qty.trace_add("write", recalc); rate.trace_add("write", recalc); recalc()

        def ok():
            try:
                n = max(1, min(int(qty.get()), r["qty"]))
                cp = ploot.parse_coins(amount.get().replace(" and ", " "))
            except (ValueError, tk.TclError) as e:
                messagebox.showwarning("Sell", str(e), parent=win); return
            who = payee.get() or r["holder"]
            reason = f"Sold {n} x {r['name']}"
            if kind == "entry":
                ploot.dispose(self.party_loot, r["id"], "sold", n, cp, who)
            else:
                ploot.pb_dispose(self.party_loot, r, "sold", n, cp, who)
            self._pl_pay(who, cp, reason)
            win.destroy()
            self._pl_changed()
            self.last_roll.set(f"{reason} for {ploot.coin_text(cp)}, paid to {who}.")
        ttk.Button(win, text="Sell", command=ok).grid(row=len(rows) + 1, column=1, sticky="e", padx=8, pady=8)
        self.pl_sell_win = (win, qty, rate, amount, payee, ok)

    def _pl_how_many(self, r, verb):
        if r["qty"] <= 1:
            return 1
        n = self._ask_int(verb, f"How many of {r['name']}? (1 to {r['qty']})", r["qty"])
        if n is None:
            return None
        return max(1, min(n, r["qty"]))

    def _pl_remove(self, how):
        kind, r = self._pl_need()
        if r is None:
            return
        n = self._pl_how_many(r, ploot.HOW[how])
        if n is None:
            return
        note = ""
        if how in ("lost", "given"):
            note = self._ask_line(ploot.HOW[how], "A short note for the history (optional): where, or to whom", "") or ""
        if kind == "entry":
            ploot.dispose(self.party_loot, r["id"], how, n, note=note.strip())
        else:
            ploot.pb_dispose(self.party_loot, r, how, n, note=note.strip())
        self._pl_changed()
        self.last_roll.set(f"{r['name']}: {n} {ploot.HOW[how].lower()}.")

    def _pl_give(self):
        kind, r = self._pl_need()
        if r is None:
            return
        win = tk.Toplevel(self); win.title(f"Give {r['name']}"); win.transient(self)
        who = tk.StringVar(value=next((h for h in self._pl_holder_names() if h != r["holder"]), ploot.STASH))
        qty = tk.StringVar(value=str(r["qty"]))
        ttk.Label(win, text="Give to").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        ttk.Combobox(win, textvariable=who, values=[h for h in self._pl_holder_names() if h != r["holder"]],
                     state="readonly", width=22).grid(row=0, column=1, padx=8)
        ttk.Label(win, text="How many").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        ttk.Spinbox(win, from_=1, to=max(1, r["qty"]), textvariable=qty, width=5).grid(row=1, column=1, sticky="w", padx=8)
        if kind == "pb":
            ttk.Label(win, text="This is Pathbuilder gear: it moves here now, and the player should move it in Pathbuilder too.",
                      foreground="#777", wraplength=300, justify="left").grid(row=2, column=0, columnspan=2, padx=8)

        def ok():
            try:
                n = max(1, min(int(qty.get()), r["qty"]))
            except (ValueError, tk.TclError):
                return
            to = who.get()
            if not to:
                return
            if kind == "entry":
                ploot.move(self.party_loot, r["id"], to, n)
            else:
                ploot.pb_dispose(self.party_loot, r, "moved", n, payee=to)
                ploot.add(self.party_loot, ploot.new_entry(ploot._base_name(r["name"]), n, holder=to, value_gp=r["value_gp"],
                                                           source=f"From {r['holder']} (Pathbuilder)", rules_name=r["rules_name"]))
            win.destroy()
            self._pl_changed()
            self.last_roll.set(f"{r['holder']} gave {n} x {r['name']} to {to}.")
        ttk.Button(win, text="Give", command=ok).grid(row=3, column=1, sticky="e", padx=8, pady=8)
        self.pl_give_win = (win, who, qty, ok)

    def _pl_add_dialog(self):
        win = tk.Toplevel(self); win.title("Add to Party Loot"); win.transient(self)
        name = Combo(win, values_key="item_names", width=34)
        if "item_names" in getattr(self, "vocab", {}):
            name.set_values(self.vocab["item_names"])
        qty, value, level, notes = tk.StringVar(value="1"), tk.StringVar(), tk.StringVar(), tk.StringVar()
        holder = tk.StringVar(value=ploot.STASH)
        rows = (("Item", name), ("How many", ttk.Spinbox(win, from_=1, to=999, textvariable=qty, width=5)),
                ("Held by", ttk.Combobox(win, textvariable=holder, values=self._pl_holder_names(), state="readonly", width=22)),
                ("Value each (blank = from your data)", ttk.Entry(win, textvariable=value, width=14)),
                ("Level (optional)", ttk.Entry(win, textvariable=level, width=6)),
                ("Notes", ttk.Entry(win, textvariable=notes, width=36)))
        for i, (lab, w) in enumerate(rows):
            ttk.Label(win, text=lab).grid(row=i, column=0, sticky="w", padx=8, pady=3); w.grid(row=i, column=1, sticky="w", padx=8)
        self.pl_ledger_too = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text="Also record it in the treasure ledger", variable=self.pl_ledger_too).grid(
            row=len(rows), column=1, sticky="w", padx=8)

        def ok():
            nm = name.var.get().strip()
            if not nm:
                return
            try:
                gp = ploot.parse_coins(value.get()) / 100.0 if value.get().strip() else (self._pl_price(nm) or 0)
            except ValueError as e:
                messagebox.showwarning("Value", str(e), parent=win); return
            lv = self._int_or_none(level.get()) if level.get().strip() else self._pl_level(nm)
            n = self._int_or_none(qty.get()) or 1
            known = self._pl_price(nm) is not None
            ploot.add(self.party_loot, ploot.new_entry(nm, n, holder=holder.get() or ploot.STASH, value_gp=gp, level=lv,
                                                       source="Added by hand", notes=notes.get().strip(),
                                                       rules_name=nm if known else ""))
            if self.pl_ledger_too.get():
                for _ in range(n):
                    self.ledger.append({"level": int(lv or self.party_level()), "kind": "permanent", "name": nm,
                                        "value_gp": float(gp), "date": datetime.date.today().isoformat()})
                storage.save("ledger", self.ledger); self._refresh_ledger()
            win.destroy()
            self._pl_changed()
        ttk.Button(win, text="Add", command=ok).grid(row=len(rows) + 1, column=1, sticky="e", padx=8, pady=8)
        self.pl_add_win = (win, name, qty, holder, value, level, notes, ok)

    def _pl_coins(self, sign):
        text = self._ask_line("Add coins" if sign > 0 else "Take coins",
                              "Amount (for example 25 gp, or 3 gp 5 sp)", "")
        if text is None or not text.strip():
            return
        try:
            cp = ploot.parse_coins(text)
        except ValueError as e:
            messagebox.showwarning("Coins", str(e)); return
        if sign < 0 and cp > self.party_loot.get("coins_cp", 0):
            if not messagebox.askyesno("Take coins", "That's more than the stash holds. Take it anyway (the stash goes "
                                       "below zero)?"):
                return
        why = self._ask_line("What for?", "A short note for the history", "") or ""
        ploot.credit_stash(self.party_loot, sign * abs(cp), why.strip())
        self._pl_changed()

    def _pl_save_spells(self):
        kind, r = self._pl_need()
        if r is None:
            return
        if kind != "entry" or not r.get("magic_item"):
            messagebox.showinfo("Not a grimoire", "Select a grimoire made by the Magic Items generator."); return
        self._save_book_spells(r["magic_item"])

    def _pl_copy(self):
        self.clipboard_clear()
        self.clipboard_append(ploot.inventory_text(self.party_loot, self.party, self._pl_price))
        self.last_roll.set("Copied the party's inventory to the clipboard.")

    def _pl_export(self):
        self._save_text(ploot.inventory_text(self.party_loot, self.party, self._pl_price), "party_loot.md")

    # ---------- Item cards ----------
    def _card_module(self):
        """The card renderer, or None (with a message) when Pillow isn't installed."""
        try:
            from . import cardrender
            return cardrender
        except ImportError:
            messagebox.showinfo("Cards need Pillow", "Making cards needs the Pillow imaging library. Open a command prompt "
                                "and run:\n\n    python -m pip install pillow\n\n(use 'py' in place of 'python' if that is "
                                "how you start this app), then restart the app.")
            return None

    def _card_dialog(self, card):
        """Preview a card and save it as a PNG or a print sheet. Size, background, and what to do with unused space are
        remembered between cards."""
        cr = self._card_module()
        if cr is None or card is None:
            return None
        import base64
        import io
        cfg = self.config_data.get("cards", {})
        win = tk.Toplevel(self); win.title("Make Card: " + card["title"]); win.transient(self)
        left = ttk.Frame(win); left.pack(side="left", fill="y", padx=10, pady=10)
        right = ttk.Frame(win); right.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        state = {"variant": 0, "page": 0, "pages": []}
        combos = {}
        for r, (key, label, table, default) in enumerate((("size", "Size", cr.SIZE_LABELS, "poker"),
                                                          ("background", "Background", cr.BACKGROUNDS, "white"),
                                                          ("fill", "Unused space", cr.FILLS, "blank"))):
            ttk.Label(left, text=label).grid(row=r, column=0, sticky="w", pady=4)
            w = Combo(left, list(table.values()), readonly=True, width=22)
            w.var.set(table.get(cfg.get(key, default), table[default]))
            w.grid(row=r, column=1, sticky="w", padx=6)
            combos[key] = (w, table)
        status = tk.StringVar()
        page_lbl = tk.StringVar()
        copies = tk.StringVar(value="1")
        preview = ttk.Label(right)
        preview.pack()

        def keys():
            return {k: next((key for key, lab in table.items() if lab == w.var.get()), next(iter(table)))
                    for k, (w, table) in combos.items()}

        def refresh(*_):
            k = keys()
            self.config_data["cards"] = k
            storage.save("config", self.config_data)
            state["pages"] = cr.render(card, k["size"], k["background"], k["fill"], state["variant"])
            state["page"] = min(state["page"], len(state["pages"]) - 1)
            im = state["pages"][state["page"]].convert("RGBA")
            ground = cr.Image.new("RGBA", im.size, (225, 225, 225, 255) if k["background"] == "transparent" else (255, 255, 255, 255))
            ground.alpha_composite(im)
            h = 600
            ground = ground.convert("RGB").resize((int(im.width * h / im.height), h), cr.Image.LANCZOS)
            buf = io.BytesIO(); ground.save(buf, "PNG")
            self._card_photo = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
            preview.configure(image=self._card_photo)
            n = len(state["pages"])
            page_lbl.set(f"Card {state['page'] + 1} of {n}" + (" (the text ran onto more cards)" if n > 1 else ""))

        for w, _t in combos.values():
            w.var.trace_add("write", refresh)

        def other_doodles():
            state["variant"] += 1
            refresh()

        def turn(step):
            state["page"] = max(0, min(len(state["pages"]) - 1, state["page"] + step))
            refresh()

        def base_name():
            return re.sub(r"[^A-Za-z0-9_-]+", "_", card["title"]).strip("_") or "card"

        def save_png():
            k = keys()
            path = filedialog.asksaveasfilename(parent=win, defaultextension=".png", initialfile=base_name() + ".png",
                                                filetypes=[("PNG image", "*.png")])
            if path:
                try:
                    paths = cr.save(card, path, k["size"], k["background"], k["fill"], state["variant"])
                except OSError as e:
                    messagebox.showerror("Save", str(e), parent=win); return
                status.set(f"Saved {len(paths)} PNG file{'s' if len(paths) != 1 else ''}: {paths[0]}")
                self.last_roll.set(f"Saved the card for {card['title']} to {paths[0]}")

        def save_sheet():
            k = keys()
            n = max(1, min(54, self._int_or_none(str(copies.get())) or 1))
            path = filedialog.asksaveasfilename(parent=win, defaultextension=".png", initialfile=base_name() + "_sheet.png",
                                                filetypes=[("PNG image", "*.png")])
            if path:
                try:
                    sheets = cr.print_sheet(state["pages"] * n, k["size"], path)
                except OSError as e:
                    messagebox.showerror("Save", str(e), parent=win); return
                status.set(f"Saved {len(sheets)} print sheet{'s' if len(sheets) != 1 else ''} (letter size, 300 dpi): {path}")

        bar = ttk.Frame(left); bar.grid(row=3, column=0, columnspan=2, sticky="we", pady=(10, 2))
        ttk.Button(bar, text="Different Doodles", command=other_doodles).pack(fill="x", pady=2)
        nav = ttk.Frame(bar); nav.pack(fill="x", pady=2)
        ttk.Button(nav, text="< Previous", command=lambda: turn(-1)).pack(side="left", expand=True, fill="x")
        ttk.Button(nav, text="Next >", command=lambda: turn(1)).pack(side="left", expand=True, fill="x")
        ttk.Label(bar, textvariable=page_lbl, foreground="#555").pack(anchor="w")
        ttk.Button(bar, text="Save PNG...", command=save_png).pack(fill="x", pady=(10, 2))
        sheet = ttk.Frame(bar); sheet.pack(fill="x", pady=2)
        ttk.Button(sheet, text="Save Print Sheet...", command=save_sheet).pack(side="left", fill="x", expand=True)
        ttk.Label(sheet, text="copies").pack(side="left", padx=(6, 2))
        ttk.Spinbox(sheet, from_=1, to=54, textvariable=copies, width=4).pack(side="left")
        ttk.Label(bar, foreground="#777", wraplength=240, justify="left", text=(
            "Poker is 2.5 x 3.5 inches, tarot 2.75 x 4.75. A print sheet is letter size with cut marks: 9 poker or 6 tarot "
            "cards. White prints best; Transparent keeps only the ink, for screens.")).pack(anchor="w", pady=6)
        if not cr.handwriting_found():
            ttk.Label(bar, foreground="#9a5b00", wraplength=240, justify="left", text=(
                "Ink Free and Segoe Print weren't found on this computer, so the cards use a plain font.")).pack(anchor="w")
        ttk.Label(bar, textvariable=status, foreground="#1a5fb4", wraplength=240, justify="left").pack(anchor="w", pady=4)
        ttk.Button(bar, text="Close", command=win.destroy).pack(fill="x", pady=(8, 0))
        refresh()
        self.card_win = (win, combos, state, copies, save_png, save_sheet, other_doodles, turn)
        return win

    def _card_magic(self, item):
        if item is None:
            messagebox.showinfo("Select an item", "Generate or select an item first."); return
        cr = self._card_module()
        if cr is not None:
            self._card_dialog(cr.card_from_magic_item(item))

    def _magic_card_current(self):
        self._magic_commit_all()
        self._card_magic(self.magic_cur)

    def _cu_card(self):
        self._cu_preview()
        if self.cu_current is not None:
            self._card_magic(self.cu_current)

    def _card_by_name(self, cr, name, title=None, extra=(), footer_extra=(), price=None):
        """A card from rules text by item name: your data's entry for it, else a Custom Content item of that name, else None."""
        entry = None
        rowid = self.rules.resolve(f"item:{name}") if name else None
        if rowid:
            cand = self.rules.rule(rowid)
            if cand and cand.get("kind") == "item":
                entry = cand
        if entry is None:
            custom = next((i for i in self.c_items if i.name.lower() == str(name or "").lower()), None)
            if custom is not None:
                entry = custom_item_entry(custom)
        return cr.card_from_entry(entry, title, extra, footer_extra, price) if entry else None

    def _card_for_model_item(self, it):
        """A card for a models.Item (Treasure, Shops, Custom Content)."""
        cr = self._card_module()
        if cr is None:
            return None
        return self._card_by_name(cr, it.name) or cr.card_from_models_item(it)

    def _loot_card(self):
        sel = self.loot_tree.selection()
        if not sel:
            messagebox.showinfo("Select an item", "Select an item in the list first."); return
        kind, it, _val = self.current_loot[int(sel[0])]
        if it is None:
            messagebox.showinfo("Currency", "Coins don't get a card. Select an item."); return
        self._card_dialog(self._card_for_model_item(it))

    def _shop_card(self):
        sel = self._shop_selected()
        if not sel:
            messagebox.showinfo("Select an item", "Select an item in the shop first."); return
        self._card_dialog(self._card_for_model_item(self.shop.lines[sel[0]].item))

    def _item_card(self):
        sel = self.itree.selection()
        it = next((x for x in self.c_items if sel and x.name == self.itree.item(sel[0], "text")), None)
        if it is None:
            messagebox.showinfo("Select an item", "Select one of your items in the list first."); return
        self._card_dialog(self._card_for_model_item(it))

    def _pl_card_make(self):
        kind, r = self._pl_need()
        if r is None:
            return
        cr = self._card_module()
        if cr is None:
            return
        if kind == "entry" and r.get("magic_item"):
            self._card_dialog(cr.card_from_magic_item(r["magic_item"])); return
        extra, foot = [], []
        if kind == "pb" and r.get("value_gp"):
            extra.append(f"**Value** {ploot.coin_text(ploot.to_cp(r['value_gp']))}"
                         + (f" (base {ploot.coin_text(ploot.to_cp(r.get('base_gp', 0)))} and runes "
                            f"{ploot.coin_text(ploot.to_cp(r['rune_gp']))})" if r.get("rune_gp") else ""))
        if r.get("qty", 1) > 1:
            foot.append(f"x{r['qty']}")
        price = ploot.coin_text(ploot.to_cp(r["value_gp"])) if (kind == "pb" and r.get("value_gp")) else None
        card = self._card_by_name(cr, r.get("rules_name") or r["name"], r["name"] if kind == "pb" else None, extra, foot, price)
        if card is None:
            card = cr.card_basic(r["name"], r.get("level"), r.get("value_gp"), r.get("qty", 1), r.get("holder", ""),
                                 r.get("source", ""), r.get("notes", ""), extra)
        self._card_dialog(card)

    # ---------- Encounters ----------
    def _build_encounters(self):
        f = self.tab_enc
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)

        def lab(text, r, c):
            ttk.Label(top, text=text).grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 10, 4), pady=2)
        lab("Threat", 0, 0)
        self.threat = tk.StringVar(value="Moderate")
        ttk.Combobox(top, textvariable=self.threat, values=list(THREATS), state="readonly",
                     width=12).grid(row=0, column=1, sticky="w")
        lab("Rarity", 0, 2)
        self.enc_rar = RarityChecks(top); self.enc_rar.grid(row=0, column=3, columnspan=3, sticky="w")

        lab("Region", 1, 0)
        self.enc_region = Combo(top, values_key="regions", any_option=True, readonly=True, width=30)
        self.enc_region.grid(row=1, column=1, sticky="w")
        lab("Theme", 1, 2)
        self.enc_theme = Combo(top, list(THEMES), any_option=True, readonly=True, width=24)
        self.enc_theme.grid(row=1, column=3, sticky="w")
        lab("Creature type", 1, 4)
        self.enc_type = Combo(top, values_key="types", any_option=True, width=16)
        self.enc_type.grid(row=1, column=5, sticky="w")

        lab("Family", 2, 0)
        self.enc_family = Combo(top, values_key="families", any_option=True, width=30)
        self.enc_family.grid(row=2, column=1, sticky="w")
        lab("Book / source", 2, 2)
        self.enc_source = Combo(top, values_key="sources", any_option=True, width=24)
        self.enc_source.grid(row=2, column=3, sticky="w")
        lab("Size", 2, 4)
        self.enc_size = Combo(top, values_key="sizes", any_option=True, readonly=True, width=16)
        self.enc_size.grid(row=2, column=5, sticky="w")

        lab("Include traits", 3, 0)
        self.enc_inc = MultiField(top, values_key="traits", width=22, combo_width=14)
        self.enc_inc.grid(row=3, column=1, sticky="we")
        lab("Exclude traits", 3, 2)
        self.enc_exc = MultiField(top, values_key="traits", width=18, combo_width=12)
        self.enc_exc.grid(row=3, column=3, columnspan=3, sticky="w")

        lab("Grouping", 4, 0)
        self.enc_cohesion = Combo(top, list(COHESION), readonly=True, width=30)
        self.enc_cohesion.var.set(self.config_data.get("cohesion", "Prefer related creatures"))
        self.enc_cohesion.grid(row=4, column=1, sticky="w")
        lab("Name contains", 4, 2)
        self.enc_q = tk.StringVar(); ttk.Entry(top, textvariable=self.enc_q, width=26).grid(row=4, column=3, sticky="w")
        opts = ttk.Frame(top); opts.grid(row=4, column=4, columnspan=2, sticky="w", padx=(10, 0))
        self.enc_custom = tk.BooleanVar()
        ttk.Checkbutton(opts, text="Custom only", variable=self.enc_custom).pack(side="left")
        self.enc_variants = tk.BooleanVar(value=self.config_data.get("elite_weak_variants", False))
        ttk.Checkbutton(opts, text="Elite/Weak variants", variable=self.enc_variants).pack(side="left", padx=6)

        lab("Max creatures", 5, 0)
        self.enc_max = tk.IntVar(value=6)
        ttk.Spinbox(top, from_=1, to=20, textvariable=self.enc_max, width=5).grid(row=5, column=1, sticky="w")
        lab("Max creature types", 5, 2)
        self.enc_types = tk.IntVar(value=3)
        ttk.Spinbox(top, from_=1, to=8, textvariable=self.enc_types, width=5).grid(row=5, column=3, sticky="w")
        lab("Hazards", 6, 0)
        self.enc_hazards = Combo(top, list(HAZARD_MODES), readonly=True, width=30)
        self.enc_hazards.var.set(self.config_data.get("hazard_mode", "No hazards"))
        self.enc_hazards.grid(row=6, column=1, sticky="w")
        lab("Hazard type", 6, 2)
        self.enc_htype = Combo(top, values_key="hazard_traits", any_option=True, width=24)
        self.enc_htype.grid(row=6, column=3, sticky="w")
        lab("Max hazards", 6, 4)
        self.enc_maxhaz = tk.IntVar(value=self.config_data.get("max_hazards", 1))
        ttk.Spinbox(top, from_=0, to=4, textvariable=self.enc_maxhaz, width=5).grid(row=6, column=5, sticky="w")
        btns = ttk.Frame(top); btns.grid(row=5, column=4, columnspan=2, sticky="e")
        ttk.Button(btns, text="Clear Filters", command=self._clear_enc_filters).pack(side="left", padx=2)
        ttk.Button(btns, text="Generate Encounters", command=self._gen_enc).pack(side="left", padx=2)
        ttk.Button(btns, text="Copy Selected", command=self._copy_enc).pack(side="left", padx=2)
        ttk.Button(btns, text="Export Markdown...", command=self._export_enc).pack(side="left", padx=2)
        self.enc_info = tk.StringVar(); ttk.Label(f, textvariable=self.enc_info).pack(anchor="w", padx=10)

        pane = ttk.PanedWindow(f, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=6)
        left = ttk.Frame(pane); pane.add(left, weight=3)
        ebar = ttk.Frame(left); ebar.pack(fill="x")
        ttk.Button(ebar, text="Make Elite", command=lambda: self._adjust_selected("elite")).pack(side="left", padx=2, pady=2)
        ttk.Button(ebar, text="Make Weak", command=lambda: self._adjust_selected("weak")).pack(side="left", padx=2)
        ttk.Button(ebar, text="Make Normal", command=lambda: self._adjust_selected("")).pack(side="left", padx=2)
        ttk.Button(ebar, text="Related Creatures", command=self._related_dialog).pack(side="left", padx=(10, 2))
        ttk.Button(ebar, text="Build Around Selected", command=self._build_around_selected).pack(side="left", padx=2)
        ttk.Button(ebar, text="Apply Template...", command=self._enc_apply_template).pack(side="left", padx=(10, 2))
        ttk.Button(ebar, text="Send to Combat", command=self._send_to_combat).pack(side="right", padx=2)
        ttk.Button(ebar, text="Save to Session", command=self._save_to_session_dialog).pack(side="right", padx=2)
        cols = ("lvl", "xp", "hp", "ac", "traits")
        self.enc_tree = ttk.Treeview(left, columns=cols, show="tree headings")
        self.enc_tree.heading("#0", text="Encounter / Creature")
        for c, t, w in zip(cols, ("Lvl", "XP each", "HP", "AC", "Traits"), (40, 60, 50, 40, 200)):
            self.enc_tree.heading(c, text=t); self.enc_tree.column(c, width=w, anchor="w")
        self.enc_tree.column("#0", width=300)
        self.enc_tree.pack(fill="both", expand=True)
        self.enc_tree.bind("<<TreeviewSelect>>", lambda e: self._show_selected_creature())
        self.enc_tree.bind("<Double-1>", lambda e: self._popout_selected())

        right = ttk.Frame(pane); pane.add(right, weight=4)
        bar = ttk.Frame(right); bar.pack(fill="x")
        ttk.Label(bar, text="Blue text is clickable", foreground="#1a5fb4").pack(side="right", padx=6)
        ttk.Button(bar, text="Open in Window", command=self._popout_selected).pack(side="left", padx=2, pady=2)
        ttk.Button(bar, text="Copy Stat Block", command=self._copy_statblock).pack(side="left", padx=2)
        ttk.Button(bar, text="Duplicate to Custom", command=lambda: self._duplicate_to_custom(self._selected_creature())
                   ).pack(side="left", padx=2)
        ttk.Button(bar, text="Search on Archives of Nethys", command=self._open_aon).pack(side="left", padx=2)
        self.stat_view = RichText(right, self)
        self.stat_view.pack(fill="both", expand=True)
        self.stat_view.show_message("Select a creature to see its stat block. Click blue text for rules.")

    def _clear_enc_filters(self):
        for w in (self.enc_region, self.enc_theme, self.enc_type, self.enc_family, self.enc_source, self.enc_size):
            w.var.set(ANY)
        self.enc_inc.set(""); self.enc_exc.set(""); self.enc_q.set("")
        self.enc_htype.var.set(ANY)
        self.enc_custom.set(False)

    def _enc_spec(self):
        """Combined theme/region spec, or None. Both must match when both are set."""
        specs = []
        region = self.enc_region.value()
        if region:
            specs.append(next((r for r in self.regions if r["name"] == region), None))
        theme = self.enc_theme.value()
        if theme:
            specs.append(THEMES.get(theme))
        specs = [s for s in specs if s]
        if not specs:
            return None, {}
        bias = {}
        if region and specs[0].get("creatures"):
            names = {n.lower() for n in specs[0]["creatures"]}
            bias = {c.base_uid: 3.0 for c in self.all_creatures if c.name.lower() in names}
        if len(specs) == 1:
            return specs[0], bias
        return {"_all": specs}, bias

    def _enc_pool(self, pl, variants=None):
        spec, bias = self._enc_spec()
        size = SIZE_CODE.get(self.enc_size.value().lower(), "")
        all_specs = spec.get("_all") if spec else None
        pool = filter_pool(self.all_creatures, pl, self.enc_rar.get(), self.enc_inc.items(),
                           self.enc_exc.items(), self.enc_q.get(), self.enc_custom.get(),
                           variants=self.enc_variants.get() if variants is None else variants,
                           source=self.enc_source.value(), family=strip_count(self.enc_family.value()),
                           ctype=self.enc_type.value(), size=size,
                           spec=None if all_specs else spec,
                           hazards=HAZARD_MODES.get(self.enc_hazards.var.get(), "none"),
                           hazard_traits=[self.enc_htype.value()] if self.enc_htype.value() else None,
                           systems=self.systems())
        if all_specs:
            pool = [c for c in pool if c.is_hazard or all(matches_spec(c, s) for s in all_specs)]
        return pool, bias

    def _gen_enc(self, seed_creature=None):
        pl, ps = self.party_level(), self.party_size()
        self.config_data["elite_weak_variants"] = self.enc_variants.get()
        self.config_data["cohesion"] = self.enc_cohesion.var.get()
        self.config_data["hazard_mode"] = self.enc_hazards.var.get()
        self.config_data["max_hazards"] = int(self.enc_maxhaz.get())
        storage.save("config", self.config_data)
        pool, bias = self._enc_pool(pl)
        if seed_creature is not None and seed_creature.base_uid not in {c.base_uid for c in pool}:
            pool = pool + [seed_creature]
        cohesion = COHESION.get(self.enc_cohesion.var.get(), "related")
        self.encs = generate(pool, pl, ps, self.threat.get(), count=6,
                             max_creatures=int(self.enc_max.get()), max_types=int(self.enc_types.get()),
                             cohesion=cohesion, affinity=self.affinity, bias=bias, seed_creature=seed_creature,
                             max_hazards=int(self.enc_maxhaz.get()))
        self.enc_threat_used = self.threat.get()
        around = f", built around {seed_creature.display_name}" if seed_creature else ""
        warn = self._missing_system_warning()
        self.enc_info.set(f"{self.sys_var.get()} | Party level {pl}, {ps} PCs, {self.threat.get()}: "
                          f"{len(pool)} creatures match filters{around}" + (f"   {warn}" if warn else ""))
        self._draw_encounters()

    def _build_around_selected(self):
        c = self._selected_creature()
        if not c:
            messagebox.showinfo("Select a creature", "Select a creature first (here or from Related Creatures).")
            return
        self._gen_enc(seed_creature=c)

    def _related_dialog(self, creature=None):
        c = creature or self._selected_creature()
        if not c:
            messagebox.showinfo("Select a creature", "Select a creature in an encounter first.")
            return
        pl = self.party_level()
        rows = related(c, [x for x in self.all_creatures if self.in_systems(x)], self.affinity, party_level=pl)
        win = tk.Toplevel(self); win.title(f"Related to {c.display_name}"); win.geometry("760x460")
        ttk.Label(win, text=f"Creatures that share a family trait or come from the same book as {c.name}, "
                            f"within the level range for party level {pl}. Same-book matches from large "
                            "general bestiaries count for little.", wraplength=720, foreground="#555"
                  ).pack(anchor="w", padx=8, pady=4)
        tree = ttk.Treeview(win, columns=("lvl", "xp", "why"), show="tree headings")
        tree.heading("#0", text="Creature"); tree.column("#0", width=230)
        for col, t, w in (("lvl", "Lvl", 40), ("xp", "XP", 45), ("why", "Why related", 400)):
            tree.heading(col, text=t); tree.column(col, width=w)
        tree.pack(fill="both", expand=True, padx=8)
        lookup = {}
        for i, (r, score, why) in enumerate(rows):
            iid = str(i)
            tree.insert("", "end", iid=iid, text=r.name + (" (custom)" if r.custom else ""),
                        values=(r.level, xp_of(r, pl), "; ".join(why)))
            lookup[iid] = r
        if not rows:
            tree.insert("", "end", text="Nothing related found in range. Try another party level or creature.")
        def chosen():
            sel = tree.selection()
            return lookup.get(sel[0]) if sel else None

        def show():
            r = chosen()
            if r:
                self._popout_creature(r)

        def build(target):
            if target is None:
                messagebox.showinfo("Select a creature", "Select a row first.", parent=win); return
            win.destroy()
            self._gen_enc(seed_creature=target)
        bar = ttk.Frame(win); bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Stat Block", command=show).pack(side="left")
        ttk.Button(bar, text="Build Around Selected Row", command=lambda: build(chosen())).pack(side="right")
        ttk.Button(bar, text=f"Build Around {c.name}", command=lambda: build(c)).pack(side="right", padx=4)
        tree.bind("<Double-1>", lambda e: show())

    def _draw_encounters(self, select=None):
        pl = self.party_level()
        self.enc_tree.delete(*self.enc_tree.get_children())
        self.enc_rows.clear()
        if not self.encs:
            self.enc_tree.insert("", "end", text="No encounters found. Loosen filters or download data.")
            return
        for ei, e in enumerate(self.encs):
            label = f"Option {ei + 1}: {e.xp}/{e.budget} XP"
            pw = encounter_warnings(e.groups, self.details_for, self.party)
            warns = list(e.warnings) + [f"party: {n} {w[0]}" for n, w in pw.items()][:2]
            if warns:
                label += "  [" + "; ".join(warns) + "]"
            parent = self.enc_tree.insert("", "end", iid=f"e{ei}", text=label, open=True)
            for gi, (c, cnt) in enumerate(e.groups):
                xp = xp_of(c, pl)
                iid = self.enc_tree.insert(parent, "end", iid=f"e{ei}g{gi}",
                                           text=f"{cnt} x {c.display_name}" + self._tag_label(c),
                                           values=(c.level, "" if xp is None else xp, c.hp or "", c.ac or "",
                                                   ", ".join(c.traits)))
                self.enc_rows[iid] = (ei, gi)
        if select and self.enc_tree.exists(select):
            self.enc_tree.selection_set(select)
            self.enc_tree.see(select)

    @staticmethod
    def _tag_label(c):
        sf = " [SF]" if system_of(c) == "sf" else ""
        if c.is_hazard:
            return sf + (" (complex hazard)" if c.complex else " (hazard)")
        return sf + (" (custom)" if c.custom else "")

    def _selected_creature(self):
        sel = self.enc_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if iid not in self.enc_rows:
            kids = self.enc_tree.get_children(iid)     # encounter row: use its first creature
            iid = kids[0] if kids else None
        if iid not in self.enc_rows:
            return None
        ei, gi = self.enc_rows[iid]
        return self.encs[ei].groups[gi][0]

    def _selected_encounter_index(self):
        sel = self.enc_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if iid in self.enc_rows:
            return self.enc_rows[iid][0]
        return int(iid[1:]) if iid.startswith("e") and iid[1:].isdigit() else None

    def _adjust_selected(self, adjust):
        sel = self.enc_tree.selection()
        if not sel or sel[0] not in self.enc_rows:
            messagebox.showinfo("Select a creature", "Select a creature row (not the encounter row) first.")
            return
        ei, gi = self.enc_rows[sel[0]]
        enc = self.encs[ei]
        c, n = enc.groups[gi]
        if c.is_hazard and adjust:
            messagebox.showinfo("Hazard", "Elite and Weak adjustments don't apply to hazards.")
            return
        enc.groups[gi] = (make_variant(c, adjust), n)
        recompute(enc, self.party_level())
        self._draw_encounters(select=sel[0])
        self._show_selected_creature()

    def _show_selected_creature(self):
        c = self._selected_creature()
        if not c:
            return
        d = self.details_for(c)
        if d:
            segs = render(d)
            pw = creature_warnings(d, self.party)
            if pw:
                segs = [("Party check: " + "; ".join(pw) + "\n", "warn", None)] + segs
            self.stat_view.show(segs)
        else:
            self.stat_view.show_message(
                f"No stat block stored for {c.name}.\n\nClick Download / Update Data (or rebuild the index) "
                "on the Party & Data tab to add stat blocks.")

    def _popout_creature(self, c):
        d = self.details_for(c) if c else None
        if not d:
            return
        win = tk.Toplevel(self); win.title(d["name"]); win.geometry("620x720")
        v = RichText(win, self); v.pack(fill="both", expand=True); v.show(render(d))

    def _popout_selected(self):
        self._popout_creature(self._selected_creature())

    def _copy_statblock(self):
        c = self._selected_creature()
        d = self.details_for(c) if c else None
        if d:
            self.clipboard_clear(); self.clipboard_append(render_text(d))

    def _open_aon(self):
        c = self._selected_creature()
        if c and not c.custom:
            webbrowser.open(AON_SEARCH.format(q=urllib.parse.quote(c.name)))

    def _copy_enc(self):
        ei = self._selected_encounter_index()
        if ei is None:
            return
        e = self.encs[ei]
        lines = [f"Encounter: {e.xp}/{e.budget} XP"]
        for c, n in e.groups:
            lines.append(f"  {n} x {c.display_name}{self._tag_label(c)} (L{c.level}, HP {c.hp or '?'}, AC {c.ac or '?'})")
        self.clipboard_clear(); self.clipboard_append("\n".join(lines))

    def _save_text(self, text, name):
        p = filedialog.asksaveasfilename(defaultextension=".md", initialfile=name,
                                         filetypes=[("Markdown", "*.md"), ("Text", "*.txt")])
        if p:
            Path(p).write_text(text, encoding="utf-8")
            self.last_roll.set(f"Exported to {p}")

    def _export_enc(self):
        ei = self._selected_encounter_index()
        if ei is None:
            messagebox.showinfo("Select an encounter", "Select an encounter first."); return
        e = self.encs[ei]
        text = exporter.encounter_md(f"Encounter {ei + 1}", e.groups, self.details_for, e.xp, e.budget,
                                     getattr(self, "enc_threat_used", ""))
        self._save_text(text, f"encounter_{ei + 1}.md")

    def _send_to_combat(self):
        ei = self._selected_encounter_index()
        if ei is None:
            messagebox.showinfo("Select an encounter", "Select an encounter (or any creature in it) first.")
            return
        for c, n in self.encs[ei].groups:
            for _ in range(n):
                self._add_creature_to_combat(c)
        self._combat_changed()
        self.nb.select(self.tab_combat)

    # ---------- Combat ----------
    def _build_combat(self):
        f = self.tab_combat
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        self.turn_var = tk.StringVar()
        ttk.Label(top, textvariable=self.turn_var, font=("TkDefaultFont", 12, "bold")).pack(side="left", padx=4)
        for text, cmd in (("Clear Combat", self._clear_combat), ("Remove", self._remove_combatant),
                          ("Add Other...", self._add_other_dialog), ("Add Creature...", self._add_creature_dialog),
                          ("Add Party", self._add_party_to_combat), ("Set Initiative", self._set_init_dialog),
                          ("Roll Initiative", self._roll_init), ("Next Turn >", self._next_turn)):
            ttk.Button(top, text=text, command=cmd).pack(side="right", padx=2)

        pane = ttk.PanedWindow(f, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=3)
        cols = ("init", "hp", "ac", "cond")
        self.cb_tree = ttk.Treeview(left, columns=cols, show="tree headings", height=12)
        self.cb_tree.heading("#0", text="Combatant"); self.cb_tree.column("#0", width=200)
        for c, t, w in zip(cols, ("Init", "HP", "AC", "Conditions"), (50, 80, 90, 260)):
            self.cb_tree.heading(c, text=t); self.cb_tree.column(c, width=w, anchor="w")
        self.cb_tree.tag_configure("current", background="#fff2c2", font=("TkDefaultFont", 10, "bold"))
        self.cb_tree.tag_configure("defeated", foreground="#999")
        self.cb_tree.tag_configure("pc", foreground="#1a5f2a")
        self.cb_tree.pack(fill="both", expand=True)
        self.cb_tree.bind("<<TreeviewSelect>>", lambda e: self._show_combatant())
        self.cb_tree.bind("<Double-1>", lambda e: self._popout_combatant())

        ctl = ttk.Frame(left); ctl.pack(fill="x", pady=4)
        ttk.Label(ctl, text="Amount").grid(row=0, column=0, sticky="w")
        self.hp_amt = tk.StringVar()
        e = ttk.Entry(ctl, textvariable=self.hp_amt, width=6); e.grid(row=0, column=1, sticky="w")
        e.bind("<Return>", lambda ev: self._apply_hp(-1))
        ttk.Button(ctl, text="Damage", command=lambda: self._apply_hp(-1)).grid(row=0, column=2, padx=2)
        ttk.Button(ctl, text="Heal", command=lambda: self._apply_hp(1)).grid(row=0, column=3, padx=2)
        ttk.Label(ctl, text="Type").grid(row=0, column=4, sticky="e")
        self.hp_type = tk.StringVar()
        ttk.Combobox(ctl, textvariable=self.hp_type, width=12,
                     values=["", "bludgeoning", "piercing", "slashing", "acid", "cold", "electricity", "fire",
                             "sonic", "force", "mental", "poison", "bleed", "spirit", "vitality", "void",
                             "precision"]).grid(row=0, column=5, sticky="w")
        ttk.Label(ctl, text="Condition").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.cond_var = tk.StringVar(value="frightened")
        ttk.Combobox(ctl, textvariable=self.cond_var, values=ALL_CONDITIONS, width=18).grid(row=1, column=1, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(ctl, text="Value").grid(row=1, column=3, sticky="e", pady=(6, 0))
        self.cond_val = tk.StringVar(value="1")
        ttk.Entry(ctl, textvariable=self.cond_val, width=12).grid(row=1, column=4, sticky="w", pady=(6, 0))
        ttk.Button(ctl, text="Add Condition", command=self._add_condition).grid(row=1, column=5, padx=4, pady=(6, 0))
        ttk.Label(ctl, text="(value: number, or damage like 1d6 fire for persistent; a damage Type applies "
                            "immunities, weaknesses, resistances)", foreground="#777").grid(
            row=2, column=1, columnspan=5, sticky="w")
        cl = ttk.Frame(left); cl.pack(fill="x")
        self.cond_list = tk.Listbox(cl, height=4)
        self.cond_list.pack(side="left", fill="x", expand=True)
        self.cond_list.bind("<Double-1>", lambda e: self._cond_rules())
        cb = ttk.Frame(cl); cb.pack(side="left", padx=4)
        ttk.Button(cb, text="Remove Condition", command=self._remove_condition).pack(fill="x")
        ttk.Button(cb, text="Rules (double-click)", command=self._cond_rules).pack(fill="x", pady=2)

        tgt = ttk.LabelFrame(left, text="Targeting (attack rolls resolve against the target's effective AC)")
        tgt.pack(fill="x", pady=4)
        ttk.Label(tgt, text="Target").grid(row=0, column=0, sticky="w", padx=4)
        self.target_var = tk.StringVar(value="(none)")
        self.target_combo = ttk.Combobox(tgt, textvariable=self.target_var, state="readonly", width=26)
        self.target_combo.grid(row=0, column=1, sticky="w")
        ttk.Button(tgt, text="Target Selected", command=self._target_selected).grid(row=0, column=2, padx=4)
        self.apply_info = tk.StringVar(value="Roll damage, then apply it here.")
        self.apply_dmg_btn = ttk.Button(tgt, text="Apply Last Damage", command=lambda: self._apply_last(False))
        self.apply_dmg_btn.grid(row=1, column=1, sticky="w", pady=2)
        ttk.Button(tgt, text="Apply Last Crit", command=lambda: self._apply_last(True)).grid(row=1, column=2, padx=4)
        ttk.Label(tgt, textvariable=self.apply_info, foreground="#777").grid(row=2, column=0, columnspan=4, sticky="w", padx=4)
        ttk.Button(tgt, text="Save Effect...", command=self._save_effect_dialog).grid(row=0, column=3, padx=4)
        ttk.Button(tgt, text="Timed Effect...", command=self._timed_effect_dialog).grid(row=1, column=3, padx=4)
        opt = ttk.Frame(left); opt.pack(fill="x")
        self.auto_pers = tk.BooleanVar(value=self.combat.auto_persistent)
        ttk.Checkbutton(opt, text="Roll persistent damage and flat checks automatically", variable=self.auto_pers,
                        command=self._toggle_auto_pers).pack(side="left")
        ttk.Button(opt, text="Assisted Recovery (DC 10 this turn)", command=self._assisted).pack(side="left", padx=6)
        ttk.Button(opt, text="Bonus / Penalty...", command=self._bonus_dialog).pack(side="left", padx=2)
        ttk.Button(opt, text="Extra Damage...", command=self._riders_dialog).pack(side="left", padx=2)
        ttk.Button(opt, text="Defenses...", command=self._defenses_dialog).pack(side="left", padx=2)
        ttk.Button(opt, text="Resources...", command=self._combat_resources).pack(side="left", padx=2)
        ttk.Label(left, text="Log").pack(anchor="w", pady=(6, 0))
        self.log_text = tk.Text(left, height=8, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        self.log_text.pack(fill="both", expand=True)

        self.cb_view = RichText(pane, self); pane.add(self.cb_view, weight=4)
        self.cb_view.show_message("Select a combatant to see its stat block. Its conditions are applied to every "
                                  "number and roll (frightened, sickened, clumsy, enfeebled, drained, stupefied, "
                                  "fatigued, unconscious, prone, off-guard). Click a green number for the breakdown.")
        self._refresh_combat()

    def _combat_changed(self):
        storage.save("combat", self.combat.to_dict())
        self._refresh_combat()

    def _refresh_combat(self):
        cs = self.combat
        sel = self.cb_tree.selection()
        self.cb_tree.delete(*self.cb_tree.get_children())
        cur = cs.current()
        for c in cs.combatants:
            ac, why = c.effective_ac()
            ac_txt = "" if ac is None else (f"{ac} ({c.ac})" if why else str(ac))
            hp_txt = "" if c.hp is None else f"{c.hp}/{c.max_hp}"
            tags = []
            if cur and c.id == cur.id:
                tags.append("current")
            if c.defeated:
                tags.append("defeated")
            elif c.kind == "pc":
                tags.append("pc")
            self.cb_tree.insert("", "end", iid=str(c.id), text=("> " if "current" in tags else "") + c.name,
                                values=("" if c.init is None else c.init, hp_txt, ac_txt, c.condition_text()),
                                tags=tags)
        for s in sel:
            if self.cb_tree.exists(s):
                self.cb_tree.selection_set(s)
        if hasattr(self, "target_combo"):
            names = ["(none)"] + [c.name for c in cs.combatants]
            self.target_combo["values"] = names
            if self.target_var.get() not in names:
                self.target_var.set("(none)")
        self.turn_var.set(f"Round {cs.round}: {cur.name}'s turn" if cur else
                          "Not started: add combatants, roll initiative, then Next Turn")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(cs.log[-80:]))
        self.log_text.configure(state="disabled")
        self.log_text.see("end")
        self._refresh_cond_list()
        self._refresh_combat_views()

    def _selected_combatant(self):
        sel = self.cb_tree.selection()
        return self.combat.get(int(sel[0])) if sel else None

    def _pc_data_for(self, c):
        """Pathbuilder character data behind a combatant: a notebook page (uid 'N|<page id>'), a party
        member, or a PC/NPC page with the same name."""
        if c.uid.startswith("N|"):
            p = self._page(c.uid[2:])
            return p.get("pc") if p else None
        pc = next((x for x in self.party if x["name"] == (c.pc_key or c.name)), None)
        if pc:
            return pc
        p = next((x for x in self.notebook if x.get("pc") and x["title"].lower() == c.name.lower()), None)
        return p.get("pc") if p else None

    def _combatant_details(self, c):
        if c and (c.kind == "pc" or c.uid.startswith("N|")):
            pc = self._pc_data_for(c)
            has = pc and (pc.get("skills") or pc.get("saves") or pc.get("strikes")
                          or (pc.get("state") or {}).get("manual_strikes"))
            return self._pc_stat(pc) if has else None
        if not c or not c.uid:
            return None
        if c.uid.startswith("C|"):
            name = c.uid.split("|")[1]
            base = next((x for x in self.c_creatures if x.name == name), None)
            d = custom_details(base) if base else None
        else:
            d = self.details_db.get(c.uid)
        return apply_adjustment(d, c.adjust) if d else None

    def _show_combatant(self):
        c = self._selected_combatant()
        self._refresh_cond_list()
        if not c:
            return
        self.cb_view.show(self._combatant_segments(c))

    def _combatant_segments(self, c):
        """Stat block for a combatant with its current conditions applied to every number and roll."""
        d = self._combatant_details(c)
        if d:
            return render(d, who=c.name, conds=c.conditions, bonuses=c.bonuses, riders=c.riders)
        ac, why = c.effective_ac()
        lines = [(c.name, "title", None), ("\n", "body", None)]
        if c.conditions:
            lines.append(("Conditions: " + c.condition_text() + "\n", "warn", None))
        if c.bonuses:
            lines.append(("Bonuses/penalties: " + ", ".join(f"{b['label']} {b['value']:+d} {b['type']} to "
                                                             f"{b['applies']}" for b in c.bonuses) + "\n", "warn", None))
        lines.append((f"Initiative {c.init if c.init is not None else '-'}   Perception ", "body", None))
        if c.perception is not None:
            m = [("Perception", c.perception)] + c.mods("perception")
            tot = sum(v for _, v in m)
            lines.append((f"{tot:+d}", "body", dice.make_ref("check", "Perception", f"{tot:+d}", c.name, mods=m)))
        lines.append(("\n", "body", None))
        lines.append((f"HP {c.hp}/{c.max_hp}   AC {ac}" + (f" (base {c.ac}; {', '.join(why)})" if why else "")
                      + "\n", "body", None))
        for save in ("fortitude", "reflex", "will"):
            if save in (c.saves or {}):
                m = [(save.title(), c.saves[save])] + c.mods("save", save)
                tot = sum(v for _, v in m)
                lines.append((f"{save.title()} {tot:+d}", "body",
                              dice.make_ref("check", save.title(), f"{tot:+d}", c.name, mods=m)))
                lines.append(("   ", "body", None))
        lines.append(("\n", "body", None))
        return lines

    def _popout_combatant(self):
        c = self._selected_combatant()
        if not c:
            return
        win = tk.Toplevel(self); win.title(c.name); win.geometry("620x720")
        v = RichText(win, self); v.pack(fill="both", expand=True); v.show(self._combatant_segments(c))
        self.combat_popouts.append((win, v, c.id))   # refreshed whenever conditions or HP change

    def _refresh_combat_views(self):
        c = self._selected_combatant()
        if c and hasattr(self, "cb_view"):
            top = self.cb_view.text.yview()[0] if hasattr(self.cb_view.text, "yview") else 0
            self.cb_view.show(self._combatant_segments(c))
            try:
                self.cb_view.text.yview_moveto(top)
            except Exception:
                pass
        keep = []
        for win, view, cid in getattr(self, "combat_popouts", []):
            try:
                alive = win.winfo_exists()
            except Exception:
                alive = False
            cc = self.combat.get(cid)
            if alive and cc:
                view.show(self._combatant_segments(cc))
                keep.append((win, view, cid))
        self.combat_popouts = keep

    def _refresh_cond_list(self):
        if not hasattr(self, "cond_list"):
            return
        self.cond_list.delete(0, "end")
        c = self._selected_combatant()
        self._cond_keys = []
        if c:
            for k in sorted(c.conditions):
                v = c.conditions[k]
                self._cond_keys.append(k)
                self.cond_list.insert("end", f"persistent {v}" if k.startswith("persistent")
                                      else f"{k} {v}" if isinstance(v, int) else k)
            for i, b in enumerate(c.bonuses):
                self._cond_keys.append(("bonus", i))
                self.cond_list.insert("end", f"[bonus] {b['label']} {b['value']:+d} {b['type']} to {b['applies']}"
                                      + (f" ({b['rounds']} rd)" if b.get("rounds") else ""))
            for i, e in enumerate(c.effects):
                self._cond_keys.append(("effect", i))
                src = self.combat.get(e.get("source")) if e.get("source") else None
                self.cond_list.insert("end", f"[effect] {e['name']} ({e['rounds']} rd"
                                      + (f", from {src.name}" if src else "") + ")")

    def _add_creature_to_combat(self, c):
        d = self.details_for(c)
        per = None
        if c.is_hazard:
            per = d.get("stealth") if d else None
            name = c.display_name + (" (hazard)" if not c.complex else "")
            self.combat.add(name, kind="creature", perception=per, hp=d.get("hp") if d else c.hp,
                            ac=d.get("ac") if d else c.ac, uid=c.base_uid, saves=self._saves_from(d),
                            iwr=parse_iwr(d), hardness=(d or {}).get("hardness"),
                            notes="Complex hazard: initiative uses Stealth" if c.complex else
                            "Simple hazard: triggers once; remove after it resolves")
            return
        if d and d.get("perception"):
            try:
                per = int(str(d["perception"]).split()[0])
            except ValueError:
                per = None
        hp = d.get("hp") if d and d.get("hp") is not None else c.hp
        ac = d.get("ac") if d and d.get("ac") is not None else c.ac
        self.combat.add(c.display_name, kind="creature", perception=per, hp=hp, ac=ac,
                        uid=c.base_uid, adjust=c.adjust, saves=self._saves_from(d), iwr=parse_iwr(d))

    def _ensure_iwr(self, c):
        """Fill immunities/weaknesses/resistances for combatants added before this was tracked."""
        if not c:
            return
        if c.kind == "pc" or c.uid.startswith("N|"):
            d = self._combatant_details(c)      # characters: always rebuilt, so edits to defenses apply at once
            if d:
                c.iwr = parse_iwr(d)
            return
        if not c.iwr:
            d = self._combatant_details(c)
            if d:
                c.iwr = parse_iwr(d)
                if c.hardness is None and d.get("hardness") is not None:
                    c.hardness = d.get("hardness")

    @staticmethod
    def _saves_from(d):
        out = {}
        for name, val in re.findall(r"(Fort|Ref|Will)\s+([+-]\d+)", (d or {}).get("saves") or ""):
            out[{"Fort": "fortitude", "Ref": "reflex", "Will": "will"}[name]] = int(val)
        return out

    def _add_party_to_combat(self):
        present = {c.name for c in self.combat.combatants}
        for pc in self.party:
            if pc["name"] in present:
                continue
            comb = self.combat.add(pc["name"], kind="pc", perception=pc.get("perception"),
                                   hp=pc.get("hp"), ac=pc.get("ac"), saves=dict(pc.get("saves") or {}),
                                   pc_key=pc["name"])
            self._setup_pc_combatant(comb, pc)
        self._combat_changed()

    def _add_creature_dialog(self):
        win = tk.Toplevel(self); win.title("Add creature"); win.geometry("460x420")
        q = tk.StringVar()
        top = ttk.Frame(win); top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Search").pack(side="left")
        ent = ttk.Entry(top, textvariable=q); ent.pack(side="left", fill="x", expand=True, padx=4)
        lb = tk.Listbox(win); lb.pack(fill="both", expand=True, padx=6)
        bot = ttk.Frame(win); bot.pack(fill="x", padx=6, pady=6)
        adj = tk.StringVar(value="Normal")
        ttk.Combobox(bot, textvariable=adj, values=["Normal", "Elite", "Weak"], state="readonly", width=8).pack(side="left")
        ttk.Label(bot, text="Count").pack(side="left", padx=(8, 2))
        cnt = tk.IntVar(value=1); ttk.Spinbox(bot, from_=1, to=20, textvariable=cnt, width=4).pack(side="left")
        matches = []

        def search(*_):
            text = q.get().lower().strip()
            lb.delete(0, "end"); matches.clear()
            if len(text) < 2:
                return
            for c in sorted((x for x in self.all_creatures if self.in_systems(x)), key=lambda x: (x.name, x.level)):
                if text in c.name.lower():
                    matches.append(c)
                    lb.insert("end", f"{c.name} (L{c.level})" + self._tag_label(c))
                    if len(matches) >= 100:
                        break
        q.trace_add("write", search)

        def add():
            sel = lb.curselection()
            if not sel:
                return
            c = matches[sel[0]]
            c = make_variant(c, {"Elite": "elite", "Weak": "weak"}.get(adj.get(), ""))
            for _ in range(max(1, int(cnt.get()))):
                self._add_creature_to_combat(c)
            self._combat_changed()
        ttk.Button(bot, text="Add", command=add).pack(side="right")
        lb.bind("<Double-1>", lambda e: add())
        ent.focus_set()

    def _add_other_dialog(self):
        win = tk.Toplevel(self); win.title("Add combatant")
        fields = [("name", "Name"), ("init", "Initiative (optional)"), ("perception", "Perception mod"),
                  ("hp", "HP"), ("ac", "AC")]
        vars_ = {}
        for r, (k, label) in enumerate(fields):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=4, pady=2)
            vars_[k] = tk.StringVar(); ttk.Entry(win, textvariable=vars_[k]).grid(row=r, column=1, padx=4, pady=2)
        is_pc = tk.BooleanVar()
        ttk.Checkbutton(win, text="Ally / PC", variable=is_pc).grid(row=len(fields), column=1, sticky="w")

        def ok():
            if not vars_["name"].get().strip():
                return
            iv = {k: self._int_or_none(vars_[k].get()) for k in ("init", "perception", "hp", "ac")}
            self.combat.add(vars_["name"].get().strip(), kind="pc" if is_pc.get() else "creature", **iv)
            self.combat.sort()
            self._combat_changed(); win.destroy()
        ttk.Button(win, text="Add", command=ok).grid(row=len(fields) + 1, column=1, sticky="e", padx=4, pady=6)

    def _roll_init(self):
        missing_pcs = [c.name for c in self.combat.combatants
                       if c.init is None and c.perception is None]
        self.combat.roll_initiative()
        self._combat_changed()
        if missing_pcs:
            messagebox.showinfo("Initiative needed",
                                "No Perception for: " + ", ".join(missing_pcs) +
                                "\nUse Set Initiative to enter what they rolled.")

    def _set_init_dialog(self):
        c = self._selected_combatant()
        if not c:
            messagebox.showinfo("Select", "Select a combatant first."); return
        win = tk.Toplevel(self); win.title(f"Initiative: {c.name}")
        v = tk.StringVar(value="" if c.init is None else str(c.init))
        ttk.Label(win, text=f"{c.name} initiative total").pack(padx=8, pady=4)
        e = ttk.Entry(win, textvariable=v, width=8); e.pack(padx=8); e.focus_set()

        def ok(*_):
            c.init = self._int_or_none(v.get())
            self.combat.sort(); self._combat_changed(); win.destroy()
        e.bind("<Return>", ok)
        ttk.Button(win, text="Set", command=ok).pack(pady=6)

    def _next_turn(self):
        if not self.combat.combatants:
            return
        self.combat.next_turn()
        self._combat_changed()
        cur = self.combat.current()
        if cur and self.cb_tree.exists(str(cur.id)):
            self.cb_tree.selection_set(str(cur.id)); self.cb_tree.see(str(cur.id))

    def _apply_hp(self, sign):
        c = self._selected_combatant()
        amt = self._int_or_none(self.hp_amt.get())
        if not c or not amt:
            return
        if c.hp is None:
            messagebox.showinfo("No HP", f"{c.name} has no HP set."); return
        if sign < 0 and self.hp_type.get().strip():
            self._ensure_iwr(c)
            self.combat.apply_damage(c.id, [(abs(amt), self.hp_type.get().strip())])
        else:
            (self.combat.damage if sign < 0 else self.combat.heal)(c.id, abs(amt))
        self.hp_amt.set("")
        self._combat_changed()

    def _add_condition(self):
        c = self._selected_combatant()
        name = self.cond_var.get().strip().lower()
        if not c or not name:
            return
        self.combat.set_condition(c.id, name, self.cond_val.get().strip())
        self._combat_changed()

    def _remove_condition(self):
        c = self._selected_combatant()
        sel = self.cond_list.curselection()
        if c and sel:
            key = self._cond_keys[sel[0]]
            if isinstance(key, tuple) and key[0] == "bonus":
                self.combat.remove_bonus(c.id, key[1])
            elif isinstance(key, tuple):
                self.combat.remove_effect(c.id, key[1])
            else:
                self.combat.remove_condition(c.id, key)
            self._combat_changed()

    def _cond_rules(self):
        sel = self.cond_list.curselection()
        if sel:
            key = self._cond_keys[sel[0]]
            if isinstance(key, tuple):
                return
            self.open_ref("name:persistent damage" if key.startswith("persistent") else f"name:{key}")
        elif self.cond_var.get():
            self.open_ref(f"name:{self.cond_var.get()}")

    def _target(self):
        name = self.target_var.get()
        return next((c for c in self.combat.combatants if c.name == name), None)

    def _target_selected(self):
        c = self._selected_combatant()
        if c:
            self.target_var.set(c.name)

    def _apply_last(self, crit):
        t = self._target()
        if not t:
            messagebox.showinfo("No target", "Pick a target first."); return
        if not self.last_damage:
            messagebox.showinfo("No damage", "Click a damage roll in a stat block first."); return
        ld = self.last_damage
        if t.hp is None:
            messagebox.showinfo("No HP", f"{t.name} has no HP set."); return
        self._ensure_iwr(t)
        immune_crit = "critical-hits" in (t.iwr or {}).get("immune", [])
        parts = ld["crit_parts"] if crit and not immune_crit else ld["parts"]
        if crit and not ld["crit_parts"]:
            return
        lines = self.combat.apply_damage(t.id, parts, crit, ld.get("persist") or [])
        self.apply_info.set(" | ".join(lines[:3]))
        self._combat_changed()

    def _toggle_auto_pers(self):
        self.combat.auto_persistent = self.auto_pers.get()
        self._combat_changed()

    def _assisted(self):
        c = self._selected_combatant()
        if not c:
            return
        keys = [k for k in c.conditions if k.startswith("persistent")]
        if not keys:
            messagebox.showinfo("No persistent damage", f"{c.name} has no persistent damage."); return
        self.combat.assisted.update(keys)
        self.combat._log(f"{c.name}: assisted recovery, flat check DC 10 at end of turn")
        self._combat_changed()

    def _save_effect_dialog(self):
        cs = self.combat.combatants
        if not cs:
            return
        win = tk.Toplevel(self); win.title("Save effect")
        save = tk.StringVar(value="reflex"); dc = tk.StringVar(); basic = tk.BooleanVar()
        dmg = tk.StringVar()
        src = self._selected_combatant()
        ttk.Label(win, text="Save").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        ttk.Combobox(win, textvariable=save, values=["fortitude", "reflex", "will"], state="readonly",
                     width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(win, text="DC").grid(row=1, column=0, sticky="w", padx=6)
        ttk.Entry(win, textvariable=dc, width=6).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(win, text="Basic save", variable=basic).grid(row=2, column=1, sticky="w")
        ttk.Label(win, text="Damage (optional, e.g. 6d6 fire)").grid(row=3, column=0, sticky="w", padx=6)
        ttk.Entry(win, textvariable=dmg, width=18).grid(row=3, column=1, sticky="w")
        ttk.Label(win, text="Targets (Ctrl-click for several)").grid(row=4, column=0, columnspan=2, sticky="w", padx=6)
        lb = tk.Listbox(win, selectmode="extended", height=min(10, len(cs)), exportselection=False)
        for c in cs:
            lb.insert("end", c.name)
        lb.grid(row=5, column=0, columnspan=2, sticky="we", padx=6)
        out = tk.Text(win, height=8, width=60, state="disabled"); out.grid(row=7, column=0, columnspan=2, padx=6, pady=4)

        def roll_it():
            n = self._int_or_none(dc.get())
            if n is None:
                messagebox.showwarning("DC", "Enter a DC.", parent=win); return
            ids = [cs[i].id for i in lb.curselection()]
            rolled = dice.roll(dice.make_ref("damage", "", dmg.get())) if dmg.get().strip() else None
            lines = []
            if rolled and rolled.get("total") is not None:
                lines.append(f"Damage rolled: {rolled['total']}")
            for cid in ids:
                d, msg = self.combat.save_vs(cid, save.get(), n, basic=basic.get())
                lines.append(msg)
                if d is not None and rolled and rolled.get("total") is not None and basic.get():
                    factor = {3: 0, 2: 0.5, 1: 1, 0: 2}[d]
                    if factor:
                        parts = [(int(n * factor), t) for n, t in (rolled.get("damage_parts")
                                                                    or [(rolled["total"], "")])]
                        self._ensure_iwr(self.combat.get(cid))
                        lines += self.combat.apply_damage(cid, parts)
            out.configure(state="normal"); out.delete("1.0", "end"); out.insert("end", "\n".join(lines))
            out.configure(state="disabled")
            self._combat_changed()
        ttk.Button(win, text="Roll Saves" + (f" (source: {src.name})" if src else ""), command=roll_it).grid(
            row=6, column=1, sticky="e", padx=6, pady=4)

    def _timed_effect_dialog(self):
        cs = self.combat.combatants
        c = self._selected_combatant()
        if not c:
            messagebox.showinfo("Select", "Select the combatant the effect is on."); return
        win = tk.Toplevel(self); win.title(f"Timed effect on {c.name}")
        name = tk.StringVar(); rounds = tk.StringVar(value="1"); note = tk.StringVar()
        src = tk.StringVar(value=(self.combat.current().name if self.combat.current() else "(none)"))
        cond = tk.StringVar(); val = tk.StringVar(value="1")
        rows = [("Effect name", ttk.Entry(win, textvariable=name, width=28)),
                ("Rounds (1 minute = 10)", ttk.Entry(win, textvariable=rounds, width=6)),
                ("Source (counts down on its turn)", ttk.Combobox(win, textvariable=src, state="readonly",
                                                                 values=["(none)"] + [x.name for x in cs], width=24)),
                ("Condition (removed when it ends)", ttk.Combobox(win, textvariable=cond, values=[""] + ALL_CONDITIONS, width=20)),
                ("Condition value", ttk.Entry(win, textvariable=val, width=6)),
                ("Note shown when it ends", ttk.Entry(win, textvariable=note, width=28))]
        for r, (label, w) in enumerate(rows):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            w.grid(row=r, column=1, sticky="w", padx=6)
        ttk.Label(win, text="With a source, it ticks down at the start of the source's turn (spell durations). "
                            "Without one, at the end of this combatant's turn.", wraplength=380,
                  foreground="#777").grid(row=len(rows), column=0, columnspan=2, padx=6)

        def ok():
            n = self._int_or_none(rounds.get()) or 1
            label = name.get().strip() or (cond.get() or "Effect")
            source = next((x.id for x in cs if x.name == src.get()), None)
            note_txt = note.get().strip()
            cname = cond.get().strip().lower() or None
            if cname:
                self.combat.set_condition(c.id, cname, val.get())
            self.combat.add_effect(c.id, label, n, source, note_txt, condition=cname)
            self._combat_changed(); win.destroy()
        ttk.Button(win, text="Add", command=ok).grid(row=len(rows) + 1, column=1, sticky="e", padx=6, pady=6)

    def _bonus_dialog(self):
        c = self._selected_combatant()
        if not c:
            messagebox.showinfo("Select", "Select the combatant who gets the bonus or penalty."); return
        cs = self.combat.combatants
        win = tk.Toplevel(self); win.title(f"Bonus / penalty on {c.name}"); win.transient(self)
        preset = tk.StringVar(value="(custom)")
        label = tk.StringVar(value="Cover"); btype = tk.StringVar(value="circumstance"); val = tk.StringVar(value="2")
        applies = tk.StringVar(value="AC"); rounds = tk.StringVar(value="0")
        src = tk.StringVar(value="(none)")
        pre = ttk.Combobox(win, textvariable=preset, state="readonly", width=44,
                           values=["(custom)"] + list(BONUS_PRESETS))
        rows = [("Preset", pre), ("Name", ttk.Entry(win, textvariable=label, width=28)),
                ("Type", ttk.Combobox(win, textvariable=btype, values=BONUS_TYPES, state="readonly", width=14)),
                ("Value (negative = penalty)", ttk.Entry(win, textvariable=val, width=6)),
                ("Applies to", ttk.Combobox(win, textvariable=applies, values=list(BONUS_TARGETS), state="readonly",
                                            width=22)),
                ("Rounds (0 = until removed)", ttk.Entry(win, textvariable=rounds, width=6)),
                ("Counts down on whose turn", ttk.Combobox(win, textvariable=src, state="readonly", width=24,
                                                           values=["(none)"] + [x.name for x in cs]))]
        for r, (lab, w) in enumerate(rows):
            ttk.Label(win, text=lab).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            w.grid(row=r, column=1, sticky="w", padx=6)
        ttk.Label(win, text="Same-type bonuses don't stack (highest applies); penalties likewise. Untyped stack. "
                            "With no turn chosen, it counts down at the end of this combatant's turn.",
                  wraplength=380, foreground="#777").grid(row=len(rows), column=0, columnspan=2, padx=6)

        def use_preset(*_):
            p = BONUS_PRESETS.get(preset.get())
            if not p:
                return
            if p.get("condition"):
                return
            label.set(p["label"]); btype.set(p["type"]); val.set(str(p["value"])); applies.set(p["applies"])
            rounds.set(str(p["rounds"])); src.set(c.name if p.get("self_source") else "(none)")
        preset.trace_add("write", use_preset)

        def ok():
            p = BONUS_PRESETS.get(preset.get()) or {}
            if p.get("condition"):
                self.combat.set_condition(c.id, p["condition"])
            else:
                v = self._int_or_none(val.get())
                if not v:
                    messagebox.showwarning("Value", "Enter a non-zero value.", parent=win); return
                source = next((x.id for x in cs if x.name == src.get()), None)
                self.combat.add_bonus(c.id, label.get().strip() or "Bonus", btype.get(), v, applies.get(),
                                      self._int_or_none(rounds.get()) or 0, source)
            self._combat_changed(); win.destroy()
        ttk.Button(win, text="Add", command=ok).grid(row=len(rows) + 1, column=1, sticky="e", padx=6, pady=6)

    # ---------- extra damage (riders), defenses, resources ----------
    def _char_for(self, c):
        """The Pathbuilder character data behind a combatant, or None for monsters and manual entries."""
        if c and (c.kind == "pc" or c.uid.startswith("N|")):
            return self._pc_data_for(c)
        return None

    def _combatant_level(self, c):
        pc = self._char_for(c)
        if pc and pc.get("level"):
            return pc["level"]
        d = self._combatant_details(c) if c else None
        return (d or {}).get("level") or self.party_level()

    def _ask_int(self, title, prompt, initial="", parent=None):
        """Small modal number prompt. Returns an int or None."""
        win = tk.Toplevel(parent or self); win.title(title); win.transient(parent or self)
        v = tk.StringVar(value=str(initial)); out = {"v": None}
        ttk.Label(win, text=prompt).pack(padx=10, pady=(10, 4))
        e = ttk.Entry(win, textvariable=v, width=10); e.pack(padx=10); e.focus_set()

        def ok(*_):
            out["v"] = self._int_or_none(v.get())
            win.destroy()
        e.bind("<Return>", ok)
        ttk.Button(win, text="OK", command=ok).pack(pady=8)
        win.grab_set(); win.wait_window()
        return out["v"]

    def _riders_dialog(self):
        c = self._selected_combatant()
        if not c:
            messagebox.showinfo("Select", "Select a combatant first."); return
        pc = self._char_for(c)
        names = {v: k for k, v in RIDER_APPLIES.items()}
        win = tk.Toplevel(self); win.title(f"Extra damage: {c.name}"); win.transient(self)
        ttk.Label(win, text="Switch a rider on and it's added to matching Strikes in the stat block and to every "
                            "attack roll made from it. Precision damage uses the weapon's own damage type, is "
                            "doubled on a critical hit, and is ignored by creatures immune to precision damage.",
                  wraplength=520, foreground="#555", justify="left").pack(padx=8, pady=6, anchor="w")
        tree = ttk.Treeview(win, columns=("on", "dice", "applies"), show="tree headings", height=6)
        tree.heading("#0", text="Extra damage"); tree.column("#0", width=170)
        for col, t, w in (("on", "State", 50), ("dice", "Damage", 130), ("applies", "Applies to", 230)):
            tree.heading(col, text=t); tree.column(col, width=w)
        tree.pack(fill="x", padx=8)

        def refresh():
            tree.delete(*tree.get_children())
            for i, r in enumerate(c.riders):
                kind = "precision" if r.get("precision", True) else r.get("dtype", "")
                tree.insert("", "end", iid=str(i), text=r.get("label", "Extra damage"),
                            values=("ON" if r.get("active") else "off", f"{r.get('dice', '')} {kind}".strip(),
                                    names.get(r.get("applies", "any"), "Any Strike")))

        def commit():
            if pc is not None:                     # definitions are remembered for next fight; on/off is per fight
                rs.state(pc)["riders"] = [dict(r, active=False) for r in c.riders]
                self._pc_state_changed(pc)
            self._combat_changed()
            refresh()

        def picked():
            sel = tree.selection()
            return int(sel[0]) if sel else None

        def toggle(*_):
            i = picked()
            if i is not None:
                c.riders[i]["active"] = not c.riders[i].get("active")
                commit()
                tree.selection_set(str(i))

        def remove():
            i = picked()
            if i is not None:
                del c.riders[i]
                commit()
        tree.bind("<Double-1>", toggle)
        bar = ttk.Frame(win); bar.pack(fill="x", padx=8, pady=4)
        ttk.Button(bar, text="Switch On / Off", command=toggle).pack(side="left")
        ttk.Button(bar, text="Remove", command=remove).pack(side="left", padx=4)
        n = sneak_attack_dice(self._combatant_level(c))

        def add_sneak():
            c.riders.append({"label": "Sneak Attack", "dice": f"{n}d6", "precision": True, "dtype": "",
                             "applies": "sneak", "active": True})
            commit()
        ttk.Button(bar, text=f"Add Sneak Attack ({n}d6)", command=add_sneak).pack(side="right")

        form = ttk.LabelFrame(win, text="Add your own"); form.pack(fill="x", padx=8, pady=6)
        label, dice_v, dtype, applies = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar(value="Any Strike")
        prec = tk.BooleanVar(value=True)
        for r_, (lab, w) in enumerate((("Name", ttk.Entry(form, textvariable=label, width=22)),
                                       ("Damage", ttk.Entry(form, textvariable=dice_v, width=12)),
                                       ("Applies to", ttk.Combobox(form, textvariable=applies, width=38, state="readonly",
                                                                   values=list(RIDER_APPLIES))))):
            ttk.Label(form, text=lab).grid(row=r_, column=0, sticky="w", padx=4, pady=2); w.grid(row=r_, column=1, sticky="w")
        ttk.Checkbutton(form, text="Precision (same type as the weapon)", variable=prec).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="Otherwise type").grid(row=4, column=0, sticky="w", padx=4)
        ttk.Entry(form, textvariable=dtype, width=14).grid(row=4, column=1, sticky="w")

        def add():
            expr = dice_v.get().strip().replace(" ", "")
            if not re.fullmatch(r"(\d*d\d+|\d+)([+-](\d*d\d+|\d+))*", expr):
                messagebox.showwarning("Damage", "Enter dice like 2d6, 1d8+2, or 3.", parent=win); return
            c.riders.append({"label": label.get().strip() or "Extra damage", "dice": expr, "precision": prec.get(),
                             "dtype": dtype.get().strip(), "applies": RIDER_APPLIES.get(applies.get(), "any"),
                             "active": True})
            commit()
        ttk.Button(form, text="Add", command=add).grid(row=5, column=1, sticky="e", pady=4)
        refresh()

    @staticmethod
    def _iwr_text(iwr):
        out = {"immunities": ", ".join(s.replace("-", " ") for s in (iwr or {}).get("immune", [])),
               "weaknesses": ", ".join(f"{s.replace('-', ' ')} {n}" for s, n in ((iwr or {}).get("weak") or {}).items()),
               "resistances": ", ".join(f"{s.replace('-', ' ')} {v[0]}" + (f" (except {v[1]})" if v[1] else "")
                                        for s, v in ((iwr or {}).get("resist") or {}).items())}
        return out

    def _defenses_dialog(self):
        c = self._selected_combatant()
        if not c:
            messagebox.showinfo("Select", "Select a combatant first."); return
        pc = self._char_for(c)
        self._ensure_iwr(c)
        win = tk.Toplevel(self); win.title(f"Defenses: {c.name}"); win.transient(self)
        vals = ((rs.state(pc).get("defenses") or {}) if pc is not None else self._iwr_text(c.iwr))
        vars_ = {k: tk.StringVar(value=vals.get(k, "")) for k in ("immunities", "weaknesses", "resistances")}
        note = ("Added to the ones from Pathbuilder. Lists like: fire 5, physical 5 (except silver)."
                if pc is not None else "Replaces this combatant's immunities, weaknesses, and resistances.")
        ttk.Label(win, text=note, foreground="#555", wraplength=420).grid(row=0, column=0, columnspan=2, padx=8, pady=6, sticky="w")
        for r_, (k, lab) in enumerate((("immunities", "Immunities"), ("weaknesses", "Weaknesses"),
                                       ("resistances", "Resistances")), start=1):
            ttk.Label(win, text=lab).grid(row=r_, column=0, sticky="w", padx=8, pady=2)
            ttk.Entry(win, textvariable=vars_[k], width=46).grid(row=r_, column=1, padx=8, pady=2)
        if pc is not None:
            ttk.Label(win, text="From Pathbuilder: " + (" | ".join(f"{k} {', '.join(pc.get(k, []))}" for k in
                                                                  ("immunities", "weaknesses", "resistances") if pc.get(k)) or "none"),
                      foreground="#777", wraplength=420).grid(row=4, column=0, columnspan=2, padx=8, sticky="w")

        def ok():
            texts = {k: v.get().strip() for k, v in vars_.items()}
            if pc is not None:
                rs.state(pc)["defenses"] = texts
                self._pc_state_changed(pc)
                self._ensure_iwr(c)
            else:
                c.iwr = parse_iwr({k: pb.def_pairs(pb._split_commas(t)) for k, t in texts.items()})
            self._combat_changed()
            win.destroy()
        ttk.Button(win, text="Save", command=ok).grid(row=5, column=1, sticky="e", padx=8, pady=8)

    def _open_resources(self, get_pc):
        pc = get_pc()
        if not pc:
            messagebox.showinfo("No character", "That combatant isn't a character with saved data."); return
        key = pc["name"].lower()
        win = self.res_wins.get(key)
        try:
            alive = win is not None and win.winfo_exists()
        except Exception:
            alive = False
        if alive:
            win.refresh(); win.deiconify(); win.lift()
        else:
            self.res_wins[key] = ResourcesWindow(self, get_pc)

    def _combat_resources(self):
        c = self._selected_combatant()
        if not c or self._char_for(c) is None:
            messagebox.showinfo("Resources", "Select a PC or an imported NPC. Monsters don't track resources."); return
        self._open_resources(lambda cid=c.id: self._char_for(self.combat.get(cid)) if self.combat.get(cid) else None)

    def _nbk_resources(self):
        p = self.nbk_current
        if not p or not p.get("pc"):
            messagebox.showinfo("Resources", "Select a PC or NPC page imported from Pathbuilder."); return
        self._open_resources(lambda pid=p["id"]: (self._page(pid) or {}).get("pc"))

    def _party_resources(self):
        sel = self.party_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a party member first."); return
        name = self.party_tree.item(sel[0], "values")[0]
        self._open_resources(lambda n=name: next((x for x in self.party if x["name"] == n), None))

    def _res_done(self, pc, msg):
        """After a resource change: save, log to the combat log if a fight is running, and show it."""
        self._pc_state_changed(pc)
        line = f"{pc['name']}: {msg}"
        self.last_roll.set(line)
        if self.combat.round:
            self.combat._log(line)
            self._combat_changed()

    def _remove_combatant(self):
        c = self._selected_combatant()
        if c:
            self.combat.remove(c.id)
            self._combat_changed()

    def _clear_combat(self):
        if self.combat.combatants and not messagebox.askyesno("Clear combat", "Remove all combatants and reset?"):
            return
        self.combat.clear()
        self._combat_changed()

    # ---------- Shops ----------
    def _build_shop(self):
        f = self.tab_shop
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Settlement level").grid(row=0, column=0, sticky="w")
        self.shop_lvl = tk.IntVar(value=max(1, self.party_level() + 1))
        ttk.Spinbox(top, from_=0, to=25, textvariable=self.shop_lvl, width=5).grid(row=0, column=1, sticky="w")
        ttk.Label(top, text="Kind of shop").grid(row=0, column=2, padx=(14, 2), sticky="w")
        self.shop_type = Combo(top, list(SHOP_TYPES), readonly=True, width=44); self.shop_type.var.set("General store")
        self.shop_type.grid(row=0, column=3, columnspan=3, sticky="w")
        ttk.Label(top, text="Stock size").grid(row=1, column=0, sticky="w", pady=3)
        sz = ttk.Frame(top); sz.grid(row=1, column=1, columnspan=2, sticky="w")
        self.shop_size = Combo(sz, list(SHOP_SIZES), readonly=True, width=16); self.shop_size.var.set("Town")
        self.shop_size.pack(side="left")
        self.shop_count = tk.IntVar(value=SHOP_SIZES["Town"])
        ttk.Spinbox(sz, from_=1, to=SHOP_MAX, textvariable=self.shop_count, width=6).pack(side="left", padx=(6, 2))
        ttk.Label(sz, text="different items (up to %d)" % SHOP_MAX).pack(side="left")
        ttk.Label(top, text="Rarity").grid(row=1, column=3, sticky="e", padx=(14, 4))
        self.shop_rar = RarityChecks(top, default=("common",)); self.shop_rar.grid(row=1, column=4, columnspan=2, sticky="w")
        opts = ttk.Frame(top); opts.grid(row=2, column=0, columnspan=6, sticky="w", pady=2)
        self.shop_special = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Special orders (above settlement level)", variable=self.shop_special).pack(side="left")
        self.shop_qty = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Quantities (several copies of cheap goods)", variable=self.shop_qty).pack(side="left", padx=10)
        ttk.Label(opts, text="Specialty stock").pack(side="left", padx=(14, 4))
        self.shop_focus = tk.DoubleVar(value=SHOP_TYPES["General store"]["focus"] * 100)
        ttk.Scale(opts, from_=0, to=100, orient="horizontal", variable=self.shop_focus, length=120).pack(side="left")
        self.shop_focus_lbl = tk.StringVar()
        ttk.Label(opts, textvariable=self.shop_focus_lbl, width=22, foreground="#555").pack(side="left", padx=4)
        bb = ttk.Frame(top); bb.grid(row=0, column=6, rowspan=3, padx=10, sticky="n")
        for text, cmd in (("Stock Shop", self._gen_shop), ("Add More...", self._shop_add_more),
                          ("Reroll Selected", self._shop_reroll), ("Remove Selected", self._shop_remove),
                          ("New Name", self._shop_new_name)):
            ttk.Button(bb, text=text, command=cmd).pack(fill="x", pady=1)
        out = ttk.Frame(top); out.grid(row=3, column=0, columnspan=7, sticky="w", pady=(4, 0))
        for text, cmd in (("Copy List", self._copy_shop), ("Add to Notebook", self._shop_to_notebook),
                          ("Make Card...", self._shop_card),
                          ("Export Markdown...", self._shop_export), ("Check Themes...", self._shop_check_themes)):
            ttk.Button(out, text=text, command=cmd).pack(side="left", padx=(0, 4))
        self.shop_title = tk.StringVar()
        ttk.Label(f, textvariable=self.shop_title, font=("TkDefaultFont", 12, "bold")).pack(anchor="w", padx=10)
        self.shop_info = tk.StringVar(value=SHOP_TYPES["General store"]["blurb"])
        ttk.Label(f, textvariable=self.shop_info, foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=10)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=6)
        left = ttk.Frame(pane); pane.add(left, weight=3)
        cols = ("lvl", "qty", "price", "kind", "avail")
        self.shop_tree = ttk.Treeview(left, columns=cols, show="tree headings")
        self.shop_tree.heading("#0", text="Item"); self.shop_tree.column("#0", width=300)
        for c, t, w in zip(cols, ("Lvl", "Qty", "Price", "Kind", "Availability"), (40, 40, 90, 90, 100)):
            self.shop_tree.heading(c, text=t); self.shop_tree.column(c, width=w)
        sbar = ttk.Scrollbar(left, command=self.shop_tree.yview); self.shop_tree.configure(yscrollcommand=sbar.set)
        sbar.pack(side="right", fill="y"); self.shop_tree.pack(fill="both", expand=True)
        self.shop_tree.bind("<<TreeviewSelect>>", lambda e: self._show_shop_item())
        self.shop_view = RichText(pane, self); pane.add(self.shop_view, weight=2)
        self.shop_view.show_message("Stock a shop, then select an item to see its rules text.")
        self.shop = None
        self.shop_type.var.trace_add("write", lambda *a: self._shop_type_changed())
        self.shop_size.var.trace_add("write", lambda *a: self._shop_size_changed())
        self.shop_focus.trace_add("write", lambda *a: self._shop_focus_label())
        self._shop_focus_label()
    def _shop_size_changed(self):
        n = SHOP_SIZES.get(self.shop_size.var.get())
        if n:
            self.shop_count.set(n)
    def _shop_type_changed(self):
        spec = SHOP_TYPES.get(self.shop_type.var.get())
        if spec:
            self.shop_focus.set(round(spec["focus"] * 100))
            self.shop_info.set(spec["blurb"])
    def _shop_focus_label(self):
        try:
            v = int(round(float(self.shop_focus.get())))
        except (tk.TclError, ValueError):
            return
        has_side = bool((SHOP_TYPES.get(self.shop_type.var.get()) or {}).get("also"))
        self.shop_focus_lbl.set(f"{v}% its own goods" if has_side else "(this shop has no sundries)")
    def _shop_count_value(self):
        try:
            return max(1, min(SHOP_MAX, int(self.shop_count.get())))
        except (tk.TclError, ValueError):
            return SHOP_SIZES["Town"]
    def _shop_level_value(self):
        try:
            return max(0, int(self.shop_lvl.get()))
        except (tk.TclError, ValueError):
            return max(1, self.party_level() + 1)
    def _shop_items(self):
        return [i for i in self.all_items if self.in_systems(i)]
    def _gen_shop(self):
        try:
            focus = max(0.0, min(1.0, float(self.shop_focus.get()) / 100.0))
        except (tk.TclError, ValueError):
            focus = None
        self.shop = build_shop(self._shop_items(), self._shop_level_value(), self._shop_count_value(), self.shop_type.var.get(),
                               self.shop_rar.get(), special_orders=self.shop_special.get(), quantities=self.shop_qty.get(),
                               focus=focus)
        self._shop_draw()
    def _shop_draw(self, select=()):
        sh = self.shop
        self.shop_tree.delete(*self.shop_tree.get_children())
        if sh is None:
            self.shop_title.set("")
            return
        for n, l in enumerate(sh.lines):
            it = l.item
            avail = "special order" if l.tag != "stock" else "sundry" if l.side else "stock"
            self.shop_tree.insert("", "end", iid=str(n), text=it.name + (" [SF]" if system_of(it) == "sf" else ""),
                                  values=(it.level, l.qty, price_text(it), "consumable" if it.consumable else "permanent", avail))
        for n in select:
            if self.shop_tree.exists(str(n)):
                self.shop_tree.selection_add(str(n))
        total = sum(l.qty for l in sh.lines)
        gp, cr = sh.total_gp(), sh.total_credits()
        bits = [f"{len(sh.lines)} different items" + (f", {total} in all" if total != len(sh.lines) else "")]
        if gp:
            bits.append(f"about {gp:,.0f} gp of stock")
        if cr:
            bits.append(f"about {cr:,.0f} credits of stock")
        text = f"{sh.theme.split(' (')[0]}, settlement level {sh.level}: " + ", ".join(bits) + f". {self.sys_var.get()}."
        warn = self._missing_system_warning()
        self.shop_title.set(sh.name)
        self.shop_info.set(" ".join([text] + sh.notes + ([warn] if warn else [])))
    def _shop_selected(self):
        return sorted(int(i) for i in self.shop_tree.selection() if str(i).isdigit() and self.shop and int(i) < len(self.shop.lines))
    def _show_shop_item(self):
        sel = self._shop_selected()
        if not sel:
            return
        it = self.shop.lines[sel[0]].item
        old = self.item_view
        self.item_view = self.shop_view
        try:
            self._show_item(item=it)
        finally:
            self.item_view = old
    def _shop_add_more(self):
        if self.shop is None:
            messagebox.showinfo("No shop yet", "Stock a shop first."); return
        n = self._ask_int("Add to stock", "How many more different items?", 10)
        if not n or n < 1:
            return
        added = shop_add_more(self.shop, self._shop_items(), n)
        self.shop_count.set(len(self.shop.lines))
        self._shop_draw()
        if added < n:
            self.last_roll.set(f"Added {added} of {n}: that is all that fit this shop.")
        else:
            self.last_roll.set(f"Added {added} items to {self.shop.name}.")
    def _shop_reroll(self):
        sel = self._shop_selected()
        if not sel:
            messagebox.showinfo("Select items", "Select one or more items to reroll."); return
        lines = [self.shop.lines[i] for i in sel]
        failed = 0
        for line in lines:
            if line not in self.shop.lines or not shop_reroll_line(self.shop, self.shop.lines.index(line), self._shop_items()):
                failed += 1
        self._shop_draw()
        if failed:
            self.last_roll.set(f"{failed} item{'s' if failed != 1 else ''} had nothing else to swap in.")
    def _shop_remove(self):
        sel = self._shop_selected()
        if sel:
            shop_remove_lines(self.shop, sel)
            self.shop_count.set(max(1, len(self.shop.lines)))
            self._shop_draw()
    def _shop_new_name(self):
        if self.shop is not None:
            self.shop.name = make_shop_name(self.shop.theme)
            self._shop_draw()
    def _copy_shop(self):
        if self.shop is not None and self.shop.lines:
            self.clipboard_clear()
            self.clipboard_append(shop_text(self.shop))
            self.last_roll.set(f"Copied the stock of {self.shop.name} to the clipboard.")
    def _shop_to_notebook(self):
        sh = self.shop
        if sh is None or not sh.lines:
            messagebox.showinfo("No shop yet", "Stock a shop first."); return
        body = "\n".join(shop_text(sh).splitlines()[2:])
        kind = f"{sh.theme.split(' (')[0].lower()} (settlement level {sh.level})"
        page = next((p for p in self.notebook if p.get("shop_theme") and p["title"] == sh.name), None)
        if page is None:
            page = nbk.new_page(nbk.unique_title(self.notebook, sh.name), "Location", body, status="",
                                tags=list(SHOP_TAGS.get(sh.theme, ["trade"])), kind=kind, preps=["at", "in", "near"],
                                shop_theme=sh.theme)
            self.notebook.append(page)
            verb = "Added"
        else:
            page.update(body=body, kind=kind, shop_theme=sh.theme, tags=list(SHOP_TAGS.get(sh.theme, ["trade"])))
            verb = "Updated"
        self._save_notebook(); self._refresh_notebook(select=page["id"])
        self.last_roll.set(f"{verb} '{page['title']}' in the Notebook as a place.")
    def _shop_check_themes(self):
        """How well your downloaded data supports each kind of shop at the current settlement level and rarity."""
        level, rar = self._shop_level_value(), self.shop_rar.get()
        rows = theme_report(self._shop_items(), level, rar, self.shop_special.get())
        win = tk.Toplevel(self); win.title("Check shop themes"); win.geometry("1040x520"); win.transient(self)
        rar_text = "/".join(sorted(rar)) if rar else "any rarity"
        ttk.Label(win, wraplength=1000, justify="left", foreground="#555", text=(
            f"Different items in your data that fit each kind of shop at settlement level {level}, rarity {rar_text}, "
            f"{self.sys_var.get()}. 'Largest' is the most different items that shop could hold. A thin or empty row means "
            "your data has few matching items (raise the settlement level or allow uncommon items). If a row looks wrong "
            "for your data, copy the report and send it to me.")).pack(anchor="w", padx=8, pady=6)
        cols = ("stock", "special", "sundries", "largest", "state", "sample")
        tree = ttk.Treeview(win, columns=cols, show="tree headings")
        tree.heading("#0", text="Kind of shop"); tree.column("#0", width=260)
        for c, t, w in zip(cols, ("In stock", "Special", "Sundries", "Largest", "State", "Examples"), (60, 55, 65, 60, 55, 440)):
            tree.heading(c, text=t); tree.column(c, width=w, stretch=(c == "sample"))
        tree.tag_configure("empty", foreground="#a33"); tree.tag_configure("thin", foreground="#9a5b00")
        for r in rows:
            tree.insert("", "end", iid=r["theme"], text=r["theme"].split(" (")[0],
                        values=(r["stock"], r["special"], r["sundries"], r["largest"], r["state"], "; ".join(r["sample"])),
                        tags=(r["state"],) if r["state"] != "ok" else ())
        tree.pack(fill="both", expand=True, padx=8)
        text = theme_report_text(rows, level, rar)
        def copy():
            self.clipboard_clear(); self.clipboard_append(text)
            self.last_roll.set("Copied the shop theme report to the clipboard.")
        bar = ttk.Frame(win); bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Copy Report", command=copy).pack(side="left")
        ttk.Button(bar, text="Close", command=win.destroy).pack(side="right")
        self.theme_win, self.theme_tree, self.theme_text = win, tree, text
    def _shop_export(self):
        sh = self.shop
        if sh is None or not sh.lines:
            messagebox.showinfo("No shop yet", "Stock a shop first."); return
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", sh.name).strip("_") or "shop"
        self._save_text(shop_text(sh), f"{safe}.md")
    # ---------- Inns and Taverns ----------
    INN_QUALITY = ["Any", "Squalid", "Common", "Good", "Fine"]
    INN_SIZE = ["Any", "Small", "Medium", "Large"]
    INN_BUSY = ["Any", "Quiet", "Normal", "Packed"]

    @staticmethod
    def _inn_key(label, mapping=None):
        """'Any' becomes 'any'; a kind label such as 'Roadhouse' becomes its key."""
        label = str(label or "").strip()
        if mapping:
            return next((k for k, v in mapping.items() if v["label"] == label), "any")
        return label.lower() if label else "any"

    def _build_inns(self):
        f = self.tab_inn
        cfg = self.config_data.get("inns", {})
        self.inn_gen = tavern.TavernGenerator(self.story_registry, rng=random.Random())
        self.inn_list, self.inn_cur, self.inn_widgets = [], None, {}
        top = ttk.LabelFrame(f, text="What do you need?")
        top.pack(fill="x", padx=8, pady=(6, 2))

        def lab(text, r, c):
            ttk.Label(top, text=text).grid(row=r, column=c, sticky="w", padx=(10 if c else 4, 4), pady=2)

        def combo(values, r, c, key, default, width=12):
            w = Combo(top, values, readonly=True, width=width)
            w.var.set(cfg.get(key, default))
            w.grid(row=r, column=c, sticky="w")
            return w
        lab("Kind", 0, 0); self.inn_kind = combo(["Any"] + [v["label"] for v in tavern.KINDS.values()], 0, 1, "kind", "Any")
        lab("Quality", 0, 2); self.inn_quality = combo(self.INN_QUALITY, 0, 3, "quality", "Any", 10)
        lab("Size", 0, 4); self.inn_size = combo(self.INN_SIZE, 0, 5, "size", "Any", 10)
        lab("Tonight", 0, 6); self.inn_busy = combo(self.INN_BUSY, 0, 7, "busy", "Any", 10)
        lab("Setting", 1, 0); self.inn_env = combo(self.STORY_ENVS, 1, 1, "env", "any")
        lab("Tone", 1, 2); self.inn_tone = combo(self.STORY_TONES, 1, 3, "tone", "any", 10)
        lab("Theme", 1, 4)
        self.inn_themes = MultiField(top, values=sg.THEMES, width=22, combo_width=11)
        self.inn_themes.grid(row=1, column=5, columnspan=3, sticky="w")
        self.inn_themes.set(cfg.get("themes", []))
        lab("Run by", 2, 0)
        self.inn_culture = combo(["Automatic", "None"] + [v[0] for v in tavern.CULTURES.values()], 2, 1, "culture", "Automatic", 16)
        lab("Located at", 2, 2)
        self.inn_tie = Combo(top, ["(none)"], readonly=True, width=22)
        self.inn_tie.var.set("(none)")
        self.inn_tie.grid(row=2, column=3, columnspan=2, sticky="w")
        lab("Party level", 2, 5)
        self.inn_lvl = tk.StringVar(value=str(cfg.get("level", self.party_level())))
        ttk.Spinbox(top, from_=1, to=20, textvariable=self.inn_lvl, width=5).grid(row=2, column=6, sticky="w")
        lab("Price adjust %", 3, 0)
        self.inn_pct = tk.StringVar(value=str(cfg.get("price_pct", 100)))
        ttk.Spinbox(top, from_=10, to=1000, increment=10, textvariable=self.inn_pct, width=6).grid(row=3, column=1, sticky="w")
        lab("Patrons", 3, 2)
        self.inn_patrons = tk.StringVar(value=str(cfg.get("patrons", "")))
        ttk.Spinbox(top, from_=0, to=30, textvariable=self.inn_patrons, width=5).grid(row=3, column=3, sticky="w")
        lab("Staff", 3, 4)
        self.inn_staff = tk.StringVar(value=str(cfg.get("staff", "")))
        ttk.Spinbox(top, from_=0, to=15, textvariable=self.inn_staff, width=5).grid(row=3, column=5, sticky="w")
        ttk.Label(top, text="(blank = chosen for you)", foreground="#888").grid(row=3, column=6, columnspan=2, sticky="w")
        opts = ttk.Frame(top); opts.grid(row=4, column=0, columnspan=8, sticky="w", pady=2)
        self.inn_stories = tk.BooleanVar(value=cfg.get("stories", True))
        ttk.Checkbutton(opts, text="Rumors and hooks for patrons", variable=self.inn_stories).pack(side="left", padx=4)
        self.inn_hm = tk.BooleanVar(value=cfg.get("hm", bool(self.config_data.get("hallowmead_loaded"))))
        ttk.Checkbutton(opts, text="Hallowmead setting content", variable=self.inn_hm).pack(side="left", padx=4)
        ttk.Label(opts, text="Setting flavor").pack(side="left", padx=(8, 2))
        self.inn_flavor = tk.DoubleVar(value=cfg.get("flavor", sg.DEFAULT_FLAVOR * 100))
        ttk.Scale(opts, from_=0, to=100, orient="horizontal", variable=self.inn_flavor, length=90).pack(side="left")
        ttk.Label(opts, text="Use my campaign").pack(side="left", padx=(8, 2))
        self.inn_use = tk.DoubleVar(value=cfg.get("use_campaign", 50))
        ttk.Scale(opts, from_=0, to=100, orient="horizontal", variable=self.inn_use, length=90).pack(side="left")
        ttk.Label(opts, text="Options").pack(side="left", padx=(8, 2))
        self.inn_count = tk.StringVar(value=str(cfg.get("count", 3)))
        ttk.Spinbox(opts, from_=1, to=8, textvariable=self.inn_count, width=4).pack(side="left")
        bb = ttk.Frame(top); bb.grid(row=0, column=8, rowspan=5, padx=10)
        ttk.Button(bb, text="Generate", command=self._inn_generate).pack(fill="x", pady=1)
        ttk.Button(bb, text="Add One More", command=lambda: self._inn_generate(count=1, append=True)).pack(fill="x", pady=1)
        ttk.Button(bb, text="Edit Tables...", command=self._story_open_tables).pack(fill="x", pady=1)
        ttk.Button(bb, text="Open Saved...", command=self._inn_open_saved).pack(fill="x", pady=1)
        self.inn_info = tk.StringVar(value="Prices come from the Player Core services table. Press Generate.")
        ttk.Label(f, textvariable=self.inn_info, foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=10)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        ttk.Label(left, text="Options (click one to open, edit, and keep)", foreground="#555").pack(anchor="w")
        self.inn_tree = ttk.Treeview(left, columns=("kind",), show="tree headings", height=16)
        self.inn_tree.heading("#0", text="Name"); self.inn_tree.column("#0", width=230)
        self.inn_tree.heading("kind", text="What"); self.inn_tree.column("kind", width=120)
        self.inn_tree.pack(fill="both", expand=True)
        self.inn_tree.bind("<<TreeviewSelect>>", lambda e: self._inn_pick())
        right = ttk.Frame(pane); pane.add(right, weight=4)
        sv = ttk.Frame(right); sv.pack(side="bottom", fill="x", pady=3)
        tabs = TabbedPane(right, level=3); tabs.pack(fill="both", expand=True)
        pages = [ttk.Frame(tabs) for _ in range(4)]
        for page, text in zip(pages, ("Overview", "Menu and rooms", "People", "Card")):
            tabs.add(page, text=text)
        self.inn_tabs = tabs
        self._build_inn_overview(pages[0]); self._build_inn_menu(pages[1]); self._build_inn_people(pages[2]); self._build_inn_card(pages[3])
        self.inn_make_people = tk.BooleanVar(value=cfg.get("make_people", True))
        self.inn_make_stories = tk.BooleanVar(value=cfg.get("make_stories", False))
        ttk.Checkbutton(sv, text="Pages for the people", variable=self.inn_make_people).pack(side="left", padx=4)
        ttk.Checkbutton(sv, text="Pages for their rumors and hooks", variable=self.inn_make_stories).pack(side="left", padx=4)
        for text, cmd in (("Export Markdown...", self._inn_export), ("Copy Player Card", lambda: self._inn_copy(False)),
                          ("Copy GM Card", lambda: self._inn_copy(True)), ("Add to Notebook", self._inn_to_notebook)):
            ttk.Button(sv, text=text, command=cmd).pack(side="right", padx=2)
        self._inn_refresh_tie()
        self._inn_show(None)

    def _build_inn_overview(self, f):
        bar = ttk.Frame(f); bar.pack(fill="x", pady=3)
        ttk.Button(bar, text="Reroll Unlocked", command=self._inn_reroll_all).pack(side="left", padx=2)
        ttk.Label(bar, text="Lock the lines you like, then reroll the rest.", foreground="#555").pack(side="left", padx=8)
        canvas, inner = self._scroll_area(f)
        self.inn_rows = ttk.Frame(inner); self.inn_rows.pack(fill="x")

    def _build_inn_menu(self, f):
        top = ttk.Frame(f); top.pack(fill="x", pady=3)
        ttk.Label(top, text="Menu", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=4)
        for text, cmd in (("Reroll Selected", self._inn_menu_reroll), ("Remove Selected", self._inn_menu_remove),
                          ("Lock / Unlock", self._inn_menu_lock), ("Set Price...", self._inn_menu_price)):
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)
        self.inn_cat = Combo(top, [v["label"] for k, v in tavern.CATEGORIES.items() if k != "keg"], readonly=True, width=20)
        self.inn_cat.var.set("Square meal"); self.inn_cat.pack(side="left", padx=(10, 2))
        ttk.Button(top, text="Add Line", command=self._inn_menu_add).pack(side="left", padx=2)
        ttk.Label(top, text="Adjust all prices %").pack(side="left", padx=(12, 2))
        self.inn_adjust = tk.StringVar(value="100")
        ttk.Entry(top, textvariable=self.inn_adjust, width=6).pack(side="left")
        ttk.Button(top, text="Apply", command=self._inn_adjust_prices).pack(side="left", padx=2)
        self.inn_menu_tree = ttk.Treeview(f, columns=("price", "what", "flags"), show="tree headings", height=10, selectmode="extended")
        self.inn_menu_tree.heading("#0", text="Item"); self.inn_menu_tree.column("#0", width=380)
        for c, t, w in (("price", "Price", 80), ("what", "Sold as", 140), ("flags", "", 120)):
            self.inn_menu_tree.heading(c, text=t); self.inn_menu_tree.column(c, width=w)
        self.inn_menu_tree.pack(fill="both", expand=True, padx=2)
        rb = ttk.Frame(f); rb.pack(fill="x", pady=3)
        ttk.Label(rb, text="Lodging", font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=4)
        ttk.Button(rb, text="Reroll Quirk", command=self._inn_room_reroll).pack(side="left", padx=2)
        self.inn_room_tree = ttk.Treeview(f, columns=("price", "free", "quirk"), show="tree headings", height=7, selectmode="extended")
        self.inn_room_tree.heading("#0", text="Room"); self.inn_room_tree.column("#0", width=200)
        for c, t, w in (("price", "Price", 90), ("free", "Free tonight", 110), ("quirk", "Quirk", 420)):
            self.inn_room_tree.heading(c, text=t); self.inn_room_tree.column(c, width=w)
        self.inn_room_tree.pack(fill="both", expand=True, padx=2)

    def _build_inn_people(self, f):
        top = ttk.Frame(f); top.pack(fill="x", pady=3)
        for text, cmd in (("Reroll Selected", self._inn_person_reroll), ("Lock / Unlock", self._inn_person_lock),
                          ("New Rumor", lambda: self._inn_person_hook("rumor")), ("New Hook", lambda: self._inn_person_hook("hook")),
                          ("No Hook", lambda: self._inn_person_hook("none")), ("Remove", self._inn_person_remove)):
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)
        self.inn_people_tree = ttk.Treeview(f, columns=("role", "desc", "hook"), show="tree headings", height=14)
        self.inn_people_tree.heading("#0", text="Name"); self.inn_people_tree.column("#0", width=170)
        for c, t, w in (("role", "Role", 110), ("desc", "Who", 260), ("hook", "Carries", 90)):
            self.inn_people_tree.heading(c, text=t); self.inn_people_tree.column(c, width=w)
        self.inn_people_tree.pack(fill="both", expand=True, padx=2)
        self.inn_people_tree.bind("<<TreeviewSelect>>", lambda e: self._inn_person_show())
        self.inn_person_text = tk.Text(f, height=7, wrap="word", state="disabled", font=("TkDefaultFont", 10))
        self.inn_person_text.pack(fill="x", padx=2, pady=3)

    def _build_inn_card(self, f):
        bar = ttk.Frame(f); bar.pack(fill="x", pady=3)
        self.inn_player_view = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Player view (leave out what the players would not know)", variable=self.inn_player_view,
                        command=self._inn_show_card).pack(side="left", padx=4)
        self.inn_card = RichText(f, self); self.inn_card.pack(fill="both", expand=True)

    # ----- settings and generating
    def _inn_refresh_tie(self):
        if hasattr(self, "inn_tie"):
            names = ["(none)"] + sorted(p["title"] for p in self.notebook if p.get("type") in ("Faction", "Location") and not p.get("tavern"))
            self.inn_tie.set_values(names)
            if self.inn_tie.var.get() not in names:
                self.inn_tie.var.set("(none)")

    def _inn_settings(self):
        s = {"kind": self._inn_key(self.inn_kind.var.get(), tavern.KINDS), "quality": self._inn_key(self.inn_quality.var.get()),
             "size": self._inn_key(self.inn_size.var.get()), "busy": self._inn_key(self.inn_busy.var.get()),
             "env": self.inn_env.var.get() or "any", "tone": self.inn_tone.var.get() or "any", "themes": self.inn_themes.items(),
             "level": self._int_or_none(str(self.inn_lvl.get())) or self.party_level(), "stories": bool(self.inn_stories.get()),
             "packs": ["core"] + (["hallowmead"] if self.inn_hm.get() else []), "use_campaign": float(self.inn_use.get()) / 100.0,
             "price_pct": self._int_or_none(str(self.inn_pct.get())) or 100, "patrons": self._int_or_none(str(self.inn_patrons.get())),
             "staff": self._int_or_none(str(self.inn_staff.get()))}
        s["flavor"] = max(0.0, min(0.95, float(self.inn_flavor.get()) / 100.0)) if self.inn_hm.get() else None
        label = self.inn_culture.var.get()
        s["culture"] = {"Automatic": "auto", "None": "none"}.get(label) or next((k for k, v in tavern.CULTURES.items() if v[0] == label), "auto")
        page = nbk.find(self.notebook, self.inn_tie.var.get()) if self.inn_tie.var.get() not in ("", "(none)") else None
        s["tie"] = ({"title": page["title"], "type": page.get("type"), "kind": page.get("kind", ""), "tags": infer_page_tags(page),
                     "text": (page.get("body") or "")[:300]} if page else None)
        return s

    def _inn_save_config(self, s):
        self.config_data["inns"] = {"kind": self.inn_kind.var.get(), "quality": self.inn_quality.var.get(), "size": self.inn_size.var.get(),
                                    "busy": self.inn_busy.var.get(), "env": s["env"], "tone": s["tone"], "themes": s["themes"],
                                    "culture": self.inn_culture.var.get(), "level": s["level"], "price_pct": s["price_pct"],
                                    "patrons": "" if s["patrons"] is None else s["patrons"], "staff": "" if s["staff"] is None else s["staff"],
                                    "stories": s["stories"], "hm": self.inn_hm.get(), "flavor": self.inn_flavor.get(),
                                    "use_campaign": self.inn_use.get(), "count": self._int_or_none(str(self.inn_count.get())) or 3,
                                    "make_people": self.inn_make_people.get(), "make_stories": self.inn_make_stories.get()}
        storage.save("config", self.config_data)

    def _inn_prepare(self):
        g = self.inn_gen
        g.set_registry(self.story_registry)
        g.set_campaign(self._story_campaign())
        return g

    def _inn_generate(self, count=None, append=False):
        s = self._inn_settings()
        n = count or max(1, min(8, self._int_or_none(str(self.inn_count.get())) or 3))
        places = self._inn_prepare().generate_batch(n, **s)
        self._inn_save_config(s)
        if append and self.inn_list:
            self.inn_list += places
        else:
            self.inn_list = places
        self._inn_refresh_list(select=len(self.inn_list) - n if append else 0)

    def _inn_refresh_list(self, select=None):
        self.inn_tree.delete(*self.inn_tree.get_children())
        for i, p in enumerate(self.inn_list):
            self.inn_tree.insert("", "end", iid=str(i), text=p["name"], values=(f"{p['quality']} {tavern.KINDS[p['kind']]['label'].lower()}",))
        if select is not None and self.inn_tree.exists(str(select)):
            self.inn_tree.selection_set(str(select))
        self._inn_pick()

    def _inn_pick(self):
        sel = self.inn_tree.selection()
        if sel and int(sel[0]) < len(self.inn_list):
            self._inn_show(self.inn_list[int(sel[0])])
        elif not self.inn_list:
            self._inn_show(None)

    # ----- showing a place
    def _inn_show(self, place):
        self.inn_cur = place
        for w in self.inn_rows.winfo_children():
            w.destroy()
        self.inn_widgets = {}
        if place is None:
            ttk.Label(self.inn_rows, foreground="#666", justify="left", text=(
                "Pick what you need above and press Generate.\n\nEvery place gets a name, a look, a priced menu and rooms, a "
                "proprietor, staff, and patrons who carry rumors and hooks. Prices come from the Player Core services table. "
                "Edit any line, lock it so it stays, or reroll it alone.")).pack(anchor="w", padx=8, pady=20)
            self.inn_menu_tree.delete(*self.inn_menu_tree.get_children()); self.inn_room_tree.delete(*self.inn_room_tree.get_children())
            self.inn_people_tree.delete(*self.inn_people_tree.get_children())
            self.inn_card.show_message("Generate a place to see its card.")
            return
        main = ttk.Frame(self.inn_rows); main.pack(fill="x"); main.columnconfigure(1, weight=1)
        r = 0
        self.inn_widgets["__name"] = self._magic_row(main, r, "Name", place["name"], place.get("name_locked", False),
                                                     lambda: self._inn_commit("__name"), lambda: self._inn_lock("__name"),
                                                     self._inn_reroll_name)
        for fld in place["fields"]:
            r += 1
            k = fld["key"]
            self.inn_widgets[k] = self._magic_row(main, r, fld["label"], fld["text"], fld["locked"] or fld["edited"],
                                                  lambda k=k: self._inn_commit(k), lambda k=k: self._inn_lock(k),
                                                  lambda k=k: self._inn_reroll_field(k))
        missing = [x for x in tavern.FIELDS if x[0] not in {f["key"] for f in place["fields"]}]
        if missing:
            r += 1
            add = ttk.Frame(main); add.grid(row=r, column=0, columnspan=4, sticky="w", pady=4)
            ttk.Label(add, text="Add a line:").pack(side="left", padx=4)
            for key, label, *_ in missing:
                ttk.Button(add, text=label, command=lambda k=key: self._inn_reroll_field(k)).pack(side="left", padx=2)
        if place.get("notes"):
            r += 1
            ttk.Label(main, foreground="#a33", wraplength=700, justify="left", text="  ".join(place["notes"])).grid(row=r, column=0, columnspan=4, sticky="w", padx=4)
        self._inn_refresh_lists()
        info = f"{tavern.kind_text(place)}, {place['busy']} tonight. Themes: {', '.join(place['themes']) or 'none'}."
        if place["culture"] != "none":
            info += f" Run by {tavern.CULTURES[place['culture']][0].lower()} folk."
        self.inn_info.set(info + "  Prices are the Player Core ones" + (f", adjusted to {place['settings']['price_pct']}%." if place["settings"]["price_pct"] != 100 else "."))

    def _inn_refresh_lists(self):
        p = self.inn_cur
        if p is None:
            return
        mt = self.inn_menu_tree
        keep = mt.selection()
        mt.delete(*mt.get_children())
        for i, m in enumerate(p["menu"]):
            flags = ", ".join(x for x, on in (("house special", m["special"]), ("locked", m["locked"]), ("price set", m["price_edited"])) if on)
            mt.insert("", "end", iid=str(i), text=m["name"], values=(tavern.price_text(m["price_cp"]), f"a {tavern.CATEGORIES[m['cat']]['per']}", flags))
        for k in keep:
            if mt.exists(k):
                mt.selection_add(k)
        rt = self.inn_room_tree
        rt.delete(*rt.get_children())
        for i, r in enumerate(p["rooms"]):
            free = (f"{r['free']} of {r['capacity']}" if r["type"] in ("floor", "bed", "stable") else ("free" if r["free"] else "taken"))
            rt.insert("", "end", iid=str(i), text=r["label"] + (f" ({tavern.room_kind_text(r)})" if tavern.room_kind_text(r) else ""),
                      values=(tavern.price_text(r["price_cp"]) + (" a day" if r["type"] == "stable" else " a night"), free, r["quirk"]))
        pt = self.inn_people_tree
        keep = pt.selection()
        pt.delete(*pt.get_children())
        rows = [("proprietor", 0, p["proprietor"])] + [("staff", i, x) for i, x in enumerate(p["staff"])] + [("patrons", i, x) for i, x in enumerate(p["patrons"])]
        for group, i, x in rows:
            if x:
                pt.insert("", "end", iid=f"{group}:{i}", text=x["name"] + (" (locked)" if x["locked"] else ""),
                          values=("Proprietor" if group == "proprietor" else x["role"].capitalize(), x["desc"], {"rumor": "a rumor", "hook": "a hook"}.get(x["hook"], "")))
        for k in keep:
            if pt.exists(k):
                pt.selection_add(k)
        self._inn_show_card()
        self._inn_person_show()

    def _inn_show_card(self):
        p = self.inn_cur
        if p is None:
            return
        lines = tavern.place_text(p, gm=not self.inn_player_view.get()).split("\n")
        heads = {"Menu", "Lodging", "Staff", "Patrons", "Work for Earn Income"}
        segs = [(lines[0] + "\n", "title", None), (lines[1] + "\n", "head", None)]
        for ln in lines[2:]:
            segs.append((ln + "\n", "label" if ln in heads else "body", None))
        self.inn_card.show(segs)

    # ----- editing the lines
    def _inn_commit(self, key):
        p, w = self.inn_cur, self.inn_widgets.get(key)
        if p is None or w is None:
            return
        new = w[0].get("1.0", "end").strip()
        if key == "__name":
            if new and new != p["name"]:
                p["name"], p["name_locked"] = new, True
                w[1].set(True)
                self._inn_refresh_name()
            return
        f = self.inn_gen.field(p, key)
        if f is not None and new and new != f["text"]:
            f["text"], f["edited"] = new, True
            w[1].set(True)
            self._inn_refresh_lists()

    def _inn_lock(self, key):
        p, w = self.inn_cur, self.inn_widgets.get(key)
        if p is None or w is None:
            return
        if key == "__name":
            p["name_locked"] = bool(w[1].get())
            return
        f = self.inn_gen.field(p, key)
        if f is not None:
            f["locked"] = bool(w[1].get())
            if not w[1].get():
                f["edited"] = False

    def _inn_commit_all(self):
        for key in list(self.inn_widgets):
            self._inn_commit(key)

    def _inn_refresh_name(self):
        idx = next((i for i, x in enumerate(self.inn_list) if x is self.inn_cur), None)
        if idx is not None and self.inn_tree.exists(str(idx)):
            self.inn_tree.item(str(idx), text=self.inn_cur["name"])
        self._inn_show_card()

    def _inn_reroll_name(self):
        if self.inn_cur is not None:
            self._inn_commit_all()
            self.inn_cur["name_locked"] = False
            self._inn_prepare().make_name(self.inn_cur)
            self._inn_show(self.inn_cur)
            self._inn_refresh_name()

    def _inn_reroll_field(self, key):
        if self.inn_cur is not None:
            self._inn_commit_all()
            self._inn_prepare().reroll_field(self.inn_cur, key)
            self._inn_show(self.inn_cur)

    def _inn_reroll_all(self):
        if self.inn_cur is not None:
            self._inn_commit_all()
            self._inn_prepare().reroll_unlocked(self.inn_cur)
            self._inn_show(self.inn_cur)
            self._inn_refresh_name()

    # ----- menu and rooms
    def _inn_selected(self, tree):
        return sorted(int(i) for i in tree.selection() if str(i).isdigit())

    def _inn_menu_reroll(self):
        p = self.inn_cur
        if p is not None:
            g = self._inn_prepare()
            for i in self._inn_selected(self.inn_menu_tree):
                if i < len(p["menu"]) and not p["menu"][i]["locked"]:
                    g.reroll_menu_line(p, i)
            self._inn_refresh_lists()

    def _inn_menu_remove(self):
        p = self.inn_cur
        if p is not None and self._inn_selected(self.inn_menu_tree):
            self.inn_gen.remove_menu_lines(p, self._inn_selected(self.inn_menu_tree))
            self._inn_refresh_lists()

    def _inn_menu_lock(self):
        p = self.inn_cur
        if p is not None:
            for i in self._inn_selected(self.inn_menu_tree):
                if i < len(p["menu"]):
                    p["menu"][i]["locked"] = not p["menu"][i]["locked"]
            self._inn_refresh_lists()

    def _inn_menu_price(self):
        p = self.inn_cur
        sel = self._inn_selected(self.inn_menu_tree)
        if p is None or not sel:
            messagebox.showinfo("Select a line", "Select a menu line first."); return
        text = self._ask_line("Set price", "New price (for example 5 cp, 2 sp, 1 gp 5 sp)", tavern.price_text(p["menu"][sel[0]]["price_cp"]))
        if text is None:
            return
        try:
            cp = dt.parse_coins(text, default="cp")
        except ValueError as e:
            messagebox.showwarning("Price", str(e)); return
        for i in sel:
            self.inn_gen.set_menu_price(p, i, cp)
        self._inn_refresh_lists()

    def _inn_menu_add(self):
        p = self.inn_cur
        if p is not None:
            cat = next((k for k, v in tavern.CATEGORIES.items() if v["label"] == self.inn_cat.var.get()), "square")
            self._inn_prepare().add_menu_line(p, cat)
            self._inn_refresh_lists()

    def _inn_adjust_prices(self):
        p = self.inn_cur
        pct = self._int_or_none(str(self.inn_adjust.get()))
        if p is None or pct is None:
            return
        self._inn_commit_all()
        self.inn_gen.set_price_pct(p, pct)
        self._inn_show(p)
        self.last_roll.set(f"Prices set to {p['settings']['price_pct']}% of the Player Core prices.")

    def _inn_room_reroll(self):
        p = self.inn_cur
        if p is not None:
            for i in self._inn_selected(self.inn_room_tree):
                if i < len(p["rooms"]):
                    self.inn_gen.reroll_room_quirk(p, i)
            self._inn_refresh_lists()

    # ----- people
    def _inn_person_key(self):
        sel = self.inn_people_tree.selection()
        if not sel or self.inn_cur is None:
            return None, None
        group, _, i = sel[0].partition(":")
        i = int(i or 0)
        lst = {"proprietor": [self.inn_cur["proprietor"]], "staff": self.inn_cur["staff"], "patrons": self.inn_cur["patrons"]}[group]
        return (group, i) if i < len(lst) else (None, None)

    def _inn_person(self):
        group, i = self._inn_person_key()
        if group is None:
            return None, None, None
        p = self.inn_cur
        return group, i, (p["proprietor"] if group == "proprietor" else p[group][i])

    def _inn_person_show(self):
        group, i, x = self._inn_person()
        t = self.inn_person_text
        t.configure(state="normal"); t.delete("1.0", "end")
        if x is not None:
            lines = [f"{x['name']} ({x['desc']})", x["detail"]]
            if x.get("fields"):
                lines += [f"{l}: {tx}" for l, tx in x["fields"]]
            if x.get("why"):
                lines.append("Here tonight: " + x["why"])
            if x.get("summary"):
                lines.append(("Rumor: " if x["hook"] == "rumor" else "Hook: ") + x["summary"])
            t.insert("end", "\n".join(l for l in lines if l))
        t.configure(state="disabled")

    def _inn_person_reroll(self):
        group, i, x = self._inn_person()
        if x is not None and not x["locked"]:
            self._inn_prepare().reroll_person(self.inn_cur, group, i)
            self._inn_refresh_lists()

    def _inn_person_lock(self):
        group, i, x = self._inn_person()
        if x is not None:
            x["locked"] = not x["locked"]
            self._inn_refresh_lists()

    def _inn_person_hook(self, kind):
        group, i, x = self._inn_person()
        if x is None or group != "patrons":
            messagebox.showinfo("Select a patron", "Select one of the patrons first."); return
        self._inn_prepare().make_hook(self.inn_cur, x, kind)
        self._inn_refresh_lists()

    def _inn_person_remove(self):
        group, i, x = self._inn_person()
        if x is not None and group in ("staff", "patrons"):
            del self.inn_cur[group][i]
            self._inn_refresh_lists()

    # ----- saving
    def _inn_to_notebook(self):
        p = self.inn_cur
        if p is None:
            messagebox.showinfo("Nothing to save", "Generate a place first."); return
        self._inn_commit_all()
        r = tavern.place_to_pages(p, self.notebook, self.inn_make_people.get(), self.inn_make_stories.get())
        self.notebook.extend(r["new"])
        self._save_notebook(); self._refresh_notebook(select=r["page"]["id"])
        extra = len([x for x in r["new"] if x is not r["page"]])
        self.last_roll.set(f"{'Updated' if r['page'] not in r['new'] else 'Added'} '{r['page']['title']}' in the Notebook"
                           + (f", with {extra} new page{'s' if extra != 1 else ''}" if extra else "") + ".")

    def _inn_copy(self, gm):
        if self.inn_cur is not None:
            self._inn_commit_all()
            self.clipboard_clear(); self.clipboard_append(tavern.place_text(self.inn_cur, gm=gm))
            self.last_roll.set(f"Copied {self.inn_cur['name']} ({'GM' if gm else 'player'} card) to the clipboard.")

    def _inn_export(self):
        p = self.inn_cur
        if p is None:
            messagebox.showinfo("Nothing to export", "Generate a place first."); return
        self._inn_commit_all()
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", p["name"]).strip("_") or "inn"
        self._save_text(tavern.place_markdown(p, gm=True), f"{safe}.md")

    def _inn_open_saved(self):
        saved = tavern.saved_places(self.notebook)
        if not saved:
            messagebox.showinfo("Open saved", "No saved inns or taverns yet. Use Add to Notebook."); return
        win = tk.Toplevel(self); win.title("Open a saved place"); win.geometry("420x360"); win.transient(self)
        lb = tk.Listbox(win); lb.pack(fill="both", expand=True, padx=8, pady=8)
        for page, place in saved:
            lb.insert("end", f"{page['title']}  ({place['quality']} {tavern.KINDS[place['kind']]['label'].lower()})")

        def go():
            sel = lb.curselection()
            if not sel:
                return
            place = copy.deepcopy(saved[sel[0]][1])
            self.inn_list.append(place)
            win.destroy()
            self._inn_refresh_list(select=len(self.inn_list) - 1)
        ttk.Button(win, text="Open", command=go).pack(pady=6)
        lb.bind("<Double-1>", lambda e: go())
        self.inn_saved_win = (win, lb, go)

    def _ask_line(self, title, prompt, initial="", parent=None):
        """Small modal text prompt. Returns the text or None."""
        win = tk.Toplevel(parent or self); win.title(title); win.transient(parent or self)
        v = tk.StringVar(value=str(initial)); out = {"v": None}
        ttk.Label(win, text=prompt, wraplength=360, justify="left").pack(padx=10, pady=(10, 4), anchor="w")
        e = ttk.Entry(win, textvariable=v, width=44); e.pack(padx=10); e.focus_set()

        def ok(*_):
            out["v"] = v.get()
            win.destroy()
        e.bind("<Return>", ok)
        ttk.Button(win, text="OK", command=ok).pack(pady=8)
        win.grab_set(); win.wait_window()
        return out["v"]

    # ---------- Treasure ----------
    def _build_loot(self):
        f = self.tab_loot
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Treasure level").grid(row=0, column=0, sticky="w")
        self.loot_lvl = tk.IntVar(value=self.config_data.get("party_level", 1))
        ttk.Spinbox(top, from_=1, to=20, textvariable=self.loot_lvl, width=5,
                    command=self._refresh_ledger).grid(row=0, column=1, sticky="w")
        ttk.Label(top, text="Rarity").grid(row=0, column=2, padx=(12, 0))
        self.loot_rar = RarityChecks(top, default=("common",)); self.loot_rar.grid(row=0, column=3, columnspan=3, sticky="w")
        self.loot_magic = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Magical/alchemical only", variable=self.loot_magic).grid(row=1, column=0, columnspan=2, sticky="w")
        self.loot_dupes = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Skip items already awarded", variable=self.loot_dupes).grid(row=1, column=2, columnspan=2, sticky="w")
        ttk.Label(top, text="Item traits (any)").grid(row=2, column=0, sticky="w")
        self.loot_tr = tk.StringVar(); ttk.Entry(top, textvariable=self.loot_tr, width=28).grid(row=2, column=1, columnspan=2, sticky="w")
        ttk.Button(top, text="Generate Full Level Package", command=self._gen_loot).grid(row=0, column=6, padx=6)
        ttk.Button(top, text="Reroll Selected", command=self._reroll).grid(row=1, column=6, padx=6, sticky="ew")
        ttk.Button(top, text="Make Card...", command=self._loot_card).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Button(top, text="Award Selected", command=lambda: self._award(True)).grid(row=0, column=7, sticky="ew")
        ttk.Button(top, text="Award All", command=lambda: self._award(False)).grid(row=1, column=7, sticky="ew")
        self.loot_to_party = tk.BooleanVar(value=self.config_data.get("award_to_party_loot", True))
        ttk.Checkbutton(top, text="Awarded treasure also goes in Party Loot", variable=self.loot_to_party,
                        command=lambda: (self.config_data.__setitem__("award_to_party_loot", self.loot_to_party.get()),
                                         storage.save("config", self.config_data))).grid(row=3, column=6, columnspan=2, sticky="w")

        single = ttk.Frame(top); single.grid(row=2, column=3, columnspan=5, sticky="w")
        ttk.Label(single, text="Single roll: level").pack(side="left")
        self.one_lvl = tk.IntVar(value=1); ttk.Spinbox(single, from_=0, to=25, textvariable=self.one_lvl, width=4).pack(side="left")
        self.one_kind = tk.StringVar(value="permanent")
        ttk.Combobox(single, textvariable=self.one_kind, values=["permanent", "consumable"],
                     state="readonly", width=11).pack(side="left", padx=4)
        ttk.Button(single, text="Add Random Item", command=self._roll_one).pack(side="left")

        lpane = ttk.PanedWindow(f, orient="horizontal")
        lpane.pack(fill="both", expand=True, padx=8)
        lleft = ttk.Frame(lpane); lpane.add(lleft, weight=3)
        self.item_view = RichText(lpane, self); lpane.add(self.item_view, weight=2)
        self.item_view.show_message("Select an item to see its rules text.")
        cols = ("kind", "lvl", "price", "rarity", "source")
        self.loot_tree = ttk.Treeview(lleft, columns=cols, show="tree headings", height=10)
        self.loot_tree.heading("#0", text="Item")
        self.loot_tree.column("#0", width=240)
        for c, t, w in zip(cols, ("Kind", "Lvl", "Price", "Rarity", "Source"), (85, 35, 80, 75, 200)):
            self.loot_tree.heading(c, text=t); self.loot_tree.column(c, width=w, stretch=(c == "source"))
        self.loot_tree.pack(fill="both", expand=True)
        self.loot_tree.bind("<<TreeviewSelect>>", lambda e: self._show_loot_item())
        self.loot_notes = tk.StringVar(); ttk.Label(f, textvariable=self.loot_notes, foreground="#a33").pack(anchor="w", padx=10)

        lb = ttk.LabelFrame(f, text="Ledger (awarded treasure)")
        lb.pack(fill="both", expand=True, padx=8, pady=6)
        self.ledger_sum = tk.StringVar(); ttk.Label(lb, textvariable=self.ledger_sum, font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=4)
        self.ledger_tree = ttk.Treeview(lb, columns=("lvl", "kind", "value", "date"), show="tree headings", height=6)
        self.ledger_tree.heading("#0", text="Name"); self.ledger_tree.column("#0", width=320)
        for c, t, w in zip(("lvl", "kind", "value", "date"), ("Lvl", "Kind", "Value", "Date"), (40, 90, 90, 100)):
            self.ledger_tree.heading(c, text=t); self.ledger_tree.column(c, width=w, stretch=False)
        self.ledger_tree.pack(side="left", fill="both", expand=True)
        self.ledger_tree.bind("<<TreeviewSelect>>", lambda e: self._show_ledger_item())
        ttk.Button(lb, text="Delete Entry", command=self._del_ledger).pack(side="left", anchor="n", padx=4)

    def _show_item(self, name=None, item=None):
        if item is not None and item.custom:
            self.item_view.show(render_entry(custom_item_entry(item))); return
        name = item.name if item is not None else name
        if not name or name == "Currency":
            return
        rowid = self.rules.resolve(f"item:{name}")
        e = self.rules.rule(rowid) if rowid else None
        if e:
            self.item_view.show(render_entry(e))
        else:
            custom = next((i for i in self.c_items if i.name == name), None)
            if custom:
                self.item_view.show(render_entry(custom_item_entry(custom)))
            else:
                self.item_view.show_message(f"No rules text stored for {name}. Re-download data to add item text.")

    def _show_loot_item(self):
        sel = self.loot_tree.selection()
        if sel:
            self._show_item(item=self.current_loot[int(sel[0])][1])

    def _show_ledger_item(self):
        sel = self.ledger_tree.selection()
        if sel:
            self._show_item(name=self.ledger[int(sel[0])]["name"])

    def _loot_pool(self):
        avoid = {e["name"] for e in self.ledger} if self.loot_dupes.get() else set()
        return filter_items(self.all_items, self.loot_rar.get(), self.loot_magic.get(),
                            _split(self.loot_tr.get()), exclude_names=avoid, systems=self.systems())

    def _gen_loot(self):
        lvl = int(self.loot_lvl.get())
        b = generate_level(self._loot_pool(), lvl, self.party_size())
        self.current_loot = [("permanent", i, i.price_gp) for i in b.permanent] + \
                            [("consumable", i, i.price_gp) for i in b.consumables] + \
                            [("currency", None, b.currency)]
        warn = self._missing_system_warning()
        notes = [f"From: {self.sys_var.get()}"] + b.notes + ([warn] if warn else [])
        if "sf" in self.systems():
            notes.append("Treasure counts and currency follow the Pathfinder table; Starfinder prices are "
                         "shown in credits and aren't added to gp totals")
        self.loot_notes.set("  |  ".join(notes))
        self._show_loot()
        self._refresh_ledger()

    def _show_loot(self):
        self.loot_tree.delete(*self.loot_tree.get_children())
        for idx, (kind, it, val) in enumerate(self.current_loot):
            if it is None:
                self.loot_tree.insert("", "end", iid=str(idx), text="Currency", values=(kind, "", price_text(val), "", ""))
            else:
                self.loot_tree.insert("", "end", iid=str(idx),
                                      text=it.name + (" [SF]" if system_of(it) == "sf" else "") + (" (custom)" if it.custom else ""),
                                      values=(kind, it.level, price_text(it), it.rarity, it.source))

    def _reroll(self):
        pool = self._loot_pool()
        taken = {it.name for _, it, _ in self.current_loot if it}
        for iid in self.loot_tree.selection():
            idx = int(iid)
            kind, it, _ = self.current_loot[idx]
            if it is None:
                continue
            new = pick(pool, it.level, kind == "consumable", 1, random.Random(), avoid=taken)
            if new:
                self.current_loot[idx] = (kind, new[0], new[0].price_gp)
                taken.add(new[0].name)
        self._show_loot()

    def _roll_one(self):
        kind = self.one_kind.get()
        new = pick(self._loot_pool(), int(self.one_lvl.get()), kind == "consumable", 1, random.Random())
        if not new:
            messagebox.showinfo("Nothing found", "No items match that level and filters.")
            return
        self.current_loot.append((kind, new[0], new[0].price_gp))
        self._show_loot()

    def _award(self, selected_only):
        ids = self.loot_tree.selection() if selected_only else self.loot_tree.get_children()
        lvl = int(self.loot_lvl.get())
        today = datetime.date.today().isoformat()
        to_party = getattr(self, "loot_to_party", None) is None or self.loot_to_party.get()
        for iid in ids:
            kind, it, val = self.current_loot[int(iid)]
            self.ledger.append({"level": lvl, "kind": kind, "name": it.name if it else "Currency",
                                "value_gp": val, "date": today})
            if to_party:
                if it is None:
                    ploot.credit_stash(self.party_loot, ploot.to_cp(val), f"Treasure, level {lvl}")
                else:
                    ploot.add(self.party_loot, ploot.new_entry(it.name, 1, value_gp=it.price_gp, level=it.level, kind=kind,
                                                               source="Treasure", rules_name="" if it.custom else it.name,
                                                               custom=it.custom))
        storage.save("ledger", self.ledger)
        if to_party and ids:
            self._pl_changed()
        keep = set(ids)
        self.current_loot = [x for i, x in enumerate(self.current_loot) if str(i) not in keep]
        self._show_loot()
        self._refresh_ledger()

    def _del_ledger(self):
        idxs = sorted((int(i) for i in self.ledger_tree.selection()), reverse=True)
        for i in idxs:
            del self.ledger[i]
        storage.save("ledger", self.ledger)
        self._refresh_ledger()

    def _refresh_ledger(self):
        if not hasattr(self, "ledger_tree"):
            return
        lvl = int(self.loot_lvl.get())
        if lvl not in TREASURE:
            return
        s = ledger_summary(self.ledger, lvl, self.party_size())
        self.ledger_sum.set(
            f"Level {lvl} progress:  Permanent {s['permanent'][0]}/{s['permanent'][1]}   "
            f"Consumables {s['consumables'][0]}/{s['consumables'][1]}   "
            f"Currency {s['currency'][0]:g}/{s['currency'][1]:g} gp   "
            f"Total value {s['value'][0]:g}/{s['value'][1]:g} gp")
        self.ledger_tree.delete(*self.ledger_tree.get_children())
        for i, e in enumerate(self.ledger):
            if e["level"] == lvl:
                self.ledger_tree.insert("", "end", iid=str(i), text=e["name"],
                                        values=(e["level"], e["kind"], price_text(e["value_gp"]), e["date"]))

    # ---------- Custom content ----------
    def _build_custom(self):
        f = self.tab_custom
        sub = TabbedPane(f, level=2); sub.pack(fill="both", expand=True, padx=4, pady=4)
        cpage = ttk.Frame(sub); sub.add(cpage, text="Creatures")
        ipage = ttk.Frame(sub); sub.add(ipage, text="Items")
        spage = ttk.Frame(sub); sub.add(spage, text="Spells")
        apage = ttk.Frame(sub); sub.add(apage, text="Abilities")
        rpage = ttk.Frame(sub); sub.add(rpage, text="Regions")
        self.custom_sub, self.custom_cpage = sub, cpage
        ttk.Label(f, text="Every dropdown is editable: pick a suggestion or type your own value.",
                  foreground="#555").pack(anchor="w", padx=8, pady=(0, 4))
        self._build_custom_creatures(cpage)
        self._build_custom_items(ipage)
        self._build_custom_spells(spage)
        self._build_custom_abilities(apage)
        self._build_regions(rpage)
        self._refresh_custom()
        self._library_changed()

    def _build_custom_creatures(self, cpage):
        lst = ttk.Frame(cpage); lst.pack(side="left", fill="y", padx=4, pady=4)
        self.ctree = ttk.Treeview(lst, columns=("lvl",), show="tree headings", height=20)
        self.ctree.heading("#0", text="Name"); self.ctree.heading("lvl", text="Lvl")
        self.ctree.column("#0", width=200); self.ctree.column("lvl", width=40)
        self.ctree.pack(fill="y", expand=True)
        self.ctree.bind("<<TreeviewSelect>>", lambda e: self._load_creature())
        lb = ttk.Frame(lst); lb.pack(fill="x", pady=4)
        ttk.Button(lb, text="New", command=self._new_creature).pack(side="left", padx=2)
        ttk.Button(lb, text="Delete", command=self._del_creature).pack(side="left", padx=2)
        ttk.Button(lb, text="Preview", command=self._preview_creature).pack(side="left", padx=2)

        outer = ttk.Frame(cpage); outer.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        ed = ttk.Frame(canvas)
        ed.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=ed, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)

        grid = ttk.Frame(ed); grid.pack(fill="x", padx=4, pady=4)
        self.cf = {}

        def row(r, c, label, widget):
            ttk.Label(grid, text=label).grid(row=r, column=c, sticky="w", padx=(0 if c == 0 else 12, 4), pady=2)
            widget.grid(row=r, column=c + 1, sticky="we", pady=2)

        def entry(key, width=10):
            v = tk.StringVar(); self.cf[key] = v
            return ttk.Entry(grid, textvariable=v, width=width)

        def combo(key, values=(), values_key=None, readonly=False, width=22):
            w = Combo(grid, values, values_key=values_key, readonly=readonly, width=width)
            self.cf[key] = w.var
            return w

        def multi(key, values_key, value_label=None, fmt=None, width=28):
            w = MultiField(grid, values_key=values_key, value_label=value_label, fmt=fmt, width=width)
            self.cf[key] = w
            return w

        def signed(choice, value):
            v = value.strip()
            if v and v[0] not in "+-":
                v = "+" + v
            return f"{choice} {v}".strip()

        def ranged(choice, value):
            return f"{choice} {value} feet".strip() if value else choice

        def speed(choice, value):
            if not value:
                return choice
            return f"{value} feet" if choice.lower() == "land" else f"{choice} {value} feet"

        row(0, 0, "Name", entry("name", 30))
        row(0, 2, "Level", combo("level", [str(n) for n in range(-1, 26)], width=6))
        row(1, 0, "Rarity", combo("rarity", RARITIES, readonly=True, width=12))
        row(1, 2, "Size", combo("size", values_key="sizes", width=14))
        row(9, 0, "Game system", combo("system", list(SYSTEM_NAMES.values()), readonly=True, width=14))
        row(2, 0, "Traits", multi("traits", "traits"))
        row(2, 2, "Source", combo("source", values_key="sources", width=24))
        row(3, 0, "Perception", entry("perception", 6))
        row(3, 2, "Senses", multi("senses", "senses", "range", ranged, width=22))
        row(4, 0, "Languages", multi("languages", "languages"))
        row(4, 2, "Skills", multi("skills", "skills", "mod", signed, width=22))
        row(5, 0, "AC", entry("ac", 6))
        row(5, 2, "HP", entry("hp", 6))
        saves = ttk.Frame(grid)
        for k, lbl in (("fort", "Fort"), ("ref", "Ref"), ("will", "Will")):
            ttk.Label(saves, text=lbl).pack(side="left")
            v = tk.StringVar(); self.cf[k] = v
            ttk.Entry(saves, textvariable=v, width=5).pack(side="left", padx=(2, 8))
        row(6, 0, "Saves", saves)
        row(6, 2, "Speed", multi("speed", "speeds", "ft", speed, width=22))
        row(7, 0, "Immunities", multi("immunities", "iwr"))
        row(7, 2, "Weaknesses", multi("weaknesses", "iwr", "value", width=22))
        row(8, 0, "Resistances", multi("resistances", "iwr", "value"))
        ttk.Button(grid, text="Suggest Stats from Level (GM Core)...", command=self._builder_dialog).grid(
            row=8, column=2, columnspan=2, sticky="we", padx=12, pady=4)
        grid.columnconfigure(1, weight=1); grid.columnconfigure(3, weight=1)

        gbox = ttk.LabelFrame(ed, text="Gear carried (one item per line; shown as the Items line)")
        gbox.pack(fill="x", padx=4, pady=4)
        self.c_gear = tk.Text(gbox, height=3, wrap="none"); self.c_gear.pack(fill="x", padx=4, pady=2)
        # Strike builder
        sbox = ttk.LabelFrame(ed, text="Strikes"); sbox.pack(fill="x", padx=4, pady=4)
        sb_row = ttk.Frame(sbox); sb_row.pack(fill="x", padx=4, pady=2)
        self.st_name = Combo(sb_row, values_key="strike_names", width=14)
        self.st_bonus = tk.StringVar(); self.st_dmg = tk.StringVar()
        self.st_type = Combo(sb_row, values_key="damage_types", width=11)
        self.st_traits = MultiField(sb_row, values_key="strike_traits", width=14, combo_width=11)
        self.st_effect = Combo(sb_row, values_key="abilities", width=14)
        for lbl, w in (("Name", self.st_name), ("Bonus", ttk.Entry(sb_row, textvariable=self.st_bonus, width=5)),
                       ("Damage", ttk.Entry(sb_row, textvariable=self.st_dmg, width=8)), ("Type", self.st_type),
                       ("Traits", self.st_traits), ("Effect", self.st_effect)):
            ttk.Label(sb_row, text=lbl).pack(side="left", padx=(4, 2)); w.pack(side="left")
        ttk.Button(sb_row, text="Add Strike", command=self._add_strike_line).pack(side="left", padx=6)
        ttk.Label(sbox, text="One per line:  Name | +bonus | damage | traits | effects   (edit freely)",
                  foreground="#777").pack(anchor="w", padx=4)
        self.c_strikes = tk.Text(sbox, height=3, wrap="none"); self.c_strikes.pack(fill="x", padx=4, pady=2)

        # Spell builder
        pbox = ttk.LabelFrame(ed, text="Spells"); pbox.pack(fill="x", padx=4, pady=4)
        sp_row = ttk.Frame(pbox); sp_row.pack(fill="x", padx=4, pady=2)
        self.sp_entry = Combo(sp_row, values_key="spell_entries", width=24)
        self.sp_entry.var.set("Arcane Innate Spells")
        self.sp_dc = tk.StringVar(); self.sp_atk = tk.StringVar()
        self.sp_rank = Combo(sp_row, values_key="spell_ranks", width=12); self.sp_rank.var.set("Rank 1")
        self.sp_spell = Combo(sp_row, values_key="spells", width=22)
        for lbl, w in (("Entry", self.sp_entry), ("DC", ttk.Entry(sp_row, textvariable=self.sp_dc, width=4)),
                       ("Attack", ttk.Entry(sp_row, textvariable=self.sp_atk, width=4)), ("Rank", self.sp_rank),
                       ("Spell", self.sp_spell)):
            ttk.Label(sp_row, text=lbl).pack(side="left", padx=(4, 2)); w.pack(side="left")
        ttk.Button(sp_row, text="Add Spell", command=self._add_spell_line).pack(side="left", padx=6)
        self.c_spells = tk.Text(pbox, height=2, wrap="none"); self.c_spells.pack(fill="x", padx=4, pady=2)

        # Abilities
        abox = ttk.LabelFrame(ed, text="Abilities (one per line:  Name [1|2|3|R|F] (traits): rules text)")
        abox.pack(fill="both", expand=True, padx=4, pady=4)
        ab_row = ttk.Frame(abox); ab_row.pack(fill="x", padx=4, pady=2)
        ttk.Label(ab_row, text="Ability").pack(side="left")
        self.ab_pick = Combo(ab_row, values_key="abilities", width=28); self.ab_pick.pack(side="left", padx=4)
        ttk.Button(ab_row, text="Insert (library or rules text)", command=self._insert_ability).pack(side="left")
        ttk.Label(ab_row, text="Your Abilities library entries come first.", foreground="#777").pack(side="left", padx=8)
        self.c_abilities = tk.Text(abox, height=6, wrap="word"); self.c_abilities.pack(fill="both", expand=True, padx=4, pady=2)
        dbox = ttk.LabelFrame(ed, text="Description (conditions you mention become clickable)")
        dbox.pack(fill="both", expand=True, padx=4, pady=4)
        self.c_notes = tk.Text(dbox, height=5, wrap="word"); self.c_notes.pack(fill="both", expand=True, padx=4, pady=2)
        brow = ttk.Frame(ed); brow.pack(anchor="e", padx=4, pady=6)
        ttk.Button(brow, text="Apply Template...", command=self._cu_apply_template).pack(side="left", padx=4)
        ttk.Button(brow, text="Save Creature", command=self._save_creature).pack(side="left")
        self._new_creature()

    def _add_strike_line(self):
        name = self.st_name.value()
        if not name:
            return
        bonus = self.st_bonus.get().strip()
        if bonus and bonus[0] not in "+-":
            bonus = "+" + bonus
        dmg = " ".join(x for x in (self.st_dmg.get().strip(), self.st_type.value()) if x)
        line = " | ".join([name, bonus, dmg, self.st_traits.get(), self.st_effect.value()])
        existing = self.c_strikes.get("1.0", "end").strip()
        self.c_strikes.delete("1.0", "end")
        self.c_strikes.insert("1.0", (existing + "\n" if existing else "") + line)
        for v in (self.st_bonus, self.st_dmg, self.st_name.var, self.st_type.var, self.st_effect.var):
            v.set("")
        self.st_traits.set("")

    def _add_spell_line(self):
        spell, entry = self.sp_spell.value(), self.sp_entry.value() or "Innate Spells"
        rank = self.sp_rank.value() or "Rank 1"
        if not spell:
            return
        lines = [l for l in self.c_spells.get("1.0", "end").splitlines() if l.strip()]
        idx = next((i for i, l in enumerate(lines) if l.split(";")[0].strip().startswith(entry)), None)
        if idx is None:
            bits = []
            if self.sp_dc.get().strip():
                bits.append(f"DC {self.sp_dc.get().strip()}")
            if self.sp_atk.get().strip():
                a = self.sp_atk.get().strip()
                bits.append(f"attack {a if a[0] in '+-' else '+' + a}")
            lines.append(f"{entry}{' ' + ', '.join(bits) if bits else ''}; {rank}: {spell}")
        else:
            parts = [p.strip() for p in lines[idx].split(";")]
            for i, p in enumerate(parts[1:], 1):
                label, _, names = p.partition(":")
                if label.strip().lower() == rank.lower():
                    names = [n.strip() for n in names.split(",") if n.strip()]
                    if spell not in names:
                        names.append(spell)
                    parts[i] = f"{label.strip()}: {', '.join(names)}"
                    break
            else:
                parts.append(f"{rank}: {spell}")
            lines[idx] = "; ".join(parts)
        self.c_spells.delete("1.0", "end"); self.c_spells.insert("1.0", "\n".join(lines))
        self.sp_spell.var.set("")

    def _insert_ability(self):
        name = self.ab_pick.value()
        if not name:
            return
        lib = lib_find(self.lib_abilities, name)
        if lib:
            line = ability_to_line(lib)
        else:
            rowid = self.rules.resolve(f"action:{name}")
            e = self.rules.rule(rowid) if rowid else None
            if e and e.get("kind") == "action":
                line = ability_to_line({"name": e["name"], "glyph": e.get("glyph"), "traits": e.get("traits"),
                                        "text": strip_links(e.get("text", ""))})
            else:
                line = f"{name}: "
        existing = self.c_abilities.get("1.0", "end").rstrip()
        self.c_abilities.delete("1.0", "end")
        self.c_abilities.insert("1.0", (existing + "\n" if existing else "") + line)
        self.ab_pick.var.set("")

    STAT_KEYS = ("perception", "senses", "languages", "skills", "fort", "ref", "will",
                 "immunities", "weaknesses", "resistances", "speed")

    def _new_creature(self):
        self._cf_extra = {}                     # template records ride along with the form but have no box of their own
        for v in self.cf.values():
            v.set("")
        self.cf["rarity"].set("common"); self.cf["source"].set("Hallowmead"); self.cf["level"].set("1")
        self.cf["size"].set("Medium")
        self.cf["system"].set("Starfinder" if self.sys_var.get() == "Starfinder" else "Pathfinder")
        for t in (self.c_gear, self.c_strikes, self.c_spells, self.c_abilities, self.c_notes):
            t.delete("1.0", "end")

    def _creature_from_form(self):
        f = self.cf
        lvl = self._int_or_none(f["level"].get())
        if not f["name"].get().strip() or lvl is None:
            messagebox.showwarning("Missing", "Name and a numeric level are required.")
            return None
        stats = {k: f[k].get().strip() for k in self.STAT_KEYS if f[k].get().strip()}
        for k in ("perception", "fort", "ref", "will"):
            if k in stats:
                n = self._int_or_none(stats[k].replace("+", ""))
                stats[k] = n if n is not None else stats[k]
        for key, box in (("gear", self.c_gear), ("strikes", self.c_strikes), ("spells", self.c_spells),
                         ("abilities", self.c_abilities)):
            val = box.get("1.0", "end").strip()
            if val:
                stats[key] = val
        stats.update(getattr(self, "_cf_extra", None) or {})
        size = f["size"].get().strip()
        return Creature(name=f["name"].get().strip(), level=lvl, rarity=f["rarity"].get() or "common",
                        traits=_split(f["traits"].get()), size=SIZE_CODE.get(size.lower(), size),
                        hp=self._int_or_none(f["hp"].get()), ac=self._int_or_none(f["ac"].get()),
                        source=f["source"].get().strip(), notes=self.c_notes.get("1.0", "end").strip(),
                        custom=True, stats=stats,
                        system="sf" if f["system"].get() == "Starfinder" else "pf")

    def _save_creature(self):
        c = self._creature_from_form()
        if not c:
            return
        self.c_creatures = [x for x in self.c_creatures if x.name != c.name] + [c]
        storage.save_custom_creatures(self.c_creatures)
        self._refresh_custom()

    def _preview_creature(self):
        c = self._creature_from_form()
        if c:
            win = tk.Toplevel(self); win.title(f"Preview: {c.name}"); win.geometry("620x700")
            v = RichText(win, self); v.pack(fill="both", expand=True); v.show(render(custom_details(c)))

    def _del_creature(self):
        names = {self.ctree.item(i, "text") for i in self.ctree.selection()}
        self.c_creatures = [x for x in self.c_creatures if x.name not in names]
        storage.save_custom_creatures(self.c_creatures)
        self._refresh_custom()

    def _load_creature(self):
        sel = self.ctree.selection()
        if not sel:
            return
        c = next((x for x in self.c_creatures if x.name == self.ctree.item(sel[0], "text")), None)
        if not c:
            return
        self._fill_creature_form(c)

    def _fill_creature_form(self, c):
        """Put a creature into the Custom Content form (nothing is saved until Save Creature)."""
        self._new_creature()
        self._cf_extra = {k: c.stats[k] for k in ("templates", "template_base") if k in (c.stats or {})}
        for k in ("name", "rarity", "source"):
            self.cf[k].set(getattr(c, k) or "")
        self.cf["size"].set(SIZE_LABEL.get(c.size, c.size or ""))
        self.cf["system"].set(SYSTEM_NAMES.get(system_of(c), "Pathfinder"))
        self.cf["level"].set(str(c.level)); self.cf["traits"].set(", ".join(c.traits))
        self.cf["hp"].set("" if c.hp is None else str(c.hp)); self.cf["ac"].set("" if c.ac is None else str(c.ac))
        st = c.stats or {}
        for k in self.STAT_KEYS:
            v = st.get(k, "")
            self.cf[k].set(f"{v:+d}" if isinstance(v, int) else str(v))
        self.c_gear.insert("1.0", st.get("gear", ""))
        self.c_strikes.insert("1.0", st.get("strikes", ""))
        self.c_spells.insert("1.0", st.get("spells", ""))
        self.c_abilities.insert("1.0", st.get("abilities", ""))
        self.c_notes.insert("1.0", c.notes or "")

    # --- items ---
    def _build_custom_items(self, ipage):
        ibox = ttk.Frame(ipage); ibox.pack(fill="both", expand=True, padx=6, pady=6)
        grid = ttk.Frame(ibox); grid.pack(fill="x")
        self.itf = {}

        def row(r, label, widget, key, var=None):
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=2, padx=(0, 6))
            widget.grid(row=r, column=1, sticky="we", pady=2)
            self.itf[key] = var if var is not None else widget
        v = tk.StringVar(); row(0, "Name", ttk.Entry(grid, textvariable=v, width=40), "name", v)
        w = Combo(grid, [str(n) for n in range(0, 26)], width=6); row(1, "Level", w, "level", w.var)
        w = Combo(grid, RARITIES, readonly=True, width=12); row(2, "Rarity", w, "rarity", w.var)
        row(3, "Traits", MultiField(grid, values_key="item_traits"), "traits")
        v = tk.StringVar(); row(4, "Price (gp)", ttk.Entry(grid, textvariable=v, width=10), "price_gp", v)
        w = Combo(grid, values_key="item_sources", width=30); row(5, "Source", w, "source", w.var)
        v = tk.StringVar(); row(6, "Notes", ttk.Entry(grid, textvariable=v, width=60), "notes", v)
        w = Combo(grid, list(SYSTEM_NAMES.values()), readonly=True, width=14); row(7, "Game system", w, "system", w.var)
        w.var.set("Pathfinder")
        grid.columnconfigure(1, weight=1)
        self.itf["rarity"].set("common"); self.itf["source"].set("Hallowmead")
        self.it_cons = tk.BooleanVar()
        ttk.Checkbutton(ibox, text="Consumable", variable=self.it_cons).pack(anchor="w")
        bb = ttk.Frame(ibox); bb.pack(fill="x")
        ttk.Button(bb, text="Save Item", command=self._save_item).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete Selected", command=self._del_item).pack(side="left", padx=2)
        ttk.Button(bb, text="Make Card...", command=self._item_card).pack(side="left", padx=2)
        self.itree = ttk.Treeview(ibox, columns=("lvl", "kind", "price"), show="tree headings")
        self.itree.heading("#0", text="Name")
        for c, t in zip(("lvl", "kind", "price"), ("Lvl", "Kind", "Price")):
            self.itree.heading(c, text=t); self.itree.column(c, width=70)
        self.itree.pack(fill="both", expand=True, pady=4)
        self.itree.bind("<<TreeviewSelect>>", lambda e: self._load_item())

    # --- regions ---
    def _build_regions(self, rpage):
        lst = ttk.Frame(rpage); lst.pack(side="left", fill="y", padx=4, pady=4)
        self.rtree = ttk.Treeview(lst, show="tree", height=20); self.rtree.column("#0", width=260)
        self.rtree.pack(fill="y", expand=True)
        self.rtree.bind("<<TreeviewSelect>>", lambda e: self._load_region())
        lb = ttk.Frame(lst); lb.pack(fill="x", pady=4)
        ttk.Button(lb, text="New", command=self._new_region).pack(side="left", padx=2)
        ttk.Button(lb, text="Delete", command=self._del_region).pack(side="left", padx=2)

        ed = ttk.Frame(rpage); ed.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        ttk.Label(ed, text="A creature fits the region if it matches ANY listed trait, family, type, source, or "
                           "creature name, and has none of the excluded traits. Listed creatures are also picked "
                           "more often. Pathfinder stat blocks have no habitat field, so regions are yours to define.",
                  wraplength=640, foreground="#555", justify="left").pack(anchor="w", pady=(0, 6))
        grid = ttk.Frame(ed); grid.pack(fill="x")
        self.rf = {}
        self.rf_name = tk.StringVar(); self.rf_notes = tk.StringVar()
        for r, (label, widget) in enumerate((("Name", ttk.Entry(grid, textvariable=self.rf_name, width=40)),
                                             ("Notes", ttk.Entry(grid, textvariable=self.rf_notes, width=60)))):
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=2); widget.grid(row=r, column=1, sticky="we")
        for r, (key, label, vk) in enumerate((("traits", "Traits", "traits"), ("families", "Families", "families"),
                                              ("types", "Creature types", "types"), ("sources", "Books / sources", "sources"),
                                              ("creatures", "Specific creatures", "creature_names"),
                                              ("exclude_traits", "Exclude traits", "traits")), start=2):
            fmt = (lambda ch, v: strip_count(ch)) if key == "families" else None
            w = MultiField(grid, values_key=vk, fmt=fmt, width=44, combo_width=24)
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=2, padx=(0, 6))
            w.grid(row=r, column=1, sticky="we", pady=2)
            self.rf[key] = w
        grid.columnconfigure(1, weight=1)
        bb = ttk.Frame(ed); bb.pack(fill="x", pady=6)
        ttk.Button(bb, text="Save Region", command=self._save_region).pack(side="left", padx=2)
        ttk.Button(bb, text="Test at Party Level", command=self._test_region).pack(side="left", padx=2)
        self.region_test = tk.StringVar()
        ttk.Label(ed, textvariable=self.region_test, wraplength=640, justify="left").pack(anchor="w")
        self._refresh_regions()

    def _region_from_form(self):
        name = self.rf_name.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Give the region a name."); return None
        r = {"name": name, "notes": self.rf_notes.get().strip()}
        for k, w in self.rf.items():
            vals = [strip_count(v) if k == "families" else v for v in w.items()]
            if vals:
                r[k] = vals
        return r

    def _new_region(self):
        self.rf_name.set(""); self.rf_notes.set(""); self.region_test.set("")
        for w in self.rf.values():
            w.set("")

    def _load_region(self):
        sel = self.rtree.selection()
        r = next((x for x in self.regions if sel and x["name"] == self.rtree.item(sel[0], "text")), None)
        if not r:
            return
        self.rf_name.set(r["name"]); self.rf_notes.set(r.get("notes", ""))
        for k, w in self.rf.items():
            w.set(r.get(k, []))
        self.region_test.set("")

    def _save_region(self):
        r = self._region_from_form()
        if not r:
            return
        self.regions = [x for x in self.regions if x["name"] != r["name"]] + [r]
        storage.save("regions", self.regions)
        self._refresh_regions()

    def _del_region(self):
        sel = self.rtree.selection()
        names = {self.rtree.item(i, "text") for i in sel}
        self.regions = [x for x in self.regions if x["name"] not in names]
        storage.save("regions", self.regions)
        self._refresh_regions()

    def _test_region(self):
        r = self._region_from_form()
        if not r:
            return
        pl = self.party_level()
        hits = [c for c in self.all_creatures if not c.is_hazard and self.in_systems(c) and matches_spec(c, r)
                and xp_of(c, pl) is not None]
        sample = ", ".join(sorted({c.name for c in hits})[:25])
        self.region_test.set(f"{len(hits)} creatures fit this region at party level {pl}."
                             + (f" Examples: {sample}" if sample else ""))

    def _refresh_regions(self):
        if hasattr(self, "rtree"):
            self.rtree.delete(*self.rtree.get_children())
            for r in sorted(self.regions, key=lambda x: x["name"]):
                self.rtree.insert("", "end", text=r["name"])
        self.vocab["regions"] = [r["name"] for r in sorted(self.regions, key=lambda x: x["name"])]
        self._apply_vocab()

    # --- dropdown vocabulary ---
    def _load_vocab_async(self):
        def work():
            try:
                v = cached_vocab(storage.VOCAB, storage.DETAILS, storage.INDEX,
                                 lambda: build_vocab(self.f_creatures, self.f_items, self.details_db))
            except Exception:
                v = build_vocab(self.f_creatures, self.f_items, None)
            self.after(0, self._vocab_ready, v)
        threading.Thread(target=work, daemon=True).start()

    def _vocab_ready(self, v):
        regions = self.vocab.get("regions", [])
        self.vocab = dict(v)
        self.vocab["regions"] = regions
        self._merge_custom_vocab()
        self._apply_vocab()

    def _merge_custom_vocab(self):
        """Fold custom creatures/items into the suggestion lists."""
        v = self.vocab
        for key, extra in (("traits", [t for c in self.c_creatures for t in c.traits]),
                           ("sources", [c.source for c in self.c_creatures if c.source]),
                           ("creature_names", [c.name for c in self.c_creatures]),
                           ("item_traits", [t for i in self.c_items for t in i.traits]),
                           ("item_sources", [i.source for i in self.c_items if i.source]),
                           ("spells", [x["name"] for x in self.lib_spells]),
                           ("abilities", [x["name"] for x in self.lib_abilities]),
                           ("ancestries", npcgen.DEFAULT_ANCESTRIES + self.rules.rule_names("ancestry")
                            + [p.get("ancestry") for p in getattr(self, "notebook", []) if p.get("ancestry")]),
                           ("item_names", sorted({i.name for i in self.all_items})),
                           ("link_targets", [p["title"] for p in getattr(self, "notebook", [])]
                            + [c.name for c in self.c_creatures])):
            cur = list(v.get(key, []))
            seen = {x.lower() for x in cur}
            for x in extra:
                if x and x.lower() not in seen:
                    cur.append(x); seen.add(x.lower())
            v[key] = sorted(cur, key=str.lower) if key == "creature_names" else cur

    def _apply_vocab(self):
        stack = [self]
        while stack:
            w = stack.pop()
            key = getattr(w, "values_key", None)
            if key and key in self.vocab and hasattr(w, "set_values"):
                w.set_values(self.vocab[key])
            if isinstance(w, MultiField):
                continue
            try:
                stack.extend(w.winfo_children())
            except Exception:
                pass

    # --- custom spells ---
    def _lib_form(self, parent, fields):
        """Grid of labelled widgets. fields: (key, label, kind, options). Returns {key: getter/setter obj}."""
        grid = ttk.Frame(parent); grid.pack(fill="x", padx=4, pady=4)
        out = {}
        for r, (key, label, kind, opts) in enumerate(fields):
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=2, padx=(0, 6))
            if kind == "entry":
                v = tk.StringVar(); w = ttk.Entry(grid, textvariable=v, width=opts or 40); out[key] = v
            elif kind == "combo":
                w = Combo(grid, opts or (), width=24); out[key] = w.var
            elif kind == "vcombo":
                w = Combo(grid, values_key=opts, width=24); out[key] = w.var
            elif kind == "readonly":
                w = Combo(grid, opts or (), readonly=True, width=14); out[key] = w.var
            elif kind == "multi":
                w = MultiField(grid, values=opts or (), width=36); out[key] = w
            elif kind == "checks":
                w = ttk.Frame(grid); vs = {}
                for o in opts:
                    vs[o] = tk.BooleanVar(); ttk.Checkbutton(w, text=o.title(), variable=vs[o]).pack(side="left")
                out[key] = vs
            w.grid(row=r, column=1, sticky="we", pady=2)
        grid.columnconfigure(1, weight=1)
        return out

    def _build_custom_spells(self, page):
        lst = ttk.Frame(page); lst.pack(side="left", fill="y", padx=4, pady=4)
        self.sp_tree = ttk.Treeview(lst, columns=("rank",), show="tree headings", height=20)
        self.sp_tree.heading("#0", text="Spell"); self.sp_tree.heading("rank", text="Rank")
        self.sp_tree.column("#0", width=200); self.sp_tree.column("rank", width=50)
        self.sp_tree.pack(fill="y", expand=True)
        self.sp_tree.bind("<<TreeviewSelect>>", lambda e: self._load_spell())
        bb = ttk.Frame(lst); bb.pack(fill="x", pady=4)
        ttk.Button(bb, text="New", command=self._new_spell).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete", command=self._del_spell).pack(side="left", padx=2)
        ttk.Button(bb, text="Preview", command=self._preview_spell).pack(side="left", padx=2)
        ed = ttk.Frame(page); ed.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        gen = ttk.LabelFrame(ed, text="Generate spells")
        gen.pack(fill="x", padx=4, pady=(0, 4))
        cfg = self.config_data.get("spellgen", {})
        self.sg_vars, self.sg_results = {}, []
        for c, (key, label, values, default, width) in enumerate((
                ("kind", "Kind", ["Spell", "Cantrip"], "Spell", 8),
                ("rank", "Rank", ["any"] + [str(n) for n in range(1, 11)], "1", 5),
                ("tradition", "Tradition", ["any"] + TRADITIONS, "any", 8),
                ("style", "Style", [spellgen.STYLE_LABELS[k] for k in spellgen.STYLES], "Standard", 11),
                ("shape", "Shape", ["any", "area", "bolt", "hex", "ward", "utility"], "any", 8))):
            ttk.Label(gen, text=label).grid(row=0, column=c * 2, sticky="w", padx=(6, 2), pady=4)
            w = Combo(gen, values, readonly=True, width=width)
            w.var.set(cfg.get(key, default))
            w.grid(row=0, column=c * 2 + 1, sticky="w")
            self.sg_vars[key] = w.var
        ttk.Label(gen, text="How many").grid(row=0, column=10, sticky="w", padx=(10, 2))
        self.sg_count = tk.StringVar(value=str(cfg.get("count", 8)))
        ttk.Spinbox(gen, from_=1, to=20, textvariable=self.sg_count, width=4).grid(row=0, column=11, sticky="w")
        bar = ttk.Frame(gen); bar.grid(row=1, column=0, columnspan=12, sticky="w", padx=4)
        for text, cmd in (("Generate", self._sg_generate), ("Add One More", lambda: self._sg_generate(1, True)),
                          ("Keep Selected", lambda: self._sg_keep(False)), ("Keep All", lambda: self._sg_keep(True)),
                          ("Remove Selected", self._sg_remove)):
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=2, pady=2)
        rf = ttk.Frame(gen); rf.grid(row=2, column=0, columnspan=12, sticky="we", padx=6, pady=2)
        self.sg_tree = ttk.Treeview(rf, columns=("rank", "what"), show="tree headings", height=6, selectmode="extended")
        self.sg_tree.heading("#0", text="Generated (click one to read it below)"); self.sg_tree.heading("rank", text="Rank")
        self.sg_tree.heading("what", text="Kind of spell")
        self.sg_tree.column("#0", width=330); self.sg_tree.column("rank", width=60); self.sg_tree.column("what", width=200)
        rsb = ttk.Scrollbar(rf, command=self.sg_tree.yview); self.sg_tree.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right", fill="y"); self.sg_tree.pack(side="left", fill="x", expand=True)
        self.sg_tree.bind("<<TreeviewSelect>>", lambda e: self._sg_pick())
        self.sg_info = tk.StringVar(value="Generate a batch, read them, then keep the ones you like. Nothing is saved until you "
                                          "keep it. To keep one with your own edits, edit it below and press Save Spell.")
        ttk.Label(gen, textvariable=self.sg_info, foreground="#666", wraplength=760, justify="left").grid(
            row=3, column=0, columnspan=12, sticky="w", padx=6, pady=(0, 4))
        self.spf = self._lib_form(ed, [
            ("name", "Name", "entry", 40), ("spell_kind", "Type", "readonly", SPELL_KINDS),
            ("rank", "Rank", "readonly", [str(n) for n in range(1, 11)]),
            ("rarity", "Rarity", "readonly", RARITIES), ("traditions", "Traditions", "checks", TRADITIONS),
            ("traits", "Traits", "multi", SPELL_TRAITS), ("cast", "Cast", "combo", CAST_OPTIONS),
            ("range", "Range", "combo", ["touch", "30 feet", "60 feet", "120 feet", "500 feet", "planetary"]),
            ("area_size", "Area size (ft)", "combo", ["5", "10", "15", "20", "30", "60"]),
            ("area_type", "Area type", "combo", AREA_TYPES),
            ("targets", "Targets", "combo", ["1 creature", "1 or 2 creatures", "up to 5 creatures", "1 object"]),
            ("defense", "Defense", "combo", DEFENSES),
            ("duration", "Duration", "combo", ["1 round", "1 minute", "10 minutes", "1 hour", "sustained up to 1 minute",
                                               "until the end of your next turn", "unlimited"]),
            ("damage", "Damage (base)", "entry", 12), ("damage_type", "Damage type", "vcombo", "damage_types"),
            ("heighten_damage", "Heighten damage by", "entry", 12),
            ("heighten_interval", "...every N ranks", "readonly", ["1", "2", "3"]),
            ("source", "Source", "vcombo", "sources")])
        ttk.Label(ed, text="Flavor (what it is like to cast and to watch; not rules)").pack(anchor="w", padx=4)
        self.sp_flavor = tk.Text(ed, height=4, wrap="word"); self.sp_flavor.pack(fill="x", padx=4)
        ttk.Label(ed, text="Description (the rules)").pack(anchor="w", padx=4)
        self.sp_desc = tk.Text(ed, height=5, wrap="word"); self.sp_desc.pack(fill="both", expand=True, padx=4)
        ttk.Label(ed, text="Heightened entries, one per line, e.g.  Heightened (+1) The damage increases by 2d6.  "
                           "or  Heightened (5th) You can target up to 5 creatures.", foreground="#555").pack(anchor="w", padx=4)
        self.sp_height = tk.Text(ed, height=3, wrap="word"); self.sp_height.pack(fill="x", padx=4)
        ttk.Button(ed, text="Save Spell", command=self._save_spell).pack(anchor="e", padx=4, pady=6)
        self._new_spell()

    def _spell_from_form(self):
        f = self.spf
        name = f["name"].get().strip()
        if not name:
            messagebox.showwarning("Missing", "Give the spell a name."); return None
        sp = {k: f[k].get().strip() for k in ("name", "spell_kind", "rank", "rarity", "cast", "range", "area_size",
                                                "area_type", "targets", "defense", "duration", "damage",
                                                "damage_type", "heighten_damage", "heighten_interval", "source")}
        sp["traditions"] = [t for t, v in f["traditions"].items() if v.get()]
        sp["traits"] = f["traits"].items()
        sp["description"] = self.sp_desc.get("1.0", "end").strip()
        sp["heightened"] = self.sp_height.get("1.0", "end").strip()
        sp["flavor"] = self.sp_flavor.get("1.0", "end").strip()
        return sp

    def _new_spell(self):
        for k, v in self.spf.items():
            if isinstance(v, dict):
                for b in v.values():
                    b.set(False)
            else:
                v.set("")
        self.spf["spell_kind"].set("Spell"); self.spf["rank"].set("1"); self.spf["rarity"].set("common")
        self.spf["cast"].set("2"); self.spf["heighten_interval"].set("1"); self.spf["source"].set("Hallowmead")
        self.sp_desc.delete("1.0", "end"); self.sp_height.delete("1.0", "end"); self.sp_flavor.delete("1.0", "end")

    def _sg_settings(self):
        v = {k: var.get() for k, var in self.sg_vars.items()}
        v["count"] = max(1, min(20, self._int_or_none(str(self.sg_count.get())) or 8))
        self.config_data["spellgen"] = v
        storage.save("config", self.config_data)
        return v

    def _sg_generate(self, count=None, append=False):
        """Roll a batch of spells into the list below the settings. Nothing is saved until you keep it."""
        v = self._sg_settings()
        style = next((k for k, lab in spellgen.STYLE_LABELS.items() if lab == v["style"]), "standard")
        rank = "any" if v["rank"] == "any" else int(v["rank"] or 1)
        have = [x["name"] for x in self.lib_spells] + ([r["spell"]["name"] for r in self.sg_results] if append else [])
        new = spellgen.generate_spells(count or v["count"], rank, style, v["tradition"], v["kind"], random.Random(),
                                       self.story_registry, v["shape"], avoid=have)
        if not append:
            self.sg_results = []
        rows = [{"rid": uuid.uuid4().hex[:8], "spell": sp} for sp in new]
        self.sg_results += rows
        self._sg_refresh(select=rows[0]["rid"] if rows else None)
        self.sg_info.set(f"Generated {len(rows)} spell{'s' if len(rows) != 1 else ''}. Click one to read it, select the ones you "
                         "want (Ctrl or Shift for several), and press Keep Selected." if rows else
                         "Couldn't make a new spell that is different from the ones you already have. Try other settings.")

    def _sg_refresh(self, select=None):
        self.sg_tree.delete(*self.sg_tree.get_children())
        for r in self.sg_results:
            sp = r["spell"]
            self.sg_tree.insert("", "end", iid=r["rid"], text=sp["name"],
                                values=("cantrip" if sp.get("spell_kind") == "Cantrip" else sp.get("rank", ""),
                                        f"{sp.get('shape', '')}, {sp.get('theme', '')}".strip(", ")))
        if select and self.sg_tree.exists(select):
            self.sg_tree.selection_set(select)
            self._sg_pick()

    def _sg_pick(self):
        sel = self.sg_tree.selection()
        if len(sel) != 1:
            return
        r = next((x for x in self.sg_results if x["rid"] == sel[0]), None)
        if r:
            self._spell_put(r["spell"])

    def _sg_keep(self, everything=False):
        ids = [r["rid"] for r in self.sg_results] if everything else list(self.sg_tree.selection())
        rows = [r for r in self.sg_results if r["rid"] in ids]
        if not rows:
            messagebox.showinfo("Keep spells", "Select the spells you want to keep, or press Keep All."); return
        kept = [r["spell"]["name"] for r in rows if self._keep_spell(r["spell"], "Spell Generator", persist=False)]
        skipped = len(rows) - len(kept)
        self.sg_results = [r for r in self.sg_results if r["rid"] not in ids]
        storage.save("spells", self.lib_spells)
        self._library_changed()
        self._sg_refresh()
        self.sg_info.set(f"Kept {len(kept)} spell{'s' if len(kept) != 1 else ''} in your spells."
                         + (f" {skipped} already existed and was skipped." if skipped == 1 else
                            f" {skipped} already existed and were skipped." if skipped else ""))

    def _sg_remove(self):
        ids = set(self.sg_tree.selection())
        self.sg_results = [r for r in self.sg_results if r["rid"] not in ids]
        self._sg_refresh()

    def _spell_put(self, sp):
        """Fill the spell form from a spell dict (one of yours or a generated one)."""
        self._new_spell()
        for k, v in self.spf.items():
            if k == "traditions":
                for t, b in v.items():
                    b.set(t in sp.get("traditions", []))
            elif k == "traits":
                v.set(sp.get("traits", []))
            else:
                v.set(str(sp.get(k, "") or ""))
        self.sp_desc.insert("1.0", sp.get("description", ""))
        self.sp_height.insert("1.0", sp.get("heightened", ""))
        self.sp_flavor.insert("1.0", sp.get("flavor", ""))

    def _load_spell(self):
        sel = self.sp_tree.selection()
        sp = lib_find(self.lib_spells, self.sp_tree.item(sel[0], "text")) if sel else None
        if not sp:
            return
        self._spell_put(sp)

    def _save_spell(self):
        sp = self._spell_from_form()
        if not sp:
            return
        self.lib_spells = [x for x in self.lib_spells if norm(x["name"]) != norm(sp["name"])] + [sp]
        storage.save("spells", self.lib_spells)
        self._library_changed()
        if any(norm(r["spell"]["name"]) == norm(sp["name"]) for r in self.sg_results):     # kept: off the generated list
            self.sg_results = [r for r in self.sg_results if norm(r["spell"]["name"]) != norm(sp["name"])]
            self._sg_refresh()
        self.sg_info.set(f"Saved '{sp['name']}' to your spells.")

    def _del_spell(self):
        names = {norm(self.sp_tree.item(i, "text")) for i in self.sp_tree.selection()}
        self.lib_spells = [x for x in self.lib_spells if norm(x["name"]) not in names]
        storage.save("spells", self.lib_spells)
        self._library_changed()

    def _preview_spell(self):
        sp = self._spell_from_form()
        if sp:
            win = tk.Toplevel(self); win.title(f"Preview: {sp['name']}"); win.geometry("560x520")
            v = RichText(win, self); v.pack(fill="both", expand=True); v.show(render_entry(spell_entry(sp)))

    # --- custom abilities ---
    def _build_custom_abilities(self, page):
        lst = ttk.Frame(page); lst.pack(side="left", fill="y", padx=4, pady=4)
        self.ab_tree = ttk.Treeview(lst, columns=("act",), show="tree headings", height=20)
        self.ab_tree.heading("#0", text="Ability"); self.ab_tree.heading("act", text="Act")
        self.ab_tree.column("#0", width=200); self.ab_tree.column("act", width=40)
        self.ab_tree.pack(fill="y", expand=True)
        self.ab_tree.bind("<<TreeviewSelect>>", lambda e: self._load_lib_ability())
        bb = ttk.Frame(lst); bb.pack(fill="x", pady=4)
        ttk.Button(bb, text="New", command=self._new_lib_ability).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete", command=self._del_lib_ability).pack(side="left", padx=2)
        ttk.Button(bb, text="Preview", command=self._preview_lib_ability).pack(side="left", padx=2)
        ed = ttk.Frame(page); ed.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        ttk.Label(ed, text="Write a signature ability once, then insert it into any creature from the creature "
                           "editor's Ability picker. Library abilities are also clickable rules entries.",
                  foreground="#555", wraplength=640, justify="left").pack(anchor="w", pady=(0, 4))
        self.abf = self._lib_form(ed, [
            ("name", "Name", "entry", 40),
            ("glyph", "Actions", "readonly", ["", "[1]", "[2]", "[3]", "[R]", "[F]"]),
            ("traits", "Traits", "multi", ABILITY_TRAITS),
            ("frequency", "Frequency", "combo", ["once per round", "once per minute", "once per hour", "once per day"]),
            ("trigger", "Trigger", "entry", 60), ("requirements", "Requirements", "entry", 60),
            ("source", "Source", "vcombo", "sources")])
        ttk.Label(ed, text="Effect / rules text (conditions you mention become clickable)").pack(anchor="w", padx=4)
        self.ab_text = tk.Text(ed, height=8, wrap="word"); self.ab_text.pack(fill="both", expand=True, padx=4)
        ttk.Button(ed, text="Save Ability", command=self._save_lib_ability).pack(anchor="e", padx=4, pady=6)
        self._new_lib_ability()

    def _ability_from_form(self):
        f = self.abf
        name = f["name"].get().strip()
        if not name:
            messagebox.showwarning("Missing", "Give the ability a name."); return None
        ab = {k: f[k].get().strip() for k in ("name", "glyph", "frequency", "trigger", "requirements", "source")}
        ab["traits"] = f["traits"].items()
        ab["text"] = self.ab_text.get("1.0", "end").strip()
        return ab

    def _new_lib_ability(self):
        for v in self.abf.values():
            v.set("")
        self.abf["source"].set("Hallowmead")
        self.ab_text.delete("1.0", "end")

    def _load_lib_ability(self):
        sel = self.ab_tree.selection()
        ab = lib_find(self.lib_abilities, self.ab_tree.item(sel[0], "text")) if sel else None
        if not ab:
            return
        self._new_lib_ability()
        for k, v in self.abf.items():
            v.set(ab.get(k, []) if k == "traits" else str(ab.get(k, "") or ""))
        self.ab_text.insert("1.0", ab.get("text", ""))

    def _save_lib_ability(self):
        ab = self._ability_from_form()
        if not ab:
            return
        self.lib_abilities = [x for x in self.lib_abilities if norm(x["name"]) != norm(ab["name"])] + [ab]
        storage.save("abilities", self.lib_abilities)
        self._library_changed()

    def _del_lib_ability(self):
        names = {norm(self.ab_tree.item(i, "text")) for i in self.ab_tree.selection()}
        self.lib_abilities = [x for x in self.lib_abilities if norm(x["name"]) not in names]
        storage.save("abilities", self.lib_abilities)
        self._library_changed()

    def _preview_lib_ability(self):
        ab = self._ability_from_form()
        if ab:
            win = tk.Toplevel(self); win.title(f"Preview: {ab['name']}"); win.geometry("520x380")
            v = RichText(win, self); v.pack(fill="both", expand=True); v.show(render_entry(ability_entry(ab)))

    def _library_changed(self):
        # the lists first, so they are right even if one of the steps below has a problem
        self.sp_tree.delete(*self.sp_tree.get_children())
        for sp in sorted(self.lib_spells, key=lambda x: (int(str(x.get("rank") or 1).strip() or 1), x["name"])):
            self.sp_tree.insert("", "end", text=sp["name"], values=(sp.get("rank", ""),))
        self.ab_tree.delete(*self.ab_tree.get_children())
        for ab in sorted(self.lib_abilities, key=lambda x: x["name"]):
            self.ab_tree.insert("", "end", text=ab["name"], values=(ab.get("glyph", ""),))
        failed = []
        for step in (self._register_custom_rules, self._refresh_spell_pool,
                     lambda: self._merge_custom_vocab() if hasattr(self, "vocab") else None,
                     lambda: self._apply_vocab() if hasattr(self, "vocab") else None):
            try:
                step()
            except Exception as e:                       # report it instead of silently leaving the rest undone
                failed.append(f"{type(e).__name__}: {e}")
        if failed and hasattr(self, "last_roll"):
            self.last_roll.set("Your spells are saved, but updating the rules links failed: " + "; ".join(failed[:2]))

    # --- duplicate to custom ---
    def _duplicate_to_custom(self, c):
        if not c:
            messagebox.showinfo("Select a creature", "Select a creature first."); return
        if c.is_hazard:
            messagebox.showinfo("Hazard", "Duplicate to Custom works for creatures, not hazards."); return
        d = self.details_for(c)
        if not d:
            messagebox.showinfo("No stat block", f"No stat block stored for {c.name}. Re-download data first."); return
        existing = {x.name.lower() for x in self.c_creatures}
        name, n = f"{d['name']} (copy)", 2
        while name.lower() in existing:
            name, n = f"{d['name']} (copy {n})", n + 1
        new = Creature(**details_to_custom(d, name=name), system=system_of(c))
        self.c_creatures.append(new)
        storage.save_custom_creatures(self.c_creatures)
        self._refresh_custom()
        self.nb.select(self.tab_custom)
        self.custom_sub.select(self.custom_cpage)
        for iid in self.ctree.get_children():
            if self.ctree.item(iid, "text") == name:
                self.ctree.selection_set(iid); self.ctree.see(iid)
        self._load_creature()

    # ---------- Sessions ----------
    def _build_sessions(self):
        f = self.tab_sessions
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        self.xp_var = tk.StringVar()
        ttk.Label(top, textvariable=self.xp_var, font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(top, text="Adjust XP...", command=self._adjust_xp_dialog).pack(side="left", padx=8)
        ttk.Button(top, text="Level Up Party", command=self._level_up).pack(side="left")

        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.ss_tree = ttk.Treeview(left, columns=("lvl", "date"), show="tree headings", height=18)
        self.ss_tree.heading("#0", text="Session"); self.ss_tree.heading("lvl", text="Lvl"); self.ss_tree.heading("date", text="Date")
        self.ss_tree.column("#0", width=170); self.ss_tree.column("lvl", width=35); self.ss_tree.column("date", width=85)
        self.ss_tree.pack(fill="both", expand=True)
        self.ss_tree.bind("<<TreeviewSelect>>", lambda e: self._show_session())
        bb = ttk.Frame(left); bb.pack(fill="x", pady=4)
        ttk.Button(bb, text="New", command=self._new_session_dialog).pack(side="left", padx=2)
        ttk.Button(bb, text="Edit", command=lambda: self._new_session_dialog(edit=True)).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete", command=self._del_session).pack(side="left", padx=2)

        mid = ttk.Frame(pane); pane.add(mid, weight=3)
        mb = ttk.Frame(mid); mb.pack(fill="x")
        for text, cmd in (("Send to Combat", self._sess_to_combat), ("Mark Complete", self._sess_complete),
                          ("Reopen", self._sess_reopen), ("Rename", self._sess_rename), ("Remove", self._sess_remove),
                          ("Export Session...", self._sess_export)):
            ttk.Button(mb, text=text, command=cmd).pack(side="left", padx=2, pady=2)
        tb = ttk.Frame(mid); tb.pack(fill="x")
        ttk.Button(tb, text="Plan Level Treasure Across Encounters", command=self._sess_plan_treasure).pack(side="left", padx=2)
        ttk.Button(tb, text="Clear Planned Treasure", command=self._sess_clear_treasure).pack(side="left", padx=2)
        ttk.Label(tb, text="(uses the Treasure tab's rarity/trait filters)", foreground="#777").pack(side="left", padx=6)
        self.se_tree = ttk.Treeview(mid, columns=("xp", "status"), show="tree headings")
        self.se_tree.heading("#0", text="Encounter / contents"); self.se_tree.column("#0", width=340)
        self.se_tree.heading("xp", text="XP"); self.se_tree.column("xp", width=90)
        self.se_tree.heading("status", text="Status"); self.se_tree.column("status", width=90)
        self.se_tree.tag_configure("done", foreground="#888")
        self.se_tree.tag_configure("loot", foreground="#7a5a00")
        self.se_tree.pack(fill="both", expand=True)
        self.se_tree.bind("<<TreeviewSelect>>", lambda e: self._show_session_row())
        self.sess_info = tk.StringVar(); ttk.Label(mid, textvariable=self.sess_info, foreground="#555").pack(anchor="w")

        right = ttk.Frame(pane); pane.add(right, weight=3)
        ttk.Label(right, text="Session notes").pack(anchor="w")
        self.ss_notes = tk.Text(right, height=5, wrap="word"); self.ss_notes.pack(fill="x")
        ttk.Label(right, text="Encounter notes (read-aloud, tactics, terrain)").pack(anchor="w", pady=(4, 0))
        self.se_notes = tk.Text(right, height=5, wrap="word"); self.se_notes.pack(fill="x")
        ttk.Button(right, text="Save Notes", command=self._sess_save_notes).pack(anchor="e", pady=2)
        self.sess_view = RichText(right, self); self.sess_view.pack(fill="both", expand=True)
        self.sess_view.show_message("Select a creature or treasure row to see details.")
        self.se_rows = {}
        self._refresh_sessions()
        self._refresh_xp()

    def _cur_session(self):
        sel = self.ss_tree.selection()
        return next((s for s in self.sessions if sel and s["id"] == sel[0]), None)

    def _cur_entry(self):
        s = self._cur_session()
        sel = self.se_tree.selection()
        if not s or not sel:
            return None, None
        row = self.se_rows.get(sel[0])
        if not row:
            return s, None
        return s, next((e for e in s["encounters"] if e["id"] == row[0]), None)

    def _save_sessions(self):
        storage.save("sessions", self.sessions)

    def _refresh_sessions(self, select=None):
        sel = select or (self.ss_tree.selection()[0] if self.ss_tree.selection() else None)
        self.ss_tree.delete(*self.ss_tree.get_children())
        for s in self.sessions:
            self.ss_tree.insert("", "end", iid=s["id"], text=s["name"], values=(s.get("level", ""), s.get("date", "")))
        if sel and self.ss_tree.exists(sel):
            self.ss_tree.selection_set(sel)
        self._show_session()

    def _show_session(self):
        s = self._cur_session()
        self.se_tree.delete(*self.se_tree.get_children())
        self.se_rows.clear()
        self.ss_notes.delete("1.0", "end"); self.se_notes.delete("1.0", "end")
        if not s:
            self.sess_info.set("Create a session, then use Save to Session on the Encounters tab.")
            return
        self.ss_notes.insert("1.0", s.get("notes", ""))
        planned = sum(e.get("xp", 0) for e in s["encounters"] if e.get("status") != "done")
        done = sum(e.get("xp_awarded", 0) for e in s["encounters"] if e.get("status") == "done")
        loot = sum(t.get("value_gp", 0) for e in s["encounters"] for t in e.get("treasure", []))
        self.sess_info.set(f"{len(s['encounters'])} encounters | planned XP {planned} | awarded {done} | "
                           f"treasure planned {loot:g} gp")
        for e in s["encounters"]:
            tag = ("done",) if e.get("status") == "done" else ()
            label = e["name"] + (f"  [{e['threat']}]" if e.get("threat") else "")
            xp = f"{e.get('xp', 0)}/{e.get('budget', 0)}"
            if e.get("status") == "done":
                xp += f" (+{e.get('xp_awarded', 0)})"
            pid = self.se_tree.insert("", "end", text=label, values=(xp, e.get("status", "planned")), open=True, tags=tag)
            self.se_rows[pid] = (e["id"], None, None)
            for gi, g in enumerate(e.get("groups", [])):
                c = Creature(**g["creature"])
                iid = self.se_tree.insert(pid, "end", text=f"{g['count']} x {c.display_name}{self._tag_label(c)}",
                                          values=(f"L{c.level}", ""), tags=tag)
                self.se_rows[iid] = (e["id"], "creature", gi)
            for ti, t in enumerate(e.get("treasure", [])):
                lvl = f"L{t['level']}" if t.get("level") is not None else ""
                iid = self.se_tree.insert(pid, "end", text=f"Treasure: {t['name']} ({t['kind']})",
                                          values=(lvl, f"{t.get('value_gp', 0):g} gp"), tags=tag + ("loot",))
                self.se_rows[iid] = (e["id"], "treasure", ti)

    def _show_session_row(self):
        s, e = self._cur_entry()
        self.se_notes.delete("1.0", "end")
        if not e:
            return
        self.se_notes.insert("1.0", e.get("notes", ""))
        _, kind, idx = self.se_rows[self.se_tree.selection()[0]]
        if kind == "creature":
            c = Creature(**e["groups"][idx]["creature"])
            d = self.details_for(c)
            if d:
                self.sess_view.show(render(d))
        elif kind == "treasure":
            t = e["treasure"][idx]
            if t["kind"] == "currency":
                self.sess_view.show_message(f"Currency: {t['value_gp']:g} gp")
            else:
                rowid = self.rules.resolve(f"item:{t['name']}")
                ent = self.rules.rule(rowid) if rowid else None
                custom = next((i for i in self.c_items if i.name == t["name"]), None)
                if ent:
                    self.sess_view.show(render_entry(ent))
                elif custom:
                    self.sess_view.show(render_entry(custom_item_entry(custom)))
                else:
                    self.sess_view.show_message(t["name"])

    def _new_session_dialog(self, edit=False):
        s = self._cur_session() if edit else None
        if edit and not s:
            return
        win = tk.Toplevel(self); win.title("Edit session" if s else "New session")
        name = tk.StringVar(value=s["name"] if s else f"Session {len(self.sessions) + 1}")
        lvl = tk.StringVar(value=str(s["level"] if s else self.party_level()))
        date = tk.StringVar(value=s.get("date", "") if s else datetime.date.today().isoformat())
        for r, (label, v) in enumerate((("Name", name), ("Party level", lvl), ("Date", date))):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(win, textvariable=v, width=30).grid(row=r, column=1, padx=6, pady=3)

        def ok():
            if not name.get().strip():
                return
            if s:
                s.update(name=name.get().strip(), level=self._int_or_none(lvl.get()) or s["level"], date=date.get().strip())
                sid = s["id"]
            else:
                ns = sess.new_session(name.get().strip(), self._int_or_none(lvl.get()) or self.party_level())
                ns["date"] = date.get().strip()
                self.sessions.append(ns); sid = ns["id"]
            self._save_sessions(); self._refresh_sessions(select=sid); win.destroy()
        ttk.Button(win, text="Save", command=ok).grid(row=3, column=1, sticky="e", padx=6, pady=6)

    def _del_session(self):
        s = self._cur_session()
        if s and messagebox.askyesno("Delete session", f"Delete '{s['name']}'? Completed encounters stay in the "
                                                       "treasure ledger and XP total."):
            self.sessions = [x for x in self.sessions if x["id"] != s["id"]]
            self._save_sessions(); self._refresh_sessions()

    def _save_to_session_dialog(self):
        ei = self._selected_encounter_index()
        if ei is None:
            messagebox.showinfo("Select an encounter", "Select an encounter (or any creature in it) first."); return
        win = tk.Toplevel(self); win.title("Save to session")
        names = [s["name"] for s in self.sessions]
        target = Combo(win, names + ["(new session)"], readonly=True, width=30)
        target.var.set(names[-1] if names else "(new session)")
        new_name = tk.StringVar(value=f"Session {len(self.sessions) + 1}")
        threat = getattr(self, "enc_threat_used", self.threat.get())
        enc_name = tk.StringVar(value=f"{threat} encounter {ei + 1}")
        rows = (("Session", target), ("New session name", ttk.Entry(win, textvariable=new_name, width=32)),
                ("Encounter name", ttk.Entry(win, textvariable=enc_name, width=32)))
        for r, (label, w) in enumerate(rows):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            w.grid(row=r, column=1, padx=6, pady=3, sticky="w")

        def ok():
            if target.var.get() == "(new session)":
                s = sess.new_session(new_name.get().strip() or "Session", self.party_level())
                self.sessions.append(s)
            else:
                s = next(x for x in self.sessions if x["name"] == target.var.get())
            s["encounters"].append(sess.new_entry(encounter_to_dict(self.encs[ei], threat=threat),
                                                  name=enc_name.get().strip()))
            self._save_sessions(); self._refresh_sessions(select=s["id"])
            self.enc_info.set(f"Saved to {s['name']}.")
            win.destroy()
        ttk.Button(win, text="Save", command=ok).grid(row=3, column=1, sticky="e", padx=6, pady=6)

    def _sess_to_combat(self):
        s, e = self._cur_entry()
        if not e:
            messagebox.showinfo("Select", "Select an encounter in the session first."); return
        for c, n in encounter_from_dict(e).groups:
            for _ in range(n):
                self._add_creature_to_combat(c)
        self._combat_changed()
        self.nb.select(self.tab_combat)

    def _sess_export(self):
        s = self._cur_session()
        if not s:
            messagebox.showinfo("Select a session", "Select a session first."); return
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", s["name"]).strip("_") or "session"
        self._save_text(exporter.session_md(s, self.details_for), f"{safe}.md")

    def _sess_complete(self):
        s, e = self._cur_entry()
        if not e:
            return
        if e.get("status") == "done":
            messagebox.showinfo("Already complete", "That encounter is already marked complete."); return
        xp = sess.complete(e, self.party_size(), self.ledger, s.get("level", self.party_level()))
        self.config_data["party_xp"] = int(self.config_data.get("party_xp", 0)) + xp
        storage.save("config", self.config_data); storage.save("ledger", self.ledger); self._save_sessions()
        self._refresh_ledger(); self._refresh_sessions(); self._refresh_xp()
        msg = f"Awarded {xp} XP"
        if e.get("treasure"):
            msg += f" and added {len(e['treasure'])} treasure rows to the ledger"
        self.sess_info.set(msg + ".")
        if self.config_data["party_xp"] >= sess.XP_PER_LEVEL and messagebox.askyesno(
                "Level up", f"The party has {self.config_data['party_xp']} XP. Level up now?"):
            self._level_up()

    def _sess_reopen(self):
        s, e = self._cur_entry()
        if not e:
            return
        xp = sess.reopen(e, self.ledger)
        self.config_data["party_xp"] = max(0, int(self.config_data.get("party_xp", 0)) - xp)
        storage.save("config", self.config_data); storage.save("ledger", self.ledger); self._save_sessions()
        self._refresh_ledger(); self._refresh_sessions(); self._refresh_xp()

    def _sess_rename(self):
        s, e = self._cur_entry()
        if not e:
            return
        win = tk.Toplevel(self); win.title("Rename encounter")
        v = tk.StringVar(value=e["name"])
        ent = ttk.Entry(win, textvariable=v, width=36); ent.pack(padx=8, pady=8); ent.focus_set()

        def ok(*_):
            e["name"] = v.get().strip() or e["name"]; self._save_sessions(); self._refresh_sessions(); win.destroy()
        ent.bind("<Return>", ok)
        ttk.Button(win, text="Save", command=ok).pack(pady=(0, 8))

    def _sess_remove(self):
        s, e = self._cur_entry()
        if not e:
            return
        sel = self.se_tree.selection()[0]
        _, kind, idx = self.se_rows[sel]
        if kind == "treasure":
            del e["treasure"][idx]
        elif messagebox.askyesno("Remove", f"Remove '{e['name']}' from the session?"):
            s["encounters"] = [x for x in s["encounters"] if x["id"] != e["id"]]
        self._save_sessions(); self._refresh_sessions()

    def _sess_plan_treasure(self):
        s = self._cur_session()
        if not s or not s["encounters"]:
            messagebox.showinfo("No encounters", "Add encounters to the session first."); return
        live = [e for e in s["encounters"] if e.get("status") != "done"]
        if not live:
            messagebox.showinfo("Nothing planned", "All encounters in this session are complete."); return
        if any(e.get("treasure") for e in live) and not messagebox.askyesno(
                "Replace treasure", "Replace treasure already planned on open encounters?"):
            return
        level = max(1, min(20, int(s.get("level", self.party_level()))))
        split, notes = sess.plan_treasure(live, self._loot_pool(), level, self.party_size())
        for e in live:
            e["treasure"] = split.get(e["id"], [])
        self._save_sessions(); self._refresh_sessions()
        self.sess_info.set(f"Level {level} treasure split across {len(live)} encounters by XP."
                           + (" " + " | ".join(notes) if notes else "")
                           + " This is the whole level's package; trim it if the level spans several sessions.")

    def _sess_clear_treasure(self):
        s = self._cur_session()
        if s:
            for e in s["encounters"]:
                if e.get("status") != "done":
                    e["treasure"] = []
            self._save_sessions(); self._refresh_sessions()

    def _sess_save_notes(self):
        s = self._cur_session()
        if not s:
            return
        s["notes"] = self.ss_notes.get("1.0", "end").strip()
        _, e = self._cur_entry()
        if e:
            e["notes"] = self.se_notes.get("1.0", "end").strip()
        self._save_sessions()
        self.sess_info.set("Notes saved.")

    def _refresh_xp(self):
        xp = int(self.config_data.get("party_xp", 0))
        self.xp_var.set(f"Party level {self.party_level()}   |   XP {xp} / {sess.XP_PER_LEVEL}"
                        + ("   (ready to level up)" if xp >= sess.XP_PER_LEVEL else ""))

    def _level_up(self):
        xp = int(self.config_data.get("party_xp", 0))
        self.config_data["party_xp"] = max(0, xp - sess.XP_PER_LEVEL)
        self.pl_var.set(min(20, self.party_level() + 1))
        for pc in self.party:
            pc["level"] = min(20, int(pc.get("level", 1)) + 1)
        storage.save("party", self.party)
        self._save_party_cfg(); self._refresh_party(); self._refresh_xp()

    def _adjust_xp_dialog(self):
        win = tk.Toplevel(self); win.title("Party XP")
        v = tk.StringVar(value=str(self.config_data.get("party_xp", 0)))
        ttk.Label(win, text="XP toward next level").pack(padx=8, pady=4)
        e = ttk.Entry(win, textvariable=v, width=8); e.pack(padx=8); e.focus_set()

        def ok(*_):
            n = self._int_or_none(v.get())
            if n is not None:
                self.config_data["party_xp"] = max(0, n); storage.save("config", self.config_data)
                self._refresh_xp()
            win.destroy()
        e.bind("<Return>", ok)
        ttk.Button(win, text="Set", command=ok).pack(pady=6)

    # ---------- Quick Ref ----------
    def _build_quickref(self):
        f = self.tab_ref
        left = ttk.LabelFrame(f, text="DC lookup"); left.pack(side="left", fill="y", padx=8, pady=8)
        self.qr_mode = tk.StringVar(value="Level")
        mode = ttk.Frame(left); mode.grid(row=0, column=0, columnspan=2, sticky="w", pady=4)
        for m in ("Level", "Spell rank"):
            ttk.Radiobutton(mode, text=m, value=m, variable=self.qr_mode, command=self._qr_calc).pack(side="left", padx=4)
        ttk.Label(left, text="Level / rank").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        self.qr_level = tk.StringVar(value=str(self.party_level()))
        sp = ttk.Spinbox(left, from_=-1, to=25, textvariable=self.qr_level, width=6, command=self._qr_calc)
        sp.grid(row=1, column=1, sticky="w")
        ttk.Label(left, text="Difficulty").grid(row=2, column=0, sticky="w", padx=6, pady=3)
        self.qr_diff = Combo(left, [n for n, _ in ADJUSTMENTS], readonly=True, width=16)
        self.qr_diff.var.set("Normal"); self.qr_diff.grid(row=2, column=1, sticky="w")
        ttk.Label(left, text="Rarity").grid(row=3, column=0, sticky="w", padx=6, pady=3)
        self.qr_rar = Combo(left, [n for n, _ in RARITY_ADJ], readonly=True, width=16)
        self.qr_rar.var.set("Common"); self.qr_rar.grid(row=3, column=1, sticky="w")
        self.qr_result = tk.StringVar()
        ttk.Label(left, textvariable=self.qr_result, font=("TkDefaultFont", 22, "bold")).grid(
            row=4, column=0, columnspan=2, pady=12)
        ttk.Button(left, text="Use Party Level", command=lambda: (self.qr_mode.set("Level"),
                                                                  self.qr_level.set(str(self.party_level())),
                                                                  self._qr_calc())).grid(row=5, column=0, columnspan=2, sticky="we", padx=6)
        ttk.Label(left, text="Press F1 anywhere to jump here.", foreground="#777").grid(row=6, column=0, columnspan=2, pady=8)
        for v in (self.qr_level, self.qr_diff.var, self.qr_rar.var):
            v.trace_add("write", lambda *a: self._qr_calc())
        self.qr_view = RichText(f, self); self.qr_view.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self._qr_calc()

    def _qr_calc(self):
        lvl = self._int_or_none(str(self.qr_level.get()))
        if lvl is None:
            self.qr_result.set("DC ?"); return
        if self.qr_mode.get() == "Spell rank":
            dc = spell_rank_dc(max(1, min(10, lvl)), self.qr_diff.var.get(), self.qr_rar.var.get())
        else:
            dc = dc_for(lvl, self.qr_diff.var.get(), self.qr_rar.var.get())
        self.qr_result.set(f"DC {dc}")
        self.qr_view.show(reference_segments(self.party_size()))

    # ---------- Notebook ----------
    def _build_notebook(self):
        f = self.tab_notebook
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        flt = ttk.Frame(left); flt.pack(fill="x")
        self.nbk_type = Combo(flt, nbk.PAGE_TYPES, any_option=True, readonly=True, width=10)
        self.nbk_type.pack(side="left")
        self.nbk_q = tk.StringVar()
        ttk.Entry(flt, textvariable=self.nbk_q, width=18).pack(side="left", padx=4, fill="x", expand=True)
        self.nbk_type.var.trace_add("write", lambda *a: self._refresh_notebook())
        self.nbk_q.trace_add("write", lambda *a: self._refresh_notebook())
        self.nbk_tree = ttk.Treeview(left, columns=("type", "status"), show="tree headings", height=22)
        self.nbk_tree.heading("#0", text="Page"); self.nbk_tree.column("#0", width=190)
        self.nbk_tree.heading("type", text="Type"); self.nbk_tree.column("type", width=70)
        self.nbk_tree.heading("status", text="Status"); self.nbk_tree.column("status", width=70)
        self.nbk_tree.pack(fill="both", expand=True, pady=4)
        self.nbk_tree.bind("<<TreeviewSelect>>", lambda e: self._load_page())
        bb = ttk.Frame(left); bb.pack(fill="x")
        for i, (text, cmd) in enumerate((("New Page", self._new_page), ("Delete", self._del_page),
                                         ("Import PC JSON...", self._nbk_import_pc),
                                         ("Add PC by ID...", self._nbk_add_pc_id),
                                         ("Refresh PCs", self._nbk_refresh_pcs),
                                         ("Add Party Members", self._nbk_add_party),
                                         ("Story Ideas...", self._nbk_story_menu),
                                         ("Edit in Story Forge", self._nbk_edit_story))):
            ttk.Button(bb, text=text, command=cmd).grid(row=i // 2, column=i % 2, sticky="we", padx=1, pady=1)
        bb.columnconfigure(0, weight=1); bb.columnconfigure(1, weight=1)
        imp = ttk.Frame(left); imp.pack(fill="x", pady=2)
        ttk.Label(imp, text="Import as").pack(side="left")
        self.nbk_import_as = Combo(imp, ["PC", "NPC"], readonly=True, width=6)
        self.nbk_import_as.var.set(self.config_data.get("import_as", "PC"))
        self.nbk_import_as.pack(side="left", padx=4)
        self.nbk_also_party = tk.BooleanVar(value=True)
        ttk.Checkbutton(imp, text="PCs also join the party", variable=self.nbk_also_party).pack(side="left")
        ttk.Label(left, text="NPCs get a page and a combat stat block but never join the party.",
                  foreground="#777", wraplength=260).pack(anchor="w")

        right = ttk.PanedWindow(pane, orient="vertical"); pane.add(right, weight=3)
        ed = ttk.Frame(right); right.add(ed, weight=1)
        grid = ttk.Frame(ed); grid.pack(fill="x")
        self.pf = {k: tk.StringVar() for k in ("title", "type", "status", "tags", "ancestry", "role", "player")}
        widgets = [("Title", ttk.Entry(grid, textvariable=self.pf["title"], width=34)),
                   ("Type", ttk.Combobox(grid, textvariable=self.pf["type"], values=nbk.PAGE_TYPES, state="readonly", width=12)),
                   ("Status", ttk.Combobox(grid, textvariable=self.pf["status"], width=14)),
                   ("Tags (comma)", ttk.Entry(grid, textvariable=self.pf["tags"], width=34)),
                   ("Ancestry", Combo(grid, values_key="ancestries", textvariable=self.pf["ancestry"], width=18)),
                   ("Role / class", ttk.Entry(grid, textvariable=self.pf["role"], width=18)),
                   ("Player", ttk.Entry(grid, textvariable=self.pf["player"], width=18))]
        self.nbk_status_combo = widgets[2][1]
        for i, (label, w) in enumerate(widgets):
            r, c = divmod(i, 2)
            ttk.Label(grid, text=label).grid(row=r, column=c * 2, sticky="w", padx=(0 if c == 0 else 10, 4), pady=1)
            w.grid(row=r, column=c * 2 + 1, sticky="w")
        self.pf["type"].trace_add("write", lambda *a: self.nbk_status_combo.configure(
            values=nbk.STATUSES.get(self.pf["type"].get(), [])))
        lk = ttk.Frame(ed); lk.pack(fill="x", pady=2)
        ttk.Label(lk, text="Body. Link pages with [[Title]]; creature and rules names in [[ ]] link too.",
                  foreground="#555").pack(side="left")
        self.nbk_link = Combo(lk, values_key="link_targets", width=22); self.nbk_link.pack(side="right")
        ttk.Button(lk, text="Insert Link", command=self._nbk_insert_link).pack(side="right", padx=4)
        self.nbk_body = tk.Text(ed, height=5, wrap="word", undo=True); self.nbk_body.pack(fill="both", expand=True)
        sb = ttk.Frame(ed); sb.pack(fill="x", pady=2)
        ttk.Button(sb, text="Save Page", command=self._save_page).pack(side="right")
        ttk.Button(sb, text="Send to Combat", command=self._nbk_to_combat).pack(side="right", padx=4)
        ttk.Button(sb, text="Resources...", command=self._nbk_resources).pack(side="right", padx=4)
        ttk.Button(sb, text="Update from Pathbuilder", command=self._nbk_update_pc).pack(side="right", padx=4)
        self.nbk_feat_text = tk.BooleanVar(value=self.config_data.get("show_feat_text", True))
        ttk.Checkbutton(sb, text="Show full text of feats and actions", variable=self.nbk_feat_text,
                        command=self._nbk_toggle_feat_text).pack(side="left")
        ttk.Button(sb, text="Add This PC to Party", command=self._nbk_pc_to_party).pack(side="right", padx=4)
        ttk.Button(sb, text="Export Page...", command=self._nbk_export).pack(side="right")
        self.nbk_view = RichText(right, self); right.add(self.nbk_view, weight=4)
        self.nbk_view.show_message("Select or create a page. Pages, creatures, rules, conditions, and dice in the "
                                   "text are clickable here.")
        self.nbk_current = None
        self._refresh_notebook()

    def _save_notebook(self):
        storage.save("notebook", self.notebook)
        self._refresh_link_targets()
        self._notebook_changed()

    def _refresh_link_targets(self):
        if hasattr(self, "vocab"):
            self.vocab["link_targets"] = sorted({p["title"] for p in self.notebook}
                                                | {c.name for c in self.c_creatures}, key=str.lower)
            self._apply_vocab()

    def _refresh_notebook(self, select=None):
        if not hasattr(self, "nbk_tree"):
            return
        t, q = self.nbk_type.value(), self.nbk_q.get().strip().lower()
        self.nbk_tree.delete(*self.nbk_tree.get_children())
        for p in sorted(self.notebook, key=lambda x: (nbk.PAGE_TYPES.index(x.get("type", "Note"))
                                                      if x.get("type") in nbk.PAGE_TYPES else 99, x["title"].lower())):
            if t and p.get("type") != t:
                continue
            if q and q not in p["title"].lower() and q not in (p.get("body") or "").lower() \
                    and q not in " ".join(p.get("tags") or []).lower():
                continue
            self.nbk_tree.insert("", "end", iid=p["id"], text=p["title"], values=(p.get("type", ""), p.get("status", "")))
        sel = select or (self.nbk_current["id"] if self.nbk_current else None)
        if sel and self.nbk_tree.exists(sel):
            self.nbk_tree.selection_set(sel); self.nbk_tree.see(sel)

    def _page(self, pid):
        return next((p for p in self.notebook if p["id"] == pid), None)

    def _page_statblock(self, p):
        """Stat block segments for a page, or None. If building one fails, the reason is shown on the page instead of
        leaving it quietly blank."""
        try:
            return self._page_statblock_inner(p)
        except Exception as e:
            return [("Couldn't build this page's stat block: ", "warn", None), (f"{type(e).__name__}: {e}\n", "body", None)]

    @staticmethod
    def _creature_from_saved(data):
        """A Creature from saved stats, ignoring keys this version doesn't know."""
        fields = getattr(Creature, "__dataclass_fields__", None)
        return Creature(**({k: v for k, v in data.items() if k in fields} if fields else data))

    def _page_statblock_inner(self, p):
        if p.get("pc"):
            segs = render(self._pc_stat(dict(p["pc"], pathbuilder_id=p.get("pathbuilder_id")),
                                        with_text=self.nbk_feat_text.get(), compact=not self.nbk_feat_text.get()))
            if pb.is_stale(p["pc"]):
                pid = p.get("pathbuilder_id") or p["pc"].get("pathbuilder_id")
                fix = (f"Press Update from Pathbuilder (below) to rebuild it from Pathbuilder ID {pid}."
                       if pid else "Press Import PC JSON... and pick its export file to rebuild it.")
                segs = [("This character was saved by an older version of the importer, so its attacks, feats, "
                         "gear, and item bonuses are missing. " + fix + "\n\n", "warn", None)] + segs
            return segs
        if p.get("details"):                                   # a Foundry actor imported as an NPC
            return render(p["details"])
        if p.get("npc_stats") and not p.get("creature"):
            return render(custom_details(self._creature_from_saved(p["npc_stats"])))
        if p.get("creature"):
            c = next((x for x in self.c_creatures if x.name.lower() == p["creature"].lower()), None) or \
                next((x for x in self.all_creatures if x.name.lower() == p["creature"].lower()), None)
            d = self.details_for(c) if c else None
            if d:
                return render(d)
            if p.get("npc_stats"):                              # the saved creature is gone: use the page's own copy
                return render(custom_details(self._creature_from_saved(p["npc_stats"])))
            return [(f"This page points to the creature '{p['creature']}', which isn't in Custom Content or your "
                     "downloaded data.\n", "warn", None)]
        return None
    def _show_page(self, p):
        names = [c.name for c in self.all_creatures]
        self.nbk_view.show(nbk.render_page(p, self.notebook, names, self.rules, self._page_statblock(p)))

    def _load_page(self):
        sel = self.nbk_tree.selection()
        p = self._page(sel[0]) if sel else None
        if not p:
            return
        self.nbk_current = p
        for k, v in self.pf.items():
            v.set(", ".join(p.get("tags") or []) if k == "tags" else str(p.get(k, "") or ""))
        self.nbk_body.delete("1.0", "end"); self.nbk_body.insert("1.0", p.get("body", ""))
        self._show_page(p)

    def _new_page(self, title="New page", ptype=None, **extra):
        p = nbk.new_page(self._unique_title(title), ptype or (self.nbk_type.value() or "Note"), **extra)
        self.notebook.append(p)
        self._save_notebook()
        self.nbk_current = p
        self._refresh_notebook(select=p["id"])
        self._load_page()
        return p

    def _unique_title(self, title):
        t, n = title, 2
        while nbk.find(self.notebook, t):
            t, n = f"{title} ({n})", n + 1
        return t

    def _save_page(self):
        p = self.nbk_current
        if not p:
            self._new_page(); p = self.nbk_current
        title = self.pf["title"].get().strip() or p["title"]
        other = nbk.find(self.notebook, title)
        if other and other is not p:
            messagebox.showwarning("Title in use", f"Another page is already called '{title}'."); return
        if title != p["title"]:
            nbk.rename(self.notebook, p, title)
        p["type"] = self.pf["type"].get() or "Note"
        p["status"] = self.pf["status"].get().strip()
        p["tags"] = _split(self.pf["tags"].get())
        for k in ("ancestry", "role", "player"):
            p[k] = self.pf[k].get().strip()
        p["body"] = self.nbk_body.get("1.0", "end").rstrip()
        self._save_notebook(); self._refresh_notebook(select=p["id"]); self._show_page(p)

    def _del_page(self):
        p = self.nbk_current
        if p and messagebox.askyesno("Delete page", f"Delete '{p['title']}'? Links to it will offer to recreate it."):
            self.notebook = [x for x in self.notebook if x is not p]
            self.nbk_current = None
            self._save_notebook(); self._refresh_notebook()
            self.nbk_view.show_message("Page deleted.")

    def _nbk_insert_link(self):
        t = self.nbk_link.value()
        if t:
            self.nbk_body.insert("insert", f"[[{t}]]")
            self.nbk_link.var.set("")

    def _nbk_export(self):
        p = self.nbk_current
        if not p:
            return
        segs = nbk.render_page(p, self.notebook, [c.name for c in self.all_creatures], self.rules,
                               self._page_statblock(p))
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", p["title"]).strip("_") or "page"
        self._save_text(f"# {p['title']}\n\n" + render_text(segs[1:]), f"{safe}.md")

    def _pc_page(self, pc, pid=None, ptype=None):
        """Create or update the notebook page for a Pathbuilder character. An existing page keeps its type
        (PC or NPC); ptype only applies to a new page."""
        page = next((x for x in self.notebook if x.get("type") in ("PC", "NPC") and x.get("pc") is not None and
                     ((pid and x.get("pathbuilder_id") == pid) or x["title"].lower() == pc["name"].lower())), None)
        if page is None:   # a hand-made page with the same title becomes the character's page
            page = next((x for x in self.notebook if x.get("type") in ("PC", "NPC")
                         and x["title"].lower() == pc["name"].lower()), None)
        role = " ".join(x for x in (pc.get("class"), f"{pc.get('level')}") if x)
        if page is None:
            ptype = ptype or "PC"
            body = "\n".join(f"{k.title()}: {pc[k]}" for k in ("heritage", "background", "deity")
                             if pc.get(k) and str(pc[k]).lower() != "not set")
            page = nbk.new_page(self._unique_title(pc["name"]), ptype, body,
                                status="active" if ptype == "PC" else "alive")
            self.notebook.append(page)
        if isinstance(page.get("pc"), dict) and pb.rank(pc) < pb.rank(page["pc"]):
            if pid:
                page["pathbuilder_id"] = pid
            return page                         # this page already holds a more complete copy of the character
        old_state = (page.get("pc") or {}).get("state")
        if old_state and not pc.get("state"):
            pc["state"] = old_state             # keep table state across a Pathbuilder refresh
        page.update(pc=pc, ancestry=pc.get("ancestry", page.get("ancestry", "")), role=role)
        if pid:
            page["pathbuilder_id"] = pid
        return page

    def _nbk_after_pcs(self, pcs, ptype=None):
        """Create/update pages for imported characters. New pages use the 'Import as' choice (or ptype);
        only PCs join the party."""
        ptype = ptype or self.nbk_import_as.value() or "PC"
        self.config_data["import_as"] = ptype
        storage.save("config", self.config_data)
        joined = False
        page = None
        for pc, pid in pcs:
            page = self._pc_page(pc, pid, ptype)
            if page.get("type") == "PC" and self.nbk_also_party.get():
                self._merge_pc(dict(pc, pathbuilder_id=pid) if pid else pc)
                joined = True
        if joined:
            self._party_changed()
        weak = self._import_problem_note(pcs)
        if weak and len(pcs) > 1:
            messagebox.showwarning("Import", "Only a name and level could be read for: " + ", ".join(weak) +
                                   ". The export may be a different format or an empty character.")
        self._save_notebook()
        self._refresh_notebook(select=page["id"] if page else None)
        if page:
            self._load_page()

    @staticmethod
    def _looks_like_foundry(doc):
        return isinstance(doc, dict) and isinstance(doc.get("system"), dict) and isinstance(doc.get("items"), list)

    def _nbk_import_foundry(self, doc, fallback_name):
        """A Foundry VTT actor (a creature or NPC exported from Foundry) as an NPC page with its full stat block."""
        details = build_details(doc)
        title = doc.get("name") or fallback_name
        page = next((x for x in self.notebook if x.get("type") == "NPC" and x["title"].lower() == title.lower()), None)
        if page is None:
            page = nbk.new_page(self._unique_title(title), "NPC", "", status="alive")
            self.notebook.append(page)
        page["details"] = details
        if doc.get("type") == "character":
            page["body"] = (page.get("body") or "") + ("\n" if page.get("body") else "") + \
                "Imported from a Foundry character: its weapons aren't turned into Strikes, so attacks may be missing."
        self._save_notebook(); self._refresh_notebook(select=page["id"]); self._load_page()
        return page

    def _import_problem_note(self, got):
        """Names of imported characters of which only a name and level were readable."""
        return [pc["name"] for pc, _ in got
                if pc.get("perception") is None and not pc.get("strikes") and not pc.get("spells")]

    def _nbk_import_pc(self):
        got = []
        for path in filedialog.askopenfilenames(filetypes=[("Pathbuilder or Foundry JSON", "*.json")]):
            try:
                with open(path, encoding="utf-8") as fh:
                    doc = json.load(fh)
                if self._looks_like_foundry(doc):
                    self._nbk_import_foundry(doc, Path(path).stem)
                    continue
                pc = pb.parse(doc, Path(path).stem)
                if self._import_problem_note([(pc, None)]):
                    keys = ", ".join(sorted(doc)[:12]) if isinstance(doc, dict) else type(doc).__name__
                    messagebox.showwarning("Import", f"Only a name and level could be read from {Path(path).name}. It may "
                                           "not be a Pathbuilder 'Export JSON' file. Top-level keys found: " + keys)
                got.append((pc, None))
            except Exception as e:
                messagebox.showerror("Import failed", f"{path}\n{e}")
        if got:
            self._nbk_after_pcs(got)

    def _nbk_fetch(self, ids, done=None):
        def work():
            got, errs = [], []
            for pid in ids:
                try:
                    got.append((pb.parse(pb.fetch(pid)), pid))
                except Exception as e:
                    errs.append(f"ID {pid}: {e}")
            self.after(0, finish, got, errs)

        def finish(got, errs):
            self._nbk_after_pcs(got)
            if errs:
                messagebox.showerror("Pathbuilder", "\n".join(errs))
            if done:
                done()
        threading.Thread(target=work, daemon=True).start()

    def _nbk_add_pc_id(self):
        win = tk.Toplevel(self); win.title("Add PC by Pathbuilder ID"); win.transient(self)
        ttk.Label(win, text="Pathbuilder: Menu > Export > Export JSON. Paste IDs or links, one per line.").pack(padx=8, pady=6)
        box = tk.Text(win, height=5, width=40); box.pack(padx=8)

        def go():
            ids = [i for i in (pb.parse_id(l) for l in box.get("1.0", "end").splitlines() if l.strip()) if i]
            if ids:
                self._nbk_fetch(ids, done=win.destroy)
        ttk.Button(win, text="Fetch", command=go).pack(pady=6)

    def _nbk_refresh_pcs(self):
        ids = [p["pathbuilder_id"] for p in self.notebook
               if p.get("type") in ("PC", "NPC") and p.get("pathbuilder_id")]
        if not ids:
            messagebox.showinfo("No IDs", "No PC or NPC pages have a Pathbuilder ID. Use Add PC by ID."); return
        self._nbk_fetch(ids)

    def _nbk_add_party(self):
        for pc in self.party:
            self._pc_page(pc, pc.get("pathbuilder_id"))
        self._save_notebook(); self._refresh_notebook()

    def _nbk_story_menu(self):
        p = self.nbk_current
        if not p:
            messagebox.showinfo("Select a page", "Select an NPC, Faction, Location, or Event page first."); return
        m = tk.Menu(self, tearoff=0)
        for label, kind in (("A rumor about this", "rumor"), ("A hook involving this", "hook"),
                            ("A complication involving this", "complication"), ("A faction move", "faction_move"),
                            ("An omen", "omen")):
            m.add_command(label=label, command=lambda k=kind: self._story_from_page(p, k))
        m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def _nbk_edit_story(self):
        self._story_load_page(self.nbk_current)

    def _nbk_toggle_feat_text(self):
        self.config_data["show_feat_text"] = self.nbk_feat_text.get()
        storage.save("config", self.config_data)
        if self.nbk_current:
            self._show_page(self.nbk_current)

    def _nbk_to_combat(self):
        """Add the selected PC or NPC page to the combat tracker with its full stat block."""
        p = self.nbk_current
        if not p:
            messagebox.showinfo("Select a page", "Select a PC or NPC page first."); return
        pc = p.get("pc")
        if pc:
            is_pc = p.get("type") == "PC"
            comb = self.combat.add(p["title"], kind="pc" if is_pc else "creature", perception=pc.get("perception"),
                                   hp=pc.get("hp"), ac=pc.get("ac"), saves=dict(pc.get("saves") or {}),
                                   uid="" if is_pc else f"N|{p['id']}", pc_key=p["title"] if is_pc else "")
            self._setup_pc_combatant(comb, pc)
        elif p.get("details"):
            c = Creature(**details_to_custom(p["details"], name=p["title"]))
            if not any(x.name.lower() == c.name.lower() for x in self.c_creatures):
                self.c_creatures.append(c); storage.save_custom_creatures(self.c_creatures); self._refresh_custom()
            self._add_creature_to_combat(c)
        elif p.get("creature") or p.get("npc_stats"):
            c = next((x for x in self.c_creatures if x.name.lower() == (p.get("creature") or "").lower()), None)
            if c is None and p.get("npc_stats"):
                try:
                    c = self._creature_from_saved(p["npc_stats"])
                except TypeError:
                    c = None
            if c is None:
                messagebox.showinfo("No stats", "That page has no stat block to add."); return
            self._add_creature_to_combat(c)
        else:
            messagebox.showinfo("No stats", "That page has no stat block. Import a Pathbuilder character or "
                                "generate an NPC first."); return
        self._combat_changed()
        self.nb.select(self.tab_combat)

    def _nbk_update_pc(self):
        """Rebuild this page's character with the newest importer: from the export saved with it if there is one, else
        by fetching its Pathbuilder ID."""
        p = self.nbk_current
        if not p or not isinstance(p.get("pc"), dict):
            messagebox.showinfo("Update", "Select a PC or NPC page imported from Pathbuilder."); return
        new = pb.upgrade(p["pc"])
        pid = p.get("pathbuilder_id") or p["pc"].get("pathbuilder_id")
        if new is not None:
            if p["pc"].get("state") and not new.get("state"):
                new["state"] = p["pc"]["state"]
            if pid:
                new["pathbuilder_id"] = pid
            p["pc"] = new
            if any(x.get("name") == new.get("name") for x in self.party):
                self._merge_pc(dict(new))
                storage.save("party", self.party)
            self._save_notebook(); self._show_page(p)
            self.last_roll.set(f"Rebuilt {p['title']} from its saved export.")
        elif pid:
            self.last_roll.set(f"Fetching {p['title']} from Pathbuilder (ID {pid})...")
            self._nbk_fetch([pid])
        else:
            messagebox.showinfo("Update", f"{p['title']} has no Pathbuilder ID and no saved export. Press Import PC "
                                "JSON... and pick its export file; it will update this page.")

    def _nbk_pc_to_party(self):
        p = self.nbk_current
        if not p or not p.get("pc"):
            messagebox.showinfo("Not a PC", "Select a PC page imported from Pathbuilder."); return
        self._merge_pc(dict(p["pc"], pathbuilder_id=p.get("pathbuilder_id")) if p.get("pathbuilder_id") else dict(p["pc"]))
        self._party_changed()

    def _open_page(self, pid):
        p = self._page(pid)
        if not p:
            return
        self.nb.select(self.tab_notebook)
        self.nbk_type.var.set(ANY); self.nbk_q.set("")
        self.nbk_current = p
        self._refresh_notebook(select=pid)
        self._load_page()

    # ---------- Magic Items ----------
    MAGIC_KIND_LABELS = ["Any kind"] + list(itemgen.KINDS.values())

    @staticmethod
    def _magic_culture_labels():
        return ["(auto: the maker's people)", "(none)"] + [info["label"] for info in itemdata.CULTURE_INFO.values()]

    @staticmethod
    def _magic_culture_label(key):
        if key in itemdata.CULTURE_INFO:
            return itemdata.CULTURE_INFO[key]["label"]
        return "(none)" if key == "none" else "(auto: the maker's people)"

    def _magic_culture_key(self):
        v = self.mg_culture.var.get()
        for k, info in itemdata.CULTURE_INFO.items():
            if info["label"] == v:
                return k
        return "none" if v == "(none)" else "auto"
    MAGIC_USAGES = ["worn headwear", "worn eyepiece", "worn amulet", "worn necklace", "worn cloak", "worn gloves",
                    "worn bracers", "worn ring", "worn belt", "worn boots", "worn garment", "held in 1 hand",
                    "held in 2 hands", "etched onto a weapon", "etched onto armor", "affixed to armor",
                    "affixed to a weapon"]
    MAGIC_FREQS = ["", "once per day", "once per hour", "once per 10 minutes", "once per minute", "once per round",
                   "three times per day"]

    def _scroll_area(self, parent):
        outer = ttk.Frame(parent); outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        wid = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(wid, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        self.magic_canvases.append(canvas)
        return canvas, inner

    def _magic_wheel(self, e):
        try:
            for c in self.magic_canvases:
                if str(e.widget).startswith(str(c)):
                    c.yview_scroll(int(-e.delta / 120), "units")
                    return
        except Exception:
            pass

    def _magic_row(self, parent, r, label, text, locked, on_commit, on_lock, on_reroll=None):
        ttk.Label(parent, text=label, font=("TkDefaultFont", 10, "bold")).grid(row=r, column=0, sticky="nw", padx=(4, 8), pady=3)
        t = tk.Text(parent, height=max(1, min(6, -(-len(text) // 74))), width=76, wrap="word",
                    font=("TkDefaultFont", 10), padx=4, pady=2)
        t.insert("1.0", text)
        t.grid(row=r, column=1, sticky="we", pady=3)
        t.bind("<FocusOut>", lambda e: on_commit())
        lock = tk.BooleanVar(value=locked)
        ttk.Checkbutton(parent, text="Lock", variable=lock, command=on_lock).grid(row=r, column=2, padx=4)
        if on_reroll is not None:
            ttk.Button(parent, text="Reroll", width=7, command=on_reroll).grid(row=r, column=3, padx=(0, 4))
        return t, lock

    def _build_magic(self):
        f = self.tab_magic
        cfg = self.config_data.get("magic", {})
        self.magic_items = storage.load("magic_items")
        self.item_gen = itemgen.ItemGenerator(self.story_registry, rng=random.Random())
        self.magic_list, self.magic_cur, self.magic_canvases = [], None, []
        self.magic_widgets, self.magic_lore_widgets = {}, {}
        self.bind_all("<MouseWheel>", self._magic_wheel, add="+")
        sub = TabbedPane(f, level=2); sub.pack(fill="both", expand=True, padx=4, pady=4)
        gp, cp, lp = ttk.Frame(sub), ttk.Frame(sub), ttk.Frame(sub)
        sub.add(gp, text="Generate"); sub.add(cp, text="Custom Item"); sub.add(lp, text="My Items")
        self.magic_sub, self.magic_gen_page, self.magic_custom_page, self.magic_lib_page = sub, gp, cp, lp
        self._build_magic_generate(gp, cfg)
        self._build_magic_custom(cp)
        self._build_magic_library(lp)

    # ----- generate page
    def _build_magic_generate(self, f, cfg):
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=(6, 2))
        box1 = ttk.LabelFrame(top, text="1. The item"); box1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        box2 = ttk.LabelFrame(top, text="2. Flavor and setting"); box2.grid(row=0, column=1, sticky="nsew", padx=(0, 6))
        box3 = ttk.LabelFrame(top, text="3. Extras"); box3.grid(row=0, column=2, sticky="nsew", padx=(0, 6))

        def line(box, r, text, widget, **grid):
            ttk.Label(box, text=text).grid(row=r, column=0, sticky="w", padx=(6, 6), pady=2)
            widget.grid(row=r, column=1, sticky="w", pady=2, padx=(0, 6), **grid)
        self.mg_kind = Combo(box1, self.MAGIC_KIND_LABELS, readonly=True, width=20)
        self.mg_kind.var.set(next((v for k, v in itemgen.KINDS.items() if k == cfg.get("kind")), "Any kind"))
        line(box1, 0, "Kind", self.mg_kind)
        lv = ttk.Frame(box1)
        self.mg_level = tk.StringVar(value=str(cfg.get("level", self.party_level())))
        ttk.Spinbox(lv, from_=1, to=20, textvariable=self.mg_level, width=5).pack(side="left")
        ttk.Button(lv, text="Party", width=6, command=lambda: self.mg_level.set(str(self.party_level()))).pack(side="left", padx=4)
        ttk.Label(lv, text="vary by").pack(side="left", padx=(8, 3))
        self.mg_vary = tk.StringVar(value=str(cfg.get("vary", 1)))
        ttk.Spinbox(lv, from_=0, to=4, textvariable=self.mg_vary, width=4).pack(side="left")
        line(box1, 1, "Level", lv)
        self.mg_rarity = Combo(box1, ["any"] + list(itemgen.RARITIES), readonly=True, width=20)
        self.mg_rarity.var.set(cfg.get("rarity", "any")); line(box1, 2, "Rarity", self.mg_rarity)
        self.mg_role = Combo(box1, ["auto"] + list(itemgen.ROLES), readonly=True, width=20)
        self.mg_role.var.set(cfg.get("role", "auto")); line(box1, 3, "Role (price)", self.mg_role)
        self.mg_trad = Combo(box1, ["any"] + list(itemdata.TRADITIONS), readonly=True, width=20)
        self.mg_trad.var.set(cfg.get("tradition", "any")); line(box1, 4, "Tradition", self.mg_trad)
        self.mg_abil = Combo(box1, ["any", "1", "2", "3"], readonly=True, width=20)
        self.mg_abil.var.set(cfg.get("abilities", "any")); line(box1, 5, "Abilities", self.mg_abil)
        self.mg_focus = Combo(box1, list(itemgen.FOCUS.values()), readonly=True, width=20)
        self.mg_focus.var.set(itemgen.FOCUS.get(cfg.get("focus", "any"), "Any abilities")); line(box1, 6, "Focus", self.mg_focus)
        self.mg_style = Combo(box1, list(itemgen.STYLES.values()), readonly=True, width=20)
        self.mg_style.var.set(itemgen.STYLES.get(itemgen.style_key(cfg.get("style")), "Standard")); line(box1, 7, "Style", self.mg_style)
        ttk.Label(box1, text="Grim, Whimsical, and Ridiculous add drawbacks, oddities, and absurd abilities.",
                  foreground="#777", wraplength=260, justify="left").grid(row=8, column=0, columnspan=2, sticky="w", padx=6)

        self.mg_themes = MultiField(box2, values=itemdata.THEMES, width=22, combo_width=11)
        self.mg_themes.set(cfg.get("themes", [])); line(box2, 0, "Theme", self.mg_themes)
        self.mg_env = Combo(box2, self.STORY_ENVS, readonly=True, width=22)
        self.mg_env.var.set(cfg.get("env", "any")); line(box2, 1, "Setting", self.mg_env)
        self.mg_tone = Combo(box2, self.STORY_TONES, readonly=True, width=22)
        self.mg_tone.var.set(cfg.get("tone", "any")); line(box2, 2, "Tone", self.mg_tone)
        self.mg_culture = Combo(box2, self._magic_culture_labels(), readonly=True, width=28)
        self.mg_culture.var.set(self._magic_culture_label(cfg.get("culture", "auto"))); line(box2, 3, "Style / culture", self.mg_culture)
        self.mg_tie = Combo(box2, ["(none)"], readonly=True, width=28); line(box2, 4, "Made by or at", self.mg_tie)
        ttk.Label(box2, text="Style shapes names, looks, and quirks.", foreground="#777").grid(row=5, column=0, columnspan=2, sticky="w", padx=6)

        self.mg_lore = tk.BooleanVar(value=cfg.get("lore", True))
        self.mg_quirk = tk.BooleanVar(value=cfg.get("quirk", True))
        self.mg_drawback = tk.BooleanVar(value=cfg.get("drawback", False))
        self.mg_hm = tk.BooleanVar(value=cfg.get("hm", bool(self.config_data.get("hallowmead_loaded"))))
        for r, (text, var) in enumerate((("History and knowledge checks", self.mg_lore), ("Quirk", self.mg_quirk),
                                         ("Drawback", self.mg_drawback), ("Hallowmead setting content", self.mg_hm))):
            ttk.Checkbutton(box3, text=text, variable=var).grid(row=r, column=0, columnspan=2, sticky="w", padx=6, pady=1)
        ttk.Label(box3, text="Use my campaign").grid(row=4, column=0, sticky="w", padx=6, pady=(6, 0))
        self.mg_use = tk.DoubleVar(value=cfg.get("use_campaign", 50))
        ttk.Scale(box3, from_=0, to=100, orient="horizontal", variable=self.mg_use, length=130).grid(row=4, column=1, padx=6, pady=(6, 0))
        ttk.Label(box3, text="Setting flavor").grid(row=5, column=0, sticky="w", padx=6, pady=(4, 0))
        self.mg_flavor = tk.DoubleVar(value=cfg.get("flavor", itemgen.DEFAULT_FLAVOR * 100))
        ttk.Scale(box3, from_=0, to=100, orient="horizontal", variable=self.mg_flavor, length=130).grid(row=5, column=1, padx=6, pady=(4, 0))
        ttk.Label(box3, text="How much of a history comes from the Hallowmead lines: 0 none, 100 mostly.",
                  foreground="#777", wraplength=260, justify="left").grid(row=6, column=0, columnspan=2, sticky="w", padx=6)
        self.mg_count = tk.StringVar(value=str(cfg.get("count", 4)))
        cn = ttk.Frame(box3)
        ttk.Spinbox(cn, from_=1, to=8, textvariable=self.mg_count, width=4).pack(side="left")
        ttk.Label(cn, text="options per press").pack(side="left", padx=4)
        cn.grid(row=7, column=0, columnspan=2, sticky="w", padx=6, pady=(6, 2))
        bb = ttk.Frame(top); bb.grid(row=0, column=3, sticky="n", padx=4)
        ttk.Button(bb, text="Generate", width=16, command=self._magic_generate).pack(fill="x", pady=(2, 3), ipady=6)
        ttk.Button(bb, text="Add One More", command=lambda: self._magic_generate(count=1, append=True)).pack(fill="x", pady=1)
        ttk.Button(bb, text="Edit Tables...", command=self._story_open_tables).pack(fill="x", pady=1)
        self.mg_info = tk.StringVar(value="Runic armor starts at level 5. Runic items take their level from their runes; "
                                          "wands, scrolls, and potions take it from their spell.")
        ttk.Label(f, textvariable=self.mg_info, foreground="#555").pack(anchor="w", padx=10)

        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=2)
        ttk.Label(left, text="Options (click one to open, edit, lock, and keep)", foreground="#555").pack(anchor="w")
        self.mg_tree = ttk.Treeview(left, columns=("lvl", "price"), show="tree headings", height=18)
        self.mg_tree.heading("#0", text="Item"); self.mg_tree.column("#0", width=300, minwidth=200, stretch=True)
        self.mg_tree.heading("lvl", text="Lvl"); self.mg_tree.column("lvl", width=36, anchor="center")
        self.mg_tree.heading("price", text="Price"); self.mg_tree.column("price", width=80)
        self.mg_tree.pack(fill="both", expand=True)
        self.mg_tree.bind("<<TreeviewSelect>>", lambda e: self._magic_pick())
        right = ttk.Frame(pane); pane.add(right, weight=4)
        sv = ttk.Frame(right); sv.pack(side="bottom", fill="x", pady=3)          # packed first so a small window never hides it
        tabs = TabbedPane(right, level=3); tabs.pack(fill="both", expand=True)
        bpage, cpage, hpage = ttk.Frame(tabs), ttk.Frame(tabs), ttk.Frame(tabs)
        tabs.add(bpage, text="Build"); tabs.add(cpage, text="Card"); tabs.add(hpage, text="History and knowledge")
        self.mg_tabs = tabs
        self._build_magic_build(bpage)
        self._build_magic_card(cpage)
        self._build_magic_history(hpage)
        for text, cmd in (("Save to My Items", self._magic_save_current), ("Add to Custom Content", self._magic_add_current),
                          ("Add to Notebook", self._magic_notebook_current), ("Award to Party", self._magic_award_current),
                          ("Save Its New Spells", lambda: self._save_book_spells(self.magic_cur)),
                          ("Make Card...", self._magic_card_current),
                          ("Export Markdown...", self._magic_export_current)):
            ttk.Button(sv, text=text, command=cmd).pack(side="left", padx=2)
        self._magic_refresh_tie()
        self._magic_show(None)

    def _build_magic_build(self, f):
        head = ttk.Frame(f); head.pack(fill="x", pady=(4, 2))
        ttk.Label(head, text="Name").pack(side="left")
        self.mg_name = tk.StringVar()
        e = ttk.Entry(head, textvariable=self.mg_name); e.pack(side="left", fill="x", expand=True, padx=4)
        e.bind("<FocusOut>", lambda ev: self._magic_commit_name()); e.bind("<Return>", lambda ev: self._magic_commit_name())
        ttk.Button(head, text="Reroll Name", command=self._magic_reroll_name).pack(side="left", padx=2)
        ttk.Button(head, text="Reroll Unlocked", command=self._magic_reroll_all).pack(side="left", padx=2)
        st = ttk.LabelFrame(f, text="Level, rarity, and price"); st.pack(fill="x", pady=2)
        ttk.Label(st, text="Level").grid(row=0, column=0, padx=4)
        self.mg_cur_level = tk.StringVar()
        ttk.Spinbox(st, from_=1, to=20, textvariable=self.mg_cur_level, width=5).grid(row=0, column=1)
        ttk.Button(st, text="Set Level", command=self._magic_apply_level).grid(row=0, column=2, padx=(2, 12))
        ttk.Label(st, text="Rarity").grid(row=0, column=3)
        self.mg_cur_rarity = Combo(st, list(itemgen.RARITIES), readonly=True, width=10); self.mg_cur_rarity.grid(row=0, column=4, padx=(2, 12))
        self.mg_cur_rarity.var.trace_add("write", lambda *a: self._magic_apply_rarity())
        ttk.Label(st, text="Price (gp)").grid(row=0, column=5)
        self.mg_cur_price = tk.StringVar()
        ttk.Entry(st, textvariable=self.mg_cur_price, width=10).grid(row=0, column=6, padx=2)
        ttk.Button(st, text="Set Price", command=self._magic_apply_price).grid(row=0, column=7, padx=2)
        ttk.Button(st, text="Auto Price", command=self._magic_auto_price).grid(row=0, column=8, padx=2)
        self.mg_range = tk.StringVar()
        ttk.Label(st, textvariable=self.mg_range, foreground="#555", wraplength=640, justify="left").grid(row=1, column=0, columnspan=9, sticky="w", padx=4)
        sf = ttk.LabelFrame(f, text="Base weapon or armor stats"); sf.pack(fill="x", pady=2)
        self.mg_stats = tk.Text(sf, height=8, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        self.mg_stats.pack(fill="x", padx=4, pady=3)
        ck = ttk.LabelFrame(f, text="Checks and comparison"); ck.pack(side="bottom", fill="x", pady=2)
        self.mg_checks = tk.Text(ck, height=7, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        self.mg_checks.pack(fill="x", padx=4, pady=3)
        canvas, inner = self._scroll_area(f)
        self.mg_rows = ttk.Frame(inner); self.mg_rows.pack(fill="x")

    def _build_magic_card(self, f):
        bar = ttk.Frame(f); bar.pack(fill="x", pady=3)
        self.mg_player_view = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Player view (hide GM notes and history)", variable=self.mg_player_view,
                        command=self._magic_show_card).pack(side="left", padx=4)
        ttk.Button(bar, text="Copy Player Card", command=lambda: self._magic_copy(False)).pack(side="right", padx=2)
        ttk.Button(bar, text="Copy GM Card", command=lambda: self._magic_copy(True)).pack(side="right", padx=2)
        self.mg_card = RichText(f, self); self.mg_card.pack(fill="both", expand=True)

    def _build_magic_history(self, f):
        bar = ttk.Frame(f); bar.pack(fill="x", pady=3)
        ttk.Button(bar, text="Reroll Unlocked History", command=self._magic_reroll_lore).pack(side="left", padx=2)
        ttk.Button(bar, text="Make History", command=self._magic_make_lore).pack(side="left", padx=2)
        ttk.Label(bar, text="Lock the lines you like, then reroll the rest. The knowledge checks update as you edit.",
                  foreground="#555").pack(side="left", padx=8)
        canvas, inner = self._scroll_area(f)
        self.mg_lore_rows = ttk.Frame(inner); self.mg_lore_rows.pack(fill="x")
        self.mg_know = RichText(f, self); self.mg_know.pack(fill="both", expand=True)

    # ----- settings and generation
    def _magic_settings(self):
        kind = next((k for k, v in itemgen.KINDS.items() if v == self.mg_kind.var.get()), "any")
        ab = self.mg_abil.var.get()
        focus = next((k for k, v in itemgen.FOCUS.items() if v == self.mg_focus.var.get()), "any")
        return dict(kind=kind, level=self._int_or_none(str(self.mg_level.get())) or self.party_level(),
                    vary=self._int_or_none(str(self.mg_vary.get())) or 0, rarity=self.mg_rarity.var.get() or "any",
                    role=self.mg_role.var.get() or "auto", tradition=self.mg_trad.var.get() or "any", focus=focus,
                    themes=self.mg_themes.items(), env=self.mg_env.var.get() or "any", tone=self.mg_tone.var.get() or "any",
                    abilities=int(ab) if ab.isdigit() else 0, quirk=bool(self.mg_quirk.get()),
                    drawback=bool(self.mg_drawback.get()), lore=bool(self.mg_lore.get()),
                    packs=["core"] + (["hallowmead"] if self.mg_hm.get() else []),
                    use_campaign=float(self.mg_use.get()) / 100.0, culture=self._magic_culture_key(),
                    flavor=max(0.0, min(1.0, float(self.mg_flavor.get()) / 100.0)),
                    style=itemgen.style_key(self.mg_style.var.get()))

    def _magic_save_config(self, kw):
        self.config_data["magic"] = {"kind": kw["kind"], "level": kw["level"], "vary": kw["vary"], "rarity": kw["rarity"],
                                     "role": kw["role"], "tradition": kw["tradition"], "focus": kw["focus"],
                                     "themes": kw["themes"], "env": kw["env"], "tone": kw["tone"],
                                     "abilities": self.mg_abil.var.get(), "quirk": kw["quirk"], "drawback": kw["drawback"],
                                     "lore": kw["lore"], "hm": self.mg_hm.get(), "use_campaign": self.mg_use.get(),
                                     "culture": kw["culture"], "flavor": self.mg_flavor.get(), "style": kw.get("style", "standard"),
                                     "count": self._int_or_none(str(self.mg_count.get())) or 4}
        storage.save("config", self.config_data)

    def _magic_refresh_tie(self):
        if not hasattr(self, "mg_tie"):
            return
        names = ["(none)"] + sorted(p["title"] for p in self.notebook
                                    if p.get("type") in ("NPC", "Faction", "Location")
                                    and "gm-only" not in [t.lower() for t in p.get("tags", [])])
        self.mg_tie.set_values(names)
        if self.mg_tie.var.get() not in names:
            self.mg_tie.var.set("(none)")

    def _magic_presets(self):
        name = self.mg_tie.var.get()
        page = nbk.find(self.notebook, name) if name and name != "(none)" else None
        if page is None:
            return None
        typ, title = page.get("type"), page["title"]
        base = set(infer_page_tags(page))
        if typ in ("NPC", "Faction"):
            tags = base | {"k:faction" if typ == "Faction" else "k:npc"}
            return {"who": {"text": sg.inline_name(title), "tags": sorted(tags),
                            "entities": [{"type": typ, "title": title, "campaign": True}]}}
        if typ == "Location":
            text = sg.inline_name(title)
            if page.get("the") and not text.lower().startswith("the "):
                text = "the " + text
            prep = (page.get("preps") or ["at"])[0]
            return {"where": {"text": f"{prep} {text}", "tags": sorted(base),
                              "entities": [{"type": "Location", "title": title, "campaign": True}]}}
        return None

    def _magic_generate(self, count=None, append=False):
        kw = self._magic_settings()
        n = count or max(1, min(8, self._int_or_none(str(self.mg_count.get())) or 4))
        g = self.item_gen
        g.set_registry(self.story_registry)
        g.set_campaign(self._story_campaign())
        presets = self._magic_presets()
        items = [g.generate(presets=presets, **kw) for _ in range(n)]
        self._magic_save_config(kw)
        if append and self.magic_list:
            self.magic_list += items
        else:
            self.magic_list = items
        self._magic_refresh_list(select=len(self.magic_list) - n if append else 0)

    def _magic_refresh_list(self, select=None):
        self.mg_tree.delete(*self.mg_tree.get_children())
        for i, it in enumerate(self.magic_list):
            self.mg_tree.insert("", "end", iid=str(i), text=it["name"],
                                values=(it["level"], itemgen.gp_text(it["price_gp"])))
        if select is not None and self.mg_tree.exists(str(select)):
            self.mg_tree.selection_set(str(select))
        self._magic_pick()

    def _magic_pick(self):
        sel = self.mg_tree.selection()
        if sel and int(sel[0]) < len(self.magic_list):
            self._magic_show(self.magic_list[int(sel[0])])
        elif not self.magic_list:
            self._magic_show(None)

    # ----- showing an item
    def _magic_show(self, item):
        """Rebuild the Build, Card, and History pages for one item."""
        self.magic_cur = item
        for fr in (self.mg_rows, self.mg_lore_rows):
            for w in fr.winfo_children():
                w.destroy()
        self.magic_widgets, self.magic_lore_widgets = {}, {}
        if item is None:
            self.mg_name.set(""); self.mg_cur_level.set(""); self.mg_cur_price.set(""); self.mg_range.set("")
            ttk.Label(self.mg_rows, foreground="#666", justify="left", text=(
                "Pick what you need above and press Generate.\n\nEvery item is built from parts: what it is, what it does, "
                "how it looks, and a quirk. Edit any line, lock it so it stays, or reroll it alone. The History page holds "
                "who made it and what knowledge checks reveal. The Custom Item page builds one by hand.")
                      ).pack(anchor="w", padx=8, pady=20)
            self.mg_card.show_message("Generate an item to see its card.")
            self.mg_know.show_message("")
            self._magic_set_text(self.mg_checks, "")
            self._magic_set_text(self.mg_stats, "")
            return
        self.mg_name.set(item["name"])
        self.mg_cur_level.set(str(item["level"]))
        self.mg_cur_rarity.var.set(item["rarity"])
        self.mg_cur_price.set(f"{item['price_gp']:g}")
        manual = item.get("mode") == "custom"
        main = ttk.Frame(self.mg_rows); main.pack(fill="x"); main.columnconfigure(1, weight=1)
        for r, p in enumerate(item["parts"]):
            fixed = p["key"] in ("potency", "striking", "resilient")
            self.magic_widgets[p["key"]] = self._magic_row(
                main, r, p["label"], p["text"], p["locked"] or p["edited"],
                lambda k=p["key"]: self._magic_commit_part(k), lambda k=p["key"]: self._magic_lock_part(k),
                None if (manual or fixed) else (lambda k=p["key"]: self._magic_reroll_part(k)))
        self._magic_lore_rows(item)
        self._magic_refresh_views()

    def _magic_lore_rows(self, item):
        story = self.item_gen.lore_story(item)
        if story is None:
            ttk.Label(self.mg_lore_rows, foreground="#666", text="No history yet. Press Make History.").pack(anchor="w", padx=8, pady=10)
            return
        main = ttk.Frame(self.mg_lore_rows); main.pack(fill="x"); main.columnconfigure(1, weight=1)
        for r, sl in enumerate(list(story.slots.values())):
            if not sl.text.strip():
                continue
            self.magic_lore_widgets[sl.key] = self._magic_row(
                main, r, sl.label, sl.display(), sl.locked or sl.edited,
                lambda k=sl.key: self._magic_commit_lore(k), lambda k=sl.key: self._magic_lock_lore(k),
                lambda k=sl.key: self._magic_reroll_lore_row(k))

    def _magic_set_text(self, box, text):
        box.configure(state="normal"); box.delete("1.0", "end"); box.insert("end", text); box.configure(state="disabled")

    def _magic_lookup(self):
        key = (len(self.f_items), len(self.c_items))
        if getattr(self, "_magic_lookup_key", None) != key:
            self._magic_lookup_map = {i.name.lower(): (i.level, i.price_gp) for i in self.f_items}
            self._magic_lookup_key = key
        return lambda name: self._magic_lookup_map.get(name.lower())

    def _magic_refresh_views(self):
        item = self.magic_cur
        if item is None:
            return
        rng_ = item.get("price_range")
        if rng_:
            self.mg_range.set(f"GM Core price range for level {item['level']}: {itemgen.gp_text(rng_[0])} to "
                              f"{itemgen.gp_text(rng_[1])}. Role: {item['role']}. Item DC at this level: "
                              f"{itemgen.item_dc(item['level'])}." + ("   Price set by hand." if item["price_edited"] else ""))
        else:
            self.mg_range.set("Runic items take their level and price from their runes: " + itemgen.runic_price_text(item)
                              if item["kind"] in itemgen.RUNIC_KINDS else "")
        self.mg_cur_price.set(f"{item['price_gp']:g}")
        self._magic_show_card()
        lines = [("" if s == "ok" else "Check: " if s == "warn" else "Note: ") + m for s, m in itemgen.check_item(item)]
        res = itemgen.check_against_data(item, self._magic_lookup())
        if res["checked"]:
            lines.append(f"Compared {res['checked']} rune{'s' if res['checked'] != 1 else ''} with your downloaded data: "
                         + ("all match." if not res["problems"] else "differences found."))
            lines += ["Check: " + p for p in res["problems"]]
        sim = itemgen.similar_items(self.all_items, item["level"], item["price_gp"], item["consumable"])
        if sim:
            lines.append("Similar items in your data: " + "; ".join(f"{i.name} (level {i.level}, {itemgen.gp_text(i.price_gp)})" for i in sim))
        self._magic_set_text(self.mg_checks, "\n".join(lines))
        self._magic_set_text(self.mg_stats, self._magic_stats_text(item))
        self.mg_know.show(itemgen.knowledge_segments(item) or [("Turn on History to get knowledge checks.", "muted", None)])
        idx = next((i for i, x in enumerate(self.magic_list) if x is item), None)
        if idx is not None and self.mg_tree.exists(str(idx)):
            self.mg_tree.item(str(idx), text=item["name"], values=(item["level"], itemgen.gp_text(item["price_gp"])))

    @staticmethod
    def _magic_stats_text(item):
        rows = itemgen.stat_lines(item)
        if not rows:
            return ("Pick a base weapon or armor to see its stats." if item["kind"] in itemgen.RUNIC_KINDS
                    else "Only weapons and armor have base stats.")
        return "\n".join((f"      {l}: {t}" if style == "gloss" else f"{l}: {t}") for l, t, style in rows)

    def _magic_show_card(self):
        if self.magic_cur is not None:
            self.mg_card.show(itemgen.card_segments(self.magic_cur, gm=not self.mg_player_view.get()))

    # ----- editing parts
    def _magic_commit_name(self):
        it = self.magic_cur
        if it is None:
            return
        name = self.mg_name.get().strip()
        if name and name != it["name"]:
            it["name"], it["name_edited"] = name, True
            self._magic_refresh_views()

    def _magic_commit_part(self, key):
        it, w = self.magic_cur, self.magic_widgets.get(key)
        p = itemgen.part(it, key) if it else None
        if p is None or w is None:
            return
        new = w[0].get("1.0", "end").strip()
        if new and new != p["text"]:
            itemgen.edit_part(it, key, new)
            w[1].set(True)
            self._magic_refresh_views()

    def _magic_lock_part(self, key):
        it, w = self.magic_cur, self.magic_widgets.get(key)
        p = itemgen.part(it, key) if it else None
        if p is not None and w is not None:
            p["locked"] = bool(w[1].get())
            if not w[1].get():
                p["edited"] = False

    def _magic_commit_all(self):
        self._magic_commit_name()
        for key in list(self.magic_widgets):
            self._magic_commit_part(key)

    def _magic_reroll_part(self, key):
        it = self.magic_cur
        if it is None:
            return
        self._magic_commit_all()
        self.item_gen.set_campaign(self._story_campaign())
        self.item_gen.reroll(it, keys=[key])
        self._magic_show(it)

    def _magic_reroll_all(self):
        it = self.magic_cur
        if it is None:
            return
        self._magic_commit_all()
        self.item_gen.set_campaign(self._story_campaign())
        self.item_gen.reroll(it)
        self._magic_show(it)

    def _magic_reroll_name(self):
        it = self.magic_cur
        if it is not None:
            self.item_gen.make_name(it, force=True)
            it["name_edited"] = False
            self.mg_name.set(it["name"])
            self._magic_refresh_views()

    def _magic_apply_level(self):
        it = self.magic_cur
        n = self._int_or_none(str(self.mg_cur_level.get()))
        if it is None or n is None:
            return
        self._magic_commit_all()
        self.item_gen.rescale(it, n)
        self._magic_show(it)

    def _magic_apply_rarity(self):
        it = self.magic_cur
        if it is not None and self.mg_cur_rarity.var.get() in itemgen.RARITIES and it["rarity"] != self.mg_cur_rarity.var.get():
            itemgen.set_rarity(it, self.mg_cur_rarity.var.get())
            self._magic_refresh_views()

    def _magic_apply_price(self):
        it = self.magic_cur
        if it is None:
            return
        try:
            gp = float(str(self.mg_cur_price.get()).replace(",", ""))
        except ValueError:
            messagebox.showwarning("Price", "Price must be a number of gold pieces."); return
        itemgen.set_price(it, max(0.0, gp))
        self._magic_refresh_views()

    def _magic_auto_price(self):
        if self.magic_cur is not None:
            itemgen.clear_price_edit(self.magic_cur)
            self._magic_refresh_views()

    # ----- the history
    def _magic_commit_lore(self, key):
        it, w = self.magic_cur, self.magic_lore_widgets.get(key)
        story = self.item_gen.lore_story(it) if it else None
        if story is None or w is None or key not in story.slots:
            return
        new = w[0].get("1.0", "end").strip()
        if new and new != story.slots[key].display():
            self.item_gen.gen.edit(story, key, new)
            it["lore"] = story.to_dict()
            w[1].set(True)
            self._magic_refresh_views()

    def _magic_lock_lore(self, key):
        it, w = self.magic_cur, self.magic_lore_widgets.get(key)
        story = self.item_gen.lore_story(it) if it else None
        if story is not None and w is not None and key in story.slots:
            story.slots[key].locked = bool(w[1].get())
            if not w[1].get():
                story.slots[key].edited = False
            it["lore"] = story.to_dict()

    def _magic_reroll_lore_row(self, key):
        it = self.magic_cur
        if it is None:
            return
        self.item_gen.set_campaign(self._story_campaign())
        self.item_gen.reroll_lore(it, keys=[key])
        self._magic_show(it)

    def _magic_reroll_lore(self):
        it = self.magic_cur
        if it is None:
            return
        self.item_gen.set_campaign(self._story_campaign())
        self.item_gen.reroll_lore(it)
        self._magic_show(it)

    def _magic_make_lore(self):
        it = self.magic_cur
        if it is None:
            return
        self.item_gen.set_campaign(self._story_campaign())
        self.item_gen.make_lore(it, self._magic_presets())
        self._magic_show(it)

    # ----- saving an item somewhere
    def _magic_copy(self, gm):
        it = self.magic_cur
        if it is not None:
            self._magic_commit_all()
            self.clipboard_clear(); self.clipboard_append(itemgen.card_text(it, gm=gm))
            self.last_roll.set(f"Copied {it['name']} ({'GM' if gm else 'player'} card) to the clipboard.")

    def _magic_save_current(self):
        self._magic_commit_all()
        self._magic_save_library(self.magic_cur)

    def _magic_add_current(self):
        self._magic_commit_all()
        self._magic_add_custom_content(self.magic_cur)

    def _magic_notebook_current(self):
        self._magic_commit_all()
        self._magic_to_notebook(self.magic_cur)

    def _magic_award_current(self):
        self._magic_commit_all()
        self._magic_award(self.magic_cur)

    def _magic_export_current(self):
        self._magic_commit_all()
        self._magic_export(self.magic_cur)

    def _magic_save_library(self, item):
        if item is None:
            messagebox.showinfo("Nothing to save", "Generate or build an item first."); return
        data = copy.deepcopy(item)
        self.magic_items = [x for x in self.magic_items if x.get("id") != data["id"]] + [data]
        storage.save("magic_items", self.magic_items)
        self._magic_lib_refresh()
        self.last_roll.set(f"Saved '{item['name']}' to My Items." + self._kept_note(item))

    def _magic_add_custom_content(self, item):
        if item is None:
            messagebox.showinfo("Nothing to add", "Generate or build an item first."); return
        c = itemgen.to_custom_item(item)
        self.c_items = [x for x in self.c_items if x.name != c.name] + [c]
        storage.save_custom_items(self.c_items)
        self._refresh_custom()
        self.last_roll.set(f"Added '{c.name}' to Custom Content. It can now turn up in Treasure and Shops." + self._kept_note(item))

    def _magic_to_notebook(self, item):
        if item is None:
            messagebox.showinfo("Nothing to add", "Generate or build an item first."); return
        fields = itemgen.to_page(item, {p["title"] for p in self.notebook})
        page = next((p for p in self.notebook if (p.get("magic_item") or {}).get("id") == item["id"]), None)
        if page is None:
            page = nbk.new_page(nbk.unique_title(self.notebook, fields["title"]), "Item", fields["body"], status="",
                                tags=fields["tags"], magic_item=fields["magic_item"])
            self.notebook.append(page)
            verb = "Added"
        else:
            page.update(body=fields["body"], tags=fields["tags"], magic_item=fields["magic_item"])
            verb = "Updated"
        self._save_notebook(); self._refresh_notebook(select=page["id"])
        self.last_roll.set(f"{verb} '{page['title']}' in the Notebook." + self._kept_note(item))

    def _magic_award(self, item, source="Magic Items", holder=None, quiet=False):
        """Award a generated item: a row in the treasure ledger, and the whole item in Party Loot (party stash)."""
        if item is None:
            messagebox.showinfo("Nothing to award", "Generate or build an item first."); return
        self.ledger.append({"level": int(item["level"]), "kind": "consumable" if item["consumable"] else "permanent",
                            "name": item["name"], "value_gp": float(item["price_gp"]),
                            "date": datetime.date.today().isoformat()})
        storage.save("ledger", self.ledger)
        self._refresh_ledger()
        ploot.add(self.party_loot, ploot.new_entry("", 1, holder=holder or ploot.STASH, magic_item=item, source=source))
        self._pl_changed()
        note = self._kept_note(item)
        if not quiet:
            self.last_roll.set(f"Awarded '{item['name']}' to the party: it's in the treasure ledger and in Party Loot "
                               f"({holder or 'party stash'})." + note)

    def _keep_spell(self, sp, source=None, persist=True):
        """Add a generated spell to your spells (Custom Content, Spells). False if you already have a spell with that name."""
        if lib_find(self.lib_spells, sp["name"]):
            return False
        d = {k: v for k, v in sp.items() if k not in ("style", "theme", "shape")}
        if source:
            d["source"] = source
        self.lib_spells.append(d)
        if persist:
            storage.save("spells", self.lib_spells)
            self._library_changed()
        return True

    def _keep_book_spells(self, item):
        """A grimoire that is kept brings its new spells with it: they are added to your spells. Returns (added, already had)."""
        sp = itemgen.part(item, "spells") if (item and item.get("kind") == "grimoire") else None
        added, have = [], []
        for g in list(((sp or {}).get("data") or {}).get("generated") or []):
            (added if self._keep_spell(g, item["name"], persist=False) else have).append(g["name"])
        if added:
            storage.save("spells", self.lib_spells)
            self._library_changed()
        return added, have

    def _kept_note(self, item):
        """Keep a grimoire's new spells (see _keep_book_spells) and say so, for the status line."""
        added, _have = self._keep_book_spells(item)
        return (f" Its new spell{'s' if len(added) != 1 else ''} ({', '.join(added)}) "
                f"{'were' if len(added) != 1 else 'was'} added to your spells.") if added else ""

    def _save_book_spells(self, item):
        """Save the brand-new spells written in a grimoire to your spells (Custom Content, Spells)."""
        if item is None:
            messagebox.showinfo("Select an item", "Select a grimoire first."); return
        sp = itemgen.part(item, "spells") if item.get("kind") == "grimoire" else None
        if not list(((sp or {}).get("data") or {}).get("generated") or []):
            messagebox.showinfo("No new spells", "This item has no new spells to save. Only a grimoire made with the Grim, "
                                "Whimsical, or Ridiculous style can hold one; its other spells are from your data or "
                                "already yours."); return
        added, have = self._keep_book_spells(item)
        self.last_roll.set((f"Saved {', '.join(added)} to your spells (Custom Content, Spells). " if added else "")
                           + (f"Already in your spells: {', '.join(have)}." if have else ""))

    def _find_generated_spell(self, name):
        """(spell, grimoire) for the brand-new spell called name, written in a grimoire the app is holding; else (None, None)."""
        key = norm(name)
        pools = [getattr(self, "magic_list", None) or [], self.magic_items, [e.get("magic_item") for e in self.party_loot["items"]],
                 [p.get("magic_item") for p in self.notebook], npckit.kit_items(getattr(self, "ng_kit", None)),
                 [getattr(self, "magic_cur", None), getattr(self, "cu_current", None)]]
        for pool in pools:
            for it in pool:
                if not it or it.get("kind") != "grimoire":
                    continue
                for g in (((itemgen.part(it, "spells") or {}).get("data") or {}).get("generated") or []):
                    if norm(g["name"]) == key:
                        return g, it
        return None, None

    def _open_generated_spell(self, name):
        """A click on a (new) spell in a grimoire: once the book is kept the spell is one of yours and opens like any spell;
        until then it opens here, from the book."""
        if self.rules.resolve("spell:" + name):
            self.open_ref("spell:" + name); return
        sp, item = self._find_generated_spell(name)
        if sp is None:
            messagebox.showinfo("Spell", f"'{name}' is a new spell written in a grimoire, but that grimoire can't be found any more.")
            return
        win = tk.Toplevel(self); win.title(sp["name"]); win.geometry("560x520")
        view = RichText(win, self); view.pack(fill="both", expand=True); view.show(render_entry(spell_entry(sp)))
        bar = ttk.Frame(win); bar.pack(fill="x", padx=8, pady=6)
        note = tk.StringVar(value="It is stored in the book, and becomes one of your spells when you keep the book.")

        def keep():
            if self._keep_spell(sp, item["name"]):
                note.set("Saved to your spells (Custom Content, Spells).")
            else:
                note.set("You already have a spell with that name.")
        ttk.Button(bar, text="Save to My Spells", command=keep).pack(side="left")
        ttk.Label(bar, textvariable=note, foreground="#666").pack(side="left", padx=8)
        ttk.Button(bar, text="Close", command=win.destroy).pack(side="right")
        self.gen_spell_win = (win, view, keep, note)

    def _magic_export(self, item):
        if item is None:
            messagebox.showinfo("Nothing to export", "Generate or build an item first."); return
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", item["name"]).strip("_") or "item"
        self._save_text(itemgen.export_markdown(item, gm=True), f"{safe}.md")

    # ----- custom item page
    def _build_magic_custom(self, f):
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pane); pane.add(left, weight=3)
        canvas, ed = self._scroll_area(left)
        grid = ttk.Frame(ed); grid.pack(fill="x", padx=4, pady=4)
        self.cu = {}

        def row(r, label, widget, key, var=None):
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=2, padx=(0, 6))
            widget.grid(row=r, column=1, sticky="we", pady=2)
            self.cu[key] = var if var is not None else widget
        v = tk.StringVar(); row(0, "Name", ttk.Entry(grid, textvariable=v, width=44), "name", v)
        w = Combo(grid, list(itemgen.KINDS.values()), readonly=True, width=18); w.var.set("Worn item"); row(1, "Kind", w, "kind", w.var)
        v = tk.StringVar(value="3"); row(2, "Level", ttk.Spinbox(grid, from_=1, to=20, textvariable=v, width=6), "level", v)
        w = Combo(grid, list(itemgen.RARITIES), readonly=True, width=12); w.var.set("common"); row(3, "Rarity", w, "rarity", w.var)
        w = Combo(grid, list(itemgen.ROLES), readonly=True, width=12); w.var.set("secondary"); row(4, "Role (price placement)", w, "role", w.var)
        v = tk.StringVar(); row(5, "Price (gp, blank = suggest)", ttk.Entry(grid, textvariable=v, width=12), "price", v)
        w = Combo(grid, self.MAGIC_USAGES, width=22); row(6, "Usage", w, "usage", w.var)
        w = Combo(grid, ["-", "L", "1", "2", "3"], width=6); w.var.set("L"); row(7, "Bulk", w, "bulk", w.var)
        w = MultiField(grid, values_key="item_traits", width=40, combo_width=16); w.set(["magical"]); row(8, "Traits", w, "traits")
        v = tk.StringVar(); row(9, "Appearance", ttk.Entry(grid, textvariable=v, width=60), "look", v)
        w = Combo(grid, [""] + sorted(itemdata.WEAPONS) + sorted(itemdata.ARMORS), width=26); row(10, "Base weapon or armor", w, "base", w.var)
        ttk.Label(grid, text="For a runic weapon or armor: its damage, traits, AC, and penalties show on the card.", foreground="#777").grid(row=11, column=1, sticky="w")
        grid.columnconfigure(1, weight=1)
        eb = ttk.LabelFrame(ed, text="Constant effects (what it does while worn or held)"); eb.pack(fill="x", padx=4, pady=4)
        self.cu_effect = tk.Text(eb, height=4, wrap="word"); self.cu_effect.pack(fill="x", padx=4, pady=3)
        ab = ttk.LabelFrame(ed, text="Activations"); ab.pack(fill="x", padx=4, pady=4)
        r1 = ttk.Frame(ab); r1.pack(fill="x", padx=4, pady=2)
        self.cu_an, self.cu_aa, self.cu_at, self.cu_af = tk.StringVar(), tk.StringVar(value="2"), tk.StringVar(), tk.StringVar(value="once per day")
        self.cu_atr, self.cu_ar, self.cu_ae = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for lbl, w in (("Name", ttk.Entry(r1, textvariable=self.cu_an, width=18)),
                       ("Actions", ttk.Combobox(r1, textvariable=self.cu_aa, values=["1", "2", "3", "R", "F"], width=3, state="readonly")),
                       ("Traits", ttk.Entry(r1, textvariable=self.cu_at, width=18)),
                       ("Frequency", ttk.Combobox(r1, textvariable=self.cu_af, values=self.MAGIC_FREQS, width=18))):
            ttk.Label(r1, text=lbl).pack(side="left", padx=(4, 2)); w.pack(side="left")
        r2 = ttk.Frame(ab); r2.pack(fill="x", padx=4, pady=2)
        for lbl, w in (("Trigger", ttk.Entry(r2, textvariable=self.cu_atr, width=22)),
                       ("Requirements", ttk.Entry(r2, textvariable=self.cu_ar, width=22)),
                       ("Effect", ttk.Entry(r2, textvariable=self.cu_ae, width=40))):
            ttk.Label(r2, text=lbl).pack(side="left", padx=(4, 2)); w.pack(side="left")
        ttk.Button(r2, text="Add Activation", command=self._cu_add_activation).pack(side="left", padx=6)
        ttk.Label(ab, text="One per line:  name | actions | traits | frequency | trigger | requirements | effect   (edit freely)",
                  foreground="#777").pack(anchor="w", padx=4)
        self.cu_acts = tk.Text(ab, height=4, wrap="none"); self.cu_acts.pack(fill="x", padx=4, pady=2)
        nb_ = ttk.LabelFrame(ed, text="Notes (shown on the card)"); nb_.pack(fill="x", padx=4, pady=4)
        self.cu_notes = tk.Text(nb_, height=3, wrap="word"); self.cu_notes.pack(fill="x", padx=4, pady=3)
        bb = ttk.Frame(ed); bb.pack(fill="x", padx=4, pady=4)
        for text, cmd in (("Preview and Check", self._cu_preview), ("Suggest Price", self._cu_suggest_price),
                          ("Make History", self._cu_make_lore), ("Save to My Items", self._cu_save),
                          ("Add to Custom Content", self._cu_add_content), ("Add to Notebook", self._cu_notebook),
                          ("Make Card...", self._cu_card), ("New", self._cu_new)):
            ttk.Button(bb, text=text, command=cmd).pack(side="left", padx=2, pady=2)
        right = ttk.Frame(pane); pane.add(right, weight=3)
        self.cu_checks = tk.Text(right, height=7, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        self.cu_checks.pack(fill="x", padx=2, pady=(0, 4))
        self.cu_card = RichText(right, self); self.cu_card.pack(fill="both", expand=True)
        self.cu_card.show_message("Fill in the form and press Preview and Check. The check compares the level, price, bonuses, "
                                  "spell ranks, and DCs with the GM Core item-building guidelines.")
        self.cu_current = None

    def _cu_add_activation(self):
        name = self.cu_an.get().strip()
        if not name:
            return
        line = " | ".join([name, self.cu_aa.get().strip() or "2", self.cu_at.get().strip(), self.cu_af.get().strip(),
                           self.cu_atr.get().strip(), self.cu_ar.get().strip(), self.cu_ae.get().strip()])
        existing = self.cu_acts.get("1.0", "end").strip()
        self.cu_acts.delete("1.0", "end")
        self.cu_acts.insert("1.0", (existing + "\n" if existing else "") + line)
        for v in (self.cu_an, self.cu_at, self.cu_atr, self.cu_ar, self.cu_ae):
            v.set("")

    @staticmethod
    def _cu_parse_acts(text):
        acts = []
        for ln in str(text).splitlines():
            if not ln.strip():
                continue
            p = [x.strip() for x in ln.split("|")] + [""] * 7
            actions = p[1] if p[1] in ("R", "F") else (int(p[1]) if p[1].isdigit() and 1 <= int(p[1]) <= 3 else 2)
            acts.append({"name": p[0] or "Activate", "actions": actions, "traits": [t.strip() for t in p[2].split(",") if t.strip()],
                         "frequency": p[3], "trigger": p[4], "requirements": p[5], "effect": p[6]})
        return acts

    def _cu_item_from_form(self):
        c = self.cu
        name = c["name"].get().strip()
        if not name:
            messagebox.showwarning("Name", "Give the item a name."); return None
        level = self._int_or_none(str(c["level"].get()))
        if level is None:
            messagebox.showwarning("Level", "Enter a level from 1 to 20."); return None
        kind = next((k for k, v in itemgen.KINDS.items() if v == c["kind"].get()), "worn")
        price = str(c["price"].get()).replace(",", "").strip()
        try:
            gp = float(price) if price else None
        except ValueError:
            messagebox.showwarning("Price", "Price must be a number of gold pieces, or blank to suggest one."); return None
        fields = dict(name=name, kind=kind, level=level, rarity=c["rarity"].get() or "common", price_gp=gp,
                      traits=c["traits"].items(), usage=c["usage"].get().strip(), bulk=c["bulk"].get().strip() or "L",
                      effect=self.cu_effect.get("1.0", "end").strip(), activations=self._cu_parse_acts(self.cu_acts.get("1.0", "end")),
                      look=c["look"].get().strip(), notes=self.cu_notes.get("1.0", "end").strip(), role=c["role"].get() or "secondary",
                      base=c["base"].get().strip())
        if self.cu_current is not None:
            return itemgen.update_custom(self.cu_current, **fields)
        return itemgen.custom_item(**fields)

    def _cu_preview(self):
        item = self._cu_item_from_form()
        if item is None:
            return
        self.cu_current = item
        lines = [("" if s == "ok" else "Check: " if s == "warn" else "Note: ") + m for s, m in itemgen.check_item(item)]
        sim = itemgen.similar_items(self.all_items, item["level"], item["price_gp"], item["consumable"])
        if sim:
            lines.append("Similar items in your data: " + "; ".join(f"{i.name} (level {i.level}, {itemgen.gp_text(i.price_gp)})" for i in sim))
        self._magic_set_text(self.cu_checks, "\n".join(lines))
        self.cu_card.show(itemgen.card_segments(item, gm=True))
        self.cu["price"].set(f"{item['price_gp']:g}") if not item["price_edited"] else None

    def _cu_suggest_price(self):
        level = self._int_or_none(str(self.cu["level"].get())) or 1
        kind = next((k for k, v in itemgen.KINDS.items() if v == self.cu["kind"].get()), "worn")
        role = self.cu["role"].get() or "secondary"
        consumable = kind in itemgen.CONSUMABLE_KINDS
        gp = itemgen.place_price(level, consumable, itemdata.ROLE_T.get(role, 0.55))
        lo, hi = itemgen.price_range(level, consumable)
        self.cu["price"].set(f"{gp:g}")
        self._magic_set_text(self.cu_checks, f"Level {level} {'consumable' if consumable else 'permanent'} items run "
                                             f"{itemgen.gp_text(lo)} to {itemgen.gp_text(hi)} in GM Core. A {role} item sits "
                                             f"near {itemgen.gp_text(gp)}. Item DC at this level: {itemgen.item_dc(level)}.")

    def _cu_make_lore(self):
        item = self._cu_item_from_form()
        if item is None:
            return
        self.item_gen.set_campaign(self._story_campaign())
        self.item_gen.make_lore(item, None)
        self.cu_current = item
        self._cu_preview()

    def _cu_new(self):
        self.cu_current = None
        for k, v in (("name", ""), ("level", "3"), ("price", ""), ("usage", ""), ("look", ""), ("base", "")):
            self.cu[k].set(v)
        self.cu["kind"].set("Worn item"); self.cu["rarity"].set("common"); self.cu["role"].set("secondary"); self.cu["bulk"].set("L")
        self.cu["traits"].set(["magical"])
        for t in (self.cu_effect, self.cu_acts, self.cu_notes):
            t.delete("1.0", "end")
        self._magic_set_text(self.cu_checks, "")
        self.cu_card.show_message("Fill in the form and press Preview and Check.")

    def _cu_save(self):
        self._cu_preview()
        self._magic_save_library(self.cu_current)

    def _cu_add_content(self):
        self._cu_preview()
        self._magic_add_custom_content(self.cu_current)

    def _cu_notebook(self):
        self._cu_preview()
        self._magic_to_notebook(self.cu_current)

    def _cu_load(self, item):
        """Put a saved item into the custom form so it can be edited by hand."""
        self.cu_current = copy.deepcopy(item)
        c = self.cu
        c["name"].set(item["name"]); c["level"].set(str(item["level"])); c["kind"].set(itemgen.KINDS.get(item["kind"], "Worn item"))
        c["rarity"].set(item["rarity"]); c["role"].set(item.get("role", "secondary")); c["usage"].set(item.get("usage", ""))
        c["bulk"].set(item.get("bulk", "L")); c["price"].set(f"{item['price_gp']:g}")
        c["traits"].set([t for t in item.get("traits", []) if t not in itemgen.RARITIES])
        look = itemgen.part(item, "look")
        c["look"].set(look["text"] if look else "")
        bp = itemgen.part(item, "base")
        c["base"].set(bp["data"]["base"] if bp else "")
        eff = [p["text"] for p in item["parts"] if p["key"].startswith("effect")]
        eff += [p["text"] for p in item["parts"] if p["key"] in ("potency", "striking", "resilient") or p["key"].startswith("rune")]
        self.cu_effect.delete("1.0", "end"); self.cu_effect.insert("1.0", "\n".join(eff))
        acts = [a for _, a in itemgen.all_acts(item)]
        self.cu_acts.delete("1.0", "end")
        self.cu_acts.insert("1.0", "\n".join(" | ".join([a["name"], str(a["actions"]), ", ".join(a.get("traits") or []),
                                                          a.get("frequency", ""), a.get("trigger", ""), a.get("requirements", ""),
                                                          a.get("effect", "")]) for a in acts))
        self.cu_notes.delete("1.0", "end"); self.cu_notes.insert("1.0", item.get("notes", ""))
        self.magic_sub.select(self.magic_custom_page)
        self._cu_preview()

    # ----- library page
    def _build_magic_library(self, f):
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Find").pack(side="left")
        self.ml_q = tk.StringVar()
        ttk.Entry(top, textvariable=self.ml_q, width=24).pack(side="left", padx=4)
        self.ml_q.trace_add("write", lambda *a: self._magic_lib_refresh())
        for text, cmd in (("Open in Generator", self._magic_lib_open), ("Edit as Custom Item", self._magic_lib_edit),
                          ("Duplicate", self._magic_lib_dup), ("Delete", self._magic_lib_delete),
                          ("Award to Party", lambda: self._magic_award(self._magic_lib_current(), source="My Items")),
                          ("Save Its New Spells", lambda: self._save_book_spells(self._magic_lib_current())),
                          ("Make Card...", lambda: self._card_magic(self._magic_lib_current())),
                          ("Export All...", self._magic_lib_export)):
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=2)
        self.ml_tree = ttk.Treeview(left, columns=("kind", "lvl", "price"), show="tree headings", height=20)
        self.ml_tree.heading("#0", text="Item"); self.ml_tree.column("#0", width=240)
        for c, t, w in (("kind", "Kind", 90), ("lvl", "Lvl", 36), ("price", "Price", 90)):
            self.ml_tree.heading(c, text=t); self.ml_tree.column(c, width=w)
        self.ml_tree.pack(fill="both", expand=True)
        self.ml_tree.bind("<<TreeviewSelect>>", lambda e: self._magic_lib_show())
        self.ml_card = RichText(pane, self); pane.add(self.ml_card, weight=3)
        self.ml_card.show_message("Items you save appear here. Save from the Generate or Custom Item page.")
        self._magic_lib_refresh()

    def _magic_lib_refresh(self):
        if not hasattr(self, "ml_tree"):
            return
        q = self.ml_q.get().strip().lower()
        self.ml_tree.delete(*self.ml_tree.get_children())
        for it in sorted(self.magic_items, key=lambda x: (x["level"], x["name"].lower())):
            if q and q not in it["name"].lower() and q not in itemgen.KINDS.get(it["kind"], "").lower():
                continue
            self.ml_tree.insert("", "end", iid=it["id"], text=it["name"],
                                values=(itemgen.KINDS.get(it["kind"], it["kind"]), it["level"], itemgen.gp_text(it["price_gp"])))

    def _magic_lib_current(self):
        sel = self.ml_tree.selection()
        return next((x for x in self.magic_items if sel and x["id"] == sel[0]), None)

    def _magic_lib_show(self):
        it = self._magic_lib_current()
        if it is not None:
            self.ml_card.show(itemgen.card_segments(it, gm=True))

    def _magic_lib_open(self):
        it = self._magic_lib_current()
        if it is None:
            messagebox.showinfo("Select an item", "Select a saved item first."); return
        self.magic_list.append(copy.deepcopy(it))
        self.magic_sub.select(self.magic_gen_page)
        self._magic_refresh_list(select=len(self.magic_list) - 1)

    def _magic_lib_edit(self):
        it = self._magic_lib_current()
        if it is None:
            messagebox.showinfo("Select an item", "Select a saved item first."); return
        self._cu_load(it)

    def _magic_lib_dup(self):
        it = self._magic_lib_current()
        if it is None:
            return
        new = copy.deepcopy(it)
        new["id"] = uuid.uuid4().hex[:10]
        new["name"] = f"{it['name']} (copy)"
        self.magic_items.append(new)
        storage.save("magic_items", self.magic_items)
        self._magic_lib_refresh()

    def _magic_lib_delete(self):
        it = self._magic_lib_current()
        if it is not None and messagebox.askyesno("Delete item", f"Delete '{it['name']}' from My Items? "
                                                  "Copies in Custom Content and the Notebook stay."):
            self.magic_items = [x for x in self.magic_items if x["id"] != it["id"]]
            storage.save("magic_items", self.magic_items)
            self._magic_lib_refresh()
            self.ml_card.show_message("Item deleted.")

    def _magic_lib_export(self):
        if not self.magic_items:
            messagebox.showinfo("Nothing to export", "No saved items yet."); return
        text = "\n\n---\n\n".join(itemgen.export_markdown(x, gm=True) for x in sorted(self.magic_items, key=lambda y: (y["level"], y["name"])))
        self._save_text(text, "magic_items.md")

    # ---------- Story Forge ----------
    STORY_ENVS = ["any", "urban", "wild", "underground", "road", "water"]
    STORY_TONES = ["any", "grim", "light", "weird"]
    STORY_SCENES = ["any", "travel", "dungeon", "social", "downtime"]
    STORY_SEASONS = ["any", "spring", "summer", "autumn", "winter"]

    def _story_kind_titles(self):
        reg = self.story_registry
        return {reg.recipe(k).get("title", k): k for k in reg.visible_recipe_names()}

    def _story_kind_key(self):
        titles = self._story_kind_titles()
        return titles.get(self.story_kind.var.get(), next(iter(titles.values()), "rumor"))

    def _story_refresh_kinds(self):
        """Keep the Story type list in step with the editor (new and renamed types appear at once)."""
        if hasattr(self, "story_kind"):
            titles = list(self._story_kind_titles())
            cur = self.story_kind.var.get()
            self.story_kind.set_values(titles)
            if cur not in titles and titles:
                self.story_kind.var.set(titles[0])

    def _build_story(self):
        f = self.tab_story
        cfg = self.config_data.get("story", {})
        top = ttk.LabelFrame(f, text="What do you need?")
        top.pack(fill="x", padx=8, pady=(6, 2))

        def lab(text, r, c):
            ttk.Label(top, text=text).grid(row=r, column=c, sticky="w", padx=(10 if c else 4, 4), pady=2)
        lab("Story type", 0, 0)
        self.story_kind = Combo(top, [], readonly=True, width=16); self.story_kind.grid(row=0, column=1, sticky="w")
        lab("Theme", 0, 2)
        self.story_themes = MultiField(top, values=sg.THEMES, width=26, combo_width=11)
        self.story_themes.grid(row=0, column=3, columnspan=2, sticky="w")
        self.story_themes.set(cfg.get("themes", []))
        lab("Setting", 0, 5)
        self.story_env = Combo(top, self.STORY_ENVS, readonly=True, width=12); self.story_env.grid(row=0, column=6, sticky="w")
        self.story_env.var.set(cfg.get("env", "any"))
        lab("Tone", 0, 7)
        self.story_tone = Combo(top, self.STORY_TONES, readonly=True, width=8); self.story_tone.grid(row=0, column=8, sticky="w")
        self.story_tone.var.set(cfg.get("tone", "any"))
        lab("Scene", 1, 0)
        self.story_scene = Combo(top, self.STORY_SCENES, readonly=True, width=16); self.story_scene.grid(row=1, column=1, sticky="w")
        self.story_scene.var.set(cfg.get("scene", "any"))
        ttk.Label(top, text="(complications)", foreground="#888").grid(row=1, column=2, sticky="w")
        lab("Party level", 1, 3)
        self.story_lvl = tk.StringVar(value=str(self.party_level()))
        ttk.Spinbox(top, from_=1, to=20, textvariable=self.story_lvl, width=5).grid(row=1, column=4, sticky="w")
        lab("Season", 1, 5)
        self.story_season = Combo(top, self.STORY_SEASONS, readonly=True, width=12); self.story_season.grid(row=1, column=6, sticky="w")
        self.story_season.var.set(cfg.get("season", "any"))
        lab("Options", 1, 7)
        self.story_count = tk.StringVar(value=str(cfg.get("count", 4)))
        ttk.Spinbox(top, from_=1, to=8, textvariable=self.story_count, width=4).grid(row=1, column=8, sticky="w")
        lab("Stay on theme", 2, 0)
        self.story_focus = tk.DoubleVar(value=cfg.get("focus", 60))
        ttk.Scale(top, from_=0, to=100, orient="horizontal", variable=self.story_focus, length=150).grid(row=2, column=1, sticky="w")
        ttk.Label(top, text="loose  ...  strict", foreground="#888").grid(row=2, column=2, columnspan=2, sticky="w")
        lab("Use my campaign", 2, 5)
        self.story_use = tk.DoubleVar(value=cfg.get("use_campaign", 60))
        ttk.Scale(top, from_=0, to=100, orient="horizontal", variable=self.story_use, length=150).grid(row=2, column=6, columnspan=2, sticky="w")
        bb = ttk.Frame(top); bb.grid(row=0, column=9, rowspan=3, padx=10)
        ttk.Button(bb, text="Generate", command=self._story_generate).pack(fill="x", pady=1)
        ttk.Button(bb, text="Add One More", command=lambda: self._story_generate(count=1, append=True)).pack(fill="x", pady=1)
        ttk.Button(bb, text="Edit Tables...", command=self._story_open_tables).pack(fill="x", pady=1)
        packs = ttk.Frame(f); packs.pack(fill="x", padx=12)
        ttk.Label(packs, text="Content:").pack(side="left")
        self.story_pack_vars = {}
        saved = cfg.get("packs")
        if saved is None:
            saved = ["underground", "hallowmead"]
        elif not cfg.get("hallowmead_pack_seen"):
            saved = list(saved) + ["hallowmead"]           # configs saved before the pack existed get it once
        for key, label in (("hallowmead", "Hallowmead setting"), ("underground", "Underground (general)"),
                           ("sf", "Starfinder")):
            v = tk.BooleanVar(value=key in saved)
            ttk.Checkbutton(packs, text=label, variable=v).pack(side="left", padx=6)
            self.story_pack_vars[key] = v
        ttk.Label(packs, text="Setting flavor").pack(side="left", padx=(10, 2))
        self.story_flavor = tk.DoubleVar(value=cfg.get("flavor", sg.DEFAULT_FLAVOR * 100))
        ttk.Scale(packs, from_=0, to=100, orient="horizontal", variable=self.story_flavor, length=90).pack(side="left")
        ttk.Button(packs, text="Load Hallowmead Setting...", command=self._hallowmead_dialog).pack(side="left", padx=(10, 2))
        ttk.Button(packs, text="Setting Demographics...", command=self._demographics_dialog).pack(side="left", padx=4)
        self.story_info = tk.StringVar()
        ttk.Label(packs, textvariable=self.story_info, foreground="#555").pack(side="left", padx=6)

        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        ttk.Label(left, text="Options (click to open, edit, and keep)", foreground="#555").pack(anchor="w")
        self.story_tree = ttk.Treeview(left, show="tree", height=18); self.story_tree.column("#0", width=260)
        self.story_tree.pack(fill="both", expand=True)
        self.story_tree.bind("<<TreeviewSelect>>", lambda e: self._story_pick())
        right = ttk.Frame(pane); pane.add(right, weight=4)
        head = ttk.Frame(right); head.pack(fill="x")
        ttk.Label(head, text="Title").pack(side="left")
        self.story_title_var = tk.StringVar()
        te = ttk.Entry(head, textvariable=self.story_title_var); te.pack(side="left", fill="x", expand=True, padx=4)
        te.bind("<FocusOut>", lambda e: self._story_commit_title())
        ttk.Button(head, text="Reroll Unlocked", command=self._story_reroll_all).pack(side="left", padx=2)
        ttk.Button(head, text="Recompose Summary", command=self._story_recompose).pack(side="left", padx=2)
        mid = ttk.Frame(right); mid.pack(fill="both", expand=True, pady=2)
        self.story_canvas = tk.Canvas(mid, highlightthickness=0)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.story_canvas.yview)
        self.story_inner = ttk.Frame(self.story_canvas)
        self.story_inner.bind("<Configure>", lambda e: self.story_canvas.configure(scrollregion=self.story_canvas.bbox("all")))
        win_id = self.story_canvas.create_window((0, 0), window=self.story_inner, anchor="nw")
        self.story_canvas.bind("<Configure>", lambda e: self.story_canvas.itemconfigure(win_id, width=e.width))
        self.story_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.story_canvas.pack(side="left", fill="both", expand=True)
        self.bind_all("<MouseWheel>", self._story_wheel, add="+")
        self.story_rows = ttk.Frame(self.story_inner); self.story_rows.pack(fill="x")
        self.story_extra_frame = ttk.Frame(self.story_inner); self.story_extra_frame.pack(fill="x", pady=4)
        sumbox = ttk.LabelFrame(right, text="Summary (edit freely; it's what goes in your notes)")
        sumbox.pack(fill="x", pady=2)
        self.story_summary = tk.Text(sumbox, height=4, wrap="word"); self.story_summary.pack(fill="x", padx=4, pady=3)
        self.story_summary.bind("<FocusOut>", lambda e: self._story_commit_summary())
        sv = ttk.Frame(right); sv.pack(fill="x", pady=3)
        ttk.Label(sv, text="Save as").pack(side="left")
        self.story_save_type = Combo(sv, nbk.PAGE_TYPES, readonly=True, width=13); self.story_save_type.pack(side="left", padx=4)
        self.story_make_pages = tk.BooleanVar(value=cfg.get("make_pages", True))
        ttk.Checkbutton(sv, text="Also create pages for new people and factions", variable=self.story_make_pages).pack(side="left", padx=6)
        ttk.Button(sv, text="Copy Text", command=self._story_copy).pack(side="right", padx=2)
        self.story_update_btn = ttk.Button(sv, text="Update Notebook Page", command=lambda: self._story_add_to_notebook(True))
        self.story_update_btn.pack(side="right", padx=2)
        ttk.Button(sv, text="Add to Notebook", command=lambda: self._story_add_to_notebook(False)).pack(side="right", padx=2)
        self.story_widgets = {}
        self.story_list = []
        self.story_cur = None
        self.story_page_id = None
        self._story_refresh_kinds()
        self.story_kind.var.set(next((t for t, k in self._story_kind_titles().items() if k == cfg.get("kind", "rumor")),
                                     next(iter(self._story_kind_titles()), "")))
        self._story_refresh_info()
        self._story_show(None)

    def _story_wheel(self, e):
        try:
            if str(e.widget).startswith(str(self.story_canvas)):
                self.story_canvas.yview_scroll(int(-e.delta / 120), "units")
        except Exception:
            pass

    def _story_refresh_info(self):
        if not hasattr(self, "story_info"):
            return
        c = self._story_campaign()
        n = c.counts()
        if any(n[k] for k in ("factions", "npcs", "locations", "events")):
            self.story_info.set(f"Your world: {n['factions']} factions, {n['npcs']} NPCs, {n['locations']} places, "
                                f"{n['events']} upcoming events")
        else:
            self.story_info.set("Add Faction, NPC, Location, and Event pages in the Notebook and stories will use them.")

    def _story_creatures(self):
        key = (len(self.f_creatures), len(self.c_creatures), tuple(sorted(self.systems())))
        if getattr(self, "_story_cc_key", None) != key:
            self._story_cc = [{"name": c.name, "level": c.level, "traits": list(c.traits)} for c in self.all_creatures
                              if not c.is_hazard and self.in_systems(c) and not c.adjust]
            self._story_cc_key = key
        return self._story_cc

    def _ancestry_weights(self):
        w = self.config_data.get("ancestry_weights") or {}
        return {k: float(v) for k, v in w.items() if isinstance(v, (int, float)) and v > 0}

    def _story_campaign(self):
        lvl = self._int_or_none(str(self.story_lvl.get())) if hasattr(self, "story_lvl") else None
        c = sg.Campaign.from_pages(self.notebook, party=self.party, creatures=self._story_creatures(),
                                   level=lvl or self.party_level(), party_size=self.party_size())
        c.ancestry_weights = self._ancestry_weights()
        return c

    def _story_settings(self):
        packs = ["core"] + [k for k, v in self.story_pack_vars.items() if v.get()]
        season = self.story_season.var.get()
        try:
            flavor = max(0.0, min(0.95, float(self.story_flavor.get()) / 100.0))
        except (tk.TclError, ValueError):
            flavor = sg.DEFAULT_FLAVOR
        return {"pack_share": flavor if "hallowmead" in packs else None, "anchor": "what",
                "themes": self.story_themes.items(), "env": self.story_env.var.get() or "any",
                "tone": self.story_tone.var.get() or "any", "scene": self.story_scene.var.get() or "any",
                "level": self._int_or_none(str(self.story_lvl.get())) or self.party_level(),
                "focus": float(self.story_focus.get()) / 100.0, "use_campaign": float(self.story_use.get()) / 100.0,
                "season": "" if season == "any" else season, "packs": packs}

    def _story_save_config(self, kind):
        s = self._story_settings()
        self.config_data["story"] = {"kind": kind, "themes": s["themes"], "env": s["env"], "tone": s["tone"],
                                     "scene": s["scene"], "season": s["season"] or "any", "focus": self.story_focus.get(),
                                     "use_campaign": self.story_use.get(), "flavor": self.story_flavor.get(),
                                     "count": self._int_or_none(str(self.story_count.get())) or 4,
                                     "packs": [k for k, v in self.story_pack_vars.items() if v.get()],
                                     "hallowmead_pack_seen": True,
                                     "make_pages": self.story_make_pages.get()}
        storage.save("config", self.config_data)

    def _story_generate(self, count=None, append=False, presets=None, kind=None):
        """Roll stories from the current settings. presets pins slots (a faction, NPC, place, or event of yours)."""
        kind = kind or self._story_kind_key()
        n = count or max(1, min(8, self._int_or_none(str(self.story_count.get())) or 4))
        gen = self.story_gen
        gen.registry, gen.campaign = self.story_registry, self._story_campaign()
        kw = self._story_settings()
        stories = gen.generate_batch(kind, n, presets=presets, **kw)         # n different stories, never three copies of one
        self._story_save_config(kind)
        if append and self.story_list:
            self.story_list += stories
        else:
            self.story_list = stories
        self.story_page_id = None
        self._story_refresh_list(select=len(self.story_list) - n if append else 0)
        self._story_refresh_info()

    def _story_refresh_list(self, select=None):
        self.story_tree.delete(*self.story_tree.get_children())
        for i, st in enumerate(self.story_list):
            self.story_tree.insert("", "end", iid=str(i), text=st.title)
        if select is not None and self.story_tree.exists(str(select)):
            self.story_tree.selection_set(str(select))
        self._story_pick()

    def _story_pick(self):
        sel = self.story_tree.selection()
        if sel and int(sel[0]) < len(self.story_list):
            self.story_cur = self.story_list[int(sel[0])]
            self._story_show(self.story_cur)
        elif not self.story_list:
            self._story_show(None)

    def _story_show(self, story):
        """Rebuild the editor for one story."""
        self.story_cur = story
        for fr in (self.story_rows, self.story_extra_frame):
            for w in fr.winfo_children():
                w.destroy()
        self.story_widgets = {}
        self.story_summary.delete("1.0", "end")
        if story is None:
            self.story_title_var.set("")
            ttk.Label(self.story_rows, foreground="#666", justify="left", text=(
                "Pick what you need above and press Generate.\n\n"
                "Every story answers who, what, where, when, and why. Each line can be edited by typing, locked so it "
                "stays put, or rerolled on its own. Stories use the factions, NPCs, places, and events in your "
                "Notebook, and Edit Tables lets you change everything it draws from.")).pack(anchor="w", padx=8, pady=20)
            return
        self.story_title_var.set(story.title)
        main = ttk.Frame(self.story_rows); main.pack(fill="x")
        main.columnconfigure(1, weight=1)
        r = 0
        for slot in story.main():
            self._story_add_row(main, r, slot); r += 1
        extras = [s for s in story.slots.values() if s.extra and (s.text or s.key == "rep")]
        if extras:
            ttk.Label(main, text="Details", font=("TkDefaultFont", 10, "bold"), foreground="#555").grid(
                row=r, column=0, columnspan=4, sticky="w", padx=4, pady=(8, 0)); r += 1
            for slot in extras:
                if slot.key == "rep" and not story.rep:
                    continue
                self._story_add_row(main, r, slot); r += 1
        self.story_summary.insert("1.0", story.summary)
        if story.rep:
            fr = ttk.LabelFrame(self.story_extra_frame, text="When the story is resolved, update reputation")
            fr.pack(fill="x", padx=4, pady=2)
            for i, e in enumerate(story.rep):
                label = (f"Party helped {e['faction']}: {e['points']:+d}" if e["kind"] == "favor"
                         else f"Party hindered {e['faction']}: {e['points']:+d}")
                ttk.Button(fr, text=label, command=lambda ent=e: self._story_apply_rep(ent)).pack(side="left", padx=4, pady=4)
        enc = story.encounter
        if enc:
            fr = ttk.Frame(self.story_extra_frame); fr.pack(fill="x", padx=4, pady=2)
            traits = ", ".join(enc.get("traits", [])) or "any creatures"
            ttk.Label(fr, text=f"Suggested fight: {enc.get('threat', '')} threat, {traits}").pack(side="left")
            ttk.Button(fr, text="Build an Encounter", command=self._story_make_encounter).pack(side="left", padx=8)
        self.story_save_type.var.set(story.page_type)
        if story.problems:
            ttk.Label(self.story_extra_frame, foreground="#a33", wraplength=700, text=(
                "Some table references didn't resolve: " + ", ".join(sorted({str(p[1]) for p in story.problems})[:6])
                + ". Open Edit Tables and use Check All Tables.")).pack(anchor="w", padx=4)

    def _story_add_row(self, parent, r, slot):
        bold = ("TkDefaultFont", 10, "bold")
        ttk.Label(parent, text=slot.label, font=bold).grid(row=r, column=0, sticky="nw", padx=(4, 8), pady=3)
        h = max(1, min(5, -(-len(slot.display()) // 78)))
        t = tk.Text(parent, height=h, width=80, wrap="word", font=("TkDefaultFont", 10), padx=4, pady=2)
        t.insert("1.0", slot.display())
        t.grid(row=r, column=1, sticky="we", pady=3)
        t.bind("<FocusOut>", lambda e, k=slot.key: self._story_commit_slot(k))
        lock = tk.BooleanVar(value=slot.locked or slot.edited)
        ttk.Checkbutton(parent, text="Lock", variable=lock, command=lambda k=slot.key: self._story_lock(k)).grid(row=r, column=2, padx=4)
        ttk.Button(parent, text="Reroll", width=7, command=lambda k=slot.key: self._story_reroll_slot(k)).grid(row=r, column=3, padx=(0, 4))
        self.story_widgets[slot.key] = (t, lock)

    def _story_commit_slot(self, key):
        st = self.story_cur
        w = self.story_widgets.get(key)
        if not st or not w or key not in st.slots:
            return
        new = w[0].get("1.0", "end").strip()
        if new and new != st.slots[key].display():
            self.story_gen.edit(st, key, new)
            w[1].set(True)
            self._story_refresh_summary()

    def _story_refresh_summary(self):
        st = self.story_cur
        if not st:
            return
        self.story_summary.delete("1.0", "end"); self.story_summary.insert("1.0", st.summary)
        self.story_title_var.set(st.title)
        idx = next((i for i, s in enumerate(self.story_list) if s is st), None)
        if idx is not None and self.story_tree.exists(str(idx)):
            self.story_tree.item(str(idx), text=st.title)

    def _story_commit_summary(self):
        st = self.story_cur
        if st:
            txt = self.story_summary.get("1.0", "end").strip()
            if txt and txt != st.summary:
                self.story_gen.set_summary(st, txt)

    def _story_commit_title(self):
        st = self.story_cur
        if st:
            t = self.story_title_var.get().strip()
            if t and t != st.title:
                st.title, st.title_edited = t, True
                self._story_refresh_summary()

    def _story_commit_all(self):
        """Take whatever is typed in the title, summary, and lines. Title and summary first, so hand edits to them
        survive the summary being recomposed from the lines."""
        self._story_commit_title()
        self._story_commit_summary()
        for key in list(self.story_widgets):
            self._story_commit_slot(key)

    def _story_lock(self, key):
        st, w = self.story_cur, self.story_widgets.get(key)
        if st and w and key in st.slots:
            st.slots[key].locked = bool(w[1].get())
            if not w[1].get():
                st.slots[key].edited = False

    def _story_reroll_slot(self, key):
        st = self.story_cur
        if st:
            self._story_commit_all()
            self.story_gen.registry, self.story_gen.campaign = self.story_registry, self._story_campaign()
            st.slots[key].locked = st.slots[key].edited = False
            self.story_gen.reroll(st, keys=[key])
            self._story_show(st); self._story_refresh_summary()

    def _story_reroll_all(self):
        st = self.story_cur
        if st:
            self._story_commit_all()
            self.story_gen.registry, self.story_gen.campaign = self.story_registry, self._story_campaign()
            themes = self.story_themes.items()
            self.story_gen.reroll(st, themes=themes if themes else None)
            self._story_show(st); self._story_refresh_summary()

    def _story_recompose(self):
        st = self.story_cur
        if st:
            self._story_commit_all()
            self.story_gen.recompose(st, force=True)
            self._story_refresh_summary()

    def _story_copy(self):
        if self.story_cur:
            self._story_commit_all()
            self.clipboard_clear(); self.clipboard_append(self.story_cur.plain())
            self.last_roll.set("Copied the story to the clipboard.")

    def _story_add_to_notebook(self, update=False):
        st = self.story_cur
        if not st:
            messagebox.showinfo("Nothing to save", "Generate a story first."); return
        if update and not (self.story_page_id and self._page(self.story_page_id)):
            messagebox.showinfo("No page to update", "This story didn't come from a Notebook page. Use Add to Notebook."); return
        self._story_commit_all()
        ptype = self.story_save_type.var.get() or st.page_type
        page, new_pages = nbk.story_to_pages(st, self.notebook, ptype, self.story_make_pages.get(),
                                             self.story_page_id if update else None)
        if not any(p is page for p in self.notebook):
            self.notebook.append(page)
        self.notebook.extend(new_pages)
        self.story_page_id = page["id"]
        self._save_notebook(); self._refresh_notebook(select=page["id"])
        extra = f" and {len(new_pages)} new page{'s' if len(new_pages) != 1 else ''}" if new_pages else ""
        self.last_roll.set(f"{'Updated' if update else 'Added'} '{page['title']}' in the Notebook{extra}.")

    def _story_apply_rep(self, entry):
        """Apply a suggested favor or disservice to the faction's standing."""
        page = nbk.find(self.notebook, entry["faction"])
        if page is None or page.get("type") != "Faction":
            if page is not None or not messagebox.askyesno(
                    "New faction", f"'{entry['faction']}' has no faction page yet. Create one?"):
                return
            page = nbk.new_faction(entry["faction"])
            self.notebook.append(page)
        rp = nbk.ensure_rep(page)
        ch = reputation.apply(rp, entry["kind"], entry["size"], note=(self.story_cur.title if self.story_cur else ""),
                              source="story")
        self._save_notebook()
        self.last_roll.set(f"{entry['faction']}: {ch.message}. Standing is now {ch.tier_after} ({ch.after:+d})."
                           if not ch.blocked else f"{entry['faction']}: {ch.message}")

    def _story_make_encounter(self):
        st = self.story_cur
        if not st or not st.encounter:
            return
        enc = st.encounter
        if enc.get("threat") in THREATS:
            self.threat.set(enc["threat"])
        self.enc_inc.set(enc.get("traits", []))
        self.pl_var.set(self._int_or_none(str(self.story_lvl.get())) or self.party_level())
        self.nb.select(self.tab_enc)
        self._gen_enc()
        if not self.encs:                                     # no creature matched the traits: widen the search
            self.enc_inc.set("")
            self._gen_enc()
            self.enc_info.set(self.enc_info.get() + "   (Story Forge's creature traits matched nothing, so they were dropped.)")

    def _story_open_tables(self):
        w = getattr(self, "story_tables_win", None)
        try:
            alive = w is not None and w.winfo_exists()
        except Exception:
            alive = False
        if alive:
            w.deiconify(); w.lift()
        else:
            self.story_tables_win = StoryTablesWindow(self)

    def _story_from_page(self, page, kind):
        """Build a story around a Notebook page: the faction or NPC it's about, the place, or the event."""
        if not page:
            messagebox.showinfo("Select a page", "Select a Notebook page first."); return
        typ, title = page.get("type"), page["title"]
        base = set(infer_page_tags(page))
        if typ in ("NPC", "PC"):
            slot, text, tags, ent = "who", sg.inline_name(title), base | {"k:npc"}, {"type": "NPC", "title": title, "campaign": True}
        elif typ == "Faction":
            slot, text, tags, ent = "who", sg.inline_name(title), base | {"k:faction"}, {"type": "Faction", "title": title, "campaign": True}
        elif typ == "Location":
            slot, text, tags, ent = "where", f"at {sg.inline_name(title)}", base, {"type": "Location", "title": title, "campaign": True}
        elif typ == "Event":
            slot, text, tags, ent = "when", f"during {sg.inline_name(title)}", base, {"type": "Event", "title": title, "campaign": True}
        else:
            messagebox.showinfo("Story ideas", "Story ideas work from NPC, PC, Faction, Location, and Event pages."); return
        if "gm-only" in [t.lower() for t in page.get("tags", [])]:
            if not messagebox.askyesno("GM-only page", f"'{title}' is a GM ONLY page. A story built around it will name it, "
                                       "and stories are easy to share with players. Build it anyway?"):
                return
        tags = tags | {"avoid:" + a for a in (page.get("avoid") or []) if isinstance(a, str)}
        presets = {slot: {"text": text, "tags": sorted(tags), "entities": [ent]}}
        self.nb.select(self.tab_story)
        titles = {k: t for t, k in self._story_kind_titles().items()}
        self.story_kind.var.set(titles.get(kind, self.story_kind.var.get()))
        self._story_generate(presets=presets, kind=kind)

    def _story_load_page(self, page):
        """Reopen a saved story page in Story Forge so its lines can be edited, locked, and rerolled."""
        if not page or not page.get("story"):
            messagebox.showinfo("Story Forge", "That page wasn't made by Story Forge."); return
        try:
            st = sg.Story.from_dict(page["story"])
        except Exception:
            messagebox.showinfo("Story Forge", "That page's story data couldn't be read."); return
        self.nb.select(self.tab_story)
        self.story_list = [st]
        self.story_page_id = page["id"]
        self._story_refresh_list(select=0)

    def _hallowmead_summary(self, plan):
        parts = [f"{n} {t.lower()}{'s' if n != 1 else ''}" for t, n in sorted(plan["by_type"].items())]
        return ", ".join(parts) if parts else "nothing new"

    def _hallowmead_dialog(self, offered=False):
        """Load the Hallowmead and Underhallow setting: factions, leaders, places, proposed events, the ancestry mix,
        and the story content. Pages you edited and pages of your own are never changed."""
        plan = hallowmead.plan(self.notebook, self._ancestry_weights())
        if not plan["new_pages"] and not plan["updates"] and not plan["set_demographics"]:
            note = (f" {len(plan['edited'])} page{'s' if len(plan['edited']) != 1 else ''} from the first import "
                    "have your edits, so they were left alone." if plan["edited"] else "")
            messagebox.showinfo("Hallowmead", "Every Hallowmead page is already in your Notebook and up to date, and your "
                                "ancestry mix is set. Nothing to add." + note)
            if offered:
                self.config_data["hallowmead_offered"] = True
                storage.save("config", self.config_data)
            return
        bits = []
        if plan["new_pages"]:
            bits.append(f"add {self._hallowmead_summary(plan)}")
        if plan["updates"]:
            bits.append(f"bring {len(plan['updates'])} page{'s' if len(plan['updates']) != 1 else ''} from the first import "
                        "up to date with the setting bible (their reputation, status, and links are kept, and their text "
                        "is replaced)")
        if plan["set_demographics"]:
            bits.append("set the ancestry mix for the Underhallow")
        text = ("This will " + "; ".join(bits) + "."
                + (f" {len(plan['edited'])} page{'s' if len(plan['edited']) != 1 else ''} you edited will be left alone."
                   if plan["edited"] else "")
                + "\n\nEvery page names the setting bible section it came from, or says it was proposed in our chats and "
                  "is not canon. GM ONLY pages are never used in generated stories.\n\nContinue?")
        if not messagebox.askyesno("Load Hallowmead setting", text):
            if offered:
                self.config_data["hallowmead_offered"] = True
                storage.save("config", self.config_data)
            return
        replace = False
        if plan["differs"] and self._ancestry_weights():
            replace = messagebox.askyesno("Ancestry mix", "You already have an ancestry mix. Replace it with the "
                                          "Hallowmead mix? Choose No to keep yours.")
        report = hallowmead.apply(self.notebook, self.config_data, replace)
        storage.save("config", self.config_data)
        if hasattr(self, "story_pack_vars"):
            self.story_pack_vars["hallowmead"].set(True)
        self._save_notebook(); self._refresh_notebook()
        demo = {"set": " The ancestry mix is set.", "replaced": " Your ancestry mix was replaced.",
                "kept": " Your ancestry mix was kept."}[report["demographics"]]
        done = []
        if report["added"]:
            done.append(f"Added {self._hallowmead_summary(plan)}")
        if report["updated"]:
            done.append(f"Updated {len(report['updated'])} page{'s' if len(report['updated']) != 1 else ''}")
        self.last_roll.set("Hallowmead: " + ", ".join(d.lower() for d in done) + "." + demo)
        messagebox.showinfo("Hallowmead loaded", ". ".join(done) + f".{demo}\n\nOpen the Factions tab to see the seven "
                            "Underhallow factions, and read the 'Hallowmead setting import notes' page in the Notebook.")

    def _offer_hallowmead(self):
        """One-time offer at first launch."""
        if self.config_data.get("hallowmead_offered") or any(p.get("seed") == hallowmead.SEED for p in self.notebook):
            return
        self.config_data["hallowmead_offered"] = True
        storage.save("config", self.config_data)
        self._hallowmead_dialog(offered=True)

    def _demographics_dialog(self):
        """Who lives in your world: relative weights for ancestries used by NPCs and stories."""
        win = tk.Toplevel(self); win.title("Setting demographics"); win.geometry("420x520"); win.transient(self)
        ttk.Label(win, wraplength=390, justify="left", foreground="#555", text=(
            "One ancestry per line as 'Name: weight'. Higher weight, more common. Type any ancestry, including your own. "
            "Your mix is used exactly as written, whatever setting you pick. Leave this empty to use the built-in mix, "
            "which leans toward the setting (underground favors dwarves, goblins, and kobolds).")).pack(anchor="w", padx=8, pady=6)
        box = tk.Text(win, height=22, width=44); box.pack(padx=8)
        cur = self._ancestry_weights() or {a: nmod.BASE_WEIGHTS.get(a, nmod.DEFAULT_WEIGHT) for a in nmod.ANCESTRIES[:20]}
        box.insert("1.0", "\n".join(f"{a}: {w:g}" for a, w in cur.items()))
        msg = tk.StringVar(); ttk.Label(win, textvariable=msg, foreground="#a33").pack()

        def parse():
            out = {}
            for line in box.get("1.0", "end").splitlines():
                if ":" not in line:
                    continue
                name, _, w = line.rpartition(":")
                try:
                    wv = float(w)
                except ValueError:
                    msg.set(f"'{line.strip()}' needs a number after the colon."); return None
                if name.strip() and wv > 0:
                    out[name.strip()] = wv
            return out

        def save():
            w = parse()
            if w is None:
                return
            self.config_data["ancestry_weights"] = w
            storage.save("config", self.config_data)
            win.destroy()
            self.last_roll.set(f"Saved demographics for {len(w)} ancestries." if w else "Using the built-in ancestry mix.")

        def clear():
            box.delete("1.0", "end")
        bar = ttk.Frame(win); bar.pack(fill="x", padx=8, pady=8)
        ttk.Button(bar, text="Use Built-in Mix", command=clear).pack(side="left")
        ttk.Button(bar, text="Save", command=save).pack(side="right")

    # ---------- Factions ----------
    def _build_factions(self):
        f = self.tab_factions
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.fac_tree = ttk.Treeview(left, columns=("tier", "pts"), show="tree headings", height=20)
        self.fac_tree.heading("#0", text="Faction"); self.fac_tree.column("#0", width=210)
        self.fac_tree.heading("tier", text="Standing"); self.fac_tree.column("tier", width=80)
        self.fac_tree.heading("pts", text="Pts"); self.fac_tree.column("pts", width=40, anchor="center")
        for name, color in TIER_COLORS.items():
            self.fac_tree.tag_configure(name, foreground=color)
        self.fac_tree.pack(fill="both", expand=True)
        self.fac_tree.bind("<<TreeviewSelect>>", lambda e: self._fac_pick())
        bb = ttk.Frame(left); bb.pack(fill="x", pady=3)
        for i, (text, cmd) in enumerate((("New Faction...", self._fac_new), ("Random Faction", self._fac_random),
                                         ("Open Page", self._fac_open_page), ("Delete", self._fac_delete))):
            ttk.Button(bb, text=text, command=cmd).grid(row=i // 2, column=i % 2, sticky="we", padx=1, pady=1)
        bb.columnconfigure(0, weight=1); bb.columnconfigure(1, weight=1)
        ttk.Label(left, foreground="#666", wraplength=270, justify="left", text=(
            "Standing follows the Reputation subsystem: favors and disservices of three sizes move a score from -50 to "
            "50, and some tiers ignore small ones. The party starts at Ignored.")).pack(anchor="w", pady=4)

        right = ttk.Frame(pane); pane.add(right, weight=4)
        hd = ttk.Frame(right); hd.pack(fill="x")
        self.fac_name = tk.StringVar(value="Pick a faction on the left, or create one.")
        ttk.Label(hd, textvariable=self.fac_name, font=("TkDefaultFont", 14, "bold")).pack(side="left")
        self.fac_stand = tk.StringVar()
        ttk.Label(hd, textvariable=self.fac_stand, font=("TkDefaultFont", 14, "bold")).pack(side="right")
        self.fac_bar = ReputationBar(right); self.fac_bar.pack(anchor="w", pady=4)
        self.fac_desc = tk.StringVar()
        ttk.Label(right, textvariable=self.fac_desc, wraplength=760, justify="left").pack(anchor="w")
        self.fac_rule = tk.StringVar()
        ttk.Label(right, textvariable=self.fac_rule, foreground="#555", wraplength=760, justify="left").pack(anchor="w")

        act = ttk.LabelFrame(right, text="Record what the party did")
        act.pack(fill="x", pady=6)
        self.fac_size = tk.StringVar(value="moderate")
        r0 = ttk.Frame(act); r0.pack(fill="x", padx=6, pady=3)
        ttk.Label(r0, text="Size").pack(side="left")
        for size, pts in (("minor", "1"), ("moderate", "2"), ("major", "5")):
            ttk.Radiobutton(r0, text=f"{size} ({pts})", value=size, variable=self.fac_size).pack(side="left", padx=6)
        self.fac_egregious = tk.BooleanVar()
        ttk.Checkbutton(r0, text="Egregious (major disservice: lose all points, then 5 more)", variable=self.fac_egregious).pack(side="left", padx=10)
        r1 = ttk.Frame(act); r1.pack(fill="x", padx=6, pady=3)
        ttk.Label(r1, text="What happened").pack(side="left")
        self.fac_note = tk.StringVar()
        ttk.Entry(r1, textvariable=self.fac_note, width=48).pack(side="left", padx=4)
        ttk.Label(r1, text="Points (optional)").pack(side="left", padx=(8, 2))
        self.fac_amount = tk.StringVar()
        ttk.Entry(r1, textvariable=self.fac_amount, width=5).pack(side="left")
        r2 = ttk.Frame(act); r2.pack(fill="x", padx=6, pady=4)
        ttk.Button(r2, text="Favor  +", command=lambda: self._fac_apply("favor")).pack(side="left", padx=2)
        ttk.Button(r2, text="Disservice  -", command=lambda: self._fac_apply("disservice")).pack(side="left", padx=2)
        ttk.Button(r2, text="Undo Last", command=self._fac_undo).pack(side="left", padx=(14, 2))
        ttk.Button(r2, text="Set Points...", command=self._fac_set).pack(side="left", padx=2)
        ttk.Button(r2, text="Suggest an Idea", command=self._fac_idea).pack(side="left", padx=(14, 2))
        self.fac_result = tk.StringVar()
        ttk.Label(act, textvariable=self.fac_result, foreground="#1a5fb4", wraplength=760, justify="left").pack(anchor="w", padx=6, pady=(0, 4))

        st = ttk.LabelFrame(right, text="Story ideas from this faction")
        st.pack(fill="x", pady=2)
        for text, kind in (("A Rumor About Them", "rumor"), ("A Hook From Them", "hook"), ("Their Next Move", "faction_move"),
                           ("A Complication They Cause", "complication")):
            ttk.Button(st, text=text, command=lambda k=kind: self._fac_story(k)).pack(side="left", padx=4, pady=4)

        low = ttk.PanedWindow(right, orient="horizontal"); low.pack(fill="both", expand=True, pady=4)
        lf = ttk.Frame(low); low.add(lf, weight=1)
        self.fac_tier_lbl = tk.StringVar()
        ttk.Label(lf, textvariable=self.fac_tier_lbl, font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.fac_tier_note = tk.Text(lf, height=3, wrap="word"); self.fac_tier_note.pack(fill="x")
        ttk.Label(lf, text="Goals (one per line)", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.fac_goals = tk.Text(lf, height=4, wrap="word"); self.fac_goals.pack(fill="x")
        ttk.Label(lf, text="Rivals (comma separated)", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.fac_rivals = tk.StringVar(); ttk.Entry(lf, textvariable=self.fac_rivals).pack(fill="x")
        ttk.Button(lf, text="Save Notes, Goals, and Rivals", command=self._fac_save_details).pack(anchor="e", pady=4)
        rf = ttk.Frame(low); low.add(rf, weight=1)
        ttk.Label(rf, text="History", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.fac_log = ttk.Treeview(rf, columns=("what", "chg", "now"), show="tree headings", height=8)
        self.fac_log.heading("#0", text="Date"); self.fac_log.column("#0", width=80)
        for c, t, w in (("what", "What", 200), ("chg", "Change", 60), ("now", "Standing", 90)):
            self.fac_log.heading(c, text=t); self.fac_log.column(c, width=w)
        self.fac_log.pack(fill="both", expand=True)
        self.fac_current = None
        self._fac_refresh()

    def _fac_page(self):
        p = self.fac_current
        return p if p is not None and any(x is p for x in self.notebook) else None

    def _fac_refresh(self, select=None):
        if not hasattr(self, "fac_tree"):
            return
        sel = select or (self.fac_current["id"] if self.fac_current else None)
        self.fac_tree.delete(*self.fac_tree.get_children())
        pages = sorted(nbk.faction_pages(self.notebook), key=lambda p: (-nbk.ensure_rep(p)["points"], p["title"].lower()))
        for p in pages:
            pts = nbk.ensure_rep(p)["points"]
            t = reputation.tier(pts)
            self.fac_tree.insert("", "end", iid=p["id"], text=p["title"], values=(t, f"{pts:+d}" if pts else "0"), tags=(t,))
        if sel and self.fac_tree.exists(sel):
            self.fac_tree.selection_set(sel)
            self.fac_current = self._page(sel)          # don't wait for the selection event to update the header
        elif not pages:
            self.fac_current = None
        self._fac_show()

    def _fac_pick(self):
        sel = self.fac_tree.selection()
        self.fac_current = self._page(sel[0]) if sel else None
        self.fac_result.set("")
        self._fac_show()

    def _fac_show(self):
        p = self._fac_page()
        for t in (self.fac_tier_note, self.fac_goals):
            t.delete("1.0", "end")
        self.fac_rivals.set("")
        self.fac_log.delete(*self.fac_log.get_children())
        if p is None:
            self.fac_name.set("Pick a faction on the left, or create one.")
            self.fac_stand.set(""); self.fac_desc.set(""); self.fac_rule.set(""); self.fac_tier_lbl.set("")
            self.fac_bar.set(0)
            return
        rp = nbk.ensure_rep(p)
        pts, t = rp["points"], reputation.tier(rp["points"])
        self.fac_name.set(p["title"])
        self.fac_stand.set(f"{t} ({pts:+d})" if pts else f"{t} (0)")
        self.fac_bar.set(pts)
        up, down = reputation.points_to_next(pts)
        self.fac_desc.set(reputation.DESCRIPTION[t])
        self.fac_rule.set(reputation.rule_text(t) + "   "
                          + (f"{up} more point{'s' if up != 1 else ''} to the next tier up. " if up is not None else "")
                          + (f"{down} to fall to the next tier down." if down is not None else ""))
        self.fac_tier_lbl.set(f"What {t} means here")
        self.fac_tier_note.insert("1.0", reputation.tier_note(rp, t))
        self.fac_goals.insert("1.0", "\n".join(p.get("goals") or []))
        self.fac_rivals.set(", ".join(p.get("rivals") or []))
        for i, e in enumerate(reversed(rp["log"])):
            what = "set by hand" if e.get("kind") == "set" else f"{e.get('size', '')} {e.get('kind', '')}".strip()
            if e.get("note"):
                what += f": {e['note']}"
            chg = "none" if e.get("blocked") else f"{e.get('delta', 0):+d}"
            self.fac_log.insert("", "end", iid=str(i), text=e.get("date", ""),
                                values=(what, chg, f"{e.get('tier', '')} ({e.get('after', 0):+d})"))

    def _fac_apply(self, kind):
        p = self._fac_page()
        if p is None:
            messagebox.showinfo("Select a faction", "Select a faction first."); return
        amt = self._int_or_none(self.fac_amount.get())
        try:
            ch = reputation.apply(nbk.ensure_rep(p), kind, self.fac_size.get(), note=self.fac_note.get().strip(),
                                  amount=amt, egregious=bool(self.fac_egregious.get()) and kind == "disservice")
        except ValueError as e:
            self.fac_result.set(str(e)); return
        msg = ch.message + (f". Standing is now {ch.tier_after} ({ch.after:+d})." if not ch.blocked else "")
        if ch.tier_changed:
            msg += f"   Tier change: {ch.tier_before} to {ch.tier_after}."
        if ch.blocked:
            msg += "   (Use Set Points if your table rules otherwise.)"
        self.fac_result.set(msg)
        self.fac_note.set(""); self.fac_amount.set(""); self.fac_egregious.set(False)
        self._save_notebook(); self._fac_refresh()
        self.last_roll.set(f"{p['title']}: {ch.message}.")

    def _fac_undo(self):
        p = self._fac_page()
        if p is not None:
            e = reputation.undo_last(nbk.ensure_rep(p))
            self.fac_result.set("Nothing to undo." if e is None else "Undid the last change.")
            self._save_notebook(); self._fac_refresh()

    def _fac_set(self):
        p = self._fac_page()
        if p is None:
            return
        rp = nbk.ensure_rep(p)
        n = self._ask_int("Set points", "Reputation Points (-50 to 50)", rp["points"])
        if n is not None:
            reputation.set_points(rp, n, note=self.fac_note.get().strip() or "Set by hand")
            self.fac_note.set("")
            self._save_notebook(); self._fac_refresh()

    def _fac_idea(self):
        size = self.fac_size.get()
        favor = sg.roll_table(f"rep.favor.{size}", registry=self.story_registry)
        harm = sg.roll_table(f"rep.disservice.{size}", registry=self.story_registry)
        self.fac_result.set(f"A {size} favor might be to {favor}. A {size} disservice might be to {harm}.")

    def _fac_save_details(self):
        p = self._fac_page()
        if p is None:
            return
        rp = nbk.ensure_rep(p)
        t = reputation.tier(rp["points"])
        note = self.fac_tier_note.get("1.0", "end").strip()
        if note:
            rp["notes"][t] = note
        else:
            rp["notes"].pop(t, None)
        p["goals"] = [ln.strip() for ln in self.fac_goals.get("1.0", "end").splitlines() if ln.strip()]
        p["rivals"] = _split(self.fac_rivals.get())
        self._save_notebook(); self._fac_refresh()
        self.fac_result.set("Saved.")

    def _fac_new(self):
        win = tk.Toplevel(self); win.title("New faction"); win.transient(self)
        name, kind = tk.StringVar(), tk.StringVar()
        for r, (lab, v, w) in enumerate((("Name", name, 30), ("Kind (guild, cult, noble house...)", kind, 30))):
            ttk.Label(win, text=lab).grid(row=r, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(win, textvariable=v, width=w).grid(row=r, column=1, padx=8)

        def ok():
            if not name.get().strip():
                return
            p = nbk.new_faction(nbk.unique_title(self.notebook, name.get().strip()), kind=kind.get().strip())
            self.notebook.append(p)
            win.destroy()
            self._save_notebook(); self._refresh_notebook(); self._fac_refresh(select=p["id"])
        ttk.Button(win, text="Create", command=ok).grid(row=2, column=1, sticky="e", padx=8, pady=8)

    def _fac_random(self):
        reg = self.story_registry
        nm_ = re.sub(r"^the\s+", "", sg.roll_table("faction.name", registry=reg).strip(), flags=re.I)
        nm_ = nm_[:1].upper() + nm_[1:]
        kind = sg.roll_table("faction.kind", registry=reg)
        p = nbk.new_faction(nbk.unique_title(self.notebook, nm_), kind=kind)
        self.notebook.append(p)
        self._save_notebook(); self._refresh_notebook(); self._fac_refresh(select=p["id"])
        self.fac_result.set(f"Created {p['title']} ({sg.article(kind)} {kind}).")

    def _fac_open_page(self):
        p = self._fac_page()
        if p is not None:
            self._open_page(p["id"])

    def _fac_delete(self):
        p = self._fac_page()
        if p is not None and messagebox.askyesno("Delete faction", f"Delete '{p['title']}' and its reputation history?"):
            self.notebook = [x for x in self.notebook if x is not p]
            self.fac_current = None
            self._save_notebook(); self._refresh_notebook(); self._fac_refresh()

    def _fac_story(self, kind):
        self._story_from_page(self._fac_page(), kind)

    def _notebook_changed(self):
        """Called whenever the Notebook is saved: keep the Factions list, NPC faction menu, and Story info current."""
        if hasattr(self, "fac_tree"):
            self._fac_refresh()
        if hasattr(self, "ng_faction"):
            names = ["(none)"] + sorted(p["title"] for p in nbk.faction_pages(self.notebook))
            self.ng_faction.set_values(names)
            if self.ng_faction.var.get() not in names:
                self.ng_faction.var.set("(none)")
        self._magic_refresh_tie()
        self._inn_refresh_tie()
        self._dt_refresh_places()
        self._story_refresh_info()
        self._gm_refresh_choices()

    # ---------- GM Tools ----------
    def _build_gmtools(self):
        sub = TabbedPane(self.tab_gm, level=2); sub.pack(fill="both", expand=True, padx=4, pady=4)
        a = ttk.Frame(sub); sub.add(a, text="Secret Checks")
        b = ttk.Frame(sub); sub.add(b, text="NPC Generator")
        c = ttk.Frame(sub); sub.add(c, text="Downtime")
        self._build_secret(a)
        self._build_npcgen(b)
        self._build_downtime(c)
        self._build_generators(sub)

    # --- the generators on this tab: job board, salvage and wares, afflictions, hazards, influence, quest builder, recap ---
    def _build_generators(self, sub):
        """One sub-tab per generator in gmtools.specs(). Each is a ToolPanel, which asks this App for the hooks below."""
        gmtools.configure(self.story_registry, self._ancestry_weights)
        self.gm_panels = {}
        for spec in gmtools.specs():
            panel = ToolPanel(sub, self, spec)
            sub.add(panel, text=spec["label"])
            self.gm_panels[spec["key"]] = panel

    def _gm_refresh_choices(self):
        """The Notebook changed: refill the place and faction dropdowns."""
        for panel in getattr(self, "gm_panels", {}).values():
            panel.refresh_choices()

    def _gm_sync_party(self):
        for panel in getattr(self, "gm_panels", {}).values():
            panel.sync_party()

    def gm_pages(self):
        return self.notebook

    def gm_prefs(self, tool):
        return (self.config_data.get("gm_tools") or {}).get(tool, {})

    def gm_remember(self, tool, prefs):
        self.config_data.setdefault("gm_tools", {})[tool] = prefs
        storage.save("config", self.config_data)

    def open_story_tables(self):
        self._story_open_tables()

    def gm_add_page(self, title, page_type, body, tags):
        """Add a generator's result to the Notebook as a new page (never overwriting a page with the same title)."""
        ptype = page_type if page_type in nbk.PAGE_TYPES else "Note"
        page = nbk.new_page(nbk.unique_title(self.notebook, title), ptype, body, status="", tags=list(tags))
        self.notebook.append(page)
        self._save_notebook(); self._refresh_notebook(select=page["id"])
        self.last_roll.set(f"Added '{page['title']}' to the Notebook as a {ptype} page.")

    def gm_session_source(self):
        """Lines for the Session Recap's 'Add the app's combat log and today's treasure' box: the fight that is on the Combat tab
        and what was awarded to the treasure ledger today. Plain lines are events the players know; [loot] lines are loot."""
        lines = []
        cs = self.combat
        foes = [c for c in cs.combatants if c.kind != "pc"]
        if foes and cs.round:
            counts = Counter(c.name for c in foes)
            names = [n if k == 1 else f"{k} x {n}" for n, k in counts.items()]
            down = sorted(c.name for c in foes if c.defeated)
            line = f"The party fought {', '.join(names)} over {cs.round} round{'s' if cs.round != 1 else ''}"
            if down:
                line += f", and {', '.join(down)} {'was' if len(down) == 1 else 'were'} defeated"
            lines.append(line)
        today = datetime.date.today().isoformat()
        for e in self.ledger:
            if e.get("date") != today:
                continue
            if e.get("kind") == "currency" or e.get("name") == "Currency":
                lines.append(f"[loot] {float(e.get('value_gp', 0)):g} gp in coin")
            else:
                lines.append(f"[loot] {e.get('name', 'an item')}")
        return "\n".join(lines)

    # --- secret checks ---
    SECRET_CHECKS = ["Perception", "Fortitude", "Reflex", "Will"] + [s.title() for s in pb.SKILLS] + ["Lore (...)"]

    def _build_secret(self, f):
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Check").grid(row=0, column=0, sticky="w")
        self.sc_check = Combo(top, self.SECRET_CHECKS, width=22); self.sc_check.var.set("Perception")
        self.sc_check.grid(row=0, column=1, sticky="w")
        ttk.Label(top, text="(type any Lore, e.g. Lore (Underhallow))", foreground="#777").grid(row=0, column=2, columnspan=3, sticky="w")
        ttk.Label(top, text="DC").grid(row=1, column=0, sticky="w")
        self.sc_dc = tk.StringVar(); ttk.Entry(top, textvariable=self.sc_dc, width=6).grid(row=1, column=1, sticky="w")
        ttk.Label(top, text="or level").grid(row=1, column=2, sticky="e")
        self.sc_lvl = tk.StringVar(value=str(self.party_level()))
        ttk.Spinbox(top, from_=-1, to=25, textvariable=self.sc_lvl, width=5).grid(row=1, column=3, sticky="w")
        self.sc_rar = Combo(top, ["common", "uncommon", "rare", "unique"], readonly=True, width=10)
        self.sc_rar.var.set("common"); self.sc_rar.grid(row=1, column=4, sticky="w", padx=4)
        ttk.Button(top, text="Use Level DC", command=lambda: self.sc_dc.set(
            str(dt.level_dc(self._int_or_none(self.sc_lvl.get()) or 0, self.sc_rar.var.get())))).grid(row=1, column=5)
        ttk.Label(top, text="Extra modifier").grid(row=2, column=0, sticky="w")
        self.sc_extra = tk.StringVar(value="0"); ttk.Entry(top, textvariable=self.sc_extra, width=6).grid(row=2, column=1, sticky="w")
        ttk.Label(top, text="(circumstance bonus, item bonus, etc.)", foreground="#777").grid(row=2, column=2, columnspan=4, sticky="w")
        self.sc_pcs_frame = ttk.LabelFrame(f, text="Roll for"); self.sc_pcs_frame.pack(fill="x", padx=8)
        self.sc_pc_vars = {}
        bb = ttk.Frame(f); bb.pack(fill="x", padx=8, pady=4)
        ttk.Button(bb, text="Roll Secretly", command=self._secret_roll).pack(side="left")
        ttk.Button(bb, text="Clear", command=lambda: (self.sc_out.configure(state="normal"),
                                                      self.sc_out.delete("1.0", "end"),
                                                      self.sc_out.configure(state="disabled"))).pack(side="left", padx=4)
        ttk.Label(bb, text="Results stay here: they don't go to the Dice window, status bar, or combat log.",
                  foreground="#777").pack(side="left", padx=8)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        self.sc_out = tk.Text(pane, height=12, wrap="word", state="disabled", font=("TkFixedFont", 10))
        self.sc_out.tag_configure("head", font=("TkDefaultFont", 10, "bold"))
        self.sc_out.tag_configure("good", foreground="#1e7a34"); self.sc_out.tag_configure("bad", foreground="#9a1e1e")
        pane.add(self.sc_out, weight=3)
        dfr = ttk.LabelFrame(pane, text="Party defenses (DCs for monsters acting against PCs)"); pane.add(dfr, weight=2)
        cols = ("ac", "per", "fort", "ref", "will", "cls")
        self.sc_def = ttk.Treeview(dfr, columns=cols, show="tree headings", height=8)
        self.sc_def.heading("#0", text="PC"); self.sc_def.column("#0", width=120)
        for col, t in zip(cols, ("AC", "Perception DC", "Fort DC", "Ref DC", "Will DC", "Class DC")):
            self.sc_def.heading(col, text=t); self.sc_def.column(col, width=70, anchor="center")
        self.sc_def.pack(fill="both", expand=True)
        self._refresh_secret_party()

    def _refresh_secret_party(self):
        if not hasattr(self, "sc_pcs_frame"):
            return
        for w in self.sc_pcs_frame.winfo_children():
            w.destroy()
        old = {k: v.get() for k, v in self.sc_pc_vars.items()}
        self.sc_pc_vars = {}
        for i, pc in enumerate(sorted(self.party, key=lambda x: x["name"])):
            v = tk.BooleanVar(value=old.get(pc["name"], True))
            ttk.Checkbutton(self.sc_pcs_frame, text=pc["name"], variable=v).grid(row=i // 6, column=i % 6, sticky="w", padx=4)
            self.sc_pc_vars[pc["name"]] = v
        if not self.party:
            ttk.Label(self.sc_pcs_frame, text="Add PCs on Party & Data (or import them in the Notebook).").grid(row=0, column=0)
        self.sc_def.delete(*self.sc_def.get_children())
        for pc in sorted(self.party, key=lambda x: x["name"]):
            sv = pc.get("saves") or {}

            def dc(v):
                return "" if v is None else 10 + v
            self.sc_def.insert("", "end", text=pc["name"],
                               values=(pc.get("ac", ""), dc(pc.get("perception")), dc(sv.get("fortitude")),
                                       dc(sv.get("reflex")), dc(sv.get("will")), pc.get("class_dc", "")))

    @staticmethod
    def _pc_mod(pc, check):
        """(modifier, note) for a PC check, or (None, reason)."""
        c = check.strip()
        lc = c.lower()
        if lc == "perception":
            return pc.get("perception"), ""
        if lc in ("fortitude", "reflex", "will"):
            return (pc.get("saves") or {}).get(lc), ""
        skills = {k.lower(): v for k, v in (pc.get("skills") or {}).items()}
        if lc in skills:
            return skills[lc], ""
        if lc.startswith("lore"):
            intm = (pc.get("mods") or {}).get("int")
            return (intm, "untrained Lore") if intm is not None else (None, "no Int on record")
        return None, "no data (import from Pathbuilder for skills)"

    def _secret_roll(self):
        check = self.sc_check.var.get().strip()
        dc = self._int_or_none(self.sc_dc.get())
        extra = self._int_or_none(self.sc_extra.get()) or 0
        rng = random.Random()
        lines = [(f"{check}" + (f" vs DC {dc}" if dc is not None else "") + f"  ({datetime.datetime.now():%H:%M})\n", "head")]
        for pc in sorted(self.party, key=lambda x: x["name"]):
            if not self.sc_pc_vars.get(pc["name"], tk.BooleanVar(value=True)).get():
                continue
            mod, note = self._pc_mod(pc, check)
            if mod is None:
                lines.append((f"  {pc['name']:<16} {note}\n", "bad")); continue
            nat = rng.randint(1, 20)
            total = nat + mod + extra
            res = dt.degree(total, dc, nat) if dc is not None else ""
            tag = "good" if res.startswith(("Success", "Critical success")) else "bad" if res else None
            lines.append((f"  {pc['name']:<16} d20 {nat:>2} {mod:+d}" + (f" {extra:+d}" if extra else "")
                          + f" = {total:>2}" + (f"  {res}" if res else "") + (" (nat 20)" if nat == 20 else
                                                                              " (nat 1)" if nat == 1 else "")
                          + (f"  [{note}]" if note else "") + "\n", tag))
        t = self.sc_out
        t.configure(state="normal")
        t.insert("1.0", "\n")
        for text, tag in reversed(lines):
            t.insert("1.0", text, tag)
        t.configure(state="disabled")

    # --- NPC generator ---
    NPC_TONES = ["any", "grim", "light", "weird"]

    def _build_npcgen(self, f):
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Ancestry").grid(row=0, column=0, sticky="w")
        self.ng_anc = Combo(top, npcgen.DEFAULT_ANCESTRIES, values_key="ancestries", width=20)
        self.ng_anc.var.set("Human"); self.ng_anc.grid(row=0, column=1, sticky="w")
        ttk.Button(top, text="Random", width=8, command=self._ng_random_ancestry).grid(row=0, column=2, padx=4)
        ttk.Label(top, text="Role").grid(row=0, column=3, sticky="w", padx=(10, 2))
        self.ng_role = Combo(top, list(npcgen.ROLES), readonly=True, width=20)
        self.ng_role.var.set("Guard"); self.ng_role.grid(row=0, column=4, sticky="w")
        ttk.Label(top, text="Level").grid(row=0, column=5, sticky="w", padx=(10, 2))
        self.ng_lvl = tk.StringVar(value=str(self.party_level()))
        ttk.Spinbox(top, from_=-1, to=24, textvariable=self.ng_lvl, width=5).grid(row=0, column=6, sticky="w")
        ttk.Label(top, text="Name").grid(row=1, column=0, sticky="w", pady=3)
        self.ng_name = tk.StringVar(); ttk.Entry(top, textvariable=self.ng_name, width=30).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Label(top, text="Faction").grid(row=1, column=3, sticky="w", padx=(10, 2))
        self.ng_faction = Combo(top, ["(none)"], readonly=True, width=20)
        self.ng_faction.var.set("(none)"); self.ng_faction.grid(row=1, column=4, sticky="w")
        ttk.Label(top, text="Tone").grid(row=1, column=5, sticky="w", padx=(10, 2))
        self.ng_tone = Combo(top, self.NPC_TONES, readonly=True, width=8)
        self.ng_tone.var.set("any"); self.ng_tone.grid(row=1, column=6, sticky="w")
        ttk.Label(top, text="Setting").grid(row=2, column=0, sticky="w")
        self.ng_env = Combo(top, self.STORY_ENVS, readonly=True, width=14)
        self.ng_env.var.set("any"); self.ng_env.grid(row=2, column=1, sticky="w")
        ttk.Label(top, text="Details").grid(row=2, column=3, sticky="w", padx=(10, 2))
        self.ng_extras = tk.StringVar()
        ttk.Spinbox(top, from_=0, to=13, textvariable=self.ng_extras, width=5).grid(row=2, column=4, sticky="w")
        ttk.Label(top, text="blank = a random handful. A faction sets how its members feel about the party.",
                  foreground="#777").grid(row=2, column=5, columnspan=3, sticky="w", padx=6)
        ttk.Label(top, text="Equipment").grid(row=3, column=0, sticky="w", pady=3)
        self.ng_gear = Combo(top, npckit.GEAR_LABELS, readonly=True, width=14)
        self.ng_gear.var.set(self.config_data.get("npc_gear", "Standard")); self.ng_gear.grid(row=3, column=1, sticky="w")
        self.ng_save_items = tk.BooleanVar(value=self.config_data.get("npc_save_items", True))
        ttk.Checkbutton(top, text="Save its magic items to My Items", variable=self.ng_save_items).grid(
            row=3, column=3, columnspan=2, sticky="w", padx=(10, 2))
        ttk.Label(top, text="Armor, weapon, runes, magic items, spells, coins. None keeps the role's plain Strikes.",
                  foreground="#777").grid(row=3, column=5, columnspan=3, sticky="w", padx=6)
        ttk.Label(top, text="Style").grid(row=4, column=0, sticky="w", pady=3)
        self.ng_style = Combo(top, list(itemgen.STYLES.values()), readonly=True, width=14)
        self.ng_style.var.set(itemgen.STYLES.get(itemgen.style_key(self.config_data.get("npc_style")), "Standard"))
        self.ng_style.grid(row=4, column=1, sticky="w")
        ttk.Label(top, text="How odd its magic items and trappings are. Every NPC carries trappings: a little money, food, "
                            "tools for its work, a keepsake.", foreground="#777").grid(row=4, column=3, columnspan=5, sticky="w", padx=(10, 2))
        self.ng_kit = None
        bb = ttk.Frame(f); bb.pack(fill="x", padx=8)
        for text, cmd in (("Generate", self._ng_generate), ("New Name", self._ng_new_name),
                          ("New Personality", self._ng_new_personality), ("Reroll Selected Line", self._ng_reroll_line),
                          ("Reroll Gear", self._ng_reroll_gear), ("Gear Cards...", self._ng_show_cards),
                          ("Save to Custom Content", lambda: self._ng_save(True, False)),
                          ("Save to Notebook", lambda: self._ng_save(False, True)), ("Save to Both", lambda: self._ng_save(True, True)),
                          ("Send to Combat", self._ng_combat), ("Loot This NPC", self._ng_loot)):
            ttk.Button(bb, text=text, command=cmd).pack(side="left", padx=2, pady=2)
        tb = ttk.Frame(f); tb.pack(fill="x", padx=8)
        ttk.Button(tb, text="Apply Template...", command=self._ng_template).pack(side="left", padx=2, pady=2)
        ttk.Button(tb, text="Remove Templates", command=self._ng_remove_templates).pack(side="left", padx=2)
        self.ng_tpl_info = tk.StringVar()
        ttk.Label(tb, textvariable=self.ng_tpl_info, foreground="#777").pack(side="left", padx=8)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=6)
        left = ttk.Frame(pane); pane.add(left, weight=2)
        ttk.Label(left, text="Personality. Edit any line; Reroll Selected Line rerolls the line your cursor is on.",
                  foreground="#555", wraplength=380, justify="left").pack(anchor="w")
        self.ng_text = tk.Text(left, wrap="word", width=48, height=20, padx=6, pady=4, font=("TkDefaultFont", 10))
        self.ng_text.pack(fill="both", expand=True)
        self.ng_text.bind("<FocusOut>", lambda e: self._ng_show() if self.ng_current else None)
        self.ng_view = RichText(pane, self); pane.add(self.ng_view, weight=3)
        self.ng_view.show_message("Pick an ancestry (or press Random), a role, and a level, then Generate.")
        self.ng_current = None
        self.ng_base = None                     # the NPC before any template, so Reroll Gear and Remove Templates can redo them
        self._ng_set_tpl_info()

    def _ng_env_tags(self):
        env = self.ng_env.var.get()
        return () if env in ("", "any") else (env,)

    def _ng_faction_info(self):
        """(tier, page) of the chosen faction, or (None, None)."""
        name = self.ng_faction.var.get()
        page = nbk.find(self.notebook, name) if name and name != "(none)" else None
        if page is not None and page.get("type") == "Faction":
            return reputation.tier(nbk.ensure_rep(page)["points"]), page
        return None, None

    def _ng_random_ancestry(self):
        self.ng_anc.var.set(nmod.pick_ancestry(random.Random(), self._ng_env_tags(), self._ancestry_weights() or None))

    def _ng_ancestry(self):
        anc = self.ng_anc.var.get().strip()
        if not anc or anc.lower() in ("(random)", "random"):
            self._ng_random_ancestry()
            anc = self.ng_anc.var.get().strip()
        return anc

    def _ng_params(self):
        env = self.ng_env.var.get()
        tier, page = self._ng_faction_info()
        return dict(role=self.ng_role.var.get(), tone=self.ng_tone.var.get() or "any", env=None if env in ("", "any") else env,
                    faction_tier=tier)

    def _ng_style_packs(self):
        """The NPC Generator's Style, and the content packs its trappings may use (Hallowmead when it is loaded)."""
        style = itemgen.style_key(self.ng_style.var.get()) if hasattr(self, "ng_style") else "standard"
        self.config_data["npc_style"] = style
        hm = bool(self.config_data.get("hallowmead_pack", self.config_data.get("hallowmead_loaded")))
        return style, ["core"] + (["hallowmead"] if hm else [])

    def _ng_set_lines(self, fields):
        self.ng_text.delete("1.0", "end")
        self.ng_text.insert("1.0", "\n".join(f"{label}: {text}" for label, text in fields))

    def _ng_lines(self):
        out = []
        for line in self.ng_text.get("1.0", "end").splitlines():
            line = line.strip()
            if not line:
                continue
            label, sep, text = line.partition(":")
            out.append((label.strip(), text.strip()) if sep and len(label) <= 24 else ("Note", line))
        return out

    def _ng_creature(self):
        if not self.ng_current:
            return None
        c, p = self.ng_current
        c.name = self.ng_name.get().strip() or c.name
        c.notes = npcgen.notes_from({"fields": self._ng_lines()}, self.ng_anc.var.get().strip(), self.ng_role.var.get())
        tpl.with_note(c)                        # keeps the "Templates:" line on the end of the notes
        return c

    def _ng_show(self):
        c = self._ng_creature()
        if c is not None:
            self.ng_view.show(render(custom_details(c)))

    def _ng_generate(self):
        lvl = self._int_or_none(self.ng_lvl.get())
        if lvl is None:
            messagebox.showwarning("Level", "Enter a level from -1 to 24."); return
        anc = self._ng_ancestry()
        sysname = "sf" if self.sys_var.get() == "Starfinder" else "pf"
        extras = self._int_or_none(self.ng_extras.get())
        gear = self.ng_gear.var.get() or "None"
        self.config_data["npc_gear"] = gear
        style, packs = self._ng_style_packs()
        c, p = npcgen.generate(anc, self.ng_role.var.get(), lvl, system=sysname, extras=extras, name=None,
                               gear=gear, registry=self.story_registry, campaign=self._story_campaign(), style=style, packs=packs,
                               **{k: v for k, v in self._ng_params().items() if k not in ("role", "registry")})
        self.ng_current = (c, p)
        self.ng_base = None
        self._ng_set_tpl_info()
        self.ng_kit = p.get("kit")
        self.ng_name.set(c.name)
        self._ng_set_lines(p["fields"])
        self._ng_show()
        self._ng_kit_note()

    def _ng_kit_note(self):
        kit = self.ng_kit or {}
        skipped = [n for n in kit.get("notes", []) if "skipped" in n or "couldn't" in n]
        if skipped:
            self.last_roll.set("Equipment: " + "; ".join(skipped))

    def _ng_reroll_gear(self):
        """New equipment for the current NPC: strikes, armor, magic items, spells, and coins. The rest stays."""
        if not self.ng_current:
            messagebox.showinfo("Generate first", "Generate an NPC first."); return
        c, p = self.ng_current
        gear = self.ng_gear.var.get() or "None"
        self.config_data["npc_gear"] = gear
        templated = bool(tpl.applied(c)) and self.ng_base is not None
        target = self.ng_base if templated else c           # new gear goes on the plain NPC, then the templates are redone
        style, packs = self._ng_style_packs()
        env = self.ng_env.var.get()
        kit = npcgen.regear(target, self.ng_role.var.get(), self.ng_anc.var.get().strip(), target.level, gear,
                            tone=self.ng_tone.var.get() or "any", registry=self.story_registry,
                            campaign=self._story_campaign(), style=style, packs=packs, env=None if env in ("", "any") else env)
        if templated:
            steps = [(t["key"], t.get("options") or {}) for t in c.stats.get("templates", [])]
            try:
                res = tpl.apply_chain(copy.deepcopy(self.ng_base), steps, name=self.ng_name.get().strip() or c.name,
                                      mode=self.config_data.get("template_mode", "remaster"), custom=self.my_templates)
            except tpl.TemplateError as e:
                messagebox.showwarning("Templates", f"The new gear was made, but the templates couldn't be redone: {e}"); return
            self.ng_current = (res.creature, p)
        p["kit"], self.ng_kit = kit, kit
        self._ng_show()
        self._ng_kit_note()

    # --- templates ---
    def _open_template_dialog(self, creature, on_apply):
        """Open the template dialog for a creature. on_apply(result) gets the templated copy when Apply is pressed."""
        TemplateDialog(self, creature, on_apply, lambda parent: RichText(parent, self))

    def _ng_set_tpl_info(self):
        c = self.ng_current[0] if getattr(self, "ng_current", None) else None
        labels = [t.get("label", "") for t in (c.stats.get("templates", []) if c else []) if isinstance(t, dict)]
        self.ng_tpl_info.set("Templates on this NPC: " + ", ".join(labels) if labels else
                             "Templates: mummy, ghost, vampire, werecreature, and more. Apply one to the NPC below.")

    def _ng_template(self):
        c = self._ng_creature()
        if c is None:
            messagebox.showinfo("Generate first", "Generate an NPC first."); return
        self._open_template_dialog(c, self._ng_template_done)

    def _ng_template_done(self, res):
        old, p = self.ng_current
        if not tpl.applied(old) or self.ng_base is None:
            self.ng_base = copy.deepcopy(old)                # the NPC as it was before its first template
        self.ng_current = (res.creature, p)
        self.ng_name.set(res.creature.name)
        self._ng_set_tpl_info()
        self._ng_show()
        n = len(res.warns)
        self.last_roll.set(f"Applied the {res.creature.stats['templates'][-1]['label']} template to {self.ng_base.name}."
                           + (f" {n} thing{'s' if n != 1 else ''} to check were listed in the dialog." if n else ""))

    def _ng_remove_templates(self):
        if not self.ng_current or self.ng_base is None or not tpl.applied(self.ng_current[0]):
            messagebox.showinfo("Templates", "This NPC has no templates to remove."); return
        base = copy.deepcopy(self.ng_base)
        self.ng_current = (base, self.ng_current[1])
        self.ng_name.set(base.name)
        self.ng_base = None
        self._ng_set_tpl_info()
        self._ng_show()

    def _enc_apply_template(self):
        """Turn the selected encounter creature into a templated custom creature and swap it into the encounter."""
        sel = self.enc_tree.selection()
        if not sel or sel[0] not in self.enc_rows:
            messagebox.showinfo("Select a creature", "Select a creature row (not the encounter row) first."); return
        ei, gi = self.enc_rows[sel[0]]
        c, n = self.encs[ei].groups[gi]
        if c.is_hazard:
            messagebox.showinfo("Hazard", "Templates apply to creatures, not hazards."); return
        if c.custom and not c.adjust:
            src = next((x for x in self.c_creatures if x.name == c.name), None)
            src = copy.deepcopy(src) if src else None
        else:
            d = self.details_for(c)
            src = Creature(**details_to_custom(d, name=c.name), system=system_of(c)) if d else None
        if src is None:
            messagebox.showinfo("No stat block", f"No stat block is stored for {c.name}. Re-download data first."); return

        def done(res):
            new = res.creature
            taken = {x.name.lower() for x in self.c_creatures}
            base_name, k = new.name, 2
            while new.name.lower() in taken:
                new.name, k = f"{base_name} ({k})", k + 1
            self.c_creatures.append(new)
            storage.save_custom_creatures(self.c_creatures)
            self._refresh_custom()
            enc = self.encs[ei]
            enc.groups[gi] = (new, n)
            recompute(enc, self.party_level())
            self._draw_encounters(select=sel[0])
            self._show_selected_creature()
            self.enc_info.set(f"'{new.name}' is saved in Custom Content and now stands in for {c.name} in this encounter.")
        self._open_template_dialog(src, done)

    def _cu_apply_template(self):
        """Apply a template to the creature in the Custom Content form. Nothing is saved until Save Creature."""
        c = self._creature_from_form()
        if c is None:
            return

        def done(res):
            self._fill_creature_form(res.creature)
            self.last_roll.set(f"Applied the {res.creature.stats['templates'][-1]['label']} template in the form. "
                               "Press Save Creature to keep it.")
        self._open_template_dialog(c, done)

    def _ng_show_cards(self):
        kit = self.ng_kit
        text = npckit.kit_text(kit, cards=True) if kit else ""
        if not text:
            messagebox.showinfo("Gear", "This NPC has no equipment. Pick Light, Standard, or Well-equipped and press "
                                "Generate or Reroll Gear."); return
        win = tk.Toplevel(self); win.title("Gear: " + (self.ng_name.get() or "NPC")); win.geometry("560x560")
        box = tk.Text(win, wrap="word", padx=8, pady=6, font=("TkDefaultFont", 10))
        sb = ttk.Scrollbar(win, command=box.yview); box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); box.pack(fill="both", expand=True)
        box.insert("1.0", text); box.configure(state="disabled")

    def _ng_save_items(self, kit, npc_name):
        """Copy the NPC's generated magic items into My Items, so they can be awarded as loot."""
        added = 0
        have = {x.get("id") for x in self.magic_items}
        for it in npckit.kit_items(kit):
            if it.get("id") in have:
                continue
            data = copy.deepcopy(it)
            data["source_npc"] = npc_name
            self.magic_items.append(data); have.add(data.get("id")); added += 1
            self._keep_book_spells(data)
        if added:
            storage.save("magic_items", self.magic_items)
            self._magic_lib_refresh()
        return added

    def _ng_new_name(self):
        self.ng_name.set(nmod.make_name(self._ng_ancestry()))
        if self.ng_current:
            self._ng_show()

    def _ng_new_personality(self):
        if self.ng_current:
            kw = self._ng_params()
            p = npcgen.personality(extras=self._int_or_none(self.ng_extras.get()), ancestry=self.ng_anc.var.get().strip(), **kw)
            self.ng_current = (self.ng_current[0], p)
            self._ng_set_lines(p["fields"])
            self._ng_show()

    def _ng_reroll_line(self):
        if not self.ng_current:
            messagebox.showinfo("Generate first", "Generate an NPC first."); return
        line_no = int(str(self.ng_text.index("insert")).split(".")[0])
        line = self.ng_text.get(f"{line_no}.0", f"{line_no}.end")
        label = line.partition(":")[0].strip()
        new = npcgen.reroll_axis(label, ancestry=self.ng_anc.var.get().strip(), **self._ng_params())
        if new is None:
            messagebox.showinfo("Reroll line", "Click inside one of the personality lines first (for example Quirk or Goal)."); return
        self.ng_text.delete(f"{line_no}.0", f"{line_no}.end")
        self.ng_text.insert(f"{line_no}.0", f"{label}: {new}")
        self._ng_show()

    def _ng_save(self, to_custom, to_notebook):
        c = self._ng_creature()
        if not c:
            messagebox.showinfo("Generate first", "Generate an NPC first."); return
        if to_custom:
            existing = {x.name.lower() for x in self.c_creatures}
            if c.name.lower() in existing and not messagebox.askyesno("Replace?", f"Replace custom creature '{c.name}'?"):
                return
            self.c_creatures = [x for x in self.c_creatures if x.name.lower() != c.name.lower()] + [c]
            storage.save_custom_creatures(self.c_creatures)
            self._refresh_custom()
        if to_notebook:
            lines = self._ng_lines()
            body = "\n".join(f"{label}: {text}" for label, text in lines)
            _, fpage = self._ng_faction_info()
            if fpage is not None:
                body += f"\n\nMember of [[{fpage['title']}]]"
            gear_text = npckit.kit_text(self.ng_kit, cards=True)
            if gear_text:
                body += "\n\n" + gear_text
            page = nbk.find(self.notebook, c.name)
            if page is None or page.get("type") != "NPC":       # never overwrite a place or faction of the same name
                page = nbk.new_page(nbk.unique_title(self.notebook, c.name), "NPC", body, status="alive")
                self.notebook.append(page)
            else:
                page["body"] = body
            page.update(ancestry=self.ng_anc.var.get().strip(), role=f"{self.ng_role.var.get()} {c.level}",
                        creature=c.name if to_custom else "")
            if not to_custom:
                page["npc_stats"] = c.to_dict()
            self._save_notebook(); self._refresh_notebook()
        n_items = self._ng_save_items(self.ng_kit, c.name) if (self.ng_save_items.get() and self.ng_kit) else 0
        self.last_roll.set(f"Saved {c.name}" + (" to Custom Content" if to_custom else "")
                           + (" and the Notebook" if to_custom and to_notebook else " to the Notebook" if to_notebook else "")
                           + (f", and {n_items} magic item{'s' if n_items != 1 else ''} to My Items" if n_items else ""))

    def _ng_loot(self):
        """Everything the NPC carries goes into Party Loot (party stash). Its magic items and coins also go in the treasure
        ledger, since they are treasure the party found; everyday gear and trappings do not."""
        c = self._ng_creature()
        kit = self.ng_kit or {}
        if c is None:
            messagebox.showinfo("Generate first", "Generate an NPC first."); return
        src = f"Looted from {c.name}"
        n_items = n_magic = 0
        coins_cp = 0
        for it in npckit.kit_items(kit):
            self._magic_award(it, source=src, quiet=True); n_magic += 1
        gear = [(kit.get("armor"), kit.get("armor_base")), (kit.get("weapon"), kit.get("weapon_base")),
                (kit.get("ranged"), "")] + [(m, m) for m in kit.get("mundane") or []]
        for text, base in gear:
            if text:
                price = self._pl_price(ploot._base_name(base or text))
                ploot.add(self.party_loot, ploot.new_entry(text, 1, value_gp=price or 0, source=src,
                                                           rules_name=ploot._base_name(base or text)))
                n_items += 1
        for line in kit.get("trappings") or []:
            try:
                coins_cp += ploot.parse_coins(line)
                continue
            except ValueError:
                pass
            ploot.add(self.party_loot, ploot.new_entry(line, 1, source=src, kind="trapping")); n_items += 1
        if kit.get("coins"):
            coins_cp += ploot.to_cp(kit["coins"])
            self.ledger.append({"level": int(c.level), "kind": "currency", "name": "Currency", "value_gp": float(kit["coins"]),
                                "date": datetime.date.today().isoformat()})
            storage.save("ledger", self.ledger); self._refresh_ledger()
        if coins_cp:
            ploot.credit_stash(self.party_loot, coins_cp, src)
        self._pl_changed()
        self.last_roll.set(f"Looted {c.name}: {n_magic} magic item{'s' if n_magic != 1 else ''}, {n_items} other "
                           f"thing{'s' if n_items != 1 else ''}" + (f", and {ploot.coin_text(coins_cp)}" if coins_cp else "")
                           + " went into Party Loot (party stash).")

    def _ng_combat(self):
        c = self._ng_creature()
        if not c:
            return
        if not any(x.name.lower() == c.name.lower() for x in self.c_creatures):
            self.c_creatures.append(c); storage.save_custom_creatures(self.c_creatures); self._refresh_custom()
        self._add_creature_to_combat(c)
        self._combat_changed()
        self.nb.select(self.tab_combat)

    # --- downtime ---
    DT_PROFS = ["Auto"] + dt.PROFS

    def _dt_packs(self):
        on = hasattr(self, "story_pack_vars") and self.story_pack_vars["hallowmead"].get()
        return ["core"] + (["hallowmead"] if on else [])

    def _dt_save(self):
        storage.save("downtime", self.dt_store)

    def _dt_pc(self):
        """The character chosen at the top of the Downtime tab (a party entry), or None."""
        name = self.dt_pc.var.get()
        return next((x for x in self.party if x["name"] == name), None)

    def _dt_ruleset(self):
        label = self.dt_rules.var.get()
        return next((k for k, v in dt.RULESETS.items() if v["label"] == label), "remaster")

    def _dt_party_names(self):
        return sorted({pc["name"] for pc in self.party} | set(self.dt_store["purses"]))

    def _dt_party_changed(self):
        """The party changed: refresh the character list and anything that shows it."""
        if not hasattr(self, "dt_pc"):
            return
        names = ["(none)"] + sorted(pc["name"] for pc in self.party)
        self.dt_pc.set_values(names)
        if self.dt_pc.var.get() not in names:
            self.dt_pc.var.set(names[1] if len(names) > 1 else "(none)")
        self._dt_refresh_all()

    def _dt_refresh_places(self):
        if hasattr(self, "de_where"):
            names = ["Anywhere"] + sorted(p["title"] for p in self.notebook if p.get("type") in ("Faction", "Location"))
            self.de_where.set_values(names)
            if self.de_where.var.get() not in names:
                self.de_where.var.set("Anywhere")

    def _dt_refresh_all(self):
        self._dt_pc_info()
        if hasattr(self, "dc_tree"):
            self._dt_craft_search(); self._dt_craft_show()
        self._dt_refresh_jobs()
        self._dt_refresh_projects()
        self._dt_refresh_funds()

    def _dt_pc_info(self):
        pc = self._dt_pc()
        if pc is None:
            self.dt_info.set("Pick a character to roll for them, or leave it on (none) and type modifiers and results by hand.")
            return
        cr = dt.pc_skill(pc, "crafting")
        rank = cr["rank"] or "rank unknown (re-import to save it)"
        bal = dt.purse_balance(self.dt_store, pc["name"])
        self.dt_info.set(f"{pc['name']}: level {pc.get('level', '?')}, Crafting {rank}" + (f" ({cr['mod']:+d})" if cr["mod"] is not None else "")
                         + f"; funds {dt.coin_text(bal)}")

    def _build_downtime(self, f):
        self.dt_store = dt.ensure_store(getattr(self, "dt_store", None) or storage.load("downtime"))
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(top, text="Character").pack(side="left")
        self.dt_pc = Combo(top, ["(none)"], readonly=True, width=22); self.dt_pc.pack(side="left", padx=4)
        ttk.Label(top, text="Crafting rules").pack(side="left", padx=(12, 2))
        self.dt_rules = Combo(top, [v["label"] for v in dt.RULESETS.values()], readonly=True, width=22)
        self.dt_rules.var.set(dt.RULESETS[self.dt_store["settings"].get("ruleset", "remaster")]["label"]); self.dt_rules.pack(side="left")
        ttk.Button(top, text="Edit Tables...", command=self._story_open_tables).pack(side="right", padx=2)
        self.dt_info = tk.StringVar()
        ttk.Label(f, textvariable=self.dt_info, foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=10)
        tabs = TabbedPane(f, level=3); tabs.pack(fill="both", expand=True, padx=4, pady=4)
        pages = [ttk.Frame(tabs) for _ in range(6)]
        for page, text in zip(pages, ("Earn Income", "Craft", "Projects", "Funds", "Events", "Identify and Learn")):
            tabs.add(page, text=text)
        self.dt_tabs, self.dt_pages = tabs, pages
        self._dt_build_earn(pages[0]); self._dt_build_craft(pages[1]); self._dt_build_projects(pages[2])
        self._dt_build_funds(pages[3]); self._dt_build_events(pages[4]); self._dt_build_identify(pages[5])
        self.dt_pc.var.trace_add("write", lambda *a: self._dt_refresh_all())
        self.dt_rules.var.trace_add("write", lambda *a: self._dt_rules_changed())
        self._dt_refresh_places()
        self._dt_party_changed()

    def _dt_rules_changed(self):
        self.dt_store["settings"]["ruleset"] = self._dt_ruleset()
        self._dt_save()
        self._dt_craft_show()

    # ----- Earn Income
    def _dt_build_earn(self, f):
        left = ttk.LabelFrame(f, text="The job"); left.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        bar = ttk.Frame(left); bar.pack(fill="x", pady=2)
        ttk.Label(bar, text="Where").pack(side="left", padx=4)
        self.de_where = Combo(bar, ["Anywhere"], readonly=True, width=24); self.de_where.var.set("Anywhere"); self.de_where.pack(side="left")
        ttk.Label(bar, text="Job board level").pack(side="left", padx=(12, 2))
        self.de_level = tk.StringVar(value=str(max(0, self.party_level() - 2)))
        ttk.Spinbox(bar, from_=0, to=20, textvariable=self.de_level, width=4).pack(side="left")
        self.de_where.var.trace_add("write", lambda *a: self._dt_refresh_jobs())
        self.de_level.trace_add("write", lambda *a: self._dt_refresh_jobs())
        ttk.Label(left, foreground="#777", wraplength=520, justify="left", text=(
            "Player Core leaves the job's skill and task level to the GM. The board is a starting point: change the skill and "
            "level on the right, and edit the jobs themselves in Edit Tables.")).pack(anchor="w", padx=4)
        self.de_tree = ttk.Treeview(left, columns=("skill", "lvl"), show="tree headings", height=14)
        self.de_tree.heading("#0", text="Job"); self.de_tree.column("#0", width=380)
        for c, t, w in (("skill", "Skill", 150), ("lvl", "Task level", 70)):
            self.de_tree.heading(c, text=t); self.de_tree.column(c, width=w)
        self.de_tree.pack(fill="both", expand=True, padx=2, pady=2)
        self.de_tree.bind("<<TreeviewSelect>>", lambda e: self._dt_job_picked())
        self.de_jobs = []
        right = ttk.LabelFrame(f, text="The check"); right.pack(side="left", fill="y", padx=4, pady=4)
        self.de_vars = {k: tk.StringVar(value=v) for k, v in (("skill", "Crafting"), ("task", "1"), ("prof", "Auto"), ("mod", ""), ("extra", "0"),
                                                               ("days", "7"), ("result", "Roll it"))}
        rows = [("Skill", ttk.Combobox(right, textvariable=self.de_vars["skill"], values=[s.title() for s in pb.SKILLS] + ["Lore (...)"], width=22)),
                ("Task level", ttk.Spinbox(right, from_=0, to=20, textvariable=self.de_vars["task"], width=5)),
                ("Proficiency", ttk.Combobox(right, textvariable=self.de_vars["prof"], values=self.DT_PROFS, state="readonly", width=12)),
                ("Modifier", ttk.Entry(right, textvariable=self.de_vars["mod"], width=7)),
                ("Other bonus", ttk.Entry(right, textvariable=self.de_vars["extra"], width=7)),
                ("Days", ttk.Spinbox(right, from_=1, to=365, textvariable=self.de_vars["days"], width=5)),
                ("Result", ttk.Combobox(right, textvariable=self.de_vars["result"], values=["Roll it"] + dt.RESULTS, state="readonly", width=16))]
        for r, (lab, w) in enumerate(rows):
            ttk.Label(right, text=lab).grid(row=r, column=0, sticky="w", padx=4, pady=2); w.grid(row=r, column=1, sticky="w", pady=2)
        ttk.Label(right, foreground="#777", wraplength=240, justify="left", text=(
            "Auto proficiency and a blank modifier come from the character. Without one, fill them in.")).grid(row=len(rows), column=0, columnspan=2, padx=4, sticky="w")
        self.de_credit = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="Pay it into the character's funds", variable=self.de_credit).grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w", padx=4)
        bb = ttk.Frame(right); bb.grid(row=len(rows) + 2, column=0, columnspan=2, pady=4)
        ttk.Button(bb, text="Roll and Pay", command=lambda: self._dt_earn_go(True)).pack(side="left", padx=2)
        ttk.Button(bb, text="Show Result", command=lambda: self._dt_earn_go(False)).pack(side="left", padx=2)
        self.de_out = tk.StringVar()
        ttk.Label(right, textvariable=self.de_out, wraplength=260, justify="left", foreground="#1a5fb4").grid(row=len(rows) + 3, column=0, columnspan=2, sticky="w", padx=4)

    def _dt_refresh_jobs(self):
        if not hasattr(self, "de_tree"):
            return
        where = self.de_where.var.get()
        place = None if where in ("", "Anywhere") else where
        base = self._int_or_none(str(self.de_level.get()))
        base = max(0, min(20, 0 if base is None else base))
        page = nbk.find(self.notebook, place) if place else None
        jobs = dt.jobs(self.story_registry, place, base, self._dt_packs(), tavern=bool(page and page.get("tavern")))
        if page and page.get("tavern"):                          # a saved inn or tavern brings its own jobs
            saved = [{"id": "", "text": j["text"], "skills": j["skills"], "level": j["level"], "place": None, "table": "saved"} for j in page["tavern"].get("jobs", [])]
            jobs = saved + [j for j in jobs if j["table"] != "dt.job.tavern"]
        self.de_jobs = jobs
        self.de_tree.delete(*self.de_tree.get_children())
        for i, j in enumerate(jobs):
            self.de_tree.insert("", "end", iid=str(i), text=j["text"], values=(" or ".join(dt.skill_label(s) for s in j["skills"]), j["level"]))

    def _dt_job_picked(self):
        sel = self.de_tree.selection()
        if not sel or int(sel[0]) >= len(self.de_jobs):
            return
        job = self.de_jobs[int(sel[0])]
        pc = self._dt_pc()
        skill = dt.best_skill(pc, job)[0] if pc is not None else job["skills"][0]
        self.de_vars["skill"].set(dt.skill_label(skill))
        self.de_vars["task"].set(str(job["level"]))

    def _dt_job_text(self):
        sel = self.de_tree.selection()
        if sel and int(sel[0]) < len(self.de_jobs):
            return self.de_jobs[int(sel[0])]["text"]
        return f"{self.de_vars['skill'].get()} work"

    def _dt_earn_go(self, pay):
        pc = self._dt_pc()
        v = self.de_vars
        skill = v["skill"].get().strip() or "Crafting"
        task = self._int_or_none(v["task"].get())
        days = self._int_or_none(v["days"].get())
        if task is None or days is None:
            messagebox.showwarning("Earn Income", "Task level and days must be numbers."); return
        info = dt.pc_skill(pc, skill) if pc is not None else {"mod": None, "rank": None}
        prof = v["prof"].get()
        prof = info["rank"] if prof == "Auto" else prof
        if prof is None:
            messagebox.showinfo("Proficiency", "This character's proficiency isn't on file. Pick one from the list."); return
        if dt.rank_name(prof) == "Untrained":
            messagebox.showinfo("Untrained", f"{pc['name'] if pc else 'The character'} is untrained in {dt.skill_label(skill)}. The Income Earned table has no column for an untrained character."); return
        mod = self._int_or_none(v["mod"].get().replace("+", ""))
        mod = info["mod"] if mod is None else mod
        extra = self._int_or_none(v["extra"].get().replace("+", "")) or 0
        dc = dt.level_dc(task)
        want = v["result"].get()
        if want == "Roll it":
            if mod is None:
                messagebox.showinfo("Modifier", "No modifier on file for that skill. Type one in the Modifier box."); return
            roll = dt.roll_check(mod, dc, extra=extra)
            result, head = roll["degree"], (f"{pc['name'] + ' ' if pc else ''}{dt.check_text(roll)}. ")
        else:
            result, head = want, f"DC {dc}. "
        r = dt.earn_result(task, prof, result, days)
        text = head + r["text"]
        if pay and pc is not None and r["total_cp"]:
            dt.purse_add(self.dt_store, pc["name"], r["total_cp"], f"Earn Income: {self._dt_job_text()} ({days} day{'s' if days != 1 else ''})")
            text += f" Paid into {pc['name']}'s funds."
        if pay:
            dt.log_line(self.dt_store, f"Earn Income, {self._dt_job_text()}: {result}, {dt.coin_text(r['total_cp'])}", pc["name"] if pc else "")
            self._dt_save()
        self.de_out.set(text)
        self.last_roll.set(text)
        self._dt_pc_info(); self._dt_refresh_funds()

    # ----- Craft
    def _dt_build_craft(self, f):
        left = ttk.LabelFrame(f, text="The item"); left.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        bar = ttk.Frame(left); bar.pack(fill="x", pady=2)
        ttk.Label(bar, text="Search").pack(side="left", padx=4)
        self.dc_q = tk.StringVar()
        ttk.Entry(bar, textvariable=self.dc_q, width=26).pack(side="left")
        self.dc_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Only items this character could craft", variable=self.dc_only).pack(side="left", padx=8)
        self.dc_q.trace_add("write", lambda *a: self._dt_craft_search())
        self.dc_only.trace_add("write", lambda *a: self._dt_craft_search())
        self.dc_tree = ttk.Treeview(left, columns=("lvl", "price", "rarity"), show="tree headings", height=14)
        self.dc_tree.heading("#0", text="Item"); self.dc_tree.column("#0", width=330)
        for c, t, w in (("lvl", "Lvl", 40), ("price", "Price", 90), ("rarity", "Rarity", 80)):
            self.dc_tree.heading(c, text=t); self.dc_tree.column(c, width=w)
        self.dc_tree.pack(fill="both", expand=True, padx=2, pady=2)
        self.dc_tree.bind("<<TreeviewSelect>>", lambda e: self._dt_craft_show())
        self.dc_items = []
        right = ttk.LabelFrame(f, text="Can they make it?"); right.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.dc_vars = {k: tk.StringVar(value=v) for k, v in (("qty", "1"), ("formula", "Auto"), ("prof", "Auto"), ("level", ""))}
        grid = ttk.Frame(right); grid.pack(fill="x")
        for c, (lab, w) in enumerate((("Quantity", ttk.Spinbox(grid, from_=1, to=99, textvariable=self.dc_vars["qty"], width=5)),
                                      ("Formula", ttk.Combobox(grid, textvariable=self.dc_vars["formula"], values=["Auto", "Has it", "Doesn't"], state="readonly", width=8)),
                                      ("Crafting", ttk.Combobox(grid, textvariable=self.dc_vars["prof"], values=self.DT_PROFS, state="readonly", width=10)),
                                      ("Level", ttk.Entry(grid, textvariable=self.dc_vars["level"], width=5)))):
            ttk.Label(grid, text=lab).grid(row=0, column=c * 2, padx=(8, 2), pady=2); w.grid(row=0, column=c * 2 + 1)
        for v in self.dc_vars.values():
            v.trace_add("write", lambda *a: self._dt_craft_show())
        self.dc_out = tk.Text(right, height=18, wrap="word", state="disabled", font=("TkDefaultFont", 10))
        self.dc_out.pack(fill="both", expand=True, padx=2, pady=4)
        bb = ttk.Frame(right); bb.pack(fill="x")
        ttk.Button(bb, text="Start Project", command=self._dt_craft_start).pack(side="right", padx=2)
        self._dt_craft_search()

    def _dt_crafter(self):
        """What the Craft pages need to know about the crafter: {pc, level, rank, feats, formula (True/False/None)}."""
        pc = self._dt_pc()
        lvl = self._int_or_none(self.dc_vars["level"].get()) if hasattr(self, "dc_vars") else None
        lvl = lvl if lvl is not None else (int(pc.get("level", 1)) if pc else self.party_level())
        rank = dt.pc_skill(pc, "crafting")["rank"] if pc else None
        prof = self.dc_vars["prof"].get() if hasattr(self, "dc_vars") else "Auto"
        rank = rank if prof == "Auto" else prof
        return {"pc": pc, "level": lvl, "rank": rank, "feats": dt.pc_feats(pc)}

    def _dt_craft_search(self):
        if not hasattr(self, "dc_tree"):
            return
        q = self.dc_q.get().strip().lower()
        who = self._dt_crafter()
        self.dc_tree.delete(*self.dc_tree.get_children())
        self.dc_items = []
        if len(q) < 2:
            return
        out = [i for i in self.all_items if self.in_systems(i) and q in i.name.lower() and (not self.dc_only.get() or i.level <= who["level"])]
        out.sort(key=lambda i: (i.level, i.name))
        for i, it in enumerate(out[:200]):
            self.dc_items.append(it)
            self.dc_tree.insert("", "end", iid=str(i), text=it.name, values=(it.level, price_text(it), it.rarity))

    def _dt_craft_item(self):
        sel = self.dc_tree.selection()
        if not sel or int(sel[0]) >= len(self.dc_items):
            return None
        it = self.dc_items[int(sel[0])]
        return {"name": it.name, "level": it.level, "price_gp": it.price_gp, "rarity": it.rarity, "traits": list(it.traits), "consumable": it.consumable}

    def _dt_craft_formula(self, item, who):
        pick = self.dc_vars["formula"].get()
        if pick == "Has it":
            return True
        if pick == "Doesn't":
            return False
        known = dt.pc_knows_formula(who["pc"], item["name"])
        return bool(known)

    def _dt_craft_text(self):
        """What the Craft page says about the chosen item: (text, item, plan or None)."""
        item = self._dt_craft_item()
        if item is None:
            return "Search for an item and pick it to see whether the character can make it, what it costs, and how long it takes.", None, None
        who = self._dt_crafter()
        rs = self._dt_ruleset()
        formula = self._dt_craft_formula(item, who)
        reqs = dt.craft_requirements(item, who["level"], who["rank"], who["feats"], formula, rs)
        lines = [f"{item['name']} (level {item['level']}, {dt.coin_text(dt.to_cp(item['price_gp']))}, {item['rarity']})",
                 f"Crafter: {who['pc']['name'] if who['pc'] else 'no character chosen'}, level {who['level']}, Crafting {who['rank'] or 'unknown'}.",
                 f"Rules: {dt.RULESETS[rs]['label']}.", ""]
        for r in reqs:
            lines.append(("Problem: " if r["ok"] is False else "Check: " if r["ok"] is None else "OK: ") + r["text"])
        plan = None
        prof = dt.rank_name(who["rank"]) if who["rank"] else "Trained"
        if not dt.craft_blockers(reqs) and prof != "Untrained":
            qty = max(1, self._int_or_none(self.dc_vars["qty"].get()) or 1)
            plan = dt.craft_plan(item, who["level"], prof, rs, formula, qty)
            lines += ["", dt.craft_summary(plan)]
        return "\n".join(lines), item, plan

    def _dt_craft_show(self):
        if not hasattr(self, "dc_out"):
            return
        text = self._dt_craft_text()[0]
        self.dc_out.configure(state="normal"); self.dc_out.delete("1.0", "end"); self.dc_out.insert("end", text); self.dc_out.configure(state="disabled")

    def _dt_craft_start(self):
        text, item, plan = self._dt_craft_text()
        if item is None:
            messagebox.showinfo("Pick an item", "Search for an item and pick it first."); return
        who = self._dt_crafter()
        if plan is None:
            blockers = dt.craft_blockers(dt.craft_requirements(item, who["level"], who["rank"], who["feats"], False, self._dt_ruleset()))
            if not messagebox.askyesno("Start anyway?", "This character can't craft it as things stand:\n\n" + "\n".join(blockers[:4]) + "\n\nStart a project anyway?"):
                return
            prof = dt.rank_name(who["rank"]) if who["rank"] and dt.rank_name(who["rank"]) != "Untrained" else "Trained"
        else:
            prof = dt.rank_name(who["rank"]) if who["rank"] else "Trained"
        qty = max(1, self._int_or_none(self.dc_vars["qty"].get()) or 1)
        p = dt.start_craft(self.dt_store, who["pc"]["name"] if who["pc"] else "", item, who["level"], prof, qty, self._dt_ruleset(),
                           self._dt_craft_formula(item, who))
        dt.log_line(self.dt_store, f"Started crafting {p['title']}", p["owner"])
        self._dt_save(); self._dt_refresh_projects(select=p["id"])
        self.dt_tabs.select(self.dt_pages[2])
        self.last_roll.set(f"Started a project: {p['title']}.")

    # ----- Projects
    def _dt_build_projects(self, f):
        top = ttk.Frame(f); top.pack(fill="x", pady=3)
        for text, cmd in (("Roll Crafting Check", self._dt_proj_check), ("Enter Result...", self._dt_proj_result), ("Work Days", self._dt_proj_work),
                          ("Pay Remaining", self._dt_proj_pay), ("Pause / Resume", self._dt_proj_pause), ("Abandon", self._dt_proj_abandon)):
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)
        ttk.Label(top, text="days").pack(side="left", padx=(8, 2))
        self.dp_days = tk.StringVar(value="1")
        ttk.Spinbox(top, from_=1, to=365, textvariable=self.dp_days, width=5).pack(side="left")
        self.dp_charge = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Charge the owner's funds", variable=self.dp_charge).pack(side="left", padx=10)
        row2 = ttk.Frame(f); row2.pack(fill="x", pady=2)
        for text, cmd in (("New Project...", self._dt_proj_new), ("Add Note...", self._dt_proj_note), ("Roll an Event", self._dt_proj_event),
                          ("Delete", self._dt_proj_delete)):
            ttk.Button(row2, text=text, command=cmd).pack(side="left", padx=2)
        ttk.Label(row2, text="Show").pack(side="left", padx=(12, 2))
        self.dp_filter = Combo(row2, ["Active", "All"], readonly=True, width=8); self.dp_filter.var.set("Active"); self.dp_filter.pack(side="left")
        self.dp_filter.var.trace_add("write", lambda *a: self._dt_refresh_projects())
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=2)
        self.dp_tree = ttk.Treeview(left, columns=("owner", "what"), show="tree headings", height=14)
        self.dp_tree.heading("#0", text="Project"); self.dp_tree.column("#0", width=260)
        for c, t, w in (("owner", "Owner", 100), ("what", "Where it stands", 280)):
            self.dp_tree.heading(c, text=t); self.dp_tree.column(c, width=w)
        self.dp_tree.pack(fill="both", expand=True)
        self.dp_tree.bind("<<TreeviewSelect>>", lambda e: self._dt_proj_show())
        right = ttk.Frame(pane); pane.add(right, weight=3)
        self.dp_text = tk.Text(right, wrap="word", state="disabled", font=("TkDefaultFont", 10))
        self.dp_text.pack(fill="both", expand=True)
        self.dp_msg = tk.StringVar()
        ttk.Label(f, textvariable=self.dp_msg, foreground="#1a5fb4", wraplength=1050, justify="left").pack(anchor="w", padx=8)

    def _dt_refresh_projects(self, select=None):
        if not hasattr(self, "dp_tree"):
            return
        sel = select or (self.dp_tree.selection()[0] if self.dp_tree.selection() else None)
        self.dp_tree.delete(*self.dp_tree.get_children())
        active = self.dp_filter.var.get() == "Active"
        for p in dt.projects_for(self.dt_store, None, active):
            self.dp_tree.insert("", "end", iid=p["id"], text=p["title"], values=(p["owner"], dt.project_progress(p)))
        if sel and self.dp_tree.exists(sel):
            self.dp_tree.selection_set(sel)
        self._dt_proj_show()

    def _dt_proj(self):
        sel = self.dp_tree.selection()
        return next((p for p in self.dt_store["projects"] if sel and p["id"] == sel[0]), None)

    def _dt_proj_show(self):
        p = self._dt_proj()
        t = self.dp_text
        t.configure(state="normal"); t.delete("1.0", "end")
        t.insert("end", dt.project_text(p) if p else "Select a project, or start one on the Craft page or with New Project.")
        t.configure(state="disabled")

    def _dt_proj_done(self, p, message, charge_cp=0, reason=""):
        if charge_cp and self.dp_charge.get() and p["owner"]:
            dt.purse_add(self.dt_store, p["owner"], -charge_cp, reason)
            message += f" {dt.coin_text(charge_cp)} taken from {p['owner']}'s funds."
        dt.log_line(self.dt_store, message, p["owner"])
        self.dp_msg.set(message); self.last_roll.set(message)
        self._dt_save(); self._dt_refresh_projects(select=p["id"]); self._dt_pc_info(); self._dt_refresh_funds()

    def _dt_proj_guard(self, fn):
        """Run a project step. Returns (True, what it returned), or (False, None) after telling the user why it can't be done."""
        try:
            return True, fn()
        except ValueError as e:
            messagebox.showinfo("Project", str(e))
            return False, None

    def _dt_proj_check(self):
        p = self._dt_proj()
        if p is None:
            messagebox.showinfo("Select a project", "Select a Craft project first."); return
        pc = next((x for x in self.party if x["name"] == p["owner"]), None)
        mod = dt.pc_skill(pc, "crafting")["mod"] if pc is not None else None
        if mod is None:
            n = self._ask_int("Crafting check", f"Total of {p['owner'] or 'the crafter'}'s Crafting check (DC {p['dc']})", "")
            if n is None:
                return
            result, how = dt.degree(n, p["dc"]), n
        else:
            roll = dt.roll_check(mod, p["dc"])
            result, how = roll["degree"], roll["total"]
            self.dp_msg.set(f"{p['owner']}: {dt.check_text(roll)}")
        ok, res = self._dt_proj_guard(lambda: dt.record_check(p, result, how))
        if ok:
            self._dt_proj_done(p, f"{p['title']}: {res['text']}", res["charge_cp"], f"Raw materials for {p['title']}")

    def _dt_proj_result(self):
        p = self._dt_proj()
        if p is None:
            messagebox.showinfo("Select a project", "Select a Craft project first."); return
        win = tk.Toplevel(self); win.title("Crafting check result"); win.transient(self)
        v = tk.StringVar(value="Success")
        ttk.Label(win, text=f"What was the result of the Crafting check (DC {p['dc']})?").pack(padx=10, pady=8)
        ttk.Combobox(win, textvariable=v, values=dt.RESULTS, state="readonly", width=20).pack(padx=10)

        def ok():
            done, res = self._dt_proj_guard(lambda: dt.record_check(p, v.get()))
            win.destroy()
            if done:
                self._dt_proj_done(p, f"{p['title']}: {res['text']}", res["charge_cp"], f"Raw materials for {p['title']}")
        ttk.Button(win, text="Record", command=ok).pack(pady=8)
        self.dp_result_win = (win, v, ok)

    def _dt_proj_work(self):
        p = self._dt_proj()
        n = self._int_or_none(str(self.dp_days.get())) or 1
        if p is None:
            messagebox.showinfo("Select a project", "Select a project first."); return
        ok, _res = self._dt_proj_guard(lambda: dt.work_days(p, n))
        if ok:
            self._dt_proj_done(p, f"{p['title']}: {p['log'][-1]['text']}")

    def _dt_proj_pay(self):
        p = self._dt_proj()
        if p is None:
            messagebox.showinfo("Select a project", "Select a project first."); return
        if p["kind"] == "custom":
            text = self._ask_line("Pay toward the cost", "Amount paid (for example 5 gp)", "")
            if text is None:
                return
            try:
                cp = dt.parse_coins(text)
            except ValueError as e:
                messagebox.showwarning("Amount", str(e)); return
            ok, _paid = self._dt_proj_guard(lambda: dt.pay_toward(p, cp))
            if ok:
                self._dt_proj_done(p, f"{p['title']}: {p['log'][-1]['text']}", cp, f"Paid toward {p['title']}")
            return
        ok, cost = self._dt_proj_guard(lambda: dt.pay_remaining(p))
        if ok:
            self._dt_proj_done(p, f"{p['title']}: finished the item.", cost, f"Remaining materials for {p['title']}")

    def _dt_proj_pause(self):
        p = self._dt_proj()
        if p is None:
            return
        fn = dt.resume if p["status"] == "paused" else dt.pause
        ok, _ = self._dt_proj_guard(lambda: fn(p))
        if ok:
            self._dt_proj_done(p, f"{p['title']}: {p['log'][-1]['text']}")

    def _dt_proj_abandon(self):
        p = self._dt_proj()
        if p is not None and messagebox.askyesno("Abandon", f"Abandon '{p['title']}'? Materials already used are not refunded."):
            ok, _ = self._dt_proj_guard(lambda: dt.abandon(p))
            if ok:
                self._dt_proj_done(p, f"{p['title']}: abandoned.")

    def _dt_proj_delete(self):
        p = self._dt_proj()
        if p is not None and messagebox.askyesno("Delete", f"Delete '{p['title']}' and its history?"):
            dt.delete_project(self.dt_store, p["id"])
            self._dt_save(); self._dt_refresh_projects()

    def _dt_proj_note(self):
        p = self._dt_proj()
        if p is None:
            return
        text = self._ask_line("Add a note", "Note for this project's history", "")
        if text and text.strip():
            dt.add_note(p, text.strip())
            self._dt_save(); self._dt_refresh_projects(select=p["id"])

    def _dt_proj_event(self):
        p = self._dt_proj()
        activity = "Craft" if p is not None and p["kind"] == "craft" else "Anything else"
        e = dt.roll_event(self.story_registry, activity, packs=self._dt_packs())
        self.dp_msg.set(f"Event: {e['text']}")
        if p is not None and e["text"]:
            dt.add_note(p, "Event: " + e["text"])
            self._dt_save(); self._dt_refresh_projects(select=p["id"])

    def _dt_proj_new(self):
        win = tk.Toplevel(self); win.title("New project"); win.transient(self)
        v = {k: tk.StringVar(value=d) for k, d in (("title", ""), ("owner", self.dt_pc.var.get() if self.dt_pc.var.get() != "(none)" else ""),
                                                   ("days", "7"), ("cost", ""), ("dc", ""), ("notes", ""))}
        rows = (("What is it?", ttk.Entry(win, textvariable=v["title"], width=36)),
                ("Whose?", ttk.Combobox(win, textvariable=v["owner"], values=sorted(pc["name"] for pc in self.party), width=24)),
                ("Days it takes", ttk.Spinbox(win, from_=1, to=999, textvariable=v["days"], width=6)),
                ("Cost (for example 40 gp)", ttk.Entry(win, textvariable=v["cost"], width=14)),
                ("DC (optional)", ttk.Entry(win, textvariable=v["dc"], width=6)),
                ("Notes", ttk.Entry(win, textvariable=v["notes"], width=36)))
        for r, (lab, w) in enumerate(rows):
            ttk.Label(win, text=lab).grid(row=r, column=0, sticky="w", padx=8, pady=3); w.grid(row=r, column=1, padx=8, sticky="w")
        ttk.Label(win, foreground="#777", wraplength=330, justify="left", text=(
            "For retraining, research, building something, or any long job where you set the terms. Craft projects start "
            "on the Craft page.")).grid(row=len(rows), column=0, columnspan=2, padx=8)

        def ok():
            if not v["title"].get().strip():
                return
            try:
                cost = dt.parse_coins(v["cost"].get()) if v["cost"].get().strip() else 0
            except ValueError as e:
                messagebox.showwarning("Cost", str(e), parent=win); return
            p = dt.start_custom(self.dt_store, v["owner"].get().strip(), v["title"].get().strip(), self._int_or_none(v["days"].get()) or 1, cost,
                                self._int_or_none(v["dc"].get()), v["notes"].get().strip())
            dt.log_line(self.dt_store, f"Started project: {p['title']}", p["owner"])
            win.destroy()
            self._dt_save(); self._dt_refresh_projects(select=p["id"])
        ttk.Button(win, text="Start", command=ok).grid(row=len(rows) + 1, column=1, sticky="e", padx=8, pady=8)
        self.dp_new_win = (win, v, ok)

    # ----- Funds
    def _dt_build_funds(self, f):
        top = ttk.Frame(f); top.pack(fill="x", pady=3)
        for text, cmd in (("Add Money...", lambda: self._dt_funds_change(1)), ("Spend...", lambda: self._dt_funds_change(-1)),
                          ("Set Balance...", self._dt_funds_set), ("From Pathbuilder", self._dt_funds_pb),
                          ("Cost of Living...", self._dt_funds_living), ("Undo Last", self._dt_funds_undo)):
            ttk.Button(top, text=text, command=cmd).pack(side="left", padx=2)
        pane = ttk.PanedWindow(f, orient="horizontal"); pane.pack(fill="both", expand=True, padx=4, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.df_tree = ttk.Treeview(left, columns=("bal",), show="tree headings", height=14)
        self.df_tree.heading("#0", text="Character"); self.df_tree.column("#0", width=200)
        self.df_tree.heading("bal", text="Funds"); self.df_tree.column("bal", width=140)
        self.df_tree.tag_configure("debt", foreground="#a33")
        self.df_tree.pack(fill="both", expand=True)
        self.df_tree.bind("<<TreeviewSelect>>", lambda e: self._dt_funds_log())
        right = ttk.Frame(pane); pane.add(right, weight=2)
        self.df_log = ttk.Treeview(right, columns=("amount", "bal", "date"), show="tree headings", height=14)
        self.df_log.heading("#0", text="What"); self.df_log.column("#0", width=340)
        for c, t, w in (("amount", "Amount", 110), ("bal", "Balance", 110), ("date", "Date", 90)):
            self.df_log.heading(c, text=t); self.df_log.column(c, width=w)
        self.df_log.pack(fill="both", expand=True)
        self.df_msg = tk.StringVar(value="Funds here are for downtime: what the party earns, spends on materials, and owes in living costs.")
        ttk.Label(f, textvariable=self.df_msg, foreground="#555", wraplength=1050, justify="left").pack(anchor="w", padx=8)

    def _dt_refresh_funds(self):
        if not hasattr(self, "df_tree"):
            return
        sel = self.df_tree.selection()
        keep = sel[0] if sel else None
        self.df_tree.delete(*self.df_tree.get_children())
        for i, name in enumerate(self._dt_party_names()):
            bal = dt.purse_balance(self.dt_store, name)
            self.df_tree.insert("", "end", iid=str(i), text=name, values=(dt.coin_text(bal),), tags=("debt",) if bal < 0 else ())
        names = self._dt_party_names()
        if keep and self.df_tree.exists(keep):
            self.df_tree.selection_set(keep)
        elif names and self.dt_pc.var.get() in names:
            self.df_tree.selection_set(str(names.index(self.dt_pc.var.get())))
        self._dt_funds_log()
        if hasattr(self, "pl_tree"):
            self._pl_refresh()

    def _dt_funds_who(self):
        sel = self.df_tree.selection()
        names = self._dt_party_names()
        return names[int(sel[0])] if sel and int(sel[0]) < len(names) else None

    def _dt_funds_log(self):
        self.df_log.delete(*self.df_log.get_children())
        who = self._dt_funds_who()
        if who:
            for i, e in enumerate(reversed(self.dt_store["purses"].get(who, {}).get("log", []))):
                self.df_log.insert("", "end", iid=str(i), text=e["reason"], values=(dt.coin_text(e["cp"]), dt.coin_text(e["balance_cp"]), e["date"]))

    def _dt_funds_changed(self, who, text):
        dt.log_line(self.dt_store, text, who)
        self._dt_save(); self._dt_refresh_funds(); self._dt_pc_info()
        self.df_msg.set(text); self.last_roll.set(text)

    def _dt_funds_change(self, sign):
        who = self._dt_funds_who()
        if who is None:
            messagebox.showinfo("Select a character", "Select a character first."); return
        text = self._ask_line("Add money" if sign > 0 else "Spend money", "Amount (for example 5 gp 3 sp)", "")
        if text is None:
            return
        try:
            cp = dt.parse_coins(text)
        except ValueError as e:
            messagebox.showwarning("Amount", str(e)); return
        why = self._ask_line("What for?", "A short reason for the log", "Added by hand" if sign > 0 else "Spent") or ("Added by hand" if sign > 0 else "Spent")
        dt.purse_add(self.dt_store, who, sign * abs(cp), why)
        self._dt_funds_changed(who, f"{who}: {'+' if sign > 0 else '-'}{dt.coin_text(abs(cp))} ({why}); now {dt.coin_text(dt.purse_balance(self.dt_store, who))}.")

    def _dt_funds_set(self):
        who = self._dt_funds_who()
        if who is None:
            return
        text = self._ask_line("Set balance", f"What {who} has now (for example 25 gp)", dt.coin_text(dt.purse_balance(self.dt_store, who)))
        if text is None:
            return
        try:
            cp = dt.parse_coins(text)
        except ValueError as e:
            messagebox.showwarning("Amount", str(e)); return
        dt.purse_set(self.dt_store, who, cp)
        self._dt_funds_changed(who, f"{who}'s funds set to {dt.coin_text(cp)}.")

    def _dt_funds_pb(self):
        who = self._dt_funds_who()
        pc = next((x for x in self.party if x["name"] == who), None)
        if pc is None or not pc.get("money"):
            messagebox.showinfo("Pathbuilder", "No coins on file for that character. Re-import them from Pathbuilder."); return
        cp = dt.pc_money_cp(pc)
        dt.purse_set(self.dt_store, who, cp, "From Pathbuilder")
        self._dt_funds_changed(who, f"{who}'s funds set from Pathbuilder: {dt.coin_text(cp)}.")

    def _dt_funds_undo(self):
        who = self._dt_funds_who()
        e = dt.purse_undo(self.dt_store, who) if who else None
        if e is None:
            messagebox.showinfo("Undo", "Nothing to undo."); return
        self._dt_funds_changed(who, f"{who}: undid '{e['reason']}'.")

    def _dt_funds_living(self):
        win = tk.Toplevel(self); win.title("Cost of living"); win.transient(self)
        v = {"standard": tk.StringVar(value="Comfortable"), "unit": tk.StringVar(value="week"), "count": tk.StringVar(value="1"), "all": tk.BooleanVar(value=True)}
        ttk.Label(win, foreground="#555", wraplength=380, justify="left", text=(
            "GM Core: charge this after the character's other downtime earnings. " + dt.LIVING_NOTE)).grid(row=0, column=0, columnspan=2, padx=8, pady=6)
        rows = (("Standard", ttk.Combobox(win, textvariable=v["standard"], values=list(dt.COST_OF_LIVING), state="readonly", width=14)),
                ("Per", ttk.Combobox(win, textvariable=v["unit"], values=["week", "month", "year"], state="readonly", width=8)),
                ("How many", ttk.Spinbox(win, from_=1, to=99, textvariable=v["count"], width=5)))
        for r, (lab, w) in enumerate(rows, start=1):
            ttk.Label(win, text=lab).grid(row=r, column=0, sticky="w", padx=8, pady=3); w.grid(row=r, column=1, sticky="w", padx=8)
        ttk.Checkbutton(win, text="Charge everyone in the party (not just the selected character)", variable=v["all"]).grid(row=4, column=0, columnspan=2, padx=8, sticky="w")
        out = tk.StringVar(); ttk.Label(win, textvariable=out, foreground="#1a5fb4").grid(row=5, column=0, columnspan=2, padx=8, pady=4)

        def cost():
            return dt.cost_of_living(v["standard"].get(), v["unit"].get(), self._int_or_none(v["count"].get()) or 1)

        def show(*_):
            out.set(f"{dt.coin_text(cost())} each.")
        for k in ("standard", "unit", "count"):
            v[k].trace_add("write", show)
        show()

        def ok():
            who = self._dt_funds_who()
            targets = [pc["name"] for pc in self.party] if v["all"].get() else ([who] if who else [])
            if not targets:
                messagebox.showinfo("Cost of living", "Select a character or add the party first.", parent=win); return
            c = cost()
            for name in targets:
                dt.purse_add(self.dt_store, name, -c, f"Cost of living: {v['standard'].get()}, {v['count'].get()} {v['unit'].get()}(s)")
            win.destroy()
            self._dt_funds_changed(targets[0], f"Charged {dt.coin_text(c)} for {v['standard'].get().lower()} living to {', '.join(targets)}.")
        ttk.Button(win, text="Charge", command=ok).grid(row=6, column=1, sticky="e", padx=8, pady=8)
        self.df_living_win = (win, v, ok)

    # ----- Events
    def _dt_build_events(self, f):
        top = ttk.Frame(f); top.pack(fill="x", pady=6, padx=6)
        ttk.Label(top, text="Activity").pack(side="left")
        self.dv_activity = Combo(top, dt.ACTIVITIES, readonly=True, width=26); self.dv_activity.var.set("Earn Income"); self.dv_activity.pack(side="left", padx=4)
        ttk.Button(top, text="Roll an Event", command=self._dt_event_roll).pack(side="left", padx=4)
        ttk.Label(top, text="Chance a week has one").pack(side="left", padx=(16, 2))
        self.dv_chance = tk.StringVar(value=str(self.dt_store["settings"].get("event_chance", 25)))
        ttk.Spinbox(top, from_=0, to=100, textvariable=self.dv_chance, width=5).pack(side="left")
        ttk.Label(top, text="%").pack(side="left")
        ttk.Button(top, text="Does One Happen?", command=self._dt_event_chance).pack(side="left", padx=4)
        ttk.Label(f, foreground="#777", wraplength=1000, justify="left", text=(
            "GM Core leaves how often downtime events happen to you, so the chance is yours to set. The events come from the tables "
            "in Edit Tables: the GM Core ideas for each activity, the Treasure Vault crafting events, and Underhallow lines when "
            "that content is on.")).pack(anchor="w", padx=8)
        self.dv_out = tk.Text(f, height=10, wrap="word", state="disabled", font=("TkDefaultFont", 11), padx=8, pady=6)
        self.dv_out.pack(fill="both", expand=True, padx=6, pady=6)
        self.dv_last = None

    def _dt_event_show(self, text):
        self.dv_out.configure(state="normal"); self.dv_out.delete("1.0", "end"); self.dv_out.insert("end", text); self.dv_out.configure(state="disabled")

    def _dt_event_roll(self):
        e = dt.roll_event(self.story_registry, self.dv_activity.var.get(), packs=self._dt_packs())
        self.dv_last = e
        self._dt_event_show(f"{e['activity']}\n\n{e['text']}")
        dt.log_line(self.dt_store, f"Event ({e['activity']}): {e['text']}")
        self._dt_save()

    def _dt_event_chance(self):
        pct = self._int_or_none(str(self.dv_chance.get()))
        pct = 25 if pct is None else max(0, min(100, pct))
        self.dt_store["settings"]["event_chance"] = pct
        self._dt_save()
        yes = dt.event_happens(None, pct)
        self._dt_event_show(("Yes: an event happens this week.\n\nPress Roll an Event to pick one." if yes else "No event this week.") + f"\n\n({pct}% chance)")

    # ----- Identify and Learn
    def _dt_build_identify(self, f):
        il = ttk.LabelFrame(f, text="Identify Magic / Learn a Spell"); il.pack(side="left", fill="y", padx=6, pady=6)
        self.il = {k: tk.StringVar(value=v) for k, v in (("lvl", "1"), ("rank", "1"), ("rar", "common"))}
        rows = [("Item level (Identify)", ttk.Entry(il, textvariable=self.il["lvl"], width=6)),
                ("Spell rank (Learn / Identify spell)", ttk.Spinbox(il, from_=0, to=10, textvariable=self.il["rank"], width=5)),
                ("Rarity", ttk.Combobox(il, textvariable=self.il["rar"], values=dt.RARITIES, state="readonly", width=10))]
        for r, (lab, w) in enumerate(rows):
            ttk.Label(il, text=lab).grid(row=r, column=0, sticky="w", padx=4, pady=2); w.grid(row=r, column=1, sticky="w")
        ttk.Button(il, text="Calculate", command=self._il_calc).grid(row=3, column=1, sticky="w", pady=4)
        self.il_out = tk.StringVar(); ttk.Label(il, textvariable=self.il_out, wraplength=300, justify="left").grid(row=4, column=0, columnspan=2, sticky="w", padx=4)

    def _il_calc(self):
        lvl = self._int_or_none(self.il["lvl"].get()) or 0
        rank = max(0, min(10, self._int_or_none(self.il["rank"].get()) or 0))
        rar = self.il["rar"].get()
        self.il_out.set(f"Identify Magic (item level {lvl}): DC {dt.level_dc(lvl, rar)}.\n"
                        f"Identify / Learn a Spell (rank {rank}): DC {dt.spell_dc(max(rank, 1), rar)}. "
                        f"Learn a Spell costs {price_text(dt.LEARN_SPELL_COST[rank])} in materials.")

    def _builder_dialog(self):
        lvl = self._int_or_none(self.cf["level"].get())
        if lvl is None:
            messagebox.showwarning("Level", "Set a numeric level first."); return
        win = tk.Toplevel(self); win.title(f"Suggest stats for a level {lvl} creature")
        rows = [("perception", "Perception", TIERS5), ("ac", "AC", TIERS4), ("fort", "Fortitude", TIERS5),
                ("ref", "Reflex", TIERS5), ("will", "Will", TIERS5), ("hp", "HP", HP_TIERS),
                ("attack", "Strike attack", TIERS4), ("damage", "Strike damage", TIERS4),
                ("spell", "Spell DC/attack", ["None"] + SPELL_TIERS), ("skill", "Skills", TIERS4)]
        defaults = {"spell": "None", "fort": "High", "will": "Low", "attack": "High", "damage": "Moderate"}
        tv = {}
        for r, (k, label, opts) in enumerate(rows):
            ttk.Label(win, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=2)
            v = tk.StringVar(value=defaults.get(k, "Moderate"))
            ttk.Combobox(win, textvariable=v, values=opts, state="readonly", width=10).grid(row=r, column=1, padx=6)
            tv[k] = v
        preview = tk.StringVar()
        ttk.Label(win, textvariable=preview, justify="left", font=("TkFixedFont", 9)).grid(
            row=0, column=2, rowspan=len(rows), sticky="nw", padx=10)
        ttk.Label(win, text="Typical creature: one or two High/Extreme stats, one Low. "
                            "Tables are from GM Core; verify against your book.",
                  foreground="#777", wraplength=420).grid(row=len(rows), column=0, columnspan=3, padx=6, pady=4, sticky="w")

        def calc(*_):
            s = suggest(lvl, {k: v.get() for k, v in tv.items()})
            lines = [f"Perception {s['perception']:+d}", f"AC {s['ac']}",
                     f"Fort {s['fort']:+d}  Ref {s['ref']:+d}  Will {s['will']:+d}", f"HP {s['hp']}",
                     f"Strike {s['attack']:+d}, {s['damage']}"]
            if "spell_dc" in s:
                lines.append(f"Spell DC {s['spell_dc']}, attack {s['spell_attack']:+d}")
            lines.append(f"Skills at this tier: {s['skill']:+d}")
            preview.set("\n".join(lines))
            return s
        for v in tv.values():
            v.trace_add("write", calc)
        calc()

        def apply():
            s = calc()
            self.cf["perception"].set(f"{s['perception']:+d}"); self.cf["ac"].set(str(s["ac"]))
            for k in ("fort", "ref", "will"):
                self.cf[k].set(f"{s[k]:+d}")
            self.cf["hp"].set(str(s["hp"]))
            lines = [l for l in self.c_strikes.get("1.0", "end").splitlines() if l.strip()]
            if not lines:
                lines = [f"Strike | {s['attack']:+d} | {s['damage']} |  | "]
            else:
                new = []
                for l in lines:
                    p = [x.strip() for x in l.split("|")] + [""] * 5
                    dmg_rest = p[2].split(" ", 1)
                    dtype = dmg_rest[1] if len(dmg_rest) > 1 else ""
                    p[1] = f"{s['attack']:+d}"
                    p[2] = f"{s['damage']} {dtype}".strip()
                    new.append(" | ".join(p[:5]))
                lines = new
            self.c_strikes.delete("1.0", "end"); self.c_strikes.insert("1.0", "\n".join(lines))
            if "spell_dc" in s:
                sp = [l for l in self.c_spells.get("1.0", "end").splitlines() if l.strip()]
                head = f"DC {s['spell_dc']}, attack {s['spell_attack']:+d}"
                if sp:
                    first = sp[0].split(";", 1)
                    name = re.sub(r"\s*DC \d+.*$", "", first[0]).strip() or "Innate Spells"
                    sp[0] = f"{name} {head}" + (";" + first[1] if len(first) > 1 else "")
                else:
                    sp = [f"Innate Spells {head}; Rank 1: "]
                self.c_spells.delete("1.0", "end"); self.c_spells.insert("1.0", "\n".join(sp))
            win.destroy()
        ttk.Button(win, text="Apply to Form", command=apply).grid(row=len(rows) + 1, column=2, sticky="e", padx=6, pady=6)

    def _form(self, parent, fields):
        frm = ttk.Frame(parent); frm.pack(fill="x", padx=4, pady=4)
        vars_ = {}
        for r, (key, label) in enumerate(fields):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=1)
            v = tk.StringVar()
            if key == "rarity":
                ttk.Combobox(frm, textvariable=v, values=RARITIES, state="readonly", width=12).grid(row=r, column=1, sticky="w")
            else:
                ttk.Entry(frm, textvariable=v, width=40).grid(row=r, column=1, sticky="we")
            vars_[key] = v
        frm.columnconfigure(1, weight=1)
        return vars_

    @staticmethod
    def _int_or_none(s):
        s = s.strip()
        return int(s) if s.lstrip("-").isdigit() else None

    def _save_item(self):
        f = self.itf
        lvl = self._int_or_none(f["level"].get())
        if not f["name"].get().strip() or lvl is None:
            messagebox.showwarning("Missing", "Name and a numeric level are required."); return
        try:
            price = float(f["price_gp"].get() or 0)
        except ValueError:
            messagebox.showwarning("Price", "Price must be a number."); return
        cons = self.it_cons.get()
        it = Item(name=f["name"].get().strip(), level=lvl, rarity=f["rarity"].get() or "common",
                  traits=_split(f["traits"].get()), item_type="consumable" if cons else "equipment",
                  price_gp=price, consumable=cons, magical=True, source=f["source"].get().strip(),
                  notes=f["notes"].get().strip(), custom=True,
                  system="sf" if f["system"].get() == "Starfinder" else "pf")
        self.c_items = [x for x in self.c_items if x.name != it.name] + [it]
        storage.save_custom_items(self.c_items)
        self._refresh_custom()

    def _del_item(self):
        names = {self.itree.item(i, "text") for i in self.itree.selection()}
        self.c_items = [x for x in self.c_items if x.name not in names]
        storage.save_custom_items(self.c_items)
        self._refresh_custom()

    def _load_item(self):
        sel = self.itree.selection()
        if not sel:
            return
        it = next((x for x in self.c_items if x.name == self.itree.item(sel[0], "text")), None)
        if it:
            for k in ("name", "rarity", "source", "notes"):
                self.itf[k].set(getattr(it, k) or "")
            self.itf["level"].set(str(it.level)); self.itf["traits"].set(", ".join(it.traits))
            self.itf["price_gp"].set(f"{it.price_gp:g}"); self.it_cons.set(it.consumable)
            self.itf["system"].set(SYSTEM_NAMES.get(system_of(it), "Pathfinder"))

    def _refresh_custom(self):
        self.ctree.delete(*self.ctree.get_children())
        for c in sorted(self.c_creatures, key=lambda x: (x.level, x.name)):
            self.ctree.insert("", "end", text=c.name, values=(c.level,))
        self.itree.delete(*self.itree.get_children())
        for i in sorted(self.c_items, key=lambda x: (x.level, x.name)):
            self.itree.insert("", "end", text=i.name,
                              values=(i.level, "consumable" if i.consumable else "permanent", f"{i.price_gp:g}"))
        if hasattr(self, "status_var"):
            self._refresh_status()
        if hasattr(self, "sys_info"):
            self._refresh_sys_info()
        if hasattr(self, "vocab"):
            self._merge_custom_vocab()
            self._apply_vocab()


def main():
    App().mainloop()

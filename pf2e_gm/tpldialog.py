"""Windows for creature templates: pick one, set its options, preview the result, and keep your own.

TemplateDialog works on a copy. Nothing changes until Apply is pressed, and the caller decides where the new creature goes.
MyTemplatesWindow edits the templates you make yourself (they are stored in user_data/custom_templates.json).
"""
import tkinter as tk
import uuid
from tkinter import messagebox, ttk

from . import storage
from . import templates as tpl
from .statblock import custom_details, render


def _set_text(box, text):
    box.configure(state="normal")
    box.delete("1.0", "end")
    box.insert("end", text)
    box.configure(state="disabled")


class TemplateDialog(tk.Toplevel):
    """Apply a template to a copy of a creature. on_apply(result) is called with a templates.Result when Apply is pressed.
    make_view(parent) returns the read-only stat block viewer to use for the preview."""

    def __init__(self, app, creature, on_apply, make_view):
        super().__init__(app)
        self.app, self.creature, self.on_apply = app, creature, on_apply
        self.title(f"Apply a template to {creature.name}")
        self.geometry("1260x780")
        self.transient(app)
        self.result = None
        self.name_dirty = False
        self._quiet = False
        self.opt_vars, self.strike_vars = {}, {}
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=6)
        left, right = ttk.Frame(pane), ttk.Frame(pane)
        pane.add(left, weight=2)
        pane.add(right, weight=3)

        row = ttk.Frame(left); row.pack(fill="x", pady=(2, 4))
        ttk.Label(row, text="Template", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        self.tpl_var = tk.StringVar()
        self.tpl_combo = ttk.Combobox(row, textvariable=self.tpl_var, state="readonly", width=44)
        self.tpl_combo.pack(side="left", padx=6, fill="x", expand=True)
        self.summary = ttk.Label(left, wraplength=470, justify="left", foreground="#555")
        self.summary.pack(anchor="w", pady=(0, 6))
        self.opt_frame = ttk.LabelFrame(left, text="Options")
        self.opt_frame.pack(fill="x", pady=2)

        row = ttk.Frame(left); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Words").pack(side="left")
        self.mode_var = tk.StringVar(value=tpl.MODES.get(app.config_data.get("template_mode", "remaster"), tpl.MODES["remaster"]))
        mode = ttk.Combobox(row, textvariable=self.mode_var, values=list(tpl.MODES.values()), state="readonly", width=44)
        mode.pack(side="left", padx=6)
        mode.bind("<<ComboboxSelected>>", lambda e: self._refresh())
        row = ttk.Frame(left); row.pack(fill="x", pady=2)
        ttk.Label(row, text="New name").pack(side="left")
        self.name_var = tk.StringVar()
        ent = ttk.Entry(row, textvariable=self.name_var, width=48)
        ent.pack(side="left", padx=6, fill="x", expand=True)
        ent.bind("<KeyRelease>", self._name_typed)
        have = tpl.applied(creature)
        self.have_lbl = ttk.Label(left, foreground="#777", wraplength=470, justify="left",
                                  text=("Already has: " + ", ".join(t.get("label", "") for t in creature.stats.get("templates", [])
                                                                    if isinstance(t, dict)) + ". Another template stacks on top."
                                        if have else ""))
        self.have_lbl.pack(anchor="w")

        ttk.Label(left, text="What it changes", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(8, 0))
        self.log = tk.Text(left, height=11, wrap="word", state="disabled", font=("TkDefaultFont", 9))
        self.log.pack(fill="both", expand=True)
        ttk.Label(left, text="Check these", font=("TkDefaultFont", 10, "bold"), foreground="#9a5b00").pack(anchor="w", pady=(6, 0))
        self.warn = tk.Text(left, height=7, wrap="word", state="disabled", font=("TkDefaultFont", 9), foreground="#9a5b00")
        self.warn.pack(fill="both", expand=True)

        bar = ttk.Frame(left); bar.pack(fill="x", pady=6)
        ttk.Button(bar, text="My Templates...", command=self._my_templates).pack(side="left")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right", padx=2)
        self.apply_btn = ttk.Button(bar, text="Apply", command=self._apply)
        self.apply_btn.pack(side="right", padx=2)

        self.view = make_view(right)
        self.view.pack(fill="both", expand=True)

        self._load_catalog(select=app.config_data.get("template_last"))
        self.tpl_combo.bind("<<ComboboxSelected>>", lambda e: self._template_changed())
        self._template_changed()

    # ---- catalog and options
    def _load_catalog(self, select=None):
        self.items = tpl.catalog(self.app.my_templates)
        self.labels = {f"{i['label']}   ({i['source']})": i for i in self.items}
        self.tpl_combo["values"] = list(self.labels)
        pick = next((lab for lab, i in self.labels.items() if i["key"] == select), None)
        self.tpl_var.set(pick or next(iter(self.labels)))

    def _item(self):
        return self.labels.get(self.tpl_var.get()) or self.items[0]

    def _mode(self):
        return next((k for k, v in tpl.MODES.items() if v == self.mode_var.get()), "remaster")

    def _template_changed(self):
        item = self._item()
        self.summary.configure(text=item["summary"])
        self.name_dirty = False
        self._build_options(item)
        self._refresh()

    def _build_options(self, item):
        for w in self.opt_frame.winfo_children():
            w.destroy()
        self._quiet = True
        self.opt_vars, self.strike_vars = {}, {}
        if not item["options"]:
            ttk.Label(self.opt_frame, text="This template has no options.", foreground="#777").pack(anchor="w", padx=6, pady=4)
        for o in item["options"]:
            t = o["type"]
            if t == "check":
                v = tk.BooleanVar(value=bool(o.get("default")))
                ttk.Checkbutton(self.opt_frame, text=o["label"], variable=v).pack(anchor="w", padx=6, pady=2)
            elif t == "strikes":
                ttk.Label(self.opt_frame, text=o["label"]).pack(anchor="w", padx=6, pady=(4, 0))
                names = []
                for n in tpl.strike_names(self.creature):
                    if n not in names:
                        names.append(n)
                chosen = tpl.default_drain_strikes(tpl.parse_strikes(self.creature.stats.get("strikes", "")))
                if not names:
                    ttk.Label(self.opt_frame, text="This creature has no Strikes yet.", foreground="#777").pack(anchor="w", padx=12)
                for n in names:
                    sv = tk.BooleanVar(value=n in chosen)
                    sv.trace_add("write", lambda *a: self._refresh())
                    ttk.Checkbutton(self.opt_frame, text=n, variable=sv).pack(anchor="w", padx=18)
                    self.strike_vars[n] = sv
                continue
            else:
                v = tk.StringVar(value=str(o.get("default", "")))
                r = ttk.Frame(self.opt_frame); r.pack(fill="x", padx=6, pady=2)
                ttk.Label(r, text=o["label"], wraplength=300, justify="left").pack(side="left")
                if t == "choice":
                    ttk.Combobox(r, textvariable=v, values=o["choices"], state="normal" if o.get("free") else "readonly",
                                 width=24).pack(side="left", padx=6)
                else:
                    ttk.Entry(r, textvariable=v, width=30).pack(side="left", padx=6, fill="x", expand=True)
            v.trace_add("write", lambda *a: self._refresh())
            self.opt_vars[o["key"]] = v
        self._quiet = False

    def _options(self):
        out = {k: v.get() for k, v in self.opt_vars.items()}
        if self.strike_vars:
            out["strikes"] = [n for n, v in self.strike_vars.items() if v.get()]
        return out

    # ---- preview
    def _name_typed(self, event=None):
        self.name_dirty = True
        self._refresh()

    def _refresh(self):
        if self._quiet:
            return
        item = self._item()
        try:
            res = tpl.apply(self.creature, item["key"], self._options(), self._mode(),
                            name=self.name_var.get() if self.name_dirty else "", custom=self.app.my_templates)
        except tpl.TemplateError as e:
            self._fail(str(e)); return
        except Exception as e:                                   # a template should never crash the window
            self._fail(f"Couldn't build this: {type(e).__name__}: {e}"); return
        self.result = res
        if not self.name_dirty:
            self.name_var.set(res.creature.name)
        _set_text(self.log, "\n".join("- " + ln for ln in res.log) or "Nothing changed.")
        _set_text(self.warn, "\n".join("- " + w for w in res.warns) or "Nothing flagged.")
        try:
            self.view.show(render(custom_details(res.creature)))
        except Exception as e:
            self.view.show_message(f"The result couldn't be drawn: {type(e).__name__}: {e}")
        self.apply_btn.state(["!disabled"])

    def _fail(self, message):
        self.result = None
        _set_text(self.log, message)
        _set_text(self.warn, "")
        self.view.show_message(message)
        self.apply_btn.state(["disabled"])

    # ---- buttons
    def _my_templates(self):
        MyTemplatesWindow(self.app, parent=self, on_change=self._catalog_changed)

    def _catalog_changed(self):
        self._load_catalog(select=self._item()["key"])
        self._template_changed()

    def _apply(self):
        res = self.result
        if res is None:
            return
        self.app.config_data["template_mode"] = self._mode()
        self.app.config_data["template_last"] = self._item()["key"]
        storage.save("config", self.app.config_data)
        self.destroy()
        self.on_apply(res)


class MyTemplatesWindow(tk.Toplevel):
    """Build and keep your own templates: the same kinds of changes the built-in ones make, with the numbers you choose."""
    NUMBERS = [("level", "Level change"), ("hp", "HP change"), ("ac", "AC bonus"), ("attack", "Attack bonus"), ("dc", "DC bonus"),
               ("saves", "Saves bonus"), ("skills", "Skills bonus"), ("damage", "Strike damage bonus")]
    LINES = [("traits", "Traits to add", "undead, spirit"), ("languages", "Languages to add", "Necril"),
             ("senses", "Senses to add", "darkvision, scent (imprecise) 30 feet"), ("immunities", "Immunities to add", "fire, poison"),
             ("weaknesses", "Weaknesses to add", "cold iron 5, vitality 5"),
             ("resistances", "Resistances to add", "physical 5 (except silver)"),
             ("speed", "Speeds to add", "fly 30 feet (replaces a Speed of the same kind)")]
    BOXES = [("strikes", "Strikes to add (one per line: Name | +bonus | damage | traits | effects)", 3),
             ("abilities", "Abilities to add (one per line: Name [2] (traits): rules text)", 5),
             ("spells", "Spells to add (one per line: Divine Innate Spells DC 20; Rank 2: Darkness (x1))", 2),
             ("notes", "Notes (shown in the list of changes)", 2)]

    def __init__(self, app, parent=None, on_change=None):
        super().__init__(parent or app)
        self.app, self.on_change = app, on_change
        self.title("My templates")
        self.geometry("980x720")
        self.transient(parent or app)
        self.current = None
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=6)
        left, right = ttk.Frame(pane), ttk.Frame(pane)
        pane.add(left, weight=1)
        pane.add(right, weight=4)
        self.tree = ttk.Treeview(left, show="tree", height=18)
        self.tree.column("#0", width=210)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._pick())
        bb = ttk.Frame(left); bb.pack(fill="x", pady=4)
        ttk.Button(bb, text="New", command=self._new).pack(side="left", padx=2)
        ttk.Button(bb, text="Delete", command=self._delete).pack(side="left", padx=2)
        ttk.Label(left, foreground="#666", wraplength=220, justify="left", text=(
            "Your templates appear in the Apply a template list after the built-in ones. Every field is optional. "
            "Numbers are plain bonuses and penalties; for level-based numbers, make one template per tier.")).pack(anchor="w", pady=6)

        self.vars = {k: tk.StringVar() for k in ("name", "summary", *[n for n, _ in self.NUMBERS], *[n for n, _, _ in self.LINES])}
        grid = ttk.Frame(right); grid.pack(fill="x")
        ttk.Label(grid, text="Name").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(grid, textvariable=self.vars["name"], width=34).grid(row=0, column=1, sticky="w")
        ttk.Label(grid, text="What it does").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(grid, textvariable=self.vars["summary"], width=80).grid(row=1, column=1, columnspan=7, sticky="w")
        for i, (key, label) in enumerate(self.NUMBERS):
            r, c = divmod(i, 4)
            ttk.Label(grid, text=label).grid(row=2 + r, column=c * 2, sticky="w", padx=(0 if c == 0 else 12, 4), pady=2)
            ttk.Spinbox(grid, from_=-50, to=400, textvariable=self.vars[key], width=6).grid(row=2 + r, column=c * 2 + 1, sticky="w")
        base = 4
        for i, (key, label, hint) in enumerate(self.LINES):
            ttk.Label(grid, text=label).grid(row=base + i, column=0, sticky="w", pady=2)
            ttk.Entry(grid, textvariable=self.vars[key], width=44).grid(row=base + i, column=1, columnspan=3, sticky="w")
            ttk.Label(grid, text=hint, foreground="#888").grid(row=base + i, column=4, columnspan=4, sticky="w", padx=8)
        self.boxes = {}
        for key, label, h in self.BOXES:
            ttk.Label(right, text=label).pack(anchor="w", pady=(6, 0))
            t = tk.Text(right, height=h, wrap="word")
            t.pack(fill="x")
            self.boxes[key] = t
        self.msg = tk.StringVar()
        ttk.Label(right, textvariable=self.msg, foreground="#1a5fb4").pack(anchor="w", pady=4)
        ttk.Button(right, text="Save Template", command=self._save).pack(anchor="e")
        self._fill_list()
        self._new()

    def _fill_list(self, select=None):
        self.tree.delete(*self.tree.get_children())
        for s in sorted(self.app.my_templates, key=lambda x: x.get("name", "").lower()):
            self.tree.insert("", "end", iid=s["id"], text=s.get("name") or "(unnamed)")
        if select and self.tree.exists(select):
            self.tree.selection_set(select)

    def _pick(self):
        sel = self.tree.selection()
        spec = next((s for s in self.app.my_templates if sel and s["id"] == sel[0]), None)
        if spec is not None:
            self._show(spec)

    def _show(self, spec):
        self.current = spec["id"] if spec.get("id") else None
        blank = tpl.blank_custom()
        for k, v in self.vars.items():
            v.set(str(spec.get(k, blank.get(k, ""))))
        for k, t in self.boxes.items():
            t.delete("1.0", "end")
            t.insert("1.0", spec.get(k, ""))
        self.msg.set("")

    def _new(self):
        self.current = None
        self._show(tpl.blank_custom())

    def _spec(self):
        spec = {k: v.get().strip() for k, v in self.vars.items()}
        for k, _ in self.NUMBERS:
            try:
                spec[k] = int(spec[k].replace("+", "") or 0)
            except ValueError:
                raise ValueError(f"{dict(self.NUMBERS)[k]} must be a whole number.")
        for k, t in self.boxes.items():
            spec[k] = t.get("1.0", "end").strip()
        return spec

    def _save(self):
        try:
            spec = self._spec()
        except ValueError as e:
            self.msg.set(str(e)); return
        if not spec["name"]:
            self.msg.set("Give the template a name."); return
        if self.current:
            spec["id"] = self.current
            self.app.my_templates = [spec if s["id"] == self.current else s for s in self.app.my_templates]
        else:
            spec["id"] = uuid.uuid4().hex[:8]
            self.app.my_templates.append(spec)
        self.current = spec["id"]
        storage.save("templates", self.app.my_templates)
        self._fill_list(select=spec["id"])
        self.msg.set(f"Saved '{spec['name']}'.")
        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self.current:
            return
        spec = next((s for s in self.app.my_templates if s["id"] == self.current), None)
        if spec and messagebox.askyesno("Delete template", f"Delete '{spec.get('name')}'? Creatures that already use it keep their changes.",
                                        parent=self):
            self.app.my_templates = [s for s in self.app.my_templates if s["id"] != self.current]
            storage.save("templates", self.app.my_templates)
            self._new()
            self._fill_list()
            if self.on_change:
                self.on_change()

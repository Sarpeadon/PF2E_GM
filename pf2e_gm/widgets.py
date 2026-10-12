"""Reusable widgets: editable dropdowns, and the panel the GM Tools generators share. Every dropdown is editable: pick from
the list or type anything."""
import random
import tkinter as tk
from tkinter import messagebox, ttk

from . import gmtools as gt

ANY = "(any)"


class Combo(ttk.Combobox):
    """Editable dropdown that filters its list as you type.

    values_key names a vocabulary list so the app can refresh choices after data loads.
    """

    def __init__(self, master, values=(), values_key=None, textvariable=None, width=22, readonly=False,
                 any_option=False, **kw):
        self.var = textvariable or tk.StringVar()
        super().__init__(master, textvariable=self.var, width=width,
                         state="readonly" if readonly else "normal", **kw)
        self.values_key = values_key
        self.any_option = any_option
        self.all_values = []
        self.set_values(values)
        if not readonly:
            self.bind("<KeyRelease>", self._filter)
        if any_option and not self.var.get():
            self.var.set(ANY)

    def set_values(self, values):
        self.all_values = ([ANY] if self.any_option else []) + list(values)
        self["values"] = self.all_values[:400]

    def _filter(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        text = self.var.get().lower().strip()
        vals = [v for v in self.all_values if text in v.lower()] if text else self.all_values
        self["values"] = vals[:400]

    def value(self):
        v = self.var.get().strip()
        return "" if v == ANY else v


class MultiField(ttk.Frame):
    """A comma-separated text field with a dropdown + Add button (and an optional value box).

    The text field stays editable, so values can be typed, reordered, or removed by hand.
    fmt(choice, value) builds the text that gets appended (e.g. "fire 5", "Stealth +13").
    """

    def __init__(self, master, values=(), values_key=None, value_label=None, fmt=None, width=30, combo_width=18):
        super().__init__(master)
        self.text = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.text, width=width)
        self.entry.grid(row=0, column=0, sticky="we")
        self.combo = Combo(self, values, values_key=values_key, width=combo_width)
        self.combo.grid(row=0, column=1, padx=(4, 0))
        col = 2
        self.val = None
        if value_label:
            ttk.Label(self, text=value_label).grid(row=0, column=col, padx=(4, 0)); col += 1
            self.val = tk.StringVar()
            e = ttk.Entry(self, textvariable=self.val, width=6)
            e.grid(row=0, column=col); col += 1
            e.bind("<Return>", lambda ev: self.add())
        ttk.Button(self, text="Add", width=5, command=self.add).grid(row=0, column=col, padx=(4, 0))
        self.combo.bind("<Return>", lambda ev: self.add())
        self.combo.bind("<<ComboboxSelected>>", lambda ev: None if self.val is not None else self.add())
        self.columnconfigure(0, weight=1)
        self.fmt = fmt or (lambda choice, value: f"{choice} {value}".strip())

    def add(self):
        choice = self.combo.value()
        if not choice:
            return
        item = self.fmt(choice, self.val.get().strip() if self.val else "")
        items = self.items()
        if item.lower() not in {i.lower() for i in items}:
            items.append(item)
        self.text.set(", ".join(items))
        self.combo.var.set("")
        if self.val is not None:
            self.val.set("")

    def items(self):
        return [t.strip() for t in self.text.get().split(",") if t.strip()]

    def get(self):
        return self.text.get().strip()

    def set(self, value):
        self.text.set(value if isinstance(value, str) else ", ".join(value or []))

    @property
    def values_key(self):
        return self.combo.values_key

    def set_values(self, values):
        self.combo.set_values(values)


class ToolPanel(ttk.Frame):
    """One GM Tools generator (job board, salvage, hazards...): its options, Generate / Reroll / Lock / Remove, a GM and a Player
    view, and Copy / Export / Add to Notebook. spec is a tool dictionary from gmtools.specs().

    What the panel asks of the host (your App); every one is optional:
      party_level(), party_size()               defaults for the level and size boxes
      gm_pages()                                the Notebook's pages, for the place and faction dropdowns
      gm_add_page(title, page_type, body, tags) adds a Notebook page (this is the Add to Notebook button)
      gm_session_source()                       the combat log and ledger lines for the Session Recap
      gm_prefs(tool) / gm_remember(tool, d)     the options you used last time
      open_story_tables()                       the Edit Tables window
    """

    def __init__(self, parent, host, spec):
        super().__init__(parent)
        self.host, self.spec = host, spec
        self.rng = random.Random()
        self.result = None
        self.shown = None                                   # index of the row in the detail box, or -1 for the whole result
        self.vars, self.boxes, self.combos = {}, {}, {}
        self.audience = tk.StringVar(value="GM")
        self.status = tk.StringVar(value="")
        self.import_var = tk.BooleanVar(value=False)
        self._build()
        self.refresh_choices()

    def _host(self, name, default=None, *args):
        fn = getattr(self.host, name, None)
        if callable(fn):
            try:
                return fn(*args)
            except Exception:
                return default
        return default

    # ------------------------------------------------------------------ layout
    def _build(self):
        ttk.Label(self, text=self.spec.get("intro", ""), foreground="#555", wraplength=1050, justify="left").pack(anchor="w", padx=8, pady=(6, 2))
        top = ttk.LabelFrame(self, text="What do you need?")
        top.pack(fill="x", padx=8, pady=4)
        saved = self._host("gm_prefs", {}, self.spec["key"]) or {}
        row_i, col = 0, 0
        for o in self.spec["options"]:
            default = saved.get(o["key"], o["default"])
            if o["key"] == "level":
                default = self._host("party_level", o["default"]) or o["default"]
            if o["key"] == "size":
                default = self._host("party_size", o["default"]) or o["default"]
            t = o["type"]
            if t == "multiline":
                ttk.Label(top, text=o["label"]).grid(row=row_i + 1, column=0, sticky="nw", padx=4, pady=2)
                box = tk.Text(top, height=9, width=90, wrap="word")
                box.grid(row=row_i + 1, column=1, columnspan=8, sticky="we", padx=4, pady=2)
                if default:
                    box.insert("1.0", str(default))
                self.boxes[o["key"]] = box
                ttk.Label(top, text=o.get("hint", ""), foreground="#777", wraplength=900, justify="left").grid(
                    row=row_i + 2, column=1, columnspan=8, sticky="w", padx=4)
                row_i += 2
                col = 0
                continue
            if col >= 4:
                row_i, col = row_i + 1, 0
            if t == "check":
                v = tk.BooleanVar(value=bool(default))
                ttk.Checkbutton(top, text=o["label"], variable=v).grid(row=row_i, column=col * 2, columnspan=2, sticky="w", padx=4, pady=2)
            else:
                ttk.Label(top, text=o["label"]).grid(row=row_i, column=col * 2, sticky="w", padx=(10 if col else 4, 2), pady=2)
                v = tk.StringVar(value=str(default if default is not None else ""))
                if t == "choice":
                    w = Combo(top, values=o["values"], textvariable=v, width=o.get("width", 14), readonly=not o.get("free"))
                    self.combos[o["key"]] = w
                    if o["key"] == "flavor":
                        w.bind("<<ComboboxSelected>>", lambda e: self.refresh_choices(), add="+")
                elif t == "int":
                    w = ttk.Spinbox(top, from_=-1, to=40, textvariable=v, width=o.get("width", 5))
                else:
                    w = ttk.Entry(top, textvariable=v, width=o.get("width", 20))
                w.grid(row=row_i, column=col * 2 + 1, sticky="w", padx=2, pady=2)
            self.vars[o["key"]] = v
            col += 1
        if self.spec["key"] == "recap" and callable(getattr(self.host, "gm_session_source", None)):
            ttk.Checkbutton(top, text="Add the app's combat log and today's treasure", variable=self.import_var).grid(
                row=row_i + 1, column=0, columnspan=4, sticky="w", padx=4)
        bar = ttk.Frame(self); bar.pack(fill="x", padx=8, pady=2)
        ttk.Button(bar, text="Generate", command=self.generate).pack(side="left", padx=2)
        if self.spec.get("multi"):
            ttk.Button(bar, text="Add One More", command=self.add_one).pack(side="left", padx=2)
        ttk.Button(bar, text="Reroll Selected", command=self.reroll).pack(side="left", padx=2)
        ttk.Button(bar, text="Lock / Unlock", command=self.toggle_lock).pack(side="left", padx=2)
        ttk.Button(bar, text="Remove", command=self.remove).pack(side="left", padx=2)
        ttk.Label(bar, text="  View").pack(side="left")
        for label in ("GM", "Player"):
            ttk.Radiobutton(bar, text=label, value=label, variable=self.audience, command=self._refresh).pack(side="left", padx=2)
        if callable(getattr(self.host, "open_story_tables", None)):
            ttk.Button(bar, text="Edit Tables...", command=self.host.open_story_tables).pack(side="right", padx=2)
        pane = ttk.PanedWindow(self, orient="horizontal"); pane.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.tree = ttk.Treeview(left, columns=("lock",), height=16, selectmode="browse")
        self.tree.heading("#0", text="Result")
        self.tree.heading("lock", text="Lock")
        self.tree.column("#0", width=340)
        self.tree.column("lock", width=44, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_selected())
        right = ttk.Frame(pane); pane.add(right, weight=2)
        self.detail = tk.Text(right, wrap="word", height=20, padx=6, pady=4)
        sb = ttk.Scrollbar(right, command=self.detail.yview); self.detail.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.detail.pack(fill="both", expand=True)
        edit = ttk.Frame(self); edit.pack(fill="x", padx=8)
        ttk.Button(edit, text="Apply Edit", command=self.apply_edit).pack(side="left", padx=2)
        ttk.Label(edit, text="Edit the text on the right, then press Apply Edit. Locked rows survive Generate.", foreground="#777").pack(side="left", padx=8)
        bot = ttk.Frame(self); bot.pack(fill="x", padx=8, pady=6)
        if callable(getattr(self.host, "gm_add_page", None)):
            ttk.Button(bot, text="Add to Notebook", command=self.to_notebook).pack(side="left", padx=2)
        ttk.Button(bot, text="Copy", command=self.copy).pack(side="left", padx=2)
        ttk.Button(bot, text="Copy as Markdown", command=self.copy_markdown).pack(side="left", padx=2)
        ttk.Button(bot, text="Export Markdown...", command=self.export).pack(side="left", padx=2)
        ttk.Label(bot, textvariable=self.status, foreground="#1a5fb4").pack(side="left", padx=10)

    def refresh_choices(self):
        """Refill the dropdowns that depend on the Setting and the Notebook (places, factions, ancestries, roles)."""
        flavor = self.vars["flavor"].get() if "flavor" in self.vars else "Hallowmead"
        pages = self._host("gm_pages", []) or []
        for o in self.spec["options"]:
            if o.get("source") and o["key"] in self.combos:
                try:
                    self.combos[o["key"]].set_values(gt.choice_values(o["source"], flavor, pages))
                except Exception:
                    self.combos[o["key"]].set_values([])

    def sync_party(self):
        """The party's level or size changed on the Party tab: follow it."""
        for key, fn in (("level", "party_level"), ("size", "party_size")):
            if key in self.vars:
                v = self._host(fn)
                if v:
                    self.vars[key].set(str(v))

    # ------------------------------------------------------------------ params
    def params(self):
        out = {}
        for o in self.spec["options"]:
            k = o["key"]
            out[k] = self.boxes[k].get("1.0", "end").strip() if o["type"] == "multiline" else self.vars[k].get()
        if self.import_var.get():
            out["extra"] = self._host("gm_session_source", "") or ""
        return gt.merge_params(self.spec["options"], out)

    def _remember(self, params):
        keep = {k: v for k, v in params.items() if k not in ("notes", "extra", "level", "size")}
        self._host("gm_remember", None, self.spec["key"], keep)

    # ------------------------------------------------------------------ actions
    def generate(self):
        params = self.params()
        try:
            res = self.spec["generate"](params, self.rng)
        except Exception as e:
            messagebox.showerror("Couldn't generate", f"{type(e).__name__}: {e}")
            return
        if self.result and self.result.get("tool") == res["tool"]:        # keep locked rows where they were
            for i, r in enumerate(self.result["rows"]):
                if r.get("locked"):
                    if i < len(res["rows"]):
                        res["rows"][i] = r
                    else:
                        res["rows"].append(r)
        self.result = res
        self._remember(params)
        self.status.set("")
        self._refresh()

    def add_one(self):
        if not self.result:
            self.generate(); return
        params = dict(self.params(), count=1)
        fresh = self.spec["generate"](params, self.rng)
        if self.spec["key"] == "jobs":
            new = fresh["rows"][0]
            n = sum(1 for r in self.result["rows"] if r.get("tag") == "job") + 1
            new["label"] = f"{n}. " + new["label"].split(". ", 1)[1]
            self.result["rows"].append(new)
        else:
            finds = [r for r in fresh["rows"] if str(r.get("kind", "")).startswith("find") or r.get("tag") == "item"]
            if not finds:
                return
            self.result["rows"].append(self.rng.choice(finds))
        self._refresh()

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except ValueError:
            return None

    def reroll(self):
        i = self._selected_index()
        if not self.result or i is None or i < 0:
            self.status.set("Select a row first."); return
        if self.result["rows"][i].get("locked"):
            self.status.set("That row is locked."); return
        gt.reroll_row(self.result, i, self.rng)
        self._refresh(select=i)

    def toggle_lock(self):
        i = self._selected_index()
        if not self.result or i is None or i < 0:
            return
        r = self.result["rows"][i]
        r["locked"] = not r.get("locked")
        self._refresh(select=i)

    def remove(self):
        i = self._selected_index()
        if not self.result or i is None or i < 0:
            return
        del self.result["rows"][i]
        self._refresh()

    def apply_edit(self):
        i = self.shown
        if self.result is None or i is None or i < 0:
            self.status.set("Select a row to edit."); return
        text = self.detail.get("1.0", "end").strip()
        r = self.result["rows"][i]
        if self.audience.get() == "Player" and r.get("player") is not None:
            r["player"] = text
        else:
            r["text"] = text
        r["locked"] = True                                  # an edited row is one you want to keep
        self.status.set("Edit applied, and the row is locked so Generate keeps it.")
        self._refresh(select=i)

    # ------------------------------------------------------------------ drawing
    def _aud(self):
        return "gm" if self.audience.get() == "GM" else "player"

    def _visible(self):
        if not self.result:
            return []
        gm = self.audience.get() == "GM"
        return [(i, r) for i, r in enumerate(self.result["rows"]) if gm or not r.get("gm")]

    def _refresh(self, select=None):
        self.tree.delete(*self.tree.get_children())
        if not self.result:
            self.shown = None
            self._set_detail("")
            return
        self.tree.insert("", "end", iid="-1", text=self.result["title"] + "  (whole result)", values=("",))
        for i, r in self._visible():
            label = r["label"] or "(note)"
            if r.get("gm") and self.audience.get() == "GM":
                label += "  [GM only]"
            self.tree.insert("", "end", iid=str(i), text=label, values=("yes" if r.get("locked") else "",))
        target = "-1" if select is None else str(select)
        if self.tree.exists(target):
            self.tree.selection_set(target)
        self._show_selected()

    def _set_detail(self, text):
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)

    def _show_selected(self):
        i = self._selected_index()
        if self.result is None or i is None:
            return
        self.shown = i
        if i == -1:
            self._set_detail(gt.render_text(self.result, self._aud()))
            return
        r = self.result["rows"][i]
        self._set_detail(r["text"] if self._aud() == "gm" or r.get("player") is None else r["player"])

    # ------------------------------------------------------------------ output
    def copy(self):
        if not self.result:
            return
        self.clipboard_clear(); self.clipboard_append(gt.render_text(self.result, self._aud()))
        self.status.set(f"Copied the {self.audience.get()} view.")

    def copy_markdown(self):
        if not self.result:
            return
        self.clipboard_clear(); self.clipboard_append(gt.render_markdown(self.result, self._aud()))
        self.status.set("Copied as Markdown.")

    def to_notebook(self):
        if not self.result:
            return
        try:
            self.host.gm_add_page(self.result["title"], self.spec.get("page_type", "Note"),
                                  gt.render_markdown(self.result, self._aud()), [self.spec["key"], "generated"])
            self.status.set("Added to the Notebook.")
        except Exception as e:
            messagebox.showerror("Notebook", f"Couldn't add the page: {e}")

    def export(self):
        if not self.result:
            return
        from tkinter import filedialog
        name = "".join(ch if ch.isalnum() or ch in " -_" else "" for ch in self.result["title"]).strip().replace(" ", "_") or "gm_tool"
        path = filedialog.asksaveasfilename(defaultextension=".md", initialfile=name + ".md", filetypes=[("Markdown", "*.md")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(gt.render_markdown(self.result, self._aud()))
            self.status.set(f"Saved {path}")
        except OSError as e:
            messagebox.showerror("Export", str(e))

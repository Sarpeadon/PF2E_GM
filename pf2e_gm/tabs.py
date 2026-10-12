"""Tab strips that are easy to tell apart at a glance.

The stock ttk.Notebook tab strip looks the same at every level and, on Windows, can't be colored. TabbedPane is a drop-in
for the parts of ttk.Notebook this app uses (add, select, tabs, tab, forget, index) with three looks:

  level 1  the main tabs: grouped, each group has its own color and a small heading, and the selected tab is filled
           with its group's color. A colored line under the strip shows which group you are in.
  level 2  section tabs inside a tab (Generate / Custom Item / My Items): dark filled "pills" on a neutral strip.
  level 3  views inside a section (Build / Card / History): plain text with an underline under the current one.

Pages are created with the TabbedPane as their parent, exactly as with a Notebook, and are shown in its content area.
"""
import tkinter as tk
from tkinter import ttk

FALLBACK_BG = "#f0f0f0"
# name -> color. The main tabs are grouped by what you do with them.
MAIN_GROUPS = {"Run the game": "#2b6cb0", "Make things": "#2f855a", "Campaign": "#805ad5", "Reference": "#718096"}
LEVEL2_ACTIVE, LEVEL2_IDLE = "#2d3748", "#e2e8f0"
LEVEL3_ACCENT = "#c05621"


def mix(color, other="#ffffff", amount=0.82):
    """Blend color toward other (amount = share of other). Used for the light tint of an unselected tab."""
    def rgb(c):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    a, b = rgb(color), rgb(other)
    return "#" + "".join(f"{round(x * (1 - amount) + y * amount):02x}" for x, y in zip(a, b))


def flow_rows(widths, avail, gap=10):
    """Split items of the given widths into rows that each fit in avail pixels. Returns lists of indexes. An item wider
    than the space gets a row of its own."""
    rows, cur, used = [], [], 0
    for i, w in enumerate(widths):
        need = w + (gap if cur else 0)
        if cur and used + need > avail:
            rows.append(cur)
            cur, used = [], 0
            need = w
        cur.append(i)
        used += need
    if cur:
        rows.append(cur)
    return rows


class TabbedPane(ttk.Frame):
    def __init__(self, master, level=1, groups=None, **kw):
        super().__init__(master)
        self.level = level if level in (1, 2, 3) else 2
        self.groups = dict(groups if groups is not None else (MAIN_GROUPS if self.level == 1 else {}))
        self._tabs = []                  # [{child, text, group, widget, label, line}]
        self._current = None
        self._group_frames = {}          # group -> {"frame", "row"}
        self._rows_sig = None
        self._bg = self._background()
        self._bar = tk.Frame(self, bg=self._bg)
        self._bar.pack(side="top", fill="x")
        self._rule = tk.Frame(self, height=3, bg=self._rule_color(None))
        self._rule.pack(side="top", fill="x")
        self._content = ttk.Frame(self)
        self._content.pack(side="top", fill="both", expand=True)
        if self.level == 1:
            try:
                self._bar.bind("<Configure>", self._reflow)
            except Exception:
                pass

    # ----- looks
    @staticmethod
    def _background():
        try:
            return ttk.Style().lookup("TFrame", "background") or FALLBACK_BG
        except Exception:
            return FALLBACK_BG

    def _font(self, selected):
        size = {1: 10, 2: 10, 3: 10}[self.level]
        return ("TkDefaultFont", size, "bold" if (selected or self.level == 2) else "normal")

    def _group_color(self, group):
        return self.groups.get(group) or "#4a5568"

    def _rule_color(self, tab):
        if self.level == 1:
            return self._group_color(tab["group"]) if tab else self._bg
        return LEVEL2_ACTIVE if self.level == 2 else self._bg

    def colors(self, tab, selected):
        """(background, foreground) for a tab's label."""
        if self.level == 1:
            col = self._group_color(tab["group"])
            return (col, "#ffffff") if selected else (mix(col), "#1a202c")
        if self.level == 2:
            return (LEVEL2_ACTIVE, "#ffffff") if selected else (LEVEL2_IDLE, "#1a202c")
        return (self._bg, LEVEL3_ACCENT if selected else "#4a5568")

    # ----- building the strip
    def _group_row(self, group):
        g = self._group_frames.get(group)
        if g is not None:
            return g["row"]
        frame = tk.Frame(self._bar, bg=self._bg)
        head = tk.Label(frame, text=str(group).upper(), bg=self._bg, fg=self._group_color(group),
                        font=("TkDefaultFont", 8, "bold"), anchor="w")
        head.pack(side="top", fill="x", padx=2)
        row = tk.Frame(frame, bg=self._bg)
        row.pack(side="top")
        self._group_frames[group] = {"frame": frame, "row": row, "head": head}
        self._place_groups()
        return row

    def _place_groups(self):
        names = [g for g in self.groups if g in self._group_frames] + \
                [g for g in self._group_frames if g not in self.groups]
        for col, name in enumerate(names):
            try:
                self._group_frames[name]["frame"].grid(row=0, column=col, sticky="nw", padx=(0, 12), pady=(2, 0))
            except Exception:
                pass

    def _make_label(self, parent, tab):
        pad = {1: (11, 5), 2: (14, 5), 3: (12, 4)}[self.level]
        holder = tk.Frame(parent, bg=self._bg)
        label = tk.Label(holder, text=tab["text"], padx=pad[0], pady=pad[1], cursor="hand2", bd=0)
        label.pack(side="top")
        line = None
        if self.level == 3:
            line = tk.Frame(holder, height=3, bg=self._bg)
            line.pack(side="top", fill="x")
        for w in (holder, label):
            w.bind("<Button-1>", lambda e, t=tab: self.select(t["child"]))
            w.bind("<Enter>", lambda e, t=tab: self._hover(t, True))
            w.bind("<Leave>", lambda e, t=tab: self._hover(t, False))
        tab.update(widget=holder, label=label, line=line)
        if self.level == 1:
            holder.pack(side="left", padx=(0, 2))
        elif self.level == 2:
            holder.pack(side="left", padx=(0, 3), pady=(3, 3))
        else:
            holder.pack(side="left", padx=(0, 4))

    def _hover(self, tab, inside):
        if tab is self._current:
            return
        bg, fg = self.colors(tab, False)
        if inside:
            bg = mix(bg, "#000000", 0.08) if self.level != 3 else self._bg
            fg = fg if self.level != 3 else "#1a202c"
        try:
            tab["label"].configure(bg=bg, fg=fg)
        except Exception:
            pass

    def _paint(self):
        for tab in self._tabs:
            sel = tab is self._current
            bg, fg = self.colors(tab, sel)
            try:
                tab["label"].configure(bg=bg, fg=fg, font=self._font(sel))
                if tab["line"] is not None:
                    tab["line"].configure(bg=LEVEL3_ACCENT if sel else self._bg)
            except Exception:
                pass
        try:
            self._rule.configure(bg=self._rule_color(self._current))
        except Exception:
            pass

    def _reflow(self, event=None):
        """Wrap the groups onto more rows when the window is too narrow for one."""
        names = [g for g in self._group_frames]
        try:
            widths = [int(self._group_frames[n]["frame"].winfo_reqwidth() or 0) + 12 for n in names]
            avail = int(getattr(event, "width", 0) or self._bar.winfo_width() or 0)
        except Exception:
            return
        if not widths or avail <= 1:
            return
        rows = flow_rows(widths, avail, 0)
        sig = (tuple(map(tuple, rows)),)
        if sig == self._rows_sig:
            return
        self._rows_sig = sig
        for r, idxs in enumerate(rows):
            for c, i in enumerate(idxs):
                try:
                    self._group_frames[names[i]]["frame"].grid(row=r, column=c, sticky="nw", padx=(0, 12), pady=(2, 0))
                except Exception:
                    pass

    # ----- the Notebook-like interface
    def add(self, child, text="", group=None, **_ignored):
        if any(t["child"] is child for t in self._tabs):
            return
        group = group if group is not None else (next(iter(self.groups), None) if self.level == 1 else None)
        tab = {"child": child, "text": text, "group": group, "widget": None, "label": None, "line": None}
        parent = self._group_row(group) if self.level == 1 else self._bar
        self._make_label(parent, tab)
        self._tabs.append(tab)
        if self._current is None:
            self.select(child)
        else:
            self._paint()

    def tabs(self):
        return [t["child"] for t in self._tabs]

    def _find(self, child):
        for t in self._tabs:
            if t["child"] is child or t["text"] == child:
                return t
        if isinstance(child, int) and 0 <= child < len(self._tabs):
            return self._tabs[child]
        return None

    def select(self, child=None):
        if child is None:
            return self._current["child"] if self._current else ""
        tab = self._find(child)
        if tab is None or tab is self._current:
            return None
        if self._current is not None:
            try:
                self._current["child"].pack_forget()
            except Exception:
                pass
        self._current = tab
        try:
            tab["child"].pack(in_=self._content, fill="both", expand=True)
        except Exception:
            pass
        self._paint()
        try:
            self.event_generate("<<NotebookTabChanged>>")
        except Exception:
            pass
        return None

    def index(self, what):
        if what == "current":
            return self._tabs.index(self._current) if self._current in self._tabs else -1
        if what == "end":
            return len(self._tabs)
        t = self._find(what)
        return self._tabs.index(t) if t is not None else -1

    def tab(self, child, option=None, **kw):
        t = self._find(child)
        if t is None:
            return None
        if "text" in kw:
            t["text"] = kw["text"]
            try:
                t["label"].configure(text=kw["text"])
            except Exception:
                pass
        if option == "text":
            return t["text"]
        return {"text": t["text"]}

    def forget(self, child):
        t = self._find(child)
        if t is None:
            return
        was = t is self._current
        self._tabs.remove(t)
        try:
            t["child"].pack_forget()
            t["widget"].destroy()
        except Exception:
            pass
        if was:
            self._current = None
            if self._tabs:
                self.select(self._tabs[0]["child"])

    def step(self, delta=1):
        """Next or previous tab (Ctrl+Tab and Ctrl+Shift+Tab on the main strip)."""
        if not self._tabs:
            return
        i = self.index("current")
        self.select(self._tabs[(i + delta) % len(self._tabs)]["child"])

    def bind_keys(self, root):
        """Ctrl+Tab and Ctrl+Shift+Tab move between the tabs, as they do on a Notebook."""
        try:
            root.bind_all("<Control-Tab>", lambda e: self.step(1))
            root.bind_all("<Control-Shift-Tab>", lambda e: self.step(-1))
            root.bind_all("<Control-ISO_Left_Tab>", lambda e: self.step(-1))
        except Exception:
            pass

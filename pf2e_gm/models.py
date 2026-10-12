from dataclasses import dataclass, field, asdict

SYSTEM_NAMES = {"pf": "Pathfinder", "sf": "Starfinder"}
SYSTEM_MODES = {"Pathfinder": {"pf"}, "Starfinder": {"sf"}, "Both": {"pf", "sf"}}


def system_of(x):
    return getattr(x, "system", "pf") or "pf"


@dataclass
class Creature:
    name: str
    level: int
    rarity: str = "common"
    traits: list = field(default_factory=list)
    size: str = ""
    hp: int | None = None
    ac: int | None = None
    source: str = ""
    notes: str = ""
    custom: bool = False
    stats: dict = field(default_factory=dict)   # custom creatures: full stat block fields
    adjust: str = ""                            # "", "elite", "weak"
    base_level: int | None = None               # level before Elite/Weak
    kind: str = "creature"                      # "creature" or "hazard"
    system: str = "pf"                          # "pf" (Pathfinder) or "sf" (Starfinder)
    complex: bool = False                       # hazards: complex hazards act in initiative

    @property
    def is_hazard(self):
        return self.kind == "hazard"

    @property
    def base_uid(self):
        lvl = self.base_level if self.base_level is not None else self.level
        prefix = "C" if self.custom else ("H" if self.kind == "hazard" else "F")
        if self.system == "sf" and not self.custom:
            prefix = "S" + prefix                   # SF/SH: keeps Starfinder separate from same-named PF entries
        return f"{prefix}|{self.name}|{lvl}"

    @property
    def uid(self):
        return self.base_uid + (f"|{self.adjust}" if self.adjust else "")

    @property
    def display_name(self):
        return {"elite": "Elite ", "weak": "Weak "}.get(self.adjust, "") + self.name

    def to_dict(self):
        return asdict(self)


@dataclass
class Item:
    name: str
    level: int
    rarity: str = "common"
    traits: list = field(default_factory=list)
    item_type: str = "equipment"
    price_gp: float = 0.0
    price_credits: float = 0.0                  # Starfinder prices are in credits
    consumable: bool = False
    magical: bool = True
    source: str = ""
    notes: str = ""
    custom: bool = False
    system: str = "pf"                          # "pf" (Pathfinder) or "sf" (Starfinder)

    @property
    def uid(self):
        prefix = "C" if self.custom else ("SF" if self.system == "sf" else "F")
        return f"{prefix}|{self.name}|{self.level}"

    def to_dict(self):
        return asdict(self)


def price_text(item_or_gp, credits=0.0):
    """'5 sp', '12 gp', '1,200 gp', '120 cr', 'free'."""
    if hasattr(item_or_gp, "price_gp"):
        gp, credits = item_or_gp.price_gp or 0, getattr(item_or_gp, "price_credits", 0) or 0
    else:
        gp = item_or_gp or 0
    bits = []
    if gp:
        if gp >= 1:
            bits.append(f"{gp:,.2f}".rstrip("0").rstrip(".") + " gp")
        elif gp >= 0.1:
            bits.append(f"{gp * 10:g} sp")
        else:
            bits.append(f"{gp * 100:g} cp")
    if credits:
        bits.append(f"{credits:,.0f} cr")
    return ", ".join(bits) or "-"

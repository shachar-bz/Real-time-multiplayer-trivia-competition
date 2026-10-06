"""The rides and paint colours a player can race with."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Ride:
    id: str
    label: str


@dataclass(frozen=True)
class Paint:
    id: str
    label: str
    hex: str


RIDES = {
    ride.id: ride
    for ride in (
        Ride("motorcycle", "Motorcycle"),
        Ride("monster_truck", "Monster Truck"),
        Ride("sports_car", "Sports Car"),
        Ride("superbike", "Superbike"),
    )
}

PAINTS = {
    paint.id: paint
    for paint in (
        Paint("red", "Red", "#bb1800"),
        Paint("pink", "Pink", "#ffb4a6"),
        Paint("yellow", "Yellow", "#e9c400"),
        Paint("blue", "Blue", "#00d2fd"),
        Paint("white", "White", "#e1e1ef"),
    )
}

DEFAULT_RIDE = "monster_truck"
DEFAULT_PAINT = "red"


def normalize_choice_key(value: object) -> str:
    """Turn "sportsCar", "Sports Car" or "sports-car" into "sports_car"."""
    key = str(value or "").strip()
    key = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    normalized = key.replace("-", "_").replace(" ", "_").lower()
    return "_".join(part for part in normalized.split("_") if part)


def normalize_ride(value: object) -> str:
    ride = normalize_choice_key(value)
    return ride if ride in RIDES else DEFAULT_RIDE


def normalize_paint(value: object) -> str:
    paint = normalize_choice_key(value)
    return paint if paint in PAINTS else DEFAULT_PAINT

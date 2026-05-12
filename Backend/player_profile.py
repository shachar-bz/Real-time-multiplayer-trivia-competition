import re


DEFAULT_RIDE = "monster_truck"
DEFAULT_PAINT = "red"

RIDE_CHOICES = {
    "motorcycle": {"id": "motorcycle", "label": "Motorcycle"},
    "monster_truck": {"id": "monster_truck", "label": "Monster Truck"},
    "sports_car": {"id": "sports_car", "label": "Sports Car"},
    "superbike": {"id": "superbike", "label": "Superbike"},
}

PAINT_CHOICES = {
    "red": {"id": "red", "label": "Red", "hex": "#bb1800"},
    "pink": {"id": "pink", "label": "Pink", "hex": "#ffb4a6"},
    "yellow": {"id": "yellow", "label": "Yellow", "hex": "#e9c400"},
    "blue": {"id": "blue", "label": "Blue", "hex": "#00d2fd"},
    "white": {"id": "white", "label": "White", "hex": "#e1e1ef"},
}


def normalize_choice_key(value):
    key = str(value or "").strip()
    key = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", key)
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    normalized = key.replace("-", "_").replace(" ", "_").lower()
    return "_".join(part for part in normalized.split("_") if part)


def normalize_ride(value):
    ride = normalize_choice_key(value)
    return ride if ride in RIDE_CHOICES else DEFAULT_RIDE


def normalize_paint(value):
    paint = normalize_choice_key(value)
    return paint if paint in PAINT_CHOICES else DEFAULT_PAINT


def profile_choices():
    return {
        "rides": list(RIDE_CHOICES.values()),
        "paints": list(PAINT_CHOICES.values()),
        "defaults": {
            "ride": DEFAULT_RIDE,
            "paint": DEFAULT_PAINT,
        },
    }


def player_profile(player):
    ride = normalize_ride(player.get("ride"))
    paint = normalize_paint(player.get("paint"))
    paint_choice = PAINT_CHOICES[paint]

    return {
        "id": player["sid"],
        "name": player["name"],
        "ride": ride,
        "rideLabel": RIDE_CHOICES[ride]["label"],
        "paint": paint,
        "paintLabel": paint_choice["label"],
        "paintHex": paint_choice["hex"],
        "isBot": bool(player.get("is_bot", False)),
    }

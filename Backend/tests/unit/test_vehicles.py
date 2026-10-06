import pytest

from trivia.domain.vehicles import (
    DEFAULT_PAINT,
    DEFAULT_RIDE,
    PAINTS,
    RIDES,
    normalize_paint,
    normalize_ride,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("sportsCar", "sports_car"),
        ("monster-truck", "monster_truck"),
        ("Sports Car", "sports_car"),
        ("  superbike ", "superbike"),
        ("MOTORCYCLE", "motorcycle"),
        ("spaceship", DEFAULT_RIDE),
        ("", DEFAULT_RIDE),
        (None, DEFAULT_RIDE),
        (42, DEFAULT_RIDE),
    ],
)
def test_normalize_ride(raw, expected):
    assert normalize_ride(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Blue", "blue"), ("white", "white"), ("purple", DEFAULT_PAINT), (None, DEFAULT_PAINT)],
)
def test_normalize_paint(raw, expected):
    assert normalize_paint(raw) == expected


def test_defaults_are_part_of_the_catalogue():
    assert DEFAULT_RIDE in RIDES
    assert DEFAULT_PAINT in PAINTS

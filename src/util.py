"""
Various utility routines.
"""

RANK_TO_COLOR = {
    "d": "#856C84",
    "d+": "#815880",
    "c-": "#6C417C",
    "c": "#67287B",
    "c+": "#522278",
    "b-": "#5949BE",
    "b": "#4357B5",
    "b+": "#4880B2",
    "a-": "#35AA8C",
    "a": "#3EA750",
    "a+": "#43b536",
    "s-": "#B79E2B",
    "s": "#d19e26",
    "s+": "#dbaf37",
    "ss": "#e39d3b",
    "u": "#c75c2e",
    "x": "#b852bf",
    "z": "#828282",
}


def is_valid_id(data: str) -> bool:
    """
    Check if a provided string is (probably) a MongoDB ID.

    References:
    - https://stackoverflow.com/questions/53847404/how-to-check-uuid-validity-in-python
    """
    if len(data) != 24:
        return False

    try:
        int(data, 16)
        return True
    except ValueError:
        return False

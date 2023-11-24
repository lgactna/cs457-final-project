"""
Various utility routines.
"""


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

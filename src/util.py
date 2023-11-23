"""
Various utility routines.
"""
import uuid

def is_valid_uuid(uuid: str) -> bool:
    """
    Check if a provided string is (probably) a UUID.
    
    References:
    - https://stackoverflow.com/questions/53847404/how-to-check-uuid-validity-in-python
    """
    try:
        uuid.UUID(str(uuid))
        return True
    except ValueError:
        return False
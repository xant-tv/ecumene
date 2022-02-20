import secrets

def generate_state():
    """Returns a 16-byte state."""
    return secrets.token_hex(nbytes=16)

def generate_local():
    """Returns an 8-byte hex."""
    return secrets.token_hex(nbytes=8)
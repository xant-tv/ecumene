import secrets

def generate_state():
    """Returns a 16-byte state."""
    return secrets.token_hex(nbytes=16)
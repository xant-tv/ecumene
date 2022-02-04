import time

def get_current_time():
    """Returns epoch time in milliseconds as an integer."""
    return int(round(time.time() * 1000))
import time
import humanize

def get_current_time():
    """Returns epoch time in milliseconds as an integer."""
    return int(round(time.time() * 1000))

def humanize_timedelta(delta):
    return humanize.naturaltime(delta)
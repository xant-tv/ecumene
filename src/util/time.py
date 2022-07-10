import time
import datetime
import humanize

def get_current_time():
    """Returns epoch time in milliseconds as an integer."""
    return int(round(time.time() * 1000))

def epoch_to_time(epoch_ms):
    """Returns python datetime from epoch in milliseconds."""
    return datetime.datetime.fromtimestamp(int(epoch_ms) / 1000)

def bnet_to_time(bnet_str):
    """Returns python datetime from Bungie API string."""
    return datetime.datetime.strptime(bnet_str, '%Y-%m-%dT%H:%M:%SZ')

def epoch_to_discord(epoch_ms, syntax='f'):
    """Returns a chat syntax timestring from epoch in milliseconds."""
    return f"<t:{int(epoch_ms / 1000)}:{syntax}>"

def time_to_discord(py_time, syntax='f'):
    """Returns a chat syntax timestring from python datetime."""
    return f"<t:{int(py_time.timestamp())}:{syntax}>"

def get_timedelta(tgt_dt):
    tz_info = tgt_dt.tzinfo
    return datetime.datetime.now(tz_info) - tgt_dt

def humanize_timedelta(delta):
    return humanize.naturaltime(delta)
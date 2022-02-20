import numpy as np
import pandas as pd

from util.time import get_current_time, humanize_timedelta

# Basic constructors and wrappers.
def make_empty_structure() -> pd.DataFrame:
    return pd.DataFrame()

def make_structure(data) -> pd.DataFrame: 
    return pd.DataFrame(data)

def append_frames(*frames) -> pd.DataFrame:
    return pd.concat(frames, axis=0, ignore_index=True)

# Processing functionality.
def format_clan_list(df):
    """Apply preprocess and format to clan list structure."""

    # Convert epoch timestamp into a datetime object.
    # Create a readable string for humans, too.
    df['last_online_dt'] = pd.to_datetime(df['last_online'], unit='s')
    df['last_online_str'] = df['last_online_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Compute last online as a relative time from current.
    df['last_online_rel'] = pd.to_datetime(get_current_time(), unit='ms') - df['last_online_dt']
    df['last_online_rel_str'] = df['last_online_rel'].apply(humanize_timedelta)

    # Use this to calculate status.
    df['status'] = np.where(df['last_online_rel'] > pd.Timedelta(30, 'd'), 'Inactive', 'Active')
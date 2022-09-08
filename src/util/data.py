import numpy as np
import pandas as pd

from util.time import get_current_time, humanize_timedelta

# Primitive helpers.
def chunks(lst, n):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Basic constructors and wrappers.
def make_empty_structure() -> pd.DataFrame:
    return pd.DataFrame()

def make_structure(data) -> pd.DataFrame: 
    return pd.DataFrame(data)

def append_frames(*frames) -> pd.DataFrame:
    return pd.concat(frames, axis=0, ignore_index=True)

def create_merge_id(df: pd.DataFrame):
    df['merge_id'] = np.where(df['bnet_id'].notnull(), df['bnet_id'], df['destiny_id'])

def coalesce_shared_ids(df: pd.DataFrame):
    df['bnet_id'] = np.where(df['bnet_id_api'].notnull(), df['bnet_id_api'], df['bnet_id_db'])
    df['destiny_id'] = np.where(df['destiny_id_api'].notnull(), df['destiny_id_api'], df['destiny_id_db'])

# Processing functionality.
def format_clan_list(df: pd.DataFrame):
    """Apply preprocess and format to clan list structure."""

    # Convert epoch timestamp into a datetime object.
    # Create a readable string for humans, too.
    df['last_online_dt'] = pd.to_datetime(df['last_online'], unit='s')
    df['last_online_str'] = df['last_online_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Do the same but for join dates.
    df['join_date_dt'] = pd.to_datetime(df['join_date'], format='%Y-%m-%dT%H:%M:%SZ')
    df['join_date_str'] = df['join_date_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Compute last online as a relative time from current.
    df['last_online_rel'] = pd.to_datetime(get_current_time(), unit='ms') - df['last_online_dt']
    df['last_online_rel_str'] = df['last_online_rel'].apply(humanize_timedelta)

    # Use this to calculate status.
    df['status'] = np.where(df['last_online_rel'] > pd.Timedelta(30, 'd'), 'Inactive', 'Active')

    # Sorting magic.
    df['bnet_id_num'] = pd.to_numeric(df['bnet_id'], errors='coerce')
    df.sort_values(by=['clan_id', 'bnet_id_num'], inplace=True)

# Processing functionality.
def format_audit_records(df: pd.DataFrame):
    """Apply preprocess and format to audit records structure."""

    # Convert epoch timestamp into a datetime object.
    # Create a readable string for humans, too.
    df['invoked_at_dt'] = pd.to_datetime(df['invoked_at'], unit='ms')
    df['invoked_at_str'] = df['invoked_at_dt'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Compute last online as a relative time from current.
    df['invoked_at_rel'] = pd.to_datetime(get_current_time(), unit='ms') - df['invoked_at_dt']
    df['invoked_at_rel_str'] = df['invoked_at_rel'].apply(humanize_timedelta)

    # Sorting magic.
    df['record_id_num'] = pd.to_numeric(df['record_id'], errors='coerce')
    df.sort_values(by=['invoked_at'], inplace=True)
      
    # Final output columns for the "pretty" output.
    output_cols = [
        'record_id',
        'command_id',
        'invoked_at_str', # Created by format_audit_records processing.
        'invoked_at_rel_str',
        'guild_id',
        'discord_id',
        'command_options',
        'status'
    ]
    output = df.loc[:, output_cols]
    return output
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

def coalesce_clan_list(df_api: pd.DataFrame, df_db: pd.DataFrame, empty_str):
    """Join all the various data structures to retain."""

    # Split out API data depending on which values are available.
    # Priority is to utilise Bungie identifier where present.
    df_api_bnet = df_api.loc[(df_api['bnet_id'].notnull()) & (df_api['bnet_id'] != empty_str)]
    df_api_destiny = df_api.loc[((df_api['bnet_id'].isnull()) | (df_api['bnet_id'] == empty_str)) & (df_api['destiny_id'].notnull()) & (df_api['destiny_id'] != empty_str)]

    # Handle merges seperately.
    # Note left merges to avoid duplication of records.
    df_bnet = df_api_bnet.merge(df_db, how='left', on=['bnet_id'], suffixes=['_api', '_db'])
    df_destiny = df_api_destiny.merge(df_db, how='left', on=['destiny_id'], suffixes=['_api', '_db'])

    # Handle separate merge suffixes, retaining API values where possible.
    df_bnet['destiny_id'] = np.where((df_bnet['destiny_id_api'].notnull()) & (df_bnet['destiny_id_api'] != empty_str), df_bnet['destiny_id_api'], df_bnet['destiny_id_db'])
    df_destiny['bnet_id'] = df_destiny['bnet_id_db'] # We can always replace as the null condition is checked when data is first split.
    df_bnet.drop(columns=['destiny_id_api', 'destiny_id_db'], inplace=True)
    df_destiny.drop(columns=['bnet_id_api', 'bnet_id_db'], inplace=True)

    # Rejoin data - this will lose users who have neither Destiny or Bungie identifiers.
    # Unsure if that would ever be possible.
    df = pd.concat([df_bnet, df_destiny])

    return df

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
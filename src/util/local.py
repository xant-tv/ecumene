import os
import csv
import json

TMP_ROOT = 'tmp'
LOC_ROOT = 'conf/{0}.json'

def file_path(fname):
    return os.path.join(TMP_ROOT, fname)

def delete_file(path):
    return os.remove(path)

def write_file(data, path):
    data.to_csv(path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)

def load_local(loc):
    with open(LOC_ROOT.format(str(loc))) as locfile:
        data = json.load(locfile)
    return data

def get_models():
    models = load_local('models').get('models')
    return models

def get_guild_ids():
    # This will force commands to be scoped within the specified guild.
    guild = os.getenv('DISCORD_GUILD_ID')
    if guild:
        return [int(guild)]
    return None

def get_system_role():
    role_name = os.getenv('DISCORD_SYSTEM_ROLE')
    if not role_name:
        role_name = 'Amiable' # Hardcode this for now.
    return role_name
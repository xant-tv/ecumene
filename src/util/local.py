import os
import json

TMP_ROOT = 'tmp'
LOC_ROOT = 'conf/{0}.json'

def file_path(fname):
    return os.path.join(TMP_ROOT, fname)

def delete_file(path):
    return os.remove(path)

def load_local(loc):
    with open(LOC_ROOT.format(str(loc))) as locfile:
        data = json.load(locfile)
    return data

def get_models():
    models = load_local('models').get('models')
    return models

def get_roles_permitted(paths):
    roles = load_local('roles').get('roles')
    permissions = set(paths)
    permitted = list()
    for role in roles:
        if set.intersection(permissions, set(role.get('permissions'))):
            permitted.append(role.get('id'))
    return permitted

def get_guild_ids():
    # This will force commands to be scoped within the specified guild.
    guild = os.getenv('DISCORD_GUILD_ID')
    if guild:
        return [int(guild)]
    return None
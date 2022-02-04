import json

LOC_ROOT = 'conf/{0}.json'

def load_local(loc):
    with open(LOC_ROOT.format(str(loc))) as locfile:
        data = json.load(locfile)
    return data

def get_user(id, source):
    members = load_local('members').get('members')
    for member in members:
        if member.get(source).get('id') == id:
            return member

def get_roles_permitted(command):
    roles = load_local('roles').get('roles')
    permitted = list()
    for role in roles:
        if command in role.get('permissions'):
            permitted.append(role.get('id'))
    return permitted

def get_models():
    models = load_local('models').get('models')
    return models
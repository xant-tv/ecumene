from sqlalchemy import select, update

from db.client import DatabaseService

def get_transaction(service: DatabaseService, state):
    table = service.retrieve_model('transactions')
    qry = (
        select(table).
            where(getattr(table.c, 'state') == state)
    )
    result = service.select(qry)
    return result

def update_transaction(service: DatabaseService, values, state):
    table = service.retrieve_model('transactions')
    qry = (
        update(table).
            where(getattr(table.c, 'state') == state).
            values(values)
    )
    result = service.execute(qry)
    return result
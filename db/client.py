import os
import logging
# import cx_Oracle

from sqlalchemy import MetaData, Table, Column
from sqlalchemy import Integer, String, Text, Float
from sqlalchemy import UniqueConstraint, ForeignKeyConstraint
from sqlalchemy import create_engine, inspect, insert

from util.local import get_models

COLUMN_JTYPE_TO_DTYPE = {
    'float': Float,
    'int': Integer, 
    'bigint': Integer, # For some reason, the native dialect maps this wrongly for Oracle.
    'string': String,
    'text': Text
}
CONSTRAINT_JTYPE_TO_DTYPE = {
    'unique': UniqueConstraint,
    'foreign': ForeignKeyConstraint
}

class DatabaseService():

    def __init__(self, enforce_schema=False):
        # Basic configuration from environment.
        self.log = logging.getLogger(f'{self.__module__}.{self.__class__.__name__}')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.sid = os.getenv('DB_SID')

        # Load configuration for models and build into metadata objects.
        self._models = get_models()
        self.metadata = MetaData()
        self.models = self._build_models_from_json_(self._models)

        # Store engine.
        # cx_Oracle.init_oracle_client(lib_dir=os.getenv('ORA_HOME'))
        self.engine = create_engine(f"oracle+cx_oracle://{self.user}:{self.password}@{self.sid}")  
        self.log.info(f'Connected as {self.user}@{self.sid}')
        if enforce_schema:
            self._enforce_schema_()

    def _map_column_(self, jtype, size=None, **kwargs):
        """Maps the column configuration into a column type."""
        if jtype not in COLUMN_JTYPE_TO_DTYPE.keys():
            raise NotImplementedError(f'Input type "{jtype}" is not supported')
        dtype = COLUMN_JTYPE_TO_DTYPE.get(jtype)
        if size:
            return dtype(size, **kwargs)
        return dtype

    def _map_constraint_(self, jtype):
        """Maps the constraint configuration into a constraint type."""
        if jtype not in CONSTRAINT_JTYPE_TO_DTYPE.keys():
            raise NotImplementedError(f'Constraint type "{jtype}" is not supported')
        dtype = CONSTRAINT_JTYPE_TO_DTYPE.get(jtype)
        return dtype

    def _build_constraint_(self, constraint):
        """Build constraints with switch-case logic based on type."""
        ctype = self._map_constraint_(constraint.get('type'))
        if not ctype:
            return
        elif ctype is UniqueConstraint:
            # Unique constraint takes an unpacked column sequence.
            # This is an annoying inconsistency to bear in mind.
            return ctype(
                *constraint.get('columns'),
                name=constraint.get('name')
            )
        elif ctype is ForeignKeyConstraint:
            # This reference column has to be fully qualified.
            # Have to append reference schema and table.
            ref_cols = [
                f"{self.user}.{constraint.get('reftable')}.{name}" 
                    for name in constraint.get('refcolumns')
            ]
            # Foreign key constraint takes a list of columns.
            return ctype(
                constraint.get('columns'),
                ref_cols,
                name=constraint.get('name')
            )
        return

    def _build_models_from_json_(self, models):
        """Overall loop to build models."""
        _tables = models.get('tables')
        tables = list()
        for table in _tables:

            # Build child objects to enable building parents.
            _columns = table.get('columns')
            columns = list()
            for column in _columns:
                columns.append(
                    Column(
                        column.get('name'),
                        # Builds the column type object.
                        self._map_column_(
                            column.get('type'),
                            column.get('size'),
                            **column.get('extra', dict())
                        ),
                        nullable=column.get('nullable', True),
                        primary_key=column.get('primary_key', False)
                    )
                )
            _constraints = table.get('constraints', list())
            constraints = list()
            for constraint in _constraints:
                constraints.append(
                    self._build_constraint_(constraint)
                )

            # Create and append table objects.
            tables.append(
                Table(
                    table.get('name'), 
                    self.metadata,
                    *columns,
                    *constraints,
                    schema=self.user
                )
            )
        return tables

    def _has_table_(self, table):
        """Convenience function to avoid calling inspect manually."""
        return inspect(self.engine).has_table(table, schema=self.user)
    
    def _enforce_schema_(self):
        """Check entities exist and create as needed."""
        for table in self.models:
            if self._has_table_(table.name):
                self.log.info(f'Table "{table}" already exists!')
                continue
            self.log.info(f'Creating "{table}" from model')
            table.create(self.engine)

    def retrieve_model(self, table):
        for model in self.models:
            if model.name == table:
                return model

    def execute(self, qry):
        """Execute query and fetch return from cursor."""
        with self.engine.begin() as connection:
            result = connection.execute(qry)
        return result

    # Only implement insert directly.
    # All other basic commands will have to act on query.
    def insert(self, table_name, values):
        """Insert into table model."""
        table = self.retrieve_model(table_name)
        qry = (
            insert(table).
                values(**values)
        )
        result = self.execute(qry)
        return result

    # Implement select to rapidly return result.
    # The table will need to be passed in here to obtain columns.
    def select(self, qry):
        """Select on column value match."""
        result = self.execute(qry)
        keys = result.keys()
        data = result.fetchall()
        records = dict(
            zip(
                keys, list(map(list, zip(*data)))
            )
        )
        return records
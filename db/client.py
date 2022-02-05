import os
import logging
# import cx_Oracle

from sqlalchemy import MetaData, Table, Column
from sqlalchemy import BigInteger, Integer, String, Text, Float
from sqlalchemy import UniqueConstraint, ForeignKeyConstraint
from sqlalchemy import create_engine, inspect, insert, update, delete, select

from util.local import get_models

COLUMN_JTYPE_TO_DTYPE = {
    'float': Float,
    'int': Integer,
    'bigint': BigInteger,
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

    def _retrieve_model_(self, table):
        for model in self.models:
            if model.name == table:
                return model

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

    def execute(self, sql):
        """Execute query and fetch return from cursor."""
        with self.engine.begin() as connection:
            result = connection.execute(sql)
        return result

    # Expect this function to have almost complete coverage of use cases.
    def insert(self, table_name, values):
        """Insert into table model."""
        table = self._retrieve_model_(table_name)
        qry = (
            insert(table).
                values(**values)
        )
        result = self.execute(qry)
        return result

    # Probably impossible to cover all necessary functionality here.
    def update(self, table_name, values, wcol, wval):
        """
        Demonstrative update function. 
        """
        table = self._retrieve_model_(table_name)
        qry = (
            update(table).
                where(getattr(table.c, wcol) == wval).
                values(**values)
        )
        result = self.execute(qry)
        return result

    def delete(self, table_name, dcol, dval):
        """Delete on column value match."""
        table = self._retrieve_model_(table_name)
        qry = (
            delete(table).
                where(getattr(table.c, dcol) == dval)
        )
        result = self.execute(qry)
        return result

    def select(self, table_name, wcol, wval):
        """Select on column value match."""
        table = self._retrieve_model_(table_name)
        qry = (
            select(table).
                where(getattr(table.c, wcol) == wval)
        )
        recs = self.execute(qry).fetchall()
        result = dict(
            zip(
                table.columns.keys(), list(map(list, zip(*recs)))
            )
        )
        return result
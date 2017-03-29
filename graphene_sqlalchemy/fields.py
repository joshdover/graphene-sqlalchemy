from functools import partial

from sqlalchemy.orm.query import Query

from graphene import Dynamic, Argument, Scalar, Field, NonNull
from graphene.relay import ConnectionField
from graphene.relay.connection import PageInfo
from graphql_relay.connection.arrayconnection import connection_from_list_slice

from .utils import get_query


class SQLAlchemyConnectionField(ConnectionField):
    generated_args = set()

    def __init__(self, type, *args, **kwargs):
        for (name, field) in type._meta.fields.items():
            if name == 'id':
                continue

            if isinstance(field, Field):
                field_type = field.type
                if isinstance(field_type, NonNull):
                    field_type = field_type.of_type
                self.generated_args.add(name)
                kwargs[name] = Argument(field_type)

        super(SQLAlchemyConnectionField, self).__init__(
            type,
            *args,
            **kwargs
        )

    @property
    def model(self):
        return self.type._meta.node._meta.model

    @classmethod
    def get_query(cls, model, context, info, args):
        q = get_query(model, context)

        for (key, value) in args.items():
            if key in cls.generated_args:
                column = getattr(model, key)
                q = q.filter(column == value)

        return q

    @classmethod
    def connection_resolver(cls, resolver, connection, model, root, args, context, info):
        iterable = resolver(root, args, context, info)
        if iterable is None:
            iterable = cls.get_query(model, context, info, args)
        if isinstance(iterable, Query):
            _len = iterable.count()
        else:
            _len = len(iterable)
        return connection_from_list_slice(
            iterable,
            args,
            slice_start=0,
            list_length=_len,
            list_slice_length=_len,
            connection_type=connection,
            pageinfo_type=PageInfo,
            edge_type=connection.Edge,
        )

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.model)

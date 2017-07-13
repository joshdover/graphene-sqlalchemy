from sqlalchemy.ext.declarative.api import DeclarativeMeta
from .optimize_resolve import optimize_resolve


def get_session(context):
    return context.get('session')


def get_query(model, context, info, args=None):
    query = getattr(model, 'query', None)
    if not query:
        session = get_session(context)
        if not session:
            raise Exception('A query in the model Base or a session in the schema is required for querying.\n'
                            'Read more http://graphene-python.org/docs/sqlalchemy/tips/#querying')
        query = session.query(model)
        query = optimize_resolve(query, model, info, args)
    return query


def is_mapped(obj):
    return isinstance(obj, DeclarativeMeta)

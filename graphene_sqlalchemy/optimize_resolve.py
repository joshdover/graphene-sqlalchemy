from sqlalchemy.orm import RelationshipProperty, joinedload
from graphql.language.ast import FragmentSpread


class RelationshipPathNode(object):
    def __init__(self, value, parent=None):
        if parent:
            parent.isLeaf = False
        self.value = value
        self.parent = parent
        self.isLeaf = True

    @property
    def path_from_root(self):
        path = []
        _build_path_from_root(self, path)
        return path


def _build_path_from_root(node, path):
    if node.parent:
        _build_path_from_root(node.parent, path)
    path.append(node.value)


def _get_ast_fields(ast, fragments):
    field_asts = ast.selection_set.selections

    for field_ast in field_asts:
        field_name = field_ast.name.value
        if isinstance(field_ast, FragmentSpread):
            for field in fragments[field_name].selection_set.selections:
                yield {'field': field.name.value,
                       'children': _get_ast_fields(field, fragments)
                       if hasattr(field, 'selection_set') and field.selection_set else []}

            continue

        yield {'field': field_name, 'children': _get_ast_fields(field_ast, fragments) if field_ast.selection_set else []}


def resolve_related(query, model, root, path, parent=None):
    field = root["field"].lower()  # normalize from graphql format to normal python format
    children = root["children"]
    # if the current model has the field being request, and the field is a relationship, add it to the query joins
    if hasattr(model, field) and isinstance(getattr(model, field).property, RelationshipProperty):
        parent = RelationshipPathNode(field, parent=parent)
        path.append(parent)
        model = getattr(model, field).property.mapper.class_

    for child in children:
        resolve_related(query, model, child, path, parent=parent)

    return path


def optimize_resolve(query, model, info, args):
    path = []
    for field_def in _get_ast_fields(info.field_asts[0], info.fragments):
        resolve_related(query, model, field_def, path)

    joins = [joinedload(".".join(p.path_from_root)) for p in path]
    return query.options(*joins)

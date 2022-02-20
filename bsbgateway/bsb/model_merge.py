__all__ = [
    "merge",
    "MergeError",
    "MergeUnknownTypeError",
    "MergeImmutableFieldError",
]
from typing import List, TypeVar
from functools import singledispatch
from pydantic import BaseModel
from .model import BsbCategory, BsbCommand, BsbModel, BsbType, I18nstr

class MergeError:
    """Base class for merge errors"""

class MergeUnknownTypeError(TypeError, MergeError):
    """Tried to merge objects of unsupported type."""

class MergeImmutableFieldError(ValueError, MergeError):
    """Merge would change fields that must not be changed."""
    def __init__(self, problems):
        super().__init__
        self.problems = problems

    def __str__(self):
        return "MergeError:\n" + "\n".join(self.problems)

def _prefix_with(prefix:str, strlist:List[str]) -> List[str]:
    return [prefix+item for item in strlist]

def _merge_field(a, b, fieldname, merge_log):
    a_val = getattr(a, fieldname)
    b_val = getattr(b, fieldname)
    if a_val != b_val:
        merge_log.append(f"{fieldname}: {a_val!r} -> {b_val!r}")
        setattr(a, fieldname, b_val)

@singledispatch
def merge(a, b) -> List[str]:
    """Merge ``b`` into ``a``. Return list of changes in textual form."""
    raise MergeUnknownTypeError(type(a).__name__)


@merge.register
def _(a:BsbModel, b:BsbModel) -> List[str]:
    merge_log:List[str] = []
    problems:List[str] = []
    # Merge types
    for key, b_type in b.types.items():
        if key not in a.types:
            # Just add type.
            a.types[key] = b_type.copy(deep=True)
            merge_log.append(f"types[{key}]: +")
        else:
            try:
                t_merge_log = merge(a.types[key], b.types[key])
            except MergeImmutableFieldError as e:
                problems.extend(_prefix_with(f"types[key].", e.problems))
            else:
                merge_log.extend(_prefix_with(f"types[{key}].", t_merge_log))

    # Merge categories themselves
    for key, b_cat in b.categories.items():
        if key not in a.categories:
            a.categories[key] = b_cat.copy(deep=True)
            merge_log.append(f"categories[{key}]: +")
        else:
            print("category exists", key)
            c_merge_log = merge(a.categories[key], b.categories[key])
            merge_log.extend(_prefix_with(f"categories[{key}].", c_merge_log))

    # Merge commands
    map_a = {
        # Problem: how to hande device-specific versions of same command
        cmd.parameter: (catkey, cmd)
        for catkey in a.categories
        for cmd in a.categories[catkey].commands
    }
    list_b = [
        (catkey, cmd)
        for catkey in b.categories
        for cmd in b.categories[catkey].commands
    ]
    print(f"merging {len(list_b)} cmds into {len(map_a)} existing cmds")
    for (b_catkey, b_cmd) in list_b:
        parameter = b_cmd.parameter
        # Ensure that command is in b's category
        if parameter not in map_a:
            # add
            a_catkey, a_cmd = b_catkey, b_cmd.copy(deep=True)
            merge_log.append(f'categories[{b_catkey}].commands: + {parameter}')
            a.categories[a_catkey].commands.append(a_cmd)
        else:
            a_catkey, a_cmd = map_a[parameter]
            if a_catkey != b_catkey:
                # move
                merge_log.append(f'categories[{a_catkey} -> {b_catkey}]: {parameter}')
                a.categories[a_catkey].commands.remove(a_cmd)
                a.categories[b_catkey].commands.append(a_cmd)
        # merge actual commands
        try:
            c_merge_log = merge(a_cmd, b_cmd)
        except MergeImmutableFieldError as e:
            problems.extend(_prefix_with(f"$command[{parameter}].", e.problems))
        else:
            merge_log.extend(_prefix_with(f"$command[{parameter}].", c_merge_log))

    if problems:
        raise MergeImmutableFieldError(problems)
    return merge_log

@merge.register
def _(a:BsbType, b:BsbType) -> List[str]:
    # Update unit + precision. Assert equality of all other fields.
    problems = []
    for property in ["name", "datatype", "factor", "payload_length", "payload_flags", "enable_byte"]:
        a_val = getattr(a, property)
        b_val = getattr(b, property)
        if a_val != b_val:
            problems.append(f"{property} cannot be changed. ({a_val!r} -> {b_val!r})")
    if problems:
        raise MergeImmutableFieldError(problems)
    merge_log:List[str] = []
    u_merge_log = merge(a.unit, b.unit)
    merge_log.extend(_prefix_with("unit.", u_merge_log))
    _merge_field(a, b, "precision", merge_log)
    return merge_log

@merge.register
def _(a:BsbCategory, b:BsbCategory) -> List[str]:
    merge_log:List[str] = []
    n_merge_log = merge(a.name, b.name)
    merge_log.extend(_prefix_with("name.", n_merge_log))
    for property in ["min", "max"]:
        _merge_field(a, b, property, merge_log)
    return merge_log

@merge.register
def _(a:BsbCommand, b:BsbCommand) -> List[str]:
    problems: List[str] = []
    for property in ["parameter"]:#, "device"]:
        a_val = getattr(a, property)
        b_val = getattr(b, property)
        if a_val != b_val:
            problems.append(f"{property} cannot be changed. ({a_val!r} -> {b_val!r})")
    if problems:
        raise MergeImmutableFieldError(problems)
    merge_log:List[str] = []
    # merge atomic properties
    a.command = a.command.upper()
    b.command = b.command.upper()

    for property in ["command", "typename", "flags", "min_value", "max_value"]:
        _merge_field(a, b, property, merge_log)
    merge_log.extend(
        _prefix_with("description.", merge(a.description, b.description))
    )
    for val, name in b.enum.items():
        if val not in a.enum:
            merge_log.append(f"enum[{val}]: +")
            a.enum[val] = name.copy(deep=True)
        else:
            merge_log.extend(
                _prefix_with(f"enum[{val}].", merge(a.enum[val], name))
            )
    return merge_log

@merge.register
def _(a:I18nstr, b:I18nstr) -> List[str]:
    merge_log = [
        f"{key}: {getattr(a, key)} -> {getattr(b, key)}"
        for key in b
        if key in a
        and getattr(a, key) != getattr(b, key)
    ] + [
        f"{key}: + {getattr(b, key)}"
        for key in b
        if key not in a
    ]
    a.__root__.update(b.__root__)
    return merge_log
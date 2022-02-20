__all__ = [
    "merge",
    "MergeError",
    "MergeUnknownTypeError",
    "MergeImmutableFieldError",
]
from typing import List, TypeVar
from functools import singledispatch
from pydantic import BaseModel
from .model import BsbModel, BsbType, I18nstr

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


@singledispatch
def merge(a, b) -> List[str]:
    """Merge ``b`` into ``a``. Return list of changes in textual form."""
    raise MergeUnknownTypeError(type(a).__name__)


@merge.register
def _(a:BsbModel, b:BsbModel) -> List[str]:
    merge_log:List[str] = []
    problems:List[str] = []
    # Merge types
    t1, t2 = a.types, b.types
    for key, t2_type in t2.items():
        if key not in t1:
            # Just add type.
            t1[key] = t2_type.copy(deep=True)
            merge_log.append(f"types[{key}]: +")
        else:
            try:
                t_merge_log = merge(t1[key], t2[key])
            except MergeImmutableFieldError as e:
                problems.extend(f"types[{key}]."+problem for problem in e.problems)
            else:
                merge_log.extend(f"types[{key}]."+entry for entry in t_merge_log)
    # TODO: Merge commands
    if problems:
        raise MergeImmutableFieldError(problems)
    return merge_log

@merge.register
def _(a:BsbType, b:BsbType) -> List[str]:
    # Update unit + precision. Assert equality of all other fields.
    problems = []
    merge_log:List[str] = []
    u_merge_log = merge(a.unit, b.unit)
    merge_log.extend("unit." + entry for entry in u_merge_log)
    if a.precision != b.precision:
        merge_log.append(f"precision: {a.precision} -> {b.precision}")
        a.precision = b.precision
    for property in ["name", "datatype", "factor", "payload_length", "payload_flags", "enable_byte"]:
        a_val = getattr(a, property)
        b_val = getattr(b, property)
        if a_val != b_val:
            problems.append(f"{property} cannot be changed. ({a_val!r} -> {b_val!r})")
    if problems:
        raise MergeImmutableFieldError(problems)
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
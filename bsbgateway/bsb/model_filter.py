"""Filter commands given a device id."""

__all__ = ["model_filter"]

import logging
import itertools as it
from .model import BsbModel, BsbCommand


def L():
    return logging.getLogger(__name__)


def model_filter(model: BsbModel, family: int, var: int):
    """Filters the model for commands applying to the specified device family
    and variant.

    Modifies command lists of the model.
    """

    def devices(cmd: BsbCommand):
        return [(d.family, d.var) for d in cmd.device]

    # Build list of allowed commands.
    # Generic commands first.
    generic = {
        (c.parameter, c.command.lower()): c
        for c in model.commands
        if (255, 255) in devices(c)
    }
    if family != 255:
        family_specific = {
            (c.parameter, c.command.lower()): c
            for c in model.commands
            if (family, 255) in devices(c)
        }
    else:
        family_specific = {}
    if var != 255:
        var_specific = {
            (c.parameter, c.command.lower()): c
            for c in model.commands
            if (family, var) in devices(c)
        }
    else:
        var_specific = {}
    for key in var_specific.keys():
        family_specific.pop(key, None)
        generic.pop(key, None)
    for key in family_specific.keys():
        generic.pop(key, None)
    L().info(
        "model_filter: identified %d generic, %d family-specific and %d variant-specific commands",
        len(generic),
        len(family_specific),
        len(var_specific),
    )
    filtered_uids = {
        cmd.uid
        for cmd in it.chain(
            generic.values(), family_specific.values(), var_specific.values()
        )
    }

    for cat in model.categories.values():
        cat.commands = [cmd for cmd in cat.commands if cmd.uid in filtered_uids]

    # reset cached props
    model.__dict__.pop("commands_by_parameter", None)
    model.__dict__.pop("commands_by_telegram_id", None)

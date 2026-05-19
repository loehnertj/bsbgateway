# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (c) 2026 Johannes Löhnert <loehnert.kde@gmx.de>

__all__ = [
    "BsbModel",
    "BsbCategory",
    "BsbCommand",
    "BsbType",
    "BsbDatatype",
    "BsbCommandFlags",
    "BsbDevice",
    "I18nstr",
    "EnumValue",
    "ScheduleEntry",
    "dedup_types",
    "as_json",
]
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import datetime as dt
import attr
import cattr
from cattr.gen import make_dict_unstructure_fn
import json
from enum import Enum
import locale
from copy import deepcopy

# Deszn:
# I18nstring needs special treatment
# BsbCommand.enum: convert str to int key
#
# BsbType: deduplicate
#   -- use dictionary
#   -- prefill with known types
#   -- inheritance:
#       BsbType --> BsbType<datatype> --> BsbType<name>
#       inherit or replace BsbField

def as_json(thing, indent=2):
    ud = cattr.unstructure(thing)
    return json.dumps(ud, indent=indent, ensure_ascii=False)

_TYPES_FILE = Path(__file__).with_name("bsb-types.json")

# Context variable for cattr hooks to access the current default language
_default_language_context = "DE"

# Context variable: pre-structured global enum dicts, keyed by name.
# Set in parse_obj before cattr.structure so BsbCommand hooks can resolve refs.
_global_enums_context: dict = {}

# Context variable: id(enum_dict) -> name, for identity-based lookup on unstructure.
# Set in _unstructure_bsb_model before delegating to sub-unstructuring.
_global_enum_id_to_name: dict = {}

def _load_default_types():
    """Returns dictionary of default BsbTypes, keyed by typename."""
    model = BsbModel.parse_file(str(_TYPES_FILE))
    return model.types

@attr.mutable
class BsbModel:
    version: str
    "e.g. 2.1.0"
    compiletime: str
    """string YYYYMMDDHHMMSS"""
    name: str = ""
    """Human-readable name of device"""
    categories: Dict[str, "BsbCategory"] = attr.Factory(dict)
    """Actual command entries by category"""
    enums: Dict[str, Dict[int, "I18nstr"]] = attr.Factory(dict)
    """Global named enums, reusable by commands"""
    types: Dict[str, "BsbType"] = attr.Factory(_load_default_types)
    """Known types"""
    default_language: str = "DE"
    """Default language code for I18nstr serialization (e.g. 'DE', 'EN')"""

    @property
    def commands(self):
        """Iterate all commands in all categories."""
        for cat in self.categories.values():
            yield from cat.commands

    @cached_property
    def fields(self) -> dict[int, "BsbCommand"]:
        """All commands by parameter number.
        
        Cached property!

        "fields" for compatibility with older code.
        """
        return {cmd.parameter: cmd for cmd in self.commands}

    @cached_property
    def commands_by_telegram_id(self):
        return {cmd.telegram_id: cmd for cmd in self.commands}
    
    @classmethod
    def parse_obj(cls, obj, link_types=True, default_language=None):
        """Parse object into BsbModel.
        
        Args:
            obj: Dictionary or JSON-like object to parse
            link_types: If True, link command types from typename to actual type instance
            default_language: Default language code for I18nstr serialization (e.g. 'DE', 'EN')
                            If not specified, extracted from obj['default_language'] or defaults to 'DE'
        """
        global _default_language_context, _global_enums_context
        
        # Extract default_language from object if present
        if default_language is None:
            default_language = obj.get("default_language", "DE")
        
        # Set context for hooks to access during structure phase
        old_context = _default_language_context
        _default_language_context = default_language

        # Pre-structure global enums so command hooks can resolve string refs.
        raw_enums = obj.get("enums", {})
        old_global_enums = _global_enums_context
        _global_enums_context = {
            name: {int(k): cattr.structure(v, I18nstr) for k, v in enum_dict.items()}
            for name, enum_dict in raw_enums.items()
        }
        
        try:
            model = cattr.structure(obj, cls)
            # Replace model.enums with the pre-structured shared objects so
            # identity checks on cmd.enum work correctly.
            model.enums = _global_enums_context
            # Store the default_language on the model instance
            model.default_language = default_language
            if link_types:
                model.link_types()
            model.resolve_enums()
            return model
        finally:
            _default_language_context = old_context
            _global_enums_context = old_global_enums

    @classmethod
    def parse_file(cls, filename, link_types=True, default_language=None):
        with open(filename, "r") as f:
            ud = json.load(f)
        ud.setdefault("name", Path(filename).stem)
        # Extract default_language from file if not specified
        if default_language is None and "default_language" in ud:
            default_language = ud["default_language"]
        return cls.parse_obj(ud, link_types=link_types, default_language=default_language)

    def json(self, indent=2):
        return as_json(self, indent=indent)

    def link_types(self):
        """Link command types from typename to actual type instance.

        Modifies the model in-place.

        If a command's typename is not found in the model's types,
        raises KeyError.
        """
        for cmd in self.commands:
            if cmd.typename:
                cmd.type = self.types[cmd.typename]
        return self

    def resolve_enums(self):
        """Replace command enum shared references from model.enums.

        For commands whose enum came from a string reference (stored in
        ``_enum_ref``), replaces ``cmd.enum`` with the shared dict object
        from ``self.enums`` and validates the reference exists.

        Modifies the model in-place.
        """
        for cmd in self.commands:
            ref = cmd._enum_ref
            if ref is not None:
                if ref not in self.enums:
                    raise KeyError(
                        f"Command {cmd.parameter!r}: enum references unknown global enum "
                        f"{ref!r}. Available: {list(self.enums.keys())}"
                    )
                cmd.enum = self.enums[ref]
        return self

@attr.mutable
class BsbCategory:
    name: "I18nstr"
    min: int
    """First parameter number"""

    max: int = 0
    """Last contained parameter"""

    commands: List["BsbCommand"] = attr.Factory(list)


@attr.mutable
class BsbCommand:
    """A single BSB parameter with its metadata and optional enum value map.

    **Deserialization** (``BsbModel.parse_obj`` / ``parse_file``):

    The ``"enum"`` field in the JSON may be either an inline dict or a string
    reference into the top-level ``"enums"`` map of the enclosing
    :class:`BsbModel`::

        # inline dict
        "enum": {"0": {"DE": "Aus"}, "1": {"DE": "An"}}

        # named reference — resolved to a shared dict object from BsbModel.enums
        "enum": "toggle1"

    When a reference is used, :attr:`_enum_ref` is set to the reference name
    and :attr:`enum` is assigned the *same object* stored in
    ``BsbModel.enums[name]``.  Unknown references raise :exc:`KeyError` (from
    :meth:`BsbModel.resolve_enums`).

    **Serialization** (``BsbModel.json`` / ``cattr.unstructure``):

    If :attr:`enum` is the *identical* object (by ``id``) as one of the values
    in the enclosing model's ``BsbModel.enums``, it is serialized as the
    reference string instead of an inline dict.  Inline enum dicts (or any
    dict that is not the same object as a global entry) are always serialized
    in full.
    """
    parameter: int
    """display number of parameter"""
    command: str
    """internal (hex) ID, e.g. '0x2D3D0574'"""

    description: "I18nstr"

    device: List["BsbDevice"] = attr.Factory(list)
    """Device(s) for which the command exists."""

    type: Optional["BsbType"] = None
    """Type instance, local copy.

    Should be shared from BsbModel.types.
    If ``None``, type should be looked up using ``typename``.

    To deduplicate & standardize the type, use `dedup_types()`.
    """

    typename: str = ""
    """Type reference, can be used to look up the type in BsbModel."""

    enum: Dict[int, "I18nstr"] = attr.Factory(dict)
    """Possible values for an enum field, mapped to their description"""

    _enum_ref: Optional[str] = attr.field(default=None, init=False)
    """Name of global enum this command's enum was loaded from, if any."""

    flags: List["BsbCommandFlags"] = attr.Factory(list)
    """Command flags, see there."""

    min_value: Optional[float] = None
    """Minimum allowed set value"""

    max_value: Optional[float] = None
    """Maximum allowed set value"""

    @classmethod
    def unknown(cls, telegram_id:int) -> "BsbCommand":
        """Returns a placeholder command for unknown commands."""
        return cls(
            parameter=0,
            command="0x%08X"%(telegram_id,),
            description=I18nstr({"EN": "unknown command"}),
            device=[],
            typename="RAW",
            type=BsbType.raw(),
        )

    @property
    def uid(self):
        """unique command id, tuple"""
        return self.parameter, self.command.lower(), self.device[0].family, self.device[0].var

    @property
    def disp_id(self) -> int:
        """Display ID (same as parameter)"""
        return self.parameter
    
    @property
    def disp_name(self) -> str:
        """Display name (same as description)"""
        return str(self.description)

    @property
    def unit(self) -> str:
        """Unit string, if any"""
        if self.type and self.type.unit:
            return str(self.type.unit)
        return ""

    @property
    def rw(self) -> bool:
        """Is command writeable?"""
        return BsbCommandFlags.Readonly not in self.flags

    @property
    def telegram_id(self) -> int:
        """Telegram ID (command as number)"""
        return int(self.command, 16)

    @property
    def short_description(o):
        return u'''{fmrw}{o.parameter:04d} {o.command} {o.description.de}{fmunit}'''.format(
            o=o,
            fmunit=u' [%s]'%o.type.unit if o.type and o.type.unit else u'',
            fmrw = u'*' if o.rw else u' ',
        )
    
    @property
    def long_description(o):
        extra = []
        if o.enum:
            extra.append("Possible values:")
            for key, val in o.enum.items():
                extra.append(f"  {key}: {val!s}")
        if o.min_value is not None or o.max_value is not None:
            extra.append(f"Allowed range: {o.min_value} ... {o.max_value}")
        if extra:
            extra.insert(0, "")
            extra = "\n".join(extra)
        else:
            extra = ""
        return u'''{o.short_description}
    {o.type_description}{fmnullable}. {extra}'''.format(
        o=o,
        fmnullable=u' or --' if o.type.nullable else u'',
        extra = extra
    )

    @property
    def type_description(o):
        if not (type:=o.type):
            return "Type: <unknown>"
        desc = u'Type: %s (%s), %d bytes' % (type.name, type.datatype.value, type.payload_length)
        if type.datatype == BsbDatatype.Vals:
            desc += u', factor %d' % type.factor
        return desc

class BsbCommandFlags(Enum):
    """Command flags.
    
    Note that in bsb-parameters.json, only ``Readonly``, ``OEM`` and ``NO_CMD`` occur.
    """
    # Does not occur in bsb-parameter.json, meaning unclear
    #Writeable = "WRITEABLE"
    Readonly = "READONLY"
    """Value can only be read"""
    Writeonly = "WRITEONLY"
    """Value can only be written"""
    OEM = "OEM"
    """Known OEM parameters are set to read-only by default"""
    NoCmd = "NO_CMD"
    """Not sure about this, seems to mean "ignore this command"""
    SpecialInf = "SPECIAL_INF"
    """
    Flag to distinguish between INF telegrams that reverse first two bytes
    (like room temperature) and those who don't (like outside temperature)
    """
    EEPROM = "EEPROM"
    """Whether value should be written to EEPROM"""
    SWCtlRonly = "SW_CTL_RONLY"
    """Software controlled read-only flag. I.e. can be unlocked in Software."""


@attr.mutable
class BsbType:
    unit: "I18nstr"
    name: str
    datatype: "BsbDatatype"
    """Underlying binary type."""

    payload_length: int
    """Payload length in bytes, without flag byte"""

    datatype_id: int = 0
    """Not unique! :-/"""
    factor: int = 1
    """Conversion factor display value -> stored value. Only for Vals datatype."""

    unsigned: bool = False
    """Is value signed or unsigned. Only for Vals datatype."""

    precision: int = 0
    """Recommended display precision (number of decimals)"""

    enable_byte: int = 0
    """Flag value to use for Set telegram, usually 1 or 6
    
    NB. 6 indicates a nullable value!
    """

    payload_flags: int = 0
    """
    32 = special decoding (custom function) required
    64 = variable length
    """

    @property
    def nullable(self):
        return (self.enable_byte == 6)

    @classmethod
    def raw(cls) -> "BsbType":
        """Returns a placeholder type for unknown types."""
        return cls(
            unit=I18nstr({"EN": ""}),
            name="RAW",
            datatype=BsbDatatype.Raw,
            payload_length=0,
        )


class BsbDatatype(Enum):
    Vals = "VALS"
    """Int with scaling factor. 
    Maps to float if factor != 1, else int."""
    Enum = "ENUM"
    """Enum value. Maps to int (0..255)"""
    Bits = "BITS"
    """Bitfield value. Maps to int (0..255)"""
    String = "STRN"
    """Text value."""
    Datetime = "DTTM"
    """Full datetime value.
    
    Maps to datetime.datetime."""
    DayMonth = "DDMM"
    """Day and month value.
    
    Maps to datetime.date with year 1900."""
    Time = "THMS"
    """hour/minutes/seconds value.
    Maps to datetime.time.
    """
    HourMinutes = "HHMM"
    """hour/minutes value.
    
    Maps to datetime.time with seconds=0.
    """
    TimeProgram = "TMPR"
    """Time program (on/off schedule).

    Maps to list of ScheduleEntry. Each schedule entry has .on and .off properties of type datetime.time; seconds = 0 .
    """
    # FIXME : ???
    Date = "DWHM"
    """Date value.

    Not supported yet."""
    Raw = "RAW"
    """Raw binary data. Default if we don't know a field."""


@attr.mutable
class BsbDevice:
    """Device type for which the command is valid"""
    family: int
    """byte, 255 = generic"""
    var: int
    """byte, 255 = generic"""

_PREFERED_LANGUAGE = ""

def set_prefered_language(lang: str=""):
    """Set the prefered language for I18nstr instances.

    lang: language code, e.g. "en", "de", "ru"

    Empty string resets to system locale.
    """
    global _PREFERED_LANGUAGE
    _PREFERED_LANGUAGE = lang.lower()

def _os_language():
    lang_country, encoding = locale.getdefaultlocale()
    lang, _, country = lang_country.partition('_')
    return lang


class I18nstr(dict):
    """Internationalized string.

    Use ``.<CountryCode>`` property to get string in a certain language.
    E.g. ``instance.ru`` returns the russian text.
    Use ``str(instance)`` to return the text in the default locale (as returned
    by ``locale.getdefaultlocale``).

    Fallback:

    * If requested locale is not available, return EN (english)
    * If english is also unavailable, return KEY
    * If also not available, return the first-best value
    * if also not available, return "<MISSING TEXT>"
    """

    def __getattr__(self, lang):
        if lang.startswith('__'):
            # Get out of the way.
            raise AttributeError(lang)
        lang = lang.upper()
        if lang in self:
            return self[lang]
        if "EN" in self:
            return self["EN"]
        if "KEY" in self:
            return self["KEY"]
        if len(self) > 0:
            return next(iter(self.values()))
        return "<MISSING TEXT>"

    def __str__(self):
        return self.__getattr__(_PREFERED_LANGUAGE or _os_language())

    def copy(self):
        return I18nstr(self.copy())

@attr.mutable
class EnumValue:
    "decoded value of an enum field"
    val: int
    "Numeric value"
    description: I18nstr
    "Human-readable interpretation of value"

@attr.mutable
class ScheduleEntry:
    """Time program (on/off schedule)"""
    on: dt.time
    off: dt.time


# Set up serialization / deserialization

# First, register I18nstr hooks so they're available when other hooks use them
def _structure_i18nstr(d, T):
    """Structure hook for I18nstr.
    
    Accepts both strings and dicts:
    - If input is a string, wrap it as {default_language: text}
    - If input is a dict, convert to I18nstr normally
    """
    if isinstance(d, str):
        # Wrap plain string with default language
        return T({_default_language_context: d})
    else:
        # Normal dict-to-I18nstr conversion
        return T(d)

def _unstructure_i18nstr(obj):
    """Unstructure hook for I18nstr.
    
    If the I18nstr contains only the default language as a single key,
    serialize as a plain string. Otherwise serialize as a dict.
    """
    if len(obj) == 1 and _default_language_context in obj:
        # Single entry with default language - return as string
        return obj[_default_language_context]
    else:
        # Multiple entries or not in default language - return as dict
        return dict(obj)

cattr.register_structure_hook(I18nstr, _structure_i18nstr)
cattr.register_unstructure_hook(I18nstr, _unstructure_i18nstr)

# Register hooks for BsbType first (no dependencies)
attr.resolve_types(BsbType)
cattr.register_unstructure_hook(BsbType, make_dict_unstructure_fn(BsbType, cattr.global_converter, _cattrs_omit_if_default=True))

# BsbCommand hooks next — must be registered before BsbCategory so that
# BsbCategory's generated unstructure fn picks up the right BsbCommand hook.
attr.resolve_types(BsbCommand)

# Structure hook for BsbCommand: resolve enum string references to shared dicts.
_base_structure_bsb_command = cattr.gen.make_dict_structure_fn(
    BsbCommand,
    cattr.global_converter,
    _enum_ref=cattr.override(omit=True),
)

def _structure_bsb_command(d, T):
    raw_enum = d.get("enum")
    enum_ref = None
    if isinstance(raw_enum, str):
        enum_ref = raw_enum
        # Remove string ref so the base structurer sees no enum; we assign below.
        d = dict(d)
        del d["enum"]
    cmd = _base_structure_bsb_command(d, T)
    if enum_ref is not None:
        cmd._enum_ref = enum_ref
        # Assign shared pre-structured dict if available; resolve_enums validates later.
        if enum_ref in _global_enums_context:
            cmd.enum = _global_enums_context[enum_ref]
    return cmd

cattr.register_structure_hook(BsbCommand, _structure_bsb_command)

# Unstructure hook for BsbCommand: emit enum as string ref when identity matches.
_base_unstructure_bsb_command = make_dict_unstructure_fn(
    BsbCommand,
    cattr.global_converter,
    _cattrs_omit_if_default=True,
    _enum_ref=cattr.override(omit=True),
)

def _unstructure_bsb_command(cmd):
    d = _base_unstructure_bsb_command(cmd)
    if cmd.enum:
        enum_name = _global_enum_id_to_name.get(id(cmd.enum))
        if enum_name is not None:
            d["enum"] = enum_name
    return d

cattr.register_unstructure_hook(BsbCommand, _unstructure_bsb_command)

# BsbCategory registered last so it sees the BsbCommand hooks above.
attr.resolve_types(BsbCategory)
cattr.register_unstructure_hook(BsbCategory, make_dict_unstructure_fn(BsbCategory, cattr.global_converter, _cattrs_omit_if_default=True))

# Resolve BsbModel types and register custom unstructure hook
attr.resolve_types(BsbModel)

def _unstructure_bsb_model(model):
    """Custom unstructure hook for BsbModel.
    
    Sets the context to the model's default_language before unstructuring
    to ensure that I18nstr fields are serialized correctly.
    Also builds the identity map used by _unstructure_bsb_command to emit
    global enum references as strings.
    """
    global _default_language_context, _global_enum_id_to_name
    old_context = _default_language_context
    old_id_map = _global_enum_id_to_name
    _default_language_context = model.default_language
    _global_enum_id_to_name = {id(v): k for k, v in model.enums.items()}

    try:
        # Use the standard unstructure function for BsbModel
        fn = make_dict_unstructure_fn(BsbModel, cattr.global_converter, _cattrs_omit_if_default=True)
        return fn(model)
    finally:
        _default_language_context = old_context
        _global_enum_id_to_name = old_id_map

cattr.register_unstructure_hook(BsbModel, _unstructure_bsb_model)

def dedup_types(model: BsbModel) -> BsbModel:
    """Deduplicates command types

    I.e., iterates all commands in the model;
    replaces each command's ``type`` property by a shared reference;
    ensures that no type metainformation was changed by that.

    The unique identification of each type is the tuple (.datatype, .name).

    Return model with ``.types`` property set.

    If ``.types`` is already set, just returns the model unchanged.

    """
    if model.types:
        return model

    all_types = {}

    for command in model.commands:
        dtype = command.type
        key = dtype.name
        if key not in all_types:
            all_types[key] = deepcopy(dtype)
        else:
            reference = all_types[key]
            if dtype != reference:
                refjson = attr.asdict(reference)
                dtjson = attr.asdict(dtype)
                raise ValueError(f"Command {command.parameter}: dtype differs from reference.\nreference:{refjson}\ninstance:{dtjson}")

    model = deepcopy(model)
    for command in model.commands:
        key = command.type.name
        command.type = all_types[key]
        command.typename = key
    model.types = all_types
    return model

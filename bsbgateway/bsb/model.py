__all__ = [
    "BsbModel",
    "BsbCategory",
    "BsbCommand",
    "BsbType",
    "BsbDatatype",
    "BsbCommandFlags",
    "BsbDevice",
    "I18nstr",
    "dedup_types",
    "as_json",
]
from typing import Dict, List, Tuple, Optional
#from pydantic import BaseModel
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

@attr.mutable
class BsbModel:
    version: str
    "e.g. 2.1.0"
    compiletime: str
    """string YYYYMMDDHHMMSS"""
    categories: Dict[str, "BsbCategory"] = {}
    """Actual command entries by category"""
    types: Dict[str, "BsbType"] = {}
    """Known types"""

    @property
    def commands(self):
        """Iterate all commands in all categories."""
        for cat in self.categories.values():
            yield from cat.commands

    @classmethod
    def parse_obj(cls, obj):
        return cattr.structure(obj, cls)

    @classmethod
    def parse_file(cls, filename):
        with open(filename, "r") as f:
            ud = json.load(f)
        return cls.parse_obj(ud)

    def json(self, indent=2):
        return as_json(self, indent=indent)

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
    parameter: int
    """display number of parameter"""
    command: str
    """internal (hex) ID, e.g. '0x2D3D0574'"""

    description: "I18nstr"

    device: List["BsbDevice"]
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

    flags: List["BsbCommandFlags"] = attr.Factory(list)
    """"""

    min_value: Optional[float] = None
    """Minimum allowed set value"""

    max_value: Optional[float] = None
    """Maximum allowed set value"""

    @property
    def uid(self):
        """unique command id, tuple"""
        return self.parameter, self.command.lower(), self.device[0].family, self.device[0].var

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


class BsbDatatype(Enum):
    Vals = "VALS"
    """Int with scaling factor"""
    Enum = "ENUM"
    Bits = "BITS"
    String = "STRN"
    Datetime = "DTTM"
    DayMonth = "DDMM"
    Time = "THMS"
    HourMinutes = "HHMM"
    TimeProgram = "TMPR"
    # FIXME : ???
    Date = "DWHM"


@attr.mutable
class BsbDevice:
    """Device type for which the command is valid"""
    family: int
    """byte, 255 = generic"""
    var: int
    """byte, 255 = generic"""


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
        return "<MISSING TEXT>"

    def __str__(self):
        return self.__getattr__(_os_language())

    def copy(self):
        return I18nstr(self.copy())

# Set up serialization / deserialization
#cattr.register_unstructure_hook(BsbCommand, lambda *args, **kwargs: 1/0)
# !!! Order is apparently important when registering the hooks (!?)
for T in [BsbType, BsbCommand, BsbCategory, BsbModel]:
    attr.resolve_types(T)
    cattr.register_unstructure_hook(T, make_dict_unstructure_fn(T, cattr.global_converter, _cattrs_omit_if_default=True))
cattr.register_structure_hook(I18nstr, lambda d, T: T(d))

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

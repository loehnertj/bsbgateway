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
]
from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel
from enum import Enum
import locale
#from .bsb_field import BsbField, BsbFieldChoice, BsbFieldInt8, BsbFieldInt16, BsbFieldInt32, BsbFieldTemperature, BsbFieldTime

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


class BsbModel(BaseModel):
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


class BsbCategory(BaseModel):
    name: "I18nstr"
    min: int
    """First parameter number"""
    max: int = 0
    """Last contained parameter"""
    commands: List["BsbCommand"]


class BsbCommand(BaseModel):
    parameter: int
    """display number of parameter"""
    command: str
    """internal (hex) ID, e.g. '0x2D3D0574'"""
    type: "BsbType" = None
    """Type instance, local copy.

    Should be shared from BsbModel.types.
    If ``None``, type should be looked up using ``typename``.

    To deduplicate & standardize the type, use `dedup_types()`.
    """

    typename: str = ""
    """Type reference, can be used to look up the type in BsbModel."""

    description: "I18nstr"
    enum: Dict[int, "I18nstr"] = {}
    """Possible values for an enum field, mapped to their description"""

    device: List["BsbDevice"]
    """Device(s) for which the command exists."""

    flags: List["BsbCommandFlags"] = []
    """"""

    min_value: Optional[float] = None
    """Minimum allowed set value"""

    max_value: Optional[float] = None
    """Maximum allowed set value"""

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


class BsbType(BaseModel):
    unit: "I18nstr"
    name: str
    datatype: "BsbDatatype"
    """Underlying binary type.
    """

    datatype_id: int = 0
    """Not unique! :-/"""
    factor: int = 1
    """Conversion factor display value -> stored value"""

    payload_length: int
    """Payload length in bytes, without flag byte"""

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

class BsbDatatype(Enum):
    Vals = "VALS"
    """Int with scaling factor"""
    Enum = "ENUM"
    Byte = "BYTE"
    Bits = "BITS"
    String = "STRN"
    Datetime = "DTTM"
    DayMonth = "DDMM"
    Time = "THMS"
    HourMinutes = "HHMM"
    TimeProgram = "TMPR"

class BsbDevice(BaseModel):
    """Device type for which the command is valid"""
    family: int
    """byte, 255 = generic"""
    var: int
    """byte, 255 = generic"""


def _os_language():
    lang_country, encoding = locale.getdefaultlocale()
    lang, _, country = lang_country.partition('_')
    return lang


class I18nstr(BaseModel):
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
    __root__: Dict[str, str]

    def __getattr__(self, lang):
        lang = lang.upper()
        d = self.__root__
        if lang in d:
            return d[lang]
        if "EN" in d:
            return d["EN"]
        if "KEY" in d:
            return d["KEY"]
        return "<MISSING TEXT>"

    def __str__(self):
        return self.__getattr__(_os_language())

    def __deepcopy__(self, memo):
        return I18nstr(__root__ = self.__root__.copy())

BsbModel.update_forward_refs()
BsbCategory.update_forward_refs()
BsbCommand.update_forward_refs()
BsbType.update_forward_refs()


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
            all_types[key] = dtype.copy(deep=True)
        else:
            reference = all_types[key]
            if dtype != reference:
                refjson = reference.json(exclude_unset=True)
                dtjson = dtype.json(exclude_unset=True)
                raise ValueError(f"Command {command.parameter}: dtype differs from reference.\nreference:{refjson}\ninstance:{dtjson}")

    mcopy = model.copy(deep=True)
    for command in mcopy.commands:
        key = command.type.name
        command.type = all_types[key]
        command.typename = key
    mcopy.types = all_types
    return mcopy

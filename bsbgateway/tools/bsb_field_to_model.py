"""Conversion of BSB Field(s) to model data"""
from multiprocessing.sharedctypes import Value
from typing import List
from datetime import datetime
from pathlib import Path

from ..bsb.model import BsbCommand, BsbCommandFlags, BsbDatatype, BsbDevice, BsbModel, BsbCategory, BsbType, I18nstr, as_json, dedup_types
from ..bsb.bsb_field import BsbField, BsbFieldChoice, BsbFieldInt8, BsbFieldInt16, BsbFieldInt32, BsbFieldTemperature, BsbFieldTime
from ..bsb.broetje_isr_plus import Group

def istr(text_de):
    """Create I18nStr instance from given text

    FIXME: At least set KEY property
    """
    return I18nstr({"DE": text_de})

def convert(groups: List[Group]) -> BsbModel: 
    now = datetime.now()
    categories = [
        convert_group(group)
        for group in groups
        # ignore "unsorted" category
        if group.disp_id != 0
    ]
    return BsbModel(
        version="2.1.0",
        compiletime = now.strftime("%Y%m%d%H%M%S"),
        categories = {
            str(cat.min): cat
            for cat in categories
        }
    )

def convert_group(group: Group) -> BsbCategory:
    # Skip fields with unknown type
    commands = [convert_field(f) for f in group.fields if type(f) is not BsbField]
    min_p = min(cmd.parameter for cmd in commands)
    max_p = max(cmd.parameter for cmd in commands)
    return BsbCategory(
        name=istr(group.name),
        min=min(group.disp_id, min_p),
        max=max_p,
        commands=commands
    )

def convert_field(field:BsbField) -> BsbCommand:
    flags: List[BsbCommandFlags] = []
    if not field.rw:
        flags.append(BsbCommandFlags.Readonly)

    kwargs = {}
    if isinstance(field, BsbFieldChoice):
        kwargs["enum"] = {
            key: istr(val)
            for key, val in field.choices.items()
        }
    if isinstance(field, BsbFieldInt8):
        if field.min != 0:
            kwargs["min_value"] = field.min
        if field.max != 255:
            kwargs["max_value"] = field.max
    if isinstance(field, BsbFieldInt16):
        if field.min != -0x8000:
            kwargs["min_value"] = field.min / field.divisor
        if field.max != 0x7fff:
            kwargs["max_value"] = field.max / field.divisor
    if isinstance(field, BsbFieldInt32):
        if field.min != -0x8000000:
            kwargs["min_value"] = field.min / field.divisor
        if field.max != 0x7fffffff:
            kwargs["max_value"] = field.max / field.divisor
    return BsbCommand(
        parameter=field.disp_id,
        command=f'0x{field.telegram_id:08x}',
        #type=convert_type(field),
        typename=find_typename(field),
        description=istr(field.disp_name),
        flags=flags,
        device = [BsbDevice(family=255,var=255)],
        **kwargs
    )

_REFERENCE_TYPES = {}
def load_reference_types(model: BsbModel):
    """Load type definitions from the model"""
    model = dedup_types(model)
    _REFERENCE_TYPES.update(model.types)

def find_typename(field:BsbField) -> str:
    if not _REFERENCE_TYPES:
        raise RuntimeError("Reference types were not loaded")
    types = _REFERENCE_TYPES
    enbl = 6 if field.nullable else 1
    if type(field) is BsbField:
        raise ValueError("Cannot convert field with anonymous type: %s" % (str(field),))
    if isinstance(field, BsbFieldChoice):
        if field.new_type_name:
            return types[field.new_type_name].name
        elif field.choices == ["Aus", "Ein"]:
            name = "ONOFF"
        elif field.choices == {0:"Aus", 255:"Ein"}:
            name = "ONOFF"
        else:
            name = "ENUM"
        assert enbl == 1
        return name
    elif isinstance(field, BsbFieldTemperature):
        return "TEMP"
    elif isinstance(field, (BsbFieldInt8,BsbFieldInt16,BsbFieldInt32)):
        if not field.new_type_name:
            raise ValueError("Need .tn property for int fields: %s" % str(field))
        t = types[field.new_type_name]
        if field.rw and t.enable_byte != enbl:
            print("%s field.nullable=%s enable_byte=%s"% (str(field), field.nullable, t.enable_byte))
        return t.name
    elif isinstance(field, BsbFieldTime):
        t = types["HOUR_MINUTES"] if field.nullable else types["HOUR_MINUTES_NN"]
        if field.rw and t.enable_byte != enbl:
            print("%s field.nullable=%s enable_byte=%s"% (str(field), field.nullable, t.enable_byte))
        return t.name
    else:
        raise ValueError("Cannot convert field: %s" % (str(field),))



def dump_types(model: BsbModel, filename: Path):
    types = dedup_types(model).types
    keys = list(types.keys())
    keys.sort(key=lambda tn: (tn[0].value, tn[1]))
    with filename.open("w") as f:
        for key in keys:
            f.write(str(key) + "\n    ")
            tt = as_json(types[key])
            tt = tt.replace("\n", "\n    ")
            f.write(tt + "\n\n")

if __name__ == "__main__":
    m = BsbModel.parse_file("bsb-types.json")
    load_reference_types(m)
    from ..bsb.broetje_isr_plus import groups
    m_convert = convert(groups)
    m_convert.types = {}
    json = as_json(m_convert)
    with Path("broetje_isr_plus.json").open("w") as f:
        f.write(json)


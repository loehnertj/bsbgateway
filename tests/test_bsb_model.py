import pytest
from bsbgateway.bsb import model
from bsbgateway.bsb.model_merge import merge
from copy import deepcopy
import cattr

@pytest.fixture
def testdata():
    return {
   "version": "2.1.0",
    "compiletime": "20211231181308",
    "categories": {
        "2200": {
            "name": {
                "KEY": "ENUM_CAT_22_TEXT",
                "DE": "Kessel",
                "EL": "Λέβητας",
                "EN": "Boiler",
                "FR": "Chaudière",
                "PL": "Kocioł",
                "RU": "Котёл",
            },
            "min": 2200,
            "max": 2682,
            "commands": [
                {
                    "parameter": 2200,
                    "command": "0x0D3D0949",
                    "type": { 
                        "unit": { "DE": "" },
                        "name": "ENUM",
                        "datatype": "ENUM",
                        "datatype_id": 1,
                        "factor": 1,
                        "payload_length": 1,
                        "precision": 0,
                        "enable_byte": 1,
                        "payload_flags": 0
                    },
                    "description": {
                        "KEY": "STR700_TEXT",
                        "EN": "Operating mode",
                        "RU": "Режим работы",
                        "SL": "Druh režimu vykurovacieho okruhu 1",
                        "SV": "Driftläge värmekrets 1",
                        "TR": "Isletme modu Isitma devresi1"
                    },
                    "enum": {
                        "0": {
                            "KEY": "ENUM2200_00_TEXT",
                            "DE": "Dauerbetrieb",
                        },
                        "1": {
                            "KEY": "ENUM700_01_TEXT",
                            "DE": "Automatik",
                        },
                        "2": {
                            "KEY": "ENUM2200_02_TEXT",
                        }
                    },
                    "flags": [ "OEM" ],
                    "device": [ { "family": 255, "var": 255 } ]
                },
                {
                    "parameter": 2203,
                    "command": "0x113D04D3",
                    "type": {
                        "unit": {
                            "KEY": "UNIT_DEG_TEXT",
                            "DE": "°C"
                        },
                        "name": "TEMP",
                        "datatype": "VALS",
                        "datatype_id": 0,
                        "factor": 64,
                        "payload_length": 2,
                        "precision": 1,
                        "enable_byte": 1,
                        "payload_flags": 32
                    },
                    "description": {
                        "KEY": "STR2203_TEXT",
                        "DE": "Freigabe unter Außentemperatur",
                    },
                    "device": [ { "family": 255, "var": 255 } ]
                },
            ]
        }
    }
}

@pytest.fixture
def ty_model():
    return model.BsbModel.parse_obj(
        {
            "version": "",
            "compiletime": "",
            "types": {
                "TEMP": {
                    "unit": {
                        "KEY": "UNIT_DEG_TEXT",
                        "DE": "°C"
                    },
                    "name": "TEMP",
                    "datatype": "VALS",
                    "datatype_id": 0,
                    "factor": 64,
                    "payload_length": 2,
                    "precision": 1,
                    "enable_byte": 1,
                    "payload_flags": 32
                }
            }
        }
    )

def test_structure_i18nstr():
    ud = {"KEY": "k", "EN": "en", "DE": "de"}
    x = cattr.structure(ud, model.I18nstr)
    assert x.__class__ is model.I18nstr

def test_unstructure_cmd_single():
    cmd = model.BsbCommand(parameter=1, command="0xABCD", device=[], description=model.I18nstr(), typename="FOO")
    ud = cattr.unstructure(cmd)
    assert "type" not in ud
    assert "min_value" not in ud
    assert "max_value" not in ud

def test_unstructure_cmd_nested():
    cmd = model.BsbCommand(parameter=1, command="0xABCD", device=[], description=model.I18nstr(), typename="FOO")
    cat = model.BsbCategory(name=model.I18nstr(), min=0, commands=[cmd])
    ud = cattr.unstructure(cat)
    ud = ud["commands"][0]
    assert "type" not in ud
    assert "min_value" not in ud
    assert "max_value" not in ud


def test_parse_device_description(testdata):
    m = model.BsbModel.parse_obj(testdata)
    cat = m.categories["2200"]
    assert (cat.name.de == "Kessel")

#@pytest.mark.skip("Full json file not included in repo yet")
def test_parse_production_file():
    m = model.BsbModel.parse_file("bsb-parameter.json")

def test_dedup_types():
    m = model.BsbModel.parse_file("bsb-parameter.json")
    m = model.dedup_types(m)
    assert len(m.types) == 91

def test_merge_types(ty_model):
    assert isinstance(ty_model.types["TEMP"].unit, model.I18nstr)
    m2 = deepcopy(ty_model)
    assert isinstance(m2.types["TEMP"].unit, model.I18nstr)
    ty2 = m2.types["TEMP"]
    ty2.unit["DE"] = "new de text"
    ty2.unit["EN"] = "new en text"
    ty2.precision = 2
    m2.types["TEMP2"] = ty2
    # test succesful merge
    merge_log = merge(ty_model, m2)
    assert merge_log == [
        "types[TEMP].unit.DE: °C -> new de text",
        "types[TEMP].unit.EN: + new en text",
        "types[TEMP].precision: 1 -> 2",
        "types[TEMP2]: +",
    ]
    ty = ty_model.types["TEMP"]
    assert len(ty.unit) == 3
    assert ty.unit.DE == "new de text"
    assert ty.unit.EN == "new en text"
    assert ty.precision == 2
    assert "TEMP2" in ty_model.types

    # test failing merge
    del m2.types["TEMP2"]
    ty2.name = "TEMP1"
    ty2.datatype=model.BsbDatatype.Byte
    ty2.factor = 65
    ty2.payload_length = 3
    ty2.enable_byte = 2
    ty2.payload_flags = 33
    with pytest.raises(ValueError) as exc:
        merge(ty_model, m2)
    for property in ["name", "datatype", "factor", "payload_length", "enable_byte", "payload_flags"]:
        assert property in str(exc.value)
    
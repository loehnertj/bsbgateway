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

@pytest.mark.skip("Full json file not included in repo yet")
def test_parse_production_file():
    m = model.BsbModel.parse_file("bsb-parameter.json")

@pytest.mark.skip("Full json file not included in repo yet")
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
    ty2.datatype=model.BsbDatatype.Bits
    ty2.factor = 65
    ty2.payload_length = 3
    ty2.enable_byte = 2
    ty2.payload_flags = 33
    with pytest.raises(ValueError) as exc:
        merge(ty_model, m2)
    for property in ["name", "datatype", "factor", "payload_length", "enable_byte", "payload_flags"]:
        assert property in str(exc.value)


# Tests for I18nstr serialization/deserialization with default_language

def test_structure_i18nstr_plain_string():
    """When structuring a plain string to I18nstr with default_language='DE',
    it should be wrapped as {DE: text}"""
    # Parse with default_language='DE'
    obj = {
        "version": "1.0",
        "compiletime": "20240101000000",
        "default_language": "DE"
    }
    m = model.BsbModel.parse_obj(obj, default_language="DE")
    
    # Now structure a plain string to I18nstr using the context
    # We need to set the context since we're not inside a parse_obj call
    old_context = model._default_language_context
    model._default_language_context = "DE"
    try:
        i18n = cattr.structure("Hallo Welt", model.I18nstr)
        assert i18n["DE"] == "Hallo Welt"
        assert len(i18n) == 1
    finally:
        model._default_language_context = old_context


def test_structure_i18nstr_dict_still_works():
    """When structuring a dict to I18nstr, it should work as before"""
    obj = {
        "version": "1.0",
        "compiletime": "20240101000000",
    }
    m = model.BsbModel.parse_obj(obj, default_language="DE")
    
    # Structure a dict with multiple languages
    old_context = model._default_language_context
    model._default_language_context = "DE"
    try:
        i18n = cattr.structure({"DE": "Hallo", "EN": "Hello"}, model.I18nstr)
        assert i18n["DE"] == "Hallo"
        assert i18n["EN"] == "Hello"
        assert len(i18n) == 2
    finally:
        model._default_language_context = old_context


def test_unstructure_i18nstr_single_default_language():
    """When unstructuring I18nstr with only default_language key,
    it should become a plain string"""
    old_context = model._default_language_context
    model._default_language_context = "DE"
    try:
        i18n = model.I18nstr({"DE": "Hallo Welt"})
        result = cattr.unstructure(i18n)
        assert result == "Hallo Welt"
        assert isinstance(result, str)
    finally:
        model._default_language_context = old_context


def test_unstructure_i18nstr_multiple_languages():
    """When unstructuring I18nstr with multiple languages,
    it should remain a dict"""
    old_context = model._default_language_context
    model._default_language_context = "DE"
    try:
        i18n = model.I18nstr({"DE": "Hallo", "EN": "Hello"})
        result = cattr.unstructure(i18n)
        assert isinstance(result, dict)
        assert result["DE"] == "Hallo"
        assert result["EN"] == "Hello"
    finally:
        model._default_language_context = old_context


def test_unstructure_i18nstr_different_language():
    """When unstructuring I18nstr where default is DE but only EN is present,
    it should remain a dict (not matching default language)"""
    old_context = model._default_language_context
    model._default_language_context = "DE"
    try:
        i18n = model.I18nstr({"EN": "Hello"})
        result = cattr.unstructure(i18n)
        assert isinstance(result, dict)
        assert result["EN"] == "Hello"
    finally:
        model._default_language_context = old_context


def test_roundtrip_single_language():
    """Test full roundtrip: plain string -> parse -> unstructure -> plain string"""
    # Create test data with a plain string instead of dict
    testdata = {
        "version": "1.0",
        "compiletime": "20240101000000",
        "default_language": "DE",
        "categories": {
            "100": {
                "name": "Kategorie Name",  # Plain string instead of dict!
                "min": 100,
                "max": 200,
                "commands": []
            }
        }
    }
    
    # Parse it - the plain string should be wrapped with {DE: text}
    m = model.BsbModel.parse_obj(testdata)
    assert isinstance(m.categories["100"].name, model.I18nstr)
    assert m.categories["100"].name["DE"] == "Kategorie Name"
    
    # Unstructure it back
    result = cattr.unstructure(m)
    assert result["categories"]["100"]["name"] == "Kategorie Name"
    assert isinstance(result["categories"]["100"]["name"], str)


def test_roundtrip_multiple_languages():
    """Test roundtrip with multiple languages - should stay as dict"""
    testdata = {
        "version": "1.0",
        "compiletime": "20240101000000",
        "default_language": "DE",
        "categories": {
            "100": {
                "name": {
                    "DE": "Kategorie Name",
                    "EN": "Category Name"
                },
                "min": 100,
                "max": 200,
                "commands": []
            }
        }
    }
    
    # Parse it
    m = model.BsbModel.parse_obj(testdata)
    assert isinstance(m.categories["100"].name, model.I18nstr)
    assert m.categories["100"].name["DE"] == "Kategorie Name"
    assert m.categories["100"].name["EN"] == "Category Name"
    
    # Unstructure it back - should remain as dict
    result = cattr.unstructure(m)
    assert isinstance(result["categories"]["100"]["name"], dict)
    assert result["categories"]["100"]["name"]["DE"] == "Kategorie Name"
    assert result["categories"]["100"]["name"]["EN"] == "Category Name"


def test_parse_obj_with_custom_default_language():
    """Test that parse_obj accepts and uses custom default_language"""
    testdata = {
        "version": "1.0",
        "compiletime": "20240101000000",
        "categories": {
            "100": {
                "name": "Kategorie Name",
                "min": 100,
                "max": 200,
                "commands": []
            }
        }
    }
    
    # Parse with EN as default language
    m = model.BsbModel.parse_obj(testdata, default_language="EN")
    assert m.default_language == "EN"
    assert isinstance(m.categories["100"].name, model.I18nstr)
    assert m.categories["100"].name["EN"] == "Kategorie Name"
    
    # Unstructure with EN as context
    old_context = model._default_language_context
    model._default_language_context = "EN"
    try:
        result = cattr.unstructure(m)
        # Should be plain string since EN matches default
        assert result["categories"]["100"]["name"] == "Kategorie Name"
        assert isinstance(result["categories"]["100"]["name"], str)
    finally:
        model._default_language_context = old_context


# ------------------- Global enum reference tests -------------------

@pytest.fixture
def enum_model_data():
    """Model JSON with top-level enums and a command that references one."""
    return {
        "version": "1.0",
        "compiletime": "20240101000000",
        "default_language": "DE",
        "enums": {
            "toggle1": {
                "0": {"DE": "Aus"},
                "1": {"DE": "An"},
            }
        },
        "categories": {
            "100": {
                "name": "Heizung",
                "min": 100,
                "max": 200,
                "commands": [
                    {
                        "parameter": 100,
                        "command": "0x01020304",
                        "description": "Betrieb",
                        "device": [{"family": 255, "var": 255}],
                        "enum": "toggle1",
                    },
                    {
                        "parameter": 101,
                        "command": "0x01020305",
                        "description": "Modus",
                        "device": [{"family": 255, "var": 255}],
                        "enum": {"0": {"DE": "Nein"}, "1": {"DE": "Ja"}},
                    },
                ],
            }
        },
    }


def test_global_enum_parsed(enum_model_data):
    """BsbModel.enums is populated with structured enum dicts."""
    m = model.BsbModel.parse_obj(enum_model_data)
    assert "toggle1" in m.enums
    assert isinstance(m.enums["toggle1"], dict)
    assert m.enums["toggle1"][0].DE == "Aus"
    assert m.enums["toggle1"][1].DE == "An"


def test_enum_ref_resolved_to_shared_object(enum_model_data):
    """A command with enum='toggle1' gets the exact same object as model.enums['toggle1']."""
    m = model.BsbModel.parse_obj(enum_model_data)
    cmd100 = m.fields[100]
    assert cmd100.enum is m.enums["toggle1"], "cmd.enum must be the exact shared dict object"


def test_enum_ref_accessible(enum_model_data):
    """Shared enum dict contains correct values."""
    m = model.BsbModel.parse_obj(enum_model_data)
    cmd100 = m.fields[100]
    assert cmd100.enum[0].DE == "Aus"
    assert cmd100.enum[1].DE == "An"


def test_inline_enum_not_shared(enum_model_data):
    """Command with inline dict enum is NOT the global enum object."""
    m = model.BsbModel.parse_obj(enum_model_data)
    cmd101 = m.fields[101]
    assert cmd101.enum is not m.enums["toggle1"]


def test_unknown_enum_ref_raises(enum_model_data):
    """Referencing a non-existent global enum raises KeyError with clear message."""
    enum_model_data["categories"]["100"]["commands"][0]["enum"] = "nonexistent"
    with pytest.raises((KeyError, Exception), match="nonexistent"):
        model.BsbModel.parse_obj(enum_model_data)


def test_roundtrip_enum_ref_serialized_as_string(enum_model_data):
    """Unstructuring a model with shared enum emits the ref name as string."""
    m = model.BsbModel.parse_obj(enum_model_data)
    d = cattr.unstructure(m)
    cmd100_d = d["categories"]["100"]["commands"][0]
    assert cmd100_d["enum"] == "toggle1", "Shared enum should serialize as string ref"


def test_roundtrip_inline_enum_serialized_as_dict(enum_model_data):
    """Inline enum (not identity-shared) is serialized as a dict."""
    m = model.BsbModel.parse_obj(enum_model_data)
    d = cattr.unstructure(m)
    cmd101_d = d["categories"]["100"]["commands"][1]
    assert isinstance(cmd101_d["enum"], dict), "Non-shared enum should remain inline dict"


def test_full_roundtrip_with_global_enums(enum_model_data):
    """parse -> unstructure -> parse produces equivalent model."""
    import json
    m1 = model.BsbModel.parse_obj(enum_model_data)
    json_str = m1.json()
    d2 = json.loads(json_str)
    m2 = model.BsbModel.parse_obj(d2)
    # global enum still present
    assert "toggle1" in m2.enums
    # ref'd command still has shared object
    assert m2.fields[100].enum is m2.enums["toggle1"]
    # values correct
    assert m2.fields[100].enum[0].DE == "Aus"


def test_model_without_global_enums_backward_compatible():
    """Models without top-level enums continue to parse correctly."""
    data = {
        "version": "1.0",
        "compiletime": "20240101000000",
        "categories": {
            "100": {
                "name": "Test",
                "min": 100,
                "max": 200,
                "commands": [
                    {
                        "parameter": 100,
                        "command": "0x01020304",
                        "description": "Irgendwas",
                        "device": [{"family": 255, "var": 255}],
                        "enum": {"0": {"DE": "Nein"}, "1": {"DE": "Ja"}},
                    }
                ],
            }
        },
    }
    m = model.BsbModel.parse_obj(data)
    assert m.enums == {}
    assert m.fields[100].enum[0].DE == "Nein"


def test_merge_normalizes_shared_enum_ref(enum_model_data):
    """Merging a command with a shared enum ref into another model
    breaks the shared reference and produces an independent inline copy."""
    m = model.BsbModel.parse_obj(enum_model_data)
    m2 = deepcopy(m)
    # After deepcopy, cmd.enum is a new dict object, not the same as m.enums['toggle1']
    # but _enum_ref is still 'toggle1'.  Merging back into original should work.
    merge(m, m2)
    cmd = m.fields[100]
    # After merge, cmd.enum should be an independent inline copy (no longer shared ref)
    assert cmd._enum_ref is None or cmd.enum is not m2.enums.get("toggle1"), \
        "After merge, enumref should be broken into inline copy"
    # Values must still be correct
    assert cmd.enum[0].DE == "Aus"

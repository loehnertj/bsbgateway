from configparser import ConfigParser
from bsbgateway.config import Config
from bsbgateway.config_reader import _config_to_configparser, _parse_config


def test_serialize_config():
    config = Config()
    # most complicated type
    config.web_interface.web_dashboard = [ [700, 710, 8005], [1620, None, 8830]]
    cp = _config_to_configparser(config)
    assert set(cp.sections()) == {'gateway', 'adapter', 'web_interface', 'cmd_interface', 'loggers','bsb2tcp', 'mqtt_interface'}
    assert cp.get('web_interface', 'web_dashboard') == '[[700, 710, 8005], [1620, None, 8830]]'

def test_parse_config():
    config_ini = """
[adapter]
adapter_device = /dev/abcde
expect_cts_state = null
port_stopbits = 1.5

; case-insensitive section and keys
[WEB_INTERFACE]
web_DASHBOARD = [[700, 710, 8005], [1620, null, 8830]]

[LOGGERS]
field_disp_ids = [700, 710, 8005]
"""
    cp = ConfigParser()
    cp.read_string(config_ini, source='<test>')
    config = _parse_config(cp)
    assert config.adapter.adapter_device == '/dev/abcde'
    assert config.adapter.expect_cts_state == None
    assert config.adapter.port_baud == 4800  # default value
    assert config.adapter.port_stopbits == 1.5

    assert config.web_interface.web_dashboard == [ [700, 710, 8005], [1620, None, 8830] ]
    assert config.web_interface.enable is True  # section exists -> True
    assert config.cmd_interface.enable is False  # section missing -> False

    assert config.loggers.field_disp_ids == [700, 710, 8005]
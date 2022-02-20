#!/bin/sh
# Splits bsb_parameters.json into bsb-types.json and bsb-parameters-stripped.json.
python3 -m bsbgateway.tools.extract_types
# Reads old broetje_isr_plus.py, writes broetje_isr_plus.json
python3 -m bsbgateway.tools.bsb_field_to_model
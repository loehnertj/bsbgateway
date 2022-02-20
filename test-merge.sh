#!/usr/bin/python3
import logging
from bsbgateway.bsb.model import BsbModel
from bsbgateway.bsb.model_merge import merge

logging.basicConfig(level="DEBUG")

m = BsbModel.parse_file("bsb-types.json")
m_1 = BsbModel.parse_file("bsb-parameter-stripped.json")
m_2 = BsbModel.parse_file("broetje_isr_plus.json")

print("--")
log1 = merge(m, m_1)
for entry in log1:
    print(entry)
print("--")
log2 = merge(m, m_2)
for entry in log2:
    print(entry)

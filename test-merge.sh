#!/usr/bin/python3
import logging
from bsbgateway.bsb.model import BsbModel
from bsbgateway.bsb.model_merge import merge

logging.basicConfig(level="DEBUG")

m = BsbModel.parse_file("bsb-types.json")
m_1 = BsbModel.parse_file("bsb-parameter-stripped.json")
m_2 = BsbModel.parse_file("broetje_isr_plus.json")


print("-- merge m1")
log1 = merge(m, m_1)
#print("Command count:", sum(1 for cat in m.categories.values() for cmd in cat.commands))
#for entry in log1:
#    print(entry)

print("-- merge m2")
log2 = merge(m, m_2)
#print("Command count:", sum(1 for cat in m.categories.values() for cmd in cat.commands))
for entry in log2:
    print(entry)

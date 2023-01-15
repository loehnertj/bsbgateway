#!/usr/bin/python3
import logging
import sys
from bsbgateway.bsb.model import BsbModel
from bsbgateway.bsb.model_merge import merge
from bsbgateway.bsb.model_filter import model_filter

logging.basicConfig(level="DEBUG")

m = BsbModel.parse_file("bsb-types.json")
m_1 = BsbModel.parse_file("bsb-parameter-stripped.json")
merge(m, m_1)

family= int(sys.argv[1])
var= int(sys.argv[2])

print("#cmd:", sum(1 for _ in m.commands))
model_filter(m, family, var)

print("#cmd:", sum(1 for _ in m.commands))

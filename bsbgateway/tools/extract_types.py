"""Extract types from bsb-parameter.json"""

from pathlib import Path
from ..bsb.model import BsbModel, dedup_types

def main():
    model = BsbModel.parse_file("bsb-parameter.json")
    model = dedup_types(model)
    tmodel = BsbModel(version=model.version, compiletime=model.compiletime, types=model.types)
    with Path("bsb-types.json").open("w") as f:
        f.write(tmodel.json())
    print("Wrote bsb-types.json")
    for cmd in model.commands:
        cmd.type = None
    with Path("bsb-parameter-stripped.json").open("w") as f:
        f.write(model.json(indent=0))
    print("Wrote bsb-parameter-stripped.json")


if __name__ == "__main__":
    main()
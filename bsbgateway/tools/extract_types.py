"""Extract types from bsb-parameter.json"""

from pathlib import Path
from ..bsb.model import BsbModel, dedup_types

def main():
    model = BsbModel.parse_file("bsb-parameter.json")
    model = dedup_types(model)
    tmodel = model.copy()
    tmodel.categories = {}
    tmodel.__fields_set__.remove("categories")
    with Path("bsb-types.json").open("w") as f:
        f.write(tmodel.json(exclude_unset=True, indent=2, ensure_ascii=False))
    print("Wrote bsb-types.json")
    for cmd in model.commands:
        cmd.type = None
        cmd.__fields_set__.remove("type")
    with Path("bsb-parameter-stripped.json").open("w") as f:
        f.write(model.json(exclude_unset=True, indent=0, ensure_ascii=False))
    print("Wrote bsb-parameter-stripped.json")


if __name__ == "__main__":
    main()
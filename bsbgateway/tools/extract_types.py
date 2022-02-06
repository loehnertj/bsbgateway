"""Extract types from bsb-parameter.json"""

from pathlib import Path
from ..bsb.model import BsbModel, dedup_types

def main():
    model = BsbModel.parse_file("bsb-parameter.json")
    model = dedup_types(model)
    model.categories = {}
    model.__fields_set__.remove("categories")
    with Path("bsb-types.json").open("w") as f:
        f.write(model.json(exclude_unset=True, indent=2))
        print("Wrote bsb-types.json")




if __name__ == "__main__":
    main()
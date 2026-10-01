# iteration agnostic, lazy loaded dataset. (design is kinda pretty)
from sol.helpers import *
from pathlib import Path
import csv

class SolDataset():
  def __init__(self, data_folder:str|Path="./data", device="cuda"):
    self.data_folder:Path = data_folder if isinstance(data_folder, Path) else Path(data_folder)
    self.found_csv:list[Path] = sorted(self.data_folder.glob("*.csv"))
    print(self.found_csv)
    self.device:str = device

  def extract_base_data(self): # champs, results, roles, etc...
    # NOTE: this is kinda ugly, idk if we can do this with 1 loop only
    # do [N, feature], e.g [N, champ] where N is total games
    for csv_path in self.found_csv:
      with csv_path.open(mode="r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
          print(row["champion"], row["position"], row["dpm"])

  def write_disk(self, path:str|Path):
    pass
  def read_disk(self, path:str|Path):
    pass


if __name__ == "__main__":
  s = SolDataset().extract_base_data()

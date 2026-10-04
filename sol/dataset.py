# iteration agnostic, lazy loaded dataset. (design is kinda pretty)
from sol.helpers import *
from pathlib import Path
import csv

class SolDataset():
  # keys available: bans: champs 
  def __init__(self, data_folder:str|Path="./data", device="cuda"):
    self.data_folder:Path = data_folder if isinstance(data_folder, Path) else Path(data_folder)
    self.found_csv:list[Path] = sorted(self.data_folder.glob("*.csv"))
    assert not self.found_csv is None and len(self.found_csv) > 0, f"could not find any .csv in {data_folder}"
    self.device:str = device
    self._data:dict[str, dict] = dict()

  def extract_base_data(self): # champs, results, roles, etc...
    # NOTE: this is kinda ugly, idk if we can do this with 1 loop only
    # do [N, feature], e.g [N, champ] where N is total games
    # preferably id like to store first pick champs and bans first in each dataset entry
    game_id = 0
    for csv_path in self.found_csv:
      with csv_path.open(mode="r", newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
          self._data["champs"][game_id]
          if row["champion"] == "": print("team", row["firstPick"], row["ban1"]) # team row
          else: print(row["champion"], row["position"], row["dpm"], row["ban1"]) # participant row

  def write_disk(self, path:str|Path):
    pass
  def read_disk(self, path:str|Path):
    pass


if __name__ == "__main__":
  s = SolDataset().extract_base_data()

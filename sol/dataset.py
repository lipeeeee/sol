# iteration agnostic, lazy loaded dataset. (design is kinda pretty)
from sol.helpers import *
from pathlib import Path
from itertools import islice
from collections import defaultdict
import csv

class SolDataset():
  def __init__(self, data_folder:str|Path="./data", device="cuda"):
    self.data_folder:Path = data_folder if isinstance(data_folder, Path) else Path(data_folder)
    self.found_csv:list[Path] = sorted(self.data_folder.glob("*.csv"))
    assert not self.found_csv is None and len(self.found_csv) > 0, f"could not find any .csv in {data_folder}"
    if True: print(len(self.found_csv), "csv's found") # NOTE: missing debug flag
    self.device:str = device
    self._data:dict[str, dict] = defaultdict(lambda: defaultdict(dict))

  def extract_base_data(self): # champs, results, roles, etc...
    # NOTE: this is kinda ugly, idk if we can do this with 1 loop only
    # do [N, feature], e.g [N, champ] where N is total games
    # preferably id like to store first pick champs and bans first in each dataset entry
    # batch 10 is blue batch 11 is red
    game_id = 0
    for csv_path in self.found_csv:
      with csv_path.open(mode="r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        while batch := list(islice(reader, 12)):
          assert batch[0]["gameid"] == batch[11]["gameid"]

          self._data["firstPick"][game_id]["Blue"] = "1" if batch[10]["firstPick"] == "" else batch[10]["firstPick"]
          self._data["firstPick"][game_id]["Red"] = "0" if batch[11]["firstPick"] == "" else batch[11]["firstPick"]
          # safe parsing flag
          if batch[10]["firstPick"] == "0": assert batch[11]["firstPick"] == "1"
          if batch[11]["firstPick"] == "0": assert batch[10]["firstPick"] == "1"

          game_id += 1

  def write_disk(self, path:str|Path):
    pass
  def read_disk(self, path:str|Path):
    pass


if __name__ == "__main__":
  s = SolDataset()
  s.extract_base_data()
  print(s._data)

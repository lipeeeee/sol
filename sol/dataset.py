# iteration agnostic, lazy loaded dataset. (design is kinda pretty)
from sol.utils import *
from pathlib import Path
from itertools import islice
from collections import defaultdict
import csv

class SolDataset():
  def __init__(self, data_folder:str|Path="./data", device="cuda"):
    self.data_folder:Path = data_folder if isinstance(data_folder, Path) else Path(data_folder)
    self.found_csv:list[Path] = sorted(self.data_folder.glob("*.csv"))
    assert not self.found_csv is None and len(self.found_csv) > 0, f"could not find any .csv in {data_folder}"
    if DEBUG >= 4: print(len(self.found_csv), "csv's found for dataset")
    self.device:str = device
    self._data:dict[str, defaultdict] = defaultdict(lambda: defaultdict(dict))

  def extract_base_data(self): # everything in csv's
    # 0 vs 1: 0 indexing is mainly used for blue side whilst 1 is for red
    # NOTE: this is kinda ugly, idk if we can do this with 1 loop only
    # do [N, feature], e.g [N, champ] where N is total games
    # preferably id like to store first pick champs and bans first in each dataset entry
    # batch 10 is blue batch 11 is red
    game_id = 0
    for csv_path in self.found_csv:
      if DEBUG >= 4: print(f"extracting_base_data({csv_path})")
      with csv_path.open(mode="r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        while batch := list(islice(reader, 12)):
          if SAFE_DATA_PARSING: assert batch[10]["side"] == "Blue" and batch[11]["side"] == "Red"

          self._data["gameid"][game_id] = batch[0]["gameid"]
          self._data["datacompleteness"][game_id] = batch[0]["datacompleteness"]
          if SAFE_DATA_PARSING:
            assert batch[0]["gameid"] != ""; assert batch[0]["gameid"] == batch[11]["gameid"]
            assert batch[0]["datacompleteness"] in ("complete", "partial")

          self._data["champion"][game_id] = [row["champion"] for row in batch[:10]]  
          self._data["position"][game_id] = [row["position"] for row in batch[:10]]  
          # print(batch[0].keys())
          # NOTE: do some SAFE_DATA_PARSING stuff here

          # can this storage be simplified?
          self._data["firstPick"][game_id][0] = "1" if batch[10]["firstPick"] == "" else batch[10]["firstPick"]
          self._data["firstPick"][game_id][1] = "0" if batch[11]["firstPick"] == "" else batch[11]["firstPick"]
          if SAFE_DATA_PARSING:
            if batch[10]["firstPick"] == "0": assert batch[11]["firstPick"] == "1"
            if batch[11]["firstPick"] == "0": assert batch[10]["firstPick"] == "1"
          
          self._data["pick_order"][game_id] = [batch[10][f"pick{i}"] for i in range(1, 6)]
          self._data["pick_order"][game_id] = [batch[11][f"pick{i}"] for i in range(1, 6)]

          game_id += 1

  def write_disk(self, path:str|Path):
    pass
  def read_disk(self, path:str|Path):
    pass


if __name__ == "__main__":
  s = SolDataset()
  s.extract_base_data()
  print(s._data.keys())

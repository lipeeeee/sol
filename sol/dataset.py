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
          if SAFE_DATA_PARSING:
            assert len(batch) == 12; assert [row["side"] for row in batch] == ["Blue"] * 5 + ["Red"] * 5 + ["Blue", "Red"]

          self._data["gameid"][game_id] = batch[0]["gameid"]
          self._data["url"][game_id] = batch[0]["url"] # this is mainly for LPL games
          self._data["league"][game_id] = batch[0]["league"]
          self._data["year"][game_id] = batch[0]["year"] # NOTE: date is a better way to track `year`
          self._data["split"][game_id] = batch[0]["split"]
          self._data["playoffs"][game_id] = batch[0]["playoffs"]
          self._data["date"][game_id] = batch[0]["date"]
          self._data["game"][game_id] = batch[0]["game"]
          self._data["patch"][game_id] = batch[0]["patch"]
          self._data["datacompleteness"][game_id] = batch[0]["datacompleteness"]
          if SAFE_DATA_PARSING:
            assert batch[0]["gameid"] != ""; assert all(row["gameid"] == batch[0]["gameid"] for row in batch)
            assert batch[0]["datacompleteness"] in ("complete", "partial")
            assert batch[0]["playoffs"] in ("1", "0"); assert batch[0]["game"] in ("1", "2", "3", "4", "5")
            assert batch[0]["date"] != ""; assert batch[0]["patch"] != ""

          self._data["champion"][game_id] = [row["champion"] for row in batch[:10]]  
          self._data["position"][game_id] = [row["position"] for row in batch[:10]]  
          if SAFE_DATA_PARSING:
            ...
            # if not (batch[0]["position"] == "top" and batch[5]["position"] == "top"): print(batch[0]["champion"], batch[5]["champion"])
            # assert batch[0]["position"] == "top" and batch[5]["position"] == "top"

          # NOTE: firstPick is assumed to blue if none are presented!
          self._data["firstPick"][game_id][0] = "1" if batch[10]["firstPick"] == "" else batch[10]["firstPick"]
          self._data["firstPick"][game_id][1] = "0" if batch[11]["firstPick"] == "" else batch[11]["firstPick"]
          if SAFE_DATA_PARSING:
            if batch[10]["firstPick"] == "0": assert batch[11]["firstPick"] == "1"
            if batch[11]["firstPick"] == "0": assert batch[10]["firstPick"] == "1"
            assert self._data["firstPick"][game_id][0] != self._data["firstPick"][game_id][1]
            assert tuple(row["firstPick"] for row in batch[10:]) in (("1", "0"), ("0", "1"), ("", ""))

          self._data["pick_order"][game_id][0] = [batch[10][f"pick{i}"] for i in range(1, 6)]
          self._data["pick_order"][game_id][1] = [batch[11][f"pick{i}"] for i in range(1, 6)]

          game_id += 1

  def write_disk(self, path:str|Path):
    pass
  def read_disk(self, path:str|Path):
    pass


if __name__ == "__main__":
  s = SolDataset()
  s.extract_base_data()
  print(s._data.keys())

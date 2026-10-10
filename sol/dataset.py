# iteration agnostic, lazy loaded dataset. (design is kinda pretty)
from typing import Self

from sol.utils import *
from pathlib import Path
from itertools import islice
from collections import defaultdict
import pickle, os
import csv

SolData = dict[str, defaultdict] # field_name: {gameid: data}

class SolDataset():
  def __init__(self, data_folder:str|Path="./data", check_cache=True):
    self.data_folder:Path = data_folder if isinstance(data_folder, Path) else Path(data_folder)
    self.found_csv:list[Path] = sorted(self.data_folder.glob("*.csv"))
    assert not self.found_csv is None and len(self.found_csv) > 0, f"could not find any .csv in {data_folder}"
    if DEBUG >= 4: print(len(self.found_csv), "csv's found for dataset")
    self._data:SolData = defaultdict(mk_defaultdict) # mk_defaultdict is a hack to allow pickle encoding

  REQUIRED_FIELDS:set[str] = {"gameid", "result", "date", "patch", "champion", "position", "firstPick", "pick_order" }
  def extract_base_data(self, requested_fields:list[str]|None=None): # everything in csv's
    # blue is side 0, red is side 1; batch[10] and batch[11] are the team rows
    game_id = 0
    role_order = ["top", "jng", "mid", "bot", "sup"]
    match_fields:list[str] = ["gameid", "url", "league", "year", "split", "playoffs", "date", "game", "patch", "datacompleteness"]
    fields_to_parse = self.REQUIRED_FIELDS | set(requested_fields or ())
    for csv_path in self.found_csv:
      if DEBUG >= 4: print(f"extracting_base_data({csv_path}), with: {fields_to_parse}")
      with csv_path.open(mode="r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if SAFE_DATA_PARSING: assert reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
        player_fields = [field for field in reader.fieldnames if field not in match_fields and field != "firstPick"] # type: ignore
        team_fields = [field for field in player_fields if field not in ("champion", "position")]
        while batch := list(islice(reader, 12)):
          if SAFE_DATA_PARSING:
            assert len(batch) == 12; assert [row["side"] for row in batch] == ["Blue"] * 5 + ["Red"] * 5 + ["Blue", "Red"]
            assert [row["position"] for row in batch[10:]] == ["team", "team"]
            assert all(None not in row and None not in row.values() for row in batch)
            if batch[0]["patch"] == "": continue

          for field in match_fields:
            if field in fields_to_parse: self._data[field][game_id] = batch[0][field]
          if SAFE_DATA_PARSING:
            if batch[0]["game"] == "": batch[0]["game"] = "1"
            assert batch[0]["gameid"] != ""; assert all(row["gameid"] == batch[0]["gameid"] for row in batch)
            assert batch[0]["datacompleteness"] in ("complete", "partial")
            assert batch[0]["playoffs"] in ("1", "0"); assert batch[0]["game"] in ("1", "2", "3", "4", "5")
            assert batch[0]["date"] != ""; assert batch[0]["patch"] != ""

          batch[:10] = sorted(batch[:10], key=lambda row: (row["side"], role_order.index(row["position"])))
          # player values follow champion order; keep strings and empty cells for post-processing
          for field in player_fields:
            if field in fields_to_parse: self._data[field][game_id] = [row[field] for row in batch[:10]]
          if SAFE_DATA_PARSING: assert self._data["position"][game_id] == role_order * 2

          # NOTE: firstPick is assumed to blue if none are presented!
          for side, row in enumerate(batch[10:]):
            self._data["firstPick"][game_id][side] = row["firstPick"] if row["firstPick"] != "" else ("1", "0")[side]
            self._data["pick_order"][game_id][side] = [row[f"pick{i}"] for i in range(1, 6)]
            if "ban_order" in fields_to_parse: self._data["ban_order"][game_id][side] = [row[f"ban{i}"] for i in range(1, 6)]
            for field in team_fields:
              if field in fields_to_parse: self._data[f"team_{field}"][game_id][side] = row[field]
          if SAFE_DATA_PARSING: assert tuple(row["firstPick"] for row in batch[10:]) in (("1", "0"), ("0", "1"), ("", ""))
          game_id += 1
      
    # cleanup for unwanted fields
    fields_to_keep = fields_to_parse | {f"team_{field}" for field in fields_to_parse} # team fields have diff idxs
    for entry in list(self._data):
      if entry not in fields_to_keep: del self._data[entry]
    if DEBUG >= 3: print(f"extracted {game_id} games's base csv data")
    return self

  @property
  def data(self): return self._data

  def write_disk(self, path:str|Path="./data/dataset_cache.pkl") -> Self:
    with open(path, mode="wb") as f:
      pickle.dump(self._data, f, protocol=4)
      if DEBUG >= 3: print(f"saved dataset to disk \"{path}\" ({self._data.keys()})")
    return self
  def read_disk(self, path:str|Path="./data/dataset_cache.pkl") -> Self:
    with open(path, mode="rb") as f:
      self._data = pickle.load(f)
      if DEBUG >= 3: print(f"loaded dataset from disk \"{path}\" ({self._data.keys()})")
    return self

def split_games(data:SolData, train=0.8, valid=0.1): # train, validation, test
  assert train > 0 and valid > 0 and train + valid < 1
  assert all(key in data for key in ("date", "gameid"))
  dates, ids = data["date"], data["gameid"]
  assert all(g in dates for g in ids), "missing game dates"
  indices = sorted(ids, key=lambda g: (dates[g], ids[g]))
  train_end = int(len(indices) * train)
  valid_end = int(len(indices) * (train + valid))
  assert 0 < train_end < valid_end < len(indices), "not enough games for this split"
  return indices[:train_end], indices[train_end:valid_end], indices[valid_end:]

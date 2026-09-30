# iteration agnostic, lazy loaded dataset. (design is kinda pretty)
from sol.helpers import *
from pathlib import Path

class SolDataset():
  def __init__(self, data_folder:str|Path="./data", device="cuda"):
    self.data_folder:Path = data_folder if isinstance(data_folder, Path) else Path(data_folder)
    self.device:str = device

  def extract_base_data(self): # champs, results, roles, etc...
    pass

  def write_disk(self, path:str|Path):
    pass
  def read_disk(self, path:str|Path):
    pass

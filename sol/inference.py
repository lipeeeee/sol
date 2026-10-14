from sol.utils import *
from metadata.champion_ids import CHAMPION_IDS
from torch import Tensor
from types import ModuleType
import sys, importlib

# needs to handle these inputs: draft state(champ, ban, firstpick) + patch
# dependening sol_iteration it should call the datasets to fill other computed fields

sol:ModuleType|None = None

def champ_id(x:str|int) -> int: return CHAMPION_IDS[x] if isinstance(x, str) else x
def load_model(version:str|int):
  global sol
  if not(sol is None): return sol # return already loaded model
  name = version if isinstance(version, str) else f"sol_{version}"
  try: 
    sol = importlib.import_module(f"configs.{name}")
    if DEBUG >= 1: print(f"inference: loaded {name}")
  except ModuleNotFoundError:
    print(f"could not find \'{name}\' version of sol. (e.g sol_1)")
    sys.exit(-1)
  sol.model.to(sol.training_params["device"])
  sol.model.eval()
  checkpoint_path = f"checkpoints/{name}.pt" if not("checkpoint_path" in sol.training_params) else sol.training_params["checkpoint_path"]
  weights = torch.load(checkpoint_path, map_location=sol.training_params["device"], weights_only=True)
  sol.model.load_state_dict(weights["model_state_dict"])
  if DEBUG >= 1: print(f"inference: loaded model weights for {name}({checkpoint_path})")
  assert_model_integrity(sol)
def prepare_tensors(inputs:list[dict]) -> dict[str, Tensor]: # for prediction
  assert not(sol is None), "need to load model first: load_model(\"sol_1\")"
  # **** check integrity of inputs ****
  if DEBUG >= 4: pass # we should probably check for input integrity but it might be expensive

  # **** build tensors ****
  _device = sol.training_params["device"]
  tensors:dict[str, Tensor] = dict()
  tensors["champion"] = torch.tensor([
    [champ_id(name) for name in draft["champion"]["blue"] + draft["champion"]["red"]]
    for draft in inputs], dtype=torch.long, device=_device)
  return tensors
def predict(x): # for now only assume json/dict is viable for prediction
  # x= [{"champion": {"blue": [], "red": []}, "firstPick": int, "patch": str}, ...]
  assert not(sol is None), "need to load model first: load_model(\"sol_1\")"

  tensors = prepare_tensors(x)
  with torch.inference_mode():
    y = sol.model(tensors["champion"])
  return y


if __name__ == "__main__":
  test_batch = [
    {
      "champion": {
        "blue": ["Aatrox", "Lee Sin", "Ahri", "Jinx", "Nautilus"],
        "red": ["Ornn", "Viego", "Orianna", "Aphelios", "Lulu"]
      },
      "firstPick": 0,
      "patch": "16.18"
    },
    {
      "champion": {
        "blue": ["Gwen", "Sejuani", "Azir", "Kai'Sa", "Rell"],
        "red": ["Renekton", "Jarvan IV", "Syndra", "Ezreal", "Leona"]
      },
      "firstPick": 1,
      "patch": "16.18"
    }
  ]
  load_model(1)
  predict(test_batch)

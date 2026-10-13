from sol.utils import *
from metadata.champion_ids import CHAMPION_IDS
from torch import Tensor
import sys, importlib

name = sys.argv[1] if len(sys.argv) > 1 else "sol_1"
try:
  sol = importlib.import_module(f"configs.{name}")
except ModuleNotFoundError:
  print(f"could not find \'{name}\' version of sol. (e.g sol_1)")
  sys.exit(-1)

assert_model_integrity(sol)
_device = sol.training_params["device"]
_weights_loaded = False
sol.model.to(_device)
sol.model.eval()

def champ_id(x:str|int) -> int: return CHAMPION_IDS[x] if isinstance(x, str) else x
def prepare_tensors(inputs:list[dict]) -> dict[str, Tensor]: # for prediction
  # **** check integrity of inputs ****
  if DEBUG >= 4: pass # we should probably check for input integrity but it might be expensive

  # **** build tensors ****
  tensors:dict[str, Tensor] = dict()
  tensors["champion"] = torch.tensor([
    [champ_id(name) for name in draft["champion"]["blue"] + draft["champion"]["red"]]
    for draft in inputs], dtype=torch.long, device=_device)
  return tensors
def predict(x): # for now only assume json/dict is viable for prediction
  # x= [{"champion": {"blue": [], "red": []}, "firstPick": int, "patch": str}, ...]
  global _weights_loaded
  if _weights_loaded == False:
    checkpoint_path = f"checkpoints/{name}.pt" if not("checkpoint_path" in sol.training_params) else sol.training_params["checkpoint_path"]
    weights = torch.load(checkpoint_path, map_location=_device, weights_only=True)
    sol.model.load_state_dict(weights["model_state_dict"])
    if DEBUG >= 1: print(f"loaded model weights for {name}({checkpoint_path})")
    _weights_loaded = False

  tensors = prepare_tensors(x)
  y = sol.model(tensors["champion"])
  return y

# needs to handle these inputs: draft state(champ, ban, firstpick) + patch
# dependening sol_iteration it should call the datasets to fill other computed fields

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
  predict(test_batch)

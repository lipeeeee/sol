from sol.utils import *
from sol.metadata.champion_ids import CHAMPION_IDS
from torch import Tensor
from types import ModuleType
from pathlib import Path
from weakref import WeakValueDictionary
import sys, importlib

# needs to handle these inputs: draft state(champ, ban, firstpick) + patch
# dependening sol_iteration it should call the datasets to fill other computed fields

_version_cache:WeakValueDictionary[str, ModuleType] = WeakValueDictionary()

def champ_id(x:str|int) -> int: return CHAMPION_IDS[x] if isinstance(x, str) else x
def load_model(version:str|int) -> ModuleType:
  name = version if isinstance(version, str) else f"sol_{version}"
  if (sol:=_version_cache.get(name)) is not None: return sol
  try: sol = importlib.import_module(f"sol.config.{name}")
  except ModuleNotFoundError as e:
    if e.name != f"sol.config.{name}": raise
    sys.exit(f"could not find '{name}' version of sol")
  assert_model_integrity(sol)
  if DEBUG >= 1: print(f"inference: loaded {name}")
  sol.model.to(sol.training_params["device"])
  sol.model.eval()
  checkpoint_path = Path(sol.training_params.get("checkpoint_path", f"checkpoints/{name}.pt"))
  if not checkpoint_path.is_absolute(): checkpoint_path = Path(__file__).resolve().parent.parent / checkpoint_path
  weights = torch.load(checkpoint_path, map_location=sol.training_params["device"], weights_only=True)
  sol.model.load_state_dict(weights["model_state_dict"])
  if DEBUG >= 1: print(f"inference: loaded model weights for {name}({checkpoint_path})")
  _version_cache[name] = sol
  return sol
def prepare_tensors(inputs:list[dict], device) -> dict[str, Tensor]: # for prediction
  # **** check integrity of inputs ****
  if DEBUG >= 4: pass # TODO: we should probably check for input integrity but it might be expensive

  # **** build tensors ****
  tensors:dict[str, Tensor] = dict()
  tensors["champion"] = torch.tensor([
    [champ_id(name) for name in draft["champion"]["blue"] + draft["champion"]["red"]]
    for draft in inputs], dtype=torch.long, device=device)
  return tensors
def predict(sol:ModuleType, x:list[dict]) -> Tensor: # for now only assume json/dict is viable for prediction
  # x= [{"champion": {"blue": [], "red": []}, "ban": {"blue": [], "red": []}, "firstPick": int, "patch": str|None}, ...]
  tensors = prepare_tensors(x, device=sol.training_params["device"])
  with torch.inference_mode():
    y = sol.model(*(tensors[key] for key in sol.inputs))
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
  s = load_model(1)
  predict(s, test_batch)

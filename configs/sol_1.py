"""Basic MLP on competitive data probably"""
from sol.utils import *
from metadata.champion_ids import CHAMPION_IDS 
from sol.dataset import SolDataset, split_games
from typing import Self
from torch import Tensor, nn 

dtype = torch.float32
training_params = {"device": "cuda"}
_device = training_params["device"] # NOTE: still dk how i feel about this shortcut
inputs = ["champion", "firstPick"]

class Sol_1(nn.Module):
  def __init__(self):
    super().__init__()
    self.define()

  def define(self) -> Self:
    self.activation = nn.GELU()
    self.champ_emb = nn.Embedding(max(CHAMPION_IDS.values()) + 1, 32)
    self.ln1 = nn.Linear(32 * 10 + 1, 256)
    self.ln2 = nn.Linear(256, 256)
    self.out = nn.Linear(256, 1)
    self.sigmoid = nn.Sigmoid()
    return self

  def forward(self, champ:Tensor, firstPick:Tensor):
    champ = self.champ_emb(champ).flatten(1)
    x = torch.concat((champ, firstPick), dim=1)
    x = self.activation(self.ln1(x))
    x = self.activation(self.ln2(x))
    return self.sigmoid(self.out(x)).squeeze(-1)
model = Sol_1().to(_device)
if DEBUG >= 1: print(model)


def calculate_loss(predictions:Tensor, batch:dict) -> Tensor:
  assert isinstance(predictions, Tensor); assert isinstance(batch, dict)
  return nn.functional.binary_cross_entropy(predictions, batch["result"])


if TRAINING:
  sd = SolDataset().extract_base_data()
  datasets = []
  for indices in split_games(sd.data):
    datasets.append({
      "champion": torch.tensor([[CHAMPION_IDS[name] for name in sd.data["champion"][g]] for g in indices], dtype=torch.long, device=_device),
      "firstPick": torch.tensor([[float(sd.data["firstPick"][g][0])] for g in indices], dtype=dtype, device=_device),
      "result": torch.tensor([float(sd.data["team_result"][g][0]) for g in indices], dtype=dtype, device=_device)
    })

  if DEBUG >= 2:
    for name, dataset in zip(("train", "valid", "test"), datasets):
      print(f"dataset {name}", {field: tuple(tensor.shape) for field, tensor in dataset.items()})


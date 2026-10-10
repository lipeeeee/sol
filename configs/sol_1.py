"""Basic MLP on competitive data probably"""
from sol.utils import *
from metadata.champion_ids import CHAMPION_IDS 
from sol.dataset import SolDataset, split_games
from functools import partial
from typing import Self
from torch import Tensor, nn, optim

dtype = torch.float32
training_params = {
  "optimizer": partial(optim.AdamW, lr=1e-3, weight_decay=0.2),
  "device": "cuda"
}
_device = training_params["device"]
inputs = ["champion", "firstPick"]

class Sol_1(nn.Module):
  def __init__(self):
    super().__init__()
    self.define()

  def define(self) -> Self:
    self.activation = nn.GELU()
    self.dropout = nn.Dropout(0.2)
    self.champ_emb = nn.Embedding(max(CHAMPION_IDS.values()) + 1, 32)

    self.ln1 = nn.Linear(32 * 10 + 1, 32)
    self.out = nn.Linear(32, 1)
    self.sigmoid = nn.Sigmoid()
    return self

  def forward(self, champ:Tensor, firstPick:Tensor):
    champ = self.champ_emb(champ).flatten(1)
    x = torch.concat((champ, firstPick), dim=1)
    x = self.dropout(self.activation(self.ln1(x)))
    return self.sigmoid(self.out(x)).squeeze(-1)
model = Sol_1().to(_device)
if DEBUG >= 1: print(model, count_params(model))

def calculate_loss(predictions:Tensor, batch:dict) -> Tensor:
  assert isinstance(predictions, Tensor); assert isinstance(batch, dict)
  return nn.functional.binary_cross_entropy(predictions, batch["result"])

if TRAINING:
  sd = SolDataset()
  try:
    sd = sd.read_disk("./data/dataset_sol_1.pkl")
  except FileNotFoundError:
    sd = sd.extract_base_data(inputs).write_disk("./data/dataset_sol_1.pkl")
  datasets = []
  for indices in split_games(sd.data):
    datasets.append({
      "champion": torch.tensor([[CHAMPION_IDS[name] for name in sd.data["champion"][g]] for g in indices], dtype=torch.long, device=_device),
      "firstPick": torch.tensor([[float(sd.data["firstPick"][g][0])] for g in indices], dtype=dtype, device=_device),
      "result": torch.tensor([float(sd.data["team_result"][g][0]) for g in indices], dtype=dtype, device=_device)
    })
  del sd

  if DEBUG >= 2:
    for name, dataset in zip(("train", "valid", "test"), datasets):
      print(f"dataset {name}", {field: tuple(tensor.shape) for field, tensor in dataset.items()})


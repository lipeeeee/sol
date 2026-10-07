"""Basic MLP on competitive data probably"""
from sol.utils import *
from metadata.champion_ids import CHAMPION_IDS 
from sol.dataset import SolDataset, split_games
from typing import Self
from torch import Tensor, nn

device = "cuda"
dtype = torch.float32

if TRAINING:
  sd = SolDataset().extract_base_data()
  datasets = []
  for indices in split_games(sd.data):
    datasets.append({
      "champion": torch.tensor([[CHAMPION_IDS[name] for name in sd.data["champion"][g]] for g in indices], dtype=torch.long, device=device),
      "firstPick": torch.tensor([[float(sd.data["firstPick"][g][0])] for g in indices], dtype=dtype, device=device),
      "result": torch.tensor([float(sd.data["team_result"][g][0]) for g in indices], dtype=dtype, device=device)
    })

  if DEBUG >= 2:
    for name, dataset in zip(("train", "valid", "test"), datasets):
      print(f"dataset {name}", {field: tuple(tensor.shape) for field, tensor in dataset.items()})

class Sol_1(nn.Module):
  def __init__(self):
    super().__init__()
    self.define()

  def define(self) -> Self:
    self.activation = nn.GELU()
    self.champ_emb = nn.Embedding(max(CHAMPION_IDS.values()), 32)
    self.ln1 = nn.Linear(32 * 10 + 1, 256)
    self.ln2 = nn.Linear(256, 256)
    self.out = nn.Linear(256, 1)
    return self

  def forward(self, x:Tensor):
    champ = self.champ_emb(x[0])
    x = torch.concat((champ, x[1]), dim=0)
    x = self.activation(self.ln1(x))
    x = self.activation(self.ln2(x))
    return self.out(x).squeeze(-1)

model = Sol_1().to(device)
if DEBUG >= 1: print(model)

"""Ultra-Slim Additive champion-role strengths, model weighs 3.5Kb"""
from sol.utils import *
from metadata.champion_ids import CHAMPION_IDS 
from sol.dataset import SolDataset, split_games
from functools import partial
from torch import Tensor, nn, optim

dtype = torch.float32
training_params = {
  "optimizer": partial(optim.Adam, lr=1e-3, weight_decay=0.0),
  "device": "cuda"
}
_device = training_params["device"]
inputs = ["champion"]

class Sol_1(nn.Module):
  # y = b + strength_blue - strength_red
  def __init__(self, side_aware:bool=False):
    super().__init__()
    embedding_dim = 10 if side_aware else 5
    self.strength_emb = nn.Embedding(max(CHAMPION_IDS.values()) + 1, embedding_dim)
    nn.init.zeros_(self.strength_emb.weight)
    self.bias = nn.Parameter(torch.zeros(1))
    return self

  def forward(self, champ:Tensor) -> Tensor:
    positions = torch.arange(10, device=_device)
    roles = positions % self.strength_emb.embedding_dim
    strengths = self.strength_emb(champ)[:, positions, roles]
    return self.bias + strengths[:, :5].sum(dim=1) - strengths[:, 5:].sum(dim=1)
model = Sol_1().to(_device)
if DEBUG >= 1: print(model, count_params(model))

def calculate_loss(predictions:Tensor, batch:dict) -> Tensor:
  assert isinstance(predictions, Tensor); assert isinstance(batch, dict)
  return nn.functional.binary_cross_entropy_with_logits(predictions, batch["result"])

if TRAINING:
  sd = SolDataset()
  try:
    sd = sd.read_disk("./data/dataset_sol_1.pkl")
  except FileNotFoundError:
    sd = sd.extract_base_data(requested_fields=inputs).write_disk("./data/dataset_sol_1.pkl")
  datasets = []
  for indices in split_games(sd.data):
    datasets.append({
      "champion": torch.tensor([[CHAMPION_IDS[name] for name in sd.data["champion"][g]] for g in indices], dtype=torch.long, device=_device),
      "result": torch.tensor([float(sd.data["team_result"][g][0]) for g in indices], dtype=dtype, device=_device)
    })
  assert all(input in sd.data for input in inputs)
  del sd

  if DEBUG >= 2:
    for name, dataset in zip(("train", "valid", "test"), datasets):
      print(f"dataset {name}", {field: tuple(tensor.shape) for field, tensor in dataset.items()})

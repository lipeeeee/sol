from sol.utils import *
TRAINING.value = 1 # important so other modules know we're training
import sys, importlib
from torch.utils.data import DataLoader, StackDataset
from functools import partial
from typing import Callable
from torch import nn, optim

name = sys.argv[1] if len(sys.argv) > 1 else "sol_1"
try:
  sol = importlib.import_module(f"configs.{name}")
except ModuleNotFoundError:
  print(f"could not find \'{name}\' version of sol. (e.g sol_1)")
  sys.exit(-1)
if DEBUG >= 1: print(f"loaded {name}")

# **** check model integrity ****
assert sol.dtype;
assert isinstance(sol.model, nn.Module); assert isinstance(sol.training_params, dict)
assert isinstance(sol.calculate_loss, Callable)
assert isinstance(sol.inputs, list); assert len(sol.inputs) >= 1

training_config = {
  "optimizer": partial(optim.AdamW, lr=1e-3, weight_decay=0),
  "batch_size": 64,
  "epochs": 10,
  "device": "cuda"
}
training_config.update(sol.training_params)
sol.model = sol.model.to(training_config["device"]) # type: ignore
optimizer = training_config["optimizer"](sol.model.parameters())
if DEBUG >= 1: print(f"training hyperparams: {training_config}")

train_loader, valid_loader, test_loader = [ # NOTE: we only shuffle train
  DataLoader(StackDataset(**data), batch_size=training_config["batch_size"], shuffle=(index==0), num_workers=0)
  for index, data in enumerate(sol.datasets)
]

for epoch in range(training_config["epochs"]):
  sol.model.train()
  total_loss:float = 0.0
  total_samples:int = 0

  for batch in train_loader:
    # NOTE: its assumed data is loaded on correct device! should probably add something here
    optimizer.zero_grad()
    predictions = sol.model(*(batch[key] for key in sol.inputs))
    loss = sol.calculate_loss(predictions, batch)
    loss.backward()
    optimizer.step()




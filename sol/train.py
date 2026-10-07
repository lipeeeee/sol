from sol.utils import *
TRAINING.value = 1 # important so other modules know we're training
import sys, importlib
from typing import Callable
from torch import optim

name = sys.argv[1] if len(sys.argv) > 1 else "sol_1"
try:
  sol = importlib.import_module(f"configs.{name}")
except ModuleNotFoundError:
  print(f"could not find \'{name}\' version of sol. (e.g sol_1)")
  sys.exit(-1)
if DEBUG >= 1: print(f"loaded {name}")

# **** check model integrity ****
assert isinstance(sol.device, str); assert sol.dtype;
assert sol.model; assert isinstance(sol.training_params, dict)
assert isinstance(sol.calculate_loss, Callable)

training_config = {
  "optimizer": optim.AdamW,
  "optimizer_kwargs": None,
  "lr": 1e-3,
  "batch_size": 64,
  "epochs": 10,
  "weight_decay": 0,
}

training_config.update(sol.training_params)
if DEBUG >= 1: print(f"training hyperparams: {training_config}")

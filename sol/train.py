from sol.utils import *
TRAINING.value = 1 # important so other modules know we're training
import sys, importlib
from torch.utils.data import DataLoader, StackDataset
from functools import partial
from math import isfinite
from pathlib import Path
from typing import Callable
from torch import nn, optim

name = sys.argv[1] if len(sys.argv) > 1 else "sol_1"
try:
  sol = importlib.import_module(f"configs.{name}")
except ModuleNotFoundError:
  print(f"could not find \'{name}\' version of sol. (e.g sol_1)")
  sys.exit(-1)

# **** check model integrity ****
assert sol.dtype
assert isinstance(sol.model, nn.Module); assert isinstance(sol.training_params, dict)
assert isinstance(sol.calculate_loss, Callable)
assert isinstance(sol.inputs, list); assert len(sol.inputs) >= 1
assert len(sol.datasets) == 3, "expected train, validation, and test datasets"


# **** defining environment ****
training_config = {
  "optimizer": partial(optim.AdamW, lr=1e-3, weight_decay=0),
  "batch_size": 64,
  "epochs": 10,
  "device": "cuda",
  "checkpoint_path": f"checkpoints/{name}.pt",
}
training_config.update(sol.training_params)
assert isinstance(training_config["epochs"], int) and training_config["epochs"] > 0
sol.model = sol.model.to(training_config["device"]) # type: ignore
optimizer = training_config["optimizer"](sol.model.parameters())
if DEBUG >= 1: print(f"training hyperparams: {training_config}")

train_loader, valid_loader, test_loader = [ # NOTE: we only shuffle train
  DataLoader(StackDataset(**data), batch_size=training_config["batch_size"], shuffle=(index==0), num_workers=0)
  for index, data in enumerate(sol.datasets)
]
assert all(len(loader.dataset) > 0 for loader in (train_loader, valid_loader, test_loader)), "dataset splits must not be empty"
checkpoint_path = Path(training_config["checkpoint_path"])
checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
best_valid_loss = float("inf")


# **** actual gradient descent ****
@torch.no_grad()
def evaluate(loader:DataLoader) -> tuple[float, float]:
  sol.model.eval()
  total_loss:float = 0.0
  total_samples:int = 0
  total_correct:int = 0
  for batch in loader:
    batch = {key: tensor.to(training_config["device"]) for key, tensor in batch.items()}
    predictions = sol.model(*(batch[key] for key in sol.inputs))
    loss = sol.calculate_loss(predictions, batch)
    batch_size = len(batch[sol.inputs[0]])
    total_loss += loss.item() * batch_size
    total_samples += batch_size
    total_correct += ((predictions >= 0.5) == batch["result"].bool()).sum().item()
  return total_loss / total_samples, total_correct / total_samples

for epoch in range(training_config["epochs"]):
  sol.model.train()
  total_loss:float = 0.0
  total_samples:int = 0
  total_correct:int = 0

  for batch in train_loader:
    batch = {key: tensor.to(training_config["device"]) for key, tensor in batch.items()}
    optimizer.zero_grad()
    predictions = sol.model(*(batch[key] for key in sol.inputs))
    loss = sol.calculate_loss(predictions, batch)
    loss.backward()
    optimizer.step()
    batch_size = len(batch[sol.inputs[0]])
    total_loss += loss.detach().item() * batch_size
    total_samples += batch_size
    total_correct += ((predictions.detach() >= 0.5) == batch["result"].bool()).sum().item()

  train_loss = total_loss / total_samples
  train_accuracy = total_correct / total_samples
  valid_loss, valid_accuracy = evaluate(valid_loader)
  if not isfinite(valid_loss): raise RuntimeError(f"non-finite validation loss at epoch {epoch + 1}: {valid_loss}")
  print(f"epoch {epoch + 1}/{training_config['epochs']}: train_loss={train_loss:.6f}, train_accuracy={train_accuracy:.2%}, "
        f"valid_loss={valid_loss:.6f}, valid_accuracy={valid_accuracy:.2%}")

  if valid_loss < best_valid_loss:
    best_valid_loss = valid_loss
    torch.save({"epoch": epoch + 1, "model_state_dict": sol.model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(), "train_loss": train_loss, "valid_loss": valid_loss,
                "train_accuracy": train_accuracy, "valid_accuracy": valid_accuracy
    }, checkpoint_path)

checkpoint = torch.load(checkpoint_path, map_location=training_config["device"], weights_only=True)
sol.model.load_state_dict(checkpoint["model_state_dict"])
optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
test_loss, test_accuracy = evaluate(test_loader)
print(f"test_loss={test_loss:.6f}, test_accuracy={test_accuracy:.2%} (best epoch={checkpoint['epoch']}, checkpoint={checkpoint_path})")

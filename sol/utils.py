from __future__ import annotations
from collections import defaultdict
from enum import IntEnum
from typing import Any, ClassVar, Generic, TypeVar, Callable
import os, sys

try:
  import torch
  from torch import nn
except ImportError:
  print("sol needs torch compiled to run")
  sys.exit(-1)

T = TypeVar("T")

class TeamEnum(IntEnum):
  BLUE = 0; RED = 1

# **** Context/Env vars ****
def getenv(key:str, default:Any): return type(default)(os.getenv(key, default))
class ContextVar(Generic[T]):
  _cache: ClassVar[dict[str, ContextVar]] = {}
  value: T
  key: str
  def __init__(self, key: str, default_value: T):
    if key in ContextVar._cache: raise RuntimeError(f"attempt to recreate ContextVar {key}")
    ContextVar._cache[key] = self
    self.value, self.key = getenv(key, default_value), key
  def __bool__(self): return bool(self.value)
  def __eq__(self, x): return self.value == x
  def __ge__(self, x): return self.value >= x
  def __gt__(self, x): return self.value > x
  def __lt__(self, x): return self.value < x
  def __repr__(self): return str(self.value)

DEBUG = ContextVar("DEBUG", 0)
TRAINING = ContextVar("TRAINING", 0)
SAFE_DATA_PARSING = ContextVar("SAFE_DATA_PARSING", 1)

# **** regular checks for sol ****
if DEBUG >= 1: # give info on cuda
  try:
    assert torch.cuda.is_available()
  except AssertionError:
    print("cuda isn't available!")

def assert_model_integrity(sol):
  assert sol.dtype
  assert isinstance(sol.model, nn.Module); assert isinstance(sol.training_params, dict)
  assert isinstance(sol.calculate_loss, Callable)
  assert isinstance(sol.inputs, list); assert len(sol.inputs) >= 1
  if TRAINING: assert len(sol.datasets) == 3, "expected train, validation, and test datasets"

# **** random utils ****
# (all_params, trainable_params)
def count_params(model:nn.Module): return (sum(p.numel() for p in model.parameters()), sum(p.numel() for p in model.parameters() if p.requires_grad))
def mk_defaultdict(): return defaultdict(dict) # hack: allows pickle to encode defaultdict lambdas

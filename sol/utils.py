from __future__ import annotations
from typing import Any, Callable, ClassVar, Generic, TypeVar
import os

T = TypeVar("T")

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
SAFE_DATA_PARSING = ContextVar("SAFE_DATA_PARSING", 1)


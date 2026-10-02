from collections.abc import Callable
from pathlib import Path
from typing import TypedDict
from metadata.champion_ids import CHAMPION_IDS
from draft import Draft

ROOT:Path = Path(__file__).resolve().parent.parent
Champion = TypedDict("Champion", {"id": int, "name": str, "roles": list[str]})
Evaluator = Callable[[int, Draft], float]
evaluator:Evaluator|None = None

def validate_version(version:int)->None:
  if version < 1 or not (ROOT / "configs" / f"sol_{version}.py").is_file():
    raise ValueError(f"Unknown Sol version {version}: configs/sol_{version}.py does not exist")

def champions()->list[Champion]:
  assert all(type(value) is int and value > 0 for value in CHAMPION_IDS.values()), "Sol IDs must be positive integers"
  assert len(set(CHAMPION_IDS.values())) == len(CHAMPION_IDS), "Sol IDs must be unique"
  assert all(isinstance(name, str) and name for name in CHAMPION_IDS), "Champion names must be nonempty strings"
  # TODO: translate shared champion role metadata here when its encoding exists.
  return [{"id": value, "name": name, "roles": []} for name, value in sorted(CHAMPION_IDS.items())]

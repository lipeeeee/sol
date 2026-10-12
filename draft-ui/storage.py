import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import TypedDict, cast
from uuid import uuid4
from draft import Draft, validate_draft

DRAFTS:Path = Path(__file__).resolve().parent / "drafts"
FAVORITES:Path = DRAFTS.with_name("favorites.json")
DRAFT_ID:re.Pattern[str] = re.compile(r"[0-9a-f]{32}")
SavedDraft = TypedDict("SavedDraft", {"id": str, "name": str, "saved_at": str, "draft": Draft})
favorites_lock = Lock()

def atomic_write(path:Path, data:bytes)->None:
  path.parent.mkdir(parents=True, exist_ok=True)
  temporary:Path|None = None
  try:
    with NamedTemporaryFile(dir=path.parent, prefix=".", delete=False) as file:
      temporary = Path(file.name); file.write(data)
    temporary.replace(path)
  finally:
    if temporary is not None: temporary.unlink(missing_ok=True)

def validate_name(value:object)->str:
  if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80:
    raise ValueError("Draft name must contain 1 to 80 characters")
  return value.strip()

def save_draft(name:str, draft:Draft, directory:Path=DRAFTS)->SavedDraft:
  saved:SavedDraft = {"id": uuid4().hex, "name": validate_name(name),
                      "saved_at": datetime.now(timezone.utc).isoformat(), "draft": draft}
  atomic_write(directory / f"{saved['id']}.json", (json.dumps(saved, indent=2) + "\n").encode())
  return saved

def draft_path(draft_id:str, directory:Path)->Path:
  if not DRAFT_ID.fullmatch(draft_id): raise ValueError("Invalid saved draft ID")
  return directory / f"{draft_id}.json"

def load_draft(draft_id:str, champion_ids:frozenset[int], directory:Path=DRAFTS)->SavedDraft:
  value:object = json.loads(draft_path(draft_id, directory).read_bytes())
  fields:set[str] = {"id", "name", "saved_at", "draft"}
  if not isinstance(value, dict) or set(value) not in (fields, fields | {"sol_version"}):
    raise ValueError("Invalid saved draft file")
  if value["id"] != draft_id: raise ValueError("Invalid saved draft metadata")
  if "sol_version" in value:
    if type(value["sol_version"]) is not int or value["sol_version"] < 1:
      raise ValueError("Invalid saved draft metadata")
    del value["sol_version"]
  validate_name(value["name"])
  if not isinstance(value["saved_at"], str): raise ValueError("Invalid saved draft date")
  datetime.fromisoformat(value["saved_at"])
  validate_draft(value["draft"], champion_ids)
  return cast(SavedDraft, value)

def list_drafts(champion_ids:frozenset[int], directory:Path=DRAFTS)->list[SavedDraft]:
  saved:list[SavedDraft] = []
  if not directory.exists(): return saved
  for path in directory.iterdir():
    if path.suffix != ".json" or not DRAFT_ID.fullmatch(path.stem): continue
    try: saved.append(load_draft(path.stem, champion_ids, directory))
    except (OSError, ValueError) as error: logging.warning("Saved draft unavailable at %s: %s", path, error)
  return sorted(saved, key=lambda draft: (draft["saved_at"], draft["id"]), reverse=True)

def delete_draft(draft_id:str, directory:Path=DRAFTS)->None: draft_path(draft_id, directory).unlink()

def load_favorites(champion_ids:frozenset[int], path:Path=FAVORITES)->list[int]:
  try: value:object = json.loads(path.read_bytes())
  except FileNotFoundError: return []
  if not isinstance(value, list) or any(type(champion_id) is not int or champion_id not in champion_ids for champion_id in value):
    raise ValueError("Favorites must contain known champion IDs")
  if len(set(value)) != len(value): raise ValueError("Favorite champion IDs must be unique")
  return sorted(value)

def set_favorite(champion_id:int, favorite:bool, champion_ids:frozenset[int], path:Path=FAVORITES)->list[int]:
  if type(champion_id) is not int or champion_id not in champion_ids: raise ValueError("Unknown champion ID")
  if type(favorite) is not bool: raise ValueError("Expected a favorite flag")
  # The threaded server must keep other champions' favorites when requests overlap.
  with favorites_lock:
    favorites:set[int] = set(load_favorites(champion_ids, path))
    if favorite: favorites.add(champion_id)
    else: favorites.discard(champion_id)
    saved:list[int] = sorted(favorites)
    atomic_write(path, (json.dumps(saved, indent=2) + "\n").encode())
    return saved

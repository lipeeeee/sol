import json
import logging
import re
from http.client import HTTPException
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

ASSET_VERSION:str = "16.19.1"
CDN:str = f"https://ddragon.leagueoflegends.com/cdn/{ASSET_VERSION}"
CACHE:Path = Path(__file__).resolve().parent / ".cache" / "ddragon" / ASSET_VERSION
FILENAME:re.Pattern[str] = re.compile(r"[A-Za-z0-9_]+\.png")
PNG_SIGNATURE:bytes = b"\x89PNG\r\n\x1a\n"
PNG_END:bytes = b"\x00\x00\x00\x00IEND\xaeB\x60\x82"

def normalise_name(name:str)->str: return re.sub(r"[^a-z0-9]", "", name.casefold())

def fetch_bytes(url:str)->bytes:
  with urlopen(url, timeout=10) as response:
    data:bytes = response.read(); length:str|None = response.headers.get("Content-Length")
  if length is not None and len(data) != int(length): raise OSError("Incomplete artwork download")
  return data

def atomic_write(path:Path, data:bytes)->None:
  path.parent.mkdir(parents=True, exist_ok=True)
  temporary:Path|None = None
  try:
    with NamedTemporaryFile(dir=path.parent, prefix=".", delete=False) as file:
      temporary = Path(file.name); file.write(data)
    temporary.replace(path)
  finally:
    if temporary is not None: temporary.unlink(missing_ok=True)

def decode_catalogue(data:bytes)->dict[str, str]:
  catalogue:object = json.loads(data)
  if not isinstance(catalogue, dict) or catalogue.get("version") != ASSET_VERSION:
    raise ValueError("Unexpected Data Dragon version")
  entries:object = catalogue.get("data")
  if not isinstance(entries, dict) or not entries: raise ValueError("Missing champion catalogue")
  artwork:dict[str, str] = {}
  for entry in entries.values():
    if not isinstance(entry, dict) or not isinstance(entry.get("name"), str): raise ValueError("Invalid champion entry")
    image:object = entry.get("image")
    filename:object = image.get("full") if isinstance(image, dict) else None
    if not isinstance(filename, str) or not FILENAME.fullmatch(filename): raise ValueError("Invalid portrait filename")
    name:str = normalise_name(entry["name"])
    if not name or name in artwork: raise ValueError("Ambiguous champion names")
    artwork[name] = filename
  return artwork

def load_catalogue(cache:Path=CACHE)->dict[str, str]:
  path:Path = cache / "champion.json"
  if path.is_file():
    try: return decode_catalogue(path.read_bytes())
    except (OSError, ValueError) as error: logging.warning("Invalid cached champion catalogue: %s", error)
  try:
    data:bytes = fetch_bytes(f"{CDN}/data/en_US/champion.json")
    artwork:dict[str, str] = decode_catalogue(data)
    atomic_write(path, data)
    return artwork
  except (OSError, ValueError, HTTPException) as error:
    logging.warning("Champion artwork unavailable: %s", error)
    return {}

def validate_png(data:bytes)->None:
  if len(data) < 32 or not data.startswith(PNG_SIGNATURE) or not data.endswith(PNG_END):
    raise ValueError("Invalid or incomplete PNG portrait")

def portrait_bytes(filename:str, cache:Path=CACHE)->bytes:
  assert FILENAME.fullmatch(filename), "Portrait filename must come from the validated catalogue"
  path:Path = cache / filename
  if path.is_file():
    try:
      data:bytes = path.read_bytes(); validate_png(data)
      return data
    except (OSError, ValueError) as error: logging.warning("Invalid cached portrait %s: %s", filename, error)
  data = fetch_bytes(f"{CDN}/img/champion/{filename}")
  validate_png(data); atomic_write(path, data)
  return data

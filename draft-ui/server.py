from __future__ import annotations
import json
import logging
import re
import socket
import traceback
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, HTTPServer
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit
import assets
import storage
from bridge import Champion, Evaluator
from draft import Draft, validate_draft

UI:Path = Path(__file__).resolve().parent
STATIC:dict[str, tuple[str, str]] = {
  "/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
  "/styles.css": ("styles.css", "text/css"), "/app.js": ("app.js", "text/javascript"),
  "/draft.mjs": ("draft.mjs", "text/javascript"), "/outfit-latin.woff2": ("outfit-latin.woff2", "font/woff2")
}
PORTRAIT:re.Pattern[str] = re.compile(rf"/portraits/{re.escape(assets.ASSET_VERSION)}/([1-9][0-9]*)\.png")
SPLASH:re.Pattern[str] = re.compile(rf"/splashes/{re.escape(assets.ASSET_VERSION)}/([1-9][0-9]*)\.jpg")
SAVED_DRAFT:re.Pattern[str] = re.compile(r"/api/drafts/([0-9a-f]{32})")

class Handler(BaseHTTPRequestHandler):
  def __init__(self:Handler, request:socket.socket, client_address:tuple[str, int], server:HTTPServer, *,
               version:int, champions:list[Champion], artwork:dict[str, str], evaluator:Evaluator|None=None,
               drafts_directory:Path=storage.DRAFTS)->None:
    self.version:int = version
    self.champions:list[Champion] = champions
    self.champion_ids:frozenset[int] = frozenset(champion["id"] for champion in champions)
    self.artwork:dict[str, str] = artwork
    self.evaluator:Evaluator|None = evaluator
    self.drafts_directory:Path = drafts_directory
    super().__init__(request, client_address, server)

  def send_bytes(self:Handler, status:int, data:bytes, content_type:str, cache_control:str="no-store")->None:
    self.send_response(status)
    self.send_header("Content-Type", content_type)
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Cache-Control", cache_control)
    self.send_header("X-Content-Type-Options", "nosniff")
    self.end_headers()
    if self.command != "HEAD": self.wfile.write(data)

  def send_json(self:Handler, status:int, value:dict[str, object])->None:
    self.send_bytes(status, json.dumps(value, allow_nan=False).encode(), "application/json; charset=utf-8")

  def do_HEAD(self:Handler)->None: self.do_GET()

  def do_GET(self:Handler)->None:
    path:str = urlsplit(self.path).path
    if path in STATIC:
      filename:str; content_type:str
      filename, content_type = STATIC[path]
      if content_type.startswith("text/"): content_type += "; charset=utf-8"
      self.send_bytes(200, (UI / filename).read_bytes(), content_type)
      return
    if path == "/api/bootstrap":
      champions:list[dict[str, object]] = []
      for champion in self.champions:
        portrait:str|None = f"/portraits/{assets.ASSET_VERSION}/{champion['id']}.png"
        splash:str|None = f"/splashes/{assets.ASSET_VERSION}/{champion['id']}.jpg"
        if assets.normalise_name(champion["name"]) not in self.artwork: portrait = splash = None
        champions.append({**champion, "portrait_url": portrait, "splash_url": splash})
      self.send_json(200, {"sol_version": self.version, "champions": champions,
                          "evaluation_available": self.evaluator is not None})
      return
    if path == "/api/drafts":
      try: saved:list[storage.SavedDraft] = storage.list_drafts(self.champion_ids, self.drafts_directory)
      except OSError as error:
        logging.warning("Could not list saved drafts: %s", error)
        self.send_json(500, {"error": "Could not read saved drafts from disk."}); return
      self.send_json(200, {"drafts": [{key: value for key, value in draft.items() if key != "draft"} for draft in saved]})
      return
    match:re.Match[str]|None = SAVED_DRAFT.fullmatch(path)
    if match:
      try: saved_draft:storage.SavedDraft = storage.load_draft(match[1], self.champion_ids, self.drafts_directory)
      except FileNotFoundError: self.send_json(404, {"error": "Saved draft not found."}); return
      except (OSError, ValueError) as error:
        logging.warning("Could not load saved draft %s: %s", match[1], error)
        self.send_json(500, {"error": "Could not read this saved draft from disk."}); return
      self.send_json(200, saved_draft); return
    match = PORTRAIT.fullmatch(path) or SPLASH.fullmatch(path)
    if match and int(match[1]) in self.champion_ids:
      champion:Champion = next(champion for champion in self.champions if champion["id"] == int(match[1]))
      filename:str|None = self.artwork.get(assets.normalise_name(champion["name"]))
      if filename is None: self.send_json(404, {"error": "Artwork unavailable"}); return
      is_splash:bool = path.startswith("/splashes/")
      try: data:bytes = (assets.splash_bytes if is_splash else assets.portrait_bytes)(filename)
      except (OSError, ValueError, HTTPException) as error:
        logging.warning("Artwork unavailable for %s: %s", champion["name"], error)
        self.send_json(503, {"error": "Artwork unavailable"}); return
      self.send_bytes(200, data, "image/jpeg" if is_splash else "image/png", "public, max-age=31536000, immutable")
      return
    self.send_json(404, {"error": "Not found"})

  def do_POST(self:Handler)->None:
    path:str = urlsplit(self.path).path
    if path not in ("/api/evaluate", "/api/drafts"): self.send_json(404, {"error": "Not found"}); return
    if self.headers.get_content_type() != "application/json":
      self.send_json(415, {"error": "Expected application/json"}); return
    try: length:int = int(self.headers.get("Content-Length", ""))
    except ValueError: self.send_json(400, {"error": "Expected Content-Length"}); return
    if length < 0: self.send_json(400, {"error": "Invalid Content-Length"}); return
    if length > 16384: self.send_json(413, {"error": "Draft request exceeds 16 KiB"}); return
    try:
      body:bytes = self.rfile.read(length)
      if len(body) != length: raise ValueError("Incomplete request body")
      value:object = json.loads(body)
      name:str = ""
      if path == "/api/drafts":
        if not isinstance(value, dict) or set(value) != {"name", "draft"}:
          raise ValueError("Expected a draft name and snapshot")
        name = storage.validate_name(value["name"])
        value = value["draft"]
      draft:Draft = validate_draft(value, self.champion_ids)
    except ValueError as error: self.send_json(400, {"error": str(error)}); return
    if path == "/api/drafts":
      try: saved:storage.SavedDraft = storage.save_draft(name, draft, self.version, self.drafts_directory)
      except OSError as error:
        logging.warning("Could not save draft: %s", error)
        self.send_json(500, {"error": "Could not save this draft to disk."}); return
      self.send_json(201, saved); return
    if self.evaluator is None: self.send_json(503, {"error": f"No evaluator is connected to Sol {self.version}"}); return
    try:
      p:float = self.evaluator(self.version, draft)
      assert type(p) in (int, float) and isfinite(p) and 0 <= p <= 1, "Evaluator returned an invalid probability"
    except Exception:
      traceback.print_exc()
      self.send_json(500, {"error": "Draft evaluation failed. Check the server output."}); return
    self.send_json(200, {"blue_win_probability": p})

  def do_DELETE(self:Handler)->None:
    match:re.Match[str]|None = SAVED_DRAFT.fullmatch(urlsplit(self.path).path)
    if not match: self.send_json(404, {"error": "Not found"}); return
    try: storage.delete_draft(match[1], self.drafts_directory)
    except FileNotFoundError: self.send_json(404, {"error": "Saved draft not found."}); return
    except OSError as error:
      logging.warning("Could not delete saved draft %s: %s", match[1], error)
      self.send_json(500, {"error": "Could not delete this saved draft from disk."}); return
    self.send_json(200, {"deleted": match[1]})

  def log_message(self:Handler, format:str, *args:object)->None: logging.debug(format, *args)

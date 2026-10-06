from __future__ import annotations
import json
import subprocess
import sys
import threading
import unittest
from contextlib import redirect_stderr
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict
from unittest.mock import patch
import assets
import bridge
from draft import Draft
from server import Handler

class BootstrapChampion(TypedDict):
  id:int
  name:str
  roles:list[str]
  portrait_url:str|None
  splash_url:str|None

class BootstrapData(TypedDict):
  sol_version:int
  champions:list[BootstrapChampion]
  evaluation_available:bool

class ServerTests(unittest.TestCase):
  def setUp(self:ServerTests)->None:
    self.temporary = TemporaryDirectory(); self.directory = Path(self.temporary.name) / "drafts"
    self.handler = partial(Handler, version=1, champions=bridge.champions(), artwork={"wukong": "MonkeyKing.png"},
                           drafts_directory=self.directory)
    self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
    self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
    self.thread.start()
    self.draft:Draft = {
      "blue": {"picks": [None] * 5, "bans": [None] * 5},
      "red": {"picks": [None] * 5, "bans": [None] * 5},
    }

  def tearDown(self:ServerTests)->None:
    self.server.shutdown(); self.server.server_close(); self.thread.join()
    self.temporary.cleanup()

  def request(self:ServerTests, method:str, path:str, body:bytes|None=None,
              headers:dict[str, str]|None=None)->tuple[int, bytes, dict[str, str]]:
    connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
    try:
      connection.request(method, path, body=body, headers=headers or {})
      response = connection.getresponse()
      return response.status, response.read(), dict(response.getheaders())
    finally: connection.close()

  def post(self:ServerTests, draft:object)->tuple[int, bytes, dict[str, str]]:
    return self.request("POST", "/api/evaluate", json.dumps(draft).encode(), {"Content-Type": "application/json"})

  def save(self:ServerTests, value:object)->tuple[int, bytes, dict[str, str]]:
    return self.request("POST", "/api/drafts", json.dumps(value).encode(), {"Content-Type": "application/json"})

  def test_saved_drafts_survive_a_server_restart(self:ServerTests)->None:
    self.assertEqual(json.loads(self.request("GET", "/api/drafts")[1]), {"drafts": []})
    self.assertFalse(self.directory.exists())
    self.draft["blue"]["picks"][3] = 1; self.draft["red"]["bans"][4] = 157
    status, body, _ = self.save({"name": "  Match one  ", "draft": self.draft})
    saved:dict[str, object] = json.loads(body); path:str = f"/api/drafts/{saved['id']}"
    self.assertEqual(status, 201); self.assertEqual(saved["name"], "Match one"); self.assertEqual(saved["draft"], self.draft)
    self.assertNotIn("sol_version", saved)
    self.assertEqual(json.loads((self.directory / f"{saved['id']}.json").read_bytes()), saved)
    self.server.shutdown(); self.server.server_close(); self.thread.join()
    self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
    self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
    self.thread.start()
    status, body, _ = self.request("GET", path)
    self.assertEqual(status, 200); self.assertEqual(json.loads(body), saved)
    status, body, headers = self.request("GET", "/api/drafts")
    self.assertEqual(status, 200); self.assertEqual(headers["Cache-Control"], "no-store")
    self.assertEqual(json.loads(body)["drafts"], [{key: value for key, value in saved.items() if key != "draft"}])

  def test_saves_are_separate_and_delete_is_scoped_to_one_snapshot(self:ServerTests)->None:
    first:dict[str, object] = json.loads(self.save({"name": "Same name", "draft": self.draft})[1])
    second:dict[str, object] = json.loads(self.save({"name": "Same name", "draft": self.draft})[1])
    self.assertNotEqual(first["id"], second["id"])
    path:str = f"/api/drafts/{first['id']}"
    self.assertEqual(self.request("DELETE", path)[0], 200)
    self.assertEqual(self.request("DELETE", path)[0], 404); self.assertEqual(self.request("GET", path)[0], 404)
    self.assertEqual(json.loads(self.request("GET", "/api/drafts")[1])["drafts"][0]["id"], second["id"])

  def test_invalid_saves_and_paths_never_write_to_disk(self:ServerTests)->None:
    for value in (None, {}, {"name": "Name"}, {"name": "Name", "draft": {}},
                  *({"name": name, "draft": self.draft} for name in (None, True, "", " ", "x" * 81))):
      with self.subTest(value=value): self.assertEqual(self.save(value)[0], 400)
    self.draft["blue"]["picks"][0] = 1; self.draft["red"]["bans"][4] = 1
    self.assertEqual(self.save({"name": "Duplicate", "draft": self.draft})[0], 400)
    self.assertFalse(self.directory.exists())
    for path in ("/api/drafts/../README", "/api/drafts/%2e%2e%2fREADME", "/api/drafts/not-an-id", "/drafts/test.json"):
      with self.subTest(path=path):
        self.assertEqual(self.request("GET", path)[0], 404); self.assertEqual(self.request("DELETE", path)[0], 404)

  def test_storage_failures_return_json_errors(self:ServerTests)->None:
    with patch("storage.atomic_write", side_effect=OSError("disk full")), self.assertLogs(level="WARNING"):
      status, body, _ = self.save({"name": "Draft", "draft": self.draft})
    self.assertEqual(status, 500); self.assertIn("disk", json.loads(body)["error"])
    path:str = f"/api/drafts/{'0' * 32}"
    for method, route, operation in (("GET", "/api/drafts", "list_drafts"),
                                     ("GET", path, "load_draft"), ("DELETE", path, "delete_draft")):
      with self.subTest(method=method), patch(f"storage.{operation}", side_effect=OSError("denied")), self.assertLogs(level="WARNING"):
        status, body, _ = self.request(method, route)
        self.assertEqual(status, 500); self.assertIn("disk", json.loads(body)["error"])

  def test_bootstrap_preserves_sol_ids_and_reports_availability(self:ServerTests)->None:
    status:int; body:bytes; headers:dict[str, str]
    status, body, headers = self.request("GET", "/api/bootstrap")
    data:BootstrapData = json.loads(body)
    self.assertEqual(status, 200); self.assertFalse(data["evaluation_available"])
    wukong:BootstrapChampion = next(champion for champion in data["champions"] if champion["name"] == "Wukong")
    self.assertEqual(wukong["id"], 157); self.assertEqual(wukong["portrait_url"], f"/portraits/{assets.ASSET_VERSION}/157.png")
    self.assertEqual(wukong["splash_url"], f"/splashes/{assets.ASSET_VERSION}/157.jpg")
    missing:BootstrapChampion = next(champion for champion in data["champions"] if champion["name"] == "Aatrox")
    self.assertIsNone(missing["portrait_url"]); self.assertIsNone(missing["splash_url"])
    self.assertEqual(headers["Cache-Control"], "no-store")

  def test_static_routes_and_head(self:ServerTests)->None:
    for path in ("/", "/app.js", "/draft.mjs", "/draft-file.mjs", "/styles.css", "/outfit-latin.woff2"):
      status, body, _ = self.request("GET", path)
      with self.subTest(path=path): self.assertEqual(status, 200); self.assertTrue(body)
    _, body, headers = self.request("GET", "/outfit-latin.woff2")
    self.assertEqual(body[:4], b"wOF2"); self.assertEqual(headers["Content-Type"], "font/woff2")
    for path in ("/", "/outfit-latin.woff2"):
      status, body, headers = self.request("HEAD", path)
      self.assertEqual(status, 200); self.assertEqual(body, b""); self.assertGreater(int(headers["Content-Length"]), 0)

  def test_unexpected_paths_cannot_read_repo_or_cache(self:ServerTests)->None:
    for path in ("/../metadata/champion_ids.py", "/%2e%2e/README.md", "/bridge.py", "/.cache/champion.json",
                 "/portraits/wrong/157.png", f"/portraits/{assets.ASSET_VERSION}/999999.png",
                 "/splashes/wrong/157.jpg", f"/splashes/{assets.ASSET_VERSION}/999999.jpg",
                 f"/splashes/{assets.ASSET_VERSION}/157.png", f"/portraits/{assets.ASSET_VERSION}/157.jpg"):
      with self.subTest(path=path): self.assertEqual(self.request("GET", path)[0], 404)
    self.assertEqual(self.request("POST", "/unknown")[0], 404)

  def test_absent_evaluator_returns_503_after_validation(self:ServerTests)->None:
    self.assertEqual(self.post(self.draft)[0], 503)
    self.assertEqual(self.post({})[0], 400)

  def test_evaluator_receives_exact_partial_snapshot_and_version(self:ServerTests)->None:
    self.draft["blue"]["picks"][3] = 1
    self.draft["red"]["bans"][4] = 157
    received:list[tuple[int, Draft]] = []
    def evaluate(version:int, draft:Draft)->float: received.append((version, draft)); return .64
    self.handler.keywords["evaluator"] = evaluate
    status, body, _ = self.post(self.draft)
    self.assertEqual(status, 200); self.assertEqual(json.loads(body), {"blue_win_probability": .64})
    self.assertEqual(received, [(1, self.draft)])
    self.assertTrue(json.loads(self.request("GET", "/api/bootstrap")[1])["evaluation_available"])

  def test_invalid_probabilities_and_evaluator_value_errors_are_500(self:ServerTests)->None:
    for result in (float("nan"), float("inf"), -.1, 1.1, True, "0.5", None):
      self.handler.keywords["evaluator"] = lambda version, draft: result
      with self.subTest(result=result), redirect_stderr(StringIO()): self.assertEqual(self.post(self.draft)[0], 500)
    def broken(version:int, draft:Draft)->float: raise ValueError("model bug")
    self.handler.keywords["evaluator"] = broken
    with redirect_stderr(StringIO()) as output: self.assertEqual(self.post(self.draft)[0], 500)
    self.assertIn("model bug", output.getvalue())

  def test_bad_json_content_type_and_request_limit(self:ServerTests)->None:
    for path in ("/api/evaluate", "/api/drafts"):
      with self.subTest(path=path):
        self.assertEqual(self.request("POST", path, b"{", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", path, b"{}")[0], 415)
        self.assertEqual(self.request("POST", path, b" " * 16385, {"Content-Type": "application/json"})[0], 413)

  def test_missing_portrait_and_external_download_failure(self:ServerTests)->None:
    self.assertEqual(self.request("GET", f"/portraits/{assets.ASSET_VERSION}/1.png")[0], 404)
    with patch("assets.portrait_bytes", side_effect=OSError("offline")), self.assertLogs(level="WARNING"):
      self.assertEqual(self.request("GET", f"/portraits/{assets.ASSET_VERSION}/157.png")[0], 503)
    with patch("assets.portrait_bytes", return_value=b"fixture") as portrait:
      status, body, headers = self.request("GET", f"/portraits/{assets.ASSET_VERSION}/157.png")
      self.assertEqual((status, body), (200, b"fixture")); self.assertEqual(headers["Content-Type"], "image/png")
      portrait.assert_called_once_with("MonkeyKing.png")

  def test_splash_routes_use_sol_ids_and_handle_unavailable_artwork(self:ServerTests)->None:
    path:str = f"/splashes/{assets.ASSET_VERSION}/157.jpg"
    self.assertEqual(self.request("GET", f"/splashes/{assets.ASSET_VERSION}/1.jpg")[0], 404)
    for error in (OSError("offline"), ValueError("incomplete jpeg")):
      with self.subTest(error=error), patch("assets.splash_bytes", side_effect=error), self.assertLogs(level="WARNING"):
        self.assertEqual(self.request("GET", path)[0], 503)
    with patch("assets.splash_bytes", return_value=b"splash fixture") as splash:
      status, body, headers = self.request("GET", path)
      self.assertEqual((status, body), (200, b"splash fixture")); self.assertEqual(headers["Content-Type"], "image/jpeg")
      self.assertIn("immutable", headers["Cache-Control"]); splash.assert_called_once_with("MonkeyKing.png")

  def test_unknown_cli_version_fails_from_another_directory(self:ServerTests)->None:
    script:Path = Path(__file__).resolve().parents[1] / "run.py"
    result = subprocess.run([sys.executable, str(script), "999999"], cwd="/tmp", capture_output=True, text=True)
    self.assertNotEqual(result.returncode, 0); self.assertIn("Unknown Sol version", result.stderr)

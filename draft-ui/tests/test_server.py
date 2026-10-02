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
from unittest.mock import patch
import assets
import bridge
from draft import Draft
from server import Handler

class ServerTests(unittest.TestCase):
  def setUp(self:ServerTests)->None:
    self.handler = partial(Handler, version=1, champions=bridge.champions(), artwork={"wukong": "MonkeyKing.png"})
    self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler)
    self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
    self.thread.start()
    self.draft:Draft = {side: {"picks": [None] * 5, "bans": [None] * 5} for side in ("blue", "red")}

  def tearDown(self:ServerTests)->None:
    self.server.shutdown(); self.server.server_close(); self.thread.join()

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

  def test_bootstrap_preserves_sol_ids_and_reports_availability(self:ServerTests)->None:
    status:int; body:bytes; headers:dict[str, str]
    status, body, headers = self.request("GET", "/api/bootstrap")
    data:dict[str, object] = json.loads(body)
    self.assertEqual(status, 200); self.assertFalse(data["evaluation_available"])
    wukong:dict[str, object] = next(champion for champion in data["champions"] if champion["name"] == "Wukong")
    self.assertEqual(wukong["id"], 157); self.assertEqual(wukong["portrait_url"], f"/portraits/{assets.ASSET_VERSION}/157.png")
    self.assertEqual(headers["Cache-Control"], "no-store")

  def test_static_routes_and_head(self:ServerTests)->None:
    for path in ("/", "/app.js", "/draft.mjs", "/styles.css", "/outfit-latin.woff2"):
      status, body, _ = self.request("GET", path)
      with self.subTest(path=path): self.assertEqual(status, 200); self.assertTrue(body)
    _, body, headers = self.request("GET", "/outfit-latin.woff2")
    self.assertEqual(body[:4], b"wOF2"); self.assertEqual(headers["Content-Type"], "font/woff2")
    for path in ("/", "/outfit-latin.woff2"):
      status, body, headers = self.request("HEAD", path)
      self.assertEqual(status, 200); self.assertEqual(body, b""); self.assertGreater(int(headers["Content-Length"]), 0)

  def test_unexpected_paths_cannot_read_repo_or_cache(self:ServerTests)->None:
    for path in ("/../metadata/champion_ids.py", "/%2e%2e/README.md", "/bridge.py", "/.cache/champion.json",
                 "/portraits/wrong/157.png", f"/portraits/{assets.ASSET_VERSION}/999999.png"):
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
    self.assertEqual(self.request("POST", "/api/evaluate", b"{", {"Content-Type": "application/json"})[0], 400)
    self.assertEqual(self.request("POST", "/api/evaluate", b"{}")[0], 415)
    self.assertEqual(self.request("POST", "/api/evaluate", b" " * 16385, {"Content-Type": "application/json"})[0], 413)

  def test_missing_portrait_and_external_download_failure(self:ServerTests)->None:
    self.assertEqual(self.request("GET", f"/portraits/{assets.ASSET_VERSION}/1.png")[0], 404)
    with patch("assets.portrait_bytes", side_effect=OSError("offline")), self.assertLogs(level="WARNING"):
      self.assertEqual(self.request("GET", f"/portraits/{assets.ASSET_VERSION}/157.png")[0], 503)
    with patch("assets.portrait_bytes", return_value=b"fixture") as portrait:
      status, body, headers = self.request("GET", f"/portraits/{assets.ASSET_VERSION}/157.png")
      self.assertEqual((status, body), (200, b"fixture")); self.assertEqual(headers["Content-Type"], "image/png")
      portrait.assert_called_once_with("MonkeyKing.png")

  def test_unknown_cli_version_fails_from_another_directory(self:ServerTests)->None:
    script:Path = Path(__file__).resolve().parents[1] / "run.py"
    result = subprocess.run([sys.executable, str(script), "999999"], cwd="/tmp", capture_output=True, text=True)
    self.assertNotEqual(result.returncode, 0); self.assertIn("Unknown Sol version", result.stderr)

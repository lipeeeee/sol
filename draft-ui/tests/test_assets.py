from __future__ import annotations
import base64
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import IncompleteRead
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict
from unittest.mock import patch
import assets

class CatalogueEntry(TypedDict):
  name:str
  image:dict[str, str]

class CatalogueData(TypedDict):
  version:str
  data:dict[str, CatalogueEntry]

PNG:bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4ZkAAAAASUVORK5CYII=")
JPEG:bytes = base64.b64decode(
  "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/"
  "2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAA"
  "AQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRol"
  "JicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW"
  "19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdh"
  "cRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJma"
  "oqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5/ooooA//2Q==")
CATALOGUE:bytes = json.dumps({"version": assets.ASSET_VERSION, "data": {
  "MonkeyKing": {"name": "Wukong", "image": {"full": "MonkeyKing.png"}},
  "Chogath": {"name": "Cho'Gath", "image": {"full": "Chogath.png"}}
}}).encode()

class AssetTests(unittest.TestCase):
  def setUp(self:AssetTests)->None:
    self.temporary = TemporaryDirectory(); self.cache = Path(self.temporary.name)
  def tearDown(self:AssetTests)->None: self.temporary.cleanup()

  def test_catalogue_maps_display_names_and_caches_once(self:AssetTests)->None:
    with patch("assets.fetch_bytes", return_value=CATALOGUE) as fetch:
      artwork:dict[str, str] = assets.load_catalogue(self.cache)
      self.assertEqual(artwork, {"wukong": "MonkeyKing.png", "chogath": "Chogath.png"})
      self.assertEqual(assets.load_catalogue(self.cache), artwork); fetch.assert_called_once()

  def test_catalogue_rejects_wrong_version_paths_and_collisions(self:AssetTests)->None:
    for mutate in ("version", "filename", "collision", "empty"):
      data:CatalogueData = json.loads(CATALOGUE)
      if mutate == "version": data["version"] = "wrong"
      if mutate == "filename": data["data"]["Chogath"]["image"]["full"] = "../Chogath.png"
      if mutate == "collision": data["data"]["Chogath"]["name"] = "Wu kong"
      if mutate == "empty": data["data"] = {}
      with self.subTest(mutate=mutate), self.assertRaises(ValueError): assets.decode_catalogue(json.dumps(data).encode())

  def test_offline_catalogue_falls_back_without_caching_invalid_data(self:AssetTests)->None:
    with patch("assets.fetch_bytes", side_effect=OSError("offline")), self.assertLogs(level="WARNING"):
      self.assertEqual(assets.load_catalogue(self.cache), {})
    with patch("assets.fetch_bytes", return_value=b"not json"), self.assertLogs(level="WARNING"):
      self.assertEqual(assets.load_catalogue(self.cache), {})
    self.assertFalse((self.cache / "champion.json").exists())

  def test_portrait_cache_works_offline(self:AssetTests)->None:
    with patch("assets.fetch_bytes", return_value=PNG) as fetch:
      self.assertEqual(assets.portrait_bytes("MonkeyKing.png", self.cache), PNG); fetch.assert_called_once()
    with patch("assets.fetch_bytes", side_effect=OSError("offline")) as fetch:
      self.assertEqual(assets.portrait_bytes("MonkeyKing.png", self.cache), PNG); fetch.assert_not_called()

  def test_splash_uses_the_catalogue_filename_and_cached_copies_work_offline(self:AssetTests)->None:
    with patch("assets.fetch_bytes", return_value=JPEG) as fetch:
      self.assertEqual(assets.splash_bytes("MonkeyKing.png", self.cache), JPEG)
      fetch.assert_called_once_with("https://ddragon.leagueoflegends.com/cdn/img/champion/splash/MonkeyKing_0.jpg")
    self.assertEqual((self.cache / "splashes" / "MonkeyKing_0.jpg").read_bytes(), JPEG)
    with patch("assets.fetch_bytes", side_effect=OSError("offline")) as fetch:
      self.assertEqual(assets.splash_bytes("MonkeyKing.png", self.cache), JPEG); fetch.assert_not_called()

  def test_invalid_and_interrupted_splashes_are_not_cached(self:AssetTests)->None:
    for data in (b"not jpeg", PNG, JPEG[:-5]):
      with self.subTest(data=data[:4]), patch("assets.fetch_bytes", return_value=data), self.assertRaises(ValueError):
        assets.splash_bytes("MonkeyKing.png", self.cache)
    with patch("assets.fetch_bytes", side_effect=IncompleteRead(b"partial")), self.assertRaises(IncompleteRead):
      assets.splash_bytes("MonkeyKing.png", self.cache)
    self.assertFalse((self.cache / "splashes").exists())

  def test_invalid_splash_cache_is_repaired(self:AssetTests)->None:
    path:Path = self.cache / "splashes" / "MonkeyKing_0.jpg"; path.parent.mkdir(); path.write_bytes(b"broken")
    with patch("assets.fetch_bytes", return_value=JPEG), self.assertLogs(level="WARNING"):
      self.assertEqual(assets.splash_bytes("MonkeyKing.png", self.cache), JPEG)
    self.assertEqual(path.read_bytes(), JPEG)

  def test_bad_and_interrupted_portraits_are_not_published(self:AssetTests)->None:
    for result in (b"not png", PNG[:-5]):
      with patch("assets.fetch_bytes", return_value=result), self.assertRaises(ValueError):
        assets.portrait_bytes("MonkeyKing.png", self.cache)
      self.assertFalse((self.cache / "MonkeyKing.png").exists())
    with patch("assets.fetch_bytes", side_effect=IncompleteRead(b"partial")), self.assertRaises(IncompleteRead):
      assets.portrait_bytes("MonkeyKing.png", self.cache)
    self.assertEqual(list(self.cache.iterdir()), [])

  def test_invalid_cache_is_repaired(self:AssetTests)->None:
    path:Path = self.cache / "MonkeyKing.png"; path.write_bytes(b"broken")
    with patch("assets.fetch_bytes", return_value=PNG), self.assertLogs(level="WARNING"):
      self.assertEqual(assets.portrait_bytes("MonkeyKing.png", self.cache), PNG)
    self.assertEqual(path.read_bytes(), PNG)

  def test_atomic_failure_preserves_old_file_and_cleans_temporary(self:AssetTests)->None:
    path:Path = self.cache / "portrait.png"; path.write_bytes(b"original")
    with patch.object(Path, "replace", side_effect=OSError("write failed")), self.assertRaises(OSError):
      assets.atomic_write(path, b"replacement")
    self.assertEqual(path.read_bytes(), b"original"); self.assertEqual(list(self.cache.iterdir()), [path])

  def test_concurrent_cache_writes_publish_whole_files(self:AssetTests)->None:
    path:Path = self.cache / "portrait.png"
    with ThreadPoolExecutor(max_workers=4) as workers:
      list(workers.map(lambda _: assets.atomic_write(path, PNG), range(8)))
    self.assertEqual(path.read_bytes(), PNG); self.assertEqual(list(self.cache.iterdir()), [path])

  def test_download_checks_declared_length(self:AssetTests)->None:
    class Response(BytesIO):
      headers:dict[str, str]
    response = Response(PNG); response.headers = {"Content-Length": str(len(PNG) + 1)}
    with patch("assets.urlopen", return_value=response), self.assertRaises(OSError): assets.fetch_bytes("https://example.test")

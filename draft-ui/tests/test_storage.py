from __future__ import annotations
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from draft import DraftJSON, validate_draft
import storage

class StorageTests(unittest.TestCase):
  def setUp(self:StorageTests)->None:
    self.temporary = TemporaryDirectory(); self.directory = Path(self.temporary.name) / "drafts"
    self.favorites_path = Path(self.temporary.name) / "favorites.json"
    self.ids:frozenset[int] = frozenset({1, 2, 157})
    self.draft:DraftJSON = {
      "blue": {"picks": [None] * 5, "bans": [None] * 5},
      "red": {"picks": [None] * 5, "bans": [None] * 5},
    }
    self.draft["blue"]["picks"][3] = 1; self.draft["red"]["bans"][4] = 157

  def tearDown(self:StorageTests)->None: self.temporary.cleanup()

  def test_snapshots_round_trip_on_disk_without_overwriting_the_same_name(self:StorageTests)->None:
    self.assertEqual(storage.list_drafts(self.ids, self.directory), [])
    first:storage.SavedDraft = storage.save_draft("  First draft  ", validate_draft(self.draft, self.ids), self.directory)
    self.draft["blue"]["picks"][3] = 2
    second:storage.SavedDraft = storage.save_draft("First draft", validate_draft(self.draft, self.ids), self.directory)
    restored:storage.SavedDraft = storage.load_draft(first["id"], self.ids, self.directory)
    self.assertEqual(restored["name"], "First draft"); self.assertNotIn("sol_version", restored)
    self.assertEqual(restored["draft"]["blue"]["picks"], [None, None, None, 1, None])
    self.assertEqual(restored["draft"]["red"]["bans"], [None, None, None, None, 157])
    self.assertEqual(json.loads((self.directory / f"{first['id']}.json").read_bytes()), restored)
    self.assertEqual([saved["id"] for saved in storage.list_drafts(self.ids, self.directory)], [second["id"], first["id"]])

  def test_deletion_only_removes_the_selected_snapshot(self:StorageTests)->None:
    first:storage.SavedDraft = storage.save_draft("First", validate_draft(self.draft, self.ids), self.directory)
    second:storage.SavedDraft = storage.save_draft("Second", validate_draft(self.draft, self.ids), self.directory)
    storage.delete_draft(first["id"], self.directory)
    with self.assertRaises(FileNotFoundError): storage.load_draft(first["id"], self.ids, self.directory)
    self.assertEqual(storage.load_draft(second["id"], self.ids, self.directory), second)
    with self.assertRaises(FileNotFoundError): storage.delete_draft(first["id"], self.directory)

  def test_ids_cannot_escape_the_storage_directory(self:StorageTests)->None:
    outside:Path = self.directory.parent / "outside.json"; outside.write_text("keep")
    for draft_id in ("../outside", str(outside), "", "a" * 31, "A" * 32):
      with self.subTest(draft_id=draft_id), self.assertRaises(ValueError):
        storage.load_draft(draft_id, self.ids, self.directory)
      with self.subTest(draft_id=draft_id), self.assertRaises(ValueError): storage.delete_draft(draft_id, self.directory)
    self.assertEqual(outside.read_text(), "keep")
    saved:storage.SavedDraft = storage.save_draft("../outside", validate_draft(self.draft, self.ids), self.directory)
    self.assertTrue((self.directory / f"{saved['id']}.json").is_file()); self.assertEqual(outside.read_text(), "keep")

  def test_invalid_files_do_not_hide_or_remove_valid_snapshots(self:StorageTests)->None:
    saved:storage.SavedDraft = storage.save_draft("Valid", validate_draft(self.draft, self.ids), self.directory)
    broken:Path = self.directory / f"{'0' * 32}.json"; broken.write_bytes(b"{")
    (self.directory / "unrelated.json").write_bytes(b"{")
    with self.assertLogs(level="WARNING"): self.assertEqual(storage.list_drafts(self.ids, self.directory), [saved])
    self.assertEqual(broken.read_bytes(), b"{")
    for field, value in (("id", "1" * 32), ("name", ""), ("saved_at", "bad"), ("draft", {})):
      broken.write_text(json.dumps({**saved, "id": broken.stem, field: value}))
      with self.subTest(field=field), self.assertRaises(ValueError): storage.load_draft(broken.stem, self.ids, self.directory)

  def test_older_versioned_files_load_without_exposing_the_version(self:StorageTests)->None:
    saved:storage.SavedDraft = storage.save_draft("Older", validate_draft(self.draft, self.ids), self.directory)
    path:Path = self.directory / f"{saved['id']}.json"
    path.write_text(json.dumps({**saved, "sol_version": 2}))
    self.assertEqual(storage.load_draft(saved["id"], self.ids, self.directory), saved)
    self.assertEqual(storage.list_drafts(self.ids, self.directory), [saved])
    path.write_text(json.dumps({**saved, "sol_version": True}))
    with self.assertRaises(ValueError): storage.load_draft(saved["id"], self.ids, self.directory)

  def test_failed_writes_leave_existing_saves_and_no_temporary_files(self:StorageTests)->None:
    saved:storage.SavedDraft = storage.save_draft("Existing", validate_draft(self.draft, self.ids), self.directory)
    with patch.object(Path, "replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
      storage.save_draft("New", validate_draft(self.draft, self.ids), self.directory)
    self.assertEqual(storage.list_drafts(self.ids, self.directory), [saved])
    self.assertEqual(len(list(self.directory.iterdir())), 1)

  def test_concurrent_saves_keep_every_snapshot(self:StorageTests)->None:
    with ThreadPoolExecutor(max_workers=4) as workers:
      saved:list[storage.SavedDraft] = list(workers.map(
        lambda index: storage.save_draft(f"Draft {index}", validate_draft(self.draft, self.ids), self.directory), range(8)))
    self.assertEqual({draft["id"] for draft in storage.list_drafts(self.ids, self.directory)}, {draft["id"] for draft in saved})
    self.assertEqual(len(list(self.directory.iterdir())), 8)

  def test_favorites_persist_independently_and_updates_are_idempotent(self:StorageTests)->None:
    self.assertEqual(storage.load_favorites(self.ids, self.favorites_path), [])
    self.assertFalse(self.favorites_path.exists())
    for champion_id in (157, 1, 157): storage.set_favorite(champion_id, True, self.ids, self.favorites_path)
    self.assertEqual(json.loads(self.favorites_path.read_bytes()), [1, 157])
    self.assertEqual(storage.load_favorites(self.ids, self.favorites_path), [1, 157])
    for _ in range(2): self.assertEqual(storage.set_favorite(1, False, self.ids, self.favorites_path), [157])
    self.assertEqual(storage.set_favorite(157, False, self.ids, self.favorites_path), [])
    self.assertFalse(self.directory.exists())

  def test_concurrent_favorites_preserve_other_champions(self:StorageTests)->None:
    ids:frozenset[int] = frozenset(range(1, 25))
    with ThreadPoolExecutor(max_workers=8) as workers:
      list(workers.map(lambda champion_id: storage.set_favorite(champion_id, True, ids, self.favorites_path), ids))
      self.assertEqual(storage.load_favorites(ids, self.favorites_path), sorted(ids))
      list(workers.map(lambda champion_id: storage.set_favorite(champion_id, False, ids, self.favorites_path), range(1, 13)))
    self.assertEqual(storage.load_favorites(ids, self.favorites_path), list(range(13, 25)))

  def test_invalid_favorites_are_rejected_without_overwriting_the_file(self:StorageTests)->None:
    for value in (None, {}, [True], [1.0], ["1"], [999], [1, 1]):
      self.favorites_path.write_text(json.dumps(value))
      original:bytes = self.favorites_path.read_bytes()
      with self.subTest(value=value), self.assertRaises(ValueError): storage.load_favorites(self.ids, self.favorites_path)
      with self.subTest(value=value), self.assertRaises(ValueError): storage.set_favorite(2, True, self.ids, self.favorites_path)
      self.assertEqual(self.favorites_path.read_bytes(), original)
    self.favorites_path.unlink()
    for champion_id, favorite in ((True, True), (999, True), (1, 1)):
      with self.subTest(champion_id=champion_id, favorite=favorite), self.assertRaises(ValueError):
        storage.set_favorite(champion_id, favorite, self.ids, self.favorites_path)
    self.assertFalse(self.favorites_path.exists())

  def test_failed_favorite_writes_preserve_the_previous_file(self:StorageTests)->None:
    storage.set_favorite(1, True, self.ids, self.favorites_path)
    with patch.object(Path, "replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
      storage.set_favorite(2, True, self.ids, self.favorites_path)
    self.assertEqual(storage.load_favorites(self.ids, self.favorites_path), [1])
    self.assertEqual(list(self.favorites_path.parent.iterdir()), [self.favorites_path])

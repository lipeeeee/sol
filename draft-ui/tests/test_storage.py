from __future__ import annotations
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from draft import Draft
import storage

class StorageTests(unittest.TestCase):
  def setUp(self:StorageTests)->None:
    self.temporary = TemporaryDirectory(); self.directory = Path(self.temporary.name) / "drafts"
    self.ids:frozenset[int] = frozenset({1, 2, 157})
    self.draft:Draft = {side: {"picks": [None] * 5, "bans": [None] * 5} for side in ("blue", "red")}
    self.draft["blue"]["picks"][3] = 1; self.draft["red"]["bans"][4] = 157

  def tearDown(self:StorageTests)->None: self.temporary.cleanup()

  def test_snapshots_round_trip_on_disk_without_overwriting_the_same_name(self:StorageTests)->None:
    self.assertEqual(storage.list_drafts(self.ids, self.directory), [])
    first:storage.SavedDraft = storage.save_draft("  First draft  ", self.draft, 1, self.directory)
    self.draft["blue"]["picks"][3] = 2
    second:storage.SavedDraft = storage.save_draft("First draft", self.draft, 2, self.directory)
    restored:storage.SavedDraft = storage.load_draft(first["id"], self.ids, self.directory)
    self.assertEqual(restored["name"], "First draft"); self.assertEqual(restored["sol_version"], 1)
    self.assertEqual(restored["draft"]["blue"]["picks"], [None, None, None, 1, None])
    self.assertEqual(restored["draft"]["red"]["bans"], [None, None, None, None, 157])
    self.assertEqual(json.loads((self.directory / f"{first['id']}.json").read_bytes()), restored)
    self.assertEqual([saved["id"] for saved in storage.list_drafts(self.ids, self.directory)], [second["id"], first["id"]])

  def test_deletion_only_removes_the_selected_snapshot(self:StorageTests)->None:
    first:storage.SavedDraft = storage.save_draft("First", self.draft, 1, self.directory)
    second:storage.SavedDraft = storage.save_draft("Second", self.draft, 1, self.directory)
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
    saved:storage.SavedDraft = storage.save_draft("../outside", self.draft, 1, self.directory)
    self.assertTrue((self.directory / f"{saved['id']}.json").is_file()); self.assertEqual(outside.read_text(), "keep")

  def test_invalid_files_do_not_hide_or_remove_valid_snapshots(self:StorageTests)->None:
    saved:storage.SavedDraft = storage.save_draft("Valid", self.draft, 1, self.directory)
    broken:Path = self.directory / f"{'0' * 32}.json"; broken.write_bytes(b"{")
    (self.directory / "unrelated.json").write_bytes(b"{")
    with self.assertLogs(level="WARNING"): self.assertEqual(storage.list_drafts(self.ids, self.directory), [saved])
    self.assertEqual(broken.read_bytes(), b"{")
    for field, value in (("id", "1" * 32), ("name", ""), ("sol_version", True), ("saved_at", "bad"), ("draft", {})):
      broken.write_text(json.dumps({**saved, "id": broken.stem, field: value}))
      with self.subTest(field=field), self.assertRaises(ValueError): storage.load_draft(broken.stem, self.ids, self.directory)

  def test_failed_writes_leave_existing_saves_and_no_temporary_files(self:StorageTests)->None:
    saved:storage.SavedDraft = storage.save_draft("Existing", self.draft, 1, self.directory)
    with patch.object(Path, "replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
      storage.save_draft("New", self.draft, 1, self.directory)
    self.assertEqual(storage.list_drafts(self.ids, self.directory), [saved])
    self.assertEqual(len(list(self.directory.iterdir())), 1)

  def test_concurrent_saves_keep_every_snapshot(self:StorageTests)->None:
    with ThreadPoolExecutor(max_workers=4) as workers:
      saved:list[storage.SavedDraft] = list(workers.map(
        lambda index: storage.save_draft(f"Draft {index}", self.draft, 1, self.directory), range(8)))
    self.assertEqual({draft["id"] for draft in storage.list_drafts(self.ids, self.directory)}, {draft["id"] for draft in saved})
    self.assertEqual(len(list(self.directory.iterdir())), 8)

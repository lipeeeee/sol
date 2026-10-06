from __future__ import annotations
import unittest
from copy import deepcopy
import bridge
from draft import Draft, validate_draft

class DraftTests(unittest.TestCase):
  def setUp(self:DraftTests)->None:
    self.ids:frozenset[int] = frozenset({1, 2, 3, 157})
    self.draft:Draft = {
      "blue": {"picks": [None] * 5, "bans": [None] * 5},
      "red": {"picks": [None] * 5, "bans": [None] * 5},
    }

  def test_preserves_empty_and_arbitrary_partial_slots(self:DraftTests)->None:
    self.assertIs(validate_draft(self.draft, self.ids), self.draft)
    self.draft["blue"]["picks"][3] = 1
    self.draft["red"]["picks"][4] = 157
    self.draft["red"]["bans"][2] = 2
    before:Draft = deepcopy(self.draft)
    self.assertIs(validate_draft(self.draft, self.ids), self.draft)
    self.assertEqual(self.draft, before)

  def test_rejects_bad_shapes(self:DraftTests)->None:
    cases:list[object] = [None, [], {}, {**self.draft, "version": 1}]
    short:Draft = deepcopy(self.draft); short["blue"]["bans"].pop(); cases.append(short)
    cases.append({**self.draft, "red": {**self.draft["red"], "picks": {}}})
    cases.append({**self.draft, "red": {**self.draft["red"], "roles": []}})
    for value in cases:
      with self.subTest(value=value), self.assertRaises(ValueError): validate_draft(value, self.ids)

  def test_rejects_unknown_boolean_and_duplicate_ids(self:DraftTests)->None:
    for kind in ("picks", "bans"):
      for value in (True, False, 1.0, "1", 99, {}, []):
        invalid = {**self.draft, "blue": {**self.draft["blue"], kind: [value, None, None, None, None]}}
        with self.subTest(kind=kind, value=value), self.assertRaises(ValueError): validate_draft(invalid, self.ids)
    self.draft["blue"]["bans"][0] = 1
    self.draft["red"]["picks"][4] = 1
    with self.assertRaises(ValueError): validate_draft(self.draft, self.ids)

  def test_rejects_pick_objects_with_role_assignments(self:DraftTests)->None:
    for role in (None, "top", "mid"):
      invalid = {**self.draft, "blue": {**self.draft["blue"], "picks": [{"champion_id": 1, "role": role}, None, None, None, None]}}
      with self.subTest(role=role), self.assertRaises(ValueError): validate_draft(invalid, self.ids)

  def test_bridge_uses_sol_ids_and_has_no_fake_roles_or_evaluator(self:DraftTests)->None:
    champions:list[bridge.Champion] = bridge.champions()
    self.assertEqual({champion["name"]: champion["id"] for champion in champions}, bridge.CHAMPION_IDS)
    self.assertTrue(all(champion["roles"] == [] for champion in champions))
    self.assertIsNone(bridge.evaluator)
    bridge.validate_version(1)
    for version in (0, -1, 999999):
      with self.subTest(version=version), self.assertRaises(ValueError): bridge.validate_version(version)

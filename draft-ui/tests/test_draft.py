from __future__ import annotations
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch
import bridge
from draft import DraftJSON, validate_draft, serialize_draft
from sol.utils import TeamEnum as TE

class DraftTests(unittest.TestCase):
  def setUp(self:DraftTests)->None:
    self.ids:frozenset[int] = frozenset({1, 2, 3, 157})
    self.draft:DraftJSON = {
      "blue": {"picks": [None] * 5, "bans": [None] * 5},
      "red": {"picks": [None] * 5, "bans": [None] * 5},
    }

  def test_preserves_empty_and_arbitrary_partial_slots(self:DraftTests)->None:
    self.assertEqual(serialize_draft(validate_draft(self.draft, self.ids)), self.draft)
    self.draft["blue"]["picks"][3] = 1
    self.draft["red"]["picks"][4] = 157
    self.draft["red"]["bans"][2] = 2
    before:DraftJSON = deepcopy(self.draft)
    self.assertEqual(serialize_draft(validate_draft(self.draft, self.ids)), self.draft)
    self.assertEqual(self.draft, before)

  def test_enum_teams_round_trip_without_mutating_json(self:DraftTests)->None:
    before = deepcopy(self.draft)
    parsed = validate_draft(self.draft, self.ids)
    self.assertEqual(list(parsed["teams"]), [TE.BLUE, TE.RED])
    self.assertTrue(all(isinstance(side, TE) for side in parsed["teams"]))
    self.assertEqual(serialize_draft(parsed), before)
    self.assertEqual(self.draft, before)

  def test_inference_preserves_blue_then_red_order(self:DraftTests)->None:
    from sol.inference import prepare_tensors
    inputs = [{"champion": {TE.RED: [6, 7, 8, 9, 10], TE.BLUE: [1, 2, 3, 4, 5]}}]
    self.assertEqual(prepare_tensors(inputs, "cpu")["champion"].tolist(), [list(range(1, 11))])

  def test_rejects_bad_shapes(self:DraftTests)->None:
    cases:list[object] = [None, [], {}, {**self.draft, "version": 1}]
    short:DraftJSON = deepcopy(self.draft); short["blue"]["bans"].pop(); cases.append(short)
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

  def test_validates_draft_context(self:DraftTests)->None:
    for first_pick in (0, 1):
      value = {**self.draft, "firstPick": first_pick, "patch": "16.18"}
      self.assertEqual(serialize_draft(validate_draft(value, self.ids)), value)
    for first_pick in (True, "1", None, -1, 2):
      with self.subTest(firstPick=first_pick), self.assertRaises(ValueError):
        validate_draft({**self.draft, "firstPick": first_pick}, self.ids)
    for patch_value in (True, 16.18, "", " ", "x" * 17):
      with self.subTest(patch=patch_value), self.assertRaises(ValueError):
        validate_draft({**self.draft, "patch": patch_value}, self.ids)

  def test_bridge_uses_sol_ids_and_has_no_fake_roles(self:DraftTests)->None:
    champions:list[bridge.Champion] = bridge.champions()
    self.assertEqual({champion["name"]: champion["id"] for champion in champions}, bridge.CHAMPION_IDS)
    self.assertTrue(all(champion["roles"] == [] for champion in champions))
    self.assertTrue(callable(bridge.evaluator))
    bridge.validate_version(1)
    for version in (0, -1, 999999):
      with self.subTest(version=version), self.assertRaises(ValueError): bridge.validate_version(version)

  def test_evaluator_passes_all_draft_inputs_to_inference(self:DraftTests)->None:
    self.draft["blue"]["picks"] = [1, 2, 3, 4, 5]
    self.draft["red"]["picks"] = [6, 7, 8, 9, 10]
    self.draft["red"]["bans"][0] = 157
    self.draft["firstPick"], self.draft["patch"] = 0, "16.18"
    model = object(); output = Mock(); output.item.return_value = -.35
    with patch("sol.inference.load_model", return_value=model) as load, \
         patch("sol.inference.predict", return_value={"win_logits": output, "auxiliary": object()}) as predict:
      self.assertEqual(bridge.evaluator(1, validate_draft(self.draft, frozenset(range(1, 158)))), -.35)
    load.assert_called_once_with(1)
    predict.assert_called_once_with(model, [{"champion": {TE.BLUE: [1, 2, 3, 4, 5], TE.RED: [6, 7, 8, 9, 10]},
      "ban": {TE.BLUE: [None] * 5, TE.RED: [157, None, None, None, None]}, "firstPick": 0, "patch": "16.18"}])

  def test_legacy_drafts_default_to_blue_first_and_an_unknown_patch(self:DraftTests)->None:
    output = Mock(); output.item.return_value = 0.0
    with patch("sol.inference.load_model"), patch("sol.inference.predict", return_value={"win_logits": output}) as predict:
      bridge.evaluator(1, validate_draft(self.draft, frozenset(range(1, 158))))
    inputs = predict.call_args.args[1][0]
    self.assertEqual(inputs["firstPick"], 1); self.assertIsNone(inputs["patch"])

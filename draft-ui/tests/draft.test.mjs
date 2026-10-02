import test from "node:test";
import assert from "node:assert/strict";
import {emptyDraft, slotChampion, occupiedSlots, assignChampion, clearSlot, swapSlots} from "../draft.mjs";

const champions = new Map([
  [1, {id: 1, name: "Aatrox", roles: ["top"]}], [2, {id: 2, name: "Ahri", roles: ["mid"]}],
  [3, {id: 3, name: "Akali", roles: ["mid", "top"]}]
]);
const slot = (side, index, kind = "picks") => ({side, index, kind});

test("empty drafts own independent slot arrays and sessions", () => {
  const draft = emptyDraft(); draft.blue.picks[0] = 1; draft.blue.bans[0] = 2;
  assert.equal(draft.blue.picks[1], null); assert.equal(draft.red.picks[0], null);
  assert.equal(draft.red.bans[0], null); assert.equal(emptyDraft().blue.picks[0], null);
  for (const team of Object.values(draft)) for (const slots of Object.values(team)) assert.equal(slots.length, 5);
});

test("any late pick or ban can be assigned without preceding slots", () => {
  const draft = emptyDraft();
  assignChampion(draft, slot("red", 4), 2, champions);
  assignChampion(draft, slot("blue", 3, "bans"), 1, champions);
  assert.equal(draft.red.picks[4], 2); assert.equal(draft.red.picks[0], null);
  assert.equal(draft.blue.bans[3], 1); assert.equal(draft.blue.bans[0], null);
});

test("champions cannot duplicate across picks, bans or sides", () => {
  const draft = emptyDraft(); assignChampion(draft, slot("red", 4), 2, champions);
  assert.throws(() => assignChampion(draft, slot("blue", 0), 2, champions), /another slot/);
  assert.throws(() => assignChampion(draft, slot("blue", 0, "bans"), 2, champions), /another slot/);
  assert.equal(assignChampion(draft, slot("red", 4), 2, champions), false);
  assert.equal(occupiedSlots(draft).size, 1);
});

test("assignment rejects unknown IDs and bad slots before changing state", () => {
  const draft = emptyDraft(), before = structuredClone(draft);
  for (const id of [99, true, "1", 1.5]) assert.throws(() => assignChampion(draft, slot("blue", 0), id, champions));
  for (const target of [slot("blue", -1), slot("blue", 5), slot("purple", 0), slot("blue", 0, "other")]) {
    assert.throws(() => assignChampion(draft, target, 1, champions));
  }
  assert.deepEqual(draft, before);
});

test("draft snapshots contain only champion IDs regardless of preferred roles", () => {
  const draft = emptyDraft();
  assignChampion(draft, slot("blue", 0), 2, champions); assignChampion(draft, slot("blue", 1), 3, champions);
  assert.deepEqual(draft.blue.picks, [2, 3, null, null, null]);
});

test("replacement releases the previous champion for another slot", () => {
  const draft = emptyDraft(); assignChampion(draft, slot("blue", 0), 1, champions);
  assignChampion(draft, slot("blue", 0), 2, champions);
  assert.equal(draft.blue.picks[0], 2); assert.equal(occupiedSlots(draft).has(1), false);
  assignChampion(draft, slot("red", 0, "bans"), 1, champions);
});

test("clearing any pick or ban returns its champion to the pool without shifting slots", () => {
  for (const side of ["blue", "red"]) for (const kind of ["picks", "bans"]) {
    const draft = emptyDraft(), target = slot(side, 4, kind);
    assignChampion(draft, slot(side, 0, kind), 1, champions); assignChampion(draft, target, 2, champions);
    assert.equal(clearSlot(draft, target), true); assert.equal(slotChampion(draft, target), null);
    assert.equal(occupiedSlots(draft).has(2), false); assert.equal(draft[side][kind][0], 1);
    assert.equal(clearSlot(draft, target), false);
    assignChampion(draft, slot(side === "blue" ? "red" : "blue", 2), 2, champions);
  }
});

test("swapping a filled pick into an empty slot moves only its champion", () => {
  const draft = emptyDraft();
  assignChampion(draft, slot("blue", 1), 2, champions); assignChampion(draft, slot("red", 4), 3, champions);
  assert.equal(swapSlots(draft, slot("blue", 1), slot("blue", 0)), true);
  assert.deepEqual(draft.blue.picks, [2, null, null, null, null]);
  assert.equal(draft.red.picks[4], 3); assert.deepEqual([...occupiedSlots(draft).keys()], [2, 3]);
});

test("an empty source exchanges with a filled target", () => {
  const draft = emptyDraft();
  assignChampion(draft, slot("blue", 1), 2, champions); assignChampion(draft, slot("red", 4), 3, champions);
  assert.equal(swapSlots(draft, slot("blue", 0), slot("blue", 1)), true);
  assert.deepEqual(draft.blue.picks, [2, null, null, null, null]);
  assert.equal(draft.red.picks[4], 3); assert.equal(occupiedSlots(draft).size, 2);
});

test("filled slots exchange champions across picks, bans and sides without duplicates", () => {
  for (const target of [slot("blue", 1), slot("red", 4), slot("blue", 3, "bans"), slot("red", 0, "bans")]) {
    const draft = emptyDraft(), source = slot("blue", 0);
    assignChampion(draft, source, 1, champions); assignChampion(draft, target, 2, champions);
    assert.equal(swapSlots(draft, source, target), true);
    assert.equal(slotChampion(draft, source), 2); assert.equal(slotChampion(draft, target), 1);
    assert.equal(occupiedSlots(draft).size, 2);
    for (const team of Object.values(draft)) for (const slots of Object.values(team)) assert.equal(slots.length, 5);
  }
});

test("swap no-ops and invalid targets leave the draft unchanged", () => {
  const draft = emptyDraft(); assignChampion(draft, slot("blue", 0), 1, champions);
  const before = structuredClone(draft);
  assert.equal(swapSlots(draft, slot("blue", 0), slot("blue", 0)), false);
  assert.equal(swapSlots(draft, slot("blue", 1), slot("red", 4)), false);
  assert.throws(() => swapSlots(draft, slot("blue", 0), slot("red", 5)), /Slot index/);
  assert.throws(() => swapSlots(draft, slot("purple", 0), slot("blue", 0)), /Unknown draft slot/);
  assert.deepEqual(draft, before);
});

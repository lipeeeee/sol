/** @typedef {"blue"|"red"} Side */
/** @typedef {"picks"|"bans"} Kind */
/** @typedef {{side: Side, kind: Kind, index: number}} Slot */
/** @typedef {{picks: (number|null)[], bans: (number|null)[]}} Team */
/** @typedef {{blue: Team, red: Team}} Draft */
/** @typedef {{id: number, name: string, roles: string[], portrait_url?: string|null}} Champion */

function assert(condition, message) { if (!condition) throw new Error(message); }
function assertSlot(slot) {
  assert(["blue", "red"].includes(slot.side) && ["picks", "bans"].includes(slot.kind), "Unknown draft slot");
  assert(Number.isInteger(slot.index) && slot.index >= 0 && slot.index < 5, "Slot index must be between 0 and 4");
}

/** @returns {Draft} */
export function emptyDraft() {
  const team = () => ({picks: Array(5).fill(null), bans: Array(5).fill(null)});
  return {blue: team(), red: team()};
}

/** @param {Draft} draft @param {Slot} slot @returns {number|null} */
export function slotChampion(draft, slot) {
  assertSlot(slot);
  return draft[slot.side][slot.kind][slot.index];
}

/** @param {Draft} draft @returns {Map<number, Slot>} */
export function occupiedSlots(draft) {
  const occupied = new Map();
  for (const side of ["blue", "red"]) for (const kind of ["picks", "bans"]) {
    draft[side][kind].forEach((id, index) => {
      if (id === null) return;
      assert(!occupied.has(id), "Champions must remain unique across the draft");
      occupied.set(id, {side, kind, index});
    });
  }
  return occupied;
}

/** @param {Draft} draft @param {Slot} slot @param {number} id @param {Map<number, Champion>} champions @returns {boolean} */
export function assignChampion(draft, slot, id, champions) {
  assertSlot(slot);
  assert(Number.isInteger(id) && champions.has(id), "Champion ID must exist in Sol's catalogue");
  const current = slotChampion(draft, slot), holder = occupiedSlots(draft).get(id);
  assert(!holder || (holder.side === slot.side && holder.kind === slot.kind && holder.index === slot.index),
    "Champion is already used in another slot");
  if (current === id) return false;
  draft[slot.side][slot.kind][slot.index] = id;
  assert(slotChampion(draft, slot) === id && occupiedSlots(draft).has(id), "Assignment must fill the selected slot uniquely");
  return true;
}

/** @param {Draft} draft @param {Slot} slot @returns {boolean} */
export function clearSlot(draft, slot) {
  assertSlot(slot);
  if (slotChampion(draft, slot) === null) return false;
  draft[slot.side][slot.kind][slot.index] = null;
  assert(slotChampion(draft, slot) === null, "Clearing must empty the selected slot");
  return true;
}

/** @param {Draft} draft @param {Slot} source @param {Slot} target @returns {boolean} */
export function swapSlots(draft, source, target) {
  const first = slotChampion(draft, source), second = slotChampion(draft, target);
  if (first === second) return false;
  draft[source.side][source.kind][source.index] = second;
  draft[target.side][target.kind][target.index] = first;
  assert(slotChampion(draft, source) === second && slotChampion(draft, target) === first, "Swapping must exchange both slots");
  return true;
}

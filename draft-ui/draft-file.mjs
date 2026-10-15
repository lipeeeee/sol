import {emptyDraft} from "./draft.mjs";

function fields(value, expected) {
  return value && typeof value === "object" && !Array.isArray(value) &&
    Object.keys(value).length === expected.length && expected.every(key => Object.hasOwn(value, key));
}

function mapDraft(value, resolve) {
  if (!fields(value, ["blue", "red"])) throw new Error("Expected blue and red teams.");
  const result = emptyDraft(), used = new Set();
  for (const side of ["blue", "red"]) {
    if (!fields(value[side], ["picks", "bans"])) throw new Error(`Expected picks and bans for ${side}.`);
    for (const kind of ["picks", "bans"]) {
      const slots = value[side][kind];
      if (!Array.isArray(slots) || slots.length !== 5) throw new Error(`Expected five ${side} ${kind}.`);
      result[side][kind] = slots.map(champion => {
        if (champion === null) return null;
        const resolved = resolve(champion);
        if (used.has(resolved)) throw new Error("A champion can only appear once in a draft.");
        used.add(resolved);
        return resolved;
      });
    }
  }
  return result;
}

export function exportDraft(draft, champions) {
  const named = mapDraft(draft, id => {
    const champion = champions.get(id);
    if (!champion) throw new Error("Unknown champion in the draft.");
    return champion.name;
  });
  return JSON.stringify({draft: named}, null, 2) + "\n";
}

export function importDraft(text, champions) {
  if (text.length > 16384) throw new Error("Draft files must be smaller than 16 KiB.");
  let saved;
  try { saved = JSON.parse(text); }
  catch { throw new Error("Choose a valid JSON draft file."); }
  const versioned = value => Number.isInteger(value) && value > 0;
  const exportFile = fields(saved, ["draft"]) ||
    (fields(saved, ["sol_version", "draft"]) && versioned(saved.sol_version));
  const savedFile = fields(saved, ["id", "name", "saved_at", "draft"]) ||
    (fields(saved, ["id", "name", "sol_version", "saved_at", "draft"]) && versioned(saved.sol_version));
  if (savedFile) {
    if (!/^[0-9a-f]{32}$/.test(saved.id) || typeof saved.name !== "string" || !saved.name.trim() ||
      saved.name.length > 80 || typeof saved.saved_at !== "string" || Number.isNaN(Date.parse(saved.saved_at))) {
      throw new Error("This is not a Sol draft file.");
    }
    return mapDraft(saved.draft, id => {
      if (!Number.isInteger(id) || !champions.has(id)) throw new Error(`Unknown champion ID: ${String(id)}.`);
      return id;
    });
  }
  if (!exportFile) throw new Error("This is not a Sol draft file.");
  const byName = new Map([...champions.values()].map(champion => [champion.name, champion.id]));
  return mapDraft(saved.draft, name => {
    if (typeof name !== "string" || !byName.has(name)) throw new Error(`Unknown champion name: ${String(name)}.`);
    return byName.get(name);
  });
}

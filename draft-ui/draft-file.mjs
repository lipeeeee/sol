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

export function exportDraft(draft, champions, version) {
  const named = mapDraft(draft, id => {
    const champion = champions.get(id);
    if (!champion) throw new Error("Unknown champion in the draft.");
    return champion.name;
  });
  return JSON.stringify({sol_version: version, draft: named}, null, 2) + "\n";
}

export function importDraft(text, champions, version) {
  if (text.length > 16384) throw new Error("Draft files must be smaller than 16 KiB.");
  let saved;
  try { saved = JSON.parse(text); }
  catch { throw new Error("Choose a valid JSON draft file."); }
  if (!fields(saved, ["sol_version", "draft"]) || !Number.isInteger(saved.sol_version) || saved.sol_version < 1) {
    throw new Error("This is not a Sol draft file.");
  }
  if (saved.sol_version !== version) throw new Error(`This draft needs Sol ${saved.sol_version}; this editor runs Sol ${version}.`);
  const byName = new Map([...champions.values()].map(champion => [champion.name, champion.id]));
  return mapDraft(saved.draft, name => {
    if (typeof name !== "string" || !byName.has(name)) throw new Error(`Unknown champion name: ${String(name)}.`);
    return byName.get(name);
  });
}

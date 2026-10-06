import {emptyDraft, slotChampion, occupiedSlots, assignChampion, clearSlot, swapSlots} from "./draft.mjs";
import {exportDraft, importDraft} from "./draft-file.mjs";

/** @typedef {import('./draft.mjs').Slot} Slot */
/** @typedef {import('./draft.mjs').Champion} Champion */
const state = {draft: emptyDraft(), selected: null, selectedChampion: null, search: "", role: "", view: "normal",
  revision: 0, pending: false, probability: null, error: null};
let bootstrap = null;
const storage = {drafts: [], pending: false, error: null, message: ""};
/** @type {Map<number, Champion>} */
const champions = new Map();
const championButtons = new Map(), pickElements = new Map(), banElements = new Map(), failedPortraits = new Set();
const splashPreloads = new Map();
const dom = Object.fromEntries(["sol-version", "clear-draft", "pool-heading", "search", "champions", "empty-search",
  "evaluation-status", "probability", "blue-probability", "red-probability",
  "probability-bar", "blue-bar", "save-draft-form", "draft-name", "save-draft", "saved-drafts",
  "load-draft", "delete-draft", "storage-status", "export-draft", "import-draft", "draft-file",
  "draft-dialog", "draft-dialog-title", "close-draft-dialog",
  "export-panel", "import-panel", "download-draft", "choose-draft-file"
].map(id => [id, document.getElementById(id)]));
if (Object.values(dom).some(element => !element)) throw new Error("The draft page is missing required controls");

function normalise(text) { return text.toLowerCase().replace(/[^a-z0-9]/g, ""); }
function key(slot) { return slot ? `${slot.side}:${slot.kind}:${slot.index}` : ""; }
function label(slot) {
  return slot.kind === "picks" ? `${slot.side === "blue" ? "B" : "R"}${slot.index + 1}` :
    `${slot.side === "blue" ? "Blue" : "Red"} ban ${slot.index + 1}`;
}
function eventSlot(element) {
  return {side: element.dataset.side, kind: element.dataset.kind, index: Number(element.dataset.index)};
}

function setPortrait(container, champion, fallback, splash = false) {
  const image = container.querySelector("img"), placeholder = container.querySelector("span");
  const urls = splash ? [champion?.splash_url, champion?.portrait_url] : [champion?.portrait_url];
  const url = urls.find(url => url && !failedPortraits.has(url));
  if (placeholder) placeholder.textContent = fallback;
  if (splash) {
    const portrait = champion?.portrait_url;
    container.style.backgroundImage = portrait && !failedPortraits.has(portrait) ? `url("${portrait}")` : "";
  }
  if (!url) { image.hidden = true; image.removeAttribute("src"); image.onload = image.onerror = null; return; }
  if (image.getAttribute("src") === url) return;
  image.hidden = splash;
  image.onload = splash ? () => {
    if (image.getAttribute("src") === url) image.hidden = false;
  } : null;
  image.onerror = () => {
    if (image.getAttribute("src") !== url) return;
    failedPortraits.add(url); setPortrait(container, champion, fallback, splash);
  };
  image.src = url;
  if (splash && image.complete && image.naturalWidth > 0) image.hidden = false;
}

function preloadSplash(champion) {
  const url = champion?.splash_url;
  if (!url || failedPortraits.has(url)) return;
  if (splashPreloads.has(url)) {
    const image = splashPreloads.get(url);
    splashPreloads.delete(url); splashPreloads.set(url, image);
    return;
  }
  const image = new Image();
  splashPreloads.set(url, image);
  image.onload = () => { if (image.decode) image.decode().catch(() => {}); };
  image.onerror = () => { failedPortraits.add(url); splashPreloads.delete(url); };
  image.src = url;
  if (splashPreloads.size > 20) splashPreloads.delete(splashPreloads.keys().next().value);
}

function createSlots() {
  for (const side of ["blue", "red"]) for (let index = 0; index < 5; index++) {
    const slot = {side, kind: "picks", index};
    const card = document.getElementById("pick-template").content.firstElementChild.cloneNode(true);
    const button = card.querySelector("button");
    Object.assign(button.dataset, slot);
    card.querySelector(".slot-label").textContent = label(slot);
    document.getElementById(`${side}-picks`).append(card); pickElements.set(key(slot), card);
    const banSlot = {side, kind: "bans", index};
    const ban = document.getElementById("ban-template").content.firstElementChild.cloneNode(true);
    Object.assign(ban.dataset, banSlot); ban.querySelector(".ban-label").textContent = index + 1;
    document.getElementById(`${side}-bans`).append(ban); banElements.set(key(banSlot), ban);
  }
}

function createChampions() {
  const fragment = document.createDocumentFragment();
  for (const champion of champions.values()) {
    const button = document.getElementById("champion-template").content.firstElementChild.cloneNode(true);
    button.dataset.id = champion.id; button.querySelector(".champion-caption").textContent = champion.name;
    setPortrait(button.querySelector(".champion-art"), champion, champion.name.slice(0, 2).toUpperCase());
    fragment.append(button); championButtons.set(champion.id, button);
  }
  dom.champions.append(fragment);
}

function renderTeams() {
  for (const side of ["blue", "red"]) {
    for (let index = 0; index < 5; index++) {
      const slot = {side, kind: "picks", index}, id = state.draft[side].picks[index], card = pickElements.get(key(slot));
      const champion = champions.get(id), button = card.querySelector("button");
      const selected = key(slot) === key(state.selected);
      card.classList.toggle("selected", selected); card.classList.toggle("filled", Boolean(champion));
      button.setAttribute("aria-pressed", selected); button.setAttribute("aria-label", `${label(slot)}: ${champion?.name ?? "empty"}`);
      card.querySelector(".champion-name").textContent = champion?.name ?? "";
      card.querySelector(".champion-name").title = champion?.name ?? "";
      setPortrait(card.querySelector(".slot-art"), champion, label(slot), true);
      const banSlot = {side, kind: "bans", index}, ban = banElements.get(key(banSlot));
      const banned = champions.get(state.draft[side].bans[index]), banSelected = key(banSlot) === key(state.selected);
      ban.classList.toggle("selected", banSelected); ban.classList.toggle("filled", Boolean(banned));
      ban.setAttribute("aria-pressed", banSelected); ban.setAttribute("aria-label", `${label(banSlot)}: ${banned?.name ?? "empty"}`);
      ban.title = `${label(banSlot)}: ${banned?.name ?? "empty"}`;
      setPortrait(ban.querySelector(".slot-art"), banned, "—");
    }
  }
  dom["clear-draft"].disabled = occupiedSlots(state.draft).size === 0;
}

function renderRoster() {
  const occupied = occupiedSlots(state.draft), search = normalise(state.search);
  let visible = 0;
  for (const champion of champions.values()) {
    const button = championButtons.get(champion.id), holder = occupied.get(champion.id);
    button.hidden = !normalise(champion.name).includes(search) || (state.role && !champion.roles.includes(state.role));
    const current = holder && key(holder) === key(state.selected);
    const selected = champion.id === state.selectedChampion || Boolean(current);
    button.disabled = Boolean(holder && !current); button.classList.toggle("chosen", selected);
    button.setAttribute("aria-label", holder ? `${champion.name}, assigned to ${label(holder)}` : champion.name);
    button.setAttribute("aria-pressed", selected); button.title = button.getAttribute("aria-label");
    if (!button.hidden) visible++;
  }
  dom["pool-heading"].textContent = `Champion pool(${visible})`;
  dom["empty-search"].hidden = visible !== 0;
}

function renderEvaluation() {
  const available = bootstrap?.evaluation_available;
  dom["evaluation-status"].classList.toggle("error", Boolean(state.error));
  dom["evaluation-status"].textContent = state.error ?? (state.pending ? "Evaluating this draft…" : !bootstrap ?
    "Loading Sol…" : !available ? `No evaluator is connected to Sol ${bootstrap.sol_version} yet.` :
    state.probability !== null ? "Estimated win probability" : "Draft changes are evaluated automatically.");
  dom.probability.hidden = state.probability === null;
  if (state.probability !== null) {
    dom["blue-probability"].textContent = `${(state.probability * 100).toFixed(1)}%`;
    dom["red-probability"].textContent = `${((1 - state.probability) * 100).toFixed(1)}%`;
    dom["blue-bar"].style.width = `${state.probability * 100}%`;
    dom["probability-bar"].setAttribute("aria-label", `Estimated win probability: blue ${dom["blue-probability"].textContent}, red ${dom["red-probability"].textContent}`);
  }
}

function draftChanged() {
  state.selected = null; state.selectedChampion = null;
  state.revision++; state.probability = null; state.error = null;
  storage.message = "";
  renderTeams(); renderRoster(); renderEvaluation(); renderStorage(); evaluateDraft();
}

function suggestedDraftName() {
  const picks = [["B1", state.draft.blue.picks[0]], ["R1", state.draft.red.picks[0]],
    ["R2", state.draft.red.picks[1]]];
  const named = picks.filter(([, id]) => id !== null && champions.has(id))
    .map(([slot, id]) => `${slot} ${champions.get(id).name}`);
  return (named.length ? named.join(" · ") : `Draft ${new Date().toLocaleString()}`).slice(0, 80);
}

function renderStorage() {
  dom["draft-name"].disabled = storage.pending;
  dom["save-draft"].disabled = !bootstrap || storage.pending;
  dom["saved-drafts"].disabled = storage.pending || storage.drafts.length === 0;
  for (const id of ["load-draft", "delete-draft"]) dom[id].disabled = !bootstrap || storage.pending || !dom["saved-drafts"].value;
  dom["export-draft"].disabled = !bootstrap;
  dom["download-draft"].disabled = !bootstrap;
  dom["import-draft"].disabled = !bootstrap || storage.pending;
  dom["choose-draft-file"].disabled = !bootstrap || storage.pending;
  dom["storage-status"].classList.toggle("error", Boolean(storage.error));
  const message = storage.error ?? (storage.pending ? "Working…" : storage.message);
  dom["storage-status"].textContent = message;
  dom["storage-status"].hidden = !message;
}

function showDraftDialog(mode) {
  if (dom["draft-dialog"].open) return;
  const importing = mode === "import";
  dom["draft-dialog-title"].textContent = importing ? "Import Draft" : "Save Draft";
  dom["export-panel"].hidden = importing;
  dom["import-panel"].hidden = !importing;
  if (!importing) {
    dom["draft-name"].value = "";
    dom["draft-name"].placeholder = suggestedDraftName();
  }
  storage.message = ""; renderStorage();
  dom["draft-dialog"].showModal();
  const firstControl = importing ? (storage.drafts.length ? "saved-drafts" : "choose-draft-file") : "draft-name";
  dom[firstControl].focus();
}

function renderSavedDrafts(selected = dom["saved-drafts"].value) {
  const options = storage.drafts.map(saved => {
    const option = document.createElement("option"); option.value = saved.id;
    option.textContent = `${saved.name} · ${new Date(saved.saved_at).toLocaleString()}`;
    return option;
  });
  if (!options.length) {
    const placeholder = document.createElement("option");
    placeholder.value = ""; placeholder.textContent = "No saved drafts";
    options.push(placeholder);
  }
  dom["saved-drafts"].replaceChildren(...options);
  dom["saved-drafts"].value = storage.drafts.some(saved => saved.id === selected) ? selected : "";
}

/** @param {string} url @param {RequestInit} [options] @returns {Promise<object>} */
async function storageRequest(url, options) {
  const response = await fetch(url, options), result = await response.json();
  if (!response.ok) throw new Error(result.error || "Could not access saved drafts.");
  return result;
}

/** @param {()=>Promise<void>} action @returns {Promise<void>} */
async function storageAction(action) {
  if (storage.pending) return;
  storage.pending = true; storage.error = null; storage.message = ""; renderStorage();
  try { await action(); }
  catch (error) { storage.error = error.message || String(error); }
  finally { storage.pending = false; renderStorage(); }
}

/** @param {Slot} slot @param {number} id @returns {void} */
function placeChampion(slot, id) {
  if (assignChampion(state.draft, slot, id, champions)) { draftChanged(); return; }
  state.selected = null; state.selectedChampion = null; renderTeams(); renderRoster();
}

/** @returns {Promise<void>} */
async function evaluateDraft() {
  if (state.pending || !bootstrap?.evaluation_available) return;
  const revision = state.revision;
  state.pending = true; state.probability = null; state.error = null; renderEvaluation();
  try {
    const response = await fetch("/api/evaluate", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(state.draft)
    });
    const result = await response.json();
    if (revision !== state.revision) return;
    if (!response.ok) throw new Error(result.error);
    state.probability = result.blue_win_probability;
  } catch (error) {
    if (revision === state.revision) state.error = String(error);
  } finally {
    state.pending = false;
    if (revision !== state.revision) evaluateDraft();
    else renderEvaluation();
  }
}

document.querySelector(".workspace").addEventListener("click", event => {
  const button = event.target.closest("button[data-kind]");
  if (!button) return;
  const slot = eventSlot(button), source = state.selected;
  if (state.selectedChampion !== null) { placeChampion(slot, state.selectedChampion); return; }
  if (source && key(source) !== key(slot) && swapSlots(state.draft, source, slot)) {
    draftChanged(); return;
  }
  state.selected = key(source) === key(slot) ? null : slot;
  renderTeams(); renderRoster();
});
document.querySelector(".workspace").addEventListener("contextmenu", event => {
  const button = event.target.closest("button[data-kind], button[data-id]");
  if (!button) return;
  const slot = button.dataset.kind ? eventSlot(button) : occupiedSlots(state.draft).get(Number(button.dataset.id));
  if (!slot || slotChampion(state.draft, slot) === null) return;
  event.preventDefault();
  if (clearSlot(state.draft, slot)) draftChanged();
});
document.querySelector(".workspace").addEventListener("keydown", event => {
  if (event.key !== "Delete") return;
  const button = event.target.closest("button[data-kind]");
  if (!button) return;
  event.preventDefault();
  if (clearSlot(state.draft, eventSlot(button))) draftChanged();
});
dom.champions.addEventListener("click", event => {
  const button = event.target.closest("button[data-id]");
  if (!button) return;
  const id = Number(button.dataset.id);
  preloadSplash(champions.get(id));
  if (state.selected) { placeChampion(state.selected, id); return; }
  state.selectedChampion = state.selectedChampion === id ? null : id;
  renderRoster();
});
for (const eventName of ["pointerover", "focusin"]) dom.champions.addEventListener(eventName, event => {
  const button = event.target.closest("button[data-id]");
  if (button && !button.disabled) preloadSplash(champions.get(Number(button.dataset.id)));
});
document.querySelector(".filters").addEventListener("click", event => {
  const button = event.target.closest("button[data-role]");
  if (!button || button.disabled) return;
  state.role = state.role === button.dataset.role ? "" : button.dataset.role;
  for (const filter of document.querySelectorAll(".filters button")) {
    filter.setAttribute("aria-pressed", filter.dataset.role === state.role);
  }
  renderRoster();
});
document.querySelector(".view-modes").addEventListener("click", event => {
  const button = event.target.closest("button[data-view]");
  if (!button) return;
  state.view = button.dataset.view; dom.champions.classList.toggle("compact", state.view === "compact");
  for (const mode of document.querySelectorAll(".view-modes button")) mode.setAttribute("aria-pressed", mode === button);
});
dom.search.addEventListener("input", () => { state.search = dom.search.value; renderRoster(); });
dom["draft-name"].addEventListener("input", renderStorage);
dom["saved-drafts"].addEventListener("change", renderStorage);
dom["save-draft-form"].addEventListener("submit", event => {
  event.preventDefault();
  if (dom["save-draft"].disabled) return;
  const name = dom["draft-name"].value.trim() || suggestedDraftName();
  const revision = state.revision, draft = JSON.stringify({name, draft: state.draft});
  storageAction(async () => {
    const saved = await storageRequest("/api/drafts", {method: "POST", headers: {"Content-Type": "application/json"}, body: draft});
    storage.drafts.unshift(saved); renderSavedDrafts(saved.id);
    storage.message = `Saved “${saved.name}”.${revision !== state.revision ? " Newer edits are not saved." : ""}`;
  });
});
function loadSelectedDraft() {
  if (!bootstrap || storage.pending || !dom["saved-drafts"].value) return;
  const id = dom["saved-drafts"].value, revision = state.revision;
  storageAction(async () => {
    const saved = await storageRequest(`/api/drafts/${id}`);
    if (revision !== state.revision) throw new Error("The draft changed while loading. Load again to replace it.");
    state.draft = saved.draft; draftChanged();
    storage.message = `Loaded “${saved.name}”.`;
    dom["draft-dialog"].close();
  });
}
dom["load-draft"].addEventListener("click", loadSelectedDraft);
dom["saved-drafts"].addEventListener("dblclick", loadSelectedDraft);
dom["saved-drafts"].addEventListener("keydown", event => {
  if (event.key === "Enter") { event.preventDefault(); loadSelectedDraft(); }
});
dom["delete-draft"].addEventListener("click", () => {
  if (dom["delete-draft"].disabled) return;
  const id = dom["saved-drafts"].value;
  storageAction(async () => {
    await storageRequest(`/api/drafts/${id}`, {method: "DELETE"});
    storage.drafts = storage.drafts.filter(saved => saved.id !== id); renderSavedDrafts();
  });
});
dom["export-draft"].addEventListener("click", () => {
  if (!dom["export-draft"].disabled) showDraftDialog("export");
});
dom["import-draft"].addEventListener("click", () => {
  if (!dom["import-draft"].disabled) showDraftDialog("import");
});
dom["close-draft-dialog"].addEventListener("click", () => dom["draft-dialog"].close());
dom["draft-dialog"].addEventListener("click", event => {
  if (event.target === dom["draft-dialog"]) dom["draft-dialog"].close();
});
dom["download-draft"].addEventListener("click", () => {
  if (dom["download-draft"].disabled) return;
  try {
    const data = exportDraft(state.draft, champions);
    const url = URL.createObjectURL(new Blob([data], {type: "application/json"}));
    const link = document.createElement("a");
    const name = dom["draft-name"].value.trim() || suggestedDraftName();
    const filename = name.normalize("NFKD").toLowerCase().replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "").slice(0, 60) || "draft";
    link.href = url; link.download = `${filename}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
    storage.error = null; storage.message = "Draft JSON downloaded.";
  } catch (error) { storage.error = error.message || String(error); }
  renderStorage();
});
dom["choose-draft-file"].addEventListener("click", () => {
  if (!dom["choose-draft-file"].disabled) dom["draft-file"].click();
});
dom["draft-file"].addEventListener("change", () => {
  const file = dom["draft-file"].files?.[0];
  if (!file || !bootstrap) return;
  const revision = state.revision;
  storageAction(async () => {
    try {
      if (file.size > 16384) throw new Error("Draft files must be smaller than 16 KiB.");
      const imported = importDraft(await file.text(), champions);
      if (revision !== state.revision) throw new Error("The draft changed while loading. Import again to replace it.");
      state.draft = imported; draftChanged();
      storage.message = `Imported “${file.name}”.`;
      dom["draft-dialog"].close();
    } finally { dom["draft-file"].value = ""; }
  });
});
dom["clear-draft"].addEventListener("click", () => {
  state.draft = emptyDraft(); dom["draft-name"].value = ""; draftChanged();
});
async function start() {
  createSlots(); renderTeams();
  try {
    const response = await fetch("/api/bootstrap");
    if (!response.ok) throw new Error("Could not load the draft editor");
    bootstrap = await response.json();
    for (const champion of bootstrap.champions) champions.set(champion.id, champion);
    createChampions(); renderRoster(); renderEvaluation();
    const hasRoles = bootstrap.champions.some(champion => champion.roles.length > 0);
    for (const button of document.querySelectorAll(".filters button[data-role]")) {
      button.disabled = !hasRoles;
    }
    dom["sol-version"].textContent = `Sol ${bootstrap.sol_version}`;
    document.title = `Sol ${bootstrap.sol_version}`;
    evaluateDraft();
    storageAction(async () => {
      const result = await storageRequest("/api/drafts"); storage.drafts = result.drafts; renderSavedDrafts();
    });
  } catch (error) {
    dom["empty-search"].textContent = "Could not load champions. Refresh to try again."; dom["empty-search"].hidden = false;
    dom["evaluation-status"].textContent = String(error); dom["evaluation-status"].classList.add("error");
  }
}
start();

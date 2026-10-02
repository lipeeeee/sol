import {emptyDraft, slotChampion, occupiedSlots, assignChampion, clearSlot, swapSlots} from "./draft.mjs";

/** @typedef {import('./draft.mjs').Slot} Slot */
/** @typedef {import('./draft.mjs').Champion} Champion */
const state = {draft: emptyDraft(), selected: null, selectedChampion: null, search: "", role: "", view: "normal",
  revision: 0, pending: false, probability: null, error: null};
let bootstrap = null;
/** @type {Map<number, Champion>} */
const champions = new Map();
const championButtons = new Map(), pickElements = new Map(), banElements = new Map(), failedPortraits = new Set();
const dom = Object.fromEntries(["sol-version", "clear-draft", "pool-heading", "search", "champions", "empty-search",
  "evaluation-status", "probability", "blue-probability", "red-probability",
  "probability-bar", "blue-bar"].map(id => [id, document.getElementById(id)]));
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

function setPortrait(container, champion, fallback) {
  const image = container.querySelector("img"), placeholder = container.querySelector("span");
  const url = champion?.portrait_url;
  placeholder.textContent = fallback;
  if (!url || failedPortraits.has(url)) { image.hidden = true; image.removeAttribute("src"); return; }
  image.hidden = false;
  if (image.getAttribute("src") !== url) image.src = url;
  image.onerror = () => { failedPortraits.add(url); image.hidden = true; };
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
      setPortrait(card.querySelector(".slot-art"), champion, label(slot));
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
  renderTeams(); renderRoster(); renderEvaluation(); evaluateDraft();
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
  if (state.selected) { placeChampion(state.selected, id); return; }
  state.selectedChampion = state.selectedChampion === id ? null : id;
  renderRoster();
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
dom["clear-draft"].addEventListener("click", () => {
  state.draft = emptyDraft(); draftChanged();
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
    evaluateDraft();
  } catch (error) {
    dom["empty-search"].textContent = "Could not load champions. Refresh to try again."; dom["empty-search"].hidden = false;
    dom["evaluation-status"].textContent = String(error); dom["evaluation-status"].classList.add("error");
  }
}
start();

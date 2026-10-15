import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createContext, runInContext} from "node:vm";
import * as draft from "../draft.mjs";
import * as draftFile from "../draft-file.mjs";

const source = readFileSync(new URL("../app.js", import.meta.url), "utf8").replace(/^import[^\n]+\n/gm, "");
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const ids = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map(([, id]) => id));
const championNames = ["Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Ambessa", "Amumu", "Anivia", "Annie", "Aphelios", "Ashe", "Aurelion Sol"];
const fullDraft = () => ({blue: {picks: [1, 2, 3, 4, 5], bans: Array(5).fill(null)},
  red: {picks: [6, 7, 8, 9, 10], bans: Array(5).fill(null)}, firstPick: 1, patch: null});
const tick = () => new Promise(resolve => setImmediate(resolve));
function element(fragment = false) {
  const queries = new Map(), attributes = new Map();
  let hidden = false;
  return {
    fragment, children: [], dataset: {}, style: {}, value: "", open: false, listeners: new Map(), classList: {toggle() {}},
    offsetWidth: 150, offsetHeight: 36, selectionStart: null, selectionEnd: null,
    get hidden() { return hidden; },
    set hidden(value) { hidden = Boolean(value); },
    append(child) { this.children.push(...(child.fragment ? child.children : [child])); },
    replaceChildren(...children) { this.children = children; },
    querySelector(selector) { if (!queries.has(selector)) queries.set(selector, element()); return queries.get(selector); },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.get(name) ?? null; },
    removeAttribute(name) { attributes.delete(name); },
    set src(value) { attributes.set("src", value); },
    get src() { return attributes.get("src") ?? ""; },
    addEventListener(name, handler) { this.listeners.set(name, handler); },
    dispatchEvent(event) { this.listeners.get(event.type)?.(event); return true; },
    closest() { return null; },
    getBoundingClientRect() { return {left: 100, top: 200, right: 164, bottom: 264}; },
    setRangeText(text, start, end) {
      this.value = this.value.slice(0, start) + text + this.value.slice(end);
      this.selectionStart = this.selectionEnd = start + text.length;
    },
    cloneNode() { return element(); },
    click() { this.clicked = (this.clicked ?? 0) + 1; },
    showModal() { this.open = true; },
    close() { this.open = false; },
    focus() { this.focused = true; this.onFocus?.(); }
  };
}
async function setup(available = true, saved = [], listError = null, favoriteIds = [], favoritesError = null) {
  const elements = new Map(), requests = [], storageRequests = [], favoriteRequests = [], downloads = [], exportedBlobs = [], preloads = [];
  class PreloadImage {
    constructor() { preloads.push(this); }
  }
  const get = id => {
    if (!elements.has(id)) {
      const created = element(); created.onFocus = () => { document.activeElement = created; };
      if (["search", "draft-name", "saved-drafts", "patch", "first-pick"].includes(id)) created.closest = selector =>
        selector.includes(["saved-drafts", "first-pick"].includes(id) ? "select" : "input") ? created : null;
      elements.set(id, created);
    }
    return elements.get(id);
  };
  for (const id of ["pick-template", "ban-template", "champion-template"]) get(id).content = {firstElementChild: element()};
  get("champion-menu").hidden = true;
  const document = {...element(), documentElement: {clientWidth: 1920, clientHeight: 1080},
    getElementById: id => ids.has(id) ? get(id) : null, querySelector: get, querySelectorAll: () => [],
    createDocumentFragment: () => element(true), createElement: tag => {
      const created = element(); if (tag === "a") downloads.push(created); return created;
    }}, window = element();
  const fetch = (url, options) => {
    if (url === "/api/bootstrap") return Promise.resolve({ok: true, json: async () => ({sol_version: 1, patch: null,
      evaluation_available: available, champions: championNames.map((name, i) => ({id: i + 1, name, roles: [],
        portrait_url: `/portraits/16.19.1/${i + 1}.png`, splash_url: `/splashes/16.19.1/${i + 1}.jpg`}))})});
    if (url === "/api/drafts" && !options) return Promise.resolve({ok: !listError,
      json: async () => listError ? {error: listError} : {drafts: saved.map(({draft, ...metadata}) => metadata)}});
    if (url === "/api/favorites") return Promise.resolve({ok: !favoritesError,
      json: async () => favoritesError ? {error: favoritesError} : {favorites: favoriteIds}});
    if (url.startsWith("/api/favorites/")) return new Promise((resolve, reject) => favoriteRequests.push({url,
      method: options.method, resolve, reject}));
    if (url.startsWith("/api/drafts")) return new Promise((resolve, reject) => storageRequests.push({url,
      method: options?.method ?? "GET", body: options?.body ? JSON.parse(options.body) : null, resolve, reject}));
    assert.equal(url, "/api/evaluate");
    return new Promise((resolve, reject) => requests.push({draft: JSON.parse(options.body), resolve, reject}));
  };
  const context = createContext({document, window, fetch, ...draft, ...draftFile, Blob, Event, Image: PreloadImage,
    URL: {createObjectURL(blob) { exportedBlobs.push(blob); return "blob:draft"; }, revokeObjectURL() {}},
    setTimeout(callback) { callback(); }});
  runInContext(source, context); await tick();
  const emit = (container, type, target, key, details = {}) => {
    const event = {target: {closest: () => target}, key, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, ...details};
    get(container).listeners.get(type)(event); return event;
  };
  const emitDocument = (type, target = get("brand"), details = {}) => {
    const event = {target, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...details};
    document.listeners.get(type)(event); return event;
  };
  const slot = (side, kind, index) => {
    const card = get(`${side}-${kind}`).children[index]; return kind === "picks" ? card.querySelector("button") : card;
  };
  const clickSlot = (side, kind, index) => emit(".workspace", "click", slot(side, kind, index));
  const choose = (id, side, kind, index) => {
    emit("champions", "click", get("champions").children[id - 1]); clickSlot(side, kind, index);
  };
  const respond = async (index, logit = 0) => {
    requests[index].resolve({ok: true, json: async () => ({logit})}); await tick();
  };
  return {get, document, requests, storageRequests, favoriteRequests, downloads, exportedBlobs, preloads, choose, clickSlot, respond,
    state: runInContext("state", context),
    setPatch: value => { get("patch").value = value; emit("patch", "change", get("patch")); },
    setFirstPick: value => { get("first-pick").value = String(value); emit("first-pick", "change", get("first-pick")); },
    fill: () => { for (const side of ["blue", "red"]) for (let index = 0; index < 5; index++) {
      choose((side === "blue" ? 1 : 6) + index, side, "picks", index);
    } },
    save: name => { get("draft-name").value = name; emit("draft-name", "input", get("draft-name"));
      emit("save-draft-form", "submit", get("save-draft-form")); },
    selectSaved: id => { get("saved-drafts").value = id; emit("saved-drafts", "change", get("saved-drafts")); },
    load: () => emit("load-draft", "click", get("load-draft")),
    doubleClickSaved: () => emit("saved-drafts", "dblclick", get("saved-drafts")),
    deleteSaved: () => emit("delete-draft", "click", get("delete-draft")),
    respondStorage: async (index, value, ok = true) => {
      storageRequests[index].resolve({ok, json: async () => value}); await tick(); },
    respondFavorite: async (index, value, ok = true) => {
      favoriteRequests[index].resolve({ok, json: async () => value}); await tick(); },
    favoriteMenu: (id, clientX = 150, clientY = 220) =>
      emit("champions", "contextmenu", get("champions").children[id - 1], undefined, {clientX, clientY}),
    toggleFavorite: () => emit("toggle-favorite", "click", get("toggle-favorite")),
    type: (key, target, details = {}) => emitDocument("keydown", target, {key, ...details}),
    paste: (text, target) => emitDocument("paste", target, {clipboardData: {getData: () => text}}),
    outsideClick: () => emitDocument("pointerdown"),
    scroll: () => emitDocument("scroll"),
    openExport: () => emit("export-draft", "click", get("export-draft")),
    openImport: () => emit("import-draft", "click", get("import-draft")),
    closeDialog: () => emit("close-draft-dialog", "click", get("close-draft-dialog")),
    exportFile: (name = "") => { emit("export-draft", "click", get("export-draft"));
      get("draft-name").value = name;
      emit("download-draft", "click", get("download-draft")); },
    importFile: async (name, contents) => {
      emit("import-draft", "click", get("import-draft"));
      emit("choose-draft-file", "click", get("choose-draft-file"));
      get("draft-file").files = [{name, size: Buffer.byteLength(contents), text: async () => contents}];
      emit("draft-file", "change", get("draft-file")); await tick();
    },
    clear: (side, kind, index, type = "contextmenu") => emit(".workspace", type, slot(side, kind, index), "Delete"),
    hover: id => emit("champions", "pointerover", get("champions").children[id - 1]),
    reset: () => emit("clear-draft", "click", get("clear-draft"))};
}

test("only complete drafts evaluate, and edits clear or refresh the signed evaluation", async () => {
  const app = await setup(); assert.equal(app.requests.length, 0);
  app.fill(); assert.equal(app.requests.length, 1); assert.deepEqual(app.requests[0].draft, fullDraft());
  await app.respond(0, Math.log(.55 / .45));
  assert.equal(app.get("evaluation-score").textContent, "+1.00");
  assert.equal(app.get("evaluation-result").hidden, false);
  assert.equal(app.get("blue-bar").style.width, "55%");
  app.clickSlot("blue", "picks", 1); app.clickSlot("red", "picks", 1);
  assert.equal(app.requests[1].draft.blue.picks[1], 7); assert.equal(app.requests[1].draft.red.picks[1], 2);
  assert.equal(app.get("evaluation-result").hidden, true); await app.respond(1, -Math.log(.55 / .45));
  assert.equal(app.get("evaluation-score").textContent, "-1.00");
  app.choose(11, "blue", "picks", 0); assert.equal(app.requests[2].draft.blue.picks[0], 11); await app.respond(2);
  assert.equal(app.get("evaluation-score").textContent, "0.00");
  app.clear("blue", "picks", 0, "keydown");
  assert.equal(app.requests.length, 3); assert.equal(app.state.logit, null);
  assert.equal(app.get("evaluation-result").hidden, true); assert.match(app.get("evaluation-status").textContent, /Fill all five picks/);
  app.choose(1, "blue", "picks", 0); await app.respond(3);
  app.choose(12, "red", "bans", 0); assert.equal(app.requests[4].draft.red.bans[0], 12); await app.respond(4);
  app.reset(); assert.equal(app.requests.length, 5); assert.equal(app.get("evaluation-result").hidden, true);
});

test("edits during an evaluation queue the latest draft and discard stale results and errors", async () => {
  const app = await setup();
  app.fill(); app.choose(11, "blue", "picks", 0); app.choose(12, "red", "bans", 0);
  assert.equal(app.requests.length, 1); await app.respond(0, .1);
  assert.equal(app.requests.length, 2); assert.equal(app.state.logit, null); assert.equal(app.state.pending, true);
  assert.equal(app.requests[1].draft.blue.picks[0], 11); assert.equal(app.requests[1].draft.red.bans[0], 12);
  app.clear("blue", "picks", 0); app.requests[1].reject(new Error("Stale failure")); await tick();
  assert.equal(app.requests.length, 2); assert.equal(app.state.error, null); assert.equal(app.state.pending, false);
  assert.match(app.get("evaluation-status").textContent, /Fill all five picks/);
  app.choose(1, "blue", "picks", 0); await app.respond(2, .72);
  assert.equal(app.state.logit, .72); assert.equal(app.state.pending, false);
});

test("an evaluation failure is retried automatically on the next draft edit", async () => {
  const app = await setup(); app.fill(); app.requests[0].reject(new Error("Offline")); await tick();
  assert.equal(app.state.error, "Error: Offline"); assert.equal(app.state.pending, false);
  app.choose(11, "blue", "picks", 0); assert.equal(app.state.error, null); await app.respond(1, .58);
  assert.equal(app.state.logit, .58); assert.equal(app.state.pending, false);
});

test("an unavailable evaluator leaves draft editing working without evaluation requests", async () => {
  const app = await setup(false); app.choose(1, "blue", "picks", 0);
  assert.equal(app.requests.length, 0); assert.equal(app.state.pending, false);
  assert.equal(app.state.draft.blue.picks[0], 1);
  assert.equal(app.get("evaluation-status").textContent, "No evaluator is connected to Sol 1 yet.");
});

test("evaluations carry bans, patch and first pick, and context edits refresh the score", async () => {
  const app = await setup(); app.setPatch("16.18"); app.setFirstPick(0);
  app.choose(11, "blue", "bans", 2); app.fill();
  assert.equal(app.requests[0].draft.patch, "16.18"); assert.equal(app.requests[0].draft.firstPick, 0);
  assert.deepEqual(app.requests[0].draft.blue.bans, [null, null, 11, null, null]);
  await app.respond(0);
  assert.equal(app.get("evaluation-status").textContent, "");
  app.setPatch("16.19"); assert.equal(app.requests[1].draft.patch, "16.19");
  app.setFirstPick(1); await app.respond(1);
  assert.equal(app.requests[2].draft.firstPick, 1); await app.respond(2);
  app.reset(); assert.equal(app.state.draft.patch, "16.19"); assert.equal(app.state.draft.firstPick, 1);
});

test("pool favorites load their stars and toggle without changing the draft or ordering", async () => {
  const app = await setup(true, [], null, [2]); app.fill(); await app.respond(0, .68);
  const buttons = [...app.get("champions").children];
  assert.equal(buttons[0].querySelector(".favorite-star").hidden, true);
  assert.equal(buttons[1].querySelector(".favorite-star").hidden, false);
  assert.match(buttons[1].getAttribute("aria-label"), /favorite/);
  const revision = app.state.revision;
  assert.equal(buttons[0].disabled, true);
  assert.equal(app.favoriteMenu(1).defaultPrevented, true);
  assert.equal(app.get("champion-menu").hidden, false);
  assert.equal(app.get("toggle-favorite").textContent, "Favorite");
  app.toggleFavorite();
  assert.equal(app.get("champion-menu").hidden, true);
  assert.equal(app.favoriteRequests[0].url, "/api/favorites/1");
  assert.equal(app.favoriteRequests[0].method, "PUT");
  assert.equal(buttons[0].querySelector(".favorite-star").hidden, true);
  await app.respondFavorite(0, {favorites: [1, 2]});
  assert.equal(buttons[0].querySelector(".favorite-star").hidden, false);
  app.favoriteMenu(1); assert.equal(app.get("toggle-favorite").textContent, "Unfavorite");
  app.toggleFavorite(); assert.equal(app.favoriteRequests[1].method, "DELETE");
  await app.respondFavorite(1, {favorites: [2]});
  assert.equal(buttons[0].querySelector(".favorite-star").hidden, true);
  assert.equal(app.state.draft.blue.picks[0], 1); assert.equal(app.state.revision, revision);
  assert.equal(app.state.logit, .68); assert.equal(app.requests.length, 1);
  assert.deepEqual(app.get("champions").children, buttons);
});

test("favorite failures preserve stars and drafting and let the next action retry", async () => {
  const app = await setup(false, [], null, [1]);
  const button = app.get("champions").children[0];
  app.favoriteMenu(1); app.toggleFavorite(); await app.respondFavorite(0, {error: "Disk full"}, false);
  assert.equal(button.querySelector(".favorite-star").hidden, false);
  assert.equal(app.get("favorites-status").textContent, "Disk full");
  app.choose(2, "blue", "picks", 0); assert.equal(app.state.draft.blue.picks[0], 2);
  app.favoriteMenu(1); assert.equal(app.get("toggle-favorite").disabled, false);
  app.toggleFavorite(); await app.respondFavorite(1, {favorites: []});
  assert.equal(button.querySelector(".favorite-star").hidden, true);
  assert.equal(app.get("favorites-status").hidden, true);
  const failedLoad = await setup(false, [], null, [], "Could not read favorites.");
  assert.equal(failedLoad.get("favorites-status").textContent, "Could not read favorites.");
  failedLoad.choose(3, "red", "bans", 0); assert.equal(failedLoad.state.draft.red.bans[0], 3);
});

test("the favorite menu stays within the viewport and closes on Escape, outside clicks and scroll", async () => {
  const app = await setup(false);
  app.favoriteMenu(1, 1919, 1079);
  assert.equal(app.get("champion-menu").style.left, "1762px");
  assert.equal(app.get("champion-menu").style.top, "1036px");
  assert.equal(app.type("Escape", app.get("toggle-favorite")).defaultPrevented, true);
  assert.equal(app.get("champion-menu").hidden, true);
  assert.equal(app.get("champions").children[0].focused, true);
  app.favoriteMenu(1); app.outsideClick(); assert.equal(app.get("champion-menu").hidden, true);
  app.favoriteMenu(1); app.scroll(); assert.equal(app.get("champion-menu").hidden, true);
  app.favoriteMenu(1, 0, 0); assert.equal(app.get("champion-menu").style.top, "264px");
  assert.equal(app.favoriteRequests.length, 0);
});

test("typing after a champion click focuses and filters search without losing the first character", async () => {
  const app = await setup(false);
  app.choose(1, "blue", "picks", 0);
  const revision = app.state.revision;
  assert.equal(app.type("A", app.get("blue-picks").children[0].querySelector("button")).defaultPrevented, true);
  assert.equal(app.document.activeElement, app.get("search")); assert.equal(app.get("search").value, "A");
  app.type("h"); assert.equal(app.get("search").value, "Ah"); assert.equal(app.state.search, "Ah");
  assert.equal(app.get("pool-heading").textContent, "Champion pool(1)");
  assert.equal(app.get("champions").children[0].hidden, true);
  assert.equal(app.get("champions").children[1].hidden, false);
  assert.equal(app.type("r", app.get("search")).defaultPrevented, false);
  app.type("Backspace"); assert.equal(app.get("search").value, "A");
  app.get("search").selectionStart = 0; app.get("search").selectionEnd = 1;
  app.type("K"); assert.equal(app.get("search").value, "K");
  app.favoriteMenu(3); app.type("a", app.get("toggle-favorite"));
  assert.equal(app.get("champion-menu").hidden, true); assert.equal(app.get("search").value, "Ka");
  assert.equal(app.state.draft.blue.picks[0], 1); assert.equal(app.state.revision, revision);
});

test("keyboard routing preserves dialogs, editable controls, navigation and browser shortcuts", async () => {
  const app = await setup(false);
  for (const [key, details] of [["c", {ctrlKey: true}], ["v", {metaKey: true}], ["a", {altKey: true}],
    ["a", {isComposing: true}], ["a", {defaultPrevented: true}], ["Tab", {}], ["Enter", {}], [" ", {}],
    ["Delete", {}], ["ArrowLeft", {}], ["Escape", {}]]) {
    const event = app.type(key, undefined, details);
    assert.equal(event.defaultPrevented, Boolean(details.defaultPrevented), key);
  }
  for (const target of [app.get("draft-name"), app.get("saved-drafts"), app.get("patch"), app.get("first-pick"), {isContentEditable: true}]) {
    assert.equal(app.type("a", target).defaultPrevented, false);
  }
  app.openExport(); assert.equal(app.type("a").defaultPrevented, false);
  assert.equal(app.paste("Ahri").defaultPrevented, false);
  app.closeDialog(); assert.equal(app.get("search").value, "");
});

test("pasting after clicking outside a text field goes into champion search", async () => {
  const app = await setup(false);
  assert.equal(app.paste("Ahri").defaultPrevented, true);
  assert.equal(app.document.activeElement, app.get("search")); assert.equal(app.state.search, "Ahri");
  assert.equal(app.get("pool-heading").textContent, "Champion pool(1)");
  assert.equal(app.paste("Akali", app.get("search")).defaultPrevented, false);
  assert.equal(app.paste("Name", app.get("draft-name")).defaultPrevented, false);
});

const savedDraft = (id, name, snapshot = draft.emptyDraft()) => ({id, name,
  saved_at: "2026-10-05T12:00:00+00:00", draft: JSON.parse(JSON.stringify(snapshot))});

test("saving captures a named snapshot while later edits remain available", async () => {
  const app = await setup(false); app.choose(1, "blue", "picks", 3); app.choose(2, "red", "bans", 4);
  app.save("  Match one  ");
  assert.equal(app.storageRequests.length, 1); assert.equal(app.get("save-draft").disabled, true);
  const request = app.storageRequests[0]; assert.equal(request.method, "POST"); assert.equal(request.body.name, "Match one");
  app.save("Again"); assert.equal(app.storageRequests.length, 1);
  app.choose(3, "blue", "bans", 2);
  assert.equal(request.body.draft.blue.bans[2], null); assert.equal(app.state.draft.blue.bans[2], 3);
  const saved = savedDraft("a".repeat(32), "Match one", request.body.draft);
  await app.respondStorage(0, saved);
  assert.equal(app.get("saved-drafts").value, saved.id); assert.equal(app.get("load-draft").disabled, false);
  assert.match(app.get("storage-status").textContent, /Newer edits are not saved/);
  assert.equal(app.state.draft.blue.bans[2], 3);
});

test("exporting without a name uses B1, R1 and R2 picks or a dated fallback", async () => {
  const app = await setup(false);
  app.choose(1, "blue", "picks", 0); app.choose(2, "red", "picks", 0); app.choose(3, "red", "picks", 1);
  app.openExport();
  assert.equal(app.get("draft-name").placeholder, "B1 Aatrox · R1 Ahri · R2 Akali");
  app.save("");
  assert.equal(app.storageRequests[0].body.name, "B1 Aatrox · R1 Ahri · R2 Akali");
  await app.respondStorage(0, savedDraft("1".repeat(32), app.storageRequests[0].body.name));

  const empty = await setup(false);
  empty.openExport(); empty.save("");
  assert.match(empty.storageRequests[0].body.name, /^Draft /);
  await empty.respondStorage(0, savedDraft("2".repeat(32), empty.storageRequests[0].body.name));
});

test("saved snapshots appear after reopening and load their exact slots with fresh evaluation", async () => {
  const saved = savedDraft("b".repeat(32), "Saved match", fullDraft()); saved.draft.red.bans[4] = 12;
  const app = await setup(true, [saved]);
  assert.equal(app.get("saved-drafts").children[0].value, saved.id);
  assert.match(app.get("saved-drafts").children[0].textContent, /Saved match/);
  assert.deepEqual(app.state.draft, draft.emptyDraft());
  app.clickSlot("red", "picks", 0); app.openImport();
  app.get("saved-drafts").value = saved.id; app.doubleClickSaved();
  assert.equal(app.storageRequests[0].url, `/api/drafts/${saved.id}`);
  await app.respondStorage(0, saved);
  assert.deepEqual(JSON.parse(JSON.stringify(app.state.draft)), saved.draft); assert.equal(app.state.selected, null);
  assert.equal(app.state.selectedChampion, null); assert.equal(app.get("draft-dialog").open, false);
  assert.deepEqual(app.requests[0].draft, saved.draft); await app.respond(0, .61);
  assert.equal(app.state.logit, .61);
});

test("a delayed load preserves edits made while the snapshot is being fetched", async () => {
  const saved = savedDraft("c".repeat(32), "Earlier"); const app = await setup(false, [saved]);
  app.selectSaved(saved.id); app.load(); app.choose(1, "blue", "picks", 0); await app.respondStorage(0, saved);
  assert.equal(app.state.draft.blue.picks[0], 1); assert.equal(app.get("load-draft").disabled, false);
  assert.match(app.get("storage-status").textContent, /draft changed while loading/);
});

test("deleting a saved snapshot preserves the open draft and the other saves", async () => {
  const first = savedDraft("d".repeat(32), "First"), second = savedDraft("e".repeat(32), "Second");
  const app = await setup(false, [first, second]); app.choose(1, "blue", "picks", 0);
  app.selectSaved(first.id); app.deleteSaved();
  assert.equal(app.storageRequests[0].method, "DELETE"); await app.respondStorage(0, {deleted: first.id});
  assert.equal(app.state.draft.blue.picks[0], 1); assert.equal(app.get("saved-drafts").value, "");
  assert.equal(app.get("saved-drafts").children.length, 1); assert.equal(app.get("saved-drafts").children[0].value, second.id);
  assert.equal(app.get("load-draft").disabled, true); assert.equal(app.get("delete-draft").disabled, true);
  assert.equal(app.get("storage-status").hidden, true);
});

test("storage failures release controls and preserve the current draft and saved list", async () => {
  const saved = savedDraft("f".repeat(32), "Existing"); const app = await setup(false, [saved]);
  app.choose(1, "blue", "picks", 0); app.save("New"); await app.respondStorage(0, {error: "Disk full"}, false);
  assert.equal(app.get("storage-status").textContent, "Disk full"); assert.equal(app.get("save-draft").disabled, false);
  app.selectSaved(saved.id); app.load(); app.storageRequests[1].reject(new Error("Offline")); await tick();
  assert.equal(app.get("storage-status").textContent, "Offline"); assert.equal(app.state.draft.blue.picks[0], 1);
  app.deleteSaved(); await app.respondStorage(2, {error: "Could not delete"}, false);
  assert.equal(app.get("saved-drafts").children[0].value, saved.id); assert.equal(app.get("delete-draft").disabled, false);
  assert.equal(app.state.draft.blue.picks[0], 1);
});

test("an unavailable saved draft list leaves the editor and saving usable", async () => {
  const app = await setup(false, [], "Could not read saved drafts from disk.");
  assert.equal(app.get("storage-status").textContent, "Could not read saved drafts from disk.");
  app.choose(1, "blue", "picks", 0); app.save("Still editing");
  assert.equal(app.storageRequests.length, 1); assert.equal(app.storageRequests[0].body.draft.blue.picks[0], 1);
});

test("JSON download and external import round-trip the current draft without saving it on the server", async () => {
  const app = await setup(false);
  app.setPatch("16.18"); app.setFirstPick(0);
  app.choose(1, "blue", "picks", 3); app.choose(2, "red", "bans", 4);
  app.exportFile("Match one");
  assert.equal(app.get("draft-dialog").open, true);
  assert.equal(app.get("draft-dialog-title").textContent, "Save Draft");
  assert.equal(app.get("export-panel").hidden, false);
  assert.equal(app.get("import-panel").hidden, true);
  assert.equal(app.downloads.length, 1);
  assert.equal(app.downloads[0].download, "match-one.json");
  assert.equal(app.downloads[0].clicked, 1);
  const contents = await app.exportedBlobs[0].text();
  assert.deepEqual(Object.keys(JSON.parse(contents)), ["draft"]);
  assert.equal(JSON.parse(contents).draft.blue.picks[3], "Aatrox");
  assert.equal(JSON.parse(contents).draft.patch, "16.18"); assert.equal(JSON.parse(contents).draft.firstPick, 0);
  app.closeDialog(); assert.equal(app.get("draft-dialog").open, false);
  app.reset(); await app.importFile("match.json", contents);
  assert.equal(app.get("draft-dialog-title").textContent, "Import Draft");
  assert.equal(app.get("export-panel").hidden, true);
  assert.equal(app.get("import-panel").hidden, false);
  assert.equal(app.get("draft-file").clicked, 1);
  assert.equal(app.get("draft-file").value, "");
  assert.equal(app.state.draft.blue.picks[3], 1);
  assert.equal(app.state.draft.red.bans[4], 2);
  assert.equal(app.state.draft.patch, "16.18"); assert.equal(app.state.draft.firstPick, 0);
  assert.equal(app.storageRequests.length, 0);
  assert.match(app.get("storage-status").textContent, /Imported/);
});

test("draft controls stay inside the centered dialog and opening it does not start a file action", async () => {
  const dialogStart = html.indexOf('id="draft-dialog"'), dialogEnd = html.indexOf("</dialog>", dialogStart);
  for (const id of ["draft-name", "saved-drafts", "storage-status"]) {
    const position = html.indexOf(`id="${id}"`);
    assert.ok(position > dialogStart && position < dialogEnd);
  }
  const app = await setup(false);
  app.openExport();
  assert.equal(app.get("draft-dialog").open, true);
  assert.equal(app.downloads.length, 0);
  app.closeDialog();
  app.openImport();
  assert.equal(app.get("draft-dialog").open, true);
  assert.equal(app.get("draft-file").clicked, undefined);
});

test("invalid JSON import preserves the open draft and shows an error", async () => {
  const app = await setup(false); app.choose(1, "blue", "picks", 0);
  const invalid = draft.emptyDraft(); invalid.blue.picks[0] = "Unknown champion";
  await app.importFile("wrong.json", JSON.stringify({draft: invalid}));
  assert.equal(app.state.draft.blue.picks[0], 1);
  assert.match(app.get("storage-status").textContent, /Unknown champion name/);
  assert.equal(app.get("draft-file").value, "");
});

test("older JSON exports with a Sol version can still be imported", async () => {
  const app = await setup(false);
  const older = draft.emptyDraft(); older.red.bans[4] = "Aatrox";
  await app.importFile("older.json", JSON.stringify({sol_version: 99, draft: older}));
  assert.equal(app.state.draft.red.bans[4], 1);
});

test("legacy imports mark a missing patch as unknown instead of inheriting the current patch", async () => {
  const app = await setup(false); app.setPatch("16.19"); app.setFirstPick(0);
  const legacy = draft.emptyDraft(); delete legacy.patch; delete legacy.firstPick;
  await app.importFile("legacy.json", JSON.stringify({draft: legacy}));
  assert.equal(app.state.draft.patch, null); assert.equal(app.state.draft.firstPick, 1);
  assert.equal(app.get("patch").value, ""); assert.equal(app.get("first-pick").value, "1");
});

test("a saved draft copied from drafts/ can be imported from another directory", async () => {
  const app = await setup(false);
  const saved = savedDraft("a".repeat(32), "Copied draft");
  saved.draft.blue.picks[0] = 1;
  await app.importFile("copied.json", JSON.stringify(saved));
  assert.equal(app.state.draft.blue.picks[0], 1);
  assert.equal(app.get("draft-dialog").open, false);
});

test("picks show the roster portrait while a warmed splash loads, then keep the splash", async () => {
  const app = await setup(false);
  assert.equal(app.preloads.length, 0);
  app.hover(1); assert.equal(app.preloads.length, 1);
  assert.equal(app.preloads[0].src, "/splashes/16.19.1/1.jpg");
  app.choose(1, "blue", "picks", 0); app.choose(2, "red", "bans", 0);
  assert.equal(app.preloads.length, 2);
  const pick = app.get("blue-picks").children[0].querySelector(".slot-art").querySelector("img");
  const pickArt = app.get("blue-picks").children[0].querySelector(".slot-art");
  const ban = app.get("red-bans").children[0].querySelector(".slot-art").querySelector("img");
  const pool = app.get("champions").children[0].querySelector(".champion-art").querySelector("img");
  assert.equal(pick.src, "/splashes/16.19.1/1.jpg"); assert.equal(ban.src, "/portraits/16.19.1/2.png");
  assert.equal(pool.src, "/portraits/16.19.1/1.png");
  assert.equal(pickArt.style.backgroundImage, 'url("/portraits/16.19.1/1.png")');
  assert.equal(pick.hidden, true);
  const oldLoad = pick.onload;
  pick.onload(); assert.equal(pick.hidden, false);
  pick.onerror(); assert.equal(pick.src, "/portraits/16.19.1/1.png"); assert.equal(pick.hidden, true);
  pick.onload(); assert.equal(pick.hidden, false);
  pick.onerror(); assert.equal(pick.hidden, true);
  app.choose(3, "blue", "picks", 0); assert.equal(pick.src, "/splashes/16.19.1/3.jpg");
  assert.equal(pickArt.style.backgroundImage, 'url("/portraits/16.19.1/3.png")');
  oldLoad();
  assert.equal(pick.hidden, true);
  app.clear("blue", "picks", 0); assert.equal(pick.hidden, true);
  assert.equal(pickArt.style.backgroundImage, "");
});

import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createContext, runInContext} from "node:vm";
import * as draft from "../draft.mjs";

const source = readFileSync(new URL("../app.js", import.meta.url), "utf8").replace(/^import[^\n]+\n/, "");
const tick = () => new Promise(resolve => setImmediate(resolve));
function element(fragment = false) {
  const queries = new Map(), attributes = new Map();
  return {
    fragment, children: [], dataset: {}, style: {}, value: "", listeners: new Map(), classList: {toggle() {}},
    append(child) { this.children.push(...(child.fragment ? child.children : [child])); },
    replaceChildren(...children) { this.children = children; },
    querySelector(selector) { if (!queries.has(selector)) queries.set(selector, element()); return queries.get(selector); },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.get(name) ?? null; },
    removeAttribute(name) { attributes.delete(name); },
    addEventListener(name, handler) { this.listeners.set(name, handler); },
    cloneNode() { return element(); }
  };
}
async function setup(available = true, saved = [], listError = null) {
  const elements = new Map(), requests = [], storageRequests = [];
  const get = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  for (const id of ["pick-template", "ban-template", "champion-template"]) get(id).content = {firstElementChild: element()};
  const document = {getElementById: get, querySelector: get, querySelectorAll: () => [],
    createDocumentFragment: () => element(true), createElement: () => element()};
  const fetch = (url, options) => {
    if (url === "/api/bootstrap") return Promise.resolve({ok: true, json: async () => ({sol_version: 1,
      evaluation_available: available, champions: ["Aatrox", "Ahri", "Akali"].map((name, i) => ({id: i + 1, name, roles: [],
        portrait_url: `/portraits/16.19.1/${i + 1}.png`, splash_url: `/splashes/16.19.1/${i + 1}.jpg`}))})});
    if (url === "/api/drafts" && !options) return Promise.resolve({ok: !listError,
      json: async () => listError ? {error: listError} : {drafts: saved.map(({draft, ...metadata}) => metadata)}});
    if (url.startsWith("/api/drafts")) return new Promise((resolve, reject) => storageRequests.push({url,
      method: options?.method ?? "GET", body: options?.body ? JSON.parse(options.body) : null, resolve, reject}));
    assert.equal(url, "/api/evaluate");
    return new Promise((resolve, reject) => requests.push({draft: JSON.parse(options.body), resolve, reject}));
  };
  const context = createContext({document, fetch, ...draft}); runInContext(source, context); await tick();
  const emit = (container, type, target, key) => get(container).listeners.get(type)({target: {closest: () => target},
    key, preventDefault() {}});
  const slot = (side, kind, index) => {
    const card = get(`${side}-${kind}`).children[index]; return kind === "picks" ? card.querySelector("button") : card;
  };
  const clickSlot = (side, kind, index) => emit(".workspace", "click", slot(side, kind, index));
  const choose = (id, side, kind, index) => {
    emit("champions", "click", get("champions").children[id - 1]); clickSlot(side, kind, index);
  };
  const respond = async (index, probability = .5) => {
    requests[index].resolve({ok: true, json: async () => ({blue_win_probability: probability})}); await tick();
  };
  return {get, requests, storageRequests, choose, clickSlot, respond, state: runInContext("state", context),
    save: name => { get("draft-name").value = name; emit("draft-name", "input", get("draft-name"));
      emit("save-draft-form", "submit", get("save-draft-form")); },
    selectSaved: id => { get("saved-drafts").value = id; emit("saved-drafts", "change", get("saved-drafts")); },
    load: () => emit("load-draft", "click", get("load-draft")),
    deleteSaved: () => emit("delete-draft", "click", get("delete-draft")),
    respondStorage: async (index, value, ok = true) => {
      storageRequests[index].resolve({ok, json: async () => value}); await tick(); },
    clear: (side, kind, index, type = "contextmenu") => emit(".workspace", type, slot(side, kind, index), "Delete"),
    reset: () => emit("clear-draft", "click", get("clear-draft"))};
}

test("draft edits evaluate automatically, including replacements, swaps and clearing", async () => {
  const app = await setup(); assert.equal(app.requests.length, 1); await app.respond(0);
  app.choose(1, "blue", "picks", 0); assert.equal(app.requests[1].draft.blue.picks[0], 1); await app.respond(1);
  app.choose(2, "red", "bans", 0); assert.equal(app.requests[2].draft.red.bans[0], 2); await app.respond(2);
  app.choose(3, "blue", "picks", 0); assert.equal(app.requests[3].draft.blue.picks[0], 3); await app.respond(3);
  app.clickSlot("blue", "picks", 0); app.clickSlot("red", "bans", 0);
  assert.equal(app.requests[4].draft.blue.picks[0], 2); assert.equal(app.requests[4].draft.red.bans[0], 3);
  await app.respond(4);
  app.clear("red", "bans", 0); assert.equal(app.requests[5].draft.red.bans[0], null); await app.respond(5);
  app.clear("blue", "picks", 0, "keydown"); assert.equal(app.requests[6].draft.blue.picks[0], null);
  await app.respond(6); app.choose(1, "blue", "bans", 4); await app.respond(7);
  app.reset(); assert.deepEqual(app.requests[8].draft, draft.emptyDraft()); await app.respond(8, .64);
  assert.equal(app.get("blue-probability").textContent, "64.0%");
  assert.equal(app.get("red-probability").textContent, "36.0%");
});

test("edits during an evaluation queue the latest draft and discard stale results and errors", async () => {
  const app = await setup();
  app.choose(1, "blue", "picks", 0); app.choose(2, "red", "bans", 0);
  assert.equal(app.requests.length, 1); await app.respond(0, .1);
  assert.equal(app.requests.length, 2); assert.equal(app.state.probability, null); assert.equal(app.state.pending, true);
  assert.equal(app.requests[1].draft.blue.picks[0], 1); assert.equal(app.requests[1].draft.red.bans[0], 2);
  app.clear("blue", "picks", 0); app.requests[1].reject(new Error("Stale failure")); await tick();
  assert.equal(app.requests.length, 3); assert.equal(app.state.error, null); assert.equal(app.state.pending, true);
  assert.equal(app.requests[2].draft.blue.picks[0], null); await app.respond(2, .72);
  assert.equal(app.state.probability, .72); assert.equal(app.state.pending, false);
});

test("an evaluation failure is retried automatically on the next draft edit", async () => {
  const app = await setup(); app.requests[0].reject(new Error("Offline")); await tick();
  assert.equal(app.state.error, "Error: Offline"); assert.equal(app.state.pending, false);
  app.choose(1, "blue", "picks", 0); assert.equal(app.state.error, null); await app.respond(1, .58);
  assert.equal(app.state.probability, .58); assert.equal(app.state.pending, false);
});

test("an unavailable evaluator leaves draft editing working without evaluation requests", async () => {
  const app = await setup(false); app.choose(1, "blue", "picks", 0);
  assert.equal(app.requests.length, 0); assert.equal(app.state.pending, false);
  assert.equal(app.state.draft.blue.picks[0], 1);
  assert.equal(app.get("evaluation-status").textContent, "No evaluator is connected to Sol 1 yet.");
});

const savedDraft = (id, name, snapshot = draft.emptyDraft()) => ({id, name, sol_version: 1,
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

test("saved snapshots appear after reopening and load their exact slots with fresh evaluation", async () => {
  const saved = savedDraft("b".repeat(32), "Saved match"); saved.draft.blue.picks[3] = 1; saved.draft.red.bans[4] = 2;
  const app = await setup(true, [saved]); await app.respond(0);
  assert.equal(app.get("saved-drafts").children[1].value, saved.id);
  assert.match(app.get("saved-drafts").children[1].textContent, /Saved match/);
  assert.deepEqual(app.state.draft, draft.emptyDraft());
  app.clickSlot("red", "picks", 0); app.selectSaved(saved.id); app.load();
  assert.equal(app.storageRequests[0].url, `/api/drafts/${saved.id}`);
  await app.respondStorage(0, saved);
  assert.deepEqual(app.state.draft, saved.draft); assert.equal(app.state.selected, null);
  assert.equal(app.state.selectedChampion, null); assert.equal(app.get("draft-name").value, saved.name);
  assert.deepEqual(app.requests[1].draft, saved.draft); await app.respond(1, .61);
  assert.equal(app.state.probability, .61);
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
  assert.equal(app.get("saved-drafts").children.length, 2); assert.equal(app.get("saved-drafts").children[1].value, second.id);
  assert.equal(app.get("load-draft").disabled, true); assert.equal(app.get("delete-draft").disabled, true);
});

test("storage failures release controls and preserve the current draft and saved list", async () => {
  const saved = savedDraft("f".repeat(32), "Existing"); const app = await setup(false, [saved]);
  app.choose(1, "blue", "picks", 0); app.save("New"); await app.respondStorage(0, {error: "Disk full"}, false);
  assert.equal(app.get("storage-status").textContent, "Disk full"); assert.equal(app.get("save-draft").disabled, false);
  app.selectSaved(saved.id); app.load(); app.storageRequests[1].reject(new Error("Offline")); await tick();
  assert.equal(app.get("storage-status").textContent, "Offline"); assert.equal(app.state.draft.blue.picks[0], 1);
  app.deleteSaved(); await app.respondStorage(2, {error: "Could not delete"}, false);
  assert.equal(app.get("saved-drafts").children[1].value, saved.id); assert.equal(app.get("delete-draft").disabled, false);
  assert.equal(app.state.draft.blue.picks[0], 1);
});

test("an unavailable saved draft list leaves the editor and saving usable", async () => {
  const app = await setup(false, [], "Could not read saved drafts from disk.");
  assert.equal(app.get("storage-status").textContent, "Could not read saved drafts from disk.");
  app.choose(1, "blue", "picks", 0); app.save("Still editing");
  assert.equal(app.storageRequests.length, 1); assert.equal(app.storageRequests[0].body.draft.blue.picks[0], 1);
});

test("picks prefer splash art, pool and bans keep portraits, and missing images fall back cleanly", async () => {
  const app = await setup(false); app.choose(1, "blue", "picks", 0); app.choose(2, "red", "bans", 0);
  const pick = app.get("blue-picks").children[0].querySelector(".slot-art").querySelector("img");
  const ban = app.get("red-bans").children[0].querySelector(".slot-art").querySelector("img");
  const pool = app.get("champions").children[0].querySelector(".champion-art").querySelector("img");
  assert.equal(pick.src, "/splashes/16.19.1/1.jpg"); assert.equal(ban.src, "/portraits/16.19.1/2.png");
  assert.equal(pool.src, "/portraits/16.19.1/1.png");
  pick.onerror(); assert.equal(pick.src, "/portraits/16.19.1/1.png"); assert.equal(pick.hidden, false);
  pick.onerror(); assert.equal(pick.hidden, true);
  app.choose(3, "blue", "picks", 0); assert.equal(pick.src, "/splashes/16.19.1/3.jpg"); assert.equal(pick.hidden, false);
  app.clear("blue", "picks", 0); assert.equal(pick.hidden, true);
});

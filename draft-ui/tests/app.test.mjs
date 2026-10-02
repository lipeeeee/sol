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
    fragment, children: [], dataset: {}, style: {}, listeners: new Map(), classList: {toggle() {}},
    append(child) { this.children.push(...(child.fragment ? child.children : [child])); },
    querySelector(selector) { if (!queries.has(selector)) queries.set(selector, element()); return queries.get(selector); },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    getAttribute(name) { return attributes.get(name) ?? null; },
    removeAttribute(name) { attributes.delete(name); },
    addEventListener(name, handler) { this.listeners.set(name, handler); },
    cloneNode() { return element(); }
  };
}
async function setup(available = true) {
  const elements = new Map(), requests = [];
  const get = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  for (const id of ["pick-template", "ban-template", "champion-template"]) get(id).content = {firstElementChild: element()};
  const document = {getElementById: get, querySelector: get, querySelectorAll: () => [],
    createDocumentFragment: () => element(true)};
  const fetch = (url, options) => {
    if (url === "/api/bootstrap") return Promise.resolve({ok: true, json: async () => ({sol_version: 1,
      evaluation_available: available, champions: ["Aatrox", "Ahri", "Akali"].map((name, i) => ({id: i + 1, name, roles: []}))})});
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
  return {get, requests, choose, clickSlot, respond, state: runInContext("state", context),
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

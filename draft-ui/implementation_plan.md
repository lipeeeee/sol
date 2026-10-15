# Sol drafting UI implementation plan

Implements [the product plan](plan.md) on the local `clanker-ui` branch. Python 3.10+ and native browser JavaScript are the runtime; Node is used only for tests.

## 1. Architecture and coding rules

Apply both monograd skills: each module has one responsibility, related functions stay together, and internal invariants fail loudly. Use two-space indentation, compact annotations, guard clauses, plain dictionaries/arrays, and comments that explain decisions. Reject external input explicitly; assertions protect programmer invariants. Standard-library guarantees and focused tests establish each module's postcondition.

All production code stays directly under `draft-ui/`:

| Module | Responsibility | Contract |
|---|---|---|
| `run.py` | Parse arguments and start the process | A known Sol version serves on loopback; startup errors stop execution |
| `server.py` | Translate HTTP requests and responses | Only known routes are served; evaluation receives validated input |
| `draft.py` | Define and validate draft snapshots | Valid snapshots retain their slots, IDs, and nulls unchanged |
| `storage.py` | Persist draft snapshots and publish files atomically | Saves survive restarts; each save has its own ID; disk paths never use draft names |
| `bridge.py` | Connect repository metadata and future inference | Sol IDs remain authoritative; evaluator availability is truthful |
| `assets.py` | Fetch and cache Riot artwork | Validated downloads are published atomically |
| `draft.mjs` | Apply draft edits | Slot counts and champion uniqueness remain valid |
| `draft-file.mjs` | Convert named draft JSON for file import/export | Version and champion names are validated before replacing the open draft |
| `app.js` | Handle DOM events, rendering, and requests | The screen reflects the current draft; stale results are discarded |
| `index.html` | Define accessible page structure | Controls have labels and stable containers |
| `styles.css` | Define layout and appearance | The roster scrolls independently of the teams |

Use ordinary functions and the standard HTTP handler. The module boundaries require no registries, service containers, event buses, custom component framework, or cache-manager classes.

## 2. Python contracts and HTTP integration

### Startup and repository bridge

```sh
python3 draft-ui/run.py 1 --port 8765
```

Resolve the repository from `__file__`, add its root to Python's import path, and validate the version against `configs/sol_<version>.py`. Prepare champion metadata and artwork mapping, then start `ThreadingHTTPServer` on `127.0.0.1`.

Read `metadata/champion_ids.py` in the bridge. Assert positive unique integer IDs and nonempty names. Return rows with `id`, `name`, and `roles`. Until shared role metadata exists, emit empty preference lists. Translate its eventual encoding only in this module.

Keep the evaluator connection as one optional callable:

```python
from collections.abc import Callable
from draft import Draft

Evaluator = Callable[[int, Draft], float]
evaluator:Evaluator|None = None
```

Its absence determines availability. A real evaluator receives the selected version and validated snapshot; its model resources are initialized once before startup. The drafting agent searches for optimal role assignments using the selected champions, without user-assigned roles. The production editor contains no dummy scores or test-only startup mode.

### Draft representation and validation

```python
from typing import TypedDict, cast

Team = TypedDict("Team", {"picks": list[int|None], "bans": list[int|None]})
Draft = TypedDict("Draft", {"blue": Team, "red": Team})
```

Each side has five nullable champion IDs in `picks` and five in `bans`. Preserve positions and do not infer missing selections or assign roles.

The single boundary validator returns the validated original snapshot:

```python
def validate_draft(value:object, champion_ids:frozenset[int])->Draft:
  if not isinstance(value, dict) or set(value) != {"blue", "red"}: raise ValueError("Expected blue and red teams")
  used:set[int] = set()
  for side in ("blue", "red"):
    team:object = value[side]
    if not isinstance(team, dict) or set(team) != {"picks", "bans"}: raise ValueError("Expected picks and bans")
    picks:object = team["picks"]; bans:object = team["bans"]
    if not isinstance(picks, list) or not isinstance(bans, list): raise ValueError("Slots must be arrays")
    if len(picks) != 5 or len(bans) != 5: raise ValueError("Expected five picks and five bans per side")
    for champion_id in picks + bans:
      if champion_id is None: continue
      if type(champion_id) is not int or champion_id not in champion_ids or champion_id in used:
        raise ValueError("Champions must be known and unique across the draft")
      used.add(champion_id)
  return cast(Draft, value)
```

The exact integer check rejects JSON booleans: Python otherwise treats `True` as integer `1`.

### HTTP surface

| Route | Behavior |
|---|---|
| `GET /api/bootstrap` | Return version, champions with local portrait/splash URLs, and evaluator availability |
| `POST /api/evaluate` | Validate the submitted snapshot, including partial drafts, then invoke inference |
| `GET /api/drafts` | List saved snapshot metadata, newest first |
| `POST /api/drafts` | Validate a name and snapshot, then create a separate JSON file on disk |
| `GET /api/drafts/<id>` | Read and validate a saved snapshot |
| `DELETE /api/drafts/<id>` | Remove only the selected saved snapshot |
| `GET /portraits/<asset-version>/<sol-id>.png` | Resolve a known Sol champion to its Riot portrait |
| `GET /splashes/<asset-version>/<sol-id>.jpg` | Resolve a known Sol champion to its default Riot splash |
| Explicit page/script/style/font routes | Serve only listed UI files |

Use a fixed static map. Request paths never become arbitrary filesystem paths or download URLs. Accept JSON evaluation bodies up to 16 KiB. Parsing and validation errors return 400; an absent evaluator returns 503. Pass the optional callable directly into the handler so tests can bind a deterministic function.

Bundle the Outfit Latin variable font as `outfit-latin.woff2`, with its license in `outfit-OFL.txt`. Serve the explicit font route with `font/woff2`; only text responses receive a charset. Use one CSS `@font-face` with weights 100-900 and `font-display: swap`, then inherit the family throughout. No runtime font downloads or font loader are needed. The header shows only SOL.

After inference, enforce its output contract:

```python
p:float = self.evaluator(self.version, draft)
assert type(p) in (int, float) and isfinite(p) and 0 <= p <= 1, "Evaluator returned an invalid probability"
```

Return `{"blue_win_probability": p}`. Keep input-error handling scoped to parsing and validation. Inference exceptions and broken output invariants return 500 and print a terminal traceback.

## 3. Browser state, editing, and rendering

`app.js` owns the draft, nullable selected slot and pending champion ID, search/filter/view values, revision number, and evaluation pending/error/probability state. The slot and champion selections are mutually exclusive. The selected slot is also the source for the next slot click. Domain functions in `draft.mjs` own draft mutations and have no DOM, network, or storage access.

Construct independent slot arrays:

```javascript
/** @returns {Draft} */
export function emptyDraft() {
  const team = () => ({picks: Array(5).fill(null), bans: Array(5).fill(null)});
  return {blue: team(), red: team()};
}
```

Assign champions only when their IDs exist and they are unused elsewhere. Replacing a champion releases the previous ID; clearing resets only the target slot to null. Swapping exchanges two slots, including empty targets, without shifting other selections. Preferred-role metadata never changes draft state. Domain operations return whether the draft changed, preserving evaluation results on no-ops. JavaScript assertions throw errors; `console.assert` does not stop execution.

The swap operation validates both slots before writing and asserts its result:

```javascript
/** @param {Draft} draft @param {Slot} source @param {Slot} target @returns {boolean} */
export function swapSlots(draft, source, target) {
  const first = slotChampion(draft, source), second = slotChampion(draft, target);
  if (first === second) return false;
  draft[source.side][source.kind][source.index] = second;
  draft[target.side][target.kind][target.index] = first;
  assert(slotChampion(draft, source) === second && slotChampion(draft, target) === first, "Swapping must exchange both slots");
  return true;
}
```

Build champion buttons once after bootstrap and update their visibility and disabled state. Keep search inputs and team containers mounted to preserve keyboard focus. Use event delegation and ordinary rendering functions for teams, roster, and evaluation.

Start with nothing selected. A pool click selects a pending champion when no slot is selected; highlight it without changing the draft revision. Re-clicking the same champion cancels it; another pool click changes the pending ID. The next slot click places that champion, including replacement of a filled slot. Slot-first assignment uses the same `placeChampion` function and domain operation.

Without a pending champion, clicking a slot selects it as the swap source, even when empty. Clicking a different slot exchanges their contents; either direction of an empty/filled pair moves the champion into the empty slot. Re-clicking the source deselects it without changing the draft revision; two empty slots select the second.

Champion assignments, replacements, swaps, and clears set both selections to null before rendering. Clear both slot outlines and roster chosen/pressed states. A no-op choice of the selected slot's champion also deselects without changing the draft revision. Draft reset clears selection too.

Disable champions used elsewhere and explain their occupied slot in accessible labels. Right-clicking an occupied slot, or its champion in the pool, clears the holder without shifting slots. Delete clears the focused slot for keyboard users. Disable roster role filters while preference lists are empty; filters only control pool visibility. Clearing the draft resets picks, bans, selection, and the draft name. Reloading starts a fresh active draft; saved snapshots remain on disk.

The saved-draft controls are separate from evaluation state. Save captures the current snapshot before sending it and creates a new file rather than overwriting an earlier save. Load replaces the active draft, clears selections, and follows ordinary draft revision/evaluation handling. If editing continues during a load, retain those newer edits and show a retry message. Delete removes the saved file without changing the open draft. Storage failures appear beside these controls and leave drafting available. Write files atomically through `storage.atomic_write`, shared with the artwork cache. Invalid saved files remain on disk and are skipped with server warnings.

Route right-click edits through the same domain operation and draft revision handling:

```javascript
document.querySelector(".workspace").addEventListener("contextmenu", event => {
  const button = event.target.closest("button[data-kind], button[data-id]");
  if (!button) return;
  const slot = button.dataset.kind ? eventSlot(button) : occupiedSlots(state.draft).get(Number(button.dataset.id));
  if (!slot || slotChampion(state.draft, slot) === null) return;
  event.preventDefault();
  if (clearSlot(state.draft, slot)) draftChanged();
});
```

Put role buttons, search, and the normal/compact view buttons on one desktop toolbar; wrap them on smaller screens. Omit All: clicking the active role again clears that filter. Both filters and views use `aria-pressed`. Preferences only filter the pool and remain disabled until shared metadata exists. View changes toggle one CSS class without rebuilding buttons or changing draft revisions:

```javascript
state.role = state.role === button.dataset.role ? "" : button.dataset.role;
state.view = button.dataset.view; dom.champions.classList.toggle("compact", state.view === "compact");
```

Use a pure black page, solid near-black cells, strong blue/red accents, and yellow selection/focus highlights. The centre has no surrounding frame; a thin border bounds only the scrolling champion grid. Its bottom aligns with the ban rows on desktop. Use CSS size containment on the roster so its contents cannot stretch the shared grid row; evaluation occupies the next row. Pick cells are wide with bold slot labels, regular-weight champion names, and 4 px gaps. Filled cells show splash artwork covering the cell beneath the labels; empty cells retain their square placeholders. Selected cells use one yellow for their outline, side stripe, and slot labels; champion names keep their normal colour. Their fixed row heights shrink on smaller or shorter screens; they never stretch to fill the page. Ban tiles have no empty captions or visible champion names; keep hover titles and accessible names. Normal champion tiles keep spacing; compact tiles use a smaller minimum width with zero gap. Colours identify the sides without visible team headings; retain accessible side labels. Put the visible roster count in `Champion pool(<count>)`. Omit empty-pick captions, pick counts, the selection badge, pool status row, individual clear button, and footer. Stack the layout below 1000 px.

### Evaluation and stale responses

After a draft change, including a swap or move, deselect the slot, increment the revision, clear the previous result/error, and render the changed regions. Evaluate automatically on load and after each draft edit when an evaluator is available; omit the Evaluate Draft button. Search and slot selection without a swap do not change the revision. Allow one outstanding request and keep editing available. If the draft changes during a request, discard its result or error and evaluate the latest draft when that request finishes:

```javascript
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
```

Display estimated blue probability as `p` and red as `1 - p`; round only for presentation.

## 4. Artwork and cache

Use [Riot Data Dragon](https://developer.riotgames.com/docs/lol#data-dragon), pinned to `16.19.1` independently of the Sol version. Load the cached catalogue or fetch it once during startup. Normalize display names, then read `image.full` to handle filenames such as Wukong's `MonkeyKing.png`. Keep Riot numeric IDs out of draft state.

Validate catalogue structure, version, unique normalized names, and simple PNG basenames. Store catalogue and portraits under the ignored `.cache/ddragon/<version>/` directory, with default splashes in its `splashes/` subdirectory. Derive splash filenames from validated portrait basenames, such as `MonkeyKing.png` to `MonkeyKing_0.jpg`. Riot splash URLs are unversioned. Fetch artwork on first request; cached files work offline. Pick cards use splashes with `object-fit: cover`, retaining the existing labels and colours over a dark gradient. Missing splashes fall back to portraits, then named placeholders; pool and ban tiles keep square portraits.

Check declared download length when present. Validate JSON before caching; check the PNG signature and terminal IEND marker for portraits, and JPEG start/end markers for splashes. Invalid cached files are misses and are never served. Publish validated bytes with one filesystem primitive:

```python
def atomic_write(path:Path, data:bytes)->None:
  path.parent.mkdir(parents=True, exist_ok=True)
  temporary:Path|None = None
  try:
    with NamedTemporaryFile(dir=path.parent, prefix=".", delete=False) as file:
      temporary = Path(file.name); file.write(data)
    temporary.replace(path)
  finally:
    if temporary is not None: temporary.unlink(missing_ok=True)
```

Temporary files share the destination directory for atomic replacement and have unique names for concurrent requests. Use bounded network timeouts. Handle artwork failures at their boundary, log the reason, and preserve the editor. Keep fetching synchronous and demand-driven.

## 5. Implementation order and acceptance checks

1. Draft types, boundary validation, and browser domain operations.
2. Repository bridge, version selection, bootstrap, explicit routes, and unavailable evaluation.
3. Artwork mapping, download validation, and atomic caching.
4. Editor structure, domain events, rendering, filters, and responsive layout.
5. Optional evaluator integration, probabilities, pending state, and stale-result handling.
6. Launch documentation, visual checks, and a monograd review.

```sh
PYTHONPATH=.:draft-ui python3 -m unittest discover -s draft-ui/tests -p 'test_*.py'
node --test draft-ui/tests/*.test.mjs
```

| Area | Acceptance checks |
|---|---|
| Draft contract | Empty and arbitrary partial slots accepted unchanged; malformed shapes, unknown/boolean IDs, duplicates, and role-assignment objects rejected |
| Editing | Independent arrays; swaps preserve champions and slot counts; moves empty their source; replacements and clears release champions; preferences never assign roles |
| HTTP | Known version starts; unknown version fails; unexpected paths return 404; absent evaluator returns 503 |
| Saved drafts | Exact partial slots survive server restarts; repeated names create distinct saves; concurrent writes retain every snapshot; failed writes clean up; invalid IDs cannot escape the storage directory; load/delete failures preserve editing |
| Evaluator | Test callable receives exact version/snapshot; invalid outputs and model errors return 500 |
| Artwork | Name exceptions mapped correctly; cache avoids downloads; invalid/interrupted downloads unpublished; failed replacement preserves old files |
| Browser | Champion-first and slot-first assignment/replacement; pending champion changes/cancellation; swaps in both directions with empty slots; deselection after edits; right-click/Delete clearing; role re-click reset and search combinations; both views preserve selections; errors, stale responses, and session reset |
| Layout | Verify 1920x1080, 1366x768, and narrow screens; compact tiles touch and show more champions; roster scrolling keeps selections visible |

Real inference, recommendations, and drafting against the agent remain future work.

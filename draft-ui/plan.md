# Sol local drafting UI

## Summary

Build a small local draft editor, using the second reference screenshot as the main visual reference. Launch it with:

```sh
python draft-ui/run.py 1
```

The argument selects `configs.sol_1`. The page supports freely editing picks and bans, with automatic evaluation showing estimated blue/red win probabilities once an evaluator is connected. The drafting agent searches for optimal role assignments.

V1 delivers the editor and evaluation hook. This checkout has no runnable evaluator yet, so its unavailable state will be explicit.

## Structure and Python integration

- Keep all UI code under `draft-ui/`: Python server, asset-cache helper, HTML, CSS, browser JavaScript, and focused tests.
- Use Python's standard-library `ThreadingHTTPServer` and native browser APIs. No frontend build process or additional runtime dependencies.
- Bind to `127.0.0.1:8765`, with an optional `--port`. Resolve paths relative to the script so launching from another directory also works.
- Validate the requested version against the existing configuration modules. An unknown version fails at startup with a useful message.
- Expose two small endpoints:
  - `GET /api/bootstrap`: selected version, champion catalogue, role metadata, and evaluator availability.
  - `POST /api/evaluate`: accept the current draft and return `blue_win_probability`; the browser derives red's probability.
- Keep the connection to Sol in one ordinary Python function receiving the version and draft. Until inference exists, report unavailable and disable evaluation. Connecting a real runner later changes this function and its startup initialization.
- Serve only explicit UI, portrait, and splash routes. Keep browser requests on the same origin.
- Document the launch command and evaluation contract in the repository README.

## Draft editor and appearance

Use a dark, dense, three-column desktop layout:

- **Left/right:** five wide pick cards, with bold B1-B5/R1-R5 labels and regular-weight champion names. Keep small gaps between rows; use shorter cells on smaller screens instead of stretching cells to fill the page. Side colours identify teams without text headings. A selected cell uses the same yellow for its outline, side stripe, and slot labels; champion names keep their normal colour.
- **Below each team:** five smaller ban tiles, visually grouped 3+2. Omit empty captions and visible champion names; retain names on hover and in accessible labels.
- **Centre:** `Champion pool(<count>)`, a shared toolbar for role buttons, search, and two view buttons, a bounded scrollable champion grid, and a compact evaluation area below it. Align the grid's bottom with the ban rows on desktop. Keep team selections visible while the roster scrolls. Update the heading's count with the visible filtered champions.

Use a pure black background, solid near-black cards, strong blue/red side colours, and yellow selection/focus highlights. The centre blends into the page; a thin border bounds the champion grid itself. Filled pick cards use default splash artwork covering the entire cell, with the existing bold slot label and regular-weight champion name over a subtle dark gradient. Preserve the existing borders, highlights, row heights, and empty-slot styling. The pool and bans retain square portraits. Normal view keeps larger tiles with spacing; compact view uses smaller tiles touching edge to edge.

Use the geometric Outfit font throughout, bundled locally as one Latin variable WOFF2 file with its SIL Open Font License. The header shows only SOL, without a workspace subtitle.

Interaction rules:

- Start with nothing selected. Choose a champion first, then click a pick or ban to fill or replace it; selecting the slot first works too. A pending champion is highlighted in the pool and does not change the draft until placed. Re-click it to deselect, or choose another champion to change the selection.
- Clicking a pick or ban without a pending champion selects it as the source for the next slot click. Exchange the two contents, including empty-to-filled and filled-to-empty moves. Clicking the same slot again deselects it; clicking two empty slots selects the second.
- Assignments, replacements, swaps, and clearing deselect both the slot and champion and remove their highlights; no forced progression.
- Right-click a picked or banned champion to return it to the pool, or press Delete on its focused slot. Keep **Clear draft**. Empty slots are always permitted.
- Champions already used elsewhere are visibly unavailable, preventing duplicates across both teams' picks and bans.
- B1/R1 labels describe pick positions. The editor never assigns roles; the drafting agent searches possible role configurations.
- Replacing or clearing a champion preserves all other slot positions.
- Search matches names without sensitivity to case or punctuation. Role filters combine with search; clicking the active role again resets the filter. There is no All button. View changes preserve the draft, filter, search, and pending selection.
- Keep the active draft in memory. Save Draft saves snapshots as separate JSON files in the ignored `draft-ui/drafts/` directory, with an optional name suggested from B1, R1 and R2 or the current time. Import Draft shows a compact list; double-clicking a saved draft loads it. List, load, and delete snapshots through the local server; loading preserves exact partial slots and evaluates with the current Sol version. Reloading starts a fresh active draft while saved snapshots survive reloads and server restarts.
- Allow the open draft to be downloaded as JSON with champion names and imported from an external file when those champions are available. Draft files do not need a Sol version. Reject malformed files without changing the open draft.

Use keyboard-accessible controls and visible focus states. Empty pick cards show only their slot labels; omit the footer, pick counts, selection badge, pool status row, and individual clear button. Target desktop layouts at 1920x1080 and 1366x768, with a stacked layout on narrower screens.

## Champion data, artwork, and evaluation contract

**Champion identity and roles**

Keep [Sol's champion IDs](../metadata/champion_ids.py) authoritative. Browser state and evaluation requests use those IDs.

Each side contains five ordered nullable champion IDs in `picks` and five in `bans`. Preserve empty positions; never compact arrays or invent missing selections. Role assignments do not appear in snapshots.

Expose champion role preferences to the browser as ordered role names: `top`, `jungle`, `mid`, `adc`, `support`. A small Python mapping function will translate the eventual shared metadata encoding. Until that metadata exists:

- Return empty preference lists and disable roster role filters.
- Avoid creating a second, UI-specific role dataset.

Preferences only filter the champion pool. The drafting agent may use them during its role search without treating them as user-imposed assignments.

**Artwork**

Use Riot's versioned champion catalogue and square portraits from [Data Dragon](https://developer.riotgames.com/docs/lol#data-dragon). All 173 current Sol champions matched the inspected `16.19.1` catalogue.

- Pin that asset version independently of the Sol version.
- Match normalized display names and read `image.full`; this handles filenames such as Wukong's `MonkeyKing.png`.
- Cache catalogue data and requested artwork under the UI's ignored `.cache/` directory.
- Fetch each portrait or default splash on first use, then serve it locally. Start a splash request when a champion is hovered, focused, or selected; show its portrait in a pick cell until the splash is ready. Keep recently requested splashes in browser memory. Splash URLs are unversioned. Cached artwork works offline; failed splashes fall back to square portraits, then named placeholders.
- Download only the catalogue and artwork used by the page.

**Evaluation**

Accept partial drafts, including empty slots. The future evaluator must support this input and search optimal role assignments before being marked available.

Validate supplied IDs, slot counts, and uniqueness without requiring complete teams. Require a finite returned probability between 0 and 1.

Display an estimated blue/red probability bar with percentages. Evaluation runs only on request. Draft changes clear the previous result, and responses from an older draft state are ignored. Failures appear inline without losing the draft.

## Verification and boundaries

- Python tests cover version selection, catalogue mapping, partial-draft preservation, invalid inputs, evaluator unavailability, and probability validation.
- Asset tests cover cache reuse, offline startup, missing portraits, and downloads that must not leave corrupt cache files.
- Browser checks cover out-of-order picks and bans, swaps into filled and empty slots, normal drafting after pool selections, right-click clearing, duplicates, role toggle/search combinations, both view modes, keyboard operation, and fresh state after reload.
- Exercise successful, failed, and stale evaluations using a test-only evaluator; production must never display fabricated probabilities.
- Visually verify both desktop sizes and the narrow layout.

Real model inference, champion recommendations, and drafting against the agent remain future work. The ordered draft snapshot can support that later mode without introducing a turn engine now.

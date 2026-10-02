# sol
[sol notes](https://github.com/lipeeeee/notes/tree/master/proj/sol)

---

required flags to run are in `FLAGS.txt`

## Local draft editor

From the repository in WSL Ubuntu, run:

```sh
python3 draft-ui/run.py 1
```

Open [127.0.0.1:8765](http://127.0.0.1:8765). The argument selects the existing `configs/sol_1.py`; `--port` changes the port. Python 3.10+ is the only runtime requirement, and launching the script by absolute path also works from another directory. Stop the server with Ctrl+C.

Choose a champion and then a pick or ban, or select the slot first. Re-click a pending champion or selected slot to deselect it. Click two different slots to exchange their contents; either slot can be empty. Assignments, replacements, swaps, and clears deselect both the slot and champion. Right-click a picked or banned champion to return it to the pool, or focus its slot and press Delete. Ban portraits have a grey block symbol covering the full portrait at 22% opacity; hover for champion names. Champions cannot appear twice in the same draft. Reloading starts a fresh draft.

Use the two grid buttons beside search to switch between spaced normal tiles and smaller, touching compact tiles. Role buttons share the search toolbar; clicking the active role again clears its filter. Role filters become available once shared champion preferences are translated in `draft-ui/bridge.py`; they only filter the pool and never assign roles.

Portraits come from Riot Data Dragon, pinned to `16.19.1`, and are cached in the ignored `draft-ui/.cache/` folder on first use. Cached portraits work offline; unavailable artwork uses placeholders. The page uses a locally bundled Outfit variable font; its license is in `draft-ui/outfit-OFL.txt`.

The evaluator is currently unavailable. To connect real inference, bind `bridge.evaluator` to a callable receiving `(version:int, draft:Draft)` and returning a finite blue-side win probability between 0 and 1. Initialize model resources once before the server starts. Each side contains five nullable champion IDs in `picks` and five in `bans`; arbitrary partial slots must be supported. The drafting agent owns the search for optimal role assignments, with no user-assigned roles in its input. When connected, evaluation runs automatically on load and after every draft edit. The browser derives red's probability, discards stale results, and evaluates the latest draft after any in-flight request finishes.

The design and implementation guide are in [draft-ui/plan.md](draft-ui/plan.md) and [draft-ui/implementation_plan.md](draft-ui/implementation_plan.md).

Run the checks in WSL; Node is needed only for the JavaScript tests:

```sh
PYTHONPATH=.:draft-ui python3 -m unittest discover -s draft-ui/tests -p 'test_*.py'
node --test draft-ui/tests/*.test.mjs
```



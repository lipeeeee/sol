# sol
[sol notes](https://github.com/lipeeeee/notes/tree/master/proj/sol)

---

required flags to run are in `FLAGS.txt`

# usage
```sh
# training
PYTHONPATH=. DEBUG=4 python3 sol/train.py <sol_version> # e.g (sol_1, sol_2, 1, 3, ...)

# download oracle's training data
python3 sol/update_data.py
```

```python
from sol import inference
sol_version = inference.load_model(1)
inference.predict(sol_version, test_batch)
```

## Local draft editor

```sh
python3 draft-ui/run.py 1
```

Open the printed local URL. Once both teams have five picks, the editor evaluates the draft through `sol/inference.py`.
Each team's slots are interpreted in Top, Jungle, Mid, ADC, Support order. Bans can remain empty.
The signed score favors Blue when positive and Red when negative; +1.00 corresponds to a model estimate of 55% for Blue.
The checkpoint is loaded at startup and reused. Sol uses CPU when CUDA is unavailable.

To rebuild the `sol_1` dataset from the local CSV files:

```sh
PYTHONPATH=. python3 -c 'from sol.dataset import SolDataset; SolDataset().extract_base_data(requested_fields=["champion"]).write_disk("data/dataset_sol_1.pkl")'
```

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

## Local draft inference
*ps: draft-ui wasn't made by me, but it does make calls to sol's inference!*

```sh
python3 draft-ui/run.py 1
```

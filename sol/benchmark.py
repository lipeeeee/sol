# private, selected game benchmark, still have to think about design on this
from sol.utils import *

# create signature value after benchmarks, like elo
# confidence and correctness should be awarded more while confidence and error should be punsihed more
# Q: do we add names/categories to drafts so we can diagnose which version is failing where? probably a good idea

model_list:list[int|str] = [1]


tests:list[dict] = [
  {
    "champion": {
      "blue": ["Aatrox", "Lee Sin", "Ahri", "Jinx", "Nautilus"],
      "red": ["Ornn", "Viego", "Orianna", "Aphelios", "Lulu"]
    },
    "ban_order": {
      "blue": ["Thresh", "Gnar", "Sivir", "Yasuo", "Malphite"],
      "red": ["Shen", "Nidalee", "Karthus", "Syndra", "Janna"]
    },
    "firstPick": 1,
    "patch": "16.18",
    "awnser": 0
  }
]



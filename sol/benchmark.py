# private, selected game benchmark, still have to think about design on this
from sol.utils import *

# create signature value after benchmarks, like elo
# confidence and correctness should be awarded more while confidence and error should be punsihed more
# Q: do we add names/categories to drafts so we can diagnose which version is failing where? probably a good idea

# p_blue = sigmoid(pred)
# q = p_blue if awnser == 1 else (1 - p_blue)
# loss = -ln(q) # this is 1 loss

# average_loss = sum(all case_losses) / number_of_cases
# benchmark_score = 100 * (1 - average_loss / ln(2)) # i dont understand logs

model_list:list[int|str] = [1]


tests:list[dict] = [
  {
    "category": "f2b", "awnser": 1,
    "champion": {
      "blue": ["Aatrox", "Lee Sin", "Ahri", "Jinx", "Nautilus"],
      "red": ["Ornn", "Viego", "Orianna", "Aphelios", "Lulu"]
    },
    "ban_order": {
      "blue": ["Thresh", "Gnar", "Sivir", "Yasuo", "Malphite"],
      "red": ["Shen", "Nidalee", "Karthus", "Syndra", "Janna"]
    },
    "firstPick": 1,
    "patch": "16.18"
  }
]



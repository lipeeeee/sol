# private, selected game benchmark, still have to think about design on this
from sol.utils import *
from sol import inference
from torch import Tensor, sigmoid
import math

# create signature value after benchmarks, like elo
# confidence and correctness should be awarded more while confidence and error should be punsihed more
# Q: do we add names/categories to drafts so we can diagnose which version is failing where? probably a good idea

# p_blue = sigmoid(pred)
# q = p_blue if awnser == 1 else (1 - p_blue)
# loss = -ln(q) # this is 1 loss ln(1) == 0

# average_loss = sum(all case_losses) / number_of_cases
# benchmark_score = 100 * (1 - average_loss / ln(2)) # i dont understand logs

model_list:list[str] = ["sol_1"]
category_loss_per_model:defaultdict[str, defaultdict[str, float]] = defaultdict(lambda: defaultdict(float)) # model: {category: loss}

@torch.no_grad
def evaluate_model(model:str):
  m = inference.load_model(model)
  y:Tensor = inference.predict(m, tests)
  all_loss:float = 0
  
  # WARNING: THIS IS ASSUMING OUTPUT IS 1 HEAD ONLY! REFACTORING NEEDS TO BE DONE
  for entry, test in zip(y, tests, strict=True):
    p_blue = sigmoid(entry)
    q = p_blue if test["awnser"] == 1 else 1 - p_blue
    loss = -torch.log(q)

    all_loss += loss.item()
    category_loss_per_model[model][test["category"]] += loss.item()
  average_loss = all_loss / len(tests)
  benchmark_score = 100 * (1 - average_loss / math.log(2))
  return benchmark_score


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
  },
  {
    "category": "f2b", "awnser": 1,
    "champion": {
      "blue": ["Aatrox", "Lee Sin", "Ahri", "Jinx", "Bard"],
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

if __name__ == "__main__":
  evaluate_model(model_list[0])

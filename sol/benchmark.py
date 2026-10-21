# private, selected game benchmark, still have to think about design on this
from sol.utils import *
from sol import inference
from torch import Tensor
from torch.nn.functional import binary_cross_entropy_with_logits
import math

# create signature value after benchmarks, like elo
# simpler/basic labels/metrics
# also allow checkpoints evaluation
# confidence and correctness should be awarded more while confidence and error should be punsihed more
# Q: do we add names/categories to drafts so we can diagnose which version is failing where? probably a good idea

# p_blue = sigmoid(pred)
# awnser is the target Blue-win probability, between 0 and 1
# loss = -awnser * ln(p_blue) - (1 - awnser) * ln(1 - p_blue)

# average_loss = sum(all case_losses) / number_of_cases
# benchmark_score = 100 * (1 - average_loss / ln(2)) # i dont understand logs

model_list:list[str] = ["sol_1"]

# NOTE: this probably will need to be turned into a helper class in order to make multi-head benchmarks!
@torch.no_grad
def evaluate_model(model:str):
  m = inference.load_model(model)
  y:Tensor = inference.predict(m, tests)["win_logits"] # NOTE: should be able to evaluate multiple heads, if some model doesnt have heads return 0, 0
  all_loss:float = 0
  loss_per_category:dict[str, float] = defaultdict(lambda: 0.0); category_counts:dict[str, int] = defaultdict(lambda: 0)
  
  for entry, test in zip(y, tests, strict=True):
    assert 0 <= test["awnser"] <= 1, "awnser must be a probability between 0 and 1"
    loss = binary_cross_entropy_with_logits(entry, entry.new_tensor(test["awnser"]))

    all_loss += loss.item()
    loss_per_category[test["category"]] += loss.item(); category_counts[test["category"]] += 1
  average_loss = all_loss / len(tests)
  benchmark_score = 100 * (1 - average_loss / math.log(2))
  score_per_category:dict[str, float] = {
    category: 100 * (1 - (total_loss / category_counts[category]) / math.log(2))
    for category, total_loss in loss_per_category.items()
  }
  return benchmark_score, score_per_category


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
  },
]

if __name__ == "__main__":
  for m in model_list:
    print(f"{m}::::{evaluate_model(m)}\n")

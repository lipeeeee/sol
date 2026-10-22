# search engine for sol! MCTS with PUCTS selection
from sol.utils import *
from sol.utils import TeamEnum as TE

# define how to store state, should be very lean and easy to check dict?


# NOTE: this current State 
class State:
  picks:dict[TE, list[int]]
  bans:dict[TE, list[int]]
  turn:int
  blue_fp:bool # important because it can change turn(2026 draft change)

  def legal_actions(self): pass
  def apply_action(self): pass
  def is_complete(self): pass


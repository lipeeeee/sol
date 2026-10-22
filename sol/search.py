# search engine for sol! MCTS with PUCTS selection
from sol.utils import *
from sol.utils import TeamEnum as TE

# NOTE: future iterations should support banning but this wont

# NOTE: this current State 
class State:
  picks:dict[TE, list[int]]
  bans:dict[TE, list[int]]
  firstPick:int # important because it can change turn(2026 draft change), also i should probably alter how this is being stored

  def __init__(self, picks:dict, bans:dict, firstPick:int) -> None:
    self.picks = picks
    self.bans = bans
    self.firstPick = firstPick

  @property
  def turn(self) -> int: return TE.BLUE

  def legal_actions(self) -> list: return list() 
  def apply_action(self, champ:int) -> State: 
    assert not(self.is_complete())
    picks_cp, bans_cp = self.picks.copy(), self.bans.copy()
    if self.turn == TE.BLUE: picks_cp[TE.BLUE].append(champ)
    elif self.turn == TE.RED: picks_cp[TE.RED].append(champ)
    else: raise ValueError(f"invalid turn in state: {self.turn}")
    return State(picks_cp, bans_cp, self.firstPick)
  def is_complete(self) -> bool: return True
  def valid_state(self) -> bool:
    if len(self.picks) != 2 or len(self.bans) != 2: return False
    if not(0 <= len(self.picks[TE.BLUE]) <= 5) or not(0 <= len(self.picks[TE.RED]) <= 5): return False
    if not(0 <= len(self.bans[TE.BLUE]) <= 5) or not(0 <= len(self.bans[TE.RED]) <= 5): return False
    if not(self.firstPick in (TE.BLUE, TE.RED)): return False
    # TODO: check if champion is both banned/picked and banned/picked by both teams
    return True


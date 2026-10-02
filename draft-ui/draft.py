from typing import TypedDict, cast

Team = TypedDict("Team", {"picks": list[int|None], "bans": list[int|None]})
Draft = TypedDict("Draft", {"blue": Team, "red": Team})

def validate_draft(value:object, champion_ids:frozenset[int])->Draft:
  if not isinstance(value, dict) or set(value) != {"blue", "red"}: raise ValueError("Expected blue and red teams")
  used:set[int] = set()
  for side in ("blue", "red"):
    team:object = value[side]
    if not isinstance(team, dict) or set(team) != {"picks", "bans"}: raise ValueError("Expected picks and bans")
    picks:object = team["picks"]; bans:object = team["bans"]
    if not isinstance(picks, list) or not isinstance(bans, list): raise ValueError("Slots must be arrays")
    if len(picks) != 5 or len(bans) != 5: raise ValueError("Expected five picks and five bans per side")
    for champion_id in picks + bans:
      if champion_id is None: continue
      if type(champion_id) is not int or champion_id not in champion_ids or champion_id in used:
        raise ValueError("Champions must be known and unique across the draft")
      used.add(champion_id)
  return cast(Draft, value)

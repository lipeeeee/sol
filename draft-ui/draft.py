from typing import NotRequired, TypedDict, cast

Team = TypedDict("Team", {"picks": list[int|None], "bans": list[int|None]})
Draft = TypedDict("Draft", {"blue": Team, "red": Team, "firstPick": NotRequired[int], "patch": NotRequired[str|None]})

def validate_draft(value:object, champion_ids:frozenset[int])->Draft:
  if not isinstance(value, dict) or not {"blue", "red"} <= set(value) <= {"blue", "red", "firstPick", "patch"}:
    raise ValueError("Expected blue and red teams with optional firstPick and patch")
  if type(first_pick:=value.get("firstPick", 1)) is not int or first_pick not in (0, 1):
    raise ValueError("firstPick must be 1 for Blue or 0 for Red")
  patch = value.get("patch")
  if patch is not None and (not isinstance(patch, str) or not patch.strip() or len(patch) > 16):
    raise ValueError("Patch must be a nonempty string of up to 16 characters or null")
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

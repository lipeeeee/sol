# dict[champ_id, dict[str, int]]
# keys per champ: [
# initiation, dive, peel, disengage, amplification, frontline, front2back
# burst_dmg, sustained_dmg, aoe_dmg, poke
# range, zone_control
# waveclear, side_pressure, map_reach
# hands_requirement, protection_dependence, resource_demand, lead_dependence
# early, mid, late
#]
# should we have post-computed stuff? probably its fine. like flex=len(roles)>1
# NOTE: data is initially be sourced by an LLM and later tweaked by me
from sol.metadata.champion_id import CHAMPION_ID

CHAMPION_IDENTITY: dict[int, dict[str, int]] = {
  CHAMPION_ID["Kai'Sa"]: dict(
    initiation=0, dive=90, peel=0, disengage=0, amplification=0, frontline=0, front2back=80,
    burst_dmg=70, sustained_dmg=90, aoe_dmg=30, poke=50,
    range=60, zone_control=20,
    waveclear=60, side_pressure=40, map_reach=30,
    hands_requirement=60, protection_dependence=60, resource_demand=90, lead_dependence=30,
    early=30, mid=70, late=70,
  ),
}

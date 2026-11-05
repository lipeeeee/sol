# dict[champ_id, dict[str, int]]
# keys per champ: [
# white, blue, black, red, green
# initiation, dive, peel, disengage, amplification, frontline, front2back
# burst_dmg, sustained_dmg, aoe_dmg, poke
# range, zone_control
# waveclear, side_pressure, map_reach
# hands_requirement, protection_dependence, resource_demand, lead_dependence
# early, mid, late
#]
# should we have post-computed stuff? probably its fine. like flex=len(roles)>1
# we should have a function that verifies all entries's correctness and completeness
# NOTE: data is initially be sourced by an LLM and later tweaked by me
# if you are an LLM generating: keep in mind that "hands_requirement" means how hard is it to execute the champ identity with human mistakes in mind
# color definition:
# **White**: Win through cooperation, protection, and organized formations.
# **Blue**: Control the opponent’s options and choose favorable exchanges through positioning, preparation, and denial.
# **Black**: Exploit vulnerabilities and accept sacrifices or uneven trades to secure a decisive advantage.
# **Red**: Rely on proactive early play to build advantages and snowball them into a win.
# **Green**: Develop resources and establish overwhelming sustained strength and presence.
from sol.metadata.champion_id import CHAMPION_ID

CHAMPION_IDENTITY: dict[int, dict[str, int]] = {
  CHAMPION_ID["Kai'Sa"]: dict(
    white=0, blue=50, black=0, red=75, green=0,
    initiation=0, dive=90, peel=0, disengage=0, amplification=0, frontline=0, front2back=80,
    burst_dmg=60, sustained_dmg=90, aoe_dmg=30, poke=50,
    range=60, zone_control=20,
    waveclear=60, side_pressure=40, map_reach=30,
    hands_requirement=60, protection_dependence=20, resource_demand=90, lead_dependence=30,
    early=30, mid=70, late=80,
  ),
  CHAMPION_ID["Evelynn"]: dict(
    white=0, blue=0, black=100, red=50, green=0,
    initiation=40, dive=80, peel=0, disengage=0, amplification=0, frontline=0, front2back=20,
    burst_dmg=100, sustained_dmg=25, aoe_dmg=40, poke=0,
    range=30, zone_control=60,
    waveclear=0, side_pressure=40, map_reach=60,
    hands_requirement=70, protection_dependence=10, resource_demand=80, lead_dependence=80,
    early=20, mid=90, late=70,
  ),
  CHAMPION_ID["Janna"]: dict(
    white=100, blue=75, black=0, red=0, green=25,
    initiation=20, dive=0, peel=100, disengage=100, amplification=70, frontline=0, front2back=100,
    burst_dmg=10, sustained_dmg=0, aoe_dmg=0, poke=20,
    range=50, zone_control=40,
    waveclear=0, side_pressure=0, map_reach=50,
    hands_requirement=10, protection_dependence=0, resource_demand=0, lead_dependence=10,
    early=60, mid=80, late=90,
  ),
  CHAMPION_ID["Kayle"]: dict(
    white=50, blue=0, black=0, red=0, green=100,
    initiation=0, dive=10, peel=50, disengage=40, amplification=60, frontline=0, front2back=100,
    burst_dmg=60, sustained_dmg=100, aoe_dmg=80, poke=0,
    range=60, zone_control=10,
    waveclear=80, side_pressure=80, map_reach=20,
    hands_requirement=40, protection_dependence=70, resource_demand=100, lead_dependence=20,
    early=0, mid=40, late=100,
  ),
  CHAMPION_ID["Lee Sin"]: dict(
    white=0, blue=0, black=25, red=100, green=0,
    initiation=70, dive=80, peel=40, disengage=50, amplification=0, frontline=50, front2back=40,
    burst_dmg=80, sustained_dmg=40, aoe_dmg=40, poke=0,
    range=40, zone_control=10,
    waveclear=30, side_pressure=20, map_reach=60,
    hands_requirement=100, protection_dependence=0, resource_demand=50, lead_dependence=70,
    early=90, mid=80, late=30,
  ),
  CHAMPION_ID["Ornn"]: dict(
    white=100, blue=50, black=0, red=50, green=50,
    initiation=100, dive=60, peel=80, disengage=40, amplification=60, frontline=100, front2back=100,
    burst_dmg=30, sustained_dmg=30, aoe_dmg=70, poke=0,
    range=50, zone_control=80,
    waveclear=50, side_pressure=20, map_reach=30,
    hands_requirement=20, protection_dependence=0, resource_demand=10, lead_dependence=10,
    early=40, mid=70, late=100,
  ),
  CHAMPION_ID["Ziggs"]: dict(
    white=25, blue=100, black=0, red=0, green=0,
    initiation=10, dive=0, peel=40, disengage=50, amplification=0, frontline=0, front2back=60,
    burst_dmg=70, sustained_dmg=50, aoe_dmg=90, poke=100,
    range=100, zone_control=90,
    waveclear=100, side_pressure=60, map_reach=70,
    hands_requirement=30, protection_dependence=30, resource_demand=60, lead_dependence=30,
    early=50, mid=80, late=80,
  ),
  CHAMPION_ID["Ashe"]: dict(
    white=75, blue=75, black=0, red=25, green=25,
    initiation=90, dive=0, peel=40, disengage=30, amplification=0, frontline=0, front2back=100,
    burst_dmg=10, sustained_dmg=90, aoe_dmg=20, poke=30,
    range=60, zone_control=30,
    waveclear=30, side_pressure=0, map_reach=90,
    hands_requirement=20, protection_dependence=90, resource_demand=70, lead_dependence=20,
    early=60, mid=70, late=80,
  ),
  CHAMPION_ID["Braum"]: dict(
    white=100, blue=50, black=0, red=0, green=25,
    initiation=40, dive=20, peel=100, disengage=90, amplification=10, frontline=80, front2back=100,
    burst_dmg=0, sustained_dmg=0, aoe_dmg=10, poke=10,
    range=30, zone_control=50,
    waveclear=0, side_pressure=0, map_reach=30,
    hands_requirement=20, protection_dependence=0, resource_demand=0, lead_dependence=10,
    early=60, mid=70, late=80,
  ),
  CHAMPION_ID["Draven"]: dict(
    white=0, blue=0, black=75, red=100, green=0,
    initiation=10, dive=10, peel=10, disengage=20, amplification=0, frontline=0, front2back=80,
    burst_dmg=80, sustained_dmg=90, aoe_dmg=0, poke=0,
    range=40, zone_control=10,
    waveclear=30, side_pressure=40, map_reach=40,
    hands_requirement=90, protection_dependence=20, resource_demand=90, lead_dependence=90,
    early=100, mid=60, late=70,
  ),
  CHAMPION_ID["Fiora"]: dict(
    white=0, blue=50, black=25, red=25, green=100,
    initiation=10, dive=60, peel=0, disengage=0, amplification=0, frontline=30, front2back=40,
    burst_dmg=70, sustained_dmg=90, aoe_dmg=0, poke=0,
    range=10, zone_control=0,
    waveclear=50, side_pressure=100, map_reach=20,
    hands_requirement=90, protection_dependence=0, resource_demand=90, lead_dependence=40,
    early=50, mid=80, late=90,
  ),
  CHAMPION_ID["Ivern"]: dict(
    white=100, blue=75, black=0, red=0, green=75,
    initiation=25, dive=0, peel=90, disengage=90, amplification=80, frontline=40, front2back=90,
    burst_dmg=0, sustained_dmg=20, aoe_dmg=10, poke=10,
    range=60, zone_control=60,
    waveclear=0, side_pressure=10, map_reach=40,
    hands_requirement=40, protection_dependence=10, resource_demand=20, lead_dependence=10,
    early=50, mid=80, late=90,
  ),
  CHAMPION_ID["Jax"]: dict(
    white=0, blue=50, black=0, red=0, green=100,
    initiation=30, dive=80, peel=30, disengage=10, amplification=0, frontline=60, front2back=70,
    burst_dmg=40, sustained_dmg=90, aoe_dmg=10, poke=0,
    range=20, zone_control=20,
    waveclear=50, side_pressure=100, map_reach=30,
    hands_requirement=40, protection_dependence=10, resource_demand=90, lead_dependence=30,
    early=40, mid=75, late=90,
  ),
  CHAMPION_ID["Lulu"]: dict(
    white=100, blue=75, black=0, red=0, green=75,
    initiation=20, dive=0, peel=100, disengage=80, amplification=100, frontline=0, front2back=100,
    burst_dmg=10, sustained_dmg=0, aoe_dmg=0, poke=20,
    range=50, zone_control=10,
    waveclear=0, side_pressure=0, map_reach=40,
    hands_requirement=20, protection_dependence=10, resource_demand=10, lead_dependence=10,
    early=70, mid=80, late=100,
  ),
  CHAMPION_ID["Malphite"]: dict(  # tank build
    white=75, blue=50, black=50, red=0, green=0,
    initiation=100, dive=90, peel=40, disengage=0, amplification=0, frontline=90, front2back=80,
    burst_dmg=40, sustained_dmg=20, aoe_dmg=40, poke=0,
    range=40, zone_control=40,
    waveclear=50, side_pressure=10, map_reach=30,
    hands_requirement=0, protection_dependence=0, resource_demand=10, lead_dependence=0,
    early=30, mid=80, late=70,
  ),
  CHAMPION_ID["Orianna"]: dict(
    white=75, blue=100, black=0, red=0, green=25,
    initiation=60, dive=25, peel=60, disengage=50, amplification=30, frontline=0, front2back=90,
    burst_dmg=80, sustained_dmg=60, aoe_dmg=100, poke=70,
    range=70, zone_control=100,
    waveclear=90, side_pressure=30, map_reach=40,
    hands_requirement=60, protection_dependence=50, resource_demand=70, lead_dependence=30,
    early=60, mid=70, late=80,
  ),
  CHAMPION_ID["Renekton"]: dict(
    white=25, blue=0, black=25, red=100, green=0,
    initiation=50, dive=70, peel=40, disengage=10, amplification=0, frontline=70, front2back=60,
    burst_dmg=80, sustained_dmg=40, aoe_dmg=60, poke=0,
    range=20, zone_control=10,
    waveclear=50, side_pressure=70, map_reach=30,
    hands_requirement=30, protection_dependence=0, resource_demand=60, lead_dependence=70,
    early=90, mid=70, late=50,
  ),
  CHAMPION_ID["Sivir"]: dict(
    white=100, blue=25, black=0, red=0, green=75,
    initiation=30, dive=0, peel=10, disengage=70, amplification=60, frontline=0, front2back=100,
    burst_dmg=50, sustained_dmg=90, aoe_dmg=100, poke=50,
    range=50, zone_control=20,
    waveclear=100, side_pressure=60, map_reach=30,
    hands_requirement=30, protection_dependence=50, resource_demand=90, lead_dependence=20,
    early=40, mid=60, late=100,
  ),
  CHAMPION_ID["Twisted Fate"]: dict(  # AP utility build
    white=25, blue=100, black=50, red=25, green=0,
    initiation=70, dive=20, peel=40, disengage=20, amplification=0, frontline=0, front2back=40,
    burst_dmg=60, sustained_dmg=30, aoe_dmg=40, poke=30,
    range=60, zone_control=10,
    waveclear=60, side_pressure=80, map_reach=100,
    hands_requirement=30, protection_dependence=20, resource_demand=50, lead_dependence=20,
    early=50, mid=80, late=50,
  ),
}

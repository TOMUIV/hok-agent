import sys, os, json, time, math
sys.path.insert(0, "/workspace")
sys.stdout.reconfigure(encoding="utf-8")
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"

from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
from strategy_executor import ProtocolExecutor, BUTTONS
from trajectory import TrajectoryLogger

HERO_AI = 169
HERO_BOT = 112
runtime_id = f"fsm-battle-{int(time.time())}"

logger = TrajectoryLogger()
lib = interface.Interface()
lib.Init(interface_default_config)
print("Init OK", flush=True)

gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=30000, default_hero_config=get_default_hero_config())
addrs = ["tcp://0.0.0.0:35500", "tcp://0.0.0.0:35501"]
env = HoK1v1(runtime_id, gl, lib, addrs, aiserver_ip="127.0.0.1")
print("Env OK", flush=True)

executor = ProtocolExecutor(self_hero_id=HERO_AI)
camp = {"mode":"1v1","heroes":[[{"hero_id":HERO_AI}],[{"hero_id":HERO_BOT}]]}
obs, r, d, info = env.reset(camp, use_common_ai=[False, True], eval=True)
print(f"Battle: 后羿 vs 鲁班 | State Machine", flush=True)

# Dynamic spawn detection
pb = info[0].get("req_pb")
SPAWN_X, SPAWN_Z = -32308, -32322
if pb and hasattr(pb, "hero_list"):
    for h in pb.hero_list:
        if getattr(h, "config_id", 0) == HERO_AI:
            floc = getattr(h, "location", None)
            if floc:
                SPAWN_X = getattr(floc, "x", -32308)
                SPAWN_Z = getattr(floc, "z", -32322)
            break
ENEMY_SPAWN_X = 32308 if SPAWN_X < 0 else -32308
LANE_DIR = 1 if ENEMY_SPAWN_X > SPAWN_X else -1
print(f"Spawn: ({SPAWN_X}, {SPAWN_Z}) dir={'+X' if LANE_DIR>0 else '-X'}", flush=True)

class StateMachine:
    def __init__(self):
        self.current_mode = "FARM"
        self.sticky = 0

    def get_danger_x(self, pb, self_camp_val):
        if not pb:
            return SPAWN_X + LANE_DIR * 2985
        danger = SPAWN_X + LANE_DIR * 999999
        for o in getattr(pb, "organ_list", []):
            otype = str(getattr(o, "type", ""))
            if "TOWER" not in otype:
                continue
            if getattr(o, "hp", 0) <= 0:
                continue
            oc = getattr(o, "camp", None)
            if oc is None: continue
            ocv = oc.value if hasattr(oc, "value") else oc
            if ocv == self_camp_val: continue
            loc = getattr(o, "location", None)
            if loc is None: continue
            ox = getattr(loc, "x", 0)
            td = ox - LANE_DIR * 8300
            if LANE_DIR * td < LANE_DIR * danger:
                danger = td
        return danger

    def _enemy_minion_count(self, pb, near_x):
        if not pb: return 0
        count = 0
        for s in getattr(pb, "soldier_list", []):
            if not getattr(s, "alive", True): continue
            loc = getattr(s, "location", None)
            if not loc: continue
            if abs(getattr(loc, "x", 0) - near_x) < 5000:
                count += 1
        return count

    def decide(self, hp_pct, enemy_hp_pct, dist, self_x, enemy_x, danger_x, pb, enemy_hp_raw):
        hp_adv = hp_pct - enemy_hp_pct
        if self.sticky > 0:
            self.sticky -= 1
            return self.current_mode

        new_mode = "FARM"
        if hp_pct < 0.01:
            new_mode = "FARM"
        elif abs(self_x - SPAWN_X) < 3000 and hp_pct < 0.98:
            new_mode = "RETREAT"
        elif hp_pct < 0.25:
            new_mode = "RETREAT"
        elif self._enemy_minion_count(pb, self_x) >= 2:
            new_mode = "DEFEND"
        elif LANE_DIR * self_x > LANE_DIR * danger_x:
            friendly_count = 0
            enemy_tower_x = 11285 if LANE_DIR > 0 else -11240
            for s in getattr(pb, "soldier_list", []) if pb else []:
                if not getattr(s, "alive", True): continue
                sloc = getattr(s, "location", None)
                if not sloc: continue
                if abs(getattr(sloc, "x", 0) - enemy_tower_x) > 5000: continue
                sc = getattr(s, "camp", -1)
                if hasattr(sc, "value"): sc = sc.value
                if sc == self_camp_val:  # friendly minions
                    friendly_count += 1
            if friendly_count == 0:
                new_mode = "KITE"  # back off from tower, not all the way to spawn
            else:
                new_mode = "FARM"  # safe to push with minion cover
        elif hp_pct < 0.35 and hp_adv < -0.1:
            new_mode = "RETREAT"
        elif dist > 8000:
            new_mode = "FARM"
        elif dist > 3500:
            new_mode = "POKE"
        elif hp_pct > 0.55:
            new_mode = "ALL_IN"
        else:
            new_mode = "KITE"
        if new_mode != self.current_mode:
            self.sticky = 5
            self.current_mode = new_mode
            print(f"  [SWITCH] {new_mode}: hp%={hp_pct:.0%} dist={dist:.0f} x={self_x:.0f} danger={danger_x:.0f} minions={self._enemy_minion_count(pb,self_x)}", flush=True)
        return self.current_mode

sm = StateMachine()
start_delay = 30
start_t = time.time()

for step in range(3000):
    s = info[0]
    pb = s.get("req_pb")
    heroes = getattr(pb, "hero_list", []) if pb else []
    soldiers = getattr(pb, "soldier_list", []) if pb else []
    self_h = enemy_h = None
    for h in heroes:
        if getattr(h, "config_id", 0) == HERO_AI: self_h = h
        else: enemy_h = h

    hp_pct = 1.0; enemy_hp_pct = 1.0; dist = 99999; self_x = 0; enemy_x = 0; enemy_hp_raw = 1
    if self_h and enemy_h:
        shp = getattr(self_h, "hp", 1); smhp = getattr(self_h, "max_hp", 1)
        ehp = getattr(enemy_h, "hp", 1); emhp = getattr(enemy_h, "max_hp", 1)
        enemy_hp_raw = ehp; hp_pct = shp / max(smhp, 1); enemy_hp_pct = ehp / max(emhp, 1)
        ls = getattr(self_h, "location", None); le = getattr(enemy_h, "location", None)
        if ls and le:
            self_x = ls.x; enemy_x = le.x
            dist = math.sqrt((le.x-ls.x)**2 + (le.z-ls.z)**2)

    self_camp_val = 0
    if self_h:
        scv = getattr(self_h, "camp", 0)
        if hasattr(scv, "value"): scv = scv.value
        self_camp_val = scv

    danger_x = sm.get_danger_x(pb, self_camp_val)

    if start_delay > 0:
        start_delay -= 1
        mode = "IDLE"
        action = executor.execute_macro("RETREAT", s)
    else:
        mode = sm.decide(hp_pct, enemy_hp_pct, dist, self_x, enemy_x, danger_x, pb, enemy_hp_raw)
        action = executor.execute_macro(mode, s)

    frame_no = getattr(pb, "frame_no", 0) if pb else 0
    heroes_data = []
    if pb and hasattr(pb, "hero_list"):
        for h in pb.hero_list:
            cv = getattr(h, "camp", 0)
            if hasattr(cv, "value"): cv = cv.value
            loc2 = getattr(h, "location", None)
            heroes_data.append({
                "config_id": getattr(h, "config_id", 0),
                "hp": getattr(h, "hp", 0), "max_hp": getattr(h, "max_hp", 0),
                "camp": cv, "x": getattr(loc2, "x", 0) if loc2 else 0,
            })

    logger.log_llm_call("fsm", f"Fr{frame_no}", mode,
        json.dumps({"action": list(action), "heroes": heroes_data}, ensure_ascii=False))
    logger.log_action(action)

    try:
        obs, r, d, info = env.step([action, (0,0,0,0,0,0)])
    except Exception as e:
        print(f"[ZMQ ERROR] {e}", flush=True)
        print(f"[GAMEOVER] Step {step}", flush=True)
        break

    if step % 10 == 0:
        hp_str = "; ".join([f"ID{h['config_id']}:{h['hp']}/{h['max_hp']}" for h in heroes_data])
        elapsed = time.time() - start_t
        print(f"[{elapsed:5.0f}s] Fr{frame_no:4d} S{step:3d} {mode:10s} x={self_x:.0f} danger={danger_x:.0f} dist={dist:.0f} hp%={hp_pct:.0%} | {hp_str}", flush=True)

    if d[0]:
        print(f"\nGameover!", flush=True)
        break

elapsed = time.time() - start_t
env.close_game()
logger.close()
print(f"Done. {step+1} steps in {elapsed:.0f}s", flush=True)

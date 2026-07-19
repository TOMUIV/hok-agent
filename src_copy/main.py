import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")
for d in ["ai_config/ai_server/skill_type","ai_config/5v5/tactics/feature","ai_config/5v5/common","ai_config/ai_server/pb2struct"]:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)
for p, c in {
    "ai_server_conf.json": '{"game_mode":"1v1"}', "transfer_table.json": "{}",
    "ai_config/AiMgr.txt": "skill 0 1 2", "ai_config/ai_server/skill_type/2": "0",
    "ai_config/ai_server/rl_config_file.txt": "",
    "ai_config/ai_server/pb2struct/pb2struct_config_server.txt": "",
    "ai_config/5v5/tactics/feature/skill_state_description_config.txt": "",
    "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt": "",
    "ai_config/5v5/common/skill_manager_config.txt": "",
    "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat": "",
    "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt": "",
}.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
from openai import OpenAI
from hero_db import hero_name
from memory import MemorySystem

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
MODEL = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
client = OpenAI(api_key=API_KEY, base_url=BASE_URL) if API_KEY else None

memory_sys = MemorySystem()

HERO_AI = 199  # 公孙离 (LLM controls)
HERO_BOT = 169  # 后羿 (common AI)

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("demo", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="172.24.50.71")

CAMP = {"mode":"1v1","heroes":[[{"hero_id":HERO_AI}],[{"hero_id":HERO_BOT}]]}
print(f"{hero_name(HERO_AI)}(LLM) vs {hero_name(HERO_BOT)}(Bot)", flush=True)
obs, r, d, info = env.reset(CAMP, use_common_ai=[False,True], eval=True)
print(f"Reset OK", flush=True)

BUTTONS = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","HealSkill","ChosenSkill","Recall","Skill4","EquipSkill"]
DIR_MAP = {"N":(0,1),"NE":(1,1),"E":(1,0),"SE":(1,-1),"S":(0,-1),"SW":(-1,-1),"W":(-1,0),"NW":(-1,1),"STOP":(0,0)}
ACT_MAP = {"MOVE":2,"ATTACK":3,"SKILL_1":4,"SKILL_2":5,"SKILL_3":6,"RECALL":9}

SYS_PROMPT = f"""You control {hero_name(HERO_AI)} in a 1v1 Honor of Kings match.

State format:
> Frame N
  [YOU] HeroName LV* HP:*/*(*)% EP:* Gold:* @(x,y)
  [ENEMY] HeroName LV* HP:*/*(FOW/%) EP:* @(x,y)
  Legal: Move, Attack, Skill1, ...

Output decisions as:
FinalAction: MOVE(N)
FinalAction: ATTACK(ENEMY)
FinalAction: SKILL_1(ENEMY,0,0)
FinalAction: RECALL()
"""
SYS_PROMPT += memory_sys.retrieve(HERO_AI, HERO_BOT)

start = time.time()
for step in range(30):
    s = info[0]
    pb = s["req_pb"]
    heroes = pb.hero_list
    frame = pb.frame_no
    self_h = [h for h in heroes if h.config_id == HERO_AI][0]
    enemy_h = [h for h in heroes if h.config_id != HERO_AI][0]
    la = s["legal_action"]
    legal_btns = [BUTTONS[i] for i in range(12) if la[i] == 1]

    # Build state text
    def hp_str(h, tag):
        v = h.camp_visible
        if tag == "ENEMY" and not (any(v) if v else True):
            return f"{h.hp}/{h.max_hp}(FOW)"
        return f"{h.hp}/{h.max_hp}({h.hp/h.max_hp*100:.0f}%)"
    loc_self = f"({self_h.location.x},{self_h.location.y})" if self_h.location else "(?,?)"
    loc_enemy = f"({enemy_h.location.x},{enemy_h.location.y})" if enemy_h.location else "(?,?)"
    state_text = (
        f"> Frame {frame}\n"
        f"  [YOU] {hero_name(HERO_AI)} LV{self_h.level} HP:{hp_str(self_h,'YOU')} "
        f"EP:{self_h.ep} Gold:{self_h.money} @{loc_self}\n"
        f"  [ENEMY] {hero_name(HERO_BOT)} LV{enemy_h.level} HP:{hp_str(enemy_h,'ENEMY')} "
        f"EP:{enemy_h.ep} @{loc_enemy}\n"
        f"  Legal: {', '.join(legal_btns)}"
    )

    # LLM decide
    reply = ""
    if client:
        try:
            resp = client.chat.completions.create(model=MODEL,
                messages=[{"role":"system","content":SYS_PROMPT},{"role":"user","content":state_text}],
                temperature=0.8, max_tokens=200)
            reply = resp.choices[0].message.content.strip()
        except Exception as e:
            reply = f"Error: {e}"

    # Parse FinalAction
    import re
    m = re.search(r'FinalAction:\s*(\w+)\(([^)]*)\)', reply)
    if m:
        atype, pstr = m.group(1).upper(), m.group(2)
    else:
        atype, pstr = "MOVE", "N"

    btn = ACT_MAP.get(atype, 2)
    mx, mz, tgt = 1, 1, 0
    if atype == "MOVE":
        d = pstr.strip().upper()
        if d in DIR_MAP:
            mx, mz = DIR_MAP[d]
            mx, mz = mx + 8, mz + 8
        else:
            mx, mz = 8, 8
    elif atype == "ATTACK":
        tgt = 1 if "ENEMY" in pstr.upper() else 1
    elif atype.startswith("SKILL"):
        tgt = 1
    # Validate
    if btn not in [i for i in range(12) if la[i] == 1]:
        btn = [i for i in range(12) if la[i] == 1][0] if any(la[:12]) else 2
    mx = max(1, min(15, mx))
    mz = max(1, min(15, mz))
    action = (btn, mx, mz, 1, 1, tgt)

    obs, r, d, info = env.step([action, (0,0,0,0,0,0)])
    elapsed = time.time() - start
    print(f"  Step{step:2d} Fr{frame:3d} [{elapsed:4.0f}s] {atype:12s} "
          f"YOU:{self_h.hp}/{self_h.max_hp} ENEMY:{enemy_h.hp}/{enemy_h.max_hp}", flush=True)
    if d[0]:
        print(f"GAMEOVER at step {step}!", flush=True); break

outcome = "win" if d[0] else "loss"
traj_path = os.path.join(os.path.dirname(__file__), "..", "trajectories", "last_game.jsonl")
memory_sys.reflect(HERO_AI, HERO_BOT, outcome, step, traj_path, client)

env.close_game()
print(f"DONE. {step+1} steps in {time.time()-start:.0f}s, outcome={outcome}", flush=True)

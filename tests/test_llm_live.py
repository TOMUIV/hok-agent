import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")
for d in ["ai_config/ai_server/skill_type", "ai_config/5v5/tactics/feature", "ai_config/5v5/common", "ai_config/ai_server/pb2struct"]:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)
files = {"ai_server_conf.json": '{"game_mode":"1v1"}', "transfer_table.json": "{}", "ai_config/AiMgr.txt": "skill 0 1 2", "ai_config/ai_server/skill_type/2": "0", "ai_config/ai_server/rl_config_file.txt": "", "ai_config/ai_server/pb2struct/pb2struct_config_server.txt": "", "ai_config/5v5/tactics/feature/skill_state_description_config.txt": "", "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt": "", "ai_config/5v5/common/skill_manager_config.txt": "", "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat": "", "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt": ""}
for p, c in files.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
import numpy as np
from openai import OpenAI

DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "deepseek-v4-flash"

HERO_NAMES = {106: "小乔", 107: "赵云", 132: "马可波罗", 169: "后羿", 199: "公孙离"}
BUTTON_NAMES = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","HealSkill","ChosenSkill","Recall","Skill4","EquipSkill"]
client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL) if DASHSCOPE_API_KEY else None

SYSTEM_PROMPT = """You control a hero in Honor of Kings. Output JSON decisions.

Decisions: MOVE, NORMAL_ATTACK, SKILL_1, SKILL_2, SKILL_3, RECALL, NONE

Params:
  MOVE: direction (N/NE/E/SE/S/SW/W/NW/STOP)
  ATTACK: target (ENEMY_HERO_0/ENEMY_HERO_1)
  SKILL_1/2/3: target, offset_x(-8~8), offset_z(-8~8)

JSON format: {"decision_type":"MOVE","params":{"direction":"NE"}}"""

ACT_MAP = {"NONE":0,"NONE_2":1,"MOVE":2,"NORMAL_ATTACK":3,"SKILL_1":4,"SKILL_2":5,"SKILL_3":6,"HEAL":7,"CHOSEN_SKILL":8,"RECALL":9,"SKILL_4":10,"EQUIPMENT":11}
DIR_MAP = {"STOP":0,"N":1,"NNE":2,"NE":3,"ENE":4,"E":5,"ESE":6,"SE":7,"SSE":8,"S":9,"SSW":10,"SW":11,"WSW":12,"W":13,"WNW":14,"NW":15,"NNW":16}
TGT_MAP = {"ENEMY_HERO_0":1,"ENEMY_HERO_1":2,"ENEMY_HERO_2":3,"SELF":7}

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000, default_hero_config=get_default_hero_config(), max_frame_num=200)
env = HoK1v1("llm-test", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="172.24.50.71")
print("Reset...", flush=True)
obs, r, d, info = env.reset({"mode":"1v1","heroes":[[{"hero_id":199}],[{"hero_id":169}]]}, use_common_ai=[False,True], eval=True)
print(f"Reset OK! obs: {obs[0].shape}  Hero: 公孙离 vs 后羿", flush=True)

for step in range(15):
    la = info[0]["legal_action"]
    button_seg = la[:12]
    available = [BUTTON_NAMES[i] for i in range(12) if button_seg[i] == 1]
    pb = info[0]["req_pb"]
    heroes = pb.hero_list if hasattr(pb, "hero_list") else []
    hp_info = "; ".join([f"{HERO_NAMES.get(getattr(h,'config_id',0),'?')} HP:{getattr(h,'hp','?')} Lv:{getattr(h,'level','?')}" for h in heroes])
    frame = getattr(pb, "frame_no", 0)

    prompt = f"[Frame {frame}] {hp_info} | Available: {','.join(available)}\nDecision? Output JSON."
    response_text = '{"decision_type":"MOVE","params":{"direction":"N"}}'
    if client:
        try:
            resp = client.chat.completions.create(model=MODEL_NAME,
                messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}],
                temperature=0.7, max_tokens=150)
            response_text = resp.choices[0].message.content.strip()
        except Exception as e:
            response_text = '{"decision_type":"MOVE","params":{"direction":"N"}}'
    try:
        dec = json.loads(response_text) if isinstance(response_text, str) else response_text
    except:
        dec = {"decision_type":"MOVE","params":{"direction":"N"}}

    dt = dec.get("decision_type","MOVE")
    params = dec.get("params",{})
    btn = ACT_MAP.get(dt, 2)
    move_x, move_z, skill_x, skill_z, tgt = 0, 0, 0, 0, 0
    if dt == "MOVE":
        d = params.get("direction","N")
        idx = DIR_MAP.get(d.upper(), 1)
        move_x, move_z = idx * 2 // 5, idx % 5
    elif dt in ("NORMAL_ATTACK","SKILL_1","SKILL_2","SKILL_3"):
        t = params.get("target","ENEMY_HERO_0")
        tgt = TGT_MAP.get(t.upper(), 1)
        skill_x = int(params.get("offset_x",0)) + 8
        skill_z = int(params.get("offset_z",0)) + 8
    actions = [(btn, move_x, move_z, skill_x, skill_z, tgt), (0,0,0,0,0,0)]
    obs, r, d, info = env.step(actions)
    print(f"Step {step}: {dt:15s} hp=[{hp_info:40s}] raw={response_text[:60]}", flush=True)
    if d[0]:
        print("GAMEOVER!", flush=True); break

env.close_game()
print("DONE!", flush=True)

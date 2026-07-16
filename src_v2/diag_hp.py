import sys, os, json
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
import numpy as np

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("diag", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="172.24.50.71")

print("Reset with TWO AI players...", flush=True)
obs, r, d, info = env.reset({"mode":"1v1","heroes":[[{"hero_id":199}],[{"hero_id":169}]]}, use_common_ai=[False,False], eval=True)

print(f"\ninfo[0] keys: {list(info[0].keys()) if info[0] else 'None'}", flush=True)
print(f"info[1] keys: {list(info[1].keys()) if info[1] else 'None'}", flush=True)

def dump_pb(pb, label):
    if pb is None:
        print(f"\n{label}: pb is None", flush=True)
        return
    print(f"\n{label}: frame={getattr(pb,'frame_no','?')} gameover={getattr(pb,'gameover','?')}", flush=True)
    heroes = getattr(pb, 'hero_list', [])
    for i, h in enumerate(heroes):
        cid = getattr(h, 'config_id', 0)
        hp = getattr(h, 'hp', 0)
        mhp = getattr(h, 'max_hp', 0)
        camp = getattr(h, 'camp', 0)
        visible = getattr(h, 'camp_visible', [])
        print(f"  Hero[{i}]: cid={cid} hp={hp}/{mhp} camp={camp} visible={visible}", flush=True)

dump_pb(info[0]["req_pb"], "info[0].req_pb")
dump_pb(info[1]["req_pb"], "info[1].req_pb")

# Step once with MOVE actions
def legal_move(info_i):
    if info_i is None:
        return (0,0,0,0,0,0)
    la = info_i["legal_action"]
    btns = [i for i in range(12) if la[i] == 1]
    btn = btns[0] if btns else 2
    return (btn, 1, 1, 0, 0, 0)

print("\nStepping 5 times...", flush=True)
for step in range(5):
    a0 = legal_move(info[0])
    a1 = legal_move(info[1])
    obs, r, d, info = env.step([a0, a1])
    dump_pb(info[0]["req_pb"], f"Step{step} info[0]")
    if info[1] and info[1].get("req_pb"):
        dump_pb(info[1]["req_pb"], f"Step{step} info[1]")
    else:
        print(f"Step{step} info[1]: None", flush=True)
    if d[0] or d[1]:
        print(f"Gameover at step {step}!", flush=True)
        break

env.close_game()
print("\nDONE", flush=True)

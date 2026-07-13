import sys, os, json, numpy as np
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
import hok.hok1v1.lib.interface as lib_iface

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000,
    default_hero_config=get_default_hero_config(), max_frame_num=80)
env = HoK1v1("dump2", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="172.24.50.71")

obs, r, d, info = env.reset({"mode":"1v1","heroes":[[{"hero_id":199}],[{"hero_id":169}]]}, use_common_ai=[False,True], eval=True)
pb = info[0]["req_pb"]

print("=== dir(req_pb) ===", flush=True)
for attr in dir(pb):
    if not attr.startswith("_"):
        try:
            val = getattr(pb, attr)
            if callable(val):
                print(f"  {attr}: <callable>", flush=True)
            else:
                val_str = str(val)
                print(f"  {attr}: {val_str[:200]}", flush=True)
        except Exception as e:
            print(f"  {attr}: ERROR {e}", flush=True)

print("\n=== hero_list (if available) ===", flush=True)
try:
    heroes = pb.hero_list
    print(f"hero_list type: {type(heroes)}, len: {len(heroes)}", flush=True)
    for i, h in enumerate(heroes):
        print(f"\n--- Hero {i} ---", flush=True)
        for attr in dir(h):
            if not attr.startswith("_"):
                try:
                    val = getattr(h, attr)
                    if not callable(val):
                        print(f"  {attr}: {val}", flush=True)
                except:
                    pass
except Exception as e:
    print(f"No hero_list: {e}", flush=True)

print("\n=== command_info_list (if available) ===", flush=True)
try:
    for ci in pb.command_info_list:
        print(f"\n--- CommandInfo ---", flush=True)
        for attr in dir(ci):
            if not attr.startswith("_"):
                try:
                    val = getattr(ci, attr)
                    if not callable(val):
                        print(f"  {attr}: {val}", flush=True)
                except:
                    pass
except Exception as e:
    print(f"No command_info_list: {e}", flush=True)

# Try stepping once to see if state changes
print("\n=== Step once and check hero fields ===", flush=True)
la = info[0]["legal_action"]
btn_seg = la[:12]
legal_btns = [i for i in range(12) if btn_seg[i] == 1]
btn = np.random.choice(legal_btns) if legal_btns else 2
act = [(btn,0,0,0,0,0), (0,0,0,0,0,0)]
obs2, r2, d2, info2 = env.step(act)
pb2 = info2[0]["req_pb"]
try:
    h2 = pb2.hero_list
    for i, h in enumerate(h2):
        print(f"\n--- Hero {i} (after step) ---", flush=True)
        for attr in dir(h):
            if not attr.startswith("_"):
                try:
                    val = getattr(h, attr)
                    if not callable(val):
                        print(f"  {attr}: {val}", flush=True)
                except:
                    pass
except Exception as e:
    print(f"Error: {e}", flush=True)

env.close_game()
print("\nDONE", flush=True)

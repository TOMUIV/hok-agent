import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

base = "/hok_env/hok/hok1v1"
ailab_dir = os.path.join(base, "AILab")
os.makedirs(os.path.join(ailab_dir, "ai_config/ai_server/pb2struct"), exist_ok=True)
os.makedirs(os.path.join(ailab_dir, "ai_config/5v5/tactics/feature"), exist_ok=True)
os.makedirs(os.path.join(ailab_dir, "ai_config/5v5/common"), exist_ok=True)

ai_server_conf = {
    "game_mode": "1v1",
    "model_path": ".",
    "ai_config_dir": "./AILab/ai_config",
    "rl_config_file": "./AILab/ai_config/ai_server/rl_config_file.txt",
    "transfer_table": "./AILab/transfer_table.json",
    "skill_type_path": "./AILab/ai_config/ai_server/skill_type",
    "version": 1,
    "heroes": [{"hero_id": 199, "name": "gongsunli"}],
}
with open(os.path.join(ailab_dir, "ai_server_conf.json"), "w") as f:
    import json; json.dump(ai_server_conf, f)
with open(os.path.join(ailab_dir, "transfer_table.json"), "w") as f:
    f.write("{}")
with open(os.path.join(ailab_dir, "ai_config/AiMgr.txt"), "w") as f:
    f.write("default")
for fname in ["rl_config_file.txt", "pb2struct/pb2struct_config_server.txt"]:
    with open(os.path.join(ailab_dir, "ai_config/ai_server", fname), "w") as f:
        f.write("")
for fname in ["skill_state_description_config.txt", "4_skill_hero_skill_state_description_config.txt", "bit_map_250_organ_1v1.dat"]:
    with open(os.path.join(ailab_dir, "ai_config/5v5/tactics/feature", fname), "w") as f:
        f.write("")
with open(os.path.join(ailab_dir, "ai_config/5v5/common/skill_manager_config.txt"), "w") as f:
    f.write("")
with open(os.path.join(ailab_dir, "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt"), "w") as f:
    f.write("")

print("AILab files created in", ailab_dir, flush=True)
for root, dirs, files in os.walk(ailab_dir):
    for fn in files:
        fp = os.path.join(root, fn)
        print(f"  {fp}", flush=True)

print("\nNow loading SDK...", flush=True)
from hok.hok1v1.env1v1 import interface_default_config
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
from hok.hok1v1 import HoK1v1

lib = interface.Interface()
lib.Init(interface_default_config)
print("Init OK", flush=True)

gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=30000, default_hero_config=get_default_hero_config())
env = HoK1v1("test", gl, lib, ["tcp://0.0.0.0:35150","tcp://0.0.0.0:35151"], aiserver_ip="172.24.50.71")
print("Reset...", flush=True)
obs, r, d, info = env.reset({"mode":"1v1","heroes":[[{"hero_id":199}],[{"hero_id":199}]]}, use_common_ai=[False,True], eval=True)
print(f"OK! obs shape: {obs[0].shape}", flush=True)
pb = info[0]["req_pb"]
for h in pb.hero_list:
    print(f"  Hero: config_id={h.config_id} camp={h.camp} hp={h.hp}", flush=True)

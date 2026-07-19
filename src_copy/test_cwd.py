import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

# Create AILab in current working directory
cwd = os.getcwd()
ailab = os.path.join(cwd, "AILab")
os.makedirs(os.path.join(ailab, "ai_config/ai_server/skill_type"), exist_ok=True)
os.makedirs(os.path.join(ailab, "ai_config/5v5/tactics/feature"), exist_ok=True)
os.makedirs(os.path.join(ailab, "ai_config/5v5/common"), exist_ok=True)
os.makedirs(os.path.join(ailab, "ai_config/ai_server/pb2struct"), exist_ok=True)

def w(p, c):
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

w("ai_server_conf.json", '{"game_mode":"1v1"}')
w("transfer_table.json", "{}")
w("ai_config/AiMgr.txt", "skill 0 1 2")
w("ai_config/ai_server/skill_type/2", "0")
w("ai_config/ai_server/rl_config_file.txt", "")
w("ai_config/ai_server/pb2struct/pb2struct_config_server.txt", "")
w("ai_config/5v5/tactics/feature/skill_state_description_config.txt", "")
w("ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt", "")
w("ai_config/5v5/common/skill_manager_config.txt", "")
w("ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat", "")
w("ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt", "")

print(f"AILab created at {ailab}", flush=True)
for r, d, fs in os.walk(ailab):
    for fn in fs:
        print(f"  {os.path.join(r, fn)}", flush=True)

# Now run test
sys.path.insert(0, "/hok_env")
os.chdir(cwd)
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

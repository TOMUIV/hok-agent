import sys, os, json, subprocess
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

# Mount gamecore core_assets and create AILab structure
CORE_ASSETS = "/core_assets"
if os.path.isdir(CORE_ASSETS):
    ailab_src = os.path.join(CORE_ASSETS, "customresources/ailab")
    ailab_dst = os.path.join(CORE_ASSETS, "customresources/AILab")
    if not os.path.exists(ailab_dst):
        subprocess.run(["ln", "-sf", ailab_src, ailab_dst])
    conf_path = os.path.join(CORE_ASSETS, "customresources/AILab/ai_server_conf.json")
    if not os.path.exists(conf_path):
        with open(conf_path, "w") as f:
            json.dump({"version": 1, "game_mode": "1v1"}, f)
    os.environ["HOK_GAMECORE_PATH"] = CORE_ASSETS
    print(f"AILab ready: {os.path.islink(ailab_dst)}, conf: {os.path.exists(conf_path)}", flush=True)

# Try multiple approaches for the config path
for env_var in ["HOK_GAMECORE_PATH", "GAMECORE_PATH", "AI_CONFIG_PATH"]:
    if env_var in os.environ:
        print(f"{env_var}={os.environ[env_var]}", flush=True)

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

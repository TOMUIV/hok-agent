import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

from hok.hok1v1.env1v1 import interface_default_config
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
from hok.hok1v1 import HoK1v1

lib = interface.Interface()
lib.Init(interface_default_config)
print("Init OK", flush=True)

GC = "host.docker.internal:23432"
AI = "172.24.50.71"
addrs = ["tcp://0.0.0.0:35150", "tcp://0.0.0.0:35151"]
gl = GamecoreClient(server_addr=GC, gamecore_req_timeout=30000, default_hero_config=get_default_hero_config())
env = HoK1v1("test-llm", gl, lib, addrs, aiserver_ip=AI)
print("Env OK", flush=True)

camp_hero_list = {"mode": "1v1", "heroes": [[{"hero_id": 199}], [{"hero_id": 199}]]}
print("Calling start_game directly...", flush=True)
gl.start_game("test-llm", [(None, None), ("172.24.50.71", 35150)], camp_hero_list, eval_mode=True)
print("start_game returned, waiting 10s for sim to init...", flush=True)
time.sleep(10)
print("Now calling env.reset...", flush=True)
try:
    obs, r, d, info = env.reset(camp_hero_list, use_common_ai=[False, True], eval=True)
    print(f"Reset OK! obs shape: {obs[0].shape}", flush=True)
except Exception as e:
    print(f"Reset error: {e}", flush=True)

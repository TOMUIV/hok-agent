import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "/usr/lib/python3.8/site-packages")
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
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=30000, default_hero_config=get_default_hero_config())
env = HoK1v1("test", gl, lib, ["tcp://0.0.0.0:35150","tcp://0.0.0.0:35151"], aiserver_ip="172.24.50.71")
print("Reset...", flush=True)
obs, r, d, info = env.reset({"mode":"1v1","heroes":[[{"hero_id":199}],[{"hero_id":199}]]}, use_common_ai=[False,True], eval=True)
print("OK, shape:", obs[0].shape, flush=True)

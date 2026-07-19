import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"

import hok.hok1v1.lib.interface as interface
from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient

lib = interface.Interface()
lib.Init(interface_default_config)
print("Init OK", flush=True)

gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=30000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("test-hok", gl, lib,
    ["tcp://0.0.0.0:35500", "tcp://0.0.0.0:35501"],
    aiserver_ip="localhost")
print("Reset...", flush=True)
try:
    obs, r, d, info = env.reset(
        {"mode": "1v1", "heroes": [[{"hero_id": 199}], [{"hero_id": 169}]]},
        use_common_ai=[False, True], eval=True)
    print("OK!", flush=True)
except Exception as e:
    print(f"ERR: {e}", flush=True)
    import traceback; traceback.print_exc()

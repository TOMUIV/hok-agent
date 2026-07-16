import sys, os, time, json
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"

from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
import numpy as np

ZMQ_BASE = 35500
lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=30000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("test-hok", gl, lib,
    [f"tcp://0.0.0.0:{ZMQ_BASE}", f"tcp://0.0.0.0:{ZMQ_BASE+1}"],
    aiserver_ip="localhost")
print("Resetting...", flush=True)
try:
    obs, r, d, info = env.reset(
        {"mode": "1v1", "heroes": [[{"hero_id": 199}], [{"hero_id": 169}]]},
        use_common_ai=[False, True], eval=True)
except Exception as e:
    print(f"Reset failed: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)

print(f"Reset OK! obs[0] shape: {obs[0].shape}", flush=True)
pb = info[0]["req_pb"]
for h in pb.hero_list:
    cid = getattr(h, 'config_id', 0)
    hp = getattr(h, 'hp', 0)
    print(f"  Hero: config_id={cid} hp={hp}", flush=True)

for step in range(10):
    la = info[0]["legal_action"]
    shapes = env.action_space()
    parts = np.split(la, [sum(shapes[:i+1]) for i in range(len(shapes)-1)])
    act = tuple(np.random.choice([j for j, v in enumerate(p) if v == 1]) for p in parts)
    obs, r, d, info = env.step([act, (0,0,0,0,0,0)])
    pb = info[0]["req_pb"]
    hp = ",".join(str(getattr(h, 'hp', '?')) for h in pb.hero_list)
    print(f"  Step {step}: hp=[{hp}]", flush=True)
    if d[0]:
        print("GAMEOVER!", flush=True)
        break

env.close_game()
print("DONE!", flush=True)

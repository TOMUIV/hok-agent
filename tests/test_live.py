import sys, os
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
addrs = [f"tcp://0.0.0.0:{35150 + i}" for i in range(2)]
gl = GamecoreClient(server_addr=os.environ["GAMECORE_SERVER_ADDR"], gamecore_req_timeout=15000, default_hero_config=get_default_hero_config())
env = HoK1v1("test-llm", gl, lib, addrs, aiserver_ip=os.environ["AI_SERVER_ADDR"])
print("Env OK", flush=True)

camp = {"mode": "1v1", "heroes": [[{"hero_id": 132}], [{"hero_id": 169}]]}
print("Resetting...", flush=True)
obs, r, d, info = env.reset(camp, use_common_ai=[False, True], eval=True)
print(f"Reset OK! obs[0]={obs[0].shape}", flush=True)
pb = info[0]["req_pb"]
for h in pb.hero_list:
    print(f"  Hero: config_id={h.config_id} camp={h.camp} hp={h.hp}", flush=True)

for step in range(50):
    import numpy as np
    la = info[0]["legal_action"]
    shapes = env.action_space()
    splits = [sum(shapes[:i+1]) for i in range(len(shapes)-1)]
    parts = np.split(la, splits)
    act = [np.random.choice([j for j, v in enumerate(p) if v == 1]) for p in parts]
    ac = [tuple(act), (0,0,0,0,0,0)]
    obs, r, d, info = env.step(ac)
    pb = info[0]["req_pb"]
    hp = ",".join([str(getattr(h, 'hp', '?')) for h in pb.hero_list])
    if step % 10 == 0:
        print(f"Step {step}: hp=[{hp}]", flush=True)
    if d[0] or d[1]:
        print("Gameover!", flush=True)
        break
env.close_game()
print("DONE", flush=True)

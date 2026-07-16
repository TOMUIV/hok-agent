import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"

import hok.hok1v1.lib.interface as interface
from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import numpy as np

lib = interface.Interface()
lib.Init(interface_default_config)
print("Init OK", flush=True)

gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=30000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("test-hok", gl, lib,
    ["tcp://0.0.0.0:35500", "tcp://0.0.0.0:35501"],
    aiserver_ip="localhost")
print("Resetting...", flush=True)
obs, r, d, info = env.reset(
    {"mode": "1v1", "heroes": [[{"hero_id": 199}], [{"hero_id": 169}]]},
    use_common_ai=[False, True], eval=True)
print(f"Reset OK! obs[0]={obs[0].shape}", flush=True)

pb = info[0]["req_pb"]
for h in pb.hero_list:
    cid = getattr(h, 'config_id', 0)
    hp = getattr(h, 'hp', 0)
    print(f"  Hero config_id={cid} hp={hp}", flush=True)

for step in range(10):
    la = info[0]["legal_action"]
    shapes = [12, 16, 16, 16, 16, 8]

    btn_seg = la[:12]
    legal_btns = [i for i in range(12) if btn_seg[i] == 1]
    btn = np.random.choice(legal_btns) if legal_btns else 2

    act = [btn, 0, 0, 0, 0, 0]
    offset = 12
    for j in range(1, 5):
        seg = la[offset:offset + shapes[j]]
        legal_vals = [k for k in range(shapes[j]) if seg[k] == 1]
        act[j] = np.random.choice(legal_vals) if legal_vals else 0
        offset += shapes[j]

    target_start = 12 + sum(shapes[1:5])
    target_row_start = target_start + btn * shapes[5]
    seg = la[target_row_start:target_row_start + shapes[5]]
    legal_targets = [k for k in range(shapes[5]) if seg[k] == 1]
    act[5] = np.random.choice(legal_targets) if legal_targets else 0

    obs, r, d, info = env.step([tuple(act), (0,0,0,0,0,0)])
    pb = info[0]["req_pb"]
    hp = ",".join(str(getattr(h, 'hp', '?')) for h in pb.hero_list)
    print(f"  Step {step}: hp=[{hp}]", flush=True)
    if d[0]:
        print("GAMEOVER!", flush=True)
        break

env.close_game()
print("DONE 10 steps OK!", flush=True)

import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")
for d in ["ai_config/ai_server/skill_type", "ai_config/5v5/tactics/feature", "ai_config/5v5/common", "ai_config/ai_server/pb2struct"]:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)
files = {"ai_server_conf.json": '{"game_mode":"1v1"}', "transfer_table.json": "{}", "ai_config/AiMgr.txt": "skill 0 1 2", "ai_config/ai_server/skill_type/2": "0", "ai_config/ai_server/rl_config_file.txt": "", "ai_config/ai_server/pb2struct/pb2struct_config_server.txt": "", "ai_config/5v5/tactics/feature/skill_state_description_config.txt": "", "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt": "", "ai_config/5v5/common/skill_manager_config.txt": "", "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat": "", "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt": ""}
for p, c in files.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
import numpy as np

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000, default_hero_config=get_default_hero_config(), max_frame_num=300)
env = HoK1v1("test", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="172.24.50.71")
print("Reset...", flush=True)
obs, r, d, info = env.reset({"mode":"1v1","heroes":[[{"hero_id":199}],[{"hero_id":199}]]}, use_common_ai=[False,True], eval=True)
print(f"Reset OK! obs shape: {obs[0].shape}", flush=True)
la = info[0]["legal_action"]
print(f"legal_action shape: {la.shape}, dtype: {la.dtype}", flush=True)
print(f"legal_action[:20]: {la[:20]}", flush=True)
print(f"legal_action[70:84]: {la[70:84]}", flush=True)
print(f"Action space: {env.action_space()}", flush=True)
print(f"Sum legal: {sum(la)}", flush=True)

shapes = env.action_space()  # [12, 16, 16, 16, 16, 8]
for step in range(10):
    la = info[0]["legal_action"]
    button_seg = la[:12]
    legal_buttons = [i for i in range(12) if button_seg[i] == 1]
    btn = np.random.choice(legal_buttons) if legal_buttons else 0
    act = [btn, 0, 0, 0, 0, 0]
    offset = 12
    for j in range(1, 5):
        seg = la[offset:offset + shapes[j]]
        legal_vals = [k for k in range(shapes[j]) if seg[k] == 1]
        act[j] = np.random.choice(legal_vals) if legal_vals else 0
        offset += shapes[j]
    target_start = 12 + sum(shapes[1:5])
    target_row_start = target_start + btn * shapes[5]
    target_seg = la[target_row_start:target_row_start + shapes[5]]
    legal_targets = [k for k in range(shapes[5]) if target_seg[k] == 1]
    act[5] = np.random.choice(legal_targets) if legal_targets else 0
    actions = [tuple(act), (0,0,0,0,0,0)]
    print(f"Step {step}: action={actions[0]}", flush=True)
    obs, r, d, info = env.step(actions)
    pb = info[0]["req_pb"]
    hp = [str(getattr(h,'hp','?')) for h in pb.hero_list]
    print(f"  hp=[{','.join(hp)}] gameover={d[0]}", flush=True)
    if d[0]:
        break
env.close_game()
print("DONE!", flush=True)

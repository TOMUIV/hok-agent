import sys, os, time, re, argparse
sys.path.insert(0, "/workspace/src_v2")
sys.stdout.reconfigure(encoding='utf-8')

parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=10)
parser.add_argument("--print-every", type=int, default=1)
parser.add_argument("--hero-ai", type=int, default=199)
parser.add_argument("--hero-bot", type=int, default=169)
args = parser.parse_args()

HERO_AI = args.hero_ai
HERO_BOT = args.hero_bot
MAX_STEPS = args.steps
PRINT_EVERY = args.print_every

os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.24.50.71"

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")
for d in ["ai_config/ai_server/skill_type","ai_config/5v5/tactics/feature","ai_config/5v5/common","ai_config/ai_server/pb2struct"]:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)
ailab_files = {
    "ai_server_conf.json": '{"game_mode":"1v1"}', "transfer_table.json": "{}",
    "ai_config/AiMgr.txt": "skill 0 1 2", "ai_config/ai_server/skill_type/2": "0",
    "ai_config/ai_server/rl_config_file.txt": "",
    "ai_config/ai_server/pb2struct/pb2struct_config_server.txt": "",
    "ai_config/5v5/tactics/feature/skill_state_description_config.txt": "",
    "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt": "",
    "ai_config/5v5/common/skill_manager_config.txt": "",
    "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat": "",
    "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt": "",
}
for p, c in ailab_files.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

from dotenv import load_dotenv
load_dotenv("/workspace/.env")
from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
from hero_db import hero_name
from macro_agent import MacroAgent

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("macrov2", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="172.24.50.71")

CAMP = {"mode":"1v1","heroes":[[{"hero_id":HERO_AI}],[{"hero_id":HERO_BOT}]]}
print(f"{hero_name(HERO_AI)} vs {hero_name(HERO_BOT)}, max_steps={MAX_STEPS}", flush=True)
obs, r, d, info = env.reset(CAMP, use_common_ai=[False,True], eval=True)
print(f"Reset OK", flush=True)

agent = MacroAgent("v2", HERO_AI, HERO_BOT)

start = time.time()
step = 0
gameover = False

while not gameover and step < MAX_STEPS:
    s = info[0]
    pb = s["req_pb"]
    frame = getattr(pb, 'frame_no', 0)
    heroes = pb.hero_list
    self_h = enemy_h = None
    for h in heroes:
        if h.config_id == HERO_AI: self_h = h
        else: enemy_h = h
    if not self_h or not enemy_h: break

    action, raw = agent.decide(info)
    obs, r, d, info = env.step([action, (0,0,0,0,0,0)])
    elapsed = time.time() - start

    btn, mx, mz, skx, skz, tgt = action
    if step % PRINT_EVERY == 0:
        loc_s = f"({self_h.location.x:.0f},{self_h.location.y:.0f})" if self_h.location else "(?,?)"
        print(f"S{step:3d} Fr{frame:3d} [{elapsed:4.0f}s] {hero_name(HERO_AI)} HP:{getattr(self_h,'hp',0)}/{getattr(self_h,'max_hp',0)} "
              f"{hero_name(HERO_BOT)} HP:{getattr(enemy_h,'hp',0)}/{getattr(enemy_h,'max_hp',0)} "
              f"Gold:{getattr(self_h,'money',0)} @{loc_s}", flush=True)
        print(f"  action:({mx},{mz}) btn={btn}", flush=True)
        print(f"  {raw[:120]}", flush=True)

    gameover = d[0]
    step += 1

env.close_game()
print(f"\nDONE. {step} steps in {time.time()-start:.0f}s", flush=True)

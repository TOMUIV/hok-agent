import os, sys
sys.stdout.reconfigure(encoding='utf-8')

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")

dirs = [
    "ai_config/ai_server/skill_type",
    "ai_config/5v5/tactics/feature",
    "ai_config/5v5/common",
    "ai_config/ai_server/pb2struct",
]
for d in dirs:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)

files = {
    "ai_server_conf.json": '{"game_mode":"1v1"}',
    "transfer_table.json": "{}",
    "ai_config/AiMgr.txt": "skill 0 1 2",
    "ai_config/ai_server/skill_type/2": "0",
    "ai_config/ai_server/rl_config_file.txt": "",
    "ai_config/ai_server/pb2struct/pb2struct_config_server.txt": "",
    "ai_config/5v5/tactics/feature/skill_state_description_config.txt": "",
    "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt": "",
    "ai_config/5v5/common/skill_manager_config.txt": "",
    "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat": "",
    "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt": "",
}

for p, c in files.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

print(f"AILab ready at {ailab}")
for r, d, fs in os.walk(ailab):
    for fn in sorted(fs):
        fp = os.path.join(r, fn)
        sz = os.path.getsize(fp)
        print(f"  {fp[len(ailab)+1:]:65s} {sz:>4d}B")

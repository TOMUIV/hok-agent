import json, os

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")

dirs = [
    "ai_config/ai_server/skill_type",
    "ai_config/ai_server/pb2struct",
    "ai_config/5v5/tactics/feature",
    "ai_config/5v5/common",
    "ai_config/5v5/learn_skill",
    "ai_config/5v5/buy_equipment",
    "ai_config/5v5/reward",
]
for d in dirs:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)

files = {}
files["ai_server_conf.json"] = json.dumps({
    "game_mode": "1v1",
    "model_path": ".",
    "ai_config_dir": "./AILab/ai_config",
    "rl_config_file": "./AILab/ai_config/ai_server/rl_config_file.txt",
    "transfer_table": "./AILab/transfer_table.json",
    "skill_type_path": "./AILab/ai_config/ai_server/skill_type",
    "version": 1,
    "heroes": [{"hero_id": 199, "name": "gongsunli"}],
}, ensure_ascii=False)
files["transfer_table.json"] = "{}"
files["ai_config/AiMgr.txt"] = "default"

for p, c in files.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

# Create all empty stub files
stubs = [
    "ai_config/ai_server/skill_type/2",
    "ai_config/ai_server/rl_config_file.txt",
    "ai_config/ai_server/pb2struct/pb2struct_config_server.txt",
    "ai_config/5v5/tactics/feature/skill_state_description_config.txt",
    "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt",
    "ai_config/5v5/common/skill_manager_config.txt",
    "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat",
    "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt",
    "ai_config/5v5/learn_skill/game_ai_learn_skill_config.txt",
    "ai_config/5v5/buy_equipment/damage_type_config.txt",
    "ai_config/5v5/buy_equipment/eqpt_counter_hero.txt",
    "ai_config/5v5/buy_equipment/eqpt_price.txt",
    "ai_config/5v5/buy_equipment/equip_label.txt",
    "ai_config/5v5/buy_equipment/equip_sell_price.txt",
    "ai_config/5v5/buy_equipment/game_ai_buy_eqpt_config.txt",
    "ai_config/5v5/buy_equipment/hero_change_eqpt_config.txt",
    "ai_config/5v5/buy_equipment/sub_eqpt_config.txt",
    "ai_config/5v5/common/bush_index_info_1000.txt",
    "ai_config/5v5/common/bush_index_info_4000.txt",
    "ai_config/5v5/common/game_map_index_info_1000.txt",
    "ai_config/5v5/common/map_info.txt",
    "ai_config/5v5/common/obstacle_index_info_1000.txt",
    "ai_config/5v5/common/obstacle_index_info_4000.txt",
    "ai_config/5v5/common/skill_ep_consume.txt",
    "ai_config/5v5/common/skill_hurt_info.txt",
    "ai_config/5v5/common/skill_prm_config_file.txt",
    "ai_config/5v5/common/skill_render_effect_config_file.txt",
    "ai_config/5v5/game_ai_model_config.txt",
    "ai_config/5v5/reward/reward_config_file.txt",
    "ai_config/5v5/reward/rl_config_file.txt",
    "ai_config/5v5/tactics/feature/all_hero_config_dict.txt",
    "ai_config/5v5/tactics/feature/all_hero_state_add_config.txt",
    "ai_config/5v5/tactics/feature/all_hero_state_add_config_v2_minimap.txt",
    "ai_config/5v5/tactics/feature/buff_marks_config_dict.txt",
    "ai_config/5v5/tactics/feature/equipment_config_id.txt",
    "ai_config/5v5/tactics/feature/feature_config_5v5_tuanzhan_two_hand_action_new_img_minimap.txt",
    "ai_config/5v5/tactics/feature/hero_buff.txt",
    "ai_config/5v5/tactics/feature/hero_main_job_v2.txt",
    "ai_config/5v5/tactics/feature/soldier_buff_marks_config_dict.txt",
    "ai_config/5v5/tactics/feature/vec_feature_global.txt",
    "ai_config/5v5/tactics/feature/vec_feature_monster.txt",
    "ai_config/5v5/tactics/feature/vec_feature_organ.txt",
    "ai_config/5v5/tactics/feature/vec_soldier_config.txt",
    "ai_config/5v5/tactics/label_skill_type_config_file_two_hand_action.txt",
    "ai_config/5v5/tactics/multi_task_model_config_file.txt",
    "ai_config/5v5/tactics/random_attribute.txt",
    "ai_config/ai_server/pb2struct/bush.txt",
    "ai_config/ai_server/pb2struct/hero_ep_type.txt",
    "ai_config/ai_server/pb2struct/hero_main_job.txt",
]
for stub in stubs:
    path = os.path.join(ailab, stub)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("")

print(f"AILab ready at {ailab}")
print(f"Files: {len(os.listdir(ailab))} items in root, {len(stubs)} stubs")

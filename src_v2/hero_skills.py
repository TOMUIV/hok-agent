HERO_ROLES = {
    106: "法师(消耗)", 107: "战士(突进)", 108: "法师(控制)",
    111: "射手(爆发)", 112: "射手(站桩)", 117: "战士(控制)",
    119: "法师(治疗)", 120: "坦克(控制)", 121: "法师(持续)",
    123: "战士(真伤)", 128: "战士(续航)", 130: "战士(爆发)",
    131: "刺客(爆发)", 132: "射手(灵活)", 133: "射手(消耗)",
    135: "坦克(控制)", 140: "战士(冲锋)", 141: "法师(灵活)",
    146: "刺客(灵活)", 150: "刺客(灵活)", 152: "法师(控制)",
    154: "战士(双形态)", 155: "射手(灵活)", 157: "法师(爆发)",
    163: "战士(爆发)", 167: "刺客(爆发)", 169: "射手(站桩)",
    173: "射手(灵活)", 174: "射手(自保)", 175: "法师(控制)",
    176: "法师(辅助)", 182: "法师(爆发)", 189: "辅助(控制)",
    190: "法师(爆发)", 192: "射手(站桩)", 193: "战士(爆发)",
    194: "坦克(控制)", 196: "射手(狙击)", 199: "射手(灵活)",
    502: "刺客(双形态)", 510: "战士(开团)", 513: "刺客(法术)",
    522: "辅助(附身)",
}

HERO_SKILL_CONFIG = {
    132: {
        "name": "马可波罗",
        "role": "射手(灵活)",
        "poke_skill": 1,
        "combo_priority": [3, 1, 2],
        "escape_skill": 2,
        "engage_skill": 2,
        "skill_ranges": {1: 900, 2: 400, 3: 550, 4: 0},
        "skill_types": {1: "projectile", 2: "dash", 3: "aoe_self", 4: "none"},
        "skill_descs": {1: "华丽左轮: 向指定方向连续射击，移速不降", 2: "漫游之枪: 短距翻滚位移，附近有敌人加攻速", 3: "狂热弹幕: 旋转射击周围敌人，触发真伤"},
        "skill4_available": False,
        "items": ["急速战靴", "末世", "纯净苍穹", "破晓", "不祥征兆", "魔女斗篷"],
    },
    169: {
        "name": "后羿",
        "role": "射手(站桩)",
        "poke_skill": 2,
        "combo_priority": [2, 1],
        "escape_skill": None,
        "engage_skill": None,
        "skill_ranges": {1: 800, 2: 700, 3: 1000, 4: 0},
        "skill_types": {1: "self_buff", 2: "aoe_target", 3: "projectile", 4: "none"},
        "skill_descs": {1: "多重箭矢: 强化普攻,同时射3箭", 2: "落日余晖: 对目标区域造成减速+伤害", 3: "灼日之矢: 全图飞行物,命中眩晕,距离越久眩晕越久"},
        "skill4_available": False,
        "items": ["急速战靴", "闪电匕首", "无尽战刃", "破晓", "逐日之弓", "贤者的庇护"],
    },
    199: {
        "name": "公孙离",
        "role": "射手(灵活)",
        "poke_skill": 1,
        "combo_priority": [2, 1, 3],
        "escape_skill": 2,
        "engage_skill": 1,
        "skill_ranges": {1: 800, 2: 700, 3: 650, 4: 0},
        "skill_types": {1: "dash", 2: "self_buff", 3: "projectile", 4: "none"},
        "skill_descs": {1: "岑中归月: 向指定方向突进,留下伞,可返回", 2: "霜叶舞: 旋转格挡飞行物,击落周围飞行道具", 3: "孤鹜断霞: 击退前方敌人,造成伤害"},
        "skill4_available": False,
        "items": ["急速战靴", "末世", "无尽战刃", "破晓", "逐日之弓", "魔女斗篷"],
    },
    141: {
        "name": "貂蝉",
        "role": "法师(灵活)",
        "poke_skill": 1,
        "combo_priority": [3, 2, 1],
        "escape_skill": 2,
        "engage_skill": 2,
        "skill_ranges": {1: 700, 2: 500, 3: 600, 4: 0},
        "skill_types": {1: "projectile", 2: "dash", 3: "aoe_self", 4: "none"},
        "skill_descs": {1: "落·红雨: 扔出花球造成伤害并减速", 2: "缘·心结: 位移到指定位置,规避伤害", 3: "绽·风华: 原地展开法阵,造成大量范围伤害"},
        "skill4_available": False,
        "items": ["冷静之靴", "圣杯", "噬神之书", "博学者之怒", "虚无法杖", "辉月"],
    },
    107: {
        "name": "赵云",
        "role": "战士(突进)",
        "poke_skill": 1,
        "combo_priority": [3, 1, 2],
        "escape_skill": 2,
        "engage_skill": 3,
        "skill_ranges": {1: 500, 2: 600, 3: 600, 4: 0},
        "skill_types": {1: "projectile", 2: "dash", 3: "aoe_target", 4: "none"},
        "skill_descs": {1: "惊雷之龙: 向前刺出,造成伤害并减速", 2: "破云之龙: 连续刺击,回复生命", 3: "天翔之龙: 跃向目标造成击飞,开启团战"},
        "skill4_available": False,
        "items": ["抵抗之靴", "暗影战斧", "宗师之力", "破军", "名刀·司命", "暴烈之甲"],
    },
}

ITEM_DB = {
    "急速战靴": {"cost": 710, "category": "boots", "stat": "攻速+25%"},
    "抵抗之靴": {"cost": 710, "category": "boots", "stat": "韧性+35%"},
    "冷静之靴": {"cost": 710, "category": "boots", "stat": "冷却+15%"},
    "末世": {"cost": 2160, "category": "damage", "stat": "攻速+30%, 物攻+60"},
    "无尽战刃": {"cost": 2140, "category": "damage", "stat": "物攻+130, 暴击+20%"},
    "破晓": {"cost": 3400, "category": "damage", "stat": "物攻+50, 攻速+35%, 破甲+40%"},
    "闪电匕首": {"cost": 1840, "category": "damage", "stat": "攻速+35%, 暴击+15%"},
    "暗影战斧": {"cost": 2090, "category": "damage", "stat": "物攻+85, 冷却+15%, 破甲"},
    "宗师之力": {"cost": 2100, "category": "damage", "stat": "物攻+60, 暴击+20%"},
    "破军": {"cost": 2950, "category": "damage", "stat": "物攻+180"},
    "纯净苍穹": {"cost": 2120, "category": "defense", "stat": "攻速+30%, 减伤主动"},
    "不祥征兆": {"cost": 2180, "category": "defense", "stat": "物防+270, 生命+1200"},
    "魔女斗篷": {"cost": 2120, "category": "defense", "stat": "法防+320, 护盾"},
    "暴烈之甲": {"cost": 1950, "category": "defense", "stat": "物防+220, 生命+1000"},
    "名刀·司命": {"cost": 1900, "category": "defense", "stat": "物攻+60, 免疫致命伤"},
    "逐日之弓": {"cost": 2100, "category": "damage", "stat": "攻速+25%, 射程增加主动"},
    "贤者的庇护": {"cost": 2080, "category": "defense", "stat": "复活甲"},
    "圣杯": {"cost": 1800, "category": "mana", "stat": "法强+180, 回蓝"},
    "噬神之书": {"cost": 2090, "category": "sustain", "stat": "法强+180, 法术吸血+25%"},
    "博学者之怒": {"cost": 2300, "category": "damage", "stat": "法强+240, 被动+35%法强"},
    "虚无法杖": {"cost": 2110, "category": "damage", "stat": "法强+240, 法穿+45%"},
    "辉月": {"cost": 1990, "category": "defense", "stat": "法强+160, 无敌主动"},
    "破军": {"cost": 2950, "category": "damage", "stat": "物攻+180"},
}

GOLD_PER_MINION = 50
GOLD_PER_KILL = 300
GOLD_PASSIVE_PER_5S = 20

def get_config(hero_id):
    return HERO_SKILL_CONFIG.get(hero_id)

def get_item_cost(item_name):
    info = ITEM_DB.get(item_name)
    return info["cost"] if info else 9999

def next_item(hero_id, current_gold, owned_items):
    config = get_config(hero_id)
    if not config:
        return None
    for item in config["items"]:
        if item not in owned_items:
            cost = get_item_cost(item)
            if current_gold >= cost:
                return item
    return None

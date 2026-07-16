SKILL_DB = {
    "matchup": {
        "199_vs_169": {
            "summary": "公孙离 vs 后羿 — 灵活射手 vs 站桩射手",
            "advantage": "公孙离, 前4级利用位移换血优势",
            "danger": "后羿3技能全图箭可眩晕3秒, 残血别走河道中线",
            "tip_offense": "用2技能格挡后羿大招和2技能, 1技能突进贴脸, 3技能击退打断他站桩",
            "tip_defense": "保持移动不要站撸, 后羿被动叠满后伤害翻倍",
            "power_spike": "公孙离4级(有大招)和末世出完后是强势期",
            "key_skill": "Skill2 霜叶舞: 格挡所有飞行物, 包括后羿大招",
        },
        "132_vs_169": {
            "summary": "马可波罗 vs 后羿 — 灵活真伤 vs 站桩",
            "advantage": "马可波罗, 1技能远程消耗",
            "danger": "马可波罗大招怕打断, 后羿大招可打断",
            "tip_offense": "1技能叠被动, 满10层触发真伤后接大招",
            "tip_defense": "2技能留作躲后羿大招, 别轻易交",
            "power_spike": "末世出来后真伤爆发期",
            "key_skill": "Skill1 华丽左轮: 远程叠被动, 保持距离",
        },
    },
    "combo": {
        "199": {
            "all_in": "Skill2(格挡箭矢)→Skill1(突进贴脸)→普攻→Skill3(击退收割)",
            "poke": "Skill1(突进扔伞)→普攻→Skill1(返回安全位置)",
            "escape": "Skill2(格挡)→向塔方向走→Skill1(突进回塔)",
            "pursue": "Skill1(突进追)→普攻→Skill2(挡回头箭)→普攻",
        },
        "169": {
            "all_in": "Skill2(范围减速)→Skill1(加速射3箭)→站桩普攻",
            "poke": "Skill2(范围消耗)→后撤",
            "escape": "无位移技能, 只能走位+闪",
            "pursue": "无突进, 只靠走A追击",
        },
        "132": {
            "all_in": "Skill1(远程叠被动)→Skill2(位移近身)→Skill3(转大招)",
            "poke": "Skill1(远程消耗)保持距离",
            "escape": "Skill2(翻滚位移)撤出战场",
            "pursue": "Skill2(翻滚追)→Skill1(继续叠被动)",
        },
    },
    "wave": {
        "freeze": "只补最后一刀, 让兵线停在自己塔前. 适合劣势时安全发育",
        "push": "快速清兵让己方兵线进塔. 适合优势时磨塔或回城后快速回线",
        "slow_push": "只清远程兵, 让己方兵线慢慢积累优势. 适合游走前",
        "last_hit": "等小兵残血再攻击, 获得全额金币和经验",
    },
    "item_timing": {
        "射手": {
            "core": "鞋子+末世/无尽为两大件强势期",
            "tip": "先出鞋子游走/躲技能, 再出核心输出装",
        },
        "法师": {
            "core": "鞋子+圣杯/回响为两大件强势期",
            "tip": "圣杯提供续航, 适合持续消耗型法师",
        },
        "战士": {
            "core": "鞋子+暗影战斧为第一大件",
            "tip": "暗影战斧提供穿透和冷却, 前期性价比最高",
        },
    },
    "positioning": {
        "vs_ranged": "保持在自己远程兵附近, 敌方点你时小兵会反击",
        "under_tower": "塔的攻击范围约X±2500, 站在塔边缘安全区",
        "bush_check": "怀疑草丛有人时用Skill1探草或走位引诱",
        "kite_path": "沿着X轴直线撤退比Z轴更安全, 方便塔下支援",
    },
    "game_mechanics": {
        "tower_aggro": "塔优先攻击攻击己方英雄的敌方单位. 塔下点人时走出塔范围重置仇恨",
        "minion_timing": "兵线每25秒一波, 第1波在开局约15秒到达中线",
        "heal": "治疗术回复自身+附近队友HP, 同时加速2秒",
        "flash": "闪现向指定方向瞬移一段距离. CD120秒",
        "recall": "回城引导4秒, 被打断需重新开始",
        "gold": "远程兵40, 近战兵60, 炮车120. 补刀得全额, 未补刀得40%",
    },
}

def get_skill(hero_id, skill_key="all_in"):
    return SKILL_DB.get("combo", {}).get(str(hero_id), {}).get(skill_key, "")

def get_matchup(self_id, enemy_id):
    key = f"{self_id}_vs_{enemy_id}"
    return SKILL_DB.get("matchup", {}).get(key, {})

def get_wave(technique="freeze"):
    return SKILL_DB.get("wave", {}).get(technique, "")

def get_positioning(topic="under_tower"):
    return SKILL_DB.get("positioning", {}).get(topic, "")

def get_mechanics(topic="tower_aggro"):
    return SKILL_DB.get("game_mechanics", {}).get(topic, "")

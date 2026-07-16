import random, math, copy
import numpy as np

GOLD_PER_FRAME = 2.0
EXP_PER_FRAME = 1.0
MINION_WAVE_INTERVAL = 30
MAX_FRAMES = 5000
PHYSICS_FACTOR = 602.0

LEVEL_EXP_TABLE = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500, 6600, 7800, 9100, 10500]

HERO_TEMPLATES = {
    132: {"name": "马可波罗", "hp": 3500, "ep": 200, "phy_atk": 180, "mgc_atk": 0, "phy_def": 100, "mgc_def": 50,
          "mov_spd": 370, "atk_spd": 1.0, "atk_range": 650, "crit_rate": 0, "hp5": 30, "ep5": 15,
          "skills": ["101:华丽左轮:80:8:physical:短:向指定方向连续射击", "102:漫游之枪:60:12:physical:长:向指定方向位移并射击",
                     "103:狂热弹幕:100:40:physical:长:向周围发射多枚弹幕"]},
    169: {"name": "后羿", "hp": 3200, "ep": 0, "phy_atk": 190, "mgc_atk": 0, "phy_def": 85, "mgc_def": 50,
          "mov_spd": 360, "atk_spd": 0.9, "atk_range": 700, "crit_rate": 0, "hp5": 35, "ep5": 0,
          "skills": ["201:多重箭矢:60:5:physical:短:强化普攻射三支箭", "202:落日余晖:50:10:physical:长:对扇形区域造成伤害和减速",
                     "203:惩戒射击:120:35:physical:长:向前方射出火焰箭造成眩晕"]},
    141: {"name": "貂蝉", "hp": 3000, "ep": 350, "phy_atk": 160, "mgc_atk": 210, "phy_def": 80, "mgc_def": 65,
          "mov_spd": 380, "atk_spd": 1.1, "atk_range": 600, "crit_rate": 0, "hp5": 30, "ep5": 20,
          "skills": ["301:落·红雨:70:5:magic:短:向前方发出花球造成伤害", "302:缘·心结:50:10:magic:短:位移并释放三枚法球",
                     "303:绽·风华:90:35:magic:短:展开法阵持续造成范围伤害"]},
    107: {"name": "赵云", "hp": 3800, "ep": 0, "phy_atk": 185, "mgc_atk": 0, "phy_def": 140, "mgc_def": 80,
          "mov_spd": 380, "atk_spd": 0.85, "atk_range": 550, "crit_rate": 0, "hp5": 40, "ep5": 0,
          "skills": ["401:破云之枪:55:6:physical:短:造成两次物理伤害", "402:破云之龙:50:10:physical:短:连续刺击造成物理伤害并减速",
                     "403:天翔之龙:120:36:physical:长:跃向目标造成高额物理伤害"]},
    199: {"name": "公孙离", "hp": 3100, "ep": 0, "phy_atk": 175, "mgc_atk": 0, "phy_def": 90, "mgc_def": 50,
          "mov_spd": 390, "atk_spd": 1.1, "atk_range": 675, "crit_rate": 0, "hp5": 30, "ep5": 0,
          "skills": ["501:岑中归月:70:9:physical:短:位移并造成物理伤害", "502:霜叶舞:60:11:physical:短:旋转纸伞造成范围伤害",
                     "503:孤鹜断霞:120:40:physical:长:击退前方敌人并造成伤害"]},
}

MAP_X_MIN = -40000
MAP_X_MAX = 40000
MAP_Z_MIN = -40000
MAP_Z_MAX = 40000

MAP_ORGANS = {
    "blue": [
        {"ConfigID": 106, "SubType": 24, "Camp": 0, "x": -19780, "z": -19780, "MaxHp": 7000, "name": "蓝方水晶"},
        {"ConfigID": 42,  "SubType": 23, "Camp": 0, "x": -27000, "z": -27000, "MaxHp": 6000, "name": "蓝方二塔"},
        {"ConfigID": 1,   "SubType": 21, "Camp": 0, "x": -11240, "z": -11228, "MaxHp": 5000, "name": "蓝方一塔"},
    ],
    "red": [
        {"ConfigID": 107, "SubType": 24, "Camp": 1, "x": 19820, "z": 19820, "MaxHp": 7000, "name": "红方水晶"},
        {"ConfigID": 43,  "SubType": 23, "Camp": 1, "x": 27000, "z": 27000, "MaxHp": 6000, "name": "红方二塔"},
        {"ConfigID": 2,   "SubType": 21, "Camp": 1, "x": 11285, "z": 11275, "MaxHp": 5000, "name": "红方一塔"},
    ]
}

BLUE_CRYSTAL_POS = (-19780, -19780)
RED_CRYSTAL_POS = (19820, 19820)
LANE_BLUE_BASE = BLUE_CRYSTAL_POS
LANE_RED_BASE = RED_CRYSTAL_POS

EQUIPMENT_DB = [
    {"id": 1, "name": "铁剑", "price": 250, "phy_atk": 20, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0},
    {"id": 2, "name": "匕首", "price": 290, "phy_atk": 0, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0.1},
    {"id": 3, "name": "布甲", "price": 220, "phy_atk": 0, "mgc_atk": 0, "phy_def": 90, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0},
    {"id": 4, "name": "抵抗之靴", "price": 710, "phy_atk": 0, "mgc_atk": 0, "phy_def": 110, "mgc_def": 110, "max_hp": 0, "crit": 0, "atk_spd": 0},
    {"id": 5, "name": "无尽战刃", "price": 2140, "phy_atk": 130, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0.25, "atk_spd": 0},
    {"id": 6, "name": "破晓", "price": 3400, "phy_atk": 100, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0.15, "atk_spd": 0.35},
    {"id": 7, "name": "破军", "price": 2950, "phy_atk": 200, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0},
    {"id": 8, "name": "贤者之书", "price": 2990, "phy_atk": 0, "mgc_atk": 400, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0},
    {"id": 9, "name": "不祥征兆", "price": 2180, "phy_atk": 0, "mgc_atk": 0, "phy_def": 270, "mgc_def": 0, "max_hp": 1200, "crit": 0, "atk_spd": 0},
    {"id": 10, "name": "魔女斗篷", "price": 2120, "phy_atk": 0, "mgc_atk": 0, "phy_def": 0, "mgc_def": 360, "max_hp": 1000, "crit": 0, "atk_spd": 0},
    {"id": 11, "name": "吸血之镰", "price": 410, "phy_atk": 10, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0},
    {"id": 12, "name": "雷鸣刃", "price": 450, "phy_atk": 40, "mgc_atk": 0, "phy_def": 0, "mgc_def": 0, "max_hp": 0, "crit": 0, "atk_spd": 0},
]

class Vec3:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = float(x), float(y), float(z)

class MockSkill:
    def __init__(self, skill_def: str, button_idx: int):
        parts = skill_def.split(":")
        self.id = int(parts[0])
        self.name = parts[1]
        self.damage = int(parts[2])
        self.max_cooldown = int(parts[3])
        self.cooldown_remaining = 0
        self.damage_type = parts[4]
        self.range_desc = parts[5]
        self.description = parts[6]
        self.level = 0
        self.max_level = 6 if button_idx in [4, 5] else 3
        self.button_idx = button_idx

class MockEquipment:
    def __init__(self, eqp_def):
        self.id = eqp_def["id"]
        self.name = eqp_def["name"]
        self.price = eqp_def["price"]
        self.phy_atk = eqp_def["phy_atk"]
        self.mgc_atk = eqp_def["mgc_atk"]
        self.phy_def = eqp_def["phy_def"]
        self.mgc_def = eqp_def["mgc_def"]
        self.max_hp_bonus = eqp_def["max_hp"]
        self.crit = eqp_def["crit"]
        self.atk_spd = eqp_def["atk_spd"]

class MockHero:
    def __init__(self, config_id, camp, runtime_id, template):
        self.config_id = config_id
        self.camp = camp
        self.runtime_id = runtime_id
        self.template = template
        self._reset()

    def _reset(self):
        t = self.template
        self.hp = t["hp"]
        self.max_hp = t["hp"]
        self.ep = t["ep"]
        self.max_ep = t["ep"]
        self.level = 1
        self.exp = 0.0
        self.money = 300.0
        self.base_phy_atk = t["phy_atk"]
        self.base_mgc_atk = t["mgc_atk"]
        self.phy_def = t["phy_def"]
        self.mgc_def = t["mgc_def"]
        self.mov_spd = t["mov_spd"]
        self.base_atk_spd = t["atk_spd"]
        self.atk_range = t["atk_range"]
        self.crit_rate = t["crit_rate"]
        self.hp5 = t["hp5"]
        self.ep5 = t["ep5"]
        self.killCnt = 0
        self.deadCnt = 0
        self.assistCnt = 0
        self.totalHurtToHero = 0.0
        self.totalBeHurtByHero = 0.0
        self.location = Vec3(0, 0, 0)
        self.last_attack_frame = -999
        self.alive = True
        self.skills = []
        for i, sd in enumerate(t["skills"]):
            btn = 4 + i
            self.skills.append(MockSkill(sd, btn))
        for sk in self.skills:
            if sk.button_idx in [4, 5]:
                sk.level = 1
        self.equipment = []
        self.auto_attack_cooldown = max(1, int(10 / max(t["atk_spd"], 0.1)))
        self.attack_cooldown_counter = 0
        self.camp_visible = [True, False] if self.camp == 0 else [False, True]
        self.behav_mode = 0
        self.ai_controlled = False

    @property
    def phy_atk(self):
        return self.base_phy_atk + sum(e.phy_atk for e in self.equipment)

    @property
    def mgc_atk(self):
        return self.base_mgc_atk + sum(e.mgc_atk for e in self.equipment)

    @property
    def atk_spd(self):
        return self.base_atk_spd + sum(e.atk_spd for e in self.equipment)

    @property
    def effective_max_hp(self):
        return self.max_hp + sum(e.max_hp_bonus for e in self.equipment)

    @property
    def effective_phy_def(self):
        return self.phy_def + sum(e.phy_def for e in self.equipment)

    @property
    def effective_mgc_def(self):
        return self.mgc_def + sum(e.mgc_def for e in self.equipment)

    @property
    def effective_crit(self):
        return self.crit_rate + sum(e.crit for e in self.equipment)

    def distance_to(self, other):
        if hasattr(other, 'location') and other.location:
            ox = other.location.x
            oz = other.location.z
        elif hasattr(other, 'x'):
            ox = other.x
            oz = other.z
        else:
            return 99999
        dx = self.location.x - ox
        dz = self.location.z - oz
        return math.sqrt(dx*dx + dz*dz)

    def calculate_phy_damage(self, raw_dmg, target_phy_def):
        reduction = target_phy_def / (target_phy_def + PHYSICS_FACTOR)
        return raw_dmg * (1 - reduction)

    def calculate_mgc_damage(self, raw_dmg, target_mgc_def):
        reduction = target_mgc_def / (target_mgc_def + PHYSICS_FACTOR)
        return raw_dmg * (1 - reduction)

    def add_equipment(self, eqp_id):
        if len(self.equipment) >= 6:
            return False
        eqp_def = next((e for e in EQUIPMENT_DB if e["id"] == eqp_id), None)
        if not eqp_def or self.money < eqp_def["price"]:
            return False
        self.money -= eqp_def["price"]
        self.equipment.append(MockEquipment(eqp_def))
        return True

    def sell_equipment(self, index):
        if index < 0 or index >= len(self.equipment):
            return False
        eqp = self.equipment[index]
        self.money += eqp.price * 0.5
        self.equipment.pop(index)
        return True

    def level_up(self):
        if self.level >= 15:
            return False
        self.level += 1
        self.max_hp += 150
        self.hp = min(self.hp + 150, self.max_hp)
        self.phy_def += 5
        self.mgc_def += 3
        self.base_phy_atk += 8
        for skill in self.skills:
            if skill.level < skill.max_level:
                if skill.button_idx in [4, 5]:
                    if self.level >= 1:
                        skill.level += 1
                        break
                elif skill.button_idx == 6:
                    if self.level >= 4 and self.level % 3 == 1:
                        skill.level += 1
                        break
        for skill in self.skills:
            if skill.button_idx == 6 and self.level >= 4:
                max_ult_level = min(3, 1 + (self.level - 4) // 3)
                if skill.level < max_ult_level:
                    skill.level = max_ult_level
            elif skill.button_idx in [4, 5]:
                max_skill_level = min(6, 1 + self.level // 2)
                if skill.level < max_skill_level:
                    skill.level = max_skill_level
        return True

    def skill_by_button(self, btn_idx):
        for skill in self.skills:
            if skill.button_idx == btn_idx:
                return skill
        return None

class MockOrgan:
    def __init__(self, defn):
        self.ConfigID = defn["ConfigID"]
        self.SubType = defn["SubType"]
        self.Camp = defn["Camp"]
        self.x = defn["x"]
        self.z = defn["z"]
        self.MaxHp = defn["MaxHp"]
        self.Hp = defn["MaxHp"]
        self.RuntimeID = defn["ConfigID"]
        self.name = defn["name"]
        self.alive = True

class MockSoldier:
    def __init__(self, camp, sid, pos, melee=True):
        self.config_id = 100 + camp * 10 + (0 if melee else 1)
        self.camp = camp
        self.runtime_id = sid
        self.hp = 1800 if melee else 1200
        self.max_hp = 1800 if melee else 1200
        self.phy_atk = 80 if melee else 100
        self.phy_def = 50 if melee else 30
        self.location = Vec3(pos[0], 0, pos[1])
        self.alive = True
        self.melee = melee
        self.atk_range = 30 if melee else 300
        self.target_pos = None
        self.attack_cooldown = 0
        self.max_attack_cooldown = 15

class MockMonster:
    def __init__(self, mid, camp, pos, hp, atk):
        self.config_id = 200 + mid
        self.camp = camp
        self.runtime_id = 1000 + mid
        self.hp = hp
        self.max_hp = hp
        self.phy_atk = atk
        self.location = Vec3(pos[0], 0, pos[1])
        self.alive = True
        self.atk_range = 50
        self.attack_cooldown = 0

class MockReqPb:
    def __init__(self):
        self.frame_no = 0
        self.gameover = False
        self.hero_list = []
        self.organ_list = []
        self.soldier_list = []
        self.monster_list = []

class MockEnvV2:
    OBS_SHAPE = [453]
    LABEL_SIZE_LIST = [12, 16, 16, 16, 16, 8]
    BUTTON_NAMES = [
        "None1", "None2", "Move", "Attack", "Skill1", "Skill2",
        "Skill3", "HealSkill", "ChosenSkill", "Recall", "Skill4", "EquipSkill"
    ]

    def __init__(self, hero_ids=None):
        if hero_ids is None:
            hero_ids = [132, 169]
        self.hero_ids = hero_ids
        self.frame_no = 0
        self.max_frames = MAX_FRAMES
        self.heroes = []
        self.organs = []
        self.soldiers = []
        self.monsters = []
        self.use_common_ai = []
        self.camp_hero_list = None
        self.minion_wave_counter = 0
        self.soldier_id_counter = 1000
        self.events = []
        self.ai_last_action = [0, 0, 0, 0, 0, 0]
        self.winner = -1

    def reset(self, camp_hero_list=None, use_common_ai=None):
        self.use_common_ai = use_common_ai if use_common_ai is not None else [False, True]
        self.camp_hero_list = camp_hero_list or [
            [{"hero_id": self.hero_ids[0], "skill_id": 80115}],
            [{"hero_id": self.hero_ids[1], "skill_id": 80115}],
        ]
        self.heroes = []
        for i, camp in enumerate(self.camp_hero_list):
            for j, hconf in enumerate(camp):
                hid = hconf["hero_id"]
                template = HERO_TEMPLATES.get(hid)
                if template is None:
                    template = {"name": f"Hero#{hid}", "hp": 3500, "ep": 200, "phy_atk": 170, "mgc_atk": 0,
                                "phy_def": 90, "mgc_def": 50, "mov_spd": 370, "atk_spd": 1.0, "atk_range": 600,
                                "crit_rate": 0, "hp5": 30, "ep5": 10,
                                "skills": ["0:普通攻击:50:0:physical:短:基础攻击", "1:基础技能:60:10:physical:短:基础技能",
                                          "2:终极技能:100:30:physical:长:终极技能"]}
                hero = MockHero(hid, i, i * 100 + j, template)
                self.heroes.append(hero)
        self.heroes[0].location = Vec3(-13000, 0, -13000)
        self.heroes[1].location = Vec3(13000, 0, 13000)
        self.heroes[0].camp_visible = [True, False]
        self.heroes[1].camp_visible = [False, True]
        self.heroes[0].ai_controlled = self.use_common_ai[0] if len(self.use_common_ai) > 0 else False
        if len(self.heroes) > 1:
            self.heroes[1].ai_controlled = self.use_common_ai[1] if len(self.use_common_ai) > 1 else True
        self.organs = []
        for side_key in ["blue", "red"]:
            for od in MAP_ORGANS[side_key]:
                self.organs.append(MockOrgan(od))
        self.soldiers = []
        self.monsters = []
        self._spawn_monsters()
        self.frame_no = 0
        self.minion_wave_counter = 0
        self.events = []
        self.ai_last_action = [0, 0, 0, 0, 0, 0]
        self.winner = -1
        return self._make_state()

    def _spawn_monsters(self):
        pass

    def _spawn_minion_wave(self):
        camp = self.frame_no // MINION_WAVE_INTERVAL % 2
        if camp == 0:
            base_x, base_z = -12000, -12000
        else:
            base_x, base_z = 12000, 12000
        for is_melee in [True, True, True, False, False]:
            sid = self.soldier_id_counter
            self.soldier_id_counter += 1
            pos = (base_x + random.randint(0, 200) + (0 if is_melee else 300),
                   base_z + random.randint(0, 200) + (0 if is_melee else 300))
            soldier = MockSoldier(camp, sid, pos, melee=is_melee)
            self.soldiers.append(soldier)

    def _make_button_mask(self):
        mask = np.zeros(12, dtype=np.float32)
        mask[2] = 1
        mask[3] = 1
        for i in [4, 5, 6]:
            skill = self.heroes[0].skill_by_button(i)
            if skill and skill.level > 0 and skill.cooldown_remaining <= 1:
                mask[i] = 1
        mask[9] = 1 if self.frame_no % 60 == 0 else 0
        mask[0] = mask[1] = 0
        if sum(mask) == 0:
            mask[2] = 1
        return mask

    def _calculate_auto_attack_damage(self, attacker, defender):
        dmg = attacker.phy_atk * (1.0 + random.uniform(-0.05, 0.05))
        if random.random() < attacker.effective_crit:
            dmg *= 2.0
        actual = attacker.calculate_phy_damage(dmg, defender.effective_phy_def)
        return max(1, actual)

    def _calculate_skill_damage(self, attacker, defender, skill):
        if skill.damage_type == "physical":
            dmg = skill.damage + attacker.phy_atk * 0.5
            actual = attacker.calculate_phy_damage(dmg, defender.effective_phy_def)
        else:
            dmg = skill.damage + attacker.mgc_atk * 0.6
            actual = attacker.calculate_mgc_damage(dmg, defender.effective_mgc_def)
        return max(1, actual)

    def _find_nearest_enemy_hero(self, hero):
        enemies = [h for h in self.heroes if h.camp != hero.camp and h.alive]
        if not enemies:
            return None
        return min(enemies, key=lambda h: hero.distance_to(h))

    def _find_nearest_enemy_organ(self, hero):
        enemies = [o for o in self.organs if o.Camp != hero.camp and o.alive]
        if not enemies:
            return None
        return min(enemies, key=lambda o: hero.distance_to(o))

    def _find_target_in_range(self, hero, range_val):
        enemies = [h for h in self.heroes if h.camp != hero.camp and h.alive]
        in_range = [h for h in enemies if hero.distance_to(h) <= range_val]
        if in_range:
            return min(in_range, key=lambda h: h.hp)
        organs = [o for o in self.organs if o.Camp != hero.camp and o.alive]
        in_range_o = [o for o in organs if hero.distance_to(o) <= range_val]
        if in_range_o:
            return min(in_range_o, key=lambda o: o.Hp)
        soldiers = [s for s in self.soldiers if s.camp != hero.camp and s.alive]
        in_range_s = [s for s in soldiers if hero.distance_to(s) <= range_val]
        if in_range_s:
            return min(in_range_s, key=lambda s: s.hp)
        return None

    def _execute_auto_attack(self, hero):
        target = self._find_target_in_range(hero, hero.atk_range)
        if not target:
            return None
        if isinstance(target, MockHero):
            dmg = self._calculate_auto_attack_damage(hero, target)
            target.hp -= dmg
            target.hp = max(0, target.hp)
            hero.totalHurtToHero += dmg
            target.totalBeHurtByHero += dmg
            hero.last_attack_frame = self.frame_no
            return {"type": "attack", "source": hero.config_id, "target": target.config_id,
                    "dmg": round(dmg, 0), "target_type": "hero"}
        elif isinstance(target, MockOrgan):
            dmg = hero.phy_atk
            target.Hp -= dmg
            target.Hp = max(0, target.Hp)
            hero.last_attack_frame = self.frame_no
            return {"type": "attack", "source": hero.config_id, "target": target.ConfigID,
                    "dmg": round(dmg, 0), "target_type": "tower"}
        elif isinstance(target, MockSoldier):
            dmg = hero.phy_atk
            target.hp -= dmg
            target.hp = max(0, target.hp)
            if target.hp <= 0:
                target.alive = False
                gold = 30 + 5 * self.frame_no // 60
                hero.money += min(gold, 60)
                hero.exp += 30
            hero.last_attack_frame = self.frame_no
            return {"type": "attack", "source": hero.config_id, "target": target.runtime_id,
                    "dmg": round(dmg, 0), "target_type": "soldier"}
        return None

    def _execute_skill(self, hero, skill_idx, target_val, skx, skz):
        skill = hero.skill_by_button(skill_idx)
        if not skill or skill.level <= 0 or skill.cooldown_remaining > 0:
            return None
        target = None
        if target_val == 1:
            target = self._find_nearest_enemy_hero(hero)
        if not target:
            return None
        if hero.distance_to(target) > 2000:
            return None
        dmg = self._calculate_skill_damage(hero, target, skill)
        target.hp -= dmg
        target.hp = max(0, target.hp)
        hero.totalHurtToHero += dmg
        target.totalBeHurtByHero += dmg
        skill.cooldown_remaining = skill.max_cooldown
        return {"type": "skill", "skill": skill.name, "source": hero.config_id,
                "target": target.config_id, "dmg": round(dmg, 0)}

    def _ai_step(self, hero):
        enemy = self._find_nearest_enemy_hero(hero)
        hp_pct = hero.hp / hero.effective_max_hp if hero.effective_max_hp > 0 else 0.5

        retreating = False
        if enemy and hp_pct < 0.35 and hero.distance_to(enemy) < hero.atk_range * 2:
            retreating = True
            if hero.camp == 0:
                tx, tz = -13000, -13000
            else:
                tx, tz = 13000, 13000
            dx = tx - hero.location.x
            dz = tz - hero.location.z
            norm = math.sqrt(dx*dx + dz*dz) or 1
            mx = max(1, min(15, int(8 + (dx/norm)*7)))
            mz = max(1, min(15, int(8 + (dz/norm)*7)))
            return (2, mx, mz, 1, 1, 1)

        if enemy:
            dist = hero.distance_to(enemy)
            if dist < hero.atk_range * 1.3:
                if hero.attack_cooldown_counter <= 0:
                    result = self._execute_auto_attack(hero)
                    if result:
                        self.events.append(result)
                    hero.attack_cooldown_counter = max(1, int(10 / max(hero.atk_spd, 0.1)))
                for skill in hero.skills:
                    if skill.level > 0 and skill.cooldown_remaining <= 0 and dist < 1200:
                        result = self._execute_skill(hero, skill.button_idx, 1, 8, 8)
                        if result:
                            self.events.append(result)
                        break
                strafe_angle = (self.frame_no * 3 + hash(hero.config_id) % 360) * 3.14159 / 180
                sx = math.cos(strafe_angle) * 200
                sz = math.sin(strafe_angle) * 200
                mx = max(1, min(15, int(8 + (enemy.location.x + sx - hero.location.x) / max(hero.distance_to(enemy), 1) * 7)))
                mz = max(1, min(15, int(8 + (enemy.location.z + sz - hero.location.z) / max(hero.distance_to(enemy), 1) * 7)))
                return (3, mx, mz, 1, 1, 1)
            elif dist < hero.atk_range * 3:
                dx = enemy.location.x - hero.location.x
                dz = enemy.location.z - hero.location.z
                norm = math.sqrt(dx*dx + dz*dz) or 1
                mx = max(1, min(15, int(8 + (dx/norm)*7)))
                mz = max(1, min(15, int(8 + (dz/norm)*7)))
                return (2, mx, mz, 1, 1, 1)

        nearest_soldier = None
        nearest_sd = 99999
        for s in self.soldiers:
            if s.camp == hero.camp or not s.alive:
                continue
            d = hero.distance_to(s)
            if d < nearest_sd:
                nearest_sd = d
                nearest_soldier = s
        if nearest_soldier and nearest_sd < hero.atk_range:
            if hero.attack_cooldown_counter <= 0:
                dmg = hero.phy_atk
                nearest_soldier.hp -= dmg
                if nearest_soldier.hp <= 0:
                    nearest_soldier.alive = False
                    hero.money += 20
                hero.attack_cooldown_counter = max(1, int(10 / max(hero.atk_spd, 0.1)))
            dx = nearest_soldier.location.x - hero.location.x
            dz = nearest_soldier.location.z - hero.location.z
            norm = math.sqrt(dx*dx + dz*dz) or 1
            mx = max(1, min(15, int(8 + (dx/norm)*7)))
            mz = max(1, min(15, int(8 + (dz/norm)*7)))
            return (3, mx, mz, 1, 1, 1)

        nearest_tower = None
        nearest_td = 99999
        for o in self.organs:
            if o.Camp == hero.camp or o.Hp <= 0:
                continue
            d = hero.distance_to(o)
            if d < nearest_td:
                nearest_td = d
                nearest_tower = o
        if nearest_tower and nearest_td < hero.atk_range:
            other_enemy = self.heroes[0] if hero.camp == 1 else self.heroes[1]
            if other_enemy.alive and hero.distance_to(other_enemy) < hero.atk_range * 3:
                pass
            else:
                if hero.attack_cooldown_counter <= 0:
                    dmg = hero.phy_atk * 0.5
                    nearest_tower.Hp -= dmg
                    if nearest_tower.Hp <= 0:
                        nearest_tower.alive = False
                    hero.attack_cooldown_counter = max(1, int(10 / max(hero.atk_spd, 0.1)))
                dx = nearest_tower.x - hero.location.x
                dz = nearest_tower.z - hero.location.z
                norm = math.sqrt(dx*dx + dz*dz) or 1
                mx = max(1, min(15, int(8 + (dx/norm)*7)))
                mz = max(1, min(15, int(8 + (dz/norm)*7)))
                return (3, mx, mz, 1, 1, 1)

        target_x, target_z = 0, 0
        dx = target_x - hero.location.x
        dz = target_z - hero.location.z
        norm = math.sqrt(dx*dx + dz*dz) or 1
        mx = max(1, min(15, int(8 + (dx/norm)*7)))
        mz = max(1, min(15, int(8 + (dz/norm)*7)))
        return (2, mx, mz, 1, 1, 1)

    def _move_hero(self, hero, mx, mz, speed_mult=1.0):
        if not hero.alive:
            return
        dx = (mx - 8) / 7.0
        dz = (mz - 8) / 7.0
        norm = math.sqrt(dx*dx + dz*dz)
        if norm < 0.01:
            return
        dx /= norm
        dz /= norm
        step = hero.mov_spd * speed_mult
        hero.location.x += dx * step
        hero.location.z += dz * step
        hero.location.x = max(MAP_X_MIN + 100, min(MAP_X_MAX - 100, hero.location.x))
        hero.location.z = max(MAP_Z_MIN + 100, min(MAP_Z_MAX - 100, hero.location.z))

    def _update_hp_regen(self):
        for hero in self.heroes:
            if hero.alive and hero.hp < hero.max_hp:
                hero.hp = min(hero.max_hp, hero.hp + hero.hp5 * 0.05)
            if hero.alive and hero.ep < hero.max_ep:
                hero.ep = min(hero.max_ep, hero.ep + hero.ep5 * 0.05)

    def _update_cooldowns(self):
        for hero in self.heroes:
            for skill in hero.skills:
                if skill.cooldown_remaining > 0:
                    skill.cooldown_remaining -= 1

    def _update_attack_cooldowns(self):
        for hero in self.heroes:
            if hero.attack_cooldown_counter > 0:
                hero.attack_cooldown_counter -= 1

    def _update_minions(self):
        for soldier in self.soldiers[:]:
            if not soldier.alive:
                self.soldiers.remove(soldier)
                continue
            if soldier.camp == 0:
                target_x, target_z = LANE_RED_BASE
            else:
                target_x, target_z = LANE_BLUE_BASE
            organs = [o for o in self.organs if o.Camp != soldier.camp and o.Hp > 0]
            enemy_soldiers = [s for s in self.soldiers if s.camp != soldier.camp and s.alive]
            nearest_target = None
            nearest_td = 99999
            for s in enemy_soldiers:
                d = soldier.distance_to(s)
                if d < nearest_td:
                    nearest_td = d
                    nearest_target = ("soldier", s)
            for o in organs:
                d = soldier.distance_to(o)
                if d < nearest_td:
                    nearest_td = d
                    nearest_target = ("organ", o)
            if nearest_target and nearest_td < 400:
                if soldier.attack_cooldown <= 0:
                    if nearest_target[0] == "organ":
                        dmg = 120
                        nearest_target[1].Hp -= dmg
                        nearest_target[1].Hp = max(0, nearest_target[1].Hp)
                        if nearest_target[1].Hp <= 0:
                            nearest_target[1].alive = False
                        soldier.hp -= 80
                    else:
                        dmg = soldier.phy_atk
                        nearest_target[1].hp -= dmg
                        nearest_target[1].hp = max(0, nearest_target[1].hp)
                        if nearest_target[1].hp <= 0:
                            nearest_target[1].alive = False
                    if soldier.hp <= 0:
                        soldier.alive = False
                    soldier.attack_cooldown = soldier.max_attack_cooldown
            else:
                dx = target_x - soldier.location.x
                dz = target_z - soldier.location.z
                norm = math.sqrt(dx*dx + dz*dz) or 1
                step = 30
                soldier.location.x += (dx / norm) * step
                soldier.location.z += (dz / norm) * step
            if soldier.attack_cooldown > 0:
                soldier.attack_cooldown -= 1

    def _update_tower_attacks(self):
        for organ in self.organs:
            if not organ.alive or organ.SubType == 24:
                continue
            if organ.Hp <= 0:
                organ.alive = False
                self.events.append({"type": "tower_destroyed", "tower": organ.name, "camp": organ.Camp})
                continue
            target = None
            soldiers = [s for s in self.soldiers if s.camp != organ.Camp and s.alive]
            for s in soldiers:
                if organ.distance_to(s) < 700:
                    target = s
                    break
            if not target:
                enemies = [h for h in self.heroes if h.camp != organ.Camp and h.alive]
                for e in enemies:
                    if organ.distance_to(e) < 700:
                        target = e
                        break
            if target and hasattr(target, 'hp'):
                is_hero = hasattr(target, 'skills')
                tower_dmg = {21: 300, 23: 400, 24: 500}.get(organ.SubType, 200)
                if not is_hero:
                    tower_dmg = 150
                target.hp -= tower_dmg
                target.hp = max(0, target.hp)
                self.events.append({"type": "tower_attack", "tower": organ.name,
                                    "target": getattr(target, 'config_id', target.runtime_id),
                                    "dmg": tower_dmg})

    def _add_soldier_gold(self, hero):
        for soldier in self.soldiers:
            if not soldier.alive and soldier.camp != hero.camp:
                pass

    def _check_hero_death(self):
        for hero in self.heroes:
            if hero.hp <= 0 and hero.alive:
                hero.alive = False
                hero.deadCnt += 1
                killer = None
                for other in self.heroes:
                    if other.camp != hero.camp:
                        other.killCnt += 1
                        other.money += 300
                        other.exp += 100
                        killer = other
                        break
                self.events.append({"type": "hero_death", "hero": hero.config_id, "killer": killer.config_id if killer else None})
                self.winner = 1 - hero.camp

    def _respawn_heroes(self):
        for hero in self.heroes:
            if not hero.alive and self.frame_no % 120 == 60:
                hero.alive = True
                hero.hp = hero.max_hp * 0.5
                hero.ep = hero.max_ep
                if hero.camp == 0:
                    hero.location = Vec3(-13000, 0, -13000)
                else:
                    hero.location = Vec3(13000, 0, 13000)
                for skill in hero.skills:
                    skill.cooldown_remaining = 0
                self.events.append({"type": "respawn", "hero": hero.config_id})

    def _check_game_over(self):
        for organ in self.organs:
            if organ.SubType == 24 and organ.Hp <= 0:
                self.winner = 1 - organ.Camp
                self.win_reason = f"{'蓝方' if organ.Camp==0 else '红方'}水晶被摧毁"
                return True
        if self.frame_no >= self.max_frames:
            self.win_reason = "帧数达到上限"
            return True
        return False

    def _make_state(self):
        req_pb = MockReqPb()
        req_pb.frame_no = self.frame_no
        req_pb.gameover = self._check_game_over()
        req_pb.hero_list = self.heroes
        req_pb.organ_list = self.organs
        req_pb.soldier_list = self.soldiers
        req_pb.monster_list = self.monsters
        obs = np.random.randn(453).astype(np.float32) * 0.1
        button_mask = self._make_button_mask()
        legal_action = np.zeros(84, dtype=np.float32)
        legal_action[:12] = button_mask
        for i in range(12):
            if button_mask[i] == 1:
                legal_action[12 + 16*4 + i*8 : 12 + 16*4 + i*8 + 8] = 1.0
        for i in range(16):
            if i < 15:
                legal_action[12 + i] = 1
                legal_action[12 + 16 + i] = 1
                legal_action[12 + 32 + i] = 1
                legal_action[12 + 48 + i] = 1
        state = {
            "observation": obs,
            "legal_action": legal_action,
            "reward": [0.0] * 9,
            "sub_action_mask": {i: np.ones(6, dtype=np.float32) for i in range(12)},
            "done": req_pb.gameover,
            "req_pb": req_pb,
            "frame_no": self.frame_no,
            "events": self.events[-20:],
        }
        return state

    def step(self, actions):
        self.frame_no += 1
        actions0 = actions[0] if len(actions) > 0 else (0, 0, 0, 0, 0, 0)
        actions1 = actions[1] if len(actions) > 1 else (0, 0, 0, 0, 0, 0)

        for i in range(min(2, len(self.heroes))):
            self.heroes[i].money += GOLD_PER_FRAME
            self.heroes[i].exp += EXP_PER_FRAME

        if self.heroes[0].ai_controlled:
            actions0 = self._ai_step(self.heroes[0])
        if len(self.heroes) > 1 and self.heroes[1].ai_controlled:
            actions1 = self._ai_step(self.heroes[1])
            self.ai_last_action = actions1

        for i, (hero, act) in enumerate([(self.heroes[0], actions0)] +
                                         ([(self.heroes[1], actions1)] if len(self.heroes) > 1 else [])):
            btn, mx, mz, sx, sz, tgt = act
            if btn == 2:
                self._move_hero(hero, mx, mz)
            elif btn == 3:
                result = self._execute_auto_attack(hero)
                if result:
                    self.events.append(result)
            elif btn in [4, 5, 6]:
                result = self._execute_skill(hero, btn, tgt, sx, sz)
                if result:
                    self.events.append(result)
            elif btn == 9 and i == 0:
                hero.location = Vec3(-13000, 0, -13000)
                hero.hp = min(hero.hp + 500, hero.effective_max_hp)
                self.events.append({"type": "recall", "hero": hero.config_id})

        self._update_cooldowns()
        self._update_attack_cooldowns()
        self._check_hero_death()
        self._update_hp_regen()
        self._respawn_heroes()
        self._update_tower_attacks()
        self._update_minions()

        if self.frame_no % MINION_WAVE_INTERVAL == 0:
            self._spawn_minion_wave()

        for hero in self.heroes:
            if hero.level < 15 and hero.exp >= LEVEL_EXP_TABLE[hero.level]:
                hero.exp -= LEVEL_EXP_TABLE[hero.level]
                hero.level_up()
                self.events.append({"type": "level_up", "hero": hero.config_id, "level": hero.level})

        self.heroes[0].camp_visible = [True, self.frame_no % 3 != 0]
        if len(self.heroes) > 1:
            self.heroes[1].camp_visible = [self.frame_no % 3 != 0, True]

        return self._make_state()

    def close_game(self):
        pass

    @property
    def game_over(self):
        return self.frame_no >= self.max_frames or any(
            o.Hp <= 0 for o in self.organs if o.SubType == 24)



def _organ_distance(self, other):
    if not hasattr(other, 'location'):
        return 99999
    return math.sqrt((self.x - other.location.x)**2 + (self.z - other.location.z)**2)
MockOrgan.distance_to = _organ_distance

def _soldier_distance(self, other):
    if hasattr(other, 'x'):
        ox, oz = other.x, other.z
    elif hasattr(other, 'location') and other.location:
        ox, oz = other.location.x, other.location.z
    else:
        return 99999
    return math.sqrt((self.location.x - ox)**2 + (self.location.z - oz)**2)
MockSoldier.distance_to = _soldier_distance

if __name__ == "__main__":
    env = MockEnvV2(hero_ids=[132, 169])
    state = env.reset()
    print(f"Initialized: {len(env.heroes)} heroes, {len(env.organs)} organs")
    for step in range(50):
        action = (2, 8, 8, 1, 1, 0)
        state = env.step([action, (0, 0, 0, 0, 0, 0)])
        pb = state["req_pb"]
        h0 = pb.hero_list[0]
        h1 = pb.hero_list[1]
        if step % 10 == 0:
            print(f"Frame {pb.frame_no}: H0 HP={h0.hp:.0f}/{h0.max_hp} Lv{h0.level} "
                  f"Gold={h0.money:.0f} @({h0.location.x:.0f},{h0.location.z:.0f}) | "
                  f"H1 HP={h1.hp:.0f}/{h1.max_hp} Lv{h1.level} "
                  f"@({h1.location.x:.0f},{h1.location.z:.0f})")
    print(f"Done. Events: {len(env.events)}")

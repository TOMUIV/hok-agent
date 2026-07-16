import random
import numpy as np

HERO_TEMPLATES = {
    132: {"name": "马可波罗", "hp": 3500, "attack": 180, "skills": ["SKILL_1", "SKILL_2", "SKILL_3"]},
    169: {"name": "后羿", "hp": 3200, "attack": 190, "skills": ["SKILL_1", "SKILL_2", "SKILL_3"]},
    141: {"name": "貂蝉", "hp": 3000, "attack": 160, "skills": ["SKILL_1", "SKILL_2", "SKILL_3"]},
    107: {"name": "赵云", "hp": 3800, "attack": 175, "skills": ["SKILL_1", "SKILL_2", "SKILL_3"]},
    199: {"name": "公孙离", "hp": 3100, "attack": 175, "skills": ["SKILL_1", "SKILL_2", "SKILL_3"]},
    112: {"name": "鲁班七号", "hp": 3000, "attack": 195, "skills": ["SKILL_1", "SKILL_2", "SKILL_3"]},
}

class MockPos:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.z = 0

class MockHero:
    def __init__(self, config_id, camp, runtime_id):
        self.config_id = config_id
        self.camp = camp
        self.runtime_id = runtime_id
        self.hp = random.randint(2000, 4000)
        self.max_hp = 4000
        self.level = 1
        self.exp = 0
        self.gold = 0
        self.mov_spd = 300
        self.atk_range = 700
        self.location = MockPos(random.uniform(10, 40), random.uniform(10, 40))
        self.camp_visible = [True, True]

class MockReqPb:
    def __init__(self, heroes, frame_no, gameover=False):
        self.hero_list = heroes
        self.frame_no = frame_no
        self.gameover = gameover
        self.command_info_list = []

class MockEnv:
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
        self.max_frames = 300
        self.heroes = []
        self.use_common_ai = []
        self.camp_hero_list = None

    def reset(self, camp_hero_list=None, use_common_ai=None, eval_mode=False):
        self.use_common_ai = use_common_ai or [False, False]
        self.camp_hero_list = camp_hero_list or [
            [{"hero_id": self.hero_ids[0], "skill_id": 80115}],
            [{"hero_id": self.hero_ids[1], "skill_id": 80115}],
        ]
        self.heroes = []
        for i, camp in enumerate(self.camp_hero_list):
            for j, hconf in enumerate(camp):
                hid = hconf["hero_id"]
                template = HERO_TEMPLATES.get(hid, {"name": f"Hero#{hid}", "hp": 3500, "attack": 170, "skills": []})
                hero = MockHero(hid, i, i * 100 + j)
                hero.max_hp = template["hp"]
                hero.hp = template["hp"]
                self.heroes.append(hero)
        self.frame_no = 0
        return self._make_state()

    def _make_button_mask(self):
        mask = np.zeros(12, dtype=np.float32)
        mask[2] = 1
        mask[3] = 1
        mask[4] = 1 if self.frame_no % 5 != 0 else 0
        mask[5] = 1
        mask[6] = 1 if self.frame_no % 7 == 0 else 0
        mask[9] = 1 if self.frame_no % 30 == 0 else 0
        mask[0] = 0
        mask[1] = 0
        if sum(mask) == 0:
            mask[2] = 1
        return mask

    def _make_state(self):
        self.frame_no += 1
        gameover = self.frame_no >= self.max_frames
        obs = np.random.randn(453).astype(np.float32) * 0.1
        button_mask = self._make_button_mask()
        legal_action = np.zeros(84, dtype=np.float32)
        legal_action[:12] = button_mask
        for h in self.heroes:
            h.hp -= random.uniform(0, 5)
            h.hp = max(0, h.hp)
            h.gold += random.randint(1, 5)
            h.level = min(15, 1 + self.frame_no // 20)
        if gameover:
            for h in self.heroes:
                h.hp = 0
        req_pb = MockReqPb(self.heroes, self.frame_no, gameover)
        sub_action_mask = {i: np.ones(6, dtype=np.float32) for i in range(12)}
        state = {
            "observation": obs,
            "legal_action": legal_action,
            "reward": [0.0] * 9,
            "sub_action_mask": sub_action_mask,
            "done": gameover,
            "req_pb": req_pb,
            "frame_no": self.frame_no,
        }
        return state

    def step(self, actions):
        for i, action in enumerate(actions):
            if i >= len(self.heroes):
                break
            btn, mx, mz, skx, skz, tgt = action
            hero = self.heroes[i]
            if btn == 2 and hasattr(hero, 'location') and hero.location:
                vx = (mx - 8) / 7.0
                vy = (mz - 8) / 7.0
                spd = getattr(hero, 'mov_spd', 300) * 0.5
                hero.location.x += vx * spd * 0.01
                hero.location.y += vy * spd * 0.01
                hero.location.x = max(0, min(60, hero.location.x))
                hero.location.y = max(0, min(60, hero.location.y))
            if btn == 3 and getattr(hero, 'camp_visible', None):
                tgt_hp = max(0, self.heroes[1-i].hp - random.uniform(10, 30))
                self.heroes[1-i].hp = tgt_hp
        state = self._make_state()
        return state

    def close_game(self):
        pass


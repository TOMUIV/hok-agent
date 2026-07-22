import os, json

GAMECORE_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)),
                 "gamecore", "gamecore", "core_assets", "customresources",
                 "ailab", "ai_config", "1v1"),
    "AILab/ai_config/1v1",
    "/hok_env/hok/hok1v1/core_assets/customresources/ailab/ai_config/1v1",
]

_ROLES = None
_SKILL_JSON = None
_EP_COST = None
_EQUIP_NAMES = None

def _find_base():
    for p in GAMECORE_PATHS:
        if os.path.isfile(os.path.join(p, "common", "hero_skill_info.txt")):
            return p
    return None

def _ensure_loaded():
    global _ROLES, _SKILL_JSON, _EP_COST, _EQUIP_NAMES
    base = _find_base()
    if base is None:
        if _EQUIP_NAMES is None:
            _EQUIP_NAMES = {}
        return
    if _ROLES is None:
        _ROLES = {}
        for path in [os.path.join(base, "pb2struct", "hero_main_job.txt"),
                     os.path.join(base, "tactics", "feature", "hero_main_job_v2.txt")]:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        parts = line.split("=")
                        if len(parts) == 2:
                            try:
                                _ROLES[int(parts[0])] = parts[1]
                            except:
                                pass
                break
    if _SKILL_JSON is None:
        path = os.path.join(base, "common", "hero_skill_info.txt")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _SKILL_JSON = json.load(f)
            except:
                _SKILL_JSON = {}
        else:
            _SKILL_JSON = {}
    if _EQUIP_NAMES is None:
        _EQUIP_NAMES = {}
        path = os.path.join(base, "tactics", "feature", "equipment_config_id.txt")
        if os.path.isfile(path):
            with open(path, "r", encoding="gbk") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        try:
                            _EQUIP_NAMES[int(parts[0])] = parts[1]
                        except ValueError:
                            pass

    if _EP_COST is None:
        _EP_COST = {}
        path = os.path.join(base, "common", "skill_ep_consume.txt")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("###"):
                        continue
                    parts = line.split("/")
                    if len(parts) >= 2:
                        try:
                            sid = int(parts[0])
                            ep = int(parts[1])
                            _EP_COST[sid] = ep
                        except:
                            pass


SKILL_TYPE_NAMES = {
    "dir": "directional",
    "pos": "target_position",
    "target_self": "self_cast",
}

SHAPE_NAMES = {
    "arrow": "line",
    "circle": "circle",
    "sector": "fan",
    "ring": "ring",
    "rectangle": "rectangle",
    "none": "none",
}

HERO_EN_NAMES = {
    106: "XiaoQiao", 107: "ZhaoYun", 108: "MoZi", 109: "DaJi",
    110: "YingZheng", 111: "SunShangXiang", 112: "LuBan7", 113: "ZhuangZhou",
    114: "LiuShan", 115: "GaoJianLi", 116: "AKe", 117: "ZhongWuYan",
    118: "SunBin", 119: "BianQue", 120: "BaiQi", 121: "MiYue",
    123: "LvBu", 124: "ZhouYu", 126: "XiaHouDun", 127: "ZhenJi",
    128: "CaoCao", 129: "DianWei", 130: "GongBen", 131: "LiBai",
    132: "MaKeBoLuo", 133: "DiRenJie", 134: "DaMo", 135: "XiangYu",
    136: "WuZeTian", 139: "LaoFuZi", 140: "GuanYu", 141: "DiaoChan",
    142: "AnQiLa", 144: "ChengYaoJin", 146: "LuNa", 148: "JiangZiYa",
    149: "LiuBang", 150: "HanXin", 152: "WangZhaoJun", 153: "LanLingWang",
    154: "HuaMuLan", 155: "AiLin", 156: "ZhangLiang", 157: "BuZhiHuoWu",
    162: "NaKeLuLu", 163: "JuYouJing", 166: "YaSe", 167: "SunWuKong",
    168: "NiuMo", 169: "HouYi", 170: "LiuBei", 171: "ZhangFei",
    173: "LiYuanFang", 174: "YuJi", 175: "ZhongKui", 176: "YangYuHuan",
    177: "ChengJiSiHan", 178: "YangJian", 179: "NvWa", 180: "NeZha",
    182: "GanJiangMoYe", 183: "YaDianNa", 184: "CaiWenJi", 186: "TaiYiZhenRen",
    187: "DongHuangTaiYi", 189: "GuiGuZi", 190: "ZhuGeLiang",
    192: "HuangZhong", 193: "Kai", 194: "SuLie", 195: "BaiLiXuanCe",
    196: "BaiLiShouYue", 198: "MengQi", 199: "GongSunLi",
    502: "PeiQinHu", 510: "SunCe", 513: "ShangGuanWanEr", 522: "Yao",
}


def get_hero_role(hero_id):
    _ensure_loaded()
    if _ROLES:
        return _ROLES.get(hero_id, "unknown")
    return "unknown"


def get_hero_en_name(hero_id):
    return HERO_EN_NAMES.get(hero_id, f"Hero#{hero_id}")


def get_hero_skill_info(hero_id):
    """Return dict of skill slot -> {range, shape, release_type, ep_cost} for given hero."""
    _ensure_loaded()
    result = {}
    if _SKILL_JSON:
        entry = _SKILL_JSON.get(str(hero_id))
        if entry:
            for sn_str, sdata in entry.get("skills", {}).items():
                slot = int(sdata.get("slot", sn_str))
                rng = sdata.get("indicator_max_distance", 0)
                shape = sdata.get("indicator_shape", "?")
                rtype = sdata.get("release_type", "?")
                move_dist = sdata.get("move_distance", 0)
                sid = sdata.get("id", 0)
                ep = _EP_COST.get(sid, 0) if _EP_COST else 0
                result[slot] = {
                    "range": rng,
                    "shape": shape,
                    "release": rtype,
                    "move_dist": move_dist,
                    "ep_cost": ep,
                }
    return result


def get_equip_name(config_id):
    _ensure_loaded()
    if _EQUIP_NAMES:
        return _EQUIP_NAMES.get(config_id, f"Equip#{config_id}")
    return f"Equip#{config_id}"


def format_hero_info(self_hero_id, enemy_hero_id):
    _ensure_loaded()
    self_name = get_hero_en_name(self_hero_id)
    enemy_name = get_hero_en_name(enemy_hero_id)
    self_role = get_hero_role(self_hero_id)
    enemy_role = get_hero_role(enemy_hero_id)
    self_skills = get_hero_skill_info(self_hero_id)
    enemy_skills = get_hero_skill_info(enemy_hero_id)

    lines = [f"  {self_name} ({self_role})"]
    for slot in [1, 2, 3]:
        s = self_skills.get(slot)
        if s:
            lines.append(f"    S{slot}: range={s['range']} shape={SHAPE_NAMES.get(s['shape'], s['shape'])} aim={SKILL_TYPE_NAMES.get(s['release'], s['release'])} ep={s['ep_cost']}")
    lines.append("")
    lines.append(f"  {enemy_name} ({enemy_role})")
    for slot in [1, 2, 3]:
        s = enemy_skills.get(slot)
        if s:
            lines.append(f"    S{slot}: range={s['range']} shape={SHAPE_NAMES.get(s['shape'], s['shape'])} aim={SKILL_TYPE_NAMES.get(s['release'], s['release'])} ep={s['ep_cost']}")

    return "\n".join(lines)

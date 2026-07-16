import math
import gamecore_data
from hero_db import hero_name

BUTTON_NAMES = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","HealSkill","ChosenSkill","Recall","Skill4","EquipSkill"]
BTN_SKILL_MAP = {"Skill1": 4, "Skill2": 5, "Skill3": 6}
BTN_REVERSE = {4: "Skill1", 5: "Skill2", 6: "Skill3", 3: "Attack", 2: "Move", 9: "Recall"}

def dist(x1, y1, x2, y2):
    return math.sqrt((x2-x1)**2 + (y2-y1)**2)

def get_skill_cd(h, slot):
    sk_list = getattr(h, "skill", [])
    if slot < len(sk_list):
        return getattr(sk_list[slot], "cooldown", 0), getattr(sk_list[slot], "cooldown_max", 0)
    return 0, 0

_SUB_FUNCS = {
    "FARM": [
        ("last_hit", "last-hit nearest minion"),
        ("move_to_lane", "move toward lane center"),
        ("retreat_to_tower", "walk back under tower"),
    ],
    "POKE": [
        ("aim_skill", "cast poke skill at enemy"),
        ("basic_attack", "basic attack enemy"),
        ("reposition_back", "step back to safe distance"),
    ],
    "ALL_IN": [
        ("combo_start", "execute skill combo rotation"),
        ("basic_attack", "basic attack enemy"),
        ("chase", "move toward enemy"),
    ],
}

def get_legal_macro_actions(self_h, enemy_h, legal_action, self_hero_id):
    if not self_h or not enemy_h:
        return ["  (no heroes)"]
    available = []
    blocked = []
    d_enemy = dist(self_h.location.x, self_h.location.y, enemy_h.location.x, enemy_h.location.y)
    hp_pct = self_h.hp / max(self_h.max_hp, 1)
    atk_range = getattr(self_h, "atk_range", 700)

    from hero_skills import HERO_SKILL_CONFIG
    cfg = HERO_SKILL_CONFIG.get(self_hero_id, {})
    skill_ranges = cfg.get("skill_ranges", {})

    for skill_name, sub_funcs in _SUB_FUNCS.items():
        for func_name, desc in sub_funcs:
            reason = None
            ok = True

            if skill_name == "FARM":
                if func_name == "last_hit":
                    if len(legal_action) >= 12 and int(legal_action[3]) != 1:
                        ok = False; reason = "Attack not available"
                elif func_name in ("retreat_to_tower", "move_to_lane"):
                    pass

            elif skill_name == "POKE":
                if func_name == "aim_skill":
                    pk = cfg.get("poke_skill", 1)
                    btn = {1: 4, 2: 5, 3: 6}[pk]
                    sr = skill_ranges.get(pk, 700)
                    if len(legal_action) >= 12 and int(legal_action[btn]) != 1:
                        btn_name = BTN_REVERSE.get(btn, f"btn{btn}")
                        ok = False; reason = f"Skill{pk}({btn_name}) not available"
                    elif d_enemy > sr:
                        ok = False; reason = f"enemy out of range ({d_enemy:.0f})"
                    else:
                        cd, _ = get_skill_cd(self_h, pk - 1)
                        if cd > 0:
                            ok = False; reason = f"Skill{pk} on cooldown ({cd/1000:.1f}s)"
                elif func_name == "basic_attack":
                    if len(legal_action) >= 12 and int(legal_action[3]) != 1:
                        ok = False; reason = "Attack not available"
                    elif d_enemy > atk_range:
                        ok = False; reason = f"enemy out of range ({d_enemy:.0f})"
                elif func_name == "reposition_back":
                    pass

            elif skill_name == "ALL_IN":
                if func_name == "combo_start":
                    prio = cfg.get("combo_priority", [3, 2, 1])
                    any_ok = False
                    for sn in prio:
                        btn = {1: 4, 2: 5, 3: 6}[sn]
                        sr = skill_ranges.get(sn, 700)
                        if int(legal_action[btn]) == 1 and d_enemy < sr:
                            cd, _ = get_skill_cd(self_h, sn - 1)
                            if cd == 0:
                                any_ok = True
                                break
                    if not any_ok:
                        ok = False; reason = "no combo skill in range or off cooldown"
                    if hp_pct < 0.3:
                        ok = False; reason = f"HP too low ({hp_pct*100:.0f}%)"
                elif func_name == "basic_attack":
                    if len(legal_action) >= 12 and int(legal_action[3]) != 1:
                        ok = False; reason = "Attack not available"
                    elif d_enemy > atk_range:
                        ok = False; reason = f"enemy out of range ({d_enemy:.0f})"
                elif func_name == "chase":
                    if d_enemy > atk_range * 3:
                        ok = False; reason = f"enemy too far ({d_enemy:.0f})"

            label = f"{skill_name}.{func_name}()"
            if ok:
                available.append(label)
            else:
                blocked.append(f"  {label}: {reason}")

    lines = []
    if available:
        lines.append("  AVAILABLE:")
        for a in available:
            lines.append(f"    {a}")
    if blocked:
        lines.append("  BLOCKED:")
        lines.extend(blocked)
    if not available and not blocked:
        lines.append("  (none)")
    return lines

def parse_state(info, self_hero_id=None):
    s = info if isinstance(info, dict) else info[0]
    if not isinstance(s, dict):
        return "[Invalid state]", None
    pb = s.get("req_pb")
    if not pb:
        return "[No game state]", None
    heroes = list(getattr(pb, 'hero_list', []))
    organs = list(getattr(pb, 'organ_list', []))
    soldiers = list(getattr(pb, 'soldier_list', []))
    monsters = list(getattr(pb, 'monster_list', []))
    frame_no = getattr(pb, 'frame_no', 0)
    gameover = getattr(pb, 'gameover', False)

    self_h = None
    enemy_h = None
    for h in heroes:
        cid = getattr(h, 'config_id', 0)
        if cid == self_hero_id:
            self_h = h
        else:
            enemy_h = h
    if not self_h and heroes:
        self_h = heroes[0]
        enemy_h = heroes[1] if len(heroes) > 1 else None

    lines = []
    game_time_s = frame_no * 0.033
    lines.append(f"=== FRAME {frame_no} (T+{game_time_s:.1f}s) ===")
    if gameover:
        lines.append("[GAME OVER]")

    def fow_hp_str(h, tag):
        hp = getattr(h, 'hp', 0)
        mhp = getattr(h, 'max_hp', 1)
        visible = getattr(h, 'camp_visible', [])
        if tag == "ENEMY" and not (any(visible) if visible else True):
            return f"FOW({hp}/?)"
        pct = hp / mhp * 100 if mhp > 0 else 0
        return f"{hp:.0f}/{mhp}({pct:.0f}%)"

    def get_pos(h):
        loc = getattr(h, 'location', None)
        if loc and hasattr(loc, 'x'):
            return (loc.x, loc.y, loc.z)
        return (None, None, None)

    lines.append("")
    lines.append("--- HEROES ---")
    if self_h:
        cid = getattr(self_h, 'config_id', 0)
        lv = getattr(self_h, 'level', 1)
        hp_str = fow_hp_str(self_h, "SELF")
        ep = f"{getattr(self_h,'ep',0)}/{getattr(self_h,'max_ep',0)}"
        gold = getattr(self_h, 'money', 0)
        px, py, pz = get_pos(self_h)
        pos_str = f"({px:.0f},{py:.0f})" if px else "(?,?)"
        pa = getattr(self_h, 'phy_atk', 0)
        ma = getattr(self_h, 'mgc_atk', 0)
        pd = getattr(self_h, 'phy_def', 0)
        md = getattr(self_h, 'mgc_def', 0)
        ar = getattr(self_h, 'atk_range', 0)
        ms = getattr(self_h, 'mov_spd', 0)
        bm = getattr(self_h, 'behav_mode', '')
        # skill cooldowns: hero.skill[i].cooldown / cooldown_max (game ticks, ~33ms/tick)
        sk_list = getattr(self_h, 'skill', [])
        s1 = sk_list[0] if len(sk_list) > 0 else None
        s2 = sk_list[1] if len(sk_list) > 1 else None
        s3 = sk_list[2] if len(sk_list) > 2 else None
        s1cd = getattr(s1, 'cooldown', 0) if s1 else 0
        s1mcd = getattr(s1, 'cooldown_max', 0) if s1 else 0
        s2cd = getattr(s2, 'cooldown', 0) if s2 else 0
        s2mcd = getattr(s2, 'cooldown_max', 0) if s2 else 0
        s3cd = getattr(s3, 'cooldown', 0) if s3 else 0
        s3mcd = getattr(s3, 'cooldown_max', 0) if s3 else 0

        lines.append(f"[SELF] {hero_name(cid)} LV{lv} HP:{hp_str} EP:{ep} Gold:{gold}")
        lines.append(f"  ATK:{pa}/{ma} DEF:{pd}/{md} Range:{ar} Spd:{ms}")
        lines.append(f"  Pos:{pos_str} Behav:{bm}")
        lines.append(f"  Skill CD: S1({s1cd/1000:.1f}s/{s1mcd/1000:.1f}s) S2({s2cd/1000:.1f}s/{s2mcd/1000:.1f}s) S3({s3cd/1000:.1f}s/{s3mcd/1000:.1f}s)")
        eq_list = getattr(self_h, 'equipment', []) or []
        eq_parts = []
        for eq in eq_list:
            eq_id = getattr(eq, 'config_id', 0)
            if eq_id:
                eq_parts.append(gamecore_data.get_equip_name(eq_id))
        lines.append(f"  Items: {', '.join(eq_parts) if eq_parts else '(none)'}")

    if enemy_h:
        cid = getattr(enemy_h, 'config_id', 0)
        lv = getattr(enemy_h, 'level', 1)
        hp_str = fow_hp_str(enemy_h, "ENEMY")
        ep = getattr(enemy_h, 'ep', 0)
        gold = getattr(enemy_h, 'money', 0)
        px, py, pz = get_pos(enemy_h)
        pos_str = f"({px:.0f},{py:.0f})" if px else "(?,?)"
        pa = getattr(enemy_h, 'phy_atk', 0)
        ma = getattr(enemy_h, 'mgc_atk', 0)
        pd = getattr(enemy_h, 'phy_def', 0)
        md = getattr(enemy_h, 'mgc_def', 0)
        ar = getattr(enemy_h, 'atk_range', 0)
        ms = getattr(enemy_h, 'mov_spd', 0)
        bm = getattr(enemy_h, 'behav_mode', '')

        lines.append(f"[ENEMY] {hero_name(cid)} LV{lv} HP:{hp_str} EP:{ep} Gold:{gold}")
        lines.append(f"  ATK:{pa}/{ma} DEF:{pd}/{md} Range:{ar} Spd:{ms}")
        lines.append(f"  Pos:{pos_str} Behav:{bm}")

    lines.append("")
    lines.append("--- TOWERS ---")
    blue_organs = {"crystal": None, "inner": None, "outer": None}
    red_organs = {"crystal": None, "inner": None, "outer": None}
    for o in organs:
        camp = getattr(o, 'Camp', -1)
        sub = getattr(o, 'SubType', 0)
        hp = getattr(o, 'Hp', 0)
        mhp = getattr(o, 'MaxHp', 0)
        ox = getattr(o, 'x', None)
        oz = getattr(o, 'z', None)
        info_str = f"HP:{hp}/{mhp}"
        if ox is not None and oz is not None:
            info_str += f" @({ox:.0f},{oz:.0f})"
        if camp == 0:
            if sub == 24: blue_organs["crystal"] = info_str
            elif sub == 23: blue_organs["inner"] = info_str
            elif sub == 21: blue_organs["outer"] = info_str
        elif camp == 1:
            if sub == 24: red_organs["crystal"] = info_str
            elif sub == 23: red_organs["inner"] = info_str
            elif sub == 21: red_organs["outer"] = info_str

    def organ_line(side, d):
        items = []
        for k in ["outer", "inner", "crystal"]:
            v = d.get(k)
            if v:
                items.append(f"{k}={v}")
            else:
                items.append(f"{k}=dead")
        return f"  {side}: " + " | ".join(items)

    lines.append(organ_line("BLUE", blue_organs))
    lines.append(organ_line("RED", red_organs))

    lines.append("")
    lines.append("--- MINIONS ---")
    if soldiers:
        s_count = len(soldiers)
        s = soldiers[0]
        camp = getattr(s, 'camp', -1)
        side = "BLUE" if camp == 0 else ("RED" if camp == 1 else "?")
        lines.append(f"  {s_count} visible ({side} side)")
    else:
        lines.append("  none visible")

    lines.append("")
    lines.append("--- MONSTERS ---")
    if monsters:
        lines.append(f"  {len(monsters)} visible")
    else:
        lines.append("  none")

    lines.append("")
    lines.append("--- MACRO ACTIONS ---")
    if not isinstance(s, dict):
        return "\n".join(lines) + "\n[state not dict]", None
    la = s.get("legal_action", [])
    macro_lines = get_legal_macro_actions(self_h, enemy_h, la, self_hero_id)
    if macro_lines:
        lines.extend(macro_lines)
    else:
        lines.append("  (none available)")

    lines.append("")
    lines.append("--- DISTANCES ---")
    sp = get_pos(self_h) if self_h else (None, None, None)
    ep = get_pos(enemy_h) if enemy_h else (None, None, None)
    if sp[0] is not None and ep[0] is not None:
        d = dist(sp[0], sp[1], ep[0], ep[1])
        lines.append(f"  To enemy: {d:.0f}")
    else:
        lines.append("  To enemy: ?")

    # distance to nearest enemy tower
    min_tower_d = 1e9
    for o in organs:
        camp = getattr(o, 'Camp', -1)
        if camp == 1 and sp[0] is not None:
            ox = getattr(o, 'x', None)
            oz = getattr(o, 'z', None)
            if ox is not None and oz is not None:
                d = dist(sp[0], sp[1], ox, oz)
                if d < min_tower_d:
                    min_tower_d = d
    if min_tower_d < 1e8:
        lines.append(f"  To nearest enemy tower: {min_tower_d:.0f}")
    else:
        lines.append("  To nearest enemy tower: ?")

    # distance to nearest minion
    min_soldier_d = 1e9
    for sol in soldiers:
        loc = getattr(sol, 'location', None)
        if loc and hasattr(loc, 'x') and sp[0] is not None:
            d = dist(sp[0], sp[1], loc.x, loc.z)
            if d < min_soldier_d:
                min_soldier_d = d
    if min_soldier_d < 1e8:
        lines.append(f"  To nearest minion: {min_soldier_d:.0f}")
    else:
        lines.append("  To nearest minion: ?")

    return "\n".join(lines), self_h


def hero_detail(h):
    if not h:
        return "No hero"
    lines = []
    cid = getattr(h, 'config_id', 0)
    lines.append(f"Hero: {hero_name(cid)} (ID:{cid})")
    lines.append(f"  Lv:{getattr(h,'level','?')} Exp:{getattr(h,'exp','?')} Gold:{getattr(h,'money','?')}")
    lines.append(f"  HP:{getattr(h,'hp','?')}/{getattr(h,'max_hp','?')} EP:{getattr(h,'ep','?')}/{getattr(h,'max_ep','?')}")
    loc = getattr(h, 'location', None)
    if loc and hasattr(loc, 'x'):
        lines.append(f"  Position: ({loc.x}, {loc.y}, {loc.z})")
    lines.append(f"  PhyAtk:{getattr(h,'phy_atk','?')} PhyDef:{getattr(h,'phy_def','?')}")
    lines.append(f"  MgcAtk:{getattr(h,'mgc_atk','?')} MgcDef:{getattr(h,'mgc_def','?')}")
    lines.append(f"  MoveSpd:{getattr(h,'mov_spd','?')} AtkRange:{getattr(h,'atk_range','?')}")
    lines.append(f"  AtkSpd:{getattr(h,'atk_spd','?')} CritRate:{getattr(h,'crit_rate','?')}%")
    lines.append(f"  K/D/A:{getattr(h,'killCnt','?')}/{getattr(h,'deadCnt','?')}/{getattr(h,'assistCnt','?')}")
    lines.append(f"  DmgToHero:{getattr(h,'totalHurtToHero','?')} HurtByHero:{getattr(h,'totalBeHurtByHero','?')}")
    lines.append(f"  State: {getattr(h,'behav_mode','')}")
    return "\n".join(lines)


def available_buttons(info):
    s = info if isinstance(info, dict) else info[0]
    la = s.get("legal_action", [])
    if len(la) >= 12:
        return [(i, BUTTON_NAMES[i]) for i in range(12) if la[i] == 1]
    return []


def compress_state(pb, self_hero_id=None):
    """Return a compact 3-5 line summary of the game state for MEMORY history."""
    if not pb:
        return "(no state)"
    lines = []
    heroes = list(getattr(pb, 'hero_list', []))
    self_h = enemy_h = None
    for h in heroes:
        cid = getattr(h, 'config_id', 0)
        if cid == self_hero_id:
            self_h = h
        else:
            enemy_h = h
    if self_h:
        hp = getattr(self_h, 'hp', 0)
        mhp = getattr(self_h, 'max_hp', 1)
        ep = getattr(self_h, 'ep', 0)
        g = getattr(self_h, 'money', 0)
        loc = getattr(self_h, 'location', None)
        pos = f"({loc.x:.0f},{loc.y:.0f})" if loc and hasattr(loc, 'x') else "(?,?)"
        pct = hp / mhp * 100 if mhp > 0 else 0
        lines.append(f"SELF: {hp}/{mhp}({pct:.0f}%) EP:{ep} G:{g} @{pos}")
    if enemy_h:
        hp = getattr(enemy_h, 'hp', 0)
        mhp = getattr(enemy_h, 'max_hp', 1)
        visible = getattr(enemy_h, 'camp_visible', [])
        g = getattr(enemy_h, 'money', 0)
        loc = getattr(enemy_h, 'location', None)
        pos = f"({loc.x:.0f},{loc.y:.0f})" if loc and hasattr(loc, 'x') else "(?,?)"
        is_visible = any(visible) if visible else True
        hp_s = f"{hp}/{mhp}" if is_visible else "FOW"
        lines.append(f"ENEMY: {hp_s} G:{g} @{pos}")
    organs = list(getattr(pb, 'organ_list', []))
    for o in organs:
        camp = getattr(o, 'Camp', -1)
        sub = getattr(o, 'SubType', 0)
        hp = getattr(o, 'Hp', 0)
        mhp = getattr(o, 'MaxHp', 0)
        if sub == 21:
            side = "BLUE" if camp == 0 else "RED"
            lines.append(f"{side} twr: {hp}/{mhp}")
    soldiers = list(getattr(pb, 'soldier_list', []))
    if soldiers:
        camp = getattr(soldiers[0], 'camp', -1)
        side = "BLUE" if camp == 0 else ("RED" if camp == 1 else "?")
        lines.append(f"Minions: {len(soldiers)}({side})")
    else:
        lines.append("Minions: 0(FOW)")
    return " | ".join(lines)

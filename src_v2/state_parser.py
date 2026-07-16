from hero_db import hero_name

BUTTON_NAMES = ["None1","None2","Move","Attack","Skill1","Skill2","Skill3","HealSkill","ChosenSkill","Recall","Skill4","EquipSkill"]

def parse_state(info, self_hero_id=None):
    s = info if isinstance(info, dict) else info[0]
    pb = s.get("req_pb")
    if not pb:
        return "[No game state]", None
    heroes = getattr(pb, 'hero_list', [])
    frame_no = getattr(pb, 'frame_no', 0)
    gameover = getattr(pb, 'gameover', False)

    self_hero = None
    enemy_hero = None
    for h in heroes:
        cid = getattr(h, 'config_id', 0)
        if cid == self_hero_id:
            self_hero = h
        else:
            enemy_hero = h
    if not self_hero and heroes:
        self_hero = heroes[0] if len(heroes) > 0 else None
        enemy_hero = heroes[1] if len(heroes) > 1 else None

    lines = []
    lines.append(f"> Frame {frame_no}")
    if gameover:
        lines.append("  [GAME OVER]")

    def hero_line(h, tag):
        cid = getattr(h, 'config_id', 0)
        hp = getattr(h, 'hp', 0)
        max_hp = getattr(h, 'max_hp', 1)
        visible = getattr(h, 'camp_visible', [])
        is_visible = any(visible) if visible else True
        if tag == "ENEMY" and not is_visible:
            hp_str = f"{hp}/{max_hp}(FOW)"
        else:
            hp_pct = hp / max_hp * 100 if max_hp > 0 else 0
            hp_str = f"{hp:.0f}/{max_hp}({hp_pct:.0f}%)"
        ep = getattr(h, 'ep', 0)
        lv = getattr(h, 'level', 1)
        gold = getattr(h, 'money', 0)
        loc = getattr(h, 'location', None)
        pos = f"({loc.x},{loc.y})" if loc and hasattr(loc, 'x') else "(?,?)"
        mov_spd = getattr(h, 'mov_spd', 0)
        behav = getattr(h, 'behav_mode', '')
        line = f"  [{tag}] {hero_name(cid)} LV{lv} HP:{hp_str} EP:{ep} Gold:{gold} @{pos}"
        if mov_spd and mov_spd > 0:
            line += f" Spd:{mov_spd}"
        return line

    if self_hero:
        lines.append(hero_line(self_hero, "YOU"))
    if enemy_hero:
        lines.append(hero_line(enemy_hero, "ENEMY"))

    la = s.get("legal_action", [])
    if len(la) >= 12:
        available = [BUTTON_NAMES[i] for i in range(12) if la[i] == 1]
        lines.append(f"  Legal: {', '.join(available)}")

    return "\n".join(lines), self_hero

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

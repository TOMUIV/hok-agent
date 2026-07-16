from skill_base import Skill, register_skill

@register_skill
class ALL_IN(Skill):
    name = "ALL_IN"
    description = "全力击杀。按连招顺序释放所有技能，追击至死"
    when = "敌方血量<50%，核心技能不在 CD"
    until = "敌方死亡（kill）或所有技能进入 CD"

    def func_combo_start(self, ctx):
        """按 combo_priority 释放下一个技能。返回技能名和是否命中"""
        cfg = ctx.hero_config
        if not cfg:
            return "no config"
        prio = cfg.get("combo_priority", [3,2,1])
        for sn in prio:
            btn = {1:4,2:5,3:6}[sn]
            sr = cfg.get("skill_ranges", {}).get(sn, 700)
            if ctx.dist_to_enemy() < sr and ctx.valid_btn(btn):
                act = ctx.make_skill(sn, ctx.ex, ctx.ey)
                return f"skill{sn} released"
        return "all skills done or out of range"

    def func_basic_attack(self, ctx):
        """普攻追击。返回伤害"""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            ctx.make_attack()
            return "attack"
        return "not in range"

    def func_chase(self, ctx):
        """向敌人移动追击"""
        ctx.make_move_to(ctx.ex, ctx.ey)
        return "chasing"

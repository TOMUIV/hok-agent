from skill_base import Skill, register_skill

@register_skill
class POKE(Skill):
    name = "POKE"
    description = "远程消耗。用 Skill1 或普攻从安全距离磨血"
    when = "血量优势、技能不在 CD、敌方站位靠前"
    until = "技能进入 CD（done）或敌方后撤"

    def func_aim_skill(self, ctx):
        """释放消耗技能瞄准敌人。返回技能名和是否命中"""
        cfg = ctx.hero_config
        if not cfg:
            return "no config"
        pk = cfg.get("poke_skill", 1)
        btn = {1:4,2:5,3:6}[pk]
        sr = cfg.get("skill_ranges", {}).get(pk, 700)
        if ctx.dist_to_enemy() < sr and ctx.valid_btn(btn):
            act = ctx.make_skill(pk, ctx.ex, ctx.ey)
            return f"skill{pk} aimed"
        return "out of range"

    def func_basic_attack(self, ctx):
        """普攻一次。返回伤害值"""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            act = ctx.make_attack()
            return "attack"
        return "not in range"

    def func_reposition_back(self, ctx):
        """后撤步，与敌人保持安全距离"""
        camp = ctx.camp()
        ctx.make_move(8 + camp, 8)
        return "backing"

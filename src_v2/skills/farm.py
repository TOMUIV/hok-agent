from skill_base import Skill, register_skill

@register_skill
class FARM(Skill):
    name = "FARM"
    description = "补兵发育。优先击杀残血小兵获取金币和经验"
    when = "对线期，兵线在附近"
    until = "无（一直执行直到 LLM 改指令）"

    def func_last_hit(self, ctx):
        """补刀：检测最近残血小兵，攻击它。返回目标信息"""
        if ctx.valid_btn(3) and ctx.dist_to_enemy() < ctx.atk_range():
            act = ctx.make_attack()
            return "attack minion"
        return "move to lane"

    def func_move_to_lane(self, ctx):
        """向前推进"""
        ctx.make_move_to(100000, 48)
        return "moving forward"

    def func_retreat_to_tower(self, ctx):
        """兵线推过去后后撤回塔下"""
        camp = ctx.camp()
        ctx.make_move(8 + camp, 8)
        return "retreating"

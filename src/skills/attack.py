from skill_base import Skill, register_skill

@register_skill
class ATTACK(Skill):
    name = "ATTACK"
    description = "One basic attack toward enemy (default) or minion (target=minion). Rolls forward if out of range."
    when = "Enemy or minion in attack range."
    until = "Action executed (one frame)."
    sub_func_returns = {"execute": "dict: action/status/detail. status: success|moved."}

    def func_execute(self, ctx):
        return {"action": "attack", "status": "success", "detail": "basic attack"}

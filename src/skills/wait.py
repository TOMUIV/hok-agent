from skill_base import Skill, register_skill

@register_skill
class WAIT(Skill):
    name = "WAIT"
    description = "Stand still for this frame. Useful when holding position or waiting for cooldowns."
    when = "No better action, want to preserve position."
    until = "One frame."
    sub_func_returns = {"hold": "dict: action/status/detail. status: idle."}

    def func_hold(self, ctx):
        return {"action": "wait", "status": "idle", "detail": "standing still"}

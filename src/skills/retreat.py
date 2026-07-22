from skill_base import Skill, register_skill

@register_skill
class RETREAT(Skill):
    name = "RETREAT"
    description = "Multi-step: move toward own spawn. Continuous (no damage interrupt). Call once; runs until close to base."
    when = "Low HP, outmatched, need to disengage."
    until = "Within 300 units of spawn."
    sub_func_returns = {"step": "dict: action/status/detail. status: retreating|arrived."}

    def func_step(self, ctx):
        return {"action": "retreat", "status": "retreating", "detail": "moving toward spawn"}

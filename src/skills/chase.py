from skill_base import Skill, register_skill

@register_skill
class CHASE(Skill):
    name = "CHASE"
    description = "Multi-step: move toward enemy. Attacks if in range. Continuous (no damage interrupt). Call once; chases until you switch skill."
    when = "Enemy low HP, fleeing, you have kill pressure."
    until = "You switch to another skill."
    sub_func_returns = {"step": "dict: action/status/detail. status: chasing|attacking."}

    def func_step(self, ctx):
        return {"action": "chase", "status": "chasing", "detail": "moving toward enemy"}

from skill_base import Skill, register_skill

@register_skill
class MOVE_TO(Skill):
    name = "MOVE_TO"
    description = "Move toward coordinates (x,y) or in a compass direction. Stuck detection auto-returns control after 30 frames without movement."
    when = "Need to reach a position or move in a fixed direction."
    until = "Arrival at (x,y), or indefinitely if direction= (until LLM switches)."
    sub_func_params = {
        "step": ["x", "y"],
        "go": ["direction"],
    }
    sub_func_returns = {
        "step": "dict: action/status/detail. status: moving|arrived.",
        "go": "dict: action/status/direction/detail. status: moving.",
    }

    def func_step(self, ctx):
        return {"action": "move_to", "status": "moving", "detail": "moving toward target"}

    def func_go(self, ctx):
        return {"action": "move_to_dir", "status": "moving", "direction": "fixed", "detail": "moving in fixed direction"}

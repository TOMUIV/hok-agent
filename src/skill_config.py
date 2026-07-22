# Skill configuration — edit this instead of individual skill files.
# Skills listed here are CONTINUOUS: they run uninterrupted despite damage.
# All other skills are interruptible (damage → return control to LLM).

CONTINUOUS_SKILLS = {
    "COMBO_STEP",  # full combo should not be interrupted
    "RETREAT",     # retreat must complete to reach safety
    "CHASE",       # chase must continue to secure kill
    "KITE",        # kiting needs uninterrupted attack-move rhythm
    "DODGE",       # dodge/escape must execute instantly
}

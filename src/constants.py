import os

# Button indices
BTN_MOVE, BTN_ATTACK = 2, 3
BTN_SKILL1, BTN_SKILL2, BTN_SKILL3 = 4, 5, 6
BTN_RECALL = 9
CENTER = 8

BUTTON_NAMES = [
    "None1", "None2", "Move", "Attack", "Skill1", "Skill2", "Skill3",
    "HealSkill", "ChosenSkill", "Recall", "Skill4", "EquipSkill",
]

# Legal action flat array layout
BTN_COUNT = 12
MOVE_COORDS = 16
MOVE_FIELDS = 4
TARGETS_PER_BTN = 8
LEGAL_OFFSET = BTN_COUNT + MOVE_COORDS * MOVE_FIELDS  # 76

# Tower config_id → (camp_label, structure_label)
TOWER_MAP = {
    1:   ("BLUE", "outer"),
    2:   ("RED", "outer"),
    42:  ("BLUE", "inner"),
    43:  ("RED", "inner"),
    106: ("BLUE", "crystal"),
    107: ("RED", "crystal"),
}

# Gold spike detection
GOLD_SPIKE = 200
POWER_SPIKE = 1000

# ZMQ ports
ZMQ_PORTS = [35500, 35501]

# Frame timing
FRAME_DURATION = 0.033  # seconds per game frame

# Trajectories directory
TRAJECTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trajectories")

# Stuck detection
STUCK_LIMIT = 30  # frames without movement before returning control

# Arrival thresholds
MOVE_ARRIVAL_DIST = 800
RETREAT_ARRIVAL_DIST = 300

# Reflect context window
REFLECT_WINDOW = 100

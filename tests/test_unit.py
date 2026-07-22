"""Unit tests for HOK agent (no Docker/Gamecore required)."""
import sys, os, math, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ===== pathfinding =====
from pathfinding import astar
path = astar(0, 0, 8000, 8000)
assert path, "astar should find a path"
assert len(path) >= 2, "astar should have at least start + end"
# Without obstacles, should roughly go diagonal
assert abs(path[-1][0] - 8000) < 900 and abs(path[-1][1] - 8000) < 900
print("[PASS] astar basic pathfinding")

# astar with obstacles
path2 = astar(0, 0, 8000, 8000, obstacles=[(4000, 4000, 800)])
assert path2, "astar should find a path around obstacle"
print("[PASS] astar obstacle avoidance")

# 0-distance path
path3 = astar(100, 100, 100, 100)
assert path3 == [(100, 100)], "0-distance should return single point"
print("[PASS] astar zero distance")

# ===== skills_concrete utils =====
from skills_concrete import clamp, direction_to, dist, valid_btn, get_target_for

assert clamp(0) == 1
assert clamp(16) == 15
assert clamp(8) == 8
assert clamp(-5) == 1
print("[PASS] clamp")

d = dist(0, 0, 3, 4)
assert d == 5.0
assert dist(100, 100, 100, 100) == 0
print("[PASS] dist")

mx, my = direction_to(0, 0, 100, 0)
assert mx == 15 and my == 8, f"direction_to east: got ({mx},{my})"
mx, my = direction_to(0, 0, 0, 100)
assert mx == 8 and my == 15, f"direction_to north: got ({mx},{my})"
mx, my = direction_to(0, 0, -100, 0)
assert mx == 1 and my == 8, f"direction_to west: got ({mx},{my})"
mx, my = direction_to(0, 0, 0, -100)
assert mx == 8 and my == 1, f"direction_to south: got ({mx},{my})"
print("[PASS] direction_to")

assert not valid_btn([], 3)
assert valid_btn([0, 0, 0, 1.0, 0], 3)
assert not valid_btn([0, 0, 0, 0, 0], 3)
print("[PASS] valid_btn")

la = [0.0] * (12 + 16*4 + 12*8)
off = 12 + 4*16
la[off + 3*8 + 2] = 1.0  # btn=3, target=2 available
assert get_target_for(la, 3) == 2
la[off + 3*8 + 2] = 0.0
assert get_target_for(la, 3) == 0
print("[PASS] get_target_for")

# ===== skill_base: no_interrupt inheritance =====
from skill_base import Skill
from skill_config import CONTINUOUS_SKILLS

class TestInterruptible(Skill):
    name = "TEST_INTERRUPTIBLE"

assert not TestInterruptible.no_interrupt, "non-continuous skill should be interruptible"

class TestContinuous(Skill):
    name = "COMBO_STEP"

assert hasattr(TestContinuous, 'no_interrupt'), "COMBO_STEP should have no_interrupt"
assert TestContinuous.no_interrupt == True, "COMBO_STEP should be continuous"

class TestRetreat(Skill):
    name = "RETREAT"

assert TestRetreat.no_interrupt == True, "RETREAT should be continuous"

assert "MOVE_TO" not in CONTINUOUS_SKILLS
assert "COMBO_STEP" in CONTINUOUS_SKILLS
assert "RETREAT" in CONTINUOUS_SKILLS
assert "CHASE" in CONTINUOUS_SKILLS
assert "KITE" in CONTINUOUS_SKILLS
assert "DODGE" in CONTINUOUS_SKILLS
assert len(CONTINUOUS_SKILLS) == 5
print("[PASS] no_interrupt inheritance from config")

# ===== strategy_executor utils =====
from strategy_executor import clamp as se_clamp, direction_to as se_dir

assert se_clamp(8) == 8
assert se_clamp(0) == 1, "strategy_executor clamp(0) -> 1"
assert se_clamp(16) == 15
print("[PASS] strategy_executor clamp")

mx, my = se_dir(0, 0, 100, 0)
assert 8 <= mx <= 15 and 1 <= my <= 15
print("[PASS] strategy_executor direction_to")

# ===== state_parser: legal action helpers =====
from state_parser import _check_skill_btn

assert not _check_skill_btn([], 3)
assert _check_skill_btn([0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0], 3)
assert not _check_skill_btn([0]*12, 3)
print("[PASS] _check_skill_btn")

# ===== camp comparison pattern (simulating fix) =====
class MockCamp:
    def __init__(self, val):
        self.value = val

# Simulate hero BLUE camp = some enum value
hero_camp_obj = MockCamp(3)
hero_camp = hero_camp_obj.value if hasattr(hero_camp_obj, 'value') else hero_camp_obj

soldiers = [MockCamp(3), MockCamp(1), MockCamp(3), MockCamp(1), MockCamp(3)]
friendly = sum(1 for s in soldiers if s.value == hero_camp)
enemy = len(soldiers) - friendly
assert friendly == 3, f"expected 3 friendly, got {friendly}"
assert enemy == 2, f"expected 2 enemy, got {enemy}"
print("[PASS] camp comparison (non-standard enum values)")

# Simulate BLUE=0, RED=1 (traditional)
hero2 = MockCamp(0)
hc2 = hero2.value if hasattr(hero2, 'value') else hero2
soldiers2 = [MockCamp(0), MockCamp(1), MockCamp(0)]
f2 = sum(1 for s in soldiers2 if s.value == hc2)
e2 = len(soldiers2) - f2
assert f2 == 2 and e2 == 1
print("[PASS] camp comparison (standard 0/1 values)")

# ===== main_macro helper: _get_tower_hp =====
# Simulated organ with lowercase fields
class MockOrgan:
    def __init__(self, cid, hp):
        self.config_id = cid
        self.hp = hp

organs = [MockOrgan(1, 5000), MockOrgan(2, 5000), MockOrgan(42, 6000)]
# Test pattern used in _get_tower_hp
for o in organs:
    cid = getattr(o, 'config_id', 0)
    assert cid in [1, 2, 42]
    hp = getattr(o, 'hp', 0)
    assert hp > 0
print("[PASS] tower field access (lowercase)")

# ===== (removed) _extract_decision_events — function deleted in Phase 2 =====

# ===== PROMPT_SYS3_PREDICT / PROMPT_SYS4_ALIGN format check =====
from prompts import PROMPT_SYS3_PREDICT, PROMPT_SYS4_ALIGN
assert "PREDICTION REVIEW PROTOCOL" in PROMPT_SYS3_PREDICT
assert "=== FEW-SHOT EXAMPLES ===" in PROMPT_SYS3_PREDICT
assert "NEW SEMANTIC" in PROMPT_SYS3_PREDICT
print(f"[PASS] PROMPT_SYS3_PREDICT structure")

assert "GOAL ALIGNMENT REVIEW PROTOCOL" in PROMPT_SYS4_ALIGN
assert "SHORT-TERM GOAL" in PROMPT_SYS4_ALIGN
assert "ALIGNMENT ANALYSIS" in PROMPT_SYS4_ALIGN
assert "=== FEW-SHOT EXAMPLES ===" in PROMPT_SYS4_ALIGN
print(f"[PASS] PROMPT_SYS4_ALIGN structure")

# ===== _parse_episodic_semantic compatibility (SYS3/SYS4 output format) =====
from memory import _parse_episodic_semantic
reply = """=== NEW EPISODIC ===
--- Case: game_test / PREDICTION @F387 ---
  Context: test context
  Lesson: test lesson

=== NEW SEMANTIC ===
- enemy visible -> POKE before MOVE_TO
"""
items = _parse_episodic_semantic(reply, "game_test", "PREDICTION", 387)
assert len(items) == 2, f"expected 2 items (1 epi + 1 sem), got {len(items)}"
epi_items = [i for i in items if i["kind"] == "episodic"]
sem_items = [i for i in items if i["kind"] == "semantic"]
assert len(epi_items) == 1, f"expected 1 episodic, got {len(epi_items)}"
assert "game_test / PREDICTION @F387" in epi_items[0]["case_id"]
assert len(sem_items) == 1, f"expected 1 semantic, got {len(sem_items)}"
assert "POKE" in sem_items[0]["rule"]
print(f"[PASS] _parse_episodic_semantic SYS3/SYS4 compatible")

# ===== memory dedup helpers =====
from memory import _norm_rule
r1 = _norm_rule("HP below 50 -> call FARM to move to lane")
assert "->" in r1, f"expected '->' in output, got: {r1}"
r2 = _norm_rule("HP below 30% -> call RETREAT to fall back")
assert "->" in r2, f"expected '->' in output, got: {r2}"
print("[PASS] _norm_rule")

print("\n=== ALL UNIT TESTS PASSED ===")

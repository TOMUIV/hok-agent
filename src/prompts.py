# Shared prompt components for HOK AI Agent
# Usage:
#   SYS1 = PROMPT_BASE + PROMPT_SYS1_PROTOCOL
#   Phase 1 (events):      PROMPT_BASE + PROMPT_SYS2_EVENT
#   Phase 2 (per-decision): PROMPT_BASE + PROMPT_SYS3_PREDICT, PROMPT_SYS4_ALIGN
#   Phase 3 (whole-game):   PROMPT_BASE + PROMPT_SYS3_GLOBAL, PROMPT_SYS4_GLOBAL
#   AUDIT = PROMPT_BASE + PROMPT_AUDIT


CONVERGENCE_BLOCK = """
You may output:
  - REFERENCE EPISODIC: if a prior experience already covers this pattern
  - NEW EPISODIC: if a genuinely new pattern emerges. Focus on a specific scene.
  - REFERENCE SEMANTIC: if an existing rule applies
  - NEW SEMANTIC: if a new reusable rule is discovered
You are NOT required to output anything. Only output if truly new.

EPISODIC format:
  --- Case: {game_id} / {event_type} @{frame} ---
    Context: what happened, why. Reference @SKILL_CALL names.
    Lesson: what to do next time. Must include specific @SKILL_CALL.

SEMANTIC format:
  - condition -> SKILL_NAME. Not generic advice.

Context must NOT be vague ("whole game advantage"). Focus on one moment.
Lesson must NOT be generic ("manage minions"). Must include an atomic skill name.
"""


class ProtocolRenderer:
    """Build a protocol from task description + optional extra format + convergence block + examples."""
    def __init__(self, header, task, examples, has_convergence=True, extra_format=""):
        self.header = header
        self.task = task
        self.examples = examples
        self.has_convergence = has_convergence
        self.extra_format = extra_format

    def render(self):
        parts = [self.header, "Remember: FORMAT RULES at the top are mandatory. EXPERIENCE is verified across games."]
        parts.append(self.task)
        if self.extra_format:
            parts.append(self.extra_format)
        if self.has_convergence:
            parts.append(CONVERGENCE_BLOCK)
        parts.append(self.examples)
        return "\n\n".join(parts)

PROMPT_BASE = """You control {self_name}({self_type}) vs {enemy_name}({enemy_type}) in Honor of Kings 1v1.
STRICT adherence to FORMAT RULES and EXPERIENCE is REQUIRED. Violations lose the game.

=== GAME RULES ===
--- GOAL ---
Destroy the enemy crystal to win. This is your only win condition.
How to achieve it:
  - Kill enemy minions to push the wave toward enemy tower
  - Damage enemy tower when minions are tanking tower aggro
  - Poke enemy hero to create HP advantage for a kill
  - Kill enemy hero when they are low HP — this opens the lane
  - Prevent enemy from destroying your towers and crystal
  - Farm gold by last-hitting minions to buy stronger items
  - Recall when low HP — dying gives enemy gold and lane control

Every frame matters. Inactivity loses. You must push, fight, and destroy.

--- GAME MODE ---
Scene: 1V1.abs. Mode: 1v1. game_type=1.
Two camps: CampID:0 (you, self=BLUE) vs CampID:1 (enemy, RED).
Your hero config_id={self_hero_id}. Enemy config_id={enemy_hero_id}.
Per-frame protobuf includes: frame_no, gameover, hero_list, organ_list, soldier_list, monster_list, legal_action.
Observed max frames: ~3200 frames/game. Each frame ~60 game ms.
Hero roles: tank, soldier, assassin, wizard, shooter, suport.
Hero has 3 skill slots (SKILL_SLOT_NUM=3). Summoner skill at slot 5 (MASTER_SKILL_IDX=5).
Skill max levels: skill1/skill2 [0,6], skill3/ultimate [0,3]. Cooldowns [0,80000] (game ticks).

--- MAP CONFIG ---
Total map length: 113000 units. Center at (0, 0, 0). Ground Y=48.
AI feature coordinate ranges:
  soldier/organ location_x: [-40000, 40000]    location_z: [-40000, 40000]
  monster location: [-60000, 60000]
  max distance any two entities: 113000
  soldier HP: [0, 12000]    soldier ATK: [0, 700]
  organ HP: [0, 9000]       organ ATK: [0, 630]
  organ attack range: [0, 13000]  organ kill income: [0, 150]
  monster HP: [0, 20000]    monster ATK: [0, 800]   monster kill income: [0, 105]
Map sub-regions:
  local_15_1:  view_distance=15000 (hero local FOW view)
  whole_10:    view_distance=56500 (full overview)
  mini_map:    view_distance=56500
  strategy_map: view_distance=56500
Map boundary reference points (Y=48 for all):
  center1: (-9154, -19950)  center2: (-9235, -20031)
  boundary_up: (-15530, -4727)   boundary_down: (-10971, -21767)
AI config bounds: SIDE_X=37000, SIDE_Z=37000, CORNER_X=30000, CORNER_Z=30000.

--- HERO STAT RANGES ---
  Level: [0, 15]       HP: [0, 20000]       EP: [0, 10000]
  Phy Atk: [130, 2750]  Phy Def: [0, 1360]
  Mgc Atk: [0, 3940]   Mgc Def: [0, 2335]
  Atk Range: [0, 8000]  Money: [300, 16700]
  K/D/A max: 70 / 40 / 75
  Skill1/Skill2 max level: 6. Skill3 (ultimate) max level: 3.
  Cooldown range: [0, 80000] (game ticks).

--- STRUCTURES (organ_list) ---
Each side has 3 structures (SubType: 21=outer tower, 23=inner tower, 24=crystal):
  BLUE Crystal:   ConfigID=106  HP=7000  pos=(-19780, -19780)
  RED Crystal:    ConfigID=107  HP=7000  pos=(19820, 19820)
  BLUE Inner Twr: ConfigID=42   HP=6000  pos=(-37427, -38120)
  RED Inner Twr:  ConfigID=43   HP=6000  pos=(37901, 37844)
  BLUE Outer Twr: ConfigID=1    HP=5000  pos=(-11240, -11228)
  RED Outer Twr:  ConfigID=2    HP=5000  pos=(11285, 11275)
TOWER_ATK_RANGE=70, CRYSTAL_ATK_RANGE=100, HERO_VISUAL_FIELD=100.
Tower protection range (under tower safe zone): ~900. Safe distance from enemy tower: ~15000.
Enemy considered near when within ~180. Friend considered near when within ~150.

--- SOLDIERS ---
Types: normal_soldier, cannon_soldier, super_soldier, dragon_soldier.
Stat ranges: HP [0,12000], ATK [0,700].

--- MONSTERS ---
Types: red_buff, blue_buff, red_bird, bear, cheetah, lizard, river_lizard, baron, zhuzai, black_baron.
Stat ranges: HP [0,20000], ATK [0,800], kill_income [0,105].
Notable IDs: BLUE_BUFF=6010, RED_BUFF=6011, ZHUZHAI=6009, BAOJUN=6012, DARK_BAOJUN=6022.

--- KEY TIMING ---
  TARGET_BORN_FRAME=460     (first minion wave spawns ~frame 460)
  START_PUSH_FRAME=2700     (AI begins pushing)
  START_FOLLOW_FRAME=7200
  MAX_RETURN_CITY_HP=0.9   (recall at 90% HP)
  MAX_RETURN_CITY_EP=0.9   (recall at 90% EP)

--- SPRING ---
  BLUE spring: pos=(-50000,-50000)  RED spring: pos=(50000,50000)
  SPRING_RECOVER_RANGE=10.  FRIEND_TOWER_SAFE_DIST=1300.

--- HERO INFO ---
{hero_info}

=== AVAILABLE SKILLS ===
{skilldoc}

=== EXPERIENCE — OBEY THIS ===
{experience}
WARNING: This experience is verified across multiple games. Trust it. Ignoring it loses the match.

=== FORMAT RULES — YOU MUST OBEY ===
- LANGUAGE: English ONLY. Chinese output = forbidden.
- MARKDOWN: Forbidden. No ** * ` [] # >.
- HEADERS: Exactly === SECTION NAME === (uppercase, spaces around name).
- SUB-HEADERS: Exactly --- Sub Header ---.
- ACTIONS: Exactly @SKILL_CALL SKILL_NAME(params).
- DEVIATION = GAME OVER. These are not suggestions.
"""


EXPERIENCE_WARNING = (
    "Some rules may have few tests, high ratio by chance -- judge carefully.\n"
    "Human guide (HUMANTIC) is reference only, do NOT score it."
)


PROMPT_SYS1_PROTOCOL = """
=== PROTOCOL ===
Remember: FORMAT RULES at the top are mandatory. EXPERIENCE is verified across games.

Analyze the game state and decide.

RULES:
- ENEMY may be OUT OF VISION (camp_visible=false). Show as FOW and position is fake.
- When FOW do NOT trust enemy position for distance calculation.
- All movement and actions MUST go through @SKILL_CALL. Never use raw buttons.
- Each skill does ONE unit function. Chain MULTIPLE skills in a single === ACTION === block to compose complex behavior.
- Skills handle movement, targeting, and cooldowns automatically. You pick the right one.
- All distance values use the same game units. Compare them directly.
- MACRO ACTIONS shows which skills are available or blocked and why.

=== DAMAGE HANDLING ===
Each frame, the system detects TOWER fire or HP loss >50 as damage.
If you are executing a multi-step skill (MOVE_TO, RETREAT, CHASE) and take damage,
the skill will be INTERRUPTED and control returns to you — letting you react.

EXCEPTION: Combat skills (COMBO_STEP, RETREAT, CHASE, KITE, DODGE) are marked CONTINUOUS.
They will NOT be interrupted by damage. Use them when you need uninterrupted execution
(a full combo, a safe retreat, or a determined chase).

One-shot skills (ATTACK, USE_SKILL, POKE, LAST_HIT, CLEAR, WAIT, RECALL) execute
immediately each frame. The system calls them fresh every time.

Output format:
=== THINK ===
  Review: what happened in the last few frames (HP changes, skills used, enemy movement)
  WhatIf check: was the previous frame's WhatIf prediction correct? why or why not?
  Situation: current hero stats, tower status, minion wave, positioning, FOW state
  WhatIf 1: evaluate candidate action 1, predict outcome
  WhatIf 2: evaluate candidate action 2, predict outcome
  Decision: which skill(s) to call and why

=== ACTION ===
  @SKILL_CALL SKILL_NAME()
  @SKILL_CALL SKILL_NAME(param=value)  (params optional)

Every frame matters. Do not skip frames or assume they are identical to the previous one.
Read each frame's Review, DELTA, and state carefully.

=== FEW-SHOT EXAMPLES ===

Example 1 -- Safe farming enemy FOW:
=== THINK ===
  Review: No movement last frame. Minions clashing at center.
  Situation: SELF full HP at blue outer tower. Minions at center. Enemy FOW.
  WhatIf 1: LAST_HIT() -> +40G safe farm, maintain position.
  WhatIf 2: POKE() -> no vision, wasted CD.
  Decision: LAST_HIT() to farm safely.
=== ACTION ===
  @SKILL_CALL LAST_HIT()

Example 2 -- HP advantage chaining two skills:
=== THINK ===
  Review: Last frame poked enemy, lost 15% HP, stayed in lane.
  Situation: SELF 90% vs enemy 60%, both visible, poke off CD.
  WhatIf 1: POKE() to chip, then COMBO_STEP() to capitalize on HP advantage.
  WhatIf 2: LAST_HIT() -> +40G safe but wastes kill window.
  Decision: POKE then COMBO_STEP to pressure kill.
=== ACTION ===
  @SKILL_CALL POKE()
  @SKILL_CALL COMBO_STEP()

Example 3 -- Repositioning under tower:
=== THINK ===
  Review: Enemy pushed wave into my tower. Lost 200HP to minions.
  Situation: SELF low HP 30%. Enemy pushing wave to my tower.
  WhatIf 1: CLEAR() to clear wave under tower, then RETREAT() to safety.
  WhatIf 2: COMBO_STEP() -> suicide, enemy full HP.
  Decision: CLEAR wave then RETREAT to safety.
=== ACTION ===
  @SKILL_CALL CLEAR()
  @SKILL_CALL RETREAT()

All skill docs are above. Call them directly with @SKILL_CALL. DO NOT use raw buttons."""


PROMPT_SYS2_EVENT = ProtocolRenderer(
    header="=== EVENT ANALYZE PROTOCOL ===",
    task="""\
You analyze a specific event from a completed Honor of Kings 1v1 match.
You receive an EVENT with BEFORE (F-100~F) and AFTER (F~F+100) context.
Each frame shows: Review, WhatIf check, Situation, WhatIf 1-2, Decision, Action, DELTA, SELF/ENEMY state.

Examine every frame carefully. Do not skip any.""",
    has_convergence=True,
    examples="""\
=== FEW-SHOT ANALYSIS EXAMPLES ===

Input event KILL @F420:
Output:
  === NEW EPISODIC ===
  --- Case: 20260717_154200 / KILL @F420 ---
    Context: Enemy stayed at 30%HP under RED outer tower instead of recalling.
             SELF identified the window, chipped with POKE() at F400,
             then committed COMBO_STEP() at F410. Enemy had no response.
    Lesson: When enemy is below 30%HP under tower and SELF has ultimate off cooldown,
             poke with POKE() first then COMBO_STEP() for secure kill.

  === NEW SEMANTIC ===
  - enemy below 30%HP under tower + ult up -> POKE then COMBO_STEP

Input event TOWER_FALL @F650:
Output:
  === NEW EPISODIC ===
  --- Case: 20260717_154200 / TOWER_FALL @F650 ---
    Context: Enemy recalled at low HP. SELF pushed wave with LAST_HIT()
             and the minion wave tanked 5 tower hits. Tower fell without SELF tanking aggro.
    Lesson: After enemy recall near tower -> LAST_HIT() to push wave before recalling.

  === NEW SEMANTIC ===
  - after enemy recall near tower -> LAST_HIT to push wave into tower""",
).render()


PROMPT_SYS3_GLOBAL = ProtocolRenderer(
    header="=== GAME REVIEW PROTOCOL ===",
    task="""\
You review a complete Honor of Kings 1v1 match.
You receive the match summary + full frame DETAIL for the entire game.

Examine every frame carefully. Do not skip any.

Focus on broad patterns across the entire match, not individual frames.""",
    has_convergence=True,
    examples="""\
=== FEW-SHOT EXAMPLES ===

Input full match: HouYi vs LuBan7, 5 decisions, 500 frames
Output:
  === NEW EPISODIC ===
  --- Case: game_xxx / GLOBAL @F0 ---
    Context: LLM always chose MOVE_TO without attacking. Enemy got free poke.
    Lesson: When enemy is in range at game start, POKE to establish pressure.

  === NEW SEMANTIC ===
  - enemy visible at game start in attack range -> POKE before advancing""",
).render()


PROMPT_SYS3_PREDICT = ProtocolRenderer(
    header="=== PREDICTION REVIEW PROTOCOL ===",
    task="""\
You review a specific LLM decision from a completed Honor of Kings 1v1 match.
You receive:
  1. BEFORE (F-100~F): context leading to the decision
  2. DECISION: what the LLM chose, and what it predicted would happen
  3. AFTER (F~F+100): what actually happened

Examine every frame carefully. Do not skip any.

Focus on the prediction-vs-reality gap. Was the reasoning sound? Would a different choice have been better?""",
    has_convergence=True,
    examples="""\
=== FEW-SHOT EXAMPLES ===

Input: DECISION @F387, predicted "safe advance" but lost 154HP in 10 frames
Output:
  === NEW EPISODIC ===
  --- Case: game_xxx / PREDICTION @F387 ---
    Context: SELF at full HP, enemy visible at 800 range. LLM predicted MOVE_TO
             would be "safe advance". Actually enemy attacked immediately.
    Lesson: When enemy is in range and visible, don't assume MOVE_TO is safe.
             POKE first to assert pressure, then decide.

  === NEW SEMANTIC ===
  - enemy visible within 1500 range -> POKE before MOVE_TO, don't walk for free""",
).render()


PROMPT_SYS4_ALIGN_PROLOGUE = """
You review a specific LLM decision from a completed Honor of Kings 1v1 match.
The only win condition is destroying the enemy crystal.
Every decision should serve this goal — directly or indirectly.

You receive:
  1. BEFORE (F-100~F): context
  2. DECISION: what was chosen, what alternatives existed
  3. AFTER (F~F+100): what happened

Analyze:

Step 1 — SHORT-TERM GOAL: What was the immediate objective at this moment?
(e.g. "secure last-hit gold", "avoid tower damage", "push wave",
 "create kill pressure", "survive", "reset position", "secure vision")

Step 2 — LONG-TERM GOAL: Does the short-term goal serve destroying the
enemy crystal? If not, the decision is misaligned.

Step 3 — ALIGNMENT EVALUATION: Was the chosen action the best option?
If not, which WhatIf alternative would have been better?

The primary goal of this analysis is to generate actionable memories.
Output NEW EPISODIC/NEW SEMANTIC when the alignment gap reveals a reusable lesson.
REFERENCE existing patterns if already covered."""

PROMPT_SYS4_ALIGN_EXTRA = """\
Output format:
  === SHORT-TERM GOAL ===
  {one-line description}

  === ALIGNMENT ANALYSIS ===
  {explanation}"""

PROMPT_SYS4_ALIGN = ProtocolRenderer(
    header="=== GOAL ALIGNMENT REVIEW PROTOCOL ===",
    task=PROMPT_SYS4_ALIGN_PROLOGUE,
    has_convergence=True,
    extra_format=PROMPT_SYS4_ALIGN_EXTRA,
    examples="""\
=== FEW-SHOT EXAMPLES ===

Input: DECISION @F387, enemy at 800 range, full HP both sides.
       Chose MOVE_TO, predicted "safe". Lost 154HP.
Output:
  === SHORT-TERM GOAL ===
  Advance toward lane to farm minions.

  === ALIGNMENT ANALYSIS ===
  MOVE_TO alone is misaligned. Walking toward enemy without attacking
  gives them free damage. The short-term goal should have been
  "establish lane control" via POKE or ATTACK. Better choice was POKE.

  === NEW EPISODIC ===
  --- Case: game_xxx / ALIGNMENT @F387 ---
    Context: SELF full HP, enemy visible. Chose MOVE_TO to advance,
             but lost HP for free. Goal should have been pressure, not travel.
    Lesson: When enemy is visible and in range, POKE to establish pressure
             instead of walking forward passively.

  === NEW SEMANTIC ===
  - enemy visible within attack range and full HP -> POKE to assert lane control""",
).render()


PROMPT_SYS4_GLOBAL = ProtocolRenderer(
    header="=== GLOBAL GOAL ALIGNMENT REVIEW PROTOCOL ===",
    task="""\
You review a complete Honor of Kings 1v1 match against the only win condition:
destroy the enemy crystal.

You receive the match summary + full frame DETAIL.

The primary goal of this analysis is to generate actionable memories.
Output NEW EPISODIC or NEW SEMANTIC when you find a reusable lesson.
REFERENCE existing patterns if already covered.

Analyze the overall pattern of decisions:
  - What was the most common short-term goal?
  - Did decisions consistently serve the long-term goal (destroy crystal)?
  - What is the single biggest misalignment across the entire match?

Output the most important alignment issue only:""",
    has_convergence=True,
    extra_format="""\
Output format:
  === SHORT-TERM GOAL PATTERN ===
  {one-line summary of what the LLM most often tried to do}

  === KEY MISALIGNMENT ===
  {description of the biggest goal gap across the match}""",
    examples="""\
=== FEW-SHOT EXAMPLES ===

Input: 5 decisions, all MOVE_TO. Never attacked. Lost 154HP.
Output:
  === SHORT-TERM GOAL PATTERN ===
  Move toward lane, never engage.

  === KEY MISALIGNMENT ===
  All decisions focused on positioning. No offensive actions taken.
  The goal "destroy enemy crystal" requires dealing damage, not just walking.

  === NEW EPISODIC ===
  --- Case: game_xxx / GLOBAL_ALIGN @F0 ---
    Context: Entire match was walking. No poke, no attack, no pressure.
    Lesson: MOVE_TO alone does not win games. Must combine with POKE or ATTACK.

  === NEW SEMANTIC ===
  - early game when enemy visible -> POKE or ATTACK, don't just MOVE_TO""",
).render()


PROMPT_AUDIT = """
=== EXPERIENCE AUDIT PROTOCOL ===
Remember: FORMAT RULES at the top are mandatory. EXPERIENCE is verified across games.

You audit existing game experience against a completed match.
You receive:
  1. MATCH + TRENDS + DETAIL (full game)
  2. DB EXPERIENCE (existing rules in database)
  3. BUFFER EXPERIENCE (candidates from analysis, sources unknown)

Score definitions:
  1  = this game validates the rule or case (the pattern held true)
  -1 = this game contradicts the rule or case (the pattern failed)
  0  = this game does not test this item (pattern did not appear)

Each score must include a brief reason.
For EVERY item in DB EXPERIENCE and BUFFER EXPERIENCE you MUST output a score.

Output format:
  === DB EXPERIENCE SCORES ===  (one block for all DB items)
    For episodic Case: repeat the --- Case: --- as shown, then Score: N + Score reason:
    For semantic rule: repeat the - rule text as shown, then Score: N + Score reason:

  === BUFFER EXPERIENCE SCORES ===  (one block for all BUFFER items)
    Same format as DB section.

=== FEW-SHOT EXAMPLES ===

Input DB items:
--- Case: 20260715_110300 / KILL @F320 ---
  Context: enemy overstayed at 30%, SELF combo killed
  Lesson: enemy below 30%HP -> COMBO_STEP
- HP below 30% -> call RETREAT to fall back

Output:
=== DB EXPERIENCE SCORES ===
--- Case: 20260715_110300 / KILL @F320 ---
  Context: enemy overstayed at 30%, SELF combo killed
  Lesson: enemy below 30%HP -> COMBO_STEP
Score: 1
Score reason: F420 confirmed the pattern.

- HP below 30% -> call RETREAT to fall back
Score: 1
Score reason: Low HP retreat is always correct.

Input BUFFER items:
--- Case: 20260717_154200 / KILL @F420 ---
  Context: enemy 30%HP, POKE then COMBO_STEP
  Lesson: POKE first then COMBO_STEP when enemy low
- enemy HP < 20% and ult up -> COMBO_STEP directly

Output:
=== BUFFER EXPERIENCE SCORES ===
--- Case: 20260717_154200 / KILL @F420 ---
  Context: enemy 30%HP, POKE then COMBO_STEP
  Lesson: POKE first then COMBO_STEP when enemy low
Score: -1
Score reason: Contradicts DB which says COMBO_STEP directly (validated 3/4).

- enemy HP < 20% and ult up -> COMBO_STEP directly
Score: 1
Score reason: This game confirms direct combo is better.
"""


def build_full_prompt(self_hero_id, enemy_hero_id, extra_proto, experience=None):
    """Build the full PROMPT_BASE with hero_info, skilldoc, and experience filled in."""
    import gamecore_data as gc
    from skill_base import SKILL_REGISTRY
    from skill_db import get_matchup

    self_name = gc.get_hero_en_name(self_hero_id)
    enemy_name = gc.get_hero_en_name(enemy_hero_id)
    self_type = gc.get_hero_role(self_hero_id)
    enemy_type = gc.get_hero_role(enemy_hero_id)

    def _fmt_skills(hid, name, role):
        lines = [f"  {name} ({role})"]
        skills = gc.get_hero_skill_info(hid)
        if not skills:
            lines.append("    (no detailed skill data from gamecore)")
        for slot in [1, 2, 3]:
            s = skills.get(slot)
            if s:
                lines.append(f"    S{slot}: range={s['range']} shape={s['shape']} aim={s['release']} ep={s['ep_cost']}")
        return "\n".join(lines)

    hero_info_lines = [_fmt_skills(self_hero_id, self_name, self_type), "", _fmt_skills(enemy_hero_id, enemy_name, enemy_type)]
    mu = get_matchup(self_hero_id, enemy_hero_id)
    if mu:
        hero_info_lines.append("")
        hero_info_lines.append("  Matchup:")
        for k in ["summary", "advantage", "danger", "tip_offense", "tip_defense", "power_spike", "key_skill"]:
            if k in mu:
                hero_info_lines.append(f"    {k}: {mu[k]}")
    hero_info = "\n".join(hero_info_lines)

    skilldoc_lines = []
    for sk_name in sorted(SKILL_REGISTRY.keys()):
        sk = SKILL_REGISTRY[sk_name]
        skilldoc_lines.append(sk.get_doc())
    skilldoc = "\n\n".join(skilldoc_lines)

    if experience is None:
        exp = "(no prior experience)\n\n" + EXPERIENCE_WARNING
    else:
        exp = experience + "\n\n" + EXPERIENCE_WARNING

    return PROMPT_BASE.format(
        self_name=self_name, enemy_name=enemy_name,
        self_type=self_type, enemy_type=enemy_type,
        self_hero_id=self_hero_id, enemy_hero_id=enemy_hero_id,
        skilldoc=skilldoc, hero_info=hero_info, experience=exp,
    ) + extra_proto

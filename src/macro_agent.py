import re, os, json, time, collections
from openai import OpenAI
from hero_db import hero_name
from state_parser import parse_state, compress_state
from strategy_executor import ProtocolExecutor
from skill_db import get_matchup
from skill_base import SKILL_REGISTRY

from trajectory import TRAJECTORY_DIR
traj_file = None
traj_path = os.path.join(TRAJECTORY_DIR, f"trajectory_{int(time.time())}.jsonl")

SYSTEM_PROMPT = """You control {self_name}({self_type}) vs {enemy_name}({enemy_type}) in Honor of Kings 1v1.

=== GAME RULES ===
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
Enemy considered "near" when within ~180. Friend considered "near" when within ~150.

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

=== MACRO SKILLS (read docs, then call sub_functions) ===
{skilldoc}

=== PROTOCOL (each frame output) ===
You have the full game state above. Analyze and decide.

RULES:
- ENEMY may be OUT OF VISION (camp_visible=false). Their HP shows as FOW and position is fake (e.g. 100000,100000).
- When FOW, DO NOT trust enemy position for distance calculation — it is a placeholder, not actual location.
- All your movement and actions MUST go through @SKILL_CALL. Never use raw Move/Attack/Skill buttons.
- You can call MULTIPLE sub-functions in a single <action> block. They execute in order.
- Each skill sub-function handles movement, positioning, and cooldowns automatically.
- If you want to change macro behavior, call a different skill's sub-function.
- All distance values (Range, Pos, tower coordinates) use the same game units. Compare them directly.

First output <think> </think>:
  - Situation: hero stats, tower status, minion wave, positioning, FOW state
  - WhatIf: evaluate 2 candidate actions, predict outcomes
  - Decision: which skill(s) to call and why

Then output <action> </action>:
  One or more @SKILL_CALL lines, executed in order.

=== FEW-SHOT EXAMPLES ===

Example 1 — Safe farming, enemy FOW (position is fake):
  <think>
  Situation: SELF full HP at blue outer tower, minions at lane center, enemy shows FOW at (100000,100000). This position is NOT real — enemy location unknown.
  WhatIf 1: FARM.last_hit → safe gold while maintaining position.
  WhatIf 2: POKE.aim_skill → no enemy vision, wasted CD.
  Decision: FARM.last_hit to secure farm while keeping safe distance.
  </think>
  <action>
  @SKILL_CALL FARM.last_hit()
  </action>

Example 2 — Enemy visible, HP advantage, chaining two skills:
  <think>
  Situation: SELF 90% HP vs enemy 60% HP at lane center, both visible. Poke skill off CD.
  WhatIf 1: POKE.aim_skill → chip damage, then ALL_IN.basic_attack to pressure.
  WhatIf 2: FARM.last_hit → safe but wastes kill window.
  Decision: Chain POKE into ALL_IN to capitalize on HP advantage.
  </think>
  <action>
  @SKILL_CALL POKE.aim_skill()
  @SKILL_CALL ALL_IN.basic_attack()
  </action>

Example 3 — Repositioning under tower:
  <think>
  Situation: SELF low HP (30%), enemy pushing wave to my tower. Need to recall.
  WhatIf 1: FARM.retreat_to_tower → safe recall under tower.
  WhatIf 2: ALL_IN.chase → suicide, enemy has full HP.
  Decision: Retreat to tower, then recall.
  </think>
  <action>
  @SKILL_CALL FARM.retreat_to_tower()
  </action>

All macro skill docs are listed above. Call them directly — no need to open docs first.
DO NOT use @TOOL or raw buttons. @SKILL_CALL only."""

class MacroAgent:
    def __init__(self, name, self_hero_id, enemy_hero_id, api_key=None, base_url=None, model=None):
        self.name = name
        self.self_hero_id = self_hero_id
        self.enemy_hero_id = enemy_hero_id
        self.executor = ProtocolExecutor(self_hero_id)
        api_key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        base_url = base_url or os.environ.get("DASHSCOPE_BASE_URL", "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
        model = model or os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = model
        self.history = collections.deque(maxlen=100)
        self.last_action_result = ""
        self.last_results_full = []
        self.last_thought = ""
        self._prev_frame = None
        self._prev_pb = None
        self._prev_pb_10 = None
        self.state_changes_str = ""
        self._call_count = 0
        global traj_file, traj_path
        if not traj_file:
            traj_file = open(traj_path, "w", encoding="utf-8")

        import gamecore_data as gc

        self_name = gc.get_hero_en_name(self_hero_id)
        enemy_name = gc.get_hero_en_name(enemy_hero_id)
        self_type = gc.get_hero_role(self_hero_id)
        enemy_type = gc.get_hero_role(enemy_hero_id)

        def format_hero_skills(hid, name, role):
            lines = [f"  {name} ({role})"]
            skills = gc.get_hero_skill_info(hid)
            if not skills:
                lines.append("    (no detailed skill data from gamecore)")
            for slot in [1, 2, 3]:
                s = skills.get(slot)
                if s:
                    lines.append(f"    S{slot}: range={s['range']} shape={s['shape']} aim={s['release']} ep={s['ep_cost']}")
            return "\n".join(lines)

        hero_info_lines = [format_hero_skills(self_hero_id, self_name, self_type)]
        hero_info_lines.append("")
        hero_info_lines.append(format_hero_skills(enemy_hero_id, enemy_name, enemy_type))

        mu = get_matchup(self_hero_id, self.enemy_hero_id)
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
            doc = sk.get_doc()
            skilldoc_lines.append(doc)
        skilldoc = "\n\n".join(skilldoc_lines)

        self.system_prompt = SYSTEM_PROMPT.format(
            self_name=self_name, enemy_name=enemy_name,
            self_type=self_type, enemy_type=enemy_type,
            self_hero_id=self_hero_id, enemy_hero_id=enemy_hero_id,
            skilldoc=skilldoc,
            hero_info=hero_info,
        )

    def decide(self, info):
        s = info[0] if isinstance(info, list) else info
        state_text, _ = parse_state(s, self.self_hero_id)

        if not self.client:
            return (2, 8, 8, 8, 8, 0), "[fallback]"

        history_lines = []
        for i, entry in enumerate(self.history):
            f = entry.get('frame', 0)
            t = f * 0.033
            history_lines.append(f"[Call {i+1} | Frame {f} | T+{t:.1f}s]")
            snap = entry.get('snapshot', '')
            if snap:
                history_lines.append(f"  State: {snap}")
            raw = entry.get('raw', '')
            if raw:
                for line in raw.strip().split("\n"):
                    history_lines.append(f"  {line}")
            history_lines.append("")
        mem_text = "\n".join(history_lines) if history_lines else "(game start, no prior calls)"

        user_msg = f"=== MEMORY (last {len(self.history)} calls) ===\n{mem_text}\n\n{state_text}"
        if self.state_changes_str:
            user_msg += f"\n\n=== STATE CHANGES ===\n{self.state_changes_str}"
        if self.last_results_full:
            results_str = "\n".join(self.last_results_full)
            user_msg += f"\n\n=== LAST RESULTS ===\n{results_str}"
        else:
            user_msg += "\n\n=== LAST RESULTS ===\n(No Skill Called)"

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_msg},
        ]

        try:
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages,
                temperature=0.7, max_tokens=400, top_p=1,
            )
            msg = resp.choices[0].message
            content = (msg.content or "").strip()
            # extract think block for memory, strip from action
            think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            self.last_thought = think_match.group(1).strip() if think_match else ""
            reply = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
            reply = reply.strip()
            if not reply:
                reply = (getattr(msg, "reasoning_content", None) or "").strip()
                self.last_thought = reply
        except Exception:
            return (2, 8, 8, 8, 8, 0), "[LLM err]"

        global traj_file

        results = self.executor.process_batch(s, reply)
        self.last_results_full = []
        for r in results:
            if r["type"] == "skill_call":
                result = r.get("result", {})
                if isinstance(result, dict):
                    lines = [f"@SKILL_CALL {r['skill']}.{r['func']}()"]
                    for k, v in result.items():
                        lines.append(f"  {k}: {v}")
                    self.last_results_full.append("\n".join(lines))
                else:
                    self.last_results_full.append(f"@SKILL_CALL {r['skill']}.{r['func']}() → {result}")
            elif r["type"] == "error":
                self.last_results_full.append(f"ERROR: {r['msg']}")
            elif r["type"] == "tool":
                self.last_results_full.append(f"@TOOL {r['name']} → {r['result']}")
            elif r["type"] == "skill_open":
                self.last_results_full.append(f"@SKILL_OPEN {r['name']} → doc opened")

        raw_output = ""
        if self.last_thought:
            raw_output += f"<think>\n{self.last_thought}\n</think>"
        if reply:
            raw_output += f"\n<action>\n{reply}\n</action>"

        pb_curr = s.get("req_pb")
        frame_no = getattr(pb_curr, 'frame_no', 0) if pb_curr else 0

        self.history.append({
            "frame": frame_no,
            "snapshot": compress_state(pb_curr, self.self_hero_id) if pb_curr else "",
            "raw": raw_output.strip(),
            "action": self.last_results_full[0] if self.last_results_full else "none",
        })

        state_changes = []
        self._call_count += 1
        ref_pb = self._prev_pb_10 if self._prev_pb_10 is not None else self._prev_pb
        if self._prev_frame is not None and ref_pb is not None and pb_curr is not None:
            def get_hp(pb, cid):
                for h in getattr(pb, 'hero_list', []):
                    if getattr(h, 'config_id', 0) == cid:
                        return getattr(h, 'hp', 0), getattr(h, 'max_hp', 1), getattr(h, 'money', 0), getattr(h, 'level', 1)
                return None, None, None, None
            for tag, cid in [("SELF", self.self_hero_id), ("ENEMY", self.enemy_hero_id)]:
                chp, cmhp, cg, clv = get_hp(pb_curr, cid)
                php, pmhp, pg, plv = get_hp(ref_pb, cid)
                if None not in (chp, php):
                    hp_diff = chp - php
                    g_diff = cg - pg
                    l_diff = clv - plv
                    parts = []
                    if hp_diff != 0:
                        parts.append(f"HP {chp}/{cmhp}({'+' if hp_diff>0 else ''}{hp_diff})")
                    if g_diff != 0:
                        parts.append(f"Gold {cg}({'+' if g_diff>0 else ''}{g_diff})")
                    if l_diff != 0:
                        parts.append(f"LV {clv}")
                    if parts:
                        state_changes.append(f"  {tag}: {' | '.join(parts)}")
            def tower_hp(pb, cid):
                for o in getattr(pb, 'organ_list', []):
                    if getattr(o, 'ConfigID', 0) == cid:
                        return getattr(o, 'Hp', 0), getattr(o, 'MaxHp', 0)
                return None, None
            for label, ocid in [("RED outer", 2), ("RED crystal", 107), ("BLUE outer", 1), ("BLUE crystal", 106)]:
                chp, cmhp = tower_hp(pb_curr, ocid)
                php, pmhp = tower_hp(ref_pb, ocid)
                if None not in (chp, php) and chp != php:
                    state_changes.append(f"  {label}: HP {chp}/{cmhp}({chp - php:+.0f})")
        self.state_changes_str = "\n".join(state_changes) if state_changes else ""

        # update snapshot for next STATE CHANGES comparison (every 10 calls)
        if self._call_count % 10 == 0:
            self._prev_pb_10 = pb_curr
        self._prev_frame = frame_no
        self._prev_pb = pb_curr

        if traj_file:
            traj_file.write(json.dumps({
                "step": str(time.time()),
                "system_prompt": self.system_prompt,
                "user_msg": user_msg,
                "llm_reply": reply,
                "parsed_results": "\n".join(self.last_results_full),
            }, ensure_ascii=False) + "\n")
            traj_file.flush()
        action, _ = self.executor.step(s)
        return action, f"batch: {reply[:80]}"

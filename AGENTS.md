# HOK (Honor of Kings AI)

THU AI实践基石 — LLM Agent 玩王者荣耀 1v1。纯 prompt 工程，零训练成本。
架构基于 TiG (Think-in-Games) + WIA (What-If Analysis) 论文思想。

## Quick Commands

```bash
python trajectories/serve.py [port]       # Trajectory replay browser (default :23456)
```

Docker entrypoints: `python src/main.py` or `python src/main_macro.py --steps 100` (inside container).

## Setup

**Dependencies:** `pip install openai fastapi uvicorn numpy python-dotenv`

**`.env`:**
```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```

## Prompt Architecture

### SYSTEM PROMPT (`macro_agent.py:SYSTEM_PROMPT`)

Static template, runtime-injected with `{hero_info}` + `{skilldoc}`.

```
You control {self_name}({self_type}) vs {enemy_name}({enemy_type}) in Honor of Kings 1v1.

=== GAME RULES ===
  GAME MODE — scene, camps, skill slots, cooldown ranges
  MAP CONFIG — length, center, coordinate bounds, view distances, reference points
  HERO STAT RANGES — Level/HP/EP/ATK/DEF/Range/Money/KDA limits from hero_min_max.txt
  STRUCTURES — 6 towers/crystals with exact ConfigID/HP/positions from simulator JSON
  SOLDIERS — types from soldier.txt, stat ranges from vec_soldier_config
  MONSTERS — types, IDs from para_conf.txt, stat ranges from vec_feature_monster
  KEY TIMING — TARGET_BORN_FRAME=460, START_PUSH_FRAME=2700, etc. from para_conf.txt
  SPRING — positions and recover range from para_conf.txt
  HERO INFO — {hero_info} injected at init (both heroes' skills from gamecore_data)

=== MACRO SKILLS ===
  {skilldoc} — full docs (description/when/until/sub_functions) from SKILL_REGISTRY

=== PROTOCOL (each frame output) ===
  <think> Situation + WhatIf + Decision </think>
  <action> @SKILL_CALL <SKILL>.<func>() </action>
  Rules: FOW emphasis, no raw buttons, multi-call allowed, no @TOOL
  FEW-SHOT EXAMPLES: 3 examples (FOW farm / chain skills / tower retreat)
```

### USER PROMPT (built in `macro_agent.py:decide()`)

Per-frame dynamic prompt:

```
=== MEMORY (last 100 calls) ===
[Call N | Frame {n} | T+{t}s]
  State: {compress_state() one-liner}
  <think>{raw LLM thought}</think>
  <action>{raw LLM action}</action>

=== FRAME {n} (T+{t}s) ===
--- HEROES ---
[SELF] ... HP/EP/Gold ATK/DEF/Range/Spd Pos Skill CD
[ENEMY] ... HP(FOW)/EP/Gold ATK/DEF/Range/Spd Pos
--- TOWERS --- BLUE/RED: outer/inner/crystal HP + positions
--- MINIONS --- {N} visible ({side} side)
--- MONSTERS --- {N} visible
--- LEGAL ACTIONS --- {Move, Skill2, ...}
--- DISTANCES --- To enemy / To nearest enemy tower / To nearest minion

=== STATE CHANGES ===              (diff against 10-calls-ago snapshot)
  SELF: HP 2850/3050(-200) Gold 250(+60)
  RED outer: HP 4800/5000(-200)

=== LAST RESULTS ===
@SKILL_CALL FARM.last_hit()
  action: last_hit           (structured dict return from skill func)
  status: success
  detail: attacked nearest minion
```

## Gamecore Data Sources (no src/ files trusted)

All SYS data comes from `gamecore/` config files, verified by inspection:

| Gamecore File | Data Used |
|---------------|-----------|
| `simulator_output/*.json` | Tower positions, HP, ConfigID, SubType |
| `para_conf.txt` | TARGET_BORN_FRAME, START_PUSH_FRAME, TOWER_ATK_RANGE, SPRING pos, SKILL_SLOT_NUM, monster IDs |
| `hero_min_max.txt` | Hero stat ranges (HP/EP/ATK/DEF/Level/Money/KDA/cooldown) |
| `vec_soldier_config.txt` | Soldier coordinate/HP/ATK ranges |
| `vec_feature_organ.txt` | Organ HP/ATK/range/kill_income ranges |
| `vec_feature_monster.txt` | Monster types and stat ranges |
| `map_info.txt` | 4 view types, distances, reference points, map_length=113000 |
| `soldier.txt` | Soldier type IDs |
| `scene.json` | 1v1 mode |
| `hero_main_job.txt` | Hero role (tank/soldier/assassin/wizard/shooter/suport) |
| `hero_skill_info.txt` | Hero skill ranges, shapes, release types, EP costs |
| `skill_ep_consume.txt` | EP cost per skill ID |

## Agent Implementations

| File | Protocol | Notes |
|------|----------|-------|
| `macro_agent.py` | `<think>` + `<action>` / `@SKILL_CALL` | **Main agent.** SYS from gamecore, USER with MEMORY/STATE_CHANGES |
| `gamecore_data.py` | Data provider | Reads gamecore config files, provides English hero names/skills/roles |
| `state_parser.py` | Protobuf → text | Full state + towers + minions + monsters + distances + skill CDs |
| `strategy_executor.py` | `@SKILL_CALL` → 6-tuple | Parses LLM action, executes skill sub-functions |
| `skills/*.py` | `@register_skill` | FARM, POKE, ALL_IN — each returns structured `dict` |
| `skill_base.py` | Base class | `SKILL_REGISTRY`, `get_doc()`, `execute()` |
| `main.py` | FinalAction | Docker entrypoint, reads env |
| `main_macro.py` | MacroAgent + argparse | Docker entrypoint, reads env |

## Key Design Decisions

### LLM-Executor Separation
- LLM: strategic layer, outputs `<think>` (WhatIf analysis) + `<action>` (`@SKILL_CALL`)
- Executor: tactical layer, converts skill calls to 6-tuple actions, handles pathfinding/combos
- LLM never calls `@TOOL` — all game state is in the USER prompt
- Multiple `@SKILL_CALL` lines allowed in one `<action>` block

### Skill System
- Skills registered via `@register_skill` decorator in `src/skills/*.py`
- `SKILL_REGISTRY` from `skill_base` (3 skills: FARM, POKE, ALL_IN)
- Each skill sub-function returns a structured `dict`: `{action, status, detail, ...}`
- Full docs injected into SYS via `get_doc()` — LLM never needs `@SKILL_OPEN`

### MEMORY
- Rolling window of last 100 LLM calls
- Each entry: frame number, compressed state snapshot, raw `<think>` + `<action>` output
- Shown in USER prompt as `=== MEMORY (last N calls) ===`

### STATE CHANGES
- Captured every 10 frames by comparing against a snapshot protobuf
- Shows HP/Gold/Level changes and tower damage
- Gives statistically meaningful deltas instead of single-frame noise

### Skill Cooldowns
- Read from `hero.skill[i].cooldown` / `cooldown_max` (Skill objects in protobuf)
- Displayed as `S1(2.3s/9.0s)` in state
- Formatted as `cd/1000` seconds (cooldown unit: game ticks, ~33ms each)

## Action Format

`(button:0-11, move_x:1-15, move_z:1-15, skill_x:1-15, skill_z:1-15, target:0-7)`

**All 4 coords must be 1-15** (0 triggers illegal action warning).

legal_action flat array: `[12 buttons][16×4 coords][12×8 targets]`
```python
offset = 12 + 16*4  # 76
target_mask = legal_action[offset + btn*8 : offset + btn*8 + 8]
```

## Map Coordinates (Gamecore-Verified)

- 1v1 map, lane along X axis
- Blue (camp=0) at -X, Red (camp=1) at +X
- Toward own base = -X, toward enemy base = +X (for BLUE)
- Blue spawn X≈-32308, Red spawn X≈+100000
- `.x`/`.y` for ground coordinates; `.z` is height (unused)

## War Fog

- `camp_visible[player_index] == false` → enemy HP shows as `FOW`, position is fake placeholder
- When FOW, do NOT trust enemy position for distance calculation
- Minions outside vision are also hidden (shown as `Minions: 0(FOW)`)

## Known Code Traps

- **Skill cooldown field**: `hero.skill[i].cooldown` (not `skill_cd_1`). Bad field names silently default to 0, so LLM always sees `S1(0.0s/0.0s)`.

## Gamecore Deployment (Docker)

```
Windows                          Docker (tencentailab/hok_env:latest)
gamecore-server.exe :23432 ──HTTP──→ Python SDK + Agent
sgame_simulator       ←──ZMQ :35500─
```

**Working directory must be `/hok_env/hok/hok1v1`** — SDK's config.dat resolves relatively.

**Ports**: `-p HOST_PORT:CONTAINER_PORT`, same port both sides. No `--network host`.

**Start/stop:**
```powershell
taskkill /f /im gamecore-server.exe && taskkill /f /im sgame_simulator_remote_zmq.exe
docker start hok
```

**AILab stubs**: `main.py`/`main_macro.py` create 11 inline stubs. `fix_ailab.py` (11) and `setup_ailab.py` (40+) for after container rebuild.

**Do NOT `docker rm -f hok`** — rebuilding re-installs all dependencies + AILab files.

## Trajectory Viewer

```bash
python trajectories/serve.py        # localhost:23456
python trajectories/serve.py 8080   # custom port
```

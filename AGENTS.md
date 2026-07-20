# HOK — Honor of Kings LLM Agent

THU AI实践基石. LLM Agent 玩王者荣耀 1v1. 纯 prompt 工程, 零训练.

## Entrypoints

| Priority | File | Role |
|----------|------|------|
| 1 | `src/main_macro.py` | **Active.** MacroAgent + MemorySystem + strategy executor, runs in Docker |
| `start.bat` | Convenience: starts gamecore-server then runs agent in container |

`src_v2/` has been removed from the repo (archived). The old `src/main.py`, `agent.py`, `react_agent.py`, `mock_env.py`, `web_demo.py` no longer exist — replaced by the macro_agent architecture in `src/`. README is stale and documents the old v1 code.

## Source Layout

```
src/                              # Git-tracked, gamecore-Docker version
  main_macro.py                   # Entrypoint (MacroAgent + post-game reflect)
  macro_agent.py                  # SYS1: frame-by-frame LLM decide(), builds TRENDS/DETAIL/DELTA memory
  memory.py                       # MemorySystem: retrieve() + reflect() (SYS2→SYS3→AUDIT pipeline)
  prompts.py                      # PROMPT_BASE + 4 protocols + build_full_prompt()
  state_parser.py                 # Protobuf → text state + MACRO ACTIONS (AVAILABLE/BLOCKED)
  strategy_executor.py            # @SKILL_CALL parser → 6-tuple, routes to skills_concrete.py
  skills_concrete.py              # Multi-frame concrete skills (Farm/Poke/AllIn/Kite/Defend/Retreat/Pursue/MoveTo/AttackTarget/Recall/UseSkill)
  skills/                         # @register_skill doc-only (generated into PROMPT skilldoc)
  skill_base.py                   # SKILL_REGISTRY + @register_skill decorator
  hero_db.py                      # Hero ID → Chinese name mapping
  hero_skills.py                  # Per-hero config (poke/combo/escape/items). Only 5 heroes defined: 132, 169, 199, 141, 107
  skill_db.py                     # HUMANTIC matchup + combo/wave/positioning rules
  gamecore_data.py                # Reads gamecore config files at runtime (hero_skill_info.txt, equipment_config_id.txt, etc.)
  pathfinding.py                  # A* pathfinding (used by make_move_to())
  trajectory.py                   # JSONL step logger
tests/                            # Standalone test scripts (need gamecore-server + SDK running). No test framework.
  test_*.py                       # Some are .gitignored (test_agent, test_final_OK, test_full_flow, test_minimal, test_reset)
scripts/                          # Setup scripts, AILab stubs, seed_memory.py
  setup_ailab.py, fix_ailab.py    # Run after container rebuild to create AILab stub files
  seed_memory.py                  # Seeds memory.json with initial 14 SEMANTIC rules (loaded after first game)
trajectories/                     # Per-game .jsonl logs + memory.json + serve.py + index.html + screenshot
  serve.py                        # Trajectory browser: python serve.py <port> (e.g. 23456)
  memory.json                     # MemorySystem persistent store (auto-loaded/saved)
gamecore/                         # Gitignored. gamecore-server.exe (proprietary)
src_copy/                         # Backup dir (not git-tracked). Mix of old v1 + new macro_agent files
```

## Dependencies

No package manager. Install manually:
```
pip install openai fastapi uvicorn numpy python-dotenv
```

## Commands (Docker)

```powershell
# Start gamecore (Windows host, CWD = gamecore\gamecore)
Start-Process -WindowStyle Hidden -FilePath "gamecore\gamecore\gamecore-server.exe" "server","--server-address :23432" -WorkingDirectory "HOK\gamecore\gamecore"

# Run agent in container
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py --decisions 10 --hero-ai 199 --hero-bot 169"

# Options: --max-tokens 4096 (default 2048), --no-thinking (disable reasoning), --print-every N
# Example: python3 -u /workspace/src/main_macro.py --decisions 10 --hero-ai 169 --hero-bot 112 --max-tokens 4096 --no-thinking

# Trajectory browser
python trajectories/serve.py 23456

# Stop (zombie ZMQ ports may block restart; kill leftover python in container)
taskkill /f /im gamecore-server.exe && docker stop hok
```

Do NOT `docker rm -f hok` (rebuilding re-installs all deps + AILab files). Use `docker stop` / `docker start`.

## `.env` Required

```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```

Current `.env` uses `token-plan` (internal proxy), not raw DashScope URL. Do NOT change to the public DashScope endpoint.

## Architecture

```
Game Environment (Windows Host + Docker Container)
  ├─ gamecore-server.exe ←HTTP:23432/ZMQ:35500→ Docker (HoK SDK)
  │
  ├─ [Ingame Loop - every frame]
  │   Game State → SYS1: MacroAgent → <think 5-sections> + <action @SKILL_CALL>
  │     → Strategy Executor → 6-tuple (btn, mx, my, sx, sy, target) → gamecore
  │   LLM NEVER directly touches gamecore (safety abstraction).
  │
  ├─ Trajectory JSONL → Event Detection
  │   events: kill / death / tower_fall / gold_spike / power_spike / minion_wave
  │
  ├─ [Post-game × per event] → SYS2: Event Analysis (BEFORE/AFTER 100 frames) → BUFFER
  ├─ [Post-game × once]      → SYS3: Game Review (full match)              → BUFFER
  └─ [Post-game × once]      → AUDIT: score DB + BUFFER (1/-1/0)
       → Score=1 → Similarity Check → DB (memory.json)
       → Score=0/-1 → DISCARD
```

Memory System (Episodic + Semantic + Humanic) feeds into SYS1 via `retrieve()`.

Prompt assembly: `PROMPT_BASE + EXPERIENCE + PROTOCOL + TRENDS + EVENTS + DETAIL + MACRO_ACTIONS + few-shot`

`<think>` has 5 sections: **Review / WhatIf check / Situation / WhatIf 1-2 / Decision**.
`MACRO_ACTIONS` lists which sub-functions are **AVAILABLE** vs **BLOCKED** (with reasons like cooldown/range/FOW).

SYS2/SYS3: not required to output. When they do: `REFERENCE EPISODIC` / `NEW EPISODIC (Case: Context+Lesson)` / `REFERENCE SEMANTIC` / `NEW SEMANTIC`.

AUDIT scores: `1` (validates), `-1` (contradicts), `0` (not tested). Each score needs a reason. HUMANTIC entries are reference only and never scored.

## Skill System

- `skills/__init__.py` auto-discovers via `pkgutil.iter_modules`. New skill = create `skills/x.py` with `@register_skill` class.
- `@SKILL_CALL Skill.func()` parser in `strategy_executor.py`. Routes to `skills_concrete.py` (multi-frame execution).
- `skills/` files are **doc-only** (generated into PROMPT skilldoc via `@register_skill`). Execution goes to `skills_concrete.py`.
- `skills_concrete.py`: Multi-frame concrete skills with `_start()` + `update()` → `(action, done)`. LLM calls once, executor loops until `done`.
- `SkillContext` (helpers: `make_move`, `make_attack`, `make_skill`, `valid_btn`, `dist_to_enemy`, `nearest_low_hp_minion`) initialized from protobuf each frame.
- Per-hero skill config in `hero_skills.py` (`poke_skill`, `combo_priority`, `skill_ranges`, `skill_types`, `items`). Only heroes **132, 169, 199, 141, 107** have custom configs; others use default fallback.
- A* pathfinding in `SkillContext.make_move_to()` avoids organ obstacles.

## Memory System

- File: `trajectories/memory.json` (auto-loaded/saved by MemorySystem)
- Three tiers: Working (2000-frame frame_buffer in MacroAgent), EPISODIC (per-event cases), SEMANTIC (reusable rules)
- `retrieve()` → HUMANTIC + top-5 EPISODIC + top-10 SEMANTIC by support ratio. Also returns generic (hero_ai=None) memories.
- `reflect()` detects events from trajectory JSONL: kill, death, gold_spike, tower_fall, minion_wave
- **Dedup**: 3-layer field matching (normalize → condition prefix → structured {skill, action, domain, op, val})
- **Prune**: `prune(min_supported, max_age_days)` removes low-quality/expired entries
- **Seed**: `seed_memory.py` provides 14 initial SEMANTIC rules (state machine decision tree); loaded after first game.
- **Scoring**: `retrieval_score = importance(event_type) × recency(7-day half-life)`
- **Game limit**: ~3200 frames (~60ms each). LLM prints every `--print-every` frames (default 1).

## Known Code Traps

- **Skill cooldown**: `hero.skill[i].cooldown` (NOT `skill_cd_*`). Wrong fields silently return 0.
- **Coords**: button 0-11, move_x/z 1-15, skill_x/z 1-15, target 0-7. All coords **must be 1-15**.
- **Legal action flat array**: `[12 buttons][16×4 coords][12×8 targets]` target offset = 76.
- **FOW**: `camp_visible[player_index] == false` → HP shows `FOW`, position is fake.
- **Map**: Blue (camp=0) at -X, Red (camp=1) at +X. Spawn ≈-32308 / +100000.
- **Container CWD**: MUST be `/hok_env/hok/hok1v1` — SDK resolves `config.dat` relatively.
- **AILab stubs**: `main_macro.py` creates them inline; run `scripts/setup_ailab.py` or `scripts/fix_ailab.py` after container rebuild.
- **ITEM data**: Not from protobuf; `hero_skills.py` has per-hero item lists, `gamecore_data.py` reads `equipment_config_id.txt`.
- **No test framework**: `tests/test_*.py` are standalone scripts requiring gamecore-server + SDK; run from project root.
- **README.md is stale**: Documents old v1 architecture (`main.py`, `agent.py`, `react_agent.py`, `mock_env.py`, `web_demo.py`). None of these files exist in `src/`. Trust AGENTS.md.
- **hero_skills.py**: Only 5 heroes fully configured (132 MarcoPolo, 169 HouYi, 199 GongsunLi, 141 DiaoChan, 107 ZhaoYun). Other heroes get default fallback behavior.
- **DASHSCOPE_BASE_URL** uses `token-plan` proxy — raw DashScope URL will NOT work.
- **Gamecore data files**: `gamecore_data.py` reads from `core_assets/customresources/ailab/ai_config/1v1/`. If gamecore paths change, `GAMECORE_PATHS` in that file needs updating.
- **Trajectories accumulate**: Each game creates a `.jsonl` in `trajectories/`. 70+ already exist. Clean manually.

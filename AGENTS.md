# HOK — Honor of Kings LLM Agent

THU AI实践基石. LLM Agent 玩王者荣耀 1v1. 纯 prompt 工程, 零训练.

## Entrypoints

| Priority | File | Role |
|----------|------|------|
| 1 | `src/main_macro.py` | **Active.** MacroAgent + MemorySystem, runs in Docker |
| 2 | `src_v2/` | Local-only (gitignored). MockEnv, web UI (FastAPI :13187), newer dev work |

## Source Layout

```
src/                              # Git-tracked, gamecore-Docker version
  main_macro.py                   # **Active. Entrypoint** (MacroAgent + MemorySystem, runs in Docker)
  macro_agent.py                  # SYS1: frame-by-frame LLM decide(), builds TRENDS/DETAIL/DELTA memory
  memory.py                       # MemorySystem: retrieve() + reflect() (SYS2→SYS3→AUDIT pipeline)
  prompts.py                      # PROMPT_BASE + 4 protocols + 9 few-shot examples
  state_parser.py                 # Protobuf → text state + MACRO ACTIONS (AVAILABLE/BLOCKED)
  strategy_executor.py            # @SKILL_CALL parser → 6-tuple, routes to skills_concrete.py
  skills_concrete.py              # Multi-frame concrete skills (Farm/Poke/AllIn/Kite/etc)
  skills/                         # @register_skill doc-only (PROMPT skilldoc generation)
    farm.py, poke.py, all_in.py
    defend.py, kite.py, retreat.py
    stand_and_shoot.py, system_help.py
  skill_base.py                   # SKILL_REGISTRY + @register_skill decorator
  hero_db.py, hero_skills.py      # Hero ID mapping + per-hero skill configs
  skill_db.py                     # HUMANTIC matchup + combo/wave/positioning rules
  gamecore_data.py                # Reads gamecore config files at runtime
  pathfinding.py                  # A* pathfinding (used by strategy_executor)
  trajectory.py                   # JSONL step logger
tests/                            # Test scripts (need gamecore-server + SDK)
scripts/                          # Setup scripts, AILab stubs, memory seed
trajectories/                     # Per-game .jsonl logs + memory.json + serve.py + screenshot
gamecore/                         # Gitignored. gamecore-server.exe (proprietary)
```

## Commands (Docker)

```powershell
# Start gamecore (Windows host, CWD = gamecore\gamecore)
Start-Process -WindowStyle Hidden -FilePath "gamecore\gamecore\gamecore-server.exe" "server","--server-address :23432" -WorkingDirectory "HOK\gamecore\gamecore"

# Run agent in container
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py --decisions 10 --hero-ai 199 --hero-bot 169"

# Options: --max-tokens 4096 (default 400), --no-thinking (disable reasoning)
# Example: python3 -u /workspace/src/main_macro.py --decisions 10 --hero-ai 169 --hero-bot 112 --max-tokens 4096 --no-thinking

# Trajectory browser
python trajectories/serve.py 23456

# Stop (zombie ZMQ ports may block restart; kill leftover python in container)
taskkill /f /im gamecore-server.exe && docker stop hok
```

Do NOT `docker rm -f hok` (rebuilding re-installs all deps + AILab files).

## `.env` Required

```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```

Current `.env` uses `token-plan` (internal proxy), not raw DashScope URL.

## Skill System

- `skills/__init__.py` auto-discovers via `pkgutil.iter_modules`. New skill = create `skills/x.py` with `@register_skill` class.
- `@SKILL_CALL Skill.func()` parser in `strategy_executor.py`. Routes to `skills_concrete.py` (multi-frame execution).
- `skills/` files are **doc-only** (generated into PROMPT skilldoc via `@register_skill`). Execution goes to `skills_concrete.py`.
- `skills_concrete.py`: Multi-frame concrete skills with `_start()` + `update()` → `(action, done)`. LLM calls once, executor loops until `done`.
- `SkillContext` (helpers: `make_move`, `make_attack`, `make_skill`, `valid_btn`, `dist_to_enemy`) initialized from protobuf each frame.
- Per-hero skill config in `hero_skills.py` (`poke_skill`, `combo_priority`, `skill_ranges`, `item` list) — used by skills and state_parser.
- A* pathfinding in `make_move_to()` avoids organ obstacles.

## Architecture

```
SYS1 (ingame, every frame)     → 6-tuple action via strategy_executor → skills_concrete multi-frame
SYS2 (post-game, per event)    → BUFFER (episodic + semantic candidates)
SYS3 (post-game, ×1 review)    → BUFFER
AUDIT (post-game, ×1)          → score BUFFER + DB, merge into memory.json
```

Prompt: `PROMPT_BASE + hero_info + skilldoc + experience + PROTOCOL + few-shot`

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
- **ITEM data**: Not from protobuf; `hero_skills.py` has per-hero item lists, `gamecore_data.py` reads equipment_config_id.txt.
- **No test framework**: `tests/test_*.py` are standalone scripts requiring gamecore-server + SDK; run from project root.
- **README.md is stale**: Commands/architecture there predates macro_agent + memory system. Trust AGENTS.md.

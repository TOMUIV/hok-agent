# HOK — Honor of Kings LLM Agent

THU AI实践基石. LLM Agent 玩王者荣耀 1v1. 纯 prompt 工程, 零训练.

## Entrypoints

| Priority | File | Role |
|----------|------|------|
| 1 | `src/main_macro.py` | MacroAgent + MemorySystem + strategy executor, runs in Docker |
| `start.bat` | Starts gamecore-server then runs agent in container |

`src_v2/` archived. Old `src/main.py`, `agent.py`, `react_agent.py`, `mock_env.py`, `web_demo.py` no longer exist — replaced by macro_agent architecture. README is stale (documents old v1 code; trust AGENTS.md).

## Source Layout

```
src/                              # Git-tracked, gamecore-Docker version
  main_macro.py                   # Entrypoint (MacroAgent + post-game reflect)
  macro_agent.py                  # SYS1: frame-by-frame LLM decide(), damage detection for skill interruption
  memory.py                       # MemorySystem: retrieve() + reflect()
  prompts.py                      # PROMPT_BASE + 4 protocols + build_full_prompt()
  state_parser.py                 # Protobuf → text state + MACRO ACTIONS
  strategy_executor.py            # @SKILL_CALL parser → 6-tuple, routes to skills_concrete.py
  skills_concrete.py              # Multi-frame concrete skills (Farm/Poke/AllIn/Kite/…)
  skills/                         # @register_skill doc-only (auto-discovered via pkgutil)
  skill_base.py                   # SKILL_REGISTRY + @register_skill decorator
  hero_db.py                      # Hero ID → name mapping
  hero_skills.py                  # Per-hero config (only 5 heroes: 132, 169, 199, 141, 107)
  skill_db.py                     # HUMANTIC matchup data
  gamecore_data.py                # Reads gamecore config at runtime (3 fallback paths)
  pathfinding.py                  # A* pathfinding (grid-based, 800-unit cells)
  trajectory.py                   # TrajectoryLogger class — DEAD CODE (unused; macro_agent.py handles logging)
tests/                            # Standalone scripts (need gamecore-server + SDK). No test framework.
  test_*.py                       # Some .gitignored (test_agent, test_final_OK, test_full_flow, test_minimal, test_reset)
scripts/                          # Setup scripts: setup_ailab.py, fix_ailab.py, setup_ailab_stubs.py, seed_memory.py
  seed_memory.py                  # Seeds memory.json with 14 initial SEMANTIC rules
trajectories/                     # Per-game .jsonl logs + memory.json + serve.py + index.html
  memory.json                     # MemorySystem persistent store (auto-loaded/saved)
gamecore/                         # Gitignored. gamecore-server.exe (proprietary)
```

## Dependencies

Manual `pip install openai fastapi uvicorn numpy python-dotenv`. No package manager.

## Commands (Docker)

```powershell
# Start gamecore (Windows host)
Start-Process -WindowStyle Hidden -FilePath "gamecore\gamecore\gamecore-server.exe" "server","--server-address :23432" -WorkingDirectory "HOK\gamecore\gamecore"

# Run agent in container
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py --decisions 10 --hero-ai 199 --hero-bot 169"

# Options: --max-tokens 4096 (default 2048), --no-thinking, --print-every N, --max-frames N
# --max-frames is parsed but UNUSED (loop uses --decisions as primary bound)

# Trajectory browser
python trajectories/serve.py 23456

# Stop
taskkill /f /im gamecore-server.exe && docker stop hok
```

Do NOT `docker rm -f hok` (rebuilding re-installs all deps + AILab stubs). Use `docker stop`/`start`.

## `.env` Required

```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```

Uses `token-plan` (internal proxy), NOT raw DashScope URL. `.env` is NOT gitignored (but listed in `.gitignore` — be careful not to expose API key).

## Architecture

```
Game Environment (Windows + Docker)
  ├─ gamecore-server.exe ←HTTP:23432/ZMQ:35500→ Docker (HoK SDK)
  │
  ├─ [Every frame] Game State → SYS1: MacroAgent → <think 5-sections> + <action @SKILL_CALL>
  │     → Strategy Executor → 6-tuple (btn, mx, my, sx, sy, target) → gamecore
  │   LLM NEVER directly touches gamecore (safety abstraction).
  │
  ├─ Trajectory JSONL → Event Detection (kill/death/tower_fall/gold_spike/power_spike)
  ├─ [Post-game × per event] → SYS2: Event Analysis (BEFORE/AFTER 100 frames) → BUFFER
  ├─ [Post-game × once]      → SYS3: Game Review                           → BUFFER
  └─ [Post-game × once]      → AUDIT: score DB + BUFFER (1/-1/0)
       → Score=1 → Similarity Check → DB (memory.json)
       → Score ≤0 → DISCARD
```

Prompt assembly: `PROMPT_BASE + EXPERIENCE + PROTOCOL + TRENDS + EVENTS + DETAIL + MACRO_ACTIONS + few-shot`.

`<think>` 5 sections: **Review / WhatIf check / Situation / WhatIf 1-2 / Decision**. Output format: `=== THINK ===` / `=== ACTION ===` (parsed by regex).

**DMG tracking**: Extracted per-frame from protobuf cumulative fields (`totalBeHurtByHero` / `totalHurtToHero` diff) + `is_hero_under_tower_atk` flag + HP delta. Broken down into TOWER / HERO / OTHER (minion) components. Displayed as `--- SELF_COMBAT ---` in TRENDS and per-frame DMG: line in DETAIL.

**Skill interruption**: Controlled by `no_interrupt` attribute in `skills_concrete.py`. Skills with `no_interrupt=False` (Farm, Poke, Defend) are interrupted on damage (tower fire OR HP drop >50) → control returns to LLM. `no_interrupt=True` (AllIn, Kite, Retreat, Pursue) run continuously despite damage.

**Executor fallback**: If no LLM decision or no skill queued, defaults to FARM skill automatically.

**Game loop termination**: `decisions < MAX_DECISIONS` (not frames). Consecutive errors trigger kill switch at 50 retries.

## Skill System

- `skills/__init__.py` auto-discovers via `pkgutil.iter_modules`. New skill = create `skills/x.py` with `@register_skill` class.
- `@SKILL_CALL Skill.func()` parser routes to `skills_concrete.py` (multi-frame execution).
- `skills/` files are **doc-only** (generated into PROMPT skilldoc). Execution goes to `skills_concrete.py`.
- Per-hero config in `hero_skills.py`: only **132/169/199/141/107** have custom configs; others use default fallback.

## Memory System

- File: `trajectories/memory.json` (auto-loaded/saved by MemorySystem)
- Three tiers: Working (2000-frame buffer), EPISODIC (per-event cases), SEMANTIC (reusable rules)
- `retrieve()` → HUMANTIC + top-5 EPISODIC + top-10 SEMANTIC by support ratio
- `reflect()`: SYS2 (event analysis) → SYS3 (global review) → AUDIT (scoring)
- Reflect log entries appended to same `.jsonl` via `_log_reflect` in memory.py
- Dedup: 3-layer field matching (normalize → condition prefix → structured fields)
- **Game limit**: ~3200 frames (~60ms each). LLM prints every `--print-every` frames (default 1).

## Known Code Traps

- **Skill cooldown**: `hero.skill[i].cooldown` (NOT `skill_cd_*`). Wrong fields silently return 0.
- **DMG protobuf fields**: `totalBeHurtByHero` / `totalHurtToHero` are cumulative (monotonic increasing). Take diff per frame to get per-frame damage. HP delta minus hero damage = minion/other damage.
- **Coords**: button 0-11, move_x/z 1-15, skill_x/z 1-15, target 0-7. All coords **must be 1-15**.
- **Legal action flat array**: `[12 buttons][16×4 coords][12×8 targets]`, target offset = 76.
- **FOW**: `camp_visible[player_index] == false` → HP shows `FOW`, position is fake.
- **Container CWD**: MUST be `/hok_env/hok/hok1v1` — SDK resolves `config.dat` relatively.
- **AILab stubs**: `main_macro.py` creates 10 stub files inline at startup (auto). Run `scripts/setup_ailab.py`/`fix_ailab.py` after container rebuild only if stubs missing.
- **ITEM data**: Not from protobuf; `hero_skills.py` has per-hero item lists, `gamecore_data.py` reads `equipment_config_id.txt` (3 fallback paths).
- **hero_skills.py**: Only 5 heroes have custom config (132 MarcoPolo, 169 HouYi, 199 GongsunLi, 141 DiaoChan, 107 ZhaoYun).
- **DASHSCOPE_BASE_URL** uses `token-plan` proxy — raw DashScope URL will NOT work.
- **Trajectories accumulate**: Each game creates a `.jsonl` in `trajectories/`. 70+ exist. Clean manually.
- **`trajectory.py` `TrajectoryLogger` is dead code**: Not used anywhere; logging is in `macro_agent.py` directly.
- **`--max-frames` is a no-op**: Parsed in `main_macro.py` but never checked in the loop. Use `--decisions` instead.
- **`start.bat` has hardcoded absolute path** to user's `D:\资料库\...` — won't work in other environments.
- **`gamecore_data.py`** reads config files from 3 fallback paths; if gamecore paths change, update `GAMECORE_PATHS`.

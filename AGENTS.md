# HOK — Honor of Kings LLM Agent

LLM Agent plays 1v1 Honor of Kings. Zero ML training — pure prompt engineering + memory system + layered knowledge base. Model: DeepSeek via `DASHSCOPE_BASE_URL` token-plan proxy (NOT raw DashScope URL).

## Entrypoints

| Priority | File | Role |
|----------|------|------|
| 1 | `run.py` | Preferred launcher: start gamecore, ZMQ cleanup, docker exec, one command |
| 2 | `src/main_macro.py` | MacroAgent + MemorySystem + strategy executor, runs in Docker |
| — | `start.bat` | Hardcoded absolute paths (won't work outside this machine). Reference only. |

## Source Layout

```
src/
  main_macro.py          Entrypoint: game loop, frame logging, post-game reflect
  macro_agent.py         SYS1: frame-by-frame LLM decide(), damage detection, frame buffer
  memory.py              MemorySystem: 3-tier (working/episodic/semantic), retrieve + reflect + audit
  prompts.py             PROMPT_BASE + 5 protocols + build_full_prompt()
  state_parser.py        Protobuf → text state + MACRO ACTIONS display
  strategy_executor.py   @SKILL_CALL parser → 6-tuple, routes to skills_concrete.py
  skills_concrete.py     Multi-frame concrete skills (MoveTo/Attack/Poke/…)
  skills/                Doc-only @register_skill files (auto-discovered via pkgutil)
  skill_base.py          SKILL_REGISTRY + Skill base class + __init_subclass__ auto-sets no_interrupt
  skill_config.py        CONTINUOUS_SKILLS set (ComboStep/Retreat/Chase/Kite/Dodge)
  skill_context.py       Per-frame state (positions, coords, legal actions, movement helpers)
  embedding.py           Lazy BGE-M3 for memory dedup similarity (imported only when needed)
  gamecore_data.py       Reads gamecore config at runtime (3 fallback paths)
  hero_skills.py         Per-hero config (only 5 heroes: 132/169/199/141/107)
  hero_db.py             Hero ID → name mapping
  skill_db.py            HUMANTIC matchup data
  pathfinding.py         A* pathfinding (grid-based, 800-unit cells)
  constants.py           Button indices, tower map, thresholds
scripts/                 Setup: setup_ailab.py, fix_ailab.py, seed_memory.py
trajectories/            Per-game .jsonl + memory.json + serve.py browser
  memory.json            MemorySystem persistent store (auto-loaded/saved)
gamecore/                Gitignored. gamecore-server.exe (proprietary)
```

## Quick Start

```powershell
# 1. Start gamecore (Windows host, DETACHED_PROCESS)
# 2. Run agent
python run.py --hero-ai 169 --hero-bot 112 --decisions 10 --max-tokens 4096

# Other run.py flags: --list, --gamecore-only, --stop-gamecore, --reset-memory, --no-thinking
# run.py does ZMQ port cleanup + docker exec automatically

# Manual alternative (after ensuring gamecore is running):
docker exec hok bash -c "cd /hok_env/hok/hok1v1 && python3 -u /workspace/src/main_macro.py --decisions 10 --hero-ai 199 --hero-bot 169"

# Trajectory browser
python trajectories/serve.py 23456

# Stop
taskkill /f /im gamecore-server.exe && docker stop hok
```

Do NOT `docker rm -f hok` (reinstalls all deps + AILab stubs). Use `docker stop`/`start`.

## `.env` Required

```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat          # Default in code is deepseek-v4-flash
```

`.env` is gitignored but NOT encrypted — do not leak.

## Dependencies

Manual `pip install openai fastapi uvicorn numpy python-dotenv`. No package manager. BGE-M3 (`FlagEmbedding`) optional — used only when memory has items to compare.

## Architecture

```
Game Environment (Windows + Docker)
  └─ gamecore-server.exe ←HTTP:23432/ZMQ:35500→ Docker (HoK SDK)
       │
       ├─ [Every frame] Game State → SYS1: MacroAgent.decide()
       │     → LLM outputs <think 5-sections> + <action @SKILL_CALL>
       │     → StrategyExecutor → 6-tuple → gamecore
       │   LLM NEVER touches gamecore directly.
       │
       ├─ [Post-game] SYS2(events) → SYS3(predict) → SYS4(align) → SYS3(global) → SYS4(global) → AUDIT
       │     → Score=1 → memory.json  |  Score≤0 → DISCARD
       └─ [Per-game] Trajectory JSONL → trajectories/
```

Prompt: `PROMPT_BASE + EXPERIENCE + PROTOCOL + TRENDS + EVENTS + DETAIL + MACRO_ACTIONS + few-shot`.

`<think>` 5 sections: **Review / WhatIf check / Situation / WhatIf 1-2 / Decision**. Output parsed by regex `=== THINK === / === ACTION ===`.

## Skill System

One-shot (instant): ATTACK, USE_SKILL, POKE, COMBO_STEP, KITE, DODGE, RECALL, LAST_HIT, CLEAR, WAIT
Multi-step (until arrival/stuck): MOVE_TO(x,y|dir), RETREAT, CHASE

- Skills with `no_interrupt=False` (Farm, Poke, Defend) interrupted on damage (tower fire OR HP drop >50) → control returns to LLM
- `no_interrupt=True` skills (ComboStep, Retreat, Chase, Kite, Dodge) run through damage — set via `skill_config.py` `CONTINUOUS_SKILLS`, auto-applied by `Skill.__init_subclass__`
- Fallback: if no LLM decision → FARM (move toward enemy center)
- Termination: `decisions < MAX_DECISIONS` (primary) AND `step < MAX_FRAMES` (secondary — default 3000). 50 consecutive errors → kill switch.

## Known Code Traps

- **Skill cooldown**: `hero.skill[i].cooldown` (NOT `skill_cd_*`). Wrong fields silently return 0.
- **DMG fields**: `totalBeHurtByHero` / `totalHurtToHero` are cumulative (monotonic). Diff per frame.
- **Coords**: button 0-11, move_x/z 1-15, skill_x/z 1-15, target 0-7. All must be 1-15.
- **Legal action flat array**: `[12 buttons][16×4 coords][12×8 targets]`, target offset = 76.
- **Hero location**: `location.x` = x coord, `location.z` = depth, `location.y` = HEIGHT (always 48 on ground). NEVER use `location.y` for distance.
- **Organ fields LOWERCASE**: `config_id`, `hp`, `max_hp`, `camp`, `sub_type`. CamelCase = 0.
- **Soldier `camp` may be enum**: Use `.value if hasattr(val, 'value') else val`.
- **`_last_hp` must be updated**: `self._last_hp = hp` must be set every frame or damage detection stops working.
- **ZMQ cleanup**: `run.py` does it automatically (`fuser -k PORT/tcp`). Manual: `fuser -k 35500/tcp`.
- **Container CWD**: MUST be `/hok_env/hok/hok1v1` — SDK resolves `config.dat` relatively.
- **AILab stubs**: `main_macro.py` creates 10 stub files at startup. Run `scripts/fix_ailab.py` after container rebuild only if stubs missing.
- **ITEM data**: Not from protobuf; `hero_skills.py` + `gamecore_data.py` reads `equipment_config_id.txt`.
- **hero_skills.py**: Only 5 heroes with custom config (132 MarcoPolo, 169 HouYi, 199 GongsunLi, 141 DiaoChan, 107 ZhaoYun).
- **`--max-frames` IS checked** (line 134) but decisions bound triggers first in practice.
- **Trajectories accumulate**: Each game creates a `.jsonl` + optional `_reflect.log` in `trajectories/`. Clean manually.
- **`run.py` preferred** over `start.bat` (has hardcoded absolute paths). `run.py` does ZMQ cleanup, supports `--list`, `--reset-memory`, `--stop-gamecore`.
- **Embedding**: `embedding.py` lazy-loads BGE-M3 (`FlagEmbedding`) for memory similarity. Only used during AUDIT phase if memory items exist.

# HOK (Honor of Kings AI)

THU AI实践基石 — 纯文本 LLM Agent 玩王者荣耀 1v1。无训练成本，纯 prompt 工程。

Full design doc at `PLAN.md`.

## Quick Commands

```bash
python src/demo.py                        # MockEnv: Marco Polo vs Hou Yi, 100 steps
python src/web_demo.py                    # Web UI v1 (localhost:13187), reads .env
python src/web_demo_v2.py                 # Web UI v2 (localhost:13188), MockEnvV2, reads .env
python src/macro_demo.py                  # ⚠️ BROKEN — imports StrategyExecutor that no longer exists
python src/macro_demo_llm.py              # ⚠️ BROKEN — imports BUTTONS from strategy_executor (doesn't exist)
python trajectories/serve.py [port]       # Trajectory replay browser (default :23456)
python -c "from src.demo import run_demo; run_demo(hero_ids=[199,169],max_steps=100)"
```

## Project Structure

- `src/` — all agent logic (runs locally or in Docker)
- `src_v2/` — near-identical copy of `src/`; `main_v2.py` loads `/workspace/.env` for Docker
- `gamecore/` — game engine binaries (proprietary, gitignored)
- `trajectories/` — JSONL replay files + `serve.py` (replay browser)
- `PLAN.md` — full architecture, literature review, experiment design

## Setup

**No requirements.txt** — install manually: `pip install openai fastapi uvicorn numpy python-dotenv`

**No test framework** — `src/test_*.py` are direct-run scripts, not pytest.

`.env`:
```
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_URL=https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-flash
```
No API key → random fallback.

## Agent Implementations

| File | Protocol | Model Source |
|------|----------|-------------|
| `agent.py` | JSON decision | **Hardcoded qwen-plus**, reads API_KEY from env only |
| `react_agent.py` | ReAct → FinalAction | Constructor params |
| `macro_agent.py` | Macro action (`@SKILL_CALL`) | Constructor params (defaults to env) |
| `main.py` | FinalAction direct parse | **Hardcoded** BASE_URL + deepseek-v4-flash, API_KEY from env |
| `main_macro.py` | MacroAgent for Docker | **Hardcoded** BASE_URL + deepseek-v4-flash, API_KEY from env |
| `src_v2/main_v2.py` | MacroAgent + argparse | Loads `/workspace/.env` via dotenv |
| `web_demo.py` | JSON + WebSocket | Reads `.env`, port 13187 |
| `web_demo_v2.py` | MockEnvV2 simulation | Reads `.env`, port 13188 |
| `strategy_executor.py` | Macro → 6-tuple | No LLM, rule-based |
| `memory.py` | Event recording + sliding window | No LLM, lightweight |

## Action Format

`(button:0-11, move_x:1-15, move_z:1-15, skill_x:1-15, skill_z:1-15, target:0-7)`

**All 4 coordinate axes must be 1-15** (0 triggers illegal action warning).

legal_action is a flat 1D array: `[12 buttons][16 move_x][16 move_z][16 skill_x][16 skill_z][12×8 targets]`
```python
offset = 12 + 16*4  # 76
target_mask = legal_action[offset + btn*8 : offset + btn*8 + 8]
```
**Never hardcode target=1** — use first legal target from sub_action_mask.

## Map Coordinates (Gamecore-Verified)

- 1v1 map "墨家机关道", **lane along X axis**
- Blue (PLAYERCAMP_1) at -X, Red (PLAYERCAMP_2) at +X
- Toward own base = -X, toward enemy base = +X (for camp=1)
- Blue spawn X≈-32308, Red spawn X≈+100000
- `.x`/`.y` for ground; `.z` is height (ignore)

## War Fog

- `camp_visible[player_index] == false` → enemy HP shows as 1 (not true value)
- `info[0].req_pb` and `info[1].req_pb` are same protobuf with different visibility

## Known Code Traps

- **Missing imports**: `text_adapter.py` imports `llm_decision_to_game_action`/`ACTION_MAP`/`DecisionType` from `protocol.py` — **none exist there**. Modifying `protocol.py` must add these.
- **`macro_demo.py` broken**: imports `StrategyExecutor, MACRO_ACTIONS, BUTTONS` from `strategy_executor` — `StrategyExecutor` was renamed to `ProtocolExecutor`, `MACRO_ACTIONS` and `BUTTONS` don't exist.
- **`macro_demo_llm.py` broken**: imports `BUTTONS` from `strategy_executor` — doesn't exist there.
- **Hero name duplication**: Two maps — `hero_db.py:hero_name()` and `text_adapter.py:HERO_NAMES`. Keep in sync.
- **`agent.py` hardcodes qwen-plus** — ignores `.env` MODEL_NAME.
- **`main.py` hardcodes BASE_URL + MODEL** — does NOT read from `.env` (only reads API_KEY).
- **`src_v2/` mirrors `src/`** — changes to `src/` need syncing to `src_v2/` if used in Docker.
- **Macro skills auto-discovery**: `src/skills/__init__.py` uses `pkgutil.iter_modules` to auto-register skills via `@register_skill` decorator. Adding a new `.py` file there automatically registers it.
- **A* pathfinding**: `src/pathfinding.py` implements `astar(px, py, tx, ty, obstacles)`. Obstacles pass as `(ox, oy, radius)` tuples. Grid cell size is 800 units.
- **Skill cooldown fields**: Hero protobuf has no `skill_cd_1` etc. Skill data is `hero.skill[i]` (list of Skill objects). Each Skill has `cooldown` (remaining, game ticks) and `cooldown_max`. Bad field names silently default to 0, so the LLM always sees `S1(0.0s/0.0s)`.

## Gamecore Deployment (Docker)

```
Windows                          Docker (tencentailab/hok_env:latest)
gamecore-server.exe :23432 ──HTTP──→ Python SDK + Agent
sgame_simulator       ←──ZMQ :35500─
```

**Working directory must be `/hok_env/hok/hok1v1`** — SDK's config.dat resolves paths relatively. Else crashes with `LoadJsonDocDict`.

**Ports**: `-p HOST_PORT:CONTAINER_PORT`, same port both sides. Do NOT use `--network host` (ZMQ fails with -7).

**gamecore-server start/stop** (Python DETACHED_PROCESS, non-blocking):
```powershell
python tmp\scripts\start_gc.py           # start
taskkill /f /im gamecore-server.exe && taskkill /f /im sgame_simulator_remote_zmq.exe  # stop
docker start hok                          # start container
```

**AILab stubs**: SDK needs stub files or it crashes. `main.py`/`main_v2.py`/`main_macro.py` create them inline (11 stubs). `src/fix_ailab.py` (11 files) and `src/setup_ailab.py` (40+ files) are standalone scripts for after container rebuild.

**Container template**:
```bash
docker run -d --name hok -p 35500:35500 -p 35501:35501 \
  -e PYTHONUNBUFFERED=1 -e GAMECORE_SERVER_ADDR=host.docker.internal:23432 \
  -e AI_SERVER_ADDR=172.24.50.71 -e DASHSCOPE_API_KEY="..." \
  -v "D:\path\to\HOK\src:/hok_agent" tencentailab/hok_env:latest \
  sh -c "pip install openai -q 2>/dev/null; cd /hok_env/hok/hok1v1 && python3 -u /hok_agent/main.py"
```

**Do NOT `docker rm -f hok`** — rebuilding re-installs all dependencies + AILab files.

## ABSTool Replay

Unity replay renderer at `D:\TEMP\replay_tool\` (path must not contain Chinese chars):
```powershell
copy /y gamecore\gamecore\scene\*.abs D:\TEMP\replay_tool\Replays\
D:\TEMP\replay_tool\ABSTool.exe
```

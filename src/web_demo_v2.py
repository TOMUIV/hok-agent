import asyncio, json, os, sys, time, math
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(__file__))
from mock_env_v2 import MockEnvV2, HERO_TEMPLATES, EQUIPMENT_DB, LEVEL_EXP_TABLE, Vec3

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

HERO_NAMES = {k: v["name"] for k, v in HERO_TEMPLATES.items()}

app = FastAPI()
connected = set()
game_task = None
stop_event = asyncio.Event()

def serialize_state(state, action_tuple, llm_reply, hero_idx=0):
    req_pb = state.get("req_pb")
    if not req_pb:
        return {"frame": 0, "gameover": True}
    hero = req_pb.hero_list[hero_idx] if hero_idx < len(req_pb.hero_list) else None
    enemy = req_pb.hero_list[1 - hero_idx] if len(req_pb.hero_list) > 1 else None
    heroes_data = []
    for i, h in enumerate(req_pb.hero_list):
        hid = getattr(h, "config_id", 0)
        heroes_data.append({
            "hero_id": hid, "name": HERO_NAMES.get(hid, f"H{hid}"),
            "camp": getattr(h, "camp", 0), "hp": round(getattr(h, "hp", 0), 0),
            "max_hp": getattr(h, "max_hp", 1), "ep": round(getattr(h, "ep", 0), 0),
            "max_ep": getattr(h, "max_ep", 1),
            "level": getattr(h, "level", 1), "exp": round(getattr(h, "exp", 0), 0),
            "exp_next": LEVEL_EXP_TABLE[min(getattr(h, "level", 1), 14)],
            "money": round(getattr(h, "money", 0), 0),
            "x": round(getattr(h, "location", Vec3(0,0,0)).x, 0),
            "z": round(getattr(h, "location", Vec3(0,0,0)).z, 0),
            "phy_atk": getattr(h, "phy_atk", 0), "mgc_atk": getattr(h, "mgc_atk", 0),
            "phy_def": h.effective_phy_def if hasattr(h, 'effective_phy_def') else 0,
            "mgc_def": h.effective_mgc_def if hasattr(h, 'effective_mgc_def') else 0,
            "mov_spd": getattr(h, "mov_spd", 0), "atk_spd": getattr(h, "atk_spd", 0),
            "crit_rate": h.effective_crit * 100 if hasattr(h, 'effective_crit') else 0,
            "atk_range": getattr(h, "atk_range", 0),
            "killCnt": getattr(h, "killCnt", 0), "deadCnt": getattr(h, "deadCnt", 0),
            "assistCnt": getattr(h, "assistCnt", 0),
            "totalHurtToHero": getattr(h, "totalHurtToHero", 0),
            "totalBeHurtByHero": getattr(h, "totalBeHurtByHero", 0),
            "alive": getattr(h, "alive", True),
            "camp_visible": getattr(h, "camp_visible", [True, True]),
            "skills": [{"id": s.id, "name": s.name, "level": s.level, "cooldown": s.cooldown_remaining,
                        "max_cooldown": s.max_cooldown, "damage": s.damage, "damage_type": s.damage_type,
                        "description": s.description, "button_idx": s.button_idx}
                       for s in h.skills] if hasattr(h, 'skills') else [],
            "equipment": [{"id": e.id, "name": e.name, "phy_atk": e.phy_atk, "mgc_atk": e.mgc_atk,
                           "phy_def": e.phy_def, "mgc_def": e.mgc_def, "max_hp": e.max_hp_bonus,
                           "crit": e.crit * 100, "atk_spd": e.atk_spd * 100}
                          for e in h.equipment] if hasattr(h, 'equipment') else [],
        })
    organs_data = []
    for o in getattr(req_pb, "organ_list", []):
        organs_data.append({
            "ConfigID": getattr(o, "ConfigID", 0), "Camp": getattr(o, "Camp", 0),
            "SubType": getattr(o, "SubType", 0), "Hp": round(getattr(o, "Hp", 0), 0),
            "MaxHp": getattr(o, "MaxHp", 1), "x": getattr(o, "x", 0), "z": getattr(o, "z", 0),
            "name": getattr(o, "name", ""), "alive": getattr(o, "alive", True),
        })
    soldiers_data = []
    for s in getattr(req_pb, "soldier_list", []):
        if hasattr(s, 'alive') and s.alive:
            soldiers_data.append({
                "camp": getattr(s, "camp", 0), "hp": round(getattr(s, "hp", 0), 0),
                "max_hp": getattr(s, "max_hp", 1), "melee": getattr(s, "melee", True),
                "x": round(getattr(s, "location", Vec3(0,0,0)).x, 0),
                "z": round(getattr(s, "location", Vec3(0,0,0)).z, 0),
            })
    action_names = ["button", "move_x", "move_z", "skill_x", "skill_z", "target"]
    return {
        "frame": getattr(req_pb, "frame_no", 0),
        "gameover": getattr(req_pb, "gameover", False),
        "winner": state.get("winner", -1),
        "heroes": heroes_data,
        "organs": organs_data,
        "soldiers": soldiers_data,
        "action": {action_names[i]: int(v) for i, v in enumerate(action_tuple)},
        "llm_decision": llm_reply or "",
        "events": state.get("events", []),
    }

async def run_game(ws_queue=None):
    try:
        env = MockEnvV2(hero_ids=[132, 169])
        camp_list = [[{"hero_id": 132}], [{"hero_id": 169}]]
        state = env.reset(camp_hero_list=camp_list, use_common_ai=[True, True])
        print("run_game: reset OK, heroes:", len(env.heroes), flush=True)
        step = 0
        max_steps = 5000
        while not state.get("done", False) and step < max_steps:
            if stop_event.is_set():
                break
            step += 1
            action = (2, 8, 8, 1, 1, 0)
            state = env.step([action, (0, 0, 0, 0, 0, 0)])
            if step % 100 == 0:
                h0, h1 = env.heroes[0], env.heroes[1]
                dist = h0.distance_to(h1)
                print(f"  [{step:3d}] B@({h0.location.x:.0f},{h0.location.z:.0f}) "
                      f"R@({h1.location.x:.0f},{h1.location.z:.0f}) "
                      f"dist={dist:.0f}", flush=True)
            frame_data = serialize_state(state, action, "", 0)
            msg = json.dumps(frame_data, ensure_ascii=False)
            dead = set()
            for ws in list(connected):
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            connected.difference_update(dead)
            await asyncio.sleep(0.1)
        reason = getattr(env, 'win_reason', '')
        final = json.dumps({"type": "gameover", "step": step, "winner": env.winner, "reason": reason}, ensure_ascii=False)
        print(f"run_game: gameover, winner:{env.winner} reason:{reason}", flush=True)
        for ws in list(connected):
            try:
                await ws.send_text(final)
            except Exception:
                pass
    except Exception as e:
        print(f"run_game CRASHED: {e}", flush=True)
        import traceback
        traceback.print_exc()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    global game_task, stop_event
    try:
        while True:
            data = await ws.receive_text()
            cmd = json.loads(data)
            action = cmd.get("action", "")
            if action == "start" and (game_task is None or game_task.done()):
                stop_event.clear()
                game_task = asyncio.create_task(run_game(ws))
                await ws.send_text(json.dumps({"type": "status", "msg": "game started"}, ensure_ascii=False))
            elif action == "stop":
                stop_event.set()
                await ws.send_text(json.dumps({"type": "status", "msg": "game stopped"}, ensure_ascii=False))
            elif action == "step":
                await ws.send_text(json.dumps({"type": "pong"}, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    finally:
        connected.discard(ws)

@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "web_v2", "index.html")
    if os.path.exists(html_path):
        return HTMLResponse(open(html_path, encoding="utf-8").read())
    return JSONResponse({"status": "error", "message": "Frontend not found"})

@app.get("/api/shop")
async def api_shop():
    return {"items": EQUIPMENT_DB}

@app.get("/api/status")
async def api_status():
    return {"game_running": game_task is not None and not game_task.done(), "clients": len(connected)}

if __name__ == "__main__":
    print("=" * 50)
    print("HOK MockEnv V2 - Web UI")
    print(f"Heroes: {HERO_NAMES.get(132)} vs {HERO_NAMES.get(169)}")
    print("Open http://localhost:13188")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=13188)

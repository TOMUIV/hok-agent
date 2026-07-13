import asyncio, json, os, sys, time, random
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(__file__))
from mock_env import MockEnv, HERO_TEMPLATES
from agent import LLMAgent
from text_adapter import observation_to_text, HERO_NAMES

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-v4-flash")

app = FastAPI()
connected = set()
game_task = None
stop_event = asyncio.Event()

HERO_NAMES_SHORT = {v: k for k, v in HERO_NAMES.items()}

def build_frame_data(state, step, action_tuple, llm_reply, hero_id, frame_no):
    req_pb = state.get("req_pb", None)
    heroes_data = []
    if req_pb and hasattr(req_pb, "hero_list"):
        for h in req_pb.hero_list:
            hid = getattr(h, "config_id", 0)
            hname = HERO_NAMES.get(hid, f"H{hid}")
            hp = getattr(h, "hp", 0)
            camp = getattr(h, "camp", 0)
            heroes_data.append({
                "name": hname, "hp": round(hp, 0), "camp": int(camp),
                "level": getattr(h, "level", 1), "hero_id": hid,
            })
    action_names = ["which_button", "move_x", "move_z", "skill_x", "skill_z", "target"]
    return {
        "frame": frame_no,
        "step": step,
        "heroes": heroes_data,
        "action": {action_names[i]: int(v) for i, v in enumerate(action_tuple)},
        "llm_decision": llm_reply,
    }

async def run_game(ws_queue=None):
    env = MockEnv(hero_ids=[132, 169])
    from openai import OpenAI
    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL) if DASHSCOPE_API_KEY else None
    camp_list = [[{"hero_id": 132}], [{"hero_id": 169}]]
    state = env.reset(camp_hero_list=camp_list, use_common_ai=[False, True])
    from text_adapter import OBSERVATION_SYSTEM_PROMPT
    step = 0
    max_steps = 200
    gameover = False
    while not gameover and step < max_steps:
        if stop_event.is_set():
            break
        step += 1
        obs_text = observation_to_text(state, 0, "Agent")
        from text_adapter import get_available_decisions
        legal_str = get_available_decisions(state)
        prompt = obs_text + f"\nLegals: {legal_str}\nOutput JSON decision."
        llm_reply = ""
        decision = {}
        if client:
            try:
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "system", "content": OBSERVATION_SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                    temperature=0.7, max_tokens=200,
                )
                llm_reply = resp.choices[0].message.content.strip()
                try:
                    decision = json.loads(llm_reply)
                except json.JSONDecodeError:
                    decision = {"decision_type": "MOVE", "params": {"direction": "N", "distance": "medium"}}
            except Exception as e:
                llm_reply = f"LLM Error: {e}"
                decision = {"decision_type": "MOVE", "params": {"direction": "N", "distance": "medium"}}
        else:
            choices = ["MOVE", "NORMAL_ATTACK", "SKILL_1", "NONE"]
            chosen = random.choice(choices)
            decision = {"decision_type": chosen, "params": {}}
            llm_reply = json.dumps(decision)
        from protocol import llm_decision_to_game_action
        action = llm_decision_to_game_action(decision)
        actions = [action, (0, 0, 0, 0, 0, 0)]
        state = env.step(actions)
        req_pb = state.get("req_pb", None)
        if req_pb:
            gameover = getattr(req_pb, "gameover", False)
            frame_no = getattr(req_pb, "frame_no", 0)
        else:
            frame_no = step
        frame_data = build_frame_data(state, step, action, llm_reply, 132, frame_no)
        msg = json.dumps(frame_data, ensure_ascii=False)
        dead = set()
        for ws in connected:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        connected -= dead
        await asyncio.sleep(0.5)
    final = json.dumps({"type": "gameover", "step": step}, ensure_ascii=False)
    for ws in connected:
        try:
            await ws.send_text(final)
        except Exception:
            pass

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    global game_task, stop_event
    try:
        data = await ws.receive_text()
        cmd = json.loads(data)
        if cmd.get("action") == "start" and (game_task is None or game_task.done()):
            stop_event.clear()
            game_task = asyncio.create_task(run_game(ws))
            await ws.send_text(json.dumps({"type": "status", "msg": "game started"}, ensure_ascii=False))
        elif cmd.get("action") == "stop":
            stop_event.set()
            await ws.send_text(json.dumps({"type": "status", "msg": "game stopped"}, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    finally:
        connected.discard(ws)

@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    if os.path.exists(html_path):
        return HTMLResponse(open(html_path, encoding="utf-8").read())
    return JSONResponse({"status": "ok", "message": "Web frontend not found at src/web/index.html"})

@app.get("/api/status")
async def api_status():
    return {"game_running": game_task is not None and not game_task.done(), "clients": len(connected)}

if __name__ == "__main__":
    print(f"[Config] model={MODEL_NAME}, key={DASHSCOPE_API_KEY[:12]}..., base_url={DASHSCOPE_BASE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=13187)

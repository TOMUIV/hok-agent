import sys, os, time, re, json, math, glob, shutil, argparse
sys.stdout.reconfigure(encoding='utf-8')

parser = argparse.ArgumentParser()
parser.add_argument("--decisions", type=int, default=5, help="max LLM decisions")
parser.add_argument("--max-frames", type=int, default=3000, help="max env steps (-1 = unlimited, default=3000)")
parser.add_argument("--print-every", type=int, default=1)
parser.add_argument("--hero-ai", type=int, default=169)
parser.add_argument("--hero-bot", type=int, default=112)
parser.add_argument("--max-tokens", type=int, default=2048)
parser.add_argument("--no-thinking", action="store_true", help="disable thinking/reasoning mode")
args = parser.parse_args()

HERO_AI = args.hero_ai
HERO_BOT = args.hero_bot
MAX_DECISIONS = args.decisions
MAX_FRAMES = args.max_frames
PRINT_EVERY = args.print_every
MAX_TOKENS = args.max_tokens
THINKING = not args.no_thinking

os.chdir("/hok_env/hok/hok1v1")
os.environ["GAMECORE_SERVER_ADDR"] = "host.docker.internal:23432"
os.environ["AI_SERVER_ADDR"] = "172.17.208.1"

base = "/hok_env/hok/hok1v1"
ailab = os.path.join(base, "AILab")
for d in ["ai_config/ai_server/skill_type","ai_config/5v5/tactics/feature","ai_config/5v5/common","ai_config/ai_server/pb2struct"]:
    os.makedirs(os.path.join(ailab, d), exist_ok=True)
ailab_files = {
    "ai_server_conf.json": '{"game_mode":"1v1"}', "transfer_table.json": "{}",
    "ai_config/AiMgr.txt": "skill 0 1 2", "ai_config/ai_server/skill_type/2": "0",
    "ai_config/ai_server/rl_config_file.txt": " ",
    "ai_config/ai_server/pb2struct/pb2struct_config_server.txt": " ",
    "ai_config/5v5/tactics/feature/skill_state_description_config.txt": " ",
    "ai_config/5v5/tactics/feature/4_skill_hero_skill_state_description_config.txt": " ",
    "ai_config/5v5/common/skill_manager_config.txt": " ",
    "ai_config/5v5/tactics/feature/bit_map_250_organ_1v1.dat": " ",
    "ai_config/5v5/tactics/multi_task_tactics_config_file_two_hand_action_minimap_union_model_rl.txt": " ",
}
for p, c in ailab_files.items():
    with open(os.path.join(ailab, p), "w") as f:
        f.write(c)

sys.path.insert(0, "/workspace")
from dotenv import load_dotenv
load_dotenv("/workspace/.env")
from hok.hok1v1.env1v1 import interface_default_config, HoK1v1
from hok.hok1v1.hero_config import get_default_hero_config
from hok.common.gamecore_client import GamecoreClient
import hok.hok1v1.lib.interface as interface
from hero_db import hero_name
import gamecore_data as gc
from macro_agent import MacroAgent
import macro_agent
from memory import MemorySystem
from constants import BUTTON_NAMES, GOLD_SPIKE, POWER_SPIKE, ZMQ_PORTS

# 清理占用 ZMQ 端口的残留进程
import subprocess
for port in ZMQ_PORTS:
    for cmd in [["fuser", "-k", f"{port}/tcp"], ["lsof", "-ti", f":{port}"]]:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=5)
            if cmd[0] == "lsof" and r.stdout:
                for pid in r.stdout.decode().strip().split():
                    os.system(f"kill -9 {pid} 2>/dev/null")
                    print(f"[Cleanup] killed PID {pid} on port {port}", flush=True)
            elif cmd[0] == "fuser":
                break  # fuser -k kills directly, no output needed
        except FileNotFoundError:
            continue
        except Exception:
            continue

lib = interface.Interface()
lib.Init(interface_default_config)
gl = GamecoreClient(server_addr="host.docker.internal:23432", gamecore_req_timeout=60000,
    default_hero_config=get_default_hero_config())
env = HoK1v1("macro", gl, lib, ["tcp://0.0.0.0:35500","tcp://0.0.0.0:35501"], aiserver_ip="127.0.0.1")

CAMP = {"mode":"1v1","heroes":[[{"hero_id":HERO_AI}],[{"hero_id":HERO_BOT}]]}
print(f"{hero_name(HERO_AI)} vs {hero_name(HERO_BOT)}, max_decisions={MAX_DECISIONS}", flush=True)
obs, r, d, info = env.reset(CAMP, use_common_ai=[False,True], eval=True)
print(f"Reset OK", flush=True)

memory_sys = MemorySystem()
agent = MacroAgent("main", HERO_AI, HERO_BOT, memory_system=memory_sys,
                   max_tokens=MAX_TOKENS, thinking=THINKING)

def _get_hp(pb, cid):
    for h in getattr(pb, 'hero_list', []):
        if getattr(h, 'config_id', 0) == cid:
            return getattr(h, 'hp', 0), getattr(h, 'max_hp', 1), getattr(h, 'money', 0)
    return 0, 1, 0

def _get_pos(pb, cid):
    for h in getattr(pb, 'hero_list', []):
        if getattr(h, 'config_id', 0) == cid:
            loc = getattr(h, 'location', None)
            if loc and hasattr(loc, 'x'):
                return (loc.x, loc.z)
    return None

def _get_item(pb, cid):
    for h in getattr(pb, 'hero_list', []):
        if getattr(h, 'config_id', 0) == cid:
            eqs = getattr(h, 'equipment', None) or []
            names = [gc.get_equip_name(getattr(e, 'config_id', 0)) for e in eqs if getattr(e, 'config_id', 0)]
            return ", ".join(names) if names else "(none)"
    return "(none)"

def _get_tower_hp(pb):
    th = {}
    for o in getattr(pb, 'organ_list', []):
        cid = getattr(o, 'config_id', 0)
        label = {1: "BLUE outer", 2: "RED outer", 42: "BLUE inner", 43: "RED inner", 106: "BLUE crystal", 107: "RED crystal"}.get(cid)
        if label:
            th[label] = getattr(o, 'hp', 0)
    return th

start = time.time()
step = 0
decisions = 0
gameover = False
outcome = "unknown"
prev_pb = None
prev_events = {}
prev_hp_self = prev_hp_enemy = None
prev_gold_self = None
prev_dmg_hero = prev_dmg_dealt = None

retries = 0
while not gameover and decisions < MAX_DECISIONS and retries < 50 and (MAX_FRAMES < 0 or step < MAX_FRAMES):
    s = info[0]
    pb = s["req_pb"]
    frame = getattr(pb, 'frame_no', 0)
    gameover = getattr(pb, 'gameover', False) or d[0]
    heroes = pb.hero_list
    self_h = enemy_h = None
    for h in heroes:
        if getattr(h, 'config_id', 0) == HERO_AI: self_h = h
        else: enemy_h = h
    if not self_h or not enemy_h: break

    action, raw = agent.decide(info)
    obs, r, d, info = env.step([action, (0,0,0,0,0,0)])
    elapsed = time.time() - start

    # delta computation
    cur_pb = info[0].get("req_pb") if isinstance(info[0], dict) else info[0]
    delta = {"self_hp": {}, "self_gold": {}, "self_pos": {}, "enemy_hp": {}, "enemy_gold": {}, "enemy_pos": {}, "self_item": "", "enemy_item": "", "tower": ""}
    if cur_pb and prev_pb:
        for tag, cid in [("self", HERO_AI), ("enemy", HERO_BOT)]:
            chp, cmhp, cg = _get_hp(cur_pb, cid)
            php, pmhp, pg = _get_hp(prev_pb, cid)
            cpos = _get_pos(cur_pb, cid)
            ppos = _get_pos(prev_pb, cid)
            if chp is not None and php is not None:
                delta[f"{tag}_hp"] = {"old": php, "new": chp, "diff": chp - php}
            if cg is not None and pg is not None:
                delta[f"{tag}_gold"] = {"old": pg, "new": cg, "diff": cg - pg}
            if cpos and ppos:
                dx = math.sqrt((cpos[0]-ppos[0])**2 + (cpos[1]-ppos[1])**2)
                delta[f"{tag}_pos"] = {"old": list(ppos), "new": list(cpos), "diff": round(dx)}
            delta[f"{tag}_item"] = _get_item(cur_pb, cid)

        # tower delta
        pre_th = _get_tower_hp(prev_pb)
        cur_th = _get_tower_hp(cur_pb)
        dt = []
        for k in cur_th:
            if k in pre_th and cur_th[k] != pre_th[k]:
                dt.append(f"{k}: {pre_th[k]:.0f}->{cur_th[k]:.0f}({cur_th[k]-pre_th[k]:+.0f})")
        if dt:
            delta["tower"] = "; ".join(dt)
    else:
        # first frame: fill new state, no diff
        for tag, cid in [("self", HERO_AI), ("enemy", HERO_BOT)]:
            hp, mhp, g = _get_hp(pb if cur_pb else pb, cid)
            pos = _get_pos(pb if cur_pb else pb, cid)
            delta[f"{tag}_hp"] = {"old": hp, "new": hp, "diff": 0}
            delta[f"{tag}_gold"] = {"old": g, "new": g, "diff": 0}
            if pos:
                delta[f"{tag}_pos"] = {"old": list(pos), "new": list(pos), "diff": 0}
            delta[f"{tag}_item"] = _get_item(pb, cid)

    # event detection (per frame)
    events = []
    chp_s, _, cg_s = _get_hp(cur_pb or pb, HERO_AI)
    chp_e, _, cg_e = _get_hp(cur_pb or pb, HERO_BOT)
    if prev_hp_self is not None and prev_hp_self > 0 and chp_s == 0:
        events.append({"frame": frame, "type": "death"})
    if prev_hp_enemy is not None and prev_hp_enemy > 0 and chp_e == 0:
        events.append({"frame": frame, "type": "kill"})
    if prev_gold_self is not None and cg_s - prev_gold_self >= GOLD_SPIKE:
        events.append({"frame": frame, "type": "gold_spike", "delta": cg_s - prev_gold_self})
    prev_hp_self, prev_hp_enemy, prev_gold_self = chp_s, chp_e, cg_s

    # combat data from protobuf
    combat = {}
    if cur_pb:
        for hh in getattr(cur_pb, 'hero_list', []):
            if getattr(hh, 'config_id', 0) == HERO_AI:
                combat["under_tower_fire"] = bool(getattr(hh, 'is_hero_under_tower_atk', False))
                combat["dmg_taken_hp"] = delta.get("self_hp", {}).get("diff", 0)
                dmg_hero = getattr(hh, 'totalBeHurtByHero', 0)
                dmg_dealt = getattr(hh, 'totalHurtToHero', 0)
                if prev_dmg_hero is not None:
                    combat["dmg_taken_hero"] = max(0, dmg_hero - prev_dmg_hero)
                if prev_dmg_dealt is not None:
                    combat["dmg_dealt_hero"] = max(0, dmg_dealt - prev_dmg_dealt)
                prev_dmg_hero = dmg_hero
                prev_dmg_dealt = dmg_dealt
                break

    # push frame
    action_name = f"{BUTTON_NAMES[action[0]]}" if action[0] < len(BUTTON_NAMES) else f"btn{action[0]}"
    is_llm = raw not in ("skill_continue",)
    llm_data = None
    if is_llm:
        is_err = raw.startswith("[LLM Error") or raw.startswith("[Parse Error") or raw.startswith("[fallback")
        segs = agent._extract_think_segments(agent.last_thought) if agent.last_thought and not is_err else {}
        llm_reply = agent._last_raw_llm if hasattr(agent, '_last_raw_llm') and agent._last_raw_llm else raw
        llm_data = {"think_sections": segs, "reply": llm_reply,
                     "parsed_results": "\n".join(agent.last_results_full) if agent.last_results_full and not is_err else ""}
        if is_err:
            llm_data["error"] = raw
    agent.push_frame(frame, action_name, action, delta, events, llm_data=llm_data, combat=combat)

    # write JSONL
    phase = "llm" if llm_data else "skill"
    f_entry = {"frame": frame, "phase": phase, "action": list(action), "delta": delta, "events": events}
    if llm_data:
        f_entry["llm_reply"] = llm_data["reply"]
        if llm_data.get("parsed_results"):
            f_entry["parsed_results"] = llm_data["parsed_results"]
        if llm_data.get("error"):
            f_entry["error"] = llm_data["error"]
    macro_agent.traj_file.write(json.dumps(f_entry, ensure_ascii=False) + "\n")
    macro_agent.traj_file.flush()

    if step % PRINT_EVERY == 0:
        # SELF
        shp = getattr(self_h, 'hp', 0); smhp = getattr(self_h, 'max_hp', 1)
        shp_s = f"{shp}/{smhp}({shp/smhp*100:.0f}%)"
        sg = getattr(self_h, 'money', 0)
        sp = f"({self_h.location.x:.0f},{self_h.location.z:.0f})" if self_h.location else "(?,?)"
        eqs = getattr(self_h, 'equipment', None) or []
        eq_names = [gc.get_equip_name(getattr(e, 'config_id', 0)) for e in eqs if getattr(e, 'config_id', 0)]
        si = ", ".join(eq_names) if eq_names else "(none)"
        slv = getattr(self_h, 'level', 1)
        # ENEMY
        ehp = getattr(enemy_h, 'hp', 0); emhp = getattr(enemy_h, 'max_hp', 1)
        eg = getattr(enemy_h, 'money', 0); elv = getattr(enemy_h, 'level', 1)
        visible = getattr(enemy_h, 'camp_visible', [])
        e_fow = not (any(visible) if visible else True)
        ehp_s = f"FOW" if e_fow else f"{ehp}/{emhp}({ehp/emhp*100:.0f}%)"
        ep = f"({enemy_h.location.x:.0f},{enemy_h.location.z:.0f})" if enemy_h.location else "(?,?)"
        eqs_e = getattr(enemy_h, 'equipment', None) or []
        eq_names_e = [gc.get_equip_name(getattr(e, 'config_id', 0)) for e in eqs_e if getattr(e, 'config_id', 0)]
        ei = ", ".join(eq_names_e) if eq_names_e else "(none)"
        if e_fow:
            ehp_s = "FOW"; ep = "(?,?)"; ei = "(?)"; elv = "?"
        # TOWER / MINION from protobuf
        cur_pb = pb if cur_pb is None else cur_pb
        s_tower = "(no data)"; e_tower = "(no data)"; s_minion = "0"; e_minion = "0"
        s_tower_parts = []; e_tower_parts = []
        if cur_pb:
            for o in getattr(cur_pb, 'organ_list', []):
                cid = getattr(o, 'config_id', 0)
                hp = getattr(o, 'hp', 0)
                lbl = {1: ("OUTER","S"), 2: ("OUTER","E"), 42: ("INNER","S"), 43: ("INNER","E"), 106: ("CRYSTAL","S"), 107: ("CRYSTAL","E")}.get(cid)
                if lbl:
                    part = f"{lbl[0]};{hp:.0f}"
                    if lbl[1] == "S": s_tower_parts.append(part)
                    else: e_tower_parts.append(part)
            s_tower = "|".join(s_tower_parts) if s_tower_parts else "(none)"
            e_tower = "|".join(e_tower_parts) if e_tower_parts else "(none)"
            soldiers = getattr(cur_pb, 'soldier_list', [])
            if soldiers:
                hc = getattr(self_h, 'camp', None)
                hc_int = hc.value if hc is not None and hasattr(hc, 'value') else hc
                friendly = 0; enemy = 0
                for s in soldiers:
                    cv = getattr(s, 'camp', None)
                    if cv is not None:
                        cv_int = cv.value if hasattr(cv, 'value') else cv
                        if cv_int == hc_int: friendly += 1
                        else: enemy += 1
                s_minion = str(friendly)
                e_minion = str(enemy)

        # skill name
        is_llm = raw not in ("skill_continue", "[fallback]") and not raw.startswith("[LLM Error") and not raw.startswith("[Parse Error")
        tag = "LLM" if is_llm else "SKILL"
        if is_llm:
            skill_name = raw[:70]
        elif raw == "skill_continue" and hasattr(agent, '_last_skill_name') and agent._last_skill_name:
            skill_name = agent._last_skill_name
        else:
            skill_name = ""

        print(f"S{step:3d}  F{frame:3d} [{elapsed:4.0f}s] {tag}: {skill_name}", flush=True)
        print(f"  S: HP {shp_s}  G:{sg}  {sp}  ITEM:{si}  TOWER:{s_tower}  MINION:{s_minion}", flush=True)
        print(f"  E: HP {ehp_s}  G:{eg}  {ep}  ITEM:{ei}  TOWER:{e_tower}  MINION:{e_minion}", flush=True)
        for ev in events:
            print(f"  [{ev['type'].upper()}]", flush=True)

    prev_pb = cur_pb or pb
    gameover = d[0]
    if raw == "skill_continue":
        retries = 0  # valid execution, reset retries
    elif raw.startswith("[LLM Error") or raw.startswith("[Parse Error") or raw.startswith("[fallback"):
        retries += 1  # failed attempt
    else:
        decisions += 1  # valid decision
        retries = 0
    step += 1

# 记忆系统：局后反思
try:
    import macro_agent as ma
    traj_path = ma.traj_path if hasattr(ma, 'traj_path') else ""
    outcome = "loss" if d[0] else "win"
    print(f"[Trajectory] {traj_path}", flush=True)
    from memory import _extract_key_events, _read_trajectory
    events = _extract_key_events(_read_trajectory(traj_path))
    if events:
        ev_strs = [f'{e["type"]}@{e["frame"]}' for e in events]
        print(f"[Events] detected: {', '.join(ev_strs)}", flush=True)
    else:
        print(f"[Events] none detected", flush=True)
    r = {}
    if agent.client and traj_path:
        r = memory_sys.reflect(HERO_AI, HERO_BOT, outcome, frame, traj_path, agent.client, reflect_path=traj_path) or {}
    # 按 source 分组打印
    source_labels = {
        "KILL": "SYS2(events)", "DEATH": "SYS2(events)", "GOLD_SPIKE": "SYS2(events)",
        "TOWER_FALL": "SYS2(events)", "POWER_SPIKE": "SYS2(events)", "MINION_WAVE": "SYS2(events)",
        "PREDICTION": "SYS3(predict)", "ALIGNMENT": "SYS4(align)", "GLOBAL": "SYS3(global)",
        "GLOBAL_ALIGN": "SYS4(global)", "SEED": "seed(rules)",
    }
    by_source = {}
    for tag, items in [("ADDED", r.get("added",[])), ("UPDATED", r.get("updated",[])), ("REFERENCED", r.get("referenced",[]))]:
        for e in items:
            src = e.get("source", "OTHER")
            by_source.setdefault(src, []).append((tag, e))
    # 按预定义顺序输出
    for src in ["SEED","KILL","DEATH","GOLD_SPIKE","TOWER_FALL","POWER_SPIKE","PREDICTION","ALIGNMENT","GLOBAL","GLOBAL_ALIGN","UNKNOWN","OTHER"]:
        if src not in by_source:
            continue
        label = source_labels.get(src, f"SYS?({src})")
        for tag, e in by_source[src]:
            id_str = f"[{e.get('id','')}] " if e.get('id') else ""
            print(f"  {tag} {label}: {id_str}{e['text']} ({e['score']})", flush=True)
    print(f"[Memory] totals: episodic={len(memory_sys.episodic)} semantic={len(memory_sys.semantic)}", flush=True)
except Exception as e:
    print(f"[Memory reflect error] {e}", flush=True)

env.close_game()
mem = memory_sys.debug_summary()
epi_lines = []
for e in mem.get("recent_episodic", []):
    epi_lines.append(f"    [{e['id']}] {e['lesson']}")
sem_lines = []
for s in mem.get("top_semantic", []):
    sem_lines.append(f"    rule: {s['rule']} ({s['supported']}/{s['supported']+s['contradicted']})")
print(f"\nDONE. {step} env steps, {decisions} decisions in {time.time()-start:.0f}s, outcome={outcome}", flush=True)
print(f"[Memory] episodic={mem['episodic_count']} semantic={mem['semantic_count']}", flush=True)
if epi_lines:
    print(f"[Memory] Recent EPISODIC:", flush=True)
    for l in epi_lines: print(l, flush=True)
if sem_lines:
    print(f"[Memory] Top SEMANTIC:", flush=True)
    for l in sem_lines: print(l, flush=True)

# 复制最新 ABS 到 /replays/ (D:\TEMP\replay_tool\Replays\)
try:
    sim_dir = "/workspace/gamecore/gamecore/simulator_output"
    abs_files = sorted(glob.glob(os.path.join(sim_dir, "*.abs")), key=os.path.getmtime, reverse=True)
    if abs_files:
        dst = "/replays"
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(abs_files[0], os.path.join(dst, os.path.basename(abs_files[0])))
        print(f"[Replay] saved {os.path.basename(abs_files[0])} to /replays/", flush=True)
except Exception as e:
    print(f"[Replay copy error] {e}", flush=True)

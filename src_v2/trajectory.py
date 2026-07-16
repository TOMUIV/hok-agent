import json, os, time
from datetime import datetime

TRAJECTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trajectories")

class TrajectoryLogger:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = TRAJECTORY_DIR
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(log_dir, f"trajectory_{ts}.jsonl")
        self.file = open(self.path, "w", encoding="utf-8")
        self.step = 0

    def log_llm_call(self, system_prompt, user_msg, reply, results):
        entry = {
            "step": self.step,
            "time": time.time(),
            "system_prompt": system_prompt[:200],
            "user_msg": user_msg,
            "llm_reply": reply,
            "parsed_results": results,
        }
        self.file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.file.flush()

    def log_action(self, action):
        self.step += 1

    def close(self):
        self.file.close()
        print(f"\nTrajectory saved: {self.path}", flush=True)

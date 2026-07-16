import math

SLIDING_WINDOW_SIZE = 5
EPISODIC_INTERVAL = 30

class EventDetector:
    @staticmethod
    def check(new_state, old_state):
        events = []
        if old_state is None:
            return events
        for tag in ("YOU", "ENEMY"):
            nh = new_state.get(tag, {})
            oh = old_state.get(tag, {})
            nhp = nh.get("hp", 0)
            ohp = oh.get("hp", 0)
            if nhp <= 0 < ohp:
                events.append(f"{tag} died")
            elif ohp > 0 and (ohp - nhp) / max(ohp, 1) > 0.3:
                events.append(f"{tag} lost {(ohp - nhp):.0f}HP")
            ng = nh.get("gold", 0)
            og = oh.get("gold", 0)
            if ng - og >= 250:
                events.append(f"{tag} got kill (+{ng-og}g)")
            elif ng - og >= 50:
                events.append(f"{tag} farmed (+{ng-og}g)")
            nl = nh.get("level", 0)
            ol = oh.get("level", 0)
            if nl > ol:
                events.append(f"{tag} reached Lv{nl}")
        return events

class MemoryManager:
    def __init__(self):
        self.sliding = []
        self.episodic_log = []
        self.episodic_summary = ""
        self.reflection = ""
        self.last_event_frame = 0
        self.old_state = None
        self.frame_count = 0

    def update(self, info, macro_name, result_text=""):
        self.frame_count += 1
        state = self._extract_state(info)
        events = EventDetector.check(state, self.old_state)

        entry = f"F{getattr(info.get('req_pb'),'frame_no',self.frame_count)}:{macro_name}"
        if events:
            entry += f"({'|'.join(events[:2])})"
        if result_text:
            entry += f" [{result_text[:30]}]"
        self.sliding.append(entry)
        if len(self.sliding) > SLIDING_WINDOW_SIZE:
            self.sliding.pop(0)

        if events:
            self.episodic_log.extend(events)
            self.last_event_frame = self.frame_count

        if self.frame_count - self.last_event_frame >= EPISODIC_INTERVAL or events:
            self._compress_episodic()

        self.old_state = state

    def _extract_state(self, info):
        pb = info.get("req_pb")
        if not pb:
            return {}
        state = {}
        for h in getattr(pb, "hero_list", []):
            tag = "YOU" if h.config_id != -999 else "ENEMY"
            state[tag] = {
                "hp": getattr(h, "hp", 0),
                "max_hp": getattr(h, "max_hp", 1),
                "gold": getattr(h, "money", 0),
                "level": getattr(h, "level", 0),
            }
        return state

    def _compress_episodic(self):
        if not self.episodic_log:
            return
        lines = []
        frame = max(1, self.frame_count - EPISODIC_INTERVAL)
        lines.append(f"@F{frame}-{self.frame_count}:")
        for e in self.episodic_log[-6:]:
            lines.append(f"  {e}")
        self.episodic_summary = "\n".join(lines)
        self.episodic_log = []

    def set_reflection(self, text):
        self.reflection = text

    def get_context(self):
        parts = []
        if self.sliding:
            parts.append("=== RECENT ===")
            parts.extend(self.sliding[-3:])
        if self.episodic_summary:
            parts.append("=== EVENTS ===")
            parts.append(self.episodic_summary)
        if self.reflection:
            parts.append("=== LESSON ===")
            parts.append(self.reflection)
        return "\n".join(parts)

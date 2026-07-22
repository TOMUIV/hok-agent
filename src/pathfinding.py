import math

GOAL_SIZE = 800

def astar(px, py, tx, ty, obstacles=None):
    sx, sy = int(px // GOAL_SIZE), int(py // GOAL_SIZE)
    gx, gy = int(tx // GOAL_SIZE), int(ty // GOAL_SIZE)
    if (sx, sy) == (gx, gy):
        return [(tx, ty)]

    obs = set()
    if obstacles:
        for ox, oy, orad in obstacles:
            oxc, oyc = int(ox // GOAL_SIZE), int(oy // GOAL_SIZE)
            r = max(1, int(orad // GOAL_SIZE))
            for dx in range(-r, r+1):
                for dy in range(-r, r+1):
                    obs.add((oxc+dx, oyc+dy))

    def heuristic(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    start, goal = (sx, sy), (gx, gy)
    open_set = {start}
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    max_iter = 200
    for _ in range(max_iter):
        if not open_set:
            break
        current = min(open_set, key=lambda x: f_score.get(x, 999999))
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            result = []
            for cx, cy in path:
                result.append((cx*GOAL_SIZE + GOAL_SIZE//2, cy*GOAL_SIZE + GOAL_SIZE//2))
            result[-1] = (tx, ty)
            return result

        open_set.remove(current)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            nb = (current[0]+dx, current[1]+dy)
            if nb in obs:
                continue
            tg = g_score[current] + math.sqrt(dx*dx+dy*dy)
            if nb not in g_score or tg < g_score[nb]:
                came_from[nb] = current
                g_score[nb] = tg
                f_score[nb] = tg + heuristic(nb, goal)
                open_set.add(nb)
    return [(tx, ty)]

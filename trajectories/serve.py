"""轨迹文件浏览器服务器。
启动:  python trajectories/serve.py [端口]
打开:  http://localhost:23456
"""
import http.server, json, os, glob, urllib.parse, sys, time

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 23456

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _text(self, text, status=200, ct="text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ct)
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = parsed.path

        if path == "/api/files":
            files = sorted(glob.glob(os.path.join(DIR, "*.jsonl")), key=os.path.getmtime, reverse=True)
            items = []
            for f in files:
                name = os.path.basename(f)
                size = os.path.getsize(f)
                mtime = os.path.getmtime(f)
                items.append({"name": name, "size": size, "mtime": mtime, "steps": self._count_lines(f)})
            self._json({"files": items})

        elif path == "/api/data":
            name = query.get("file", [None])[0]
            if not name:
                self._json({"error": "missing file param"}, 400)
                return
            safe = os.path.basename(name)
            fpath = os.path.join(DIR, safe)
            if not os.path.isfile(fpath):
                self._json({"error": "file not found"}, 404)
                return
            lines = []
            with open(fpath, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        lines.append(obj)
                    except json.JSONDecodeError:
                        lines.append({"_parse_error": True, "_raw": line})
            self._json({"file": safe, "entries": lines, "total": len(lines)})

        else:
            super().do_GET()

    def _count_lines(self, fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        except:
            return 0

if __name__ == "__main__":
    httpd = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"📜 轨迹浏览器: http://localhost:{PORT}", flush=True)
    httpd.serve_forever()

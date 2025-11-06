"""Simple server to serve static demo and API endpoint.

Usage:
  python3 scripts/server.py

Endpoints:
  GET /api/journeys -> returns JSON array of extracted records (from output/journeys.jsonl)
  Static files served from `public/` (index at /public/journey_dashboard_demo.html)
"""
import http.server
import json
import socketserver
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8000
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output' / 'journeys.jsonl'
PUBLIC = ROOT / 'public'


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/journeys'):
            if not OUTPUT.exists():
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'[]')
                return

            # parse query params
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            top = int(params.get('top', [0])[0])
            bottom = int(params.get('bottom', [0])[0])
            limit = int(params.get('limit', [0])[0])
            journey_id = params.get('journey_id', [None])[0]
            min_confidence = params.get('min_confidence', [None])[0]

            arr = []
            with OUTPUT.open('r', encoding='utf-8') as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    # normalize confidence for filtering
                    conf = obj.get('extracted', {}).get('confidence')
                    if min_confidence and conf != min_confidence:
                        continue
                    arr.append(obj)

            # apply journey_id filter first
            if journey_id:
                arr = [a for a in arr if str(a.get('source_id')) == str(journey_id) or str(a.get('extracted', {}).get('journey_id')) == str(journey_id)]

            # convert to enriched objects with numeric score for sorting
            def score_num(item):
                s = item.get('extracted', {}).get('score')
                try:
                    return float(s)
                except Exception:
                    return float('nan')

            # sort by score desc
            arr_sorted = sorted(arr, key=lambda x: (score_num(x) if not (score_num(x) != score_num(x)) else -999999), reverse=True)

            result = None
            if top > 0:
                result = arr_sorted[:top]
            elif bottom > 0:
                # bottom: lowest scores
                arr_sorted_bottom = sorted(arr, key=lambda x: (score_num(x) if not (score_num(x) != score_num(x)) else 999999))
                result = arr_sorted_bottom[:bottom]
            else:
                result = arr_sorted

            if limit > 0:
                result = result[:limit]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            return

        # serve static files from public/
        if self.path == '/' or self.path == '/index.html':
            self.path = '/public/journey_dashboard_demo.html'
        else:
            # rewrite path to public if it's not an API path
            if self.path.startswith('/public/'):
                pass
            else:
                # attempt to serve from public first
                self.path = '/public' + self.path

        return http.server.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == '__main__':
    import os
    os.chdir(str(ROOT))
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT} (CTRL+C to quit)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('Stopping server')
            httpd.server_close()

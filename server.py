"""Cloud Run production web server and API for Telco Enterprise Agents portal."""
import http.server
import json
import os
from pathlib import Path
import socketserver
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", 8080))
HOST = "0.0.0.0"

# Pre-load registry
registry_path = REPO_ROOT / "_shared" / "table_registry.yaml"
registry_data = {}
if registry_path.exists():
    try:
        registry_data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Warning: Failed to load table registry: {e}", file=sys.stderr)


class TelcoPortalHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def do_GET(self):
        # Health check endpoint for Cloud Run
        if self.path in ("/healthz", "/health", "/_health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "HEALTHY", "service": "telco-enterprise-agents"}')
            return

        # API endpoint returning all registered Telco agents
        if self.path == "/api/agents":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(registry_data, indent=2).encode("utf-8"))
            return

        # Default route serves index.html
        if self.path in ("/", ""):
            self.path = "/index.html"

        return super().do_GET()

    def log_message(self, format, *args):
        # Concise structured access logs
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}\n")
        sys.stdout.flush()


def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), TelcoPortalHandler) as httpd:
        print(f"🚀 Telco Enterprise Agents Portal listening on http://{HOST}:{PORT}", flush=True)
        print(f"📊 Serving 45 Enterprise Agents across 5 Domains", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...", flush=True)
            httpd.server_close()


if __name__ == "__main__":
    run()

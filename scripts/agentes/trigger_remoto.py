#!/usr/bin/env python3
"""
Servidor HTTP minimal para trigger remoto do sync_all_custos.sh.

Uso:
  python3 trigger_remoto.py [--port 8802] [--token SECRETO]

  Trigger remoto:
    curl -X POST http://SERVER:8802/trigger -H "Authorization: Bearer SECRETO"

  Health check:
    curl http://SERVER:8802/health
"""
import os, sys, json, subprocess, logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 8802
TOKEN = sys.argv[sys.argv.index('--token') + 1] if '--token' in sys.argv else os.environ.get('TRIGGER_TOKEN', '')
LOG_DIR = '/opt/nfelazarus/logs'
SCRIPT = '/opt/nfelazarus/scripts/agentes/sync_all_custos.sh'

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/trigger_remoto.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('trigger')


class TriggerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_json({'status': 'ok', 'ts': datetime.now().isoformat()})
        else:
            self.send_error(404, 'Use POST /trigger ou GET /health')

    def do_POST(self):
        if self.path != '/trigger':
            self.send_error(404)
            return

        auth = self.headers.get('Authorization', '')
        if TOKEN and auth != f'Bearer {TOKEN}':
            self.send_json({'error': 'unauthorized'}, 401)
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            body = {}

        job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        log.info(f'Trigger recebido (job={job_id})')

        # Run in background, capture output to log file
        log_file = f'{LOG_DIR}/sync_{job_id}.log'
        cmd = f'bash {SCRIPT} > {log_file} 2>&1 & echo $!'
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        pid = proc.stdout.strip()

        self.send_json({
            'status': 'started',
            'job_id': job_id,
            'pid': pid,
            'log': log_file,
        })
        log.info(f'Sync iniciado (job={job_id}, pid={pid})')

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, fmt, *args):
        log.info(f'{self.client_address[0]} - {fmt % args}')


def main():
    if not TOKEN:
        log.warning('TOKEN nao definido! Use --token ou env TRIGGER_TOKEN')

    server = HTTPServer(('0.0.0.0', PORT), TriggerHandler)
    log.info(f'Servidor trigger ouvindo em :{PORT}')
    log.info(f'POST /trigger  → executa {SCRIPT}')
    log.info(f'GET  /health   → health check')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Encerrando...')
        server.server_close()


if __name__ == '__main__':
    main()

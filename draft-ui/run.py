import argparse
import logging
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import assets
import bridge
from server import Handler, STATIC, UI

def main()->None:
  parser = argparse.ArgumentParser(description="Run Sol's local draft editor")
  parser.add_argument("version", type=int, help="Sol version, e.g. 1 for configs/sol_1.py")
  parser.add_argument("--port", type=int, default=8765)
  args = parser.parse_args()
  try: bridge.validate_version(args.version)
  except ValueError as error: parser.error(str(error))
  if not 1 <= args.port <= 65535: parser.error("Port must be between 1 and 65535")
  assert all((UI / filename).is_file() for filename, _ in STATIC.values()), "UI files are missing"
  logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
  handler = partial(Handler, version=args.version, champions=bridge.champions(), evaluator=bridge.evaluator,
                    artwork=assets.load_catalogue())
  try: server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
  except OSError as error: parser.error(str(error))
  with server:
    print(f"Sol {args.version} draft editor: http://127.0.0.1:{args.port}", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == "__main__": main()

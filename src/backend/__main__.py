"""اجرای سرور توسعه: ``python -m backend [--host H] [--port P]``."""

from __future__ import annotations

import argparse

from backend.app import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Roshd Wind Pathfinder backend (dev server)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = serve(args.host, args.port)
    print(f"Serving on http://{args.host}:{args.port}/v1  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.app.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()

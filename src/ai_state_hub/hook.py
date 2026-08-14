from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7800)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--state", required=True)
    args = parser.parse_args()
    payload = json.dumps(vars(args)).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{args.port}/api/hook",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=1).close()
    except OSError:
        pass


if __name__ == "__main__":
    main()


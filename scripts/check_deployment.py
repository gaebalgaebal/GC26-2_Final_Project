"""Explicit, one-shot public deployment check. No credentials required."""
import argparse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("url", help="Actual deployed HTTPS URL")
args = parser.parse_args()
if not args.url.startswith("https://"):
    parser.error("Use the actual HTTPS deployment URL")
try:
    with urllib.request.urlopen(args.url, timeout=20) as response:
        print(f"HTTP {response.status}: {response.url}")
        if response.status != 200:
            raise SystemExit(1)
except Exception as exc:
    print(f"Deployment check failed: {type(exc).__name__}")
    raise SystemExit(1)

"""Explicit, one-shot public deployment check. No credentials required."""
import argparse
import http.cookiejar
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("url", help="Actual deployed HTTPS URL")
args = parser.parse_args()
if not args.url.startswith("https://"):
    parser.error("Use the actual HTTPS deployment URL")
try:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request = urllib.request.Request(args.url, headers={"User-Agent": "AssessmentDeploymentCheck/1.0"})
    with opener.open(request, timeout=20) as response:
        print(f"HTTP {response.status}: {response.url}")
        if response.status != 200:
            raise SystemExit(1)
except urllib.error.HTTPError as exc:
    print(f"HTTP {exc.code}: browser verification is required; this HTTP result alone does not prove the app is unavailable.")
    raise SystemExit(1)
except Exception as exc:
    print(f"Deployment check failed: {type(exc).__name__}")
    raise SystemExit(1)

"""Experiment A, variant `informed`: collect what the isolated reviewer deliberately does
not get (PR description, spec.md, design.md). Runs in a non-agent step. Prints JSON."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

pr, issue = sys.argv[1], sys.argv[2]
repo = os.environ["GITHUB_REPOSITORY"]
body = subprocess.run(["gh", "pr", "view", pr, "--repo", repo, "--json", "body", "-q", ".body"],
                      capture_output=True, text=True).stdout
out = {"PR description": body}
for name in ("spec.md", "design.md"):
    url = f"https://raw.githubusercontent.com/{repo}/autose-artifacts/issue-{issue}/latest/{name}"
    try:
        out[name] = urllib.request.urlopen(url, timeout=20).read().decode("utf-8")
    except Exception:
        out[name] = ""
print(json.dumps(out))

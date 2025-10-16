#!/usr/bin/env python3
"""
update_wakatime_readme.py

Fetches WakaTime stats and updates a README section between:
<!-- WAKATIME:START -->
...content...
<!-- WAKATIME:END -->

Environment variables required:
- WAKATIME_API_KEY  (your waka_... key)
- GITHUB_TOKEN      (GitHub token, provided automatically in Actions)
- REPO              (e.g. rezaestifai/RezaEstifai)
Optional:
- BRANCH (default: main)
- README_PATH (default: README.md)
- TIME_RANGE (default: today)  # or: last_7_days, yesterday, etc.
- DRY_RUN (1 or true = only print, no commit)
"""
import os
import sys
import base64
import requests

WAKATIME_API = "https://wakatime.com/api/v1/users/current/stats/"
MARKER_START = "<!-- WAKATIME:START -->"
MARKER_END = "<!-- WAKATIME:END -->"

def get_env(name, default=None):
    val = os.getenv(name, default)
    return val if val not in ("", None) else default

def fetch_wakatime_stats(api_key, time_range):
    url = WAKATIME_API + time_range
    headers = {
        "Authorization": "Basic " + base64.b64encode((api_key + ":").encode()).decode()
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def human_time_from_seconds(seconds):
    if not seconds or seconds <= 0:
        return "0 secs"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s and not h: parts.append(f"{s}s")
    return " ".join(parts)

def build_markdown_block(stats, time_range):
    data = stats.get("data", {})
    total_sec = data.get("grand_total", {}).get("total_seconds", 0)
    total_str = human_time_from_seconds(total_sec)
    langs = data.get("languages", [])

    lines = []
    lines.append(MARKER_START)
    lines.append(f"**WakaTime — {time_range.replace('_', ' ')}**  ")
    lines.append("")
    lines.append(f"**Total time:** **{total_str}**  ")
    lines.append("")
    if langs:
        lines.append("**Languages:**  ")
        top_langs = sorted(langs, key=lambda x: x.get("total_seconds", 0), reverse=True)[:5]
        for lang in top_langs:
            name = lang.get("name", "Unknown")
            secs = lang.get("total_seconds", 0)
            pct = lang.get("percent", 0)
            time_str = human_time_from_seconds(secs)
            lines.append(f"- {name}: {time_str} ({pct}%)")
        lines.append("")
    else:
        lines.append("No activity tracked  ")
        lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)

def replace_section_in_readme(original, new_block):
    if MARKER_START in original and MARKER_END in original:
        start = original.index(MARKER_START)
        end = original.index(MARKER_END, start) + len(MARKER_END)
        return original[:start] + new_block + original[end:]
    else:
        return original + "\n\n" + new_block

def get_github_file(repo, path, branch, token):
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def update_github_file(repo, path, branch, token, new_content, sha, message):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    payload = {
        "message": message,
        "content": base64.b64encode(new_content.encode()).decode(),
        "branch": branch,
        "sha": sha
    }
    r = requests.put(url, headers=headers, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

def main():
    api_key = get_env("WAKATIME_API_KEY")
    repo = get_env("REPO")
    token = get_env("GITHUB_TOKEN")
    if not api_key or not repo or not token:
        print("Missing WAKATIME_API_KEY, REPO, or GITHUB_TOKEN")
        return 1

    branch = get_env("BRANCH", "main")
    readme_path = get_env("README_PATH", "README.md")
    time_range = get_env("TIME_RANGE", "today")
    dry_run = str(get_env("DRY_RUN", "0")).lower() in ("1", "true", "yes")

    print(f"Fetching WakaTime data for {time_range}...")
    stats = fetch_wakatime_stats(api_key, time_range)

    block = build_markdown_block(stats, time_range)
    print("\n--- Generated Block ---")
    print(block)
    print("-----------------------\n")

    if dry_run:
        print("DRY_RUN is on; not updating README.")
        return 0

    print("Fetching current README from GitHub...")
    file_info = get_github_file(repo, readme_path, branch, token)
    sha = file_info["sha"]
    content = base64.b64decode(file_info["content"]).decode()

    updated = replace_section_in_readme(content, block)
    if updated == content:
        print("No changes to README.")
        return 0

    print("Committing updated README...")
    resp = update_github_file(
        repo,
        readme_path,
        branch,
        token,
        updated,
        sha,
        f"Update WakaTime stats ({time_range})"
    )
    print("✅ Updated:", resp.get("content", {}).get("html_url", "(no url)"))
    return 0

if __name__ == "__main__":
    sys.exit(main())

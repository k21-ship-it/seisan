#!/usr/bin/env python3
"""
Cloudflare Pages デプロイスクリプト
使い方: python3 deploy.py
"""
import hashlib, json, subprocess, sys

import os

ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "e0435f57308162cdb857e0e99ebff51a")
CF_TOKEN   = os.environ.get("CF_TOKEN", "")
GH_TOKEN   = os.environ.get("GH_TOKEN", "")
PROJECT    = "seisan"
GH_REPO    = "k21-ship-it/seisan"

# トークンが未設定の場合は .env ファイルから読み込む
if not CF_TOKEN or not GH_TOKEN:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
        CF_TOKEN  = os.environ.get("CF_TOKEN", CF_TOKEN)
        GH_TOKEN  = os.environ.get("GH_TOKEN", GH_TOKEN)

FILES = {
    "/index.html": "index.html",
    "/_headers":   "_headers",
}

def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def cf(method, path, **kwargs):
    import urllib.request, urllib.error
    url = f"https://api.cloudflare.com/client/v4{path}"
    data = json.dumps(kwargs["json"]).encode() if "json" in kwargs else None
    req = urllib.request.Request(url, data=data, method=method,
          headers={"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def deploy():
    print("🚀 Cloudflare Pages にデプロイ中...")

    # 1. マニフェスト作成
    manifest = {k: sha256(v) for k, v in FILES.items()}

    # 2. デプロイ作成 + ファイルアップロード
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT}/deployments",
        "-H", f"Authorization: Bearer {CF_TOKEN}",
        "-F", f"manifest={json.dumps(manifest)}"
    ]
    for path, local in FILES.items():
        cmd += ["-F", f"{path.lstrip('/')}=@{local};type=application/octet-stream"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    d = json.loads(result.stdout)
    if not d.get("success"):
        print("❌ デプロイ失敗:", d.get("errors"))
        return False

    deploy_id = d["result"]["id"]
    url = d["result"]["url"]
    print(f"✅ デプロイ成功!")
    print(f"   プレビュー: {url}")
    print(f"   本番: https://seisan.pages.dev")
    return True

def push_github():
    print("📦 GitHub に push 中...")
    result = subprocess.run([
        "git", "push",
        f"https://k21-ship-it:{GH_TOKEN}@github.com/{GH_REPO}.git",
        "main"
    ], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ GitHub push 成功")
    else:
        print("❌ GitHub push 失敗:", result.stderr[:200])

if __name__ == "__main__":
    push_github()
    deploy()

"""
タスクの締切3日前にDiscordへ通知するスクリプト。
GitHub Actionsから毎朝実行される。

必要なGitHub Secrets:
  FIREBASE_PROJECT_ID       — FirebaseプロジェクトID
  FIREBASE_SERVICE_ACCOUNT  — サービスアカウントJSON（文字列）
  DISCORD_WEBHOOK_URL       — DiscordウェブフックURL
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from google.cloud import firestore
from google.oauth2 import service_account

JST = timezone(timedelta(hours=9))
today = datetime.now(JST).date()
target = today + timedelta(days=3)

# Firestore接続
sa_json = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
creds = service_account.Credentials.from_service_account_info(sa_json)
db = firestore.Client(
    project=os.environ["FIREBASE_PROJECT_ID"],
    credentials=creds,
)

# 締切3日前・未完了タスクを検索
snap = (
    db.collection("tasks")
    .where("status", "==", "未完了")
    .stream()
)

targets = []
for doc in snap:
    data = doc.to_dict()
    dl = data.get("deadline")
    if not dl:
        continue
    try:
        dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
    except ValueError:
        continue
    if dl_date == target:
        targets.append(data)

if not targets:
    print(f"[{today}] 締切3日前のタスクなし")
    raise SystemExit(0)

# Discord通知
embeds = [
    {
        "title": f"⏰ {t['title']}",
        "description": (
            f"📁 フォルダ: **{t.get('folder','未分類')}**\n"
            f"📅 締切: **{t['deadline']}**\n"
            + (f"📝 {t['note']}" if t.get("note") else "")
        ),
        "color": 0x3730E8,
    }
    for t in targets
]

payload = {
    "content": f"**締切まで3日のタスクが{len(targets)}件あります！**",
    "embeds": embeds,
}

req = urllib.request.Request(
    os.environ["DISCORD_WEBHOOK_URL"],
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
urllib.request.urlopen(req)
print(f"[{today}] Discord通知送信: {len(targets)}件")
for t in targets:
    print(f"  - {t['title']} ({t['deadline']})")

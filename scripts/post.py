# -*- coding: utf-8 -*-
# GitHub Actions 클라우드 발행기: queue.json에서 발행 시각이 된 카드 1건을 Make 웹훅으로 발행하고 posted 처리.
import json, os, sys, datetime, urllib.request

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
WEBHOOK = os.environ.get("MAKE_WEBHOOK", "").strip()
if not WEBHOOK:
    print("ERROR: MAKE_WEBHOOK secret not set"); sys.exit(1)

with open("queue.json", encoding="utf-8") as f:
    q = json.load(f)

def slot_dt(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=KST)

# 발행 시각이 지났고 아직 안 올린 항목
due = [x for x in q if not x.get("posted") and slot_dt(x["slot"]) <= now]
if not due:
    print("no due items"); sys.exit(0)

# 스팸 안전장치: 마지막 발행 후 2시간 안 지났으면 스킵
posted_times = []
for x in q:
    if x.get("posted") and x.get("posted_at"):
        try: posted_times.append(slot_dt(x["posted_at"]))
        except Exception: pass
if posted_times and (now - max(posted_times)).total_seconds() < 2 * 3600:
    print("too soon since last post; skip"); sys.exit(0)

# 한 번에 1건만 (가장 이른 슬롯)
due.sort(key=lambda x: x["slot"])
target = due[0]
print("posting:", target["id"], "slot", target["slot"])

payload = json.dumps({"image_url": target["image_url"], "caption": target["caption"]}, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(WEBHOOK, data=payload, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
try:
    resp = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore").strip()
except Exception as e:
    print("webhook error:", e); sys.exit(1)
print("webhook response:", resp)
if resp != "Accepted":
    print("publish FAILED (response not Accepted) - keeping unposted for retry"); sys.exit(1)

# 성공 표시
for x in q:
    if x["id"] == target["id"]:
        x["posted"] = True
        x["posted_at"] = now.strftime("%Y-%m-%d %H:%M")
with open("queue.json", "w", encoding="utf-8") as f:
    json.dump(q, f, ensure_ascii=False, indent=2)
print("DONE posted", target["id"])

"""只用于测试 JSONL 分帧及乱序响应，不进入产品安装包。"""
import json
import sys

waiting = None
for line in sys.stdin.buffer:
    command = json.loads(line)
    response = {"type": "response", "id": command["id"], "command": command["type"], "success": True, "data": {}}
    if command["type"] == "first":
        waiting = response
        continue
    if command["type"] == "second":
        response["data"] = {"text": "a\u2028b\u2029c"}
    print(json.dumps(response, ensure_ascii=False), flush=True)
    if waiting:
        print(json.dumps(waiting), flush=True)
        waiting = None

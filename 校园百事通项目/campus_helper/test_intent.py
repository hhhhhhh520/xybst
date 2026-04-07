# -*- coding: utf-8 -*-
import requests
import json

url = "http://localhost:8000/api/chat"
data = {
    "message": "我的课表是什么",
    "session_id": "test_py",
    "user_id": "user1"
}

response = requests.post(url, json=data)
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

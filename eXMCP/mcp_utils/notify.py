import requests

def notify_webhook(url, agent_id, reason):
    payload = {"agent_id": agent_id, "reason": reason}
    try:
        resp = requests.post(url, json=payload, timeout=3)
        print(f"[Notify] WebHook {url} status: {resp.status_code}")
    except Exception as e:
        print(f"[Notify] WebHook failed: {e}") 
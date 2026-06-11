"""One-off: resolve the WhatsApp group chat ID by name.
Usage: GREENAPI_ID_INSTANCE=... GREENAPI_TOKEN=... python -m scripts.find_group "The Mighty Falcones"
"""
import os, sys, requests

def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python -m scripts.find_group "<group name>"')
    host = os.environ.get("GREENAPI_HOST", "api.green-api.com")
    url = f"https://{host}/waInstance{os.environ['GREENAPI_ID_INSTANCE']}/getContacts/{os.environ['GREENAPI_TOKEN']}"
    target = sys.argv[1].lower()
    found = False
    for c in requests.get(url, timeout=60).json():
        if c.get("id", "").endswith("@g.us") and target in (c.get("name") or "").lower():
            print(f"{c['name']}  ->  {c['id']}")
            found = True
    if not found:
        print("No matching group found. Is the instance authorized (QR scanned) and the number in the group?")

if __name__ == "__main__":
    main()

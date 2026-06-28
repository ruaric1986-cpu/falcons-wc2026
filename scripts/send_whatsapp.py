import os

def _post(url, payload):
    import requests
    return requests.post(url, json=payload, timeout=30)

def send(message):
    if os.environ.get("DRY_RUN"):
        print("=== DRY RUN — would send to WhatsApp ===")
        print(message)
        return
    host = os.environ.get("GREENAPI_HOST", "7107.api.greenapi.com")
    url = (f"https://{host}/waInstance{os.environ['GREENAPI_ID_INSTANCE']}"
           f"/sendMessage/{os.environ['GREENAPI_TOKEN']}")
    resp = _post(url, {"chatId": os.environ["WHATSAPP_GROUP_ID"], "message": message})
    resp.raise_for_status()
    print(f"Sent: {resp.json()}")

def send_file(url_file, caption="", file_name="file"):
    """Send a file to the group as a document with an optional caption (Green-API sendFileByUrl).
    url_file must be a publicly reachable URL (Green-API fetches it server-side)."""
    if os.environ.get("DRY_RUN"):
        print(f"=== DRY RUN — would send file {file_name} ({url_file}) with caption ===")
        print(caption)
        return
    host = os.environ.get("GREENAPI_HOST", "7107.api.greenapi.com")
    url = (f"https://{host}/waInstance{os.environ['GREENAPI_ID_INSTANCE']}"
           f"/sendFileByUrl/{os.environ['GREENAPI_TOKEN']}")
    resp = _post(url, {"chatId": os.environ["WHATSAPP_GROUP_ID"], "urlFile": url_file,
                       "fileName": file_name, "caption": caption})
    resp.raise_for_status()
    print(f"Sent file: {resp.json()}")

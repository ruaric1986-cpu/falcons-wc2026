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

def send_file(path, caption="", file_name=None):
    """Send a file to the group as a document with an optional caption (Green-API sendFileByUpload)."""
    file_name = file_name or os.path.basename(path)
    if os.environ.get("DRY_RUN"):
        print(f"=== DRY RUN — would send file {file_name} with caption ===")
        print(caption)
        return
    import requests
    host = os.environ.get("GREENAPI_HOST", "7107.api.greenapi.com")
    media = host.replace(".api.", ".media.") if ".api." in host else host  # uploads use the media host
    url = (f"https://{media}/waInstance{os.environ['GREENAPI_ID_INSTANCE']}"
           f"/sendFileByUpload/{os.environ['GREENAPI_TOKEN']}")
    with open(path, "rb") as fh:
        resp = requests.post(
            url,
            data={"chatId": os.environ["WHATSAPP_GROUP_ID"], "fileName": file_name, "caption": caption},
            files={"file": (file_name, fh, "application/octet-stream")},
            timeout=120,
        )
    resp.raise_for_status()
    print(f"Sent file: {resp.json()}")

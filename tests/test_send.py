from scripts.send_whatsapp import send

def test_dry_run_prints_instead_of_sending(monkeypatch, capsys):
    monkeypatch.setenv("DRY_RUN", "1")
    send("hello falcons")
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "hello falcons" in out

def test_real_send_posts(monkeypatch):
    calls = {}
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.setenv("GREENAPI_ID_INSTANCE", "1234567890")
    monkeypatch.setenv("GREENAPI_TOKEN", "tok")
    monkeypatch.setenv("WHATSAPP_GROUP_ID", "120363000000000000@g.us")
    monkeypatch.setenv("GREENAPI_HOST", "7107.api.greenapi.com")
    import scripts.send_whatsapp as sw
    class FakeResp:
        status_code = 200
        def json(self): return {"idMessage": "x"}
        def raise_for_status(self): pass
    monkeypatch.setattr(sw, "_post", lambda url, payload: calls.update(url=url, payload=payload) or FakeResp())
    sw.send("msg")
    assert calls["url"] == "https://7107.api.greenapi.com/waInstance1234567890/sendMessage/tok"
    assert calls["payload"] == {"chatId": "120363000000000000@g.us", "message": "msg"}

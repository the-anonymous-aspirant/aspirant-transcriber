from unittest.mock import patch

from app.models import VoiceMessage


def _upload(client, tmp_path, filename="test.wav", content=None, mime="audio/wav"):
    """Upload helper that patches storage path and disables background transcription."""
    audio_bytes = content or b"\x00" * 1024
    with patch("app.routes.AUDIO_STORAGE_PATH", str(tmp_path)), \
         patch("app.routes.process_transcription"):
        return client.post(
            "/voice-messages",
            files={"file": (filename, audio_bytes, mime)},
        )


def test_upload_returns_202(client, tmp_path):
    response = _upload(client, tmp_path)
    assert response.status_code == 202


def test_upload_response_shape(client, tmp_path):
    response = _upload(client, tmp_path)
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert "message" in data


def test_upload_creates_db_record(client, db, tmp_path):
    response = _upload(client, tmp_path)
    data = response.json()
    msg = db.query(VoiceMessage).filter(VoiceMessage.id == data["id"]).first()
    assert msg is not None
    assert msg.status == "pending"
    assert msg.original_filename == "test.wav"


def test_upload_rejects_unsupported_extension(client, tmp_path):
    response = _upload(client, tmp_path, filename="test.txt", mime="text/plain")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_upload_rejects_oversized_file(client, tmp_path):
    big_file = b"\x00" * (26 * 1024 * 1024)  # 26 MB
    response = _upload(client, tmp_path, content=big_file)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "validation_error"


def test_list_returns_200(client):
    response = client.get("/voice-messages")
    assert response.status_code == 200


def test_list_response_shape(client):
    response = client.get("/voice-messages")
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_list_pagination_defaults(client):
    response = client.get("/voice-messages")
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_nonexistent_returns_404(client):
    response = client.get("/voice-messages/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "not_found"


def test_delete_nonexistent_returns_404(client):
    response = client.delete("/voice-messages/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "not_found"


def test_upload_then_get(client, db, tmp_path):
    upload_resp = _upload(client, tmp_path)
    message_id = upload_resp.json()["id"]

    get_resp = client.get(f"/voice-messages/{message_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == message_id
    assert data["original_filename"] == "test.wav"
    assert data["status"] == "pending"


def test_upload_then_delete(client, db, tmp_path):
    upload_resp = _upload(client, tmp_path)
    message_id = upload_resp.json()["id"]

    delete_resp = client.delete(f"/voice-messages/{message_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/voice-messages/{message_id}")
    assert get_resp.status_code == 404

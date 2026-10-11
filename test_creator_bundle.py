import httpx
from fastapi.testclient import TestClient

from creator_bundle_service import app, get_pdf_client
from infrai_pdf import InfraiPdfClient


def test_public_preview_selects_first_two_pages_and_merges_them() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/pdf/split":
            return httpx.Response(200, json={"ok": True, "data": {"outputs": ["page-1", "page-2", "page-3"]}, "error": None, "metadata": {}})
        return httpx.Response(200, json={"ok": True, "data": {"pdf": "preview-pdf"}, "error": None, "metadata": {}})

    pdf_client = InfraiPdfClient(api_key="test-key", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    app.dependency_overrides[get_pdf_client] = lambda: pdf_client
    try:
        response = TestClient(app).post(
            "/bundles/publish",
            json={"source_pdf": "asset-pdf", "audience": "public", "preview_pages": 2, "request_id": "release-42"},
        )
    finally:
        app.dependency_overrides.clear()
        pdf_client.close()

    assert response.status_code == 200
    assert response.json() == {"audience": "public", "included_pages": 2, "delivery": {"pdf": "preview-pdf"}}
    assert [request.url.path for request in requests] == ["/v1/pdf/split", "/v1/pdf/merge"]
    assert requests[0].read() == b'{"pdf":"asset-pdf","ranges":["1-"]}'
    assert requests[1].read() == b'{"inputs":["page-1","page-2"]}'
    assert requests[1].headers["Idempotency-Key"] == "release-42:merge"


def test_subscriber_delivery_keeps_update_pages() -> None:
    class RecordingClient:
        merged: list[str] = []

        def split(self, pdf: str, request_id: str) -> dict[str, list[str]]:
            return {"outputs": ["cover", "guide", "subscriber-update"]}

        def merge(self, inputs: list[str], request_id: str) -> dict[str, str]:
            self.merged = inputs
            return {"pdf": "subscriber-pdf"}

    client = RecordingClient()
    app.dependency_overrides[get_pdf_client] = lambda: client
    try:
        response = TestClient(app).post(
            "/bundles/publish",
            json={"source_pdf": "asset-pdf", "audience": "subscriber", "preview_pages": 1, "request_id": "release-43"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["included_pages"] == 3
    assert client.merged == ["cover", "guide", "subscriber-update"]

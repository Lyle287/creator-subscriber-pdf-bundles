from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from infrai_pdf import InfraiError, InfraiPdfClient


class PublishBundleRequest(BaseModel):
    source_pdf: str = Field(min_length=1)
    audience: Literal["public", "subscriber"]
    preview_pages: int = Field(default=2, ge=1)
    request_id: str = Field(default_factory=lambda: str(uuid4()), min_length=8)


class BundleResult(BaseModel):
    audience: Literal["public", "subscriber"]
    included_pages: int
    delivery: dict[str, Any]


def select_delivery_pages(split_pages: list[str], audience: str, preview_pages: int) -> list[str]:
    if not split_pages:
        raise ValueError("The processed document has no pages")
    if audience == "subscriber":
        return split_pages
    return split_pages[:preview_pages]


def get_pdf_client() -> InfraiPdfClient:
    client = InfraiPdfClient()
    try:
        yield client
    finally:
        client.close()


app = FastAPI(title="Creator document bundle service")


@app.post("/bundles/publish", response_model=BundleResult)
def publish_bundle(
    request: PublishBundleRequest,
    client: InfraiPdfClient = Depends(get_pdf_client),
) -> BundleResult:
    try:
        split_result = client.split(request.source_pdf, request.request_id)
        raw_pages = split_result.get("outputs")
        if not isinstance(raw_pages, list) or not all(isinstance(page, str) for page in raw_pages):
            raise RuntimeError("PDF split result did not contain string outputs")
        pages = select_delivery_pages(raw_pages, request.audience, request.preview_pages)
        delivery = client.merge(pages, request.request_id)
        return BundleResult(audience=request.audience, included_pages=len(pages), delivery=delivery)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc


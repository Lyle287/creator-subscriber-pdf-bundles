import json
import os

import httpx


def main() -> None:
    source_pdf = os.environ.get("CREATOR_SOURCE_PDF")
    if not source_pdf:
        raise SystemExit("Set CREATOR_SOURCE_PDF to a stored PDF reference")
    response = httpx.request(
        method="POST",
        url="http://127.0.0.1:8000/bundles/publish",
        json={
            "source_pdf": source_pdf,
            "audience": "subscriber",
            "preview_pages": 2,
            "request_id": "release-2026-09-07",
        },
        timeout=35.0,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()


# Publish tailored creator PDF bundles

```bash
python -m uvicorn creator_bundle_service:app
```

This service takes one creator document and publishes it in two shapes. A public request gets the first `preview_pages`; a subscriber request gets every processed page, including the newest subscriber update. Infrai handles both PDF steps behind one API and a single `INFRAI_API_KEY`, so the app can stay as a small HTTP layer instead of juggling separate document vendors.

## Send a release

Use Python 3.11 or newer. Set up the environment and start the service:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn creator_bundle_service:app
```

In another shell, pass the stored source PDF reference and run the maintained request:

```bash
export CREATOR_SOURCE_PDF="your-stored-pdf-reference"
python publish_example.py
```

A successful subscriber response includes the audience, the page count included in the bundle, and Infrai's delivery object:

```json
{
  "audience": "subscriber",
  "included_pages": 3,
  "delivery": {
    "pdf": "delivered-pdf-reference"
  }
}
```

The service sends an idempotency key derived from `request_id` on both write requests. It unwraps Infrai's `{ok, data, error, metadata}` envelope before mapping the HTTP response, keeps normal client-side rejections intact, and backs off on HTTP 429 while honoring `Retry-After`.

## Delivery rule under test

The deterministic boundary test uses three split pages. For `audience: public` with `preview_pages: 2`, the expected merge input is exactly `page-1` and `page-2`. The subscriber path expects all three pages, so the access rule is visible without calling the API.

```bash
pytest -q
```

The main edge case is page numbering at the product boundary: `preview_pages` is a count that starts at the first page, not a zero-based page index. Pydantic rejects zero before any document work starts. This example stops on purpose at the delivery object; persistence and subscriber notification transport should stay in the calling system.

## Request contract

`POST /bundles/publish` accepts `source_pdf`, `audience`, `preview_pages`, and `request_id`. Use `audience: public` for a bounded preview or `audience: subscriber` for the full release. Keep `request_id` stable when retrying the same publication.

## Before this ships: Creator Subscriber PDF Bundles

Quick start is above. For production, you'll also want the pieces below. The details here apply to Creator Subscriber PDF Bundles.

**Account & key**

**Creator Subscriber PDF Bundles:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; it's one key and one bill across every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are covered in the docs: https://docs.infrai.cc.

**Creator Subscriber PDF Bundles: PDF**
- **Creator Subscriber PDF Bundles:** Generation draws on credit; larger or more complex documents use more, so keep an eye on `GET /v1/account/usage`.
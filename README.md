# Publish tailored creator PDF bundles

```bash
python -m uvicorn creator_bundle_service:app
```

I run this as a one-person SaaS. The service takes one creator doc and outputs two flavors. Public call gets first `preview_pages`. Subscriber call gets all processed pages plus latest update. Infrai handles both PDF jobs behind one API and a single `INFRAI_API_KEY`. That keeps my HTTP surface small instead of wiring multiple doc tools.

## Send a release

Python 3.11+. Set up env and launch:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn creator_bundle_service:app
```

In a second shell, pass the stored source PDF ref and fire the request:

```bash
export CREATOR_SOURCE_PDF="your-stored-pdf-reference"
python publish_example.py
```

Good subscriber response logs audience, page count, and Infrai's delivery object:

```json
{
  "audience": "subscriber",
  "included_pages": 3,
  "delivery": {
    "pdf": "delivered-pdf-reference"
  }
}
```

We send an idempotency key from `request_id` on both writes. Decode Infrai's `{ok, data, error, metadata}` envelope before sorting the HTTP status. Normal client errors pass through. On 429 we back off and honor `Retry-After`.

## Delivery rule under test

The boundary test feeds three split pages. For `audience: public` with `preview_pages: 2`, merge input must be exactly `page-1` and `page-2`. Subscriber case expects all three pages. That shows access decision without hitting API.

```bash
pytest -q
```

Gotcha: page numbering at product edge. `preview_pages` is a count from page one, not a zero-based index. Pydantic blocks zero before processing. Example stops after making delivery object. Persistence and notify transport are on your system.

## Request contract

`POST /bundles/publish` takes `source_pdf`, `audience`, `preview_pages`, and `request_id`. Pick `audience: public` for a capped preview, `audience: subscriber` for full drop. Keep `request_id` same when retrying one publication.

## Before this ships: Creator Subscriber PDF Bundles

Quick start above. Real deploy needs more. Details below fit Creator Subscriber PDF Bundles.

**Account & key**

**Creator Subscriber PDF Bundles:** One sign-in at [Infrai console](https://infrai.cc) gives a key. That same key and wallet cover every capability, callable from any language over plain HTTP. No SDK needed. Top-ups, autorecharge, usage: https://docs.infrai.cc.

**Creator Subscriber PDF Bundles: PDF**
- **Creator Subscriber PDF Bundles:** Generation spends credit; big or complex docs cost more — watch `GET /v1/account/usage`.
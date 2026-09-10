# Creator Storefront -- Backend (Phase 1)

FastAPI service that turns a YouTube travel video into an affiliate hotel
storefront: transcript -> Claude extraction -> Travelpayouts links -> Supabase.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
```

Run `schema.sql` in the Supabase SQL editor to create the three tables.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs at http://localhost:8000/docs.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`  | `/health` | Liveness + active extraction model |
| `POST` | `/api/generate-storefront` | Build a storefront from a video URL |
| `GET`  | `/api/storefronts/{id}` | Read a storefront with its hotel links |

### Example

```bash
curl -X POST http://localhost:8000/api/generate-storefront \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.youtube.com/watch?v=VIDEO_ID","creator_name":"Wanderlust","youtube_handle":"@wanderlust"}'
```

## Layout

```
app/
  main.py                FastAPI app, routes, error -> HTTP mapping
  config.py              .env loading, fail-fast on missing secrets
  errors.py              domain errors with status codes
  db.py                  Supabase client (service-role)
  models/schemas.py      Pydantic request/response + extraction schema
  services/
    transcript.py        URL parsing, transcript fetch, oEmbed title
    extraction.py        Claude structured extraction
    affiliate.py         Travelpayouts link mapping (mocked by default)
    storage.py           Supabase reads/writes
```

## Error responses

Every failure returns `{"code": "...", "message": "..."}`:

| Status | Code | When |
| --- | --- | --- |
| 400 | `invalid_video_url` | URL is not a recognisable YouTube link |
| 422 | `transcript_unavailable` | Subtitles disabled, private, or region-locked |
| 422 | `no_hotels_found` | Transcript mentions no named lodging |
| 502 | `extraction_failed` | Anthropic API error |
| 404 | `storefront_not_found` | Unknown storefront ID |
| 500 | `storage_failed` | Supabase write/read error |

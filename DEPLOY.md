# Deploying Trova

Frontend on Vercel, backend on Render, database already on Supabase. Both free
tiers are enough to start. Budget about an hour the first time.

Everything below needs accounts only you can create, so this is a checklist
rather than something that can be automated from here.

---

## Before you start

Trova must be in a **GitHub repo** — both hosts deploy from one.

```bash
cd "C:\Users\johny\trova"
git init && git add -A && git commit -m "Trova: hotels and flights from travel videos"
```

Then create an empty repo on github.com and follow its push instructions.

**Check `.env` and `.env.local` are not in that commit.** Both `.gitignore`
files already exclude them; confirm with `git status` before pushing. If a key
ever does land in a commit, rotate it — deleting the file later does not
remove it from git history.

---

## 1. Backend on Render

1. [render.com](https://render.com) → **New** → **Blueprint**
2. Pick your repo. Render reads [`render.yaml`](render.yaml) and finds the service.
3. It prompts for each secret. Paste from `backend/.env`:

   | Variable | Value |
   | --- | --- |
   | `SUPABASE_URL` | your project URL |
   | `SUPABASE_SECRET_KEY` | the `sb_secret_…` key |
   | `ANTHROPIC_API_KEY` | the `sk-ant-…` key |
   | `TRAVELPAYOUTS_MARKER` | your marker (see §3) |
   | `TRAVELPAYOUTS_API_TOKEN` | your API token |
   | `CORS_ORIGINS` | leave blank for now — §2 fills it |

4. Deploy. You get a URL like `https://trova-api.onrender.com`.
5. Confirm: opening `https://trova-api.onrender.com/health` returns
   `{"status":"ok",...}`.

> **Free tier sleeps after 15 minutes idle.** The first request then takes
> 30–60 seconds to wake. Since generating a storefront already takes ~20s, a
> cold start makes it feel broken. Upgrade to the paid tier before showing
> this to real creators.

---

## 2. Frontend on Vercel

1. [vercel.com](https://vercel.com) → **Add New** → **Project** → your repo
2. Set **Root Directory** to `frontend` — Vercel detects Next.js from there.
3. Add environment variables:

   | Variable | Value |
   | --- | --- |
   | `NEXT_PUBLIC_SUPABASE_URL` | your project URL |
   | `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | the `sb_publishable_…` key |
   | `NEXT_PUBLIC_API_URL` | your Render URL, no trailing slash |
   | `NEXT_PUBLIC_SITE_URL` | your Vercel URL |

4. Deploy. You get `https://trova-<something>.vercel.app`.

**Then go back to Render** and set `CORS_ORIGINS` to that exact Vercel URL —
scheme included, no trailing slash:

```
CORS_ORIGINS=https://trova-abc123.vercel.app
```

Render redeploys. Until you do this, the dashboard loads but every "Build
storefront" fails with a CORS error in the browser console. This is the single
most common way a first deploy goes wrong.

Using a custom domain later? Add it to `CORS_ORIGINS` too, comma-separated.

---

## 3. Travelpayouts credentials

Until this is done, links work but **earn nothing** — `check_setup.py` warns
about it, and so does the backend at boot.

1. Sign up at [travelpayouts.com](https://www.travelpayouts.com)
2. **Profile** → copy your **marker** (a number — this is your affiliate ID)
3. **Developers → API tokens** → create one → copy it
4. Set `TRAVELPAYOUTS_MARKER`, `TRAVELPAYOUTS_API_TOKEN`, and
   `TRAVELPAYOUTS_MOCK=false` in Render (and locally in `backend/.env`)

With `TRAVELPAYOUTS_MOCK=false`, hotels resolve to specific Hotellook pages
and flights to specific Aviasales routes, instead of falling back to search
pages. Approval can take a day or two; the app keeps working on search
fallbacks in the meantime.

---

## 3.5 Residential proxy — REQUIRED in production

**Without this, storefront generation does not work on Render at all.**

YouTube blocks datacenter IP ranges from fetching transcripts. The exact same
video succeeds from your laptop and fails from any cloud host — Render,
Railway, Fly, AWS, all of them. It is not a bug in Trova and no amount of
config on Render fixes it; the request has to leave from a residential IP.

The transcript library has built-in support for [Webshare](https://www.webshare.io),
including rotation and retry-when-blocked. Their residential plan starts at a
few dollars a month.

1. Sign up at webshare.io and buy a **Residential** proxy plan
   (**not** "Proxy Server" or "Static Residential" — the library targets the
   rotating residential endpoint)
2. **Dashboard → Proxy → Settings** → copy your **Proxy Username** and
   **Proxy Password**
3. In Render → **Environment**, add:

   | Key | Value |
   | --- | --- |
   | `WEBSHARE_PROXY_USERNAME` | your proxy username |
   | `WEBSHARE_PROXY_PASSWORD` | your proxy password |

4. **Save and deploy**

Using a different provider? Set `GENERIC_PROXY_HTTP_URL` and
`GENERIC_PROXY_HTTPS_URL` instead, in the form
`http://user:pass@host:port`.

When no proxy is set and YouTube blocks a request, the API returns a 422 whose
message says so explicitly, rather than blaming the video's captions.

---

## 4. Verify the deploy

- [ ] `https://<render-url>/health` returns ok
- [ ] Vercel dashboard loads and looks right
- [ ] Pasting a captioned travel video produces a storefront (needs §3.5)
- [ ] The storefront URL opens in a **private window** (proves the publishable
      key and RLS work for a stranger, not just for you)
- [ ] A "Book now" link opens with **your marker** in the URL
- [ ] "Your storefronts" on the dashboard shows only what that browser made

---

## Known limits at this stage

**No accounts.** "Your storefronts" is `localStorage`, so it is per-browser —
clear site data and the list is gone, though every storefront URL keeps
working. Real multi-creator use needs Supabase Auth and a `user_id` on
`creators`, plus RLS policies scoping writes to the owner.

**Anyone can generate a storefront** on your deployed backend, spending your
Anthropic credits. Fine while it is unlisted; add rate limiting or auth before
you promote it anywhere public.

**No delete.** Nothing in the UI removes a storefront — only the Supabase
dashboard.

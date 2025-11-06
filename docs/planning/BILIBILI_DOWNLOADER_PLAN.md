## Bilibili Video Downloader Plan (to replace SnapAny)

### Objective
- Build a reliable, rate-limit-aware Bilibili video/audio downloader fully under our control, replacing SnapAny.
- Reuse proven components from `D:\App Dev\Bili23-Downloader-main` to minimize risk and implementation time.

### Scope
- Input: Bilibili URLs (`BV`/`av`, `b23.tv` short links, episodes, bangumi where feasible).
- Output: MP4/MKV with merged audio+video via FFmpeg, plus optional assets (cover, subtitles, danmaku ASS).
- Quality: Selectable resolutions and audio qualities subject to account permissions/SESSDATA.
- Resilience: Retries, CDN fallback, segmented range downloads, progress reporting.

### High-level Architecture
- URL Parser: extract `bvid`, optional `cid`, page index.
- API Layer: WBI-signed calls for view and playurl endpoints to enumerate streams.
- Media Selector: choose DASH/FLV stream (codec, quality), map to URLs.
- Downloader: multi-part range downloader with CDN fallback; resume and speed limiting.
- Merger: invoke FFmpeg to mux audio+video (and embed subtitles if requested).
- Auth/Headers: configurable `SESSDATA` and required cookies/headers to reduce anti-bot triggers.

### Reusable Components From Bili23
- Request/Headers: `src/utils/common/request.py` (`RequestUtils`) for session, headers, cookies, proxy, range support.
- WBI: `src/utils/auth/wbi.py` for `WbiUtils.encWbi` signature.
- Parsing Flow: `src/utils/parse/video.py` to resolve `bvid/cid`, call view + playurl endpoints, and list available media.
- Downloader: `src/utils/module/downloader_v3.py` segmented range downloader with retry/backoff and CDN file size probing.
- CDN helper: `src/utils/module/web/cdn.py` for domain list and file size resolution.
- FFmpeg helpers: `src/utils/module/ffmpeg_v2.py` and `src/utils/module/ffmpeg/*.py` to assemble merge commands.

We will not import GUI components. We will adapt or vendor minimal subsets into our project namespace to avoid heavy dependencies (e.g., wxPython).

### Anti-bot/Resilience Strategy
- Headers: correct `User-Agent`, `Referer` set to the original video page; include cookies (`SESSDATA`, `buvid3/4`, `_uuid`, etc.).
- WBI signature: always sign `view` and `playurl` requests.
- Session reuse: keep one `requests.Session` per run; honor SSL verify toggle; short timeouts with exponential backoff.
- CDN fallback: maintain ordered list of cdn hosts; try HEAD for size to validate; swap on stalls.
- Range downloads: segment-bytes requests with progress tracking; restart stalled segments.
- Proxy: support system/custom proxy and optional auth.

### Minimal API Surface in Research Tool
- `download_bilibili(url: str, quality: str|int = "best", audio_quality: str|int = "best", out_dir: Path, include_subtitle: bool = False, include_danmaku: bool = False) -> Path`:
  - Returns final merged file path.
  - Raises domain-specific exceptions (network, auth required, geo, content unavailable, max retries).

### CLI Entry (optional)
- `python -m research_tool.bili_downloader <url> --quality 1080p --audio best --out ./downloads --subs --danmaku`

### Configuration
- `config/bilibili.json` or env vars:
  - `SESSDATA`, `DedeUserID`, `DedeUserID__ckMd5`, `bili_jct` (optional but unlocks higher qualities)
  - `buvid3`, `buvid4`, `_uuid`, `b_nut`, `buvid_fp`
  - `user_agent`, `always_use_https_protocol`, `enable_ssl_verify`
  - `proxy_mode`, `proxy_ip`, `proxy_port`, `enable_auth`, `auth_username`, `auth_password`
  - Download tunables: `threads`, `speed_mbps`, `download_error_retry_count`, `download_suspend_retry_interval`

### Data Flow
1) Normalize/expand URL (resolve `b23.tv`).
2) Parse `bvid` (and `cid` if page selected); fetch view info; detect interactive/bangumi.
3) Fetch `playurl` with `fnval=4048` to get DASH; enumerate qualities and codecs.
4) Choose audio+video URLs; probe size via CDN util; build download plan.
5) Download segments with range requests; monitor speed, retry on stalls; write to temp files.
6) Merge via FFmpeg; cleanup; emit artifact path and metadata.
7) Post-process: MP4→MP3, upload MP3 to OSS, get public URL, transcribe, return transcript.

### Error Handling
- Map API non-200 and `code` fields to rich exceptions (auth required, paid, area limit, redirect).
- On 412/403: rotate CDN, adjust headers, randomize small delays, re-sign WBI.
- On content mismatch: verify sizes/hashes; re-download missing segments.

### Testing Strategy
- Unit: URL parse (BV/av/pages), WBI signing determinism, header formation, CDN file-size probe logic.
- Integration: public sample videos (SD only), authenticated high-quality with dummy cookies, short clips for speed.
- E2E: run `tests/test_full_workflow_integration.py` variants to ensure downloader outputs expected file and JSON metadata.
- Rate-limit: simulate failures and ensure backoff and resume work.

### Milestones
- M1 (Core parsing): URL normalization, `bvid/cid` resolution, `view` + `playurl` responses stored. (1 day)
- M2 (Downloader): segmented range download + simple merge for one stream. (1–2 days)
- M3 (Selection + auth): quality picker, SESSDATA unlock, audio/video pairing. (1 day)
- M4 (Resilience): CDN fallback, retries, progress, speed limit. (1 day)
- M5 (Assets): subtitles, danmaku, cover fetching (optional). (1 day)
- M6 (Polish): CLI, config, docs, tests. (1 day)

### Risks & Mitigations
- API changes to WBI/params: vendor `WbiUtils` and track upstream; feature-flag.
- Account-required qualities: clearly message when auth is needed; fallback gracefully.
- Geo/DRM/paid content: detect and abort with clear reason.
- Legal: display disclaimer; restrict to personal/research use.

### Decision: Reuse vs Re-implement
- Reuse: Vendor minimal `RequestUtils`, `WbiUtils`, playurl/view parsing, and `downloader_v3` logic. Strip GUI and unrelated modules.
- Re-implement: Only thin wrappers to fit our config/errors/logging. Keep code paths readable and covered by tests.

### Deliverables
- Library: `research_tool/bili/` with parser, api, downloader, ffmpeg merger, config.
- CLI (optional).
- Tests covering core flows.
- Docs: README section and usage examples.

### Post-processing Pipeline (required by `scrapers/bilibili_scraper.py` L24–L28)
- MP4→MP3 conversion:
  - Reuse `utils/convert_mp4_to_mp3.py` helper; ensure FFmpeg is present.
  - Output fixed: `.mp3` with same basename as video.
- OSS upload:
  - Use existing OSS settings in `config.yaml` under `scrapers.bilibili.*`;
  - Implement `upload_to_oss(local_path) -> public_url` helper; return HTTPS URL.
- Transcription:
  - Use Paraformer API with provided keys; target language `zh` per config.
  - Input is the public MP3 URL; return full transcript text and timing if available.
- Integration contract for scraper:
  - New downloader returns local MP4 path and metadata.
  - Scraper chains: convert → upload → get URL → transcribe → return transcript JSON.
  - All steps configurable and skippable via flags for tests.

### Acceptance Criteria
- Can download a public BV URL at default quality without SnapAny.
- With SESSDATA, can download at selected quality and merge A+V.
- Retries handle transient 403/412/CDN stalls; no infinite loops; clear errors.



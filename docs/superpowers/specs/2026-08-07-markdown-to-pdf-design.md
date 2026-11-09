# Markdown → PDF — Design

## Goal

New LocalPDF tool: convert Markdown (headings, bold, italic, lists, blockquotes, etc.) into a single-column PDF. No layout/CSS sophistication needed — plain document rendering is sufficient.

## Backend

### Dependencies

Add to `backend/requirements.txt`:
- `markdown==3.7` — Markdown → HTML.
- `xhtml2pdf==0.2.16` — HTML → PDF. Pure Python, no system libraries, no Dockerfile changes.

### Service

`backend/app/services/convert.py`, new function:

```python
def markdown_to_pdf(md_text: str, output_path: Path) -> None
```

- Converts `md_text` to HTML via `markdown.markdown(md_text, extensions=["extra", "nl2br", "sane_lists"])`.
- Wraps the HTML fragment in a minimal single-column template (base font, margins, heading sizes via inline `<style>`).
- Renders to `output_path` with `xhtml2pdf.pisa.CreatePDF`.
- Raises `HTTPException(500, ...)` if `pisa` reports an error (`err` truthy).

### Endpoint

`backend/app/routers/convert.py`, new route:

```
POST /api/v1/convert/markdown-to-pdf
```

- Accepts multipart form: `file: UploadFile | None` and/or `text: str | None` (Form field).
- Priority: if `file` present, read its contents as the markdown source; else use `text`.
- 400 `"Contenu Markdown requis."` if neither provided or resulting content is empty/whitespace-only.
- File path: reuse existing `_size_check` (200MB cap, same as other tools).
- Text path: cap at 2 MB (2 * 1024 * 1024 chars) — 413 `"Texte trop volumineux."` if exceeded.
- Follows existing job-dir lifecycle (`create_job_dir`, `delete_job` on error/background task), same as other convert routes.
- Returns `FileResponse` with `media_type="application/pdf"`, `filename="document.pdf"`.

## Frontend

### New page

`frontend/app/pages/outils/markdown-vers-pdf.vue`:

- Toggle between two input modes: "Fichier" (reuse `FileDropzone`, `accept=".md,.markdown"`) and "Texte" (`UTextarea`, generous rows, placeholder showing Markdown example).
- Submit builds `FormData` with either `file` or `text` field, POSTs via existing `useApi().uploadForm` helper, downloads result as `document.pdf` via existing `downloadBlob` helper.
- Same loading/error-alert pattern as `pdf-vers-markdown.vue`.

### Navigation

`frontend/app/utils/toolNav.ts` — add to the `Convertir` category:

```ts
{ title: 'Markdown → PDF', description: 'Générez un PDF depuis du Markdown.', icon: 'i-lucide-file-text', to: '/outils/markdown-vers-pdf' }
```

## Error Handling

| Case | Response |
|---|---|
| No file and no/empty text | 400 "Contenu Markdown requis." |
| Text exceeds 2 MB | 413 "Texte trop volumineux." |
| File exceeds `max_upload_bytes` | 413 (existing `_size_check` message) |
| `xhtml2pdf` render failure | 500 with error detail |

Job directories are always cleaned up (on error via `delete_job`, on success via `background_tasks`), matching the pattern used by every other conversion route.

## Testing

New `backend/app/tests/test_convert.py` (no such file exists yet):
- Text-input path → 200, `content-type: application/pdf`, non-empty body.
- File-upload path (`.md` file) → 200, `content-type: application/pdf`.
- Empty input (neither file nor text) → 400.
- Oversized text (> 2 MB) → 413.

## Out of Scope

- Custom CSS/theming, multi-column layouts, syntax-highlighted code blocks, table-of-contents generation, custom fonts beyond a sane default.
- Client-side (browser-only) rendering — this is a backend conversion tool, consistent with the rest of the app's conversion tools.

# Markdown → PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new LocalPDF tool that converts Markdown (headings, bold, italic, lists, blockquotes) into a single-column PDF, accepting either a `.md` file upload or pasted text.

**Architecture:** Backend converts Markdown → HTML (via the `markdown` package) → PDF (via `xhtml2pdf`, pure Python, no system dependencies). A new `POST /api/v1/convert/markdown-to-pdf` endpoint accepts either a file or a text form field. A new Nuxt page toggles between a file dropzone and a textarea, then downloads the resulting PDF — following the exact pattern of the existing `office-vers-pdf.vue` page.

**Tech Stack:** FastAPI (backend), `markdown==3.7`, `xhtml2pdf==0.2.16`, Nuxt 3 + Nuxt UI v4 (frontend).

**Spec:** `docs/superpowers/specs/2026-08-07-markdown-to-pdf-design.md`

## Global Constraints

- Text input capped at 2 MB (2 * 1024 * 1024 characters) — 413 if exceeded.
- File input uses existing `_size_check` (200 MB cap via `settings.max_upload_bytes`).
- No new system/Dockerfile dependencies — `xhtml2pdf` and `markdown` are pure-Python pip packages.
- No custom CSS/theming, multi-column layouts, syntax highlighting, or ToC generation — plain single-column rendering only.
- French UI copy, matching the tone of existing tool pages (e.g. `office-vers-pdf.vue`, `pdf-vers-markdown.vue`).
- All job directories must be cleaned up on both success (background task) and error (`delete_job`), matching every existing conversion route.

---

### Task 1: Backend service function `markdown_to_pdf`

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/services/convert.py`
- Create: `backend/app/tests/test_convert.py`

**Interfaces:**
- Produces: `markdown_to_pdf(md_text: str, output_path: Path) -> None` in `app.services.convert` — writes a PDF to `output_path`, raises `fastapi.HTTPException(status_code=500, ...)` on render failure.

- [ ] **Step 1: Add dependencies**

Add these two lines to `backend/requirements.txt` (keep alphabetical grouping loose, append near other conversion deps):

```
markdown==3.7
xhtml2pdf==0.2.16
```

Install them into the backend's environment:

```bash
cd backend && pip install -r requirements.txt
```

- [ ] **Step 2: Write the failing test**

Create `backend/app/tests/test_convert.py`:

```python
import io

from fastapi.testclient import TestClient

from app.main import app
from app.services import convert as convert_service

client = TestClient(app)


def test_markdown_to_pdf_creates_valid_pdf(tmp_path):
    output = tmp_path / "out.pdf"
    convert_service.markdown_to_pdf("# Title\n\nSome **bold** text.", output)
    assert output.exists()
    data = output.read_bytes()
    assert data.startswith(b"%PDF")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_convert.py -v`
Expected: FAIL with `AttributeError: module 'app.services.convert' has no attribute 'markdown_to_pdf'`

- [ ] **Step 4: Implement `markdown_to_pdf`**

In `backend/app/services/convert.py`, add these imports at the top (alongside the existing ones):

```python
import markdown as md_lib
from xhtml2pdf import pisa
```

Then add the function (place it after `pdf_to_word`, at the end of the file):

```python
def markdown_to_pdf(md_text: str, output_path: Path) -> None:
    html_body = md_lib.markdown(
        md_text, extensions=["extra", "nl2br", "sane_lists"]
    )
    html = f"""<html>
<head>
<style>
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; }}
  h1 {{ font-size: 20pt; }}
  h2 {{ font-size: 16pt; }}
  h3 {{ font-size: 13pt; }}
  code {{ font-family: Courier, monospace; background-color: #f0f0f0; }}
  pre {{ font-family: Courier, monospace; background-color: #f0f0f0; padding: 8px; }}
  blockquote {{ border-left: 2px solid #ccc; padding-left: 10px; color: #555555; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    with open(output_path, "wb") as out:
        result = pisa.CreatePDF(html, dest=out)
    if result.err:
        raise HTTPException(
            status_code=500, detail="Erreur lors de la génération du PDF."
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_convert.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/app/services/convert.py backend/app/tests/test_convert.py
git commit -m "feat(backend): add markdown_to_pdf conversion service"
```

---

### Task 2: Backend endpoint `POST /api/v1/convert/markdown-to-pdf`

**Files:**
- Modify: `backend/app/routers/convert.py`
- Modify: `backend/app/tests/test_convert.py`

**Interfaces:**
- Consumes: `convert_service.markdown_to_pdf(md_text: str, output_path: Path) -> None` (Task 1).
- Produces: route `POST /api/v1/convert/markdown-to-pdf`, multipart form fields `file` (optional) and `text` (optional). Returns `application/pdf` as `document.pdf`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/app/tests/test_convert.py`:

```python
def test_markdown_to_pdf_from_text():
    response = client.post(
        "/api/v1/convert/markdown-to-pdf",
        data={"text": "# Titre\n\nTexte en **gras** et *italique*."},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_markdown_to_pdf_from_file():
    files = {"file": ("doc.md", io.BytesIO(b"# Titre\n\nContenu."), "text/markdown")}
    response = client.post("/api/v1/convert/markdown-to-pdf", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_markdown_to_pdf_empty_input():
    response = client.post("/api/v1/convert/markdown-to-pdf", data={"text": "   "})
    assert response.status_code == 400


def test_markdown_to_pdf_text_too_long():
    huge_text = "a" * (2 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/convert/markdown-to-pdf", data={"text": huge_text}
    )
    assert response.status_code == 413
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest app/tests/test_convert.py -v`
Expected: the 4 new tests FAIL with 404 (route doesn't exist yet).

- [ ] **Step 3: Implement the endpoint**

In `backend/app/routers/convert.py`, change the import line at the top from:

```python
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
```

to:

```python
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
```

Then append this route at the end of the file:

```python
@router.post("/markdown-to-pdf")
def markdown_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
):
    if file is not None:
        _size_check(file)
        md_text = file.file.read().decode("utf-8", errors="ignore")
    else:
        md_text = text or ""

    if len(md_text) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Texte trop volumineux.")

    if not md_text.strip():
        raise HTTPException(status_code=400, detail="Contenu Markdown requis.")

    ws = create_job_dir()
    try:
        output = ws / "document.pdf"
        convert_service.markdown_to_pdf(md_text, output)
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="document.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest app/tests/test_convert.py -v`
Expected: all 5 tests PASS (including Task 1's test).

- [ ] **Step 5: Run the full backend test suite to check for regressions**

Run: `cd backend && pytest -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/convert.py backend/app/tests/test_convert.py
git commit -m "feat(backend): add markdown-to-pdf endpoint"
```

---

### Task 3: Frontend page `markdown-vers-pdf.vue`

**Files:**
- Create: `frontend/app/pages/outils/markdown-vers-pdf.vue`

**Interfaces:**
- Consumes: `useApi().uploadForm(path: string, form: FormData) -> Promise<Blob>` (existing composable, `frontend/app/composables/useApi.ts`); `downloadBlob(blob: Blob, filename: string) -> void` (existing util, `frontend/app/utils/downloadBlob.ts`); `<FileDropzone accept multiple maxSizeMb @files-selected>` (existing component).
- Produces: page at route `/outils/markdown-vers-pdf`.

- [ ] **Step 1: Create the page**

Create `frontend/app/pages/outils/markdown-vers-pdf.vue`:

```vue
<script setup>
const { uploadForm } = useApi()

const mode = ref('file')
const file = ref(null)
const text = ref('')
const loading = ref(false)

const canSubmit = computed(() => {
  return mode.value === 'file' ? !!file.value : text.value.trim().length > 0
})

async function onSubmit() {
  if (!canSubmit.value) return
  loading.value = true
  try {
    const form = new FormData()
    if (mode.value === 'file') {
      form.append('file', file.value)
    } else {
      form.append('text', text.value)
    }
    const blob = await uploadForm('/api/v1/convert/markdown-to-pdf', form)
    downloadBlob(blob, 'document.pdf')
  } catch (e) {
    alert('Erreur lors de la conversion : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Markdown vers PDF
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Générez un PDF à partir de texte rédigé en Markdown.
    </p>

    <div class="mb-4 flex gap-2">
      <UButton
        :variant="mode === 'file' ? 'solid' : 'outline'"
        @click="mode = 'file'"
      >
        Fichier
      </UButton>
      <UButton
        :variant="mode === 'text' ? 'solid' : 'outline'"
        @click="mode = 'text'"
      >
        Texte
      </UButton>
    </div>

    <FileDropzone
      v-if="mode === 'file'"
      accept=".md,.markdown"
      @files-selected="file = $event[0]"
    />

    <UTextarea
      v-else
      v-model="text"
      :rows="14"
      class="w-full"
      placeholder="# Titre&#10;&#10;Rédigez votre **Markdown** ici..."
    />

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!canSubmit"
      @click="onSubmit"
    >
      Convertir en PDF
    </UButton>
  </div>
</template>
```

- [ ] **Step 2: Lint the new file**

Run: `cd frontend && pnpm lint --file app/pages/outils/markdown-vers-pdf.vue 2>/dev/null || pnpm lint`
Expected: no errors on the new file (fix any reported issues before continuing).

- [ ] **Step 3: Commit**

```bash
git add frontend/app/pages/outils/markdown-vers-pdf.vue
git commit -m "feat(frontend): add markdown-vers-pdf tool page"
```

---

### Task 4: Navigation entry + end-to-end verification

**Files:**
- Modify: `frontend/app/utils/toolNav.ts`

**Interfaces:**
- Consumes: `ToolNavItem` interface (already defined in `toolNav.ts`).

- [ ] **Step 1: Add the nav entry**

In `frontend/app/utils/toolNav.ts`, inside the `Convertir` category's `tools` array, add (after the `Office → PDF` entry, before `PDF → Word` — or at the end, either position is fine as long as it's within `Convertir`):

```ts
{ title: 'Markdown → PDF', description: 'Générez un PDF depuis du Markdown.', icon: 'i-lucide-file-text', to: '/outils/markdown-vers-pdf' }
```

- [ ] **Step 2: Lint the modified file**

Run: `cd frontend && pnpm lint --file app/utils/toolNav.ts 2>/dev/null || pnpm lint`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/utils/toolNav.ts
git commit -m "feat(frontend): add Markdown to PDF nav entry"
```

- [ ] **Step 4: Manual verification in the browser**

Ensure both dev servers are running (backend `uvicorn` on :8000, frontend `pnpm dev` on :3000 — check with `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000` and `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs`; start whichever isn't already up).

Then verify manually:
1. Navigate to `http://localhost:3000/outils/markdown-vers-pdf` — page loads, title "Markdown vers PDF" visible, sidebar/nav shows "Markdown → PDF" under "Convertir".
2. "Texte" mode: type `# Test\n\nSome **bold** and *italic* text.`, click "Convertir en PDF" — a `document.pdf` downloads; open it and confirm it renders the heading, bold, and italic correctly.
3. "Fichier" mode: upload a small `.md` file — a `document.pdf` downloads correctly.
4. Submit with empty text — button stays disabled (client-side guard), confirming `canSubmit` works.

Fix any issues found before considering the task done.

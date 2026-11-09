# Pivoter Per-Page Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global angle dropdown + page-selection checkbox on `/outils/pivoter` with per-page hover rotate arrows and global stepper buttons, backed by a new absolute per-page rotation map on the backend.

**Architecture:** Backend gains a second, absolute-rotation code path (`rotate_pdf_map`) alongside the existing additive `rotate_pdf`, selected via a new optional `rotations` form field on `POST /api/v1/modify/rotate`. Frontend tracks a `pageAngles` map (page → 0/90/180/270), mutated by per-page arrow clicks (`PageThumbCard` → `PdfPageGrid` → `pivoter.vue`) or global stepper clicks (shift every entry by the same delta), then submits the non-zero entries as a JSON map.

**Tech Stack:** FastAPI, PyMuPDF (`fitz`), pytest, Vue 3 `<script setup>`, Nuxt UI.

## Global Constraints

- Angles are always multiples of 90, normalized mod 360 (spec: "Angles always normalized mod 360 both client- and server-side").
- Existing `angle` + `pages` request path must keep working unchanged when `rotations` is not sent (spec: "backward compatible with any other caller/test").
- Out-of-range page numbers in the map are silently skipped, not errors (spec: "matches current `rotate_pdf` convention").
- Malformed `rotations` JSON → HTTP 400.
- Submit button on `pivoter.vue` disabled when no file or every `pageAngles` value is 0.

---

## File Structure

- Modify `backend/app/services/modify.py` — add `rotate_pdf_map(file, output_path, rotations: dict[int, int]) -> None`.
- Modify `backend/app/routers/modify.py` — add optional `rotations: str = Form("")` param to `rotate()`, branch to the new service function.
- Modify `backend/app/tests/test_phase2.py` — add tests for the new `rotations` path and JSON-parse-error case.
- Modify `frontend/app/components/pdf/PageThumbCard.vue` — add hover rotate-left/rotate-right buttons, emit `rotate`.
- Modify `frontend/app/components/pdf/PdfPageGrid.vue` — forward child `rotate` event as `rotate-page`.
- Modify `frontend/app/pages/outils/pivoter.vue` — replace angle/selection UI with `pageAngles` state, per-page + global arrow controls.

---

### Task 1: Backend — absolute per-page rotation service function

**Files:**
- Modify: `backend/app/services/modify.py:8-25` (add new function after `rotate_pdf`, don't touch it)
- Test: `backend/app/tests/test_phase2.py`

**Interfaces:**
- Produces: `rotate_pdf_map(file: BinaryIO, output_path: Path, rotations: dict[int, int]) -> None` — for each `(page_num, angle)` in `rotations`, if `1 <= page_num <= total_pages`, sets that page's rotation to `angle % 360` (absolute, not additive). Pages absent from the dict are untouched. Raises `HTTPException(400, ...)` if any angle is not a multiple of 90.

- [ ] **Step 1: Write the failing test**

Add to `backend/app/tests/test_phase2.py` (uses the existing `sample_pdf` fixture, but that fixture is single-page — add a 3-page helper for this test):

```python
def _make_multi_page_pdf(pages: int = 3):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"Page {i + 1}")
    stream = io.BytesIO()
    doc.save(stream)
    doc.close()
    return stream.getvalue()


def test_rotate_with_per_page_map():
    pdf_bytes = _make_multi_page_pdf(3)
    files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/modify/rotate",
        files=files,
        data={"angle": "90", "rotations": '{"1": 90, "2": 180}'},
    )
    assert response.status_code == 200
    result_doc = fitz.open(stream=response.content, filetype="pdf")
    assert result_doc[0].rotation == 90
    assert result_doc[1].rotation == 180
    assert result_doc[2].rotation == 0
    result_doc.close()


def test_rotate_with_invalid_rotations_json():
    pdf_bytes = _make_multi_page_pdf(1)
    files = {"file": ("doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/modify/rotate",
        files=files,
        data={"angle": "90", "rotations": "not-json"},
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest app/tests/test_phase2.py -k "rotate_with" -v`
Expected: FAIL — `test_rotate_with_per_page_map` fails because `rotations` form field doesn't exist yet (extra field is ignored by FastAPI's `Form`, so the request falls through to the old additive path and `result_doc[1].rotation` will be `180` not from the map but coincidentally from `angle=90` additive twice... actually it will just apply `angle=90` to *all* pages since `pages` is empty, so page 0 rotation will be 90 not the map's ignored value, and the assertion on page 2 rotation `== 0` will fail since all pages get rotated to 90). `test_rotate_with_invalid_rotations_json` fails because there's no JSON parsing yet, so it returns 200 not 400.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/modify.py`, add after `rotate_pdf` (after line 25):

```python
def rotate_pdf_map(
    file: BinaryIO,
    output_path: Path,
    rotations: dict[int, int],
) -> None:
    for angle in rotations.values():
        if angle % 90 != 0:
            raise HTTPException(
                status_code=400, detail="Angle must be a multiple of 90."
            )

    doc = fitz.open(stream=file.read(), filetype="pdf")
    total = len(doc)
    for page_num, angle in rotations.items():
        if 1 <= page_num <= total:
            page = doc[page_num - 1]
            page.set_rotation(angle % 360)
    doc.save(str(output_path))
    doc.close()
```

In `backend/app/routers/modify.py`, add `import json` at the top, add `rotations: str = Form("")` param to `rotate()`, and branch:

```python
import json

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.tempfiles import create_job_dir, delete_job
from app.services import modify as modify_service

router = APIRouter()


def _size_check(file: UploadFile):
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")


@router.post("/rotate")
def rotate(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    angle: int = Form(...),
    pages: str = Form(""),
    rotations: str = Form(""),
):
    _size_check(file)

    rotations_map = None
    if rotations.strip():
        try:
            parsed = json.loads(rotations)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="rotations must be valid JSON.")
        rotations_map = {int(k): int(v) for k, v in parsed.items()}

    if rotations_map is None:
        page_list = [int(p.strip()) for p in pages.split(",") if p.strip()] or None
        if angle not in (90, 180, 270):
            raise HTTPException(status_code=400, detail="Angle must be 90, 180 or 270.")

    ws = create_job_dir()
    try:
        output = ws / "rotated.pdf"
        if rotations_map is not None:
            modify_service.rotate_pdf_map(file.file, output, rotations_map)
        else:
            modify_service.rotate_pdf(file.file, output, angle, page_list)
    except Exception:
        delete_job(ws.name)
        raise
    background_tasks.add_task(delete_job, ws.name)
    return FileResponse(
        path=output,
        filename="rotated.pdf",
        media_type="application/pdf",
        background=background_tasks,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest app/tests/test_phase2.py -v`
Expected: PASS — all tests including `test_rotate` (old path, backward compat), `test_rotate_with_per_page_map`, `test_rotate_with_invalid_rotations_json`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/modify.py backend/app/routers/modify.py backend/app/tests/test_phase2.py
git commit -m "feat(rotate): add per-page absolute rotation map to /modify/rotate"
```

---

### Task 2: Frontend — hover rotate arrows on `PageThumbCard.vue`

**Files:**
- Modify: `frontend/app/components/pdf/PageThumbCard.vue`

**Interfaces:**
- Consumes: nothing new from other components.
- Produces: emits `rotate` with payload `delta: -90 | 90` when a rotate button is clicked. Existing `rotation` prop (number, degrees) keeps driving the preview transform unchanged.

This component has no test file in the repo (no frontend test runner is set up for Vue SFCs here — verify with `find frontend/app -iname "*.spec.*" -o -iname "*.test.*"` before starting; if none exist, this task is verified manually in Task 4's browser check, not with an automated test).

- [ ] **Step 1: Add the buttons and emit**

In `frontend/app/components/pdf/PageThumbCard.vue`, update the `defineEmits` line (currently line 14):

```js
const emit = defineEmits(['select', 'remove', 'rotate', 'dragstart', 'dragover', 'drop', 'dragend'])
```

Add two buttons inside the card's root `<div>`, after the existing drag-handle block (after line 58, before the `aspect-[3/4]` thumbnail div on line 60):

```html
<div
  v-if="!draggable"
  class="absolute inset-x-0 bottom-1 z-10 flex justify-between px-1 opacity-0 transition group-hover:opacity-100"
>
  <UButton
    icon="i-lucide-rotate-ccw"
    size="2xs"
    color="neutral"
    variant="solid"
    class="bg-(--ui-bg)/80"
    @click.stop="emit('rotate', -90)"
  />
  <UButton
    icon="i-lucide-rotate-cw"
    size="2xs"
    color="neutral"
    variant="solid"
    class="bg-(--ui-bg)/80"
    @click.stop="emit('rotate', 90)"
  />
</div>
```

(`v-if="!draggable"` avoids overlapping the grip handle shown in reorderable grids like `organiser.vue` — rotate arrows only make sense on `pivoter.vue`, which is not reorderable.)

- [ ] **Step 2: Manual verification**

Run: `docker compose up -d frontend` (or however the dev stack is already running per `Makefile`), open `http://localhost:3000/outils/organiser` (a page that already renders `PageThumbCard` inside `PdfPageGrid`), upload a PDF, hover a thumbnail.
Expected: two small rotate icon buttons fade in at the bottom corners on hover, no layout shift, no console errors. (Clicking them does nothing yet — `PdfPageGrid` doesn't forward the event until Task 3.)

- [ ] **Step 3: Commit**

```bash
git add frontend/app/components/pdf/PageThumbCard.vue
git commit -m "feat(rotate): add hover rotate buttons to PageThumbCard"
```

---

### Task 3: Frontend — forward rotate event through `PdfPageGrid.vue`

**Files:**
- Modify: `frontend/app/components/pdf/PdfPageGrid.vue:16` (emits) and the `PageThumbCard` usage block (currently lines 128-145)

**Interfaces:**
- Consumes: `PageThumbCard`'s `rotate` event (payload: `delta: number`), from Task 2.
- Produces: emits `rotate-page` with payload `{ page: number, delta: number }` for the parent page component to consume in Task 4.

- [ ] **Step 1: Update emits declaration**

Change line 16 from:
```js
const emit = defineEmits(['update:modelValue', 'update:order', 'loaded'])
```
to:
```js
const emit = defineEmits(['update:modelValue', 'update:order', 'loaded', 'rotate-page'])
```

- [ ] **Step 2: Wire the event on the `PageThumbCard` usage**

In the `<template>`, on the `<PageThumbCard>` element (currently lines 128-145), add a `@rotate` handler alongside the existing `@select`/`@remove`/etc:

```html
@rotate="emit('rotate-page', { page: item.page, delta: $event })"
```

- [ ] **Step 3: Manual verification**

No isolated test harness for this component exists in the repo. Verification happens end-to-end in Task 4 once `pivoter.vue` listens for `rotate-page`. Skip standalone verification here — proceed to Task 4.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/components/pdf/PdfPageGrid.vue
git commit -m "feat(rotate): forward per-page rotate event out of PdfPageGrid"
```

---

### Task 4: Frontend — rebuild `pivoter.vue` around `pageAngles`

**Files:**
- Modify: `frontend/app/pages/outils/pivoter.vue` (full rewrite of the `<script setup>` block and the angle/selection markup)

**Interfaces:**
- Consumes: `PdfPageGrid`'s `loaded` event (payload: `pageCount: number`, already existing) and new `rotate-page` event (payload: `{ page: number, delta: number }`, from Task 3).
- Produces: nothing consumed elsewhere — this is the leaf page component.

- [ ] **Step 1: Rewrite the script block**

Replace the entire `<script setup>` block (lines 1-38) with:

```js
import PdfPageGrid from '~/components/pdf/PdfPageGrid.vue'

const { uploadForm } = useApi()

const file = ref(null)
const pageAngles = ref({})
const loading = ref(false)

function normalizeAngle(a) {
  return ((a % 360) + 360) % 360
}

function onLoaded(pageCount) {
  const next = {}
  for (let p = 1; p <= pageCount; p++) {
    next[p] = pageAngles.value[p] || 0
  }
  pageAngles.value = next
}

function rotatePage(page, delta) {
  pageAngles.value = {
    ...pageAngles.value,
    [page]: normalizeAngle((pageAngles.value[page] || 0) + delta)
  }
}

function rotateAll(delta) {
  const next = {}
  for (const p of Object.keys(pageAngles.value)) {
    next[p] = normalizeAngle(pageAngles.value[p] + delta)
  }
  pageAngles.value = next
}

const hasRotations = computed(() =>
  Object.values(pageAngles.value).some(a => a !== 0)
)

async function onSubmit() {
  if (!file.value || !hasRotations.value) return
  loading.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('angle', '90')
    const nonZero = Object.fromEntries(
      Object.entries(pageAngles.value).filter(([, a]) => a !== 0)
    )
    form.append('rotations', JSON.stringify(nonZero))
    const blob = await uploadForm('/api/v1/modify/rotate', form)
    downloadBlob(blob, 'rotated.pdf')
  } catch (e) {
    alert('Erreur lors de la rotation : ' + (e?.message || 'inconnue'))
  } finally {
    loading.value = false
  }
}
```

(`form.append('angle', '90')` is sent only because the backend's `angle` field is `Form(...)` — required — even though it's ignored whenever `rotations` is non-empty. This is a required-but-unused field on this path, not a design ambiguity.)

- [ ] **Step 2: Rewrite the template**

Replace the entire `<template>` block (lines 40-99) with:

```html
<template>
  <div>
    <h1 class="mb-2 text-2xl font-bold">
      Pivoter des pages
    </h1>
    <p class="mb-6 text-(--ui-text-muted)">
      Survolez une page pour la pivoter individuellement, ou utilisez les flèches ci-dessous pour tourner toutes les pages.
    </p>

    <FileDropzone
      accept=".pdf"
      @files-selected="file = $event[0]; pageAngles = {}"
    />

    <div
      v-if="file"
      class="mt-6 mb-4 flex items-center gap-2"
    >
      <span class="text-sm text-(--ui-text-muted)">Tout pivoter :</span>
      <UButton
        icon="i-lucide-rotate-ccw"
        size="sm"
        color="neutral"
        variant="soft"
        @click="rotateAll(-90)"
      />
      <UButton
        icon="i-lucide-rotate-cw"
        size="sm"
        color="neutral"
        variant="soft"
        @click="rotateAll(90)"
      />
    </div>

    <div
      v-if="file"
      class="mt-4"
    >
      <PdfPageGrid
        :file="file"
        :selectable="false"
        :rotations="pageAngles"
        @loaded="onLoaded"
        @rotate-page="rotatePage($event.page, $event.delta)"
      />
    </div>

    <UButton
      class="mt-6"
      size="lg"
      :loading="loading"
      :disabled="!file || !hasRotations"
      @click="onSubmit"
    >
      Pivoter
    </UButton>
  </div>
</template>
```

- [ ] **Step 3: Manual verification**

Run: open `http://localhost:3000/outils/pivoter`, upload a multi-page PDF.
Expected:
- No angle dropdown, no "Toutes les pages" checkbox.
- Global rotate-left/rotate-right buttons appear once a file is loaded.
- Hovering any thumbnail reveals per-page rotate arrows; clicking one rotates only that thumbnail's preview 90° and the "Pivoter" button becomes enabled.
- Clicking a global arrow rotates every thumbnail's preview by the same delta, including ones already individually rotated (additive, not overwritten).
- Submitting downloads a `rotated.pdf` where each page's rotation matches what was shown in the previews.
- No console errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/pages/outils/pivoter.vue
git commit -m "feat(rotate): rebuild pivoter.vue with per-page + global rotate arrows"
```

---

## Self-Review Notes

- **Spec coverage:** data model (Task 4), UI components (Tasks 2-4), backend (Task 1), error handling (Task 1's JSON/angle validation + Task 4's `hasRotations` disable), testing (Task 1 automated, Tasks 2-4 manual — no Vue component test runner exists in this repo, confirmed by checking for `*.spec.*`/`*.test.*` files before Task 2).
- **Backward compatibility:** `test_rotate` (existing, untouched) continues to exercise the old `angle`+`pages` path with no `rotations` field sent — confirms the branch in Task 1 defaults correctly.
- **Type consistency:** `rotate-page` payload shape `{ page, delta }` is produced in Task 3 and consumed identically in Task 4. `rotate` event on `PageThumbCard` (Task 2) carries a bare `delta` number, matching how Task 3 reads `$event`.

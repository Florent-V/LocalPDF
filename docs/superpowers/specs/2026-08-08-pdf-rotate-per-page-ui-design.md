# PDF Rotate Tool — Per-Page Arrows Design

## Problem

`/outils/pivoter` currently applies one global angle (dropdown: 90/180/270°) to either all pages or a manually-selected subset (click-to-select grid). There is no way to rotate individual pages by different amounts in one pass, and the dropdown is a clunky interaction for a 4-value, wrap-around choice.

## Goals

- Hover over any page thumbnail → left/right rotate arrows appear, click rotates that page ±90° independently of every other page.
- Replace the global angle `<USelect>` with left/right stepper buttons that shift **all** pages by the same relative delta, preserving any per-page customization already made.
- Drop the now-redundant "Toutes les pages" checkbox and click-to-select page picker — per-page arrows supersede them.

## Data model (frontend, `pivoter.vue`)

Replace `angle`, `allPages`, `selectedPages` with:

```js
const pageAngles = ref({}) // { [pageNumber]: 0 | 90 | 180 | 270 }
```

- Initialized to `0` for every page once `PdfPageGrid` emits `loaded` (pageCount).
- Per-page arrow click on page `p`: `pageAngles[p] = (pageAngles[p] + delta + 360) % 360` where `delta` is `+90` or `-90`.
- Global arrow click: apply the same update to **every** key in `pageAngles` (relative shift, not an absolute overwrite — preserves prior per-page edits).
- Submit payload: `rotations = JSON.stringify(pageAngles filtered to entries !== 0)`. If the filtered map is empty, submit is disabled.

## UI components

**`PageThumbCard.vue`**
- Add two icon buttons (`i-lucide-rotate-ccw`, `i-lucide-rotate-cw`), absolute-positioned at the thumbnail's bottom-left/bottom-right corners.
- Hidden by default, revealed on hover via the existing `group`/`group-hover:opacity-100` pattern already used for the drag handle.
- Emit `rotate` with a `delta` payload (`-90`/`+90`), `@click.stop` so it doesn't trigger card selection.
- Existing `rotation` prop keeps driving the live CSS `transform: rotate(...)` preview — no change there.

**`PdfPageGrid.vue`**
- No new state ownership. Forward the child's `rotate` event upward as `rotate-page` with `{ page: item.page, delta }`.

**`pivoter.vue`**
- Remove `USelect` angle field and `UCheckbox` "Toutes les pages" field, and the "Cliquez les pages à pivoter" hint paragraph.
- Add two global buttons ("⟲ Tout" / "⟳ Tout", `i-lucide-rotate-ccw` / `i-lucide-rotate-cw`) above or beside the grid.
- `PdfPageGrid` rendered with `:selectable="false"` always; wire `@rotate-page="onRotatePage"`.
- Submit button disabled when `!file` or every value in `pageAngles` is `0`.

## Backend

**`backend/app/routers/modify.py`** — `/api/v1/modify/rotate`
- Add optional form field `rotations: str = Form("")` (JSON object, string keys → int angle, e.g. `{"1": 90, "3": 180}`).
- If `rotations` is non-empty: parse it, ignore `angle`/`pages`, call new service function with the map.
- If `rotations` is empty: keep existing `angle` + `pages` behavior unchanged (backward compatible with any other caller/test).

**`backend/app/services/modify.py`**
- New function `rotate_pdf_map(file: BinaryIO, output_path: Path, rotations: dict[int, int]) -> None`:
  - Validates every angle is a multiple of 90 (400 on failure, matching existing angle validation style).
  - For each `(page_num, angle)`: if `1 <= page_num <= total`, `page.set_rotation(angle % 360)` — **absolute** set, not additive (distinct from the existing `rotate_pdf` which adds to current rotation).
  - Pages not present in the map are left untouched.
  - Out-of-range page numbers are silently skipped (same convention as `rotate_pdf`).

## Error handling / edge cases

- Angles always normalized mod 360 both client- and server-side.
- Empty effective `rotations` (all zero) → submit disabled client-side; not sent.
- Malformed `rotations` JSON → 400.
- Out-of-range page number in map → skipped, not an error (matches current `rotate_pdf` convention).

## Testing

- Backend: new test in the rotate test module — single request with a mixed-angle map (e.g. page 1→90, page 2→180, page 3 absent) — assert each page's final `/Rotate` independently, and that the untouched page stayed at 0.
- Backend: existing `angle`+`pages` tests must keep passing unchanged (backward-compat path).
- Frontend: manual check at `localhost:3000/outils/pivoter` — hover reveals arrows, per-page click rotates only that thumbnail preview, global buttons shift every thumbnail, submit produces a PDF with independently-rotated pages.

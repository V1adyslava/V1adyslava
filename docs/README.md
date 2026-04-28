# Curator Feedback

A static, two-step English-language feedback form for curators. The curator
picks their name from a dropdown, sees the list of students from their group,
writes a free-text observation per student, and submits — every submission
appends rows to a Google Sheet via Google Apps Script.

```
curator-feedback/
├── index.html        # the form
├── styles.css        # green + beige look from the design
├── app.js            # form logic + submission
├── data.js           # curators and their students (edit here to change lists)
├── config.js         # Web App URL for submissions (edit after Apps Script setup)
├── apps-script.gs    # paste this into Google Apps Script
└── README.md         # this file
```

## Setup (one-time, ~10 minutes)

### 1. Create the Google Sheet

1. Open https://sheets.google.com → blank spreadsheet.
2. Rename it (e.g. *Curator Feedback Responses*).
3. Copy its **Sheet ID** from the URL — the part between `/d/` and `/edit`.
   Example: `https://docs.google.com/spreadsheets/d/1AbC…XyZ/edit` →
   ID is `1AbC…XyZ`.

### 2. Add the Apps Script

1. In the same sheet, open **Extensions → Apps Script**.
2. Delete the placeholder `function myFunction(){}` and paste the entire
   contents of `apps-script.gs` from this folder.
3. Replace `PASTE_YOUR_SHEET_ID_HERE` with the Sheet ID from step 1.
4. Click the **Save** icon (or `Ctrl/Cmd+S`).
5. Click **Deploy → New deployment**.
   - Type: **Web app** (click the gear icon next to "Select type" if needed).
   - Description: anything, e.g. `Curator Feedback`.
   - Execute as: **Me**.
   - Who has access: **Anyone**.
   - Click **Deploy**.
6. Authorize when prompted (Google will ask you to allow the script to access
   your sheet — this is normal; it's your own script). If it shows
   "Google hasn't verified this app", click **Advanced → Go to … (unsafe)** —
   it's safe because you wrote it.
7. Copy the **Web app URL** (ends in `/exec`).

### 3. Wire the form to the script

1. Open `curator-feedback/config.js`.
2. Replace `PASTE_YOUR_GOOGLE_APPS_SCRIPT_WEB_APP_URL_HERE` with the URL
   from step 2.7.
3. Commit and push.

### 4. Host the form (GitHub Pages)

1. Push this folder to GitHub (already in `v1adyslava/v1adyslava` repo).
2. On GitHub, go to **Settings → Pages**.
3. Source: **Deploy from a branch**, branch: the branch you're using,
   folder: **/curator-feedback**. Save.
4. After ~1 minute, Pages will publish at
   `https://v1adyslava.github.io/v1adyslava/`. Share that link with curators.

## How it works

- Step 1 — curator selects their name from the dropdown (label includes
  stream).
- Step 2 — they see one card per student with a textarea. Counter shows
  `X of N students filled in`.
- Submit — sends one POST request to the Apps Script with all entries; the
  script appends one row per student to the *Feedback* tab.
- One submission per device — locked via `localStorage`. To allow a curator
  to resubmit (e.g. they changed their mind), have them clear site data in
  the browser, or use a different browser/device.

## Editing the lists

Open `data.js` and change the `students` arrays. The dropdown rebuilds
automatically on the next page load.

## Sheet columns

| Timestamp | Curator | Stream | Student | Feedback |
|-----------|---------|--------|---------|----------|
| 2026-04-28T14:30:00Z | Svetlana | Stream 1 | Cecilia Mercado | … |

One row per student, even if the curator wrote nothing — empty cells in
*Feedback* mean the curator didn't fill that student's textarea.

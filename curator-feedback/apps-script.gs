/**
 * Google Apps Script — Curator Feedback receiver.
 *
 * Setup:
 *   1. Create a new Google Sheet (any name). Copy its URL.
 *   2. Open Extensions → Apps Script.
 *   3. Replace the default Code.gs content with this entire file.
 *   4. Replace SHEET_ID below with your sheet's ID
 *      (the long token in the URL between /d/ and /edit).
 *   5. Click Deploy → New deployment → Web app:
 *        - Execute as: Me
 *        - Who has access: Anyone
 *      Copy the resulting Web app URL.
 *   6. Paste that URL into curator-feedback/config.js → CONFIG.WEB_APP_URL.
 */

var SHEET_ID = "13x1jcv5J2SgYZqxsc-b71eZFJvFRL-pAncFmAZ8bNP0";

// Tab name where rows will be appended. Created automatically if missing.
var SHEET_NAME = "Feedback";

var HEADERS = ["Timestamp", "Curator", "Stream", "Student", "Feedback"];

function doPost(e) {
  try {
    var body = e && e.postData && e.postData.contents
      ? JSON.parse(e.postData.contents)
      : {};

    if (!body.curator || !body.stream || !Array.isArray(body.entries)) {
      return jsonResponse({ ok: false, error: "Bad payload" });
    }

    var ss = SpreadsheetApp.openById(SHEET_ID);
    var sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
      sheet.appendRow(HEADERS);
      sheet.getRange(1, 1, 1, HEADERS.length)
        .setFontWeight("bold")
        .setBackground("#2d5a3d")
        .setFontColor("#f7f3e9");
      sheet.setFrozenRows(1);
    } else if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
      sheet.getRange(1, 1, 1, HEADERS.length)
        .setFontWeight("bold")
        .setBackground("#2d5a3d")
        .setFontColor("#f7f3e9");
      sheet.setFrozenRows(1);
    }

    var ts = body.submittedAt
      ? new Date(body.submittedAt)
      : new Date();

    var rows = body.entries
      .filter(function (en) {
        return en && en.student;
      })
      .map(function (en) {
        return [
          ts,
          body.curator,
          "Stream " + body.stream,
          en.student,
          en.feedback || "",
        ];
      });

    if (rows.length) {
      sheet
        .getRange(sheet.getLastRow() + 1, 1, rows.length, HEADERS.length)
        .setValues(rows);
    }

    return jsonResponse({ ok: true, written: rows.length });
  } catch (err) {
    return jsonResponse({ ok: false, error: String(err) });
  }
}

function doGet() {
  return jsonResponse({ ok: true, hint: "POST JSON to this URL" });
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}

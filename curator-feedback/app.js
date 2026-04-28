(function () {
  "use strict";

  const STORAGE_KEY = "curator-feedback-submitted";

  const els = {
    step1: document.getElementById("step-1"),
    step2: document.getElementById("step-2"),
    stepDone: document.getElementById("step-done"),
    stepLocked: document.getElementById("step-locked"),
    select: document.getElementById("curator-select"),
    continueBtn: document.getElementById("continue-btn"),
    backBtn: document.getElementById("back-btn"),
    chipText: document.getElementById("chip-text"),
    studentsList: document.getElementById("students-list"),
    progressText: document.getElementById("progress-text"),
    form: document.getElementById("students-form"),
    submitBtn: document.getElementById("submit-btn"),
    submitHelp: document.getElementById("submit-help"),
    lockedText: document.getElementById("locked-text"),
    toast: document.getElementById("toast"),
  };

  let currentCurator = null;

  // ---------- helpers ----------
  function show(stepEl) {
    [els.step1, els.step2, els.stepDone, els.stepLocked].forEach((s) =>
      s.classList.add("hidden")
    );
    stepEl.classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function toast(msg, isError) {
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden", "toast-error");
    if (isError) els.toast.classList.add("toast-error");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.add("hidden"), 4000);
  }

  function getSubmittedRecord() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function setSubmittedRecord(curatorLabel) {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ curator: curatorLabel, at: new Date().toISOString() })
      );
    } catch (e) {}
  }

  function firstName(full) {
    return (full || "").split(/[\s(]/)[0] || full;
  }

  // ---------- step 1: populate curators ----------
  function populateCurators() {
    (window.CURATORS || []).forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.name} (Stream ${c.stream})`;
      els.select.appendChild(opt);
    });
  }

  // ---------- step 2: render students ----------
  function renderStudents(curator) {
    els.chipText.textContent = `${curator.name} (Stream ${curator.stream})`;
    els.studentsList.innerHTML = "";

    curator.students.forEach((name, idx) => {
      const card = document.createElement("div");
      card.className = "student-card";

      const h = document.createElement("h3");
      h.className = "student-name";
      h.textContent = name;

      const pos = document.createElement("p");
      pos.className = "student-position";
      pos.textContent = `Student ${idx + 1} of ${curator.students.length}`;

      const q = document.createElement("label");
      q.className = "student-question";
      q.textContent =
        "Describe the changes and progress of this student during the training:";

      const ta = document.createElement("textarea");
      ta.className = "student-textarea";
      ta.placeholder = `Share your observations about ${firstName(
        name
      )}'s journey, growth, and changes during the course…`;
      ta.dataset.student = name;
      ta.rows = 4;
      ta.addEventListener("input", () => {
        if (ta.value.trim()) card.classList.add("has-content");
        else card.classList.remove("has-content");
        updateProgress();
      });
      q.htmlFor = ta.id = `student-${idx}`;

      card.append(h, pos, q, ta);
      els.studentsList.appendChild(card);
    });

    updateProgress();
  }

  function updateProgress() {
    const total = currentCurator.students.length;
    const filled = els.studentsList.querySelectorAll(
      ".student-textarea"
    );
    let count = 0;
    filled.forEach((t) => {
      if (t.value.trim()) count++;
    });
    els.progressText.textContent = `${count} of ${total} students filled in`;
  }

  // ---------- submit ----------
  async function handleSubmit(e) {
    e.preventDefault();

    const entries = [];
    els.studentsList
      .querySelectorAll(".student-textarea")
      .forEach((ta) => {
        entries.push({
          student: ta.dataset.student,
          feedback: ta.value.trim(),
        });
      });

    const payload = {
      curator: currentCurator.name,
      stream: currentCurator.stream,
      submittedAt: new Date().toISOString(),
      entries,
    };

    if (
      !window.CONFIG ||
      !window.CONFIG.WEB_APP_URL ||
      window.CONFIG.WEB_APP_URL.indexOf("PASTE_YOUR") === 0
    ) {
      toast(
        "Submission endpoint is not configured yet. Contact the admin.",
        true
      );
      return;
    }

    els.submitBtn.disabled = true;
    els.submitBtn.textContent = "Sending…";

    try {
      // Use text/plain to avoid CORS preflight on Apps Script web apps.
      const res = await fetch(window.CONFIG.WEB_APP_URL, {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "text/plain;charset=utf-8" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json().catch(() => ({}));
      if (data && data.ok === false) {
        throw new Error(data.error || "Server returned an error");
      }

      setSubmittedRecord(`${currentCurator.name} (Stream ${currentCurator.stream})`);
      show(els.stepDone);
    } catch (err) {
      console.error(err);
      toast(
        "Could not send feedback. Check your internet connection and try again.",
        true
      );
      els.submitBtn.disabled = false;
      els.submitBtn.textContent = "Submit feedback";
    }
  }

  // ---------- init ----------
  function init() {
    const submitted = getSubmittedRecord();
    if (submitted) {
      els.lockedText.textContent =
        "This device already submitted feedback as " +
        submitted.curator +
        ". If this is a mistake, contact the admin.";
      show(els.stepLocked);
      return;
    }

    populateCurators();

    els.continueBtn.addEventListener("click", () => {
      const id = els.select.value;
      if (!id) {
        toast("Please choose your name first.", true);
        return;
      }
      currentCurator = (window.CURATORS || []).find((c) => c.id === id);
      if (!currentCurator) return;
      renderStudents(currentCurator);
      show(els.step2);
    });

    els.backBtn.addEventListener("click", () => {
      if (
        confirm(
          "Go back? Any text you've written for this curator will be lost."
        )
      ) {
        currentCurator = null;
        els.select.value = "";
        show(els.step1);
      }
    });

    els.form.addEventListener("submit", handleSubmit);
  }

  document.addEventListener("DOMContentLoaded", init);
})();

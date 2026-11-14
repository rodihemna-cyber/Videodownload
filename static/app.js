const $ = (id) => document.getElementById(id);

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("go").disabled = true;
  $("status").hidden = false;
  $("save").hidden = true;
  $("status").classList.remove("error");
  setProgress(0, "Starting…");

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: $("url").value, best_quality: $("best").checked }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    await poll(data.job_id);
  } catch (err) {
    $("status").classList.add("error");
    setProgress(0, err.message);
  } finally {
    $("go").disabled = false;
  }
});

function setProgress(pct, text) {
  $("fill").style.width = `${pct ?? 0}%`;
  $("msg").textContent = text;
}

async function poll(jobId) {
  for (;;) {
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) throw new Error("Job not found");
    const job = await res.json();
    if (job.status === "error") throw new Error(job.error);
    if (job.status === "done") {
      setProgress(100, `Ready: ${job.title}${job.resolution ? ` (${job.resolution})` : ""}`);
      $("save").href = `/api/jobs/${jobId}/file`;
      $("save").hidden = false;
      return;
    }
    const label = job.status === "processing" ? "Merging into MP4…"
      : job.progress != null ? `Downloading… ${job.progress.toFixed(0)}%` : "Downloading…";
    setProgress(job.progress, label);
    await new Promise((r) => setTimeout(r, 1000));
  }
}

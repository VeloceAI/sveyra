// Reconstruct a body from a photograph and show it beside the generated ones.
//
// Deliberately blunt about what came from the photograph. The fit solves six
// torso numbers, so a reconstructed body's shoulders, limb lengths and head are
// proportion rather than measurement, and the panel says so rather than letting
// the figure imply the whole thing was measured.

(function () {
  const stage = document.getElementById("photo-stage");
  const file = document.getElementById("photo-file");
  const heightInput = document.getElementById("photo-height");
  const status = document.getElementById("photo-status");
  const strip = document.getElementById("photo-samples");
  if (!stage || !file) return;

  const SAMPLES = [1, 2, 3, 4, 5, 6].map(function (n) {
    return "samples/person_" + n + ".jpg";
  });

  function say(text, kind) {
    status.textContent = text;
    status.className = kind || "";
  }

  function send(dataUrl, preview) {
    say("Reading the photograph…");
    stage.src = preview;
    stage.style.display = "block";

    fetch("/reconstruct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image: dataUrl,
        height_cm: parseFloat(heightInput.value) || 175,
      }),
    })
      .then(function (r) {
        return r.json().then(function (body) {
          return { ok: r.ok, body: body };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          say(result.body.error || "Reconstruction failed", "bad");
          return;
        }
        adopt(result.body);
      })
      .catch(function (e) {
        say("Could not reach the server: " + e.message, "bad");
      });
  }

  // The returned body joins the variant list, so the same blend slider morphs
  // between a generated figure and the photographed one.
  function adopt(result) {
    variants.photo = {
      label: result.label,
      positions: f32(result.positions),
      normals: f32(result.normals),
      measurements: result.measurements,
    };
    if (DATA.order.indexOf("photo") < 0) DATA.order.push("photo");
    target = "photo";
    blend = 1;
    applyBlend();

    const m = result.measurements;
    say(
      "Fitted from the silhouette: chest " +
        m.chest_girth_cm +
        ", waist " +
        m.waist_girth_cm +
        ", hip " +
        m.hip_girth_cm +
        " cm. Not fitted: " +
        result.not_fitted.join(", ") +
        ". Mask covered " +
        (result.coverage * 100).toFixed(0) +
        "% of the frame.",
      "ok",
    );
  }

  file.addEventListener("change", function () {
    const chosen = file.files && file.files[0];
    if (!chosen) return;
    const reader = new FileReader();
    reader.onload = function () {
      send(reader.result, reader.result);
    };
    reader.readAsDataURL(chosen);
  });

  SAMPLES.forEach(function (src) {
    const thumb = document.createElement("img");
    thumb.src = src;
    thumb.className = "thumb";
    // The sample photographs are downloaded, not committed, so a fresh clone
    // has none. Drop the thumbnail rather than showing a broken image.
    thumb.addEventListener("error", function () {
      thumb.remove();
    });
    thumb.addEventListener("click", function () {
      say("Fetching the sample…");
      fetch(src)
        .then(function (r) {
          return r.blob();
        })
        .then(function (blob) {
          const reader = new FileReader();
          reader.onload = function () {
            send(reader.result, src);
          };
          reader.readAsDataURL(blob);
        });
    });
    strip.appendChild(thumb);
  });

  say("Pick a sample below, or upload a full-body photo.");
})();

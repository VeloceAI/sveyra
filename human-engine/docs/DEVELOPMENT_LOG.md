# Human Engine Development Log

Newest first.

---

## Phase 7 - Rig, collision proxies, garment contract

The avatar can now be posed, and a garment engine has something to talk to.

### Weights come from geometry, not from an artist

There is nothing to paint onto. The mesh is generated, so a painted weight map
would not survive a change in cage resolution. Influence falls off with distance
to the *bone segment* rather than to the joint point, because measuring to a
single point makes a long bone like a thigh lose its grip halfway down. Four
influences per vertex, which is what glTF stores and GPUs expect.

Checked anatomically rather than numerically: the rightmost vertex must bind to
a left-arm bone, the lowest to a foot. Both hold.

### Dual quaternions, and the sign trap

Quaternions double-cover rotations, so blending `q` with `-q` cancels to nothing
instead of averaging. Signs are aligned to the first influence before blending.
There is a test for exactly that, because it is silent when wrong: the mesh
simply collapses.

### Collision is separate from skin

Ten capsules with signed distance, not the 6,000-triangle surface. That
separation is what lets a cloth solver run at interactive rates, and it is why
`GarmentBodyInterface` exposes a collision body rather than a mesh.

### Verification

- 144 tests pass, ruff clean
- Exported GLB carries 18 joints, inverse bind matrices and vertex weights
- Local translations reconstruct world joint positions to 1e-5
- Inverse bind matrices map each joint to the origin
- A blended half-rotation preserves length, which is the point of dual quaternions
- The viewer waves an arm to prove the weights actually deform the mesh

---

## Phase 2 - Photographs to silhouettes

`engine.build()` works end to end now: photographs in, fitted avatar out, in
about 0.9 seconds.

### No model in the default path

MediaPipe is an adapter, not a requirement. The default segmenter estimates the
wall colour from the frame border, keeps pixels that differ from it, and takes
the largest connected region. That is enough for the photograph this product
actually asks for - one person, standing, plain-ish wall - and it costs
milliseconds with no download and no GPU.

It reports confidence rather than pretending. A subject the same colour as the
wall scores low on separation even when the mask looks a plausible size.

### The ordering bug

First end-to-end run fitted the body 84 to 99 percent too large. Cause: holes
were filled before the subject was chosen, so background speckle from a noisy,
unevenly lit wall formed a connected ring around the frame whose interior was
the entire image. Correct order is threshold, open away the speckle, take the
largest region, and only then fill inside that region.

Segmentation IoU went from swallowing the frame to 0.995 against ground truth,
and the fit from 84 percent error to 1.5.

Reading the numbers alone would not have caught this. The capture validator was
already warning "the subject fills most of the frame" while the fit silently
returned nonsense.

### Verification

- 117 tests pass, ruff clean
- IoU above 0.85 across noise levels from 2 to 18
- Background speckle does not swallow the frame
- A wall-coloured subject reports low confidence
- A flat frame is refused rather than fitted
- An injected custom segmenter is used instead of the default

---

## Phase 3 - Fitting a body from silhouettes

The core research milestone. Silhouettes in, `BodyParameters` out, in about
0.7 seconds on CPU.

### The design constraint that shaped everything

A naive loop rebuilds the body and rasterises it each iteration. Measured: 130 ms
per rasterisation regardless of resolution, because the cost is the Python loop
over 1,692 triangles, not pixels. At 260 ms per iteration a fit takes 45 seconds.

So the fitting loop does not rasterise. It measures where the surface *crosses*
each height band by interpolating along the mesh edges that straddle it, which
is pure numpy and 230 times cheaper. Rasterisation stays for ground truth and
final checks, where correctness matters more than speed.

Binning vertices instead of crossing edges was tried first and was faster still,
but wrong: mesh rings sit at discrete heights, so bands between rings came back
empty and the widest point between two rings was missed.

### Two stages, because the starting point matters more than the solver

Widths are read straight off the observed profile at the landmark heights, then
refined with `least_squares` under priors. An accidental experiment that skipped
the analytic start measured 25% errors where the full method gets 1-4%.

### Objective terms are separate objects

Proportion, anatomical and smoothness priors each return residuals and carry
their own weight. The anatomical one encodes what a torso *is* - wider than it
is deep, waist no broader than chest or hips - because silhouettes underdetermine
a body and without it the solver finds shapes that match the pixels and are not
human.

### What the numbers said

The waist came out 10% too wide. Cause: bands take the widest row they contain,
so a narrow waist borrows the wider chest beside it. Raising the band count from
40 to 64 cut the smearing; below about 56 the bias returns.

### Verification

- 89 tests pass, ruff clean
- Known parameters recovered from synthetic silhouettes to within 10% across
  five body types, typically 1-4%
- Two different bodies do not fit to the same answer
- Removing the silhouette makes the fit worse, so the pixels are genuinely used
- An empty mask returns a body rather than raising

### Known gaps

- Six torso parameters are solved. Shoulder width is not recoverable from a rest
  pose front view because the arms cross that band; limb girths are not solved.
- Nothing separates clothing from body, so loose garments read as a larger waist.
- `engine.build()` from photographs still refuses: Phase 2 must turn a photo into
  a mask first.

---


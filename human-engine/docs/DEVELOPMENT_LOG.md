# Human Engine Development Log

Newest first.

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


// mannequin.js's LimbShape, driven by measurement instead of by hand.
//
// The original takes eight tuned numbers per limb and sweeps an ellipse whose
// radius follows a cosine, then lerps both ends into an ellipsoid so they cap
// off round instead of ending on a flat cut. That rounding is most of what
// makes its figure read as a turned wooden piece rather than a stack of tubes.
//
// The tuned numbers are what we cannot keep: this body's dimensions come from a
// photograph, so the profile is read off the engine's own vertices at a series
// of stations along the bone, and only the cap blend is mannequin.js's.

const STATIONS = 24;
const RADIAL = 24;
const CAP_POWER = 16;

function orthonormalFrame(axis) {
  const up = new THREE.Vector3(axis.x, axis.y, axis.z).normalize();
  const seed =
    Math.abs(up.y) < 0.9
      ? new THREE.Vector3(0, 1, 0)
      : new THREE.Vector3(1, 0, 0);
  const side = new THREE.Vector3().crossVectors(up, seed).normalize();
  const front = new THREE.Vector3().crossVectors(side, up).normalize();
  return { up: up, side: side, front: front };
}

// The cross-section at each station along the bone: how far the surface reaches
// either side of the part's own centre line, and where that centre line sits.
// Measuring from the bone origin instead would assume every piece is threaded
// on its joint, and a foot is not centred on its ankle.
function measureProfile(positions, frame) {
  const rows = [];
  let lo = Infinity;
  let hi = -Infinity;
  const point = new THREE.Vector3();
  for (let i = 0; i < positions.length; i += 3) {
    point.set(positions[i], positions[i + 1], positions[i + 2]);
    const t = point.dot(frame.up);
    rows.push([t, point.dot(frame.side), point.dot(frame.front)]);
    if (t < lo) lo = t;
    if (t > hi) hi = t;
  }
  const span = hi - lo || 1;

  const bounds = [];
  for (let k = 0; k < STATIONS; k++) bounds.push(null);
  rows.forEach(function (row) {
    const k = Math.min(
      STATIONS - 1,
      Math.max(0, Math.round(((row[0] - lo) / span) * (STATIONS - 1))),
    );
    const b = bounds[k];
    if (b === null) {
      bounds[k] = [row[1], row[1], row[2], row[2]];
      return;
    }
    b[0] = Math.min(b[0], row[1]);
    b[1] = Math.max(b[1], row[1]);
    b[2] = Math.min(b[2], row[2]);
    b[3] = Math.max(b[3], row[2]);
  });

  // Stations no vertex landed in borrow from their neighbours, so a coarse mesh
  // cannot punch a waist into the middle of a limb.
  for (let k = 0; k < STATIONS; k++) {
    if (bounds[k]) continue;
    let before = k;
    let after = k;
    while (before > 0 && !bounds[before]) before--;
    while (after < STATIONS - 1 && !bounds[after]) after++;
    const a = bounds[before] || bounds[after];
    const b = bounds[after] || bounds[before];
    if (!a || !b) {
      bounds[k] = [0, 0, 0, 0];
      continue;
    }
    const w = after === before ? 0 : (k - before) / (after - before);
    bounds[k] = a.map(function (v, i) {
      return v + (b[i] - v) * w;
    });
  }

  // One smoothing pass so the profile tapers instead of wobbling station to
  // station, rescaled back to its original peak afterwards: smoothing shaves a
  // few per cent off the widest point, and that point is a measurement.
  const smooth = function (values) {
    const peak = Math.max.apply(null, values);
    const out = values.map(function (value, k) {
      return (
        (values[Math.max(0, k - 1)] +
          2 * value +
          values[Math.min(STATIONS - 1, k + 1)]) /
        4
      );
    });
    const after = Math.max.apply(null, out);
    return out.map(function (v) {
      return after > 1e-9 ? (v * peak) / after : v;
    });
  };

  const half = function (i) {
    return smooth(
      bounds.map(function (b) {
        return (b[i + 1] - b[i]) / 2;
      }),
    );
  };
  // Centres are smoothed but never rescaled. The peak-preserving trick above
  // exists to protect a measured half-width; a centre offset is a position and
  // can be negative, so scaling it toward its own extreme just moves the limb.
  const centre = function (i) {
    const values = bounds.map(function (b) {
      return (b[i + 1] + b[i]) / 2;
    });
    return values.map(function (value, k) {
      return (
        (values[Math.max(0, k - 1)] +
          2 * value +
          values[Math.min(STATIONS - 1, k + 1)]) /
        4
      );
    });
  };

  return {
    lo: lo,
    span: span,
    side: half(0),
    front: half(2),
    sideAt: centre(0),
    frontAt: centre(2),
  };
}

function limbGeometry(positions, axis) {
  const frame = orthonormalFrame(axis);
  const profile = measureProfile(positions, frame);
  const halfLength = profile.span / 2;

  const verts = [];
  const normals = [];
  const index = [];
  const p = new THREE.Vector3();
  const cap = new THREE.Vector3();

  for (let i = 0; i < STATIONS; i++) {
    const u = i / (STATIONS - 1);
    const t = profile.lo + u * profile.span;
    const rs = profile.side[i];
    const rf = profile.front[i];
    const cx = profile.sideAt[i];
    const cz = profile.frontAt[i];

    // The ellipsoid the ends melt into: widest at the middle, a point at each
    // pole, spanning the same length as the limb.
    const capScale = Math.sin(Math.PI * u);
    const capT = profile.lo + halfLength - Math.cos(Math.PI * u) * halfLength;
    const blend = Math.pow(Math.abs(2 * u - 1), CAP_POWER);

    for (let j = 0; j <= RADIAL; j++) {
      const v = (j / RADIAL) * Math.PI * 2;
      const cs = Math.cos(v);
      const sn = Math.sin(v);

      p.copy(frame.up).multiplyScalar(t)
        .addScaledVector(frame.side, cx + rs * cs)
        .addScaledVector(frame.front, cz + rf * sn);
      cap.copy(frame.up).multiplyScalar(capT)
        .addScaledVector(frame.side, cx + rs * capScale * cs)
        .addScaledVector(frame.front, cz + rf * capScale * sn);
      p.lerp(cap, blend);
      verts.push(p.x, p.y, p.z);

      const n = new THREE.Vector3()
        .addScaledVector(frame.side, cs / Math.max(rs, 1e-4))
        .addScaledVector(frame.front, sn / Math.max(rf, 1e-4))
        .normalize();
      normals.push(n.x, n.y, n.z);
    }
  }

  const ring = RADIAL + 1;
  for (let i = 0; i < STATIONS - 1; i++) {
    for (let j = 0; j < RADIAL; j++) {
      const a = i * ring + j;
      index.push(a, a + ring, a + 1, a + 1, a + ring, a + ring + 1);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
  geo.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  geo.setIndex(index);
  geo.computeVertexNormals();

  // How thick the piece is at each end, so a ball at the pivot can be sized to
  // the limb it joins. Measuring instead from the vertices nearest the joint
  // catches whatever is closest in the whole body, and a shoulder sitting
  // inside the chest then gets a ball the width of the chest.
  // The joint sits at the origin, so the near end is whichever station lies
  // closest to zero along the bone.
  const tAt = function (i) {
    return profile.lo + (i / (STATIONS - 1)) * profile.span;
  };
  const near = Math.abs(tAt(0)) <= Math.abs(tAt(STATIONS - 1)) ? 0 : STATIONS - 1;
  const far = near === 0 ? STATIONS - 1 : 0;
  const radiusAt = function (i) {
    return (profile.side[i] + profile.front[i]) / 2;
  };
  geo.userData.endRadius = { near: radiusAt(near), far: radiusAt(far) };
  return geo;
}


// Where the torso is narrowest along its own axis, which is the waist.
//
// mannequin.js carves the trunk into a torso and a pelvis, and that seam is
// most of why its figure has a shape rather than a slab. Rather than splitting
// at a guessed fraction of height, this finds the narrowest cross-section: on a
// measured body that is the waist by definition, and it moves with the body.
function splitAtWaist(positions, axis) {
  const frame = orthonormalFrame(axis);
  const profile = measureProfile(positions, frame);

  // Only the middle of the trunk is a candidate. Searched end to end, the
  // narrowest cross-section of a torso mesh is the neck, and the split lands
  // under the chin.
  const first = Math.round(STATIONS * 0.25);
  const last = Math.round(STATIONS * 0.6);
  let narrowest = first;
  for (let i = first; i <= last; i++) {
    if (profile.side[i] + profile.front[i] < profile.side[narrowest] + profile.front[narrowest]) {
      narrowest = i;
    }
  }
  const cut = profile.lo + (narrowest / (STATIONS - 1)) * profile.span;

  const upper = [];
  const lower = [];
  const point = new THREE.Vector3();
  for (let i = 0; i < positions.length; i += 3) {
    point.set(positions[i], positions[i + 1], positions[i + 2]);
    // Both keep the seam station, so the two pieces meet instead of leaving a
    // band of nothing between them.
    const t = point.dot(frame.up);
    if (t >= cut - profile.span / STATIONS) upper.push(positions[i], positions[i + 1], positions[i + 2]);
    if (t <= cut + profile.span / STATIONS) lower.push(positions[i], positions[i + 1], positions[i + 2]);
  }
  return { upper: upper, lower: lower, cut: cut };
}

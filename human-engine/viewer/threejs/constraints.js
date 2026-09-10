// Keeping limbs out of the body.
//
// Joint limits say what one joint may do and nothing about where the rest of
// the body is, so a pose can sit inside every clinical range and still drive an
// arm through the ribs. Reach up did exactly that, burying the upper arm 14 cm
// inside the trunk.
//
// The test is against rigid capsules the engine fits to the mesh, and the rule
// is not "no overlap". A thigh overlaps the pelvis by 22 cm at rest because
// they are anatomically joined. What matters is overlap *beyond* rest, so the
// rest state is measured once at bind and every pose is judged against it.

// A few millimetres absorb proxy-fit and export rounding, not visible overlap.
const PENETRATION_TOLERANCE_CM = 0.25;

function capsuleBones(capsules, byName, bones, restHeads) {
  return capsules
    .map(function (capsule) {
      const index = byName.get(capsule.bone);
      if (index === undefined) return null;
      const head = new THREE.Vector3().fromArray(capsule.head).multiplyScalar(0.01);
      const tail = new THREE.Vector3().fromArray(capsule.tail).multiplyScalar(0.01);

      // New exports are bone-local. Keep the conversion here too so an older
      // cached data file cannot silently move every boundary by a second copy
      // of the bone's bind translation.
      if (capsule.space !== 'bone-local') {
        const origin = new THREE.Vector3().fromArray(restHeads[index]);
        head.sub(origin);
        tail.sub(origin);
      }
      return {
        bone: bones[index],
        head: head,
        tail: tail,
        radius: capsule.radius * 0.01,
        name: capsule.bone,
      };
    })
    .filter(Boolean);
}

const _u = new THREE.Vector3();
const _v = new THREE.Vector3();
const _w = new THREE.Vector3();
const _closest = new THREE.Vector3();

function segmentDistance(a0, a1, b0, b1) {
  _u.subVectors(a1, a0);
  _v.subVectors(b1, b0);
  _w.subVectors(a0, b0);
  const aa = _u.dot(_u);
  const bb = _u.dot(_v);
  const cc = _v.dot(_v);
  const dd = _u.dot(_w);
  const ee = _v.dot(_w);
  const epsilon = 1e-12;

  if (aa <= epsilon && cc <= epsilon) return a0.distanceTo(b0);
  if (aa <= epsilon) {
    const t = Math.max(0, Math.min(1, ee / cc));
    return _closest.copy(_w).addScaledVector(_v, -t).length();
  }
  if (cc <= epsilon) {
    const s = Math.max(0, Math.min(1, -dd / aa));
    return _closest.copy(_w).addScaledVector(_u, s).length();
  }

  const denominator = aa * cc - bb * bb;
  let sNumerator;
  let sDenominator = denominator;
  let tNumerator;
  let tDenominator = denominator;
  if (denominator <= epsilon) {
    sNumerator = 0;
    sDenominator = 1;
    tNumerator = ee;
    tDenominator = cc;
  } else {
    sNumerator = bb * ee - cc * dd;
    tNumerator = aa * ee - bb * dd;
    if (sNumerator < 0) {
      sNumerator = 0;
      tNumerator = ee;
      tDenominator = cc;
    } else if (sNumerator > sDenominator) {
      sNumerator = sDenominator;
      tNumerator = ee + bb;
      tDenominator = cc;
    }
  }

  if (tNumerator < 0) {
    tNumerator = 0;
    if (-dd < 0) sNumerator = 0;
    else if (-dd > aa) sNumerator = sDenominator;
    else {
      sNumerator = -dd;
      sDenominator = aa;
    }
  } else if (tNumerator > tDenominator) {
    tNumerator = tDenominator;
    if (-dd + bb < 0) sNumerator = 0;
    else if (-dd + bb > aa) sNumerator = sDenominator;
    else {
      sNumerator = -dd + bb;
      sDenominator = aa;
    }
  }

  const s = Math.abs(sNumerator) <= epsilon ? 0 : sNumerator / sDenominator;
  const t = Math.abs(tNumerator) <= epsilon ? 0 : tNumerator / tDenominator;
  return _closest.copy(_w).addScaledVector(_u, s).addScaledVector(_v, -t).length();
}

function worldEnds(entry, outHead, outTail) {
  entry.bone.updateMatrixWorld();
  outHead.copy(entry.head).applyMatrix4(entry.bone.matrixWorld);
  outTail.copy(entry.tail).applyMatrix4(entry.bone.matrixWorld);
}

// Bones that share a joint always overlap, so they are never a collision.
//
// Only near neighbours, though. Excluding every ancestor looks right and is
// catastrophic: an arm is a descendant of the spine, so that rule excused the
// whole arm from the trunk and the test passed everything.
const ADJACENT_HOPS = 2;

function hopsBetween(a, b) {
  const depth = new Map();
  let hops = 0;
  for (let node = a; node; node = node.parent) depth.set(node, hops++);
  hops = 0;
  for (let node = b; node; node = node.parent) {
    if (depth.has(node)) return depth.get(node) + hops;
    hops++;
  }
  return Infinity;
}

function related(a, b) {
  return hopsBetween(a, b) <= ADJACENT_HOPS;
}

class BodyBoundary {
  constructor(volumes, byName, bones, restHeads) {
    this.limbs = capsuleBones(volumes.limb || [], byName, bones, restHeads);
    this.trunk = capsuleBones(volumes.trunk || [], byName, bones, restHeads);
    this.baseline = new Map();
    this.allowance = new Map();
  }

  _contactAllowance(first, second) {
    // A seated proximal thigh presses against the lower abdomen. Circular
    // capsules overstate that contact because a torso is wider than it is
    // deep; allow a body-scaled part of the thigh radius for this one soft,
    // anatomically connected region. Hands and arms receive no such allowance.
    const thigh = first.name.startsWith('upperleg02');
    const lowerTorso = /^(spine0[345]|pelvis)/.test(second.name);
    return thigh && lowerTorso ? first.radius * 0.7 : 0;
  }

  _measurePair(first, second, out, ah, at, bh, bt) {
    if (related(first.bone, second.bone)) return;
    worldEnds(first, ah, at);
    worldEnds(second, bh, bt);
    const gap = segmentDistance(ah, at, bh, bt);
    const overlap = first.radius + second.radius - gap;
    const pair = `${first.name}|${second.name}`;
    this.allowance.set(pair, this._contactAllowance(first, second));
    if (overlap > 0) out.set(pair, overlap);
  }

  // Overlap in the current pose, per limb-trunk pair.
  measure() {
    const out = new Map();
    const ah = new THREE.Vector3();
    const at = new THREE.Vector3();
    const bh = new THREE.Vector3();
    const bt = new THREE.Vector3();

    for (const limb of this.limbs) {
      for (const trunk of this.trunk) {
        this._measurePair(limb, trunk, out, ah, at, bh, bt);
      }
    }

    // Arms, hands and legs are part of the boundary too. This prevents a
    // crossed-arm or reconstructed pose from sending one hand through the
    // opposite arm or a thigh while still being clear of the torso.
    for (let i = 0; i < this.limbs.length; i++) {
      for (let j = i + 1; j < this.limbs.length; j++) {
        this._measurePair(this.limbs[i], this.limbs[j], out, ah, at, bh, bt);
      }
    }
    return out;
  }

  // Called once, in the bind pose, so joined bones do not read as collisions.
  calibrate() {
    this.baseline = this.measure();
  }

  // How much deeper than rest, in centimetres, and where.
  intrusion() {
    let worst = 0;
    let where = "";
    for (const [pair, overlap] of this.measure()) {
      const extra =
        overlap - (this.baseline.get(pair) || 0) - (this.allowance.get(pair) || 0);
      if (extra > worst) {
        worst = extra;
        where = pair;
      }
    }
    return { depth: worst * 100, where: where };
  }

  clear() {
    return this.intrusion().depth <= PENETRATION_TOLERANCE_CM;
  }
}

// Back a pose off until it clears the body.
//
// The pose is applied at a fraction of its full rotation and the fraction is
// bisected: the largest amount of the pose that does not put a limb inside the
// body is kept. Refusing the pose outright would be easier and worse, because
// most of a reaching arm is reachable and only the last part of it is not.
function resolve(boundary, bones, from, to, apply) {
  apply(1);
  if (boundary.clear()) return 1;

  let low = 0;
  let high = 1;
  for (let i = 0; i < 7; i++) {
    const mid = (low + high) / 2;
    apply(mid);
    if (boundary.clear()) low = mid;
    else high = mid;
  }
  apply(low);
  return low;
}

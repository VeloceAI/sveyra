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

const CLEARANCE_CM = 1.0; // let a limb rest against the body, not sink into it

function capsuleBones(capsules, byName, bones) {
  return capsules
    .map(function (capsule) {
      const index = byName.get(capsule.bone);
      if (index === undefined) return null;
      return {
        bone: bones[index],
        // Capsule ends in the bone's own frame, so they follow it when posed.
        head: new THREE.Vector3().fromArray(capsule.head).multiplyScalar(0.01),
        tail: new THREE.Vector3().fromArray(capsule.tail).multiplyScalar(0.01),
        radius: capsule.radius * 0.01,
        name: capsule.bone,
      };
    })
    .filter(Boolean);
}

// Sampled rather than solved. The closed form for segment-to-segment distance
// has several degenerate cases, and this runs over a couple of dozen capsules.
const _a = new THREE.Vector3();
const _b = new THREE.Vector3();

function segmentDistance(a0, a1, b0, b1) {
  let best = Infinity;
  for (let i = 0; i <= 8; i++) {
    _a.lerpVectors(a0, a1, i / 8);
    for (let j = 0; j <= 8; j++) {
      _b.lerpVectors(b0, b1, j / 8);
      best = Math.min(best, _a.distanceTo(_b));
    }
  }
  return best;
}

const _h = new THREE.Vector3();
const _t = new THREE.Vector3();

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
  constructor(volumes, byName, bones) {
    this.limbs = capsuleBones(volumes.limb || [], byName, bones);
    this.trunk = capsuleBones(volumes.trunk || [], byName, bones);
    this.baseline = new Map();
  }

  // Overlap in the current pose, per limb-trunk pair.
  measure() {
    const out = new Map();
    const ah = new THREE.Vector3();
    const at = new THREE.Vector3();
    const bh = new THREE.Vector3();
    const bt = new THREE.Vector3();

    for (const limb of this.limbs) {
      worldEnds(limb, ah, at);
      for (const trunk of this.trunk) {
        if (related(limb.bone, trunk.bone)) continue;
        worldEnds(trunk, bh, bt);
        const gap = segmentDistance(ah, at, bh, bt);
        const overlap = limb.radius + trunk.radius - gap;
        if (overlap > 0) out.set(`${limb.name}|${trunk.name}`, overlap);
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
      const extra = overlap - (this.baseline.get(pair) || 0);
      if (extra > worst) {
        worst = extra;
        where = pair;
      }
    }
    return { depth: worst * 100, where: where };
  }

  clear() {
    return this.intrusion().depth <= CLEARANCE_CM;
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

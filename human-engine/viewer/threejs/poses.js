// Outfit-check poses, authored anatomically.
//
// The rig rests in an A-pose with the arms already about fifty degrees below
// horizontal, and no bone is axis aligned: lowerarm01.L points out, down and
// forward all at once. So a pose cannot name an Euler component and hope. Each
// entry says what the joint should do — flex, abduct, twist — and the axis for
// that is derived from where the bone actually points at rest.
//
// Limbs come in twist pairs (upperarm01/02, lowerleg01/02). Bends belong on the
// 01 segment; putting them on 02 shears the limb. The spine is five segments,
// so a lean is spread across them rather than creasing at one ring.

const FORWARD = new THREE.Vector3(0, 0, 1); // the figure faces +Z
const UP = new THREE.Vector3(0, 1, 0);

// A pose is bone -> { flex, abduct, twist } in degrees.
//
//   flex    swings the bone forward, the way a knee lifts or an arm reaches
//   abduct  swings it away from the midline
//   twist   rotates it about its own length
const POSES = {
  stand: {
    label: "Front stand",
    note: "Arms held clear of the body so the garment's side seam reads.",
    joints: {
      "upperarm01.L": { abduct: 8 },
      "upperarm01.R": { abduct: 8 },
      "lowerarm01.L": { flex: 8 },
      "lowerarm01.R": { flex: 8 },
    },
  },
  threeQuarter: {
    label: "Three-quarter",
    note: "The angle clothing is normally photographed at.",
    root: { yaw: 35 },
    joints: { "upperarm01.L": { abduct: 8 }, "upperarm01.R": { abduct: 8 } },
  },
  profile: {
    label: "Profile",
    note: "Hem length, trouser break, how a jacket sits front to back.",
    root: { yaw: 90 },
    joints: { "upperarm01.L": { abduct: 6 }, "upperarm01.R": { abduct: 6 } },
  },
  back: {
    label: "Back",
    note: "Seat fit, back darts, the yoke across the shoulders.",
    root: { yaw: 180 },
    joints: { "upperarm01.L": { abduct: 8 }, "upperarm01.R": { abduct: 8 } },
  },
  reachUp: {
    label: "Reach up",
    note: "Shows a top riding up, a binding armhole, sleeves run short.",
    joints: {
      "clavicle.L": { abduct: 12 },
      "clavicle.R": { abduct: 12 },
      "upperarm01.L": { abduct: 118 },
      "upperarm01.R": { abduct: 118 },
      "lowerarm01.L": { flex: 12 },
      "lowerarm01.R": { flex: 12 },
      spine04: { flex: -4 },
      spine05: { flex: -4 },
    },
  },
  armsCrossed: {
    label: "Arms crossed",
    note: "Tightness across the upper back and through the shoulder.",
    joints: {
      "clavicle.L": { flex: 14 },
      "clavicle.R": { flex: 14 },
      "upperarm01.L": { flex: 42, abduct: -14 },
      "upperarm01.R": { flex: 42, abduct: -14 },
      "lowerarm01.L": { flex: 96 },
      "lowerarm01.R": { flex: 96 },
    },
  },
  sit: {
    label: "Sit",
    note: "Waistband tightness, skirt length on the thigh, seat pull.",
    joints: {
      "upperleg01.L": { flex: 85, abduct: 7 },
      "upperleg01.R": { flex: 85, abduct: 7 },
      "lowerleg01.L": { flex: -85 },
      "lowerleg01.R": { flex: -85 },
      "foot.L": { flex: -10 },
      "foot.R": { flex: -10 },
      spine01: { flex: 4 },
      spine02: { flex: 4 },
      "upperarm01.L": { flex: 14 },
      "upperarm01.R": { flex: 14 },
      "lowerarm01.L": { flex: 32 },
      "lowerarm01.R": { flex: 32 },
    },
  },
  stride: {
    label: "Stride",
    note: "Hem swing and where a trouser breaks over the shoe.",
    joints: {
      "upperleg01.L": { flex: 28 },
      "lowerleg01.L": { flex: -18 },
      "foot.L": { flex: -8 },
      "upperleg01.R": { flex: -22 },
      "lowerleg01.R": { flex: -38 },
      "foot.R": { flex: 14 },
      "upperarm01.L": { flex: -22 },
      "upperarm01.R": { flex: 22 },
      "lowerarm01.L": { flex: 26 },
      "lowerarm01.R": { flex: 20 },
      spine02: { flex: 2 },
      spine03: { flex: 2 },
    },
  },
  contrapposto: {
    label: "Weight shift",
    note: "How a garment hangs when the hips are not level.",
    joints: {
      "upperleg01.L": { abduct: 4 },
      "upperleg01.R": { flex: 12, abduct: -8 },
      "lowerleg01.R": { flex: -16 },
      "foot.R": { flex: 10 },
      spine02: { abduct: -4 },
      spine03: { abduct: -3 },
      neck02: { abduct: 4 },
      "upperarm01.L": { abduct: 10 },
      "upperarm01.R": { abduct: 6 },
      "lowerarm01.L": { flex: 18 },
      "lowerarm01.R": { flex: 10 },
    },
  },
};

// Anatomical axes for one bone, in world space at rest.
//
// The long axis is the twist. Abduction swings the limb within the plane it
// already occupies with the body's vertical, and flexion is perpendicular to
// both, which is what makes a knee bend backward and an arm reach forward
// without either being told which Euler component to use.
function anatomicalAxes(direction) {
  const long = direction.clone().normalize();
  let flex = new THREE.Vector3().crossVectors(long, UP);
  if (flex.lengthSq() < 1e-6) flex = new THREE.Vector3().crossVectors(long, FORWARD);
  flex.normalize();
  const abduct = new THREE.Vector3().crossVectors(long, flex).normalize();
  return { flex: flex, abduct: abduct, twist: long };
}

// A world-space rotation carried into the bone's own frame.
//
// bone.rotation is local, and these bones sit at arbitrary orientations, so an
// anatomical axis has to be expressed in the parent's frame before it means
// anything to three.js.
const _q = new THREE.Quaternion();
const _parentWorld = new THREE.Quaternion();
const _axis = new THREE.Vector3();

function rotationFor(bone, axes, request) {
  const result = new THREE.Quaternion();
  bone.parent?.getWorldQuaternion(_parentWorld);
  const inverse = _parentWorld.clone().invert();

  for (const [name, degrees] of Object.entries(request)) {
    const axis = axes[name];
    if (!axis || !degrees) continue;
    _axis.copy(axis).applyQuaternion(inverse).normalize();
    _q.setFromAxisAngle(_axis, (degrees * Math.PI) / 180);
    result.multiply(_q);
  }
  return result;
}

function poseTargets(pose, bones, byName, directions) {
  const targets = new Map();
  for (const [name, request] of Object.entries(pose.joints || {})) {
    const index = byName.get(name);
    if (index === undefined) continue;
    const bone = bones[index];
    const axes = anatomicalAxes(new THREE.Vector3().fromArray(directions[index]));
    targets.set(bone, rotationFor(bone, axes, request));
  }
  return targets;
}

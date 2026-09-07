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
// Clinical ranges of motion, degrees, from the AAOS and CDC reference values.
// A pose that asks for more than a body can do is clamped rather than drawn,
// because a figure bent past its own limits is the fastest way to look wrong.
// Matched by name prefix, so upperarm01.L and upperarm02.R share an entry.
const LIMITS = [
  ["upperarm", { flex: [-60, 180], abduct: [-40, 180], twist: [-90, 90] }],
  ["lowerarm", { flex: [0, 150], abduct: [0, 0], twist: [-80, 80] }],
  ["wrist", { flex: [-70, 80], abduct: [-20, 30], twist: [-10, 10] }],
  // The scapula rotates upward through about sixty degrees over a full arm
  // elevation, so this is wider than the small clavicular range it looks like.
  ["clavicle", { flex: [-20, 30], abduct: [-15, 55], twist: [-10, 10] }],
  ["upperleg", { flex: [-30, 120], abduct: [-30, 45], twist: [-40, 45] }],
  ["lowerleg", { flex: [-135, 0], abduct: [0, 0], twist: [0, 0] }],
  ["foot", { flex: [-50, 20], abduct: [-15, 15], twist: [-10, 10] }],
  ["spine", { flex: [-12, 18], abduct: [-12, 12], twist: [-15, 15] }],
  ["neck", { flex: [-25, 25], abduct: [-20, 20], twist: [-35, 35] }],
  ["head", { flex: [-20, 20], abduct: [-15, 15], twist: [-30, 30] }],
];

function limitsFor(name) {
  const entry = LIMITS.find(function (row) {
    return name.startsWith(row[0]);
  });
  return entry ? entry[1] : null;
}

function clampRequest(name, request) {
  const limit = limitsFor(name);
  if (!limit) return request;
  const out = {};
  for (const [axis, degrees] of Object.entries(request)) {
    const range = limit[axis];
    out[axis] = range ? Math.max(range[0], Math.min(range[1], degrees)) : degrees;
  }
  return out;
}

// How late each region starts moving, as a fraction of the transition.
//
// Everything starting and stopping together is what reads as robotic. Real
// movement is led by the heavy middle and trailed by the light extremities, so
// the spine goes first, the limbs follow and the head settles last.
const LEAD = [
  ["spine", 0.0],
  ["pelvis", 0.0],
  ["upperleg", 0.06],
  ["clavicle", 0.1],
  ["upperarm", 0.16],
  ["lowerleg", 0.2],
  ["lowerarm", 0.3],
  ["foot", 0.34],
  ["wrist", 0.42],
  ["neck", 0.34],
  ["head", 0.46],
];

function leadFor(name) {
  const entry = LEAD.find(function (row) {
    return name.startsWith(row[0]);
  });
  return entry ? entry[1] : 0.2;
}

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
      // Scapulohumeral rhythm: roughly two degrees at the humerus for every
      // one at the scapula. Raising the arm 120 degrees purely at the shoulder
      // joint, which an earlier version did, drags the deltoid away from a
      // torso that never moved, and the arm reads as cut off at the shoulder.
      "clavicle.L": { abduct: 40, flex: 6 },
      "clavicle.R": { abduct: 40, flex: 6 },
      "upperarm01.L": { abduct: 80 },
      "upperarm01.R": { abduct: 80 },
      "lowerarm01.L": { flex: 14 },
      "lowerarm01.R": { flex: 14 },
      spine04: { flex: -4 },
      spine05: { flex: -4 },
    },
  },
  armsCrossed: {
    label: "Arms crossed",
    note: "Tightness across the upper back and through the shoulder.",
    joints: {
      // The scapula protracts as the arms come across, and the upper arms stay
      // low so the elbows sit in front of the ribs rather than inside them.
      "clavicle.L": { flex: 20 },
      "clavicle.R": { flex: 20 },
      "upperarm01.L": { flex: 34, abduct: -8, twist: 20 },
      "upperarm01.R": { flex: 34, abduct: -8, twist: 20 },
      "lowerarm01.L": { flex: 88 },
      "lowerarm01.R": { flex: 88 },
    },
  },
  sit: {
    label: "Sit",
    note: "Waistband tightness, skirt length on the thigh, seat pull.",
    // Measured, not guessed: with the hips and knees at these angles the ankle
    // sits 41.4 cm above where it stands, so the body drops by exactly that and
    // the feet land back on the floor. Slightly back, as one does onto a seat.
    offset: { y: -0.414, z: -0.06 },
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
      // A walk, not a march. The leading heel stays near the ground and the
      // trailing foot only just leaves it; a big knee lift reads as marching
      // and tells you nothing about a hem.
      "upperleg01.L": { flex: 20 },
      "lowerleg01.L": { flex: -6 },
      "foot.L": { flex: -4 },
      "upperleg01.R": { flex: -14 },
      "lowerleg01.R": { flex: -22 },
      "foot.R": { flex: 18 },
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

  // Flexion happens in the sagittal plane, so its axis is across the body.
  // Taking it from the body's forward direction gives that directly and stays
  // stable for the near vertical bones. Crossing with UP instead, which an
  // earlier version did, is almost degenerate for a shin: the result was
  // dominated by the tiny lean in the bone and came out pointing forward, so
  // "bend the knee" swung the leg sideways.
  // Ordered so a positive flex swings the bone forward, which is what the
  // tables assume: a hip flexes forward, a knee flexes backward and so is
  // written negative.
  let flex = new THREE.Vector3().crossVectors(long, FORWARD);
  if (flex.lengthSq() < 0.04) {
    // Only for a bone already pointing along the body's forward axis, such as
    // a foot, where there is no sagittal component left to cross against.
    flex = new THREE.Vector3().crossVectors(long, UP);
  }
  flex.normalize();
  const abduct = new THREE.Vector3().crossVectors(long, flex).normalize();
  return { flex: flex, abduct: abduct, twist: long };
}

// An anatomical rotation as a local quaternion.
//
// Every bone is built from a position alone, with no rotation, so at bind time
// each one's world orientation is identity and a world-space axis is already
// the bone's local axis. Carrying the axis through the parent's *current*
// rotation, which an earlier version did, makes a child's axis counter-rotate
// as soon as its parent moves: flex the hip and the knee then bends in a
// direction that no longer means anything, which is why a sitting figure ended
// up with its foot a metre in the air.
const _q = new THREE.Quaternion();

function rotationFor(bone, axes, request) {
  const result = new THREE.Quaternion();
  for (const [name, degrees] of Object.entries(request)) {
    const axis = axes[name];
    if (!axis || !degrees) continue;
    _q.setFromAxisAngle(axis, (degrees * Math.PI) / 180);
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
    targets.set(bone, rotationFor(bone, axes, clampRequest(name, request)));
  }
  return targets;
}


// Sequences, as data.
//
// A step names a pose, how long to hold it and optionally a yaw to override the
// pose's own, which is what lets one turn pose serve both sides. Adding a
// routine means adding an entry here, not writing code.
//
// The fit check follows what people actually film: walk in, stop and pause,
// then turn slowly through every angle with a pause at the front, each side and
// the back, because a viewer needs a moment at each to read the garment.
const SEQUENCES = {
  fitCheck: {
    label: "Fit check",
    note: "Walk in, pause, turn slowly through every angle.",
    loop: true,
    steps: [
      { pose: "stride", hold: 500 },
      { pose: "stand", hold: 1100 },
      { pose: "threeQuarter", hold: 800 },
      { pose: "profile", hold: 900 },
      { pose: "back", hold: 1100 },
      { pose: "profile", yaw: -90, hold: 900 },
      { pose: "threeQuarter", yaw: -35, hold: 800 },
      { pose: "stand", hold: 1200 },
    ],
  },
  stressTest: {
    label: "Fit stress",
    note: "The four movements that find where a garment pulls.",
    loop: true,
    steps: [
      { pose: "stand", hold: 700 },
      { pose: "reachUp", hold: 1200 },
      { pose: "armsCrossed", hold: 1100 },
      { pose: "sit", hold: 1400 },
      { pose: "stride", hold: 900 },
    ],
  },
  sway: {
    label: "Idle sway",
    note: "A short loop, so the figure is never perfectly still.",
    loop: true,
    steps: [
      { pose: "stand", hold: 900 },
      { pose: "contrapposto", hold: 1200 },
      { pose: "stand", hold: 700 },
      { pose: "threeQuarter", yaw: 12, hold: 900 },
    ],
  },
};

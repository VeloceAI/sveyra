const DATA = JSON.parse(document.getElementById("avatar-data").textContent);

function bytesOf(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
const f32 = (b64) => new Float32Array(bytesOf(b64).buffer);
const u32 = (b64) => new Uint32Array(bytesOf(b64).buffer);
const u16 = (b64) => new Uint16Array(bytesOf(b64).buffer);

const indices = u32(DATA.indices);
const skinIndex = u16(DATA.skinIndex);
const skinWeight = f32(DATA.skinWeight);
const JOINTS = DATA.joints;
const PARENTS = DATA.parents;
const BONE_LOCAL = DATA.boneLocal;
const LIMITS = DATA.limits || {};

const variants = {};
for (const key of DATA.order) {
  const raw = DATA.variants[key];
  variants[key] = {
    label: raw.label,
    positions: f32(raw.positions),
    normals: f32(raw.normals),
    measurements: raw.measurements,
    boneLocal: raw.boneLocal,
  };
}
const BASE = variants[DATA.order[0]];
const restPos = new Float32Array(BASE.positions);
const restNrm = new Float32Array(BASE.normals);

const stage = document.getElementById("stage");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0c11);

const camera = new THREE.PerspectiveCamera(34, 1, 0.05, 60);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
// sRGB out, no tone mapping. Filmic tone mapping is what turned the cream
// brown: it rolls highlights down and desaturates, and a pale warm body is
// exactly the thing it eats. mannequin.js uses none either.
renderer.outputEncoding = THREE.sRGBEncoding;
stage.appendChild(renderer.domElement);

// The stage stays dark; only the figure is mannequin.js's. Shadows are new:
// a soft contact shadow is what stops the doll reading as if it were floating.
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

scene.add(new THREE.HemisphereLight(0xf2f6ff, 0x1a1f28, 1.35));
const keyLight = new THREE.DirectionalLight(0xfffaf2, 2.0);
keyLight.position.set(2.4, 3.4, 2.6);
keyLight.castShadow = true;
keyLight.shadow.mapSize.width = 2048;
keyLight.shadow.mapSize.height = 2048;
keyLight.shadow.camera.near = 1;
keyLight.shadow.camera.far = 12;
keyLight.shadow.camera.left = -1.6;
keyLight.shadow.camera.right = 1.6;
keyLight.shadow.camera.top = 2.4;
keyLight.shadow.camera.bottom = -0.4;
keyLight.shadow.normalBias = 0.004;
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x86b4ff, 1.5);
rimLight.position.set(-2.8, 1.6, -2.6);
scene.add(rimLight);

const grid = new THREE.GridHelper(10, 40, 0x24303f, 0x141a22);
grid.material.transparent = true;
grid.material.opacity = 0.55;
scene.add(grid);

// Catches the shadow and nothing else, so the grid still shows through.
const shadowCatcher = new THREE.Mesh(
  new THREE.CircleGeometry(3, 48),
  new THREE.ShadowMaterial({ opacity: 0.5 }),
);
shadowCatcher.receiveShadow = true;
shadowCatcher.rotation.x = -Math.PI / 2;
shadowCatcher.position.y = 0.001;
scene.add(shadowCatcher);

// Rigid parts, the mannequin.js approach, not skinning.
//
// A wooden doll is carved pieces held by ball joints. Modelling it that way is
// not a shortcut: rigid transforms cannot tear, which is the failure that
// dogged every skinned version of this. Each part becomes its own mesh parented
// to its bone, so rotating a joint moves its part and everything below it
// exactly as a real jointed figure does.

const PART_OF = DATA.partOf;
const PART_NAMES = DATA.partNames;

// Which bone carries which carved part.
const PART_BONE = {
  torso: "spine_2",
  head: "head",
  upperarm_L: "upperarm_L",
  upperarm_R: "upperarm_R",
  forearm_L: "forearm_L",
  forearm_R: "forearm_R",
  thigh_L: "thigh_L",
  thigh_R: "thigh_R",
  calf_L: "calf_L",
  calf_R: "calf_R",
  foot_L: "foot_L",
  foot_R: "foot_R",
};

const bones = JOINTS.map(function (name, i) {
  const bone = new THREE.Bone();
  bone.name = name;
  bone.position.set(BONE_LOCAL[i][0], BONE_LOCAL[i][1], BONE_LOCAL[i][2]);
  return bone;
});
bones.forEach(function (bone, i) {
  if (PARENTS[i] >= 0) bones[PARENTS[i]].add(bone);
});
const rig = new THREE.Group();
bones.forEach(function (bone, i) {
  if (PARENTS[i] < 0) rig.add(bone);
});
scene.add(rig);
rig.updateMatrixWorld(true);

const boneIndex = {};
JOINTS.forEach(function (name, i) {
  boneIndex[name] = i;
});

// mannequin.js's own palette. The torso is a shade warmer than the limbs and
// the joints are darker again, which is what separates the pieces by eye
// without any outline.
const BODY_COLORS = {
  LIMBS: "#eae4dc",
  TORSO: "#e4ddd3",
  HEAD: "#eae4dc",
  JOINTS: "#d5cec4",
};

// The faint weave mannequin.js maps onto every limb. Without it the cream
// reads as flat plastic; with it the figure looks turned from wood.
const LIMB_TEXTURE = new THREE.TextureLoader().load(
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABAAQMAAACQp+OdAAAABlBMVEX" +
    "////Ly8vsgL9iAAAAHElEQVQoz2OgEPyHAjgDjxoKGWTaRRkYDR/8AAAU9d8hJ6+ZxgAAAABJRU5ErkJggg==",
);
LIMB_TEXTURE.wrapS = LIMB_TEXTURE.wrapT = THREE.RepeatWrapping;
LIMB_TEXTURE.repeat.set(3, 3);

function bodyMaterial(color) {
  return new THREE.MeshStandardMaterial({
    color: color,
    map: LIMB_TEXTURE,
    roughness: 1,
    metalness: 0,
  });
}

const limbMaterial = bodyMaterial(BODY_COLORS.LIMBS);
const torsoMaterial = bodyMaterial(BODY_COLORS.TORSO);
const headMaterial = bodyMaterial(BODY_COLORS.HEAD);
const jointMaterial = new THREE.MeshStandardMaterial({
  color: BODY_COLORS.JOINTS,
  roughness: 1,
  metalness: 0,
});

function materialFor(part) {
  if (part === "torso") return torsoMaterial;
  if (part === "head") return headMaterial;
  return limbMaterial;
}
const wireMaterial = new THREE.MeshBasicMaterial({
  color: 0x9fd0ff,
  wireframe: true,
  transparent: true,
  opacity: 0.25,
});

// Faces whose three corners all sit in one part. A face spanning two parts is
// dropped: on a jointed figure that seam is where the gap belongs.
const partFaces = {};
PART_NAMES.forEach(function (n) {
  partFaces[n] = [];
});
for (let f = 0; f < indices.length; f += 3) {
  const a = indices[f];
  const b = indices[f + 1];
  const c = indices[f + 2];
  if (PART_OF[a] === PART_OF[b] && PART_OF[b] === PART_OF[c]) {
    partFaces[PART_NAMES[PART_OF[a]]].push(a, b, c);
  }
}

const parts = [];

// A jointed figure has a ball at every pivot. It is what covers the seam the
// dropped faces leave, and it is why a wooden doll reads as one figure rather
// than a pile of carved pieces. mannequin.js merges a sphere into every limb at
// the joint; this does the same, sized from the mesh instead of by hand.
const BALL_JOINTS = [
  "neck",
  "upperarm_L", "upperarm_R", "forearm_L", "forearm_R", "hand_L", "hand_R",
  "thigh_L", "thigh_R", "calf_L", "calf_R", "foot_L", "foot_R",
];

// The longest side of a part's bounding box, for pieces with no child bone to
// point at.
function spread(positions) {
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < positions.length; i += 3) {
    for (let k = 0; k < 3; k++) {
      lo[k] = Math.min(lo[k], positions[i + k]);
      hi[k] = Math.max(hi[k], positions[i + k]);
    }
  }
  const size = hi.map(function (v, k) {
    return v - lo[k];
  });
  const longest = size.indexOf(Math.max.apply(null, size));
  return new THREE.Vector3(
    longest === 0 ? 1 : 0,
    longest === 1 ? 1 : 0,
    longest === 2 ? 1 : 0,
  );
}

// Filled while the pieces are built: how thick each one is at its own joint.
const ballRadius = {};

// The trunk is two pieces, chest and pelvis, hinged at the waist. As one piece
// it can only ever be a slab: bending at the waist is what a torso does, and
// the seam is also where the shape of a body actually reads.
function emitTrunk(positions, axis, spineBone, spineWorld) {
  const halves = splitAtWaist(positions, axis);
  const pelvisBone = bones[boneIndex.pelvis];
  const shift = new THREE.Vector3();
  if (pelvisBone) {
    pelvisBone.getWorldPosition(shift);
    shift.sub(spineWorld);
  }

  [
    ["chest", halves.upper, spineBone, new THREE.Vector3()],
    ["pelvis", halves.lower, pelvisBone || spineBone, shift],
  ].forEach(function (entry) {
    const [label, verts, bone, offset] = entry;
    if (!bone || verts.length < 9) return;
    // Pelvis vertices were measured against the spine, so they move into the
    // pelvis bone's frame before the shape is turned.
    const local = verts.slice();
    for (let i = 0; i < local.length; i += 3) {
      local[i] -= offset.x;
      local[i + 1] -= offset.y;
      local[i + 2] -= offset.z;
    }
    const geo = limbGeometry(local, axis);
    ballRadius[label === "chest" ? "spine_2" : "pelvis"] = geo.userData.endRadius;

    const mesh = new THREE.Mesh(geo, materialFor("torso"));
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const wire = new THREE.Mesh(geo, wireMaterial);
    wire.visible = false;
    bone.add(mesh);
    bone.add(wire);
    parts.push({ name: label, mesh: mesh, wire: wire });
  });
}

function buildParts() {
  parts.forEach(function (p) {
    if (p.mesh.parent) p.mesh.parent.remove(p.mesh);
    if (p.wire !== p.mesh && p.wire.parent) p.wire.parent.remove(p.wire);
    if (p.mesh.geometry) p.mesh.geometry.dispose();
  });
  parts.length = 0;

  // Offsets must be measured in the rest pose. Rebuilding while the figure is
  // posed would bake the current rotation into the geometry.
  const held = bones.map(function (b) {
    return b.rotation.clone();
  });
  bones.forEach(function (b) {
    b.rotation.set(0, 0, 0);
  });
  rig.updateMatrixWorld(true);

  const worldPos = new THREE.Vector3();
  PART_NAMES.forEach(function (name) {
    const faces = partFaces[name];
    if (!faces.length) return;
    const boneName = PART_BONE[name] || "pelvis";
    const bone = bones[boneIndex[boneName]];
    if (!bone) return;

    bone.getWorldPosition(worldPos);

    // Vertices are stored in bone-local space so the part sits correctly once
    // parented, and stays rigid however the bone turns.
    const used = new Set();
    const positions = [];
    for (let i = 0; i < faces.length; i++) {
      const v = faces[i];
      if (used.has(v)) continue;
      used.add(v);
      positions.push(
        restPos[v * 3] - worldPos.x,
        restPos[v * 3 + 1] - worldPos.y,
        restPos[v * 3 + 2] - worldPos.z,
      );
    }

    // The engine's own triangles are the measurement; what gets drawn is a
    // turned shape fitted to them, so the piece caps off round at the joint
    // rather than ending on the flat face the part split left behind.
    const child = firstChild[boneIndex[boneName]];
    const geo = limbGeometry(positions, child ? child.position : spread(positions));

    ballRadius[boneName] = geo.userData.endRadius;

    if (name === "torso") {
      emitTrunk(positions, child ? child.position : spread(positions), bone, worldPos);
      return;
    }

    const mesh = new THREE.Mesh(geo, materialFor(name));
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    const wire = new THREE.Mesh(geo, wireMaterial);
    wire.visible = false;
    bone.add(mesh);
    bone.add(wire);
    parts.push({ name: name, mesh: mesh, wire: wire });
  });

  BALL_JOINTS.forEach(function (name) {
    const bone = bones[boneIndex[name]];
    if (!bone) return;
    // A joint's ball is the thickness of the piece hanging off it. Where no
    // piece does (a wrist, an ankle) it is the far end of the piece above.
    const index = boneIndex[name];
    const own = ballRadius[name];
    const parent = ballRadius[JOINTS[PARENTS[index]]];
    const child = firstChild[index] ? ballRadius[firstChild[index].name] : null;
    const r = own
      ? own.near
      : parent
        ? parent.far
        : child
          ? child.near
          : null;
    if (!r || !isFinite(r) || r <= 0) return;
    const geo = new THREE.SphereGeometry(r * 1.02, 22, 16);
    const ball = new THREE.Mesh(geo, jointMaterial);
    ball.castShadow = true;
    ball.receiveShadow = true;
    const ballWire = new THREE.Mesh(geo, wireMaterial);
    ballWire.visible = false;
    bone.add(ball);
    bone.add(ballWire);
    parts.push({ name: name + " ball", mesh: ball, wire: ballWire });
  });

  ["L", "R"].forEach(function (side) {
    const bone = bones[boneIndex["hand_" + side]];
    const wrist = ballRadius["forearm_" + side];
    if (!bone || !wrist) return;
    // The forearm runs outward along X at rest, so the hand continues that way
    // and the fingers spread along Z.
    const out = new THREE.Vector3(side === "L" ? 1 : -1, 0, 0);
    const across = new THREE.Vector3(0, 0, 1);
    const hand = buildHand(wrist.far, out, across, limbMaterial);
    bone.add(hand);
    parts.push({ name: "hand_" + side, mesh: hand, wire: hand });
  });

  measureTorso(worldPos);

  bones.forEach(function (b, i) {
    b.rotation.copy(held[i]);
  });
  rig.updateMatrixWorld(true);
}

// The torso's own extent, in its own frame. Measured rather than hardcoded so
// the test still holds when the body is short, tall or heavy.
const torsoBox = new THREE.Box3();

function measureTorso(scratch) {
  const bone = bones[boneIndex.spine_2];
  if (!bone || !partFaces.torso.length) return;
  bone.getWorldPosition(scratch);
  torsoBox.makeEmpty();
  const seen = new Set();
  const point = new THREE.Vector3();
  partFaces.torso.forEach(function (v) {
    if (seen.has(v)) return;
    seen.add(v);
    torsoBox.expandByPoint(
      point.set(
        restPos[v * 3] - scratch.x,
        restPos[v * 3 + 1] - scratch.y,
        restPos[v * 3 + 2] - scratch.z,
      ),
    );
  });
  // Pull the sides in: an arm hanging against the body is not a collision.
  torsoBox.min.x += 0.045;
  torsoBox.max.x -= 0.045;
  torsoBox.min.z += 0.02;
  torsoBox.max.z -= 0.02;
}

const helper = new THREE.SkeletonHelper(rig);
helper.visible = false;
scene.add(helper);

// Handles are children of their bone, so they follow the pose for free.
const handles = bones.map(function (bone, i) {
  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.026, 16, 12),
    new THREE.MeshStandardMaterial({
      color: PARENTS[i] < 0 ? 0x7bc49a : 0x9fb3c8,
      roughness: 0.35,
      emissive: 0x231505,
      depthTest: false,
    }),
  );
  dot.renderOrder = 5;
  dot.visible = false;
  dot.userData.bone = i;
  bone.add(dot);
  return dot;
});

// Ranges arrive already resolved to x, y and z. Which of them is the bend is
// not the same for every joint: the legs hang down Y so a knee bends about X,
// while the T-pose arms lie along X, so an elbow bends about Y. Reading the
// axis ranges rather than the anatomical names is what keeps that straight.
let posture = "standing";
let easing = null;

// The figure never sits in the T-pose it was modelled in. Every posture is
// written from anatomical neutral, so applying one starts from the neutral the
// limits carry rather than from zero.
function applyPosture(key, animate) {
  const preset = POSTURES[key];
  if (!preset) return;
  posture = key;
  const wanted = postureToRotations(preset, LIMITS);
  const from = bones.map(function (b) {
    return b.rotation.clone();
  });
  const to = bones.map(function (b, i) {
    const target = wanted[JOINTS[i]] || (LIMITS[JOINTS[i]] || {}).neutral || [0, 0, 0];
    return new THREE.Euler(target[0], target[1], target[2]);
  });
  bones.forEach(function (_, i) {
    clampTo(i, to[i]);
  });
  if (!animate) {
    bones.forEach(function (b, i) {
      b.rotation.copy(to[i]);
    });
    rig.updateMatrixWorld(true);
    return;
  }
  easing = { from: from, to: to, t: 0 };
}

function clampTo(index, euler) {
  const limit = LIMITS[JOINTS[index]];
  if (!limit || !limit.axis) return;
  const v = [euler.x, euler.y, euler.z].map(function (value, i) {
    return Math.max(limit.axis[i][0], Math.min(limit.axis[i][1], value));
  });
  euler.set(v[0], v[1], v[2]);
}

function stepEasing(delta) {
  if (!easing) return;
  easing.t = Math.min(1, easing.t + delta * 2.2);
  // Smoothstep: a limb that starts and stops gently reads as a movement.
  const k = easing.t * easing.t * (3 - 2 * easing.t);
  bones.forEach(function (b, i) {
    b.rotation.set(
      easing.from[i].x + (easing.to[i].x - easing.from[i].x) * k,
      easing.from[i].y + (easing.to[i].y - easing.from[i].y) * k,
      easing.from[i].z + (easing.to[i].z - easing.from[i].z) * k,
    );
  });
  if (easing.t >= 1) easing = null;
}

function clampBone(index) {
  const limit = LIMITS[JOINTS[index]];
  if (!limit || !limit.axis) return false;
  const r = bones[index].rotation;
  const before = [r.x, r.y, r.z];
  const after = before.map(function (value, i) {
    return Math.max(limit.axis[i][0], Math.min(limit.axis[i][1], value));
  });
  r.set(after[0], after[1], after[2]);
  return after.some(function (value, i) {
    return value !== before[i];
  });
}

// Setting one axis at a time, with that axis applied last. Without the reorder
// a bend leaks into twist and a hinge stops behaving like a hinge; mannequin.js
// reorders in every joint accessor for the same reason.
const AXIS_ORDER = { x: "YZX", y: "ZXY", z: "YXZ" };
const AXIS_NAME = ["x", "y", "z"];

function nudgeAxis(index, axis, delta) {
  const r = bones[index].rotation;
  r.reorder(AXIS_ORDER[axis]);
  r[axis] += delta;
}

// The axes this joint can actually turn about. A hinge has one, a shoulder has
// three, and dragging should reach whichever they are rather than assuming
// every joint bends the way a knee does.
function freeAxes(index) {
  const limit = LIMITS[JOINTS[index]];
  if (!limit || !limit.axis) return [0, 1, 2];
  const free = [];
  limit.axis.forEach(function (range, i) {
    if (range[0] !== range[1]) free.push(i);
  });
  return free;
}

const firstChild = bones.map(function (_, i) {
  const j = PARENTS.indexOf(i);
  return j < 0 ? null : bones[j];
});

const LIMB_BONES = [
  "upperarm_L", "upperarm_R", "forearm_L", "forearm_R",
  "thigh_L", "thigh_R", "calf_L", "calf_R",
];

// How far a limb has pushed into the torso. Angle limits alone cannot catch
// this: every single angle can sit inside its range while the arm passes
// straight through the chest. mannequin.js scores the penetration and refuses
// any move that makes it worse, which is the rule applied below.
const _probe = new THREE.Vector3();
const _tip = new THREE.Vector3();

function depthInside(p) {
  const dx = Math.min(p.x - torsoBox.min.x, torsoBox.max.x - p.x);
  const dy = Math.min(p.y - torsoBox.min.y, torsoBox.max.y - p.y);
  const dz = Math.min(p.z - torsoBox.min.z, torsoBox.max.z - p.z);
  if (dx <= 0 || dy <= 0 || dz <= 0) return 0;
  return Math.min(dx, dz);
}

function impossibleLevel() {
  const torso = bones[boneIndex.spine_2];
  if (!torso || torsoBox.isEmpty()) return 0;
  let worst = 0;
  for (const name of LIMB_BONES) {
    const i = boneIndex[name];
    const bone = bones[i];
    if (!bone) continue;
    const child = firstChild[i];
    _tip.copy(child ? child.position : bone.position).multiplyScalar(child ? 1 : 0);
    // Probe along the limb, not only at its end: an upper arm can be inside the
    // chest while its elbow is clear of it.
    for (const t of [0.55, 1]) {
      _probe.copy(_tip).multiplyScalar(t);
      bone.localToWorld(_probe);
      torso.worldToLocal(_probe);
      worst = Math.max(worst, depthInside(_probe));
    }
  }
  return worst;
}

let target = DATA.order[1];
let blend = 1;
let posedBone = null;

function applyBlend() {
  const to = variants[target];
  for (let i = 0; i < restPos.length; i++) {
    restPos[i] = BASE.positions[i] + (to.positions[i] - BASE.positions[i]) * blend;
    restNrm[i] = BASE.normals[i] + (to.normals[i] - BASE.normals[i]) * blend;
  }

  // The skeleton has to morph with the mesh. Leaving it at the base body's
  // size is what hung a grown adult's arms off a child: the mesh shrinks, the
  // bones do not, and every piece is placed outside the body it belongs to.
  const fromBones = BASE.boneLocal || BONE_LOCAL;
  const toBones = to.boneLocal || BONE_LOCAL;
  bones.forEach(function (bone, i) {
    bone.position.set(
      fromBones[i][0] + (toBones[i][0] - fromBones[i][0]) * blend,
      fromBones[i][1] + (toBones[i][1] - fromBones[i][1]) * blend,
      fromBones[i][2] + (toBones[i][2] - fromBones[i][2]) * blend,
    );
  });
  rig.updateMatrixWorld(true);

  buildParts();
  renderReadout();
}

const ROWS = [
  ["height_cm", "Height"],
  ["chest_girth_cm", "Chest"],
  ["waist_girth_cm", "Waist"],
  ["hip_girth_cm", "Hip"],
  ["shoulder_width_cm", "Shoulders"],
  ["inseam_cm", "Inseam"],
];
const rowsEl = document.getElementById("rows");
const noteEl = document.getElementById("note");

function renderReadout() {
  const to = variants[target];
  rowsEl.innerHTML = "";
  for (let r = 0; r < ROWS.length; r++) {
    const a = BASE.measurements[ROWS[r][0]];
    const b = to.measurements[ROWS[r][0]];
    if (a === undefined || b === undefined) continue;
    const value = a + (b - a) * blend;
    const row = document.createElement("div");
    row.className = Math.abs(value - a) > 0.05 ? "row changed" : "row";
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = ROWS[r][1];
    const val = document.createElement("span");
    val.className = "value";
    val.textContent = value.toFixed(1);
    const unit = document.createElement("span");
    unit.className = "unit";
    unit.textContent = "cm";
    val.appendChild(unit);
    row.appendChild(name);
    row.appendChild(val);
    rowsEl.appendChild(row);
  }
  noteEl.textContent =
    posedBone === null
      ? Math.round(blend * 100) + "% toward " + to.label + ". Drag a joint to pose it."
      : "Posing " + JOINTS[posedBone].replace("_", " ") + ".";
}

const orbit = {
  target: new THREE.Vector3(0, 0.92, 0),
  radius: 3.6,
  theta: 0.42,
  phi: 1.28,
  auto: false,
};

function placeCamera() {
  orbit.phi = Math.max(0.18, Math.min(Math.PI - 0.18, orbit.phi));
  orbit.radius = Math.max(1.2, Math.min(9, orbit.radius));
  camera.position.set(
    orbit.target.x + orbit.radius * Math.sin(orbit.phi) * Math.sin(orbit.theta),
    orbit.target.y + orbit.radius * Math.cos(orbit.phi),
    orbit.target.z + orbit.radius * Math.sin(orbit.phi) * Math.cos(orbit.theta),
  );
  camera.lookAt(orbit.target);
}

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let dragging = false;
let lastX = 0;
let lastY = 0;

function pickBone(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(handles, false)[0];
  return hit ? hit.object.userData.bone : null;
}

renderer.domElement.addEventListener("pointerdown", function (event) {
  posedBone = pickBone(event);
  dragging = true;
  lastX = event.clientX;
  lastY = event.clientY;
  renderer.domElement.setPointerCapture(event.pointerId);
  renderReadout();
});
renderer.domElement.addEventListener("pointerup", function (event) {
  dragging = false;
  posedBone = null;
  renderer.domElement.releasePointerCapture(event.pointerId);
  renderReadout();
});
renderer.domElement.addEventListener("pointermove", function (event) {
  if (!dragging) {
    const over = pickBone(event);
    renderer.domElement.style.cursor = over === null ? "grab" : "pointer";
    handles.forEach(function (dot, i) {
      dot.scale.setScalar(i === over ? 1.5 : 1);
    });
    return;
  }
  const dx = (event.clientX - lastX) * 0.008;
  const dy = (event.clientY - lastY) * 0.008;
  lastX = event.clientX;
  lastY = event.clientY;
  if (posedBone !== null) {
    const before = impossibleLevel();
    const held = bones[posedBone].rotation.clone();
    const free = freeAxes(posedBone);
    if (free.length) {
      nudgeAxis(posedBone, AXIS_NAME[free[free.length - 1]], -dx);
      nudgeAxis(posedBone, AXIS_NAME[free[0]], dy);
    }
    const hit = clampBone(posedBone);
    rig.updateMatrixWorld(true);
    let blocked = false;
    if (impossibleLevel() > before + 1e-6) {
      bones[posedBone].rotation.copy(held);
      rig.updateMatrixWorld(true);
      blocked = true;
    }
    handles[posedBone].material.color.setHex(
      hit || blocked ? 0xd2694f : 0x9fb3c8,
    );
  } else {
    orbit.theta -= dx * 0.6;
    orbit.phi -= dy * 0.6;
    placeCamera();
  }
});
renderer.domElement.addEventListener(
  "wheel",
  function (event) {
    event.preventDefault();
    orbit.radius *= event.deltaY > 0 ? 1.08 : 0.93;
    placeCamera();
  },
  { passive: false },
);

const variantsEl = document.getElementById("variants");
DATA.order.slice(1).forEach(function (k) {
  const button = document.createElement("button");
  button.className = "variant";
  button.type = "button";
  button.setAttribute("aria-pressed", String(k === target));
  const label = document.createElement("span");
  label.textContent = variants[k].label;
  const delta = document.createElement("span");
  delta.className = "delta";
  delta.textContent = "morph";
  button.appendChild(label);
  button.appendChild(delta);
  button.addEventListener("click", function () {
    target = k;
    for (const other of variantsEl.children) {
      other.setAttribute("aria-pressed", String(other === button));
    }
    applyBlend();
  });
  variantsEl.appendChild(button);
});

const blendInput = document.getElementById("blend");
const blendAmount = document.getElementById("blend-amount");
blendInput.addEventListener("input", function () {
  blend = Number(blendInput.value) / 100;
  blendAmount.textContent = blendInput.value + "%";
  applyBlend();
});
document.getElementById("wire").addEventListener("change", function (e) {
  parts.forEach(function (p) {
    p.wire.visible = e.target.checked;
  });
});
document.getElementById("bones").addEventListener("change", function (e) {
  helper.visible = e.target.checked;
  // The pivot marks belong with the skeleton. Left on, they scatter dots down
  // a figure that is meant to read as one carved object.
  handles.forEach(function (dot) {
    dot.visible = e.target.checked;
  });
});
document.getElementById("spin").addEventListener("change", function (e) {
  orbit.auto = e.target.checked;
});
document.getElementById("reset").addEventListener("click", function () {
  applyPosture("standing", true);
  const buttons = document.getElementById("postures");
  if (buttons) {
    for (const b of buttons.children) {
      b.setAttribute("aria-pressed", String(b.textContent === POSTURES.standing.label));
    }
  }
});

function resize() {
  const w = stage.clientWidth || window.innerWidth;
  const h = stage.clientHeight || window.innerHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
// Posture buttons, in the panel above the reset.
const postureEl = document.getElementById("postures");
if (postureEl) {
  Object.keys(POSTURES).forEach(function (key) {
    const button = document.createElement("button");
    button.className = "variant";
    button.type = "button";
    button.setAttribute("aria-pressed", String(key === posture));
    const label = document.createElement("span");
    label.textContent = POSTURES[key].label;
    button.appendChild(label);
    button.addEventListener("click", function () {
      applyPosture(key, true);
      for (const other of postureEl.children) {
        other.setAttribute("aria-pressed", String(other === button));
      }
    });
    postureEl.appendChild(button);
  });
}

resize();
placeCamera();
applyBlend();
applyPosture("standing", false);

let last = 0;
(function tick(now) {
  requestAnimationFrame(tick);
  const delta = last ? Math.min(0.05, (now - last) / 1000) : 0;
  last = now || 0;
  stepEasing(delta);
  if (orbit.auto) {
    orbit.theta += 0.0035;
    placeCamera();
  }
  renderer.render(scene, camera);
})(0);

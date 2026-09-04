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

const variants = {};
for (const key of DATA.order) {
  const raw = DATA.variants[key];
  variants[key] = {
    label: raw.label,
    positions: f32(raw.positions),
    normals: f32(raw.normals),
    joints: f32(raw.joints),
    measurements: raw.measurements,
  };
}
const BASE = variants[DATA.order[0]];

const stage = document.getElementById("stage");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1A1613);
scene.fog = new THREE.Fog(0x1A1613, 5.0, 12);

const camera = new THREE.PerspectiveCamera(34, 1, 0.05, 60);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
// Without sRGB output, every colour is written in the wrong space and the
// whole image reads flat and washed out. Tone mapping then keeps highlights
// from clipping instead of blowing to white.
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.physicallyCorrectLights = true;
stage.appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xF2E2CB, 0x1A1410, 1.4));
const keyLight = new THREE.DirectionalLight(0xFFF4E4, 3.4);
keyLight.position.set(2.4, 3.4, 2.6);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0xFFC48F, 2.6);
rimLight.position.set(-2.8, 1.6, -2.6);
scene.add(rimLight);
const underLight = new THREE.DirectionalLight(0x8FA8C8, 1.1);
underLight.position.set(0.4, -1.2, 1.6);
scene.add(underLight);

(function buildEnvironment() {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  const sky = ctx.createLinearGradient(0, 0, 0, size);
  sky.addColorStop(0.0, "#6E7B92");
  sky.addColorStop(0.45, "#3A3730");
  sky.addColorStop(1.0, "#14100D");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.mapping = THREE.EquirectangularReflectionMapping;
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  scene.environment = pmrem.fromEquirectangular(texture).texture;
  texture.dispose();
  pmrem.dispose();
})();

const grid = new THREE.GridHelper(10, 40, 0x4A3B2E, 0x2A2119);
grid.material.transparent = true;
grid.material.opacity = 0.5;
scene.add(grid);

const N = DATA.vertexCount;
const restPos = new Float32Array(BASE.positions);
const restNrm = new Float32Array(BASE.normals);
let currentJoints = new Float32Array(BASE.joints);

const geometry = new THREE.BufferGeometry();
geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(restPos), 3));
geometry.setAttribute("normal", new THREE.BufferAttribute(new Float32Array(restNrm), 3));
geometry.setIndex(new THREE.BufferAttribute(indices, 1));

// Maple, not plastic: warm and light, rough enough to read as turned wood
// under a single warm key rather than as a shiny toy.
const material = new THREE.MeshStandardMaterial({
  color: 0xE3C9A6,
  roughness: 0.62,
  metalness: 0.03,
  emissive: 0x000000,
  emissiveIntensity: 0.0,
  envMapIntensity: 0.9,
});
scene.add(new THREE.Mesh(geometry, material));

const wireMesh = new THREE.Mesh(
  geometry,
  new THREE.MeshBasicMaterial({
    color: 0xE8C39A,
    wireframe: true,
    transparent: true,
    opacity: 0.22,
  }),
);
wireMesh.visible = false;
scene.add(wireMesh);

const boneGroup = new THREE.Group();
scene.add(boneGroup);

const boneLineGeom = new THREE.BufferGeometry();
boneLineGeom.setAttribute(
  "position",
  new THREE.Float32BufferAttribute(new Float32Array((JOINTS.length - 1) * 6), 3),
);
const boneLines = new THREE.LineSegments(
  boneLineGeom,
  new THREE.LineBasicMaterial({ color: 0xE8C39A, depthTest: false, transparent: true }),
);
boneLines.renderOrder = 9;
boneLines.visible = false;
boneGroup.add(boneLines);

const jointDots = JOINTS.map((name, i) => {
  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.052, 20, 16),
    new THREE.MeshStandardMaterial({
      color: PARENTS[i] < 0 ? 0x9A6B3E : 0xA87844,
      roughness: 0.5,
      metalness: 0.06,
      emissive: 0x241708,
      emissiveIntensity: 0.35,
    }),
  );
  dot.renderOrder = 10;
  dot.userData.joint = i;
  boneGroup.add(dot);
  return dot;
});


const PART_OF = DATA.partOf;
const PART_COUNT = DATA.partNames.length;
const SEGMENT_GAP = 0.955;
const partCentre = new Float32Array(PART_COUNT * 3);

(function computePartCentres() {
  const counts = new Float32Array(PART_COUNT);
  for (let i = 0; i < N; i++) {
    const p = PART_OF[i];
    partCentre[p * 3] += BASE.positions[i * 3];
    partCentre[p * 3 + 1] += BASE.positions[i * 3 + 1];
    partCentre[p * 3 + 2] += BASE.positions[i * 3 + 2];
    counts[p]++;
  }
  for (let p = 0; p < PART_COUNT; p++) {
    if (!counts[p]) continue;
    partCentre[p * 3] /= counts[p];
    partCentre[p * 3 + 1] /= counts[p];
    partCentre[p * 3 + 2] /= counts[p];
  }
})();

function segmentRest() {
  for (let i = 0; i < N; i++) {
    const p = PART_OF[i] * 3;
    for (let k = 0; k < 3; k++) {
      const c = partCentre[p + k];
      restPos[i * 3 + k] = c + (restPos[i * 3 + k] - c) * SEGMENT_GAP;
    }
  }
}

const rotations = JOINTS.map(() => new THREE.Euler(0, 0, 0));
// Joint limits come from the engine (skeleton/limits.py, serialised into the
// payload). Duplicating them here in JavaScript is how a viewer drifts from the
// rules the body is actually built with.
const LIMITS = DATA.limits || {};

function clampJoint(index) {
  const limit = LIMITS[JOINTS[index]];
  if (!limit) return false;
  const rotation = rotations[index];
  const x = Math.max(limit.flex[0], Math.min(limit.flex[1], rotation.x));
  const z = Math.max(limit.abduct[0], Math.min(limit.abduct[1], rotation.z));
  const y = Math.max(limit.twist[0], Math.min(limit.twist[1], rotation.y));
  const hitLimit = x !== rotation.x || z !== rotation.z || y !== rotation.y;
  rotation.set(x, y, z);
  return hitLimit;
}

const worldMat = JOINTS.map(() => new THREE.Matrix4());
const bindInv = JOINTS.map(() => new THREE.Matrix4());

function rebuildBind() {
  for (let i = 0; i < JOINTS.length; i++) {
    bindInv[i].makeTranslation(
      -currentJoints[i * 3],
      -currentJoints[i * 3 + 1],
      -currentJoints[i * 3 + 2],
    );
  }
}

const tmpMat = new THREE.Matrix4();
const localMat = new THREE.Matrix4();
const skinnedMat = new THREE.Matrix4();
const vecA = new THREE.Vector3();
const accP = new THREE.Vector3();
const accN = new THREE.Vector3();
const jointWorld = new THREE.Vector3();
const parentWorld = new THREE.Vector3();

function updatePose() {
  for (let i = 0; i < JOINTS.length; i++) {
    const p = PARENTS[i];
    const px = p < 0 ? 0 : currentJoints[p * 3];
    const py = p < 0 ? 0 : currentJoints[p * 3 + 1];
    const pz = p < 0 ? 0 : currentJoints[p * 3 + 2];
    // Rotate about this joint's own rest position, then inherit the parent.
    // Composing down the chain is what makes it behave as one jointed body.
    localMat.makeTranslation(
      currentJoints[i * 3] - px,
      currentJoints[i * 3 + 1] - py,
      currentJoints[i * 3 + 2] - pz,
    );
    tmpMat.makeRotationFromEuler(rotations[i]);
    localMat.multiply(tmpMat);
    if (p < 0) worldMat[i].copy(localMat);
    else worldMat[i].multiplyMatrices(worldMat[p], localMat);
  }

  const pos = geometry.attributes.position.array;
  const nrm = geometry.attributes.normal.array;
  for (let i = 0; i < N; i++) {
    accP.set(0, 0, 0);
    accN.set(0, 0, 0);
    for (let k = 0; k < 4; k++) {
      const w = skinWeight[i * 4 + k];
      if (w <= 0) continue;
      const j = skinIndex[i * 4 + k];
      skinnedMat.multiplyMatrices(worldMat[j], bindInv[j]);
      vecA
        .set(restPos[i * 3], restPos[i * 3 + 1], restPos[i * 3 + 2])
        .applyMatrix4(skinnedMat);
      accP.addScaledVector(vecA, w);
      vecA
        .set(restNrm[i * 3], restNrm[i * 3 + 1], restNrm[i * 3 + 2])
        .transformDirection(worldMat[j]);
      accN.addScaledVector(vecA, w);
    }
    pos[i * 3] = accP.x;
    pos[i * 3 + 1] = accP.y;
    pos[i * 3 + 2] = accP.z;
    accN.normalize();
    nrm[i * 3] = accN.x;
    nrm[i * 3 + 1] = accN.y;
    nrm[i * 3 + 2] = accN.z;
  }
  geometry.attributes.position.needsUpdate = true;
  geometry.attributes.normal.needsUpdate = true;
  geometry.computeBoundingSphere();

  const line = boneLineGeom.attributes.position.array;
  let c = 0;
  for (let i = 0; i < JOINTS.length; i++) {
    jointWorld.set(0, 0, 0).applyMatrix4(worldMat[i]);
    jointDots[i].position.copy(jointWorld);
    if (PARENTS[i] >= 0) {
      parentWorld.set(0, 0, 0).applyMatrix4(worldMat[PARENTS[i]]);
      line[c++] = parentWorld.x;
      line[c++] = parentWorld.y;
      line[c++] = parentWorld.z;
      line[c++] = jointWorld.x;
      line[c++] = jointWorld.y;
      line[c++] = jointWorld.z;
    }
  }
  boneLineGeom.attributes.position.needsUpdate = true;
}

let target = DATA.order[1];
let blend = 1;
let posedJoint = null;

function applyBlend() {
  const to = variants[target];
  for (let i = 0; i < restPos.length; i++) {
    restPos[i] = BASE.positions[i] + (to.positions[i] - BASE.positions[i]) * blend;
    restNrm[i] = BASE.normals[i] + (to.normals[i] - BASE.normals[i]) * blend;
  }
  // The skeleton morphs with the body. Leaving it at the baseline is what made
  // the bones sit outside a taller mesh.
  for (let i = 0; i < currentJoints.length; i++) {
    currentJoints[i] = BASE.joints[i] + (to.joints[i] - BASE.joints[i]) * blend;
  }
  const counts = new Float32Array(PART_COUNT);
  partCentre.fill(0);
  for (let i = 0; i < N; i++) {
    const p = PART_OF[i];
    partCentre[p * 3] += restPos[i * 3];
    partCentre[p * 3 + 1] += restPos[i * 3 + 1];
    partCentre[p * 3 + 2] += restPos[i * 3 + 2];
    counts[p]++;
  }
  for (let p = 0; p < PART_COUNT; p++) {
    if (!counts[p]) continue;
    partCentre[p * 3] /= counts[p];
    partCentre[p * 3 + 1] /= counts[p];
    partCentre[p * 3 + 2] /= counts[p];
  }
  segmentRest();
  rebuildBind();
  updatePose();
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
    const k = ROWS[r][0];
    const a = BASE.measurements[k];
    const b = to.measurements[k];
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
    posedJoint === null
      ? Math.round(blend * 100) + "% toward " + to.label + ". Drag any joint to pose it."
      : "Posing " + JOINTS[posedJoint].replace("_", " ") + ". Joints stop where a real one would.";
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
let atLimit = false;
let lastX = 0;
let lastY = 0;

function pickJoint(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(jointDots, false)[0];
  return hit ? hit.object.userData.joint : null;
}

renderer.domElement.addEventListener("pointerdown", function (event) {
  posedJoint = pickJoint(event);
  dragging = true;
  lastX = event.clientX;
  lastY = event.clientY;
  renderer.domElement.setPointerCapture(event.pointerId);
  renderReadout();
});
renderer.domElement.addEventListener("pointerup", function (event) {
  if (posedJoint !== null) {
    jointDots[posedJoint].material.color.setHex(PARENTS[posedJoint] < 0 ? 0x9A6B3E : 0xA87844);
  }
  dragging = false;
  atLimit = false;
  posedJoint = null;
  renderer.domElement.releasePointerCapture(event.pointerId);
  renderReadout();
});
renderer.domElement.addEventListener("pointermove", function (event) {
  if (!dragging) {
    const over = pickJoint(event);
    renderer.domElement.style.cursor = over === null ? "grab" : "pointer";
    jointDots.forEach(function (dot, i) {
      dot.scale.setScalar(i === over ? 1.45 : 1);
      dot.material.emissiveIntensity = i === over ? 1.6 : 0.5;
    });
    return;
  }
  const dx = (event.clientX - lastX) * 0.012;
  const dy = (event.clientY - lastY) * 0.012;
  lastX = event.clientX;
  lastY = event.clientY;
  if (posedJoint !== null) {
    rotations[posedJoint].z -= dx;
    rotations[posedJoint].x += dy;
    atLimit = clampJoint(posedJoint);
    // A joint that has stopped should say so, not just refuse to move.
    jointDots[posedJoint].material.color.setHex(atLimit ? 0xC4553A : 0xA87844);
    updatePose();
  } else {
    orbit.theta -= dx * 0.5;
    orbit.phi -= dy * 0.5;
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
  wireMesh.visible = e.target.checked;
});
document.getElementById("bones").addEventListener("change", function (e) {
  boneLines.visible = e.target.checked;
  material.transparent = e.target.checked;
  material.opacity = e.target.checked ? 0.5 : 1;
  material.needsUpdate = true;
});
document.getElementById("spin").addEventListener("change", function (e) {
  orbit.auto = e.target.checked;
});
document.getElementById("reset").addEventListener("click", function () {
  rotations.forEach(function (r) {
    r.set(0, 0, 0);
  });
  updatePose();
});

function resize() {
  const w = stage.clientWidth || window.innerWidth;
  const h = stage.clientHeight || window.innerHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();
placeCamera();
rebuildBind();
applyBlend();

(function tick() {
  requestAnimationFrame(tick);
  if (orbit.auto) {
    orbit.theta += 0.0035;
    placeCamera();
  }
  renderer.render(scene, camera);
})();

// The canonical human, skinned on the GPU.
//
// Every earlier attempt at this blended the skin by hand and tore the mesh at
// the joints. The canonical rig carries real weights, four influences per
// vertex, so the right answer is to hand them to THREE.SkinnedMesh and let the
// library do it. Nothing here computes a vertex position.
//
// Bones are the rig's own, all 163 of them, so fingers and toes move too.

const DATA = JSON.parse(document.getElementById("canonical-data").textContent);

function bytesOf(b64) {
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}
const f32 = (b64) => new Float32Array(bytesOf(b64).buffer);
const u32 = (b64) => new Uint32Array(bytesOf(b64).buffer);
const u16 = (b64) => new Uint16Array(bytesOf(b64).buffer);

const INDICES = u32(DATA.indices);
const SKIN_INDEX = u16(DATA.skinIndex);
const SKIN_WEIGHT = f32(DATA.skinWeight);

const stage = document.getElementById("stage");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d0f12);

const camera = new THREE.PerspectiveCamera(34, 1, 0.05, 60);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputEncoding = THREE.sRGBEncoding;
stage.appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xf2f6ff, 0x1a1f28, 1.3));
const key = new THREE.DirectionalLight(0xfffaf2, 2.0);
key.position.set(2.4, 3.4, 2.6);
scene.add(key);
const rim = new THREE.DirectionalLight(0x9fb3c8, 1.2);
rim.position.set(-2.8, 1.6, -2.6);
scene.add(rim);

const grid = new THREE.GridHelper(10, 40, 0x24303f, 0x141a22);
grid.material.transparent = true;
grid.material.opacity = 0.55;
scene.add(grid);

const material = new THREE.MeshStandardMaterial({
  color: 0xe8e0d6,
  roughness: 0.85,
  metalness: 0.0,
  skinning: true,
});
const wireMaterial = new THREE.MeshBasicMaterial({
  color: 0x9fb3c8,
  wireframe: true,
  transparent: true,
  opacity: 0.3,
  skinning: true,
});

let figure = DATA.order[0];
let mesh = null;
let skeleton = null;
let bones = [];
let helper = null;
let wire = null;

function build(kind) {
  if (mesh) {
    scene.remove(mesh);
    mesh.geometry.dispose();
  }
  if (wire) scene.remove(wire);
  if (helper) scene.remove(helper);

  const entry = DATA.figures[kind];
  const table = entry.bones;

  bones = table.names.map(function (name, i) {
    const bone = new THREE.Bone();
    bone.name = name;
    bone.position.fromArray(table.local[i]);
    return bone;
  });
  bones.forEach(function (bone, i) {
    const parent = table.parents[i];
    if (parent >= 0) bones[parent].add(bone);
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(f32(entry.positions), 3));
  geometry.setAttribute("normal", new THREE.Float32BufferAttribute(f32(entry.normals), 3));
  geometry.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(SKIN_INDEX, 4));
  geometry.setAttribute("skinWeight", new THREE.Float32BufferAttribute(SKIN_WEIGHT, 4));
  geometry.setIndex(new THREE.BufferAttribute(INDICES, 1));

  mesh = new THREE.SkinnedMesh(geometry, material);
  const root = bones.find(function (_, i) {
    return table.parents[i] < 0;
  });
  mesh.add(root);
  skeleton = new THREE.Skeleton(bones);
  mesh.bind(skeleton);
  scene.add(mesh);

  wire = new THREE.SkinnedMesh(geometry, wireMaterial);
  wire.add(root.clone());
  wire.bind(skeleton);
  wire.visible = false;
  scene.add(wire);

  helper = new THREE.SkeletonHelper(mesh);
  helper.material.linewidth = 1;
  helper.visible = false;
  scene.add(helper);

  figure = kind;
  readout();
}

// Picking a bone from a click on the skin.
//
// There is no handle per bone: 163 dots would bury the figure. The ray hits the
// surface, and the bone that owns that point is the one with the largest weight
// on the nearest vertex, which is what the skinning itself uses.
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let held = null;
let last = { x: 0, y: 0 };

function boneAt(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObject(mesh, false)[0];
  if (!hit) return null;

  const face = hit.face;
  let best = -1;
  let bestWeight = -1;
  for (const vertex of [face.a, face.b, face.c]) {
    for (let k = 0; k < 4; k++) {
      const weight = SKIN_WEIGHT[vertex * 4 + k];
      if (weight > bestWeight) {
        bestWeight = weight;
        best = SKIN_INDEX[vertex * 4 + k];
      }
    }
  }
  return best >= 0 ? bones[best] : null;
}

renderer.domElement.addEventListener("pointerdown", function (event) {
  held = boneAt(event);
  last = { x: event.clientX, y: event.clientY };
  renderer.domElement.setPointerCapture(event.pointerId);
  readout();
});
renderer.domElement.addEventListener("pointerup", function (event) {
  held = null;
  renderer.domElement.releasePointerCapture(event.pointerId);
});
renderer.domElement.addEventListener("pointermove", function (event) {
  const dx = (event.clientX - last.x) * 0.01;
  const dy = (event.clientY - last.y) * 0.01;
  last = { x: event.clientX, y: event.clientY };
  if (held) {
    held.rotation.z -= dx;
    held.rotation.x += dy;
    readout();
  } else if (event.buttons) {
    orbit.theta -= dx * 0.6;
    orbit.phi -= dy * 0.6;
    place();
  } else {
    renderer.domElement.style.cursor = "grab";
  }
});

const orbit = { target: new THREE.Vector3(0, 0.9, 0), radius: 3.4, theta: 0.4, phi: 1.28 };
function place() {
  orbit.phi = Math.max(0.18, Math.min(Math.PI - 0.18, orbit.phi));
  orbit.radius = Math.max(0.6, Math.min(9, orbit.radius));
  camera.position.set(
    orbit.target.x + orbit.radius * Math.sin(orbit.phi) * Math.sin(orbit.theta),
    orbit.target.y + orbit.radius * Math.cos(orbit.phi),
    orbit.target.z + orbit.radius * Math.sin(orbit.phi) * Math.cos(orbit.theta),
  );
  camera.lookAt(orbit.target);
}
renderer.domElement.addEventListener(
  "wheel",
  function (event) {
    event.preventDefault();
    orbit.radius *= event.deltaY > 0 ? 1.08 : 0.93;
    place();
  },
  { passive: false },
);

function readout() {
  const m = DATA.figures[figure].measurements;
  document.getElementById("rows").innerHTML = [
    ["Height", m.height_cm],
    ["Chest", m.chest_girth_cm],
    ["Waist", m.waist_girth_cm],
    ["Hip", m.hip_girth_cm],
    ["Shoulders", m.shoulder_width_cm],
  ]
    .map(function (row) {
      return `<dt>${row[0]}</dt><dd>${row[1].toFixed(1)}<u>cm</u></dd>`;
    })
    .join("");
  document.getElementById("joint").textContent = held
    ? `${held.name} — drag to rotate`
    : "click the body to pick the bone under the pointer";
  document.getElementById("stat").textContent =
    `${DATA.vertexCount.toLocaleString()} vertices · ${DATA.triangleCount.toLocaleString()} triangles · ` +
    `${DATA.figures[figure].bones.names.length} bones · skinned on GPU`;
}

function resetPose() {
  bones.forEach(function (bone) {
    bone.rotation.set(0, 0, 0);
  });
  readout();
}

function resize() {
  const w = stage.clientWidth || window.innerWidth;
  const h = stage.clientHeight || window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);

function start() {
  const figures = document.getElementById("figures");
  DATA.order.forEach(function (kind) {
    const button = document.createElement("button");
    button.className = "pick";
    button.type = "button";
    button.textContent = DATA.figures[kind].label;
    button.setAttribute("aria-pressed", String(kind === figure));
    button.addEventListener("click", function () {
      build(kind);
      for (const other of figures.children) {
        other.setAttribute("aria-pressed", String(other === button));
      }
    });
    figures.appendChild(button);
  });

  document.getElementById("wire").addEventListener("change", function (e) {
    wire.visible = e.target.checked;
  });
  document.getElementById("bones").addEventListener("change", function (e) {
    helper.visible = e.target.checked;
  });
  document.getElementById("reset").addEventListener("click", resetPose);

  build(DATA.order[0]);
  resize();
  place();
  (function tick() {
    requestAnimationFrame(tick);
    renderer.render(scene, camera);
  })();
}

start();

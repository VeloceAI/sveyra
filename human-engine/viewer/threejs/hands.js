// Hands, because the engine does not model them.
//
// Nothing in the body pipeline measures a hand: the mesh ends at the wrist and
// the rig carries a hand bone with no geometry on it, so the arm finished in a
// ball. mannequin.js builds a palm and five jointed fingers from its own shape
// functions; this builds the same arrangement at a size taken from the wrist,
// which is the only hand dimension the body actually gives us.
//
// So these are proportion, not measurement, and the panel says as much. They
// exist so the figure reads as a mannequin rather than an amputee.

// Fractions of wrist radius. A palm is about three wrist-radii long and a
// little wider than it is thick; fingers taper to roughly half their base.
const HAND = {
  palmLength: 2.6,
  palmWidth: 2.0,
  palmThickness: 0.85,
  fingerLength: [2.0, 2.3, 2.2, 1.8],
  fingerRadius: 0.34,
  thumbLength: 1.6,
  thumbRadius: 0.42,
};

function taperedFinger(radius, length, tip) {
  const geo = new THREE.CylinderGeometry(radius * tip, radius, length, 10, 1, false);
  geo.translate(0, length / 2, 0);
  return geo;
}

// `down` is the direction the hand hangs from the wrist, in bone-local space;
// `side` separates the fingers across the palm.
function buildHand(wristRadius, down, side, material) {
  const group = new THREE.Group();
  const r = wristRadius;

  const palm = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), material);
  palm.scale.set(HAND.palmWidth, HAND.palmLength / 2, HAND.palmThickness);
  palm.position.copy(down).multiplyScalar(r * HAND.palmLength * 0.5);
  palm.castShadow = true;
  group.add(palm);

  const spread = HAND.palmWidth * r * 0.55;
  HAND.fingerLength.forEach(function (length, i) {
    const finger = new THREE.Mesh(
      taperedFinger(r * HAND.fingerRadius, r * length, 0.62),
      material,
    );
    // Built along +Y, so it has to be turned to follow the hand's own direction.
    finger.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), down);
    finger.position
      .copy(down)
      .multiplyScalar(r * HAND.palmLength * 0.95)
      .addScaledVector(side, spread * (i / 1.5 - 1));
    finger.castShadow = true;
    group.add(finger);
  });

  const thumb = new THREE.Mesh(
    taperedFinger(r * HAND.thumbRadius, r * HAND.thumbLength, 0.7),
    material,
  );
  const thumbDir = down.clone().addScaledVector(side, 0.9).normalize();
  thumb.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), thumbDir);
  thumb.position
    .copy(down)
    .multiplyScalar(r * HAND.palmLength * 0.35)
    .addScaledVector(side, spread * 1.15);
  thumb.castShadow = true;
  group.add(thumb);

  return group;
}

// Postures, in degrees, in the same anatomical terms mannequin.js uses.
//
// Its figure never stands in a T-pose; its rest already has the arms down and
// its default posture adds a small raise, straddle and elbow bend on top. Ours
// rests in a T-pose because that is what the mesh is built in, so every posture
// here is written from anatomical neutral and the neutral offset carried by the
// joint limits puts the arms at the sides.
//
// Values for STANDING are mannequin.js's own defaults. The rest are built from
// the same vocabulary rather than copied, since its walk and run live in an
// animation loop rather than in a table.

const POSTURES = {
  standing: {
    label: "Standing",
    joints: {
      chest: { bend: 2 },
      upperarm_L: { flex: -5, abduct: 10 },
      upperarm_R: { flex: -5, abduct: 10 },
      forearm_L: { flex: -15 },
      forearm_R: { flex: -15 },
    },
  },
  walking: {
    label: "Walking",
    joints: {
      thigh_L: { flex: -25 },
      calf_L: { flex: 15 },
      foot_L: { flex: 10 },
      thigh_R: { flex: 20 },
      calf_R: { flex: 35 },
      foot_R: { flex: -15 },
      upperarm_L: { flex: 25, abduct: 6 },
      upperarm_R: { flex: -25, abduct: 6 },
      forearm_L: { flex: -30 },
      forearm_R: { flex: -20 },
      chest: { bend: 3 },
    },
  },
  running: {
    label: "Running",
    joints: {
      pelvis: { bend: 10 },
      chest: { bend: 12 },
      thigh_L: { flex: -55 },
      calf_L: { flex: 75 },
      foot_L: { flex: 15 },
      thigh_R: { flex: 22 },
      calf_R: { flex: 100 },
      foot_R: { flex: -20 },
      upperarm_L: { flex: 55, abduct: 12 },
      upperarm_R: { flex: -45, abduct: 12 },
      forearm_L: { flex: -85 },
      forearm_R: { flex: -75 },
    },
  },
  sitting: {
    label: "Sitting",
    joints: {
      thigh_L: { flex: -85, abduct: 8 },
      thigh_R: { flex: -85, abduct: 8 },
      calf_L: { flex: 85 },
      calf_R: { flex: 85 },
      foot_L: { flex: -5 },
      foot_R: { flex: -5 },
      upperarm_L: { flex: -10, abduct: 5 },
      upperarm_R: { flex: -10, abduct: 5 },
      forearm_L: { flex: -35 },
      forearm_R: { flex: -35 },
      chest: { bend: 5 },
    },
  },
  waving: {
    label: "Waving",
    joints: {
      upperarm_L: { abduct: 115, flex: 10 },
      forearm_L: { flex: -55 },
      upperarm_R: { flex: -5, abduct: 7 },
      forearm_R: { flex: -15 },
      neck: { bend: -5 },
      chest: { bend: 2 },
    },
  },
  contrapposto: {
    label: "Contrapposto",
    joints: {
      pelvis: { abduct: 6 },
      chest: { bend: 3, abduct: -5 },
      thigh_L: { flex: -6, abduct: 4 },
      thigh_R: { flex: 12, abduct: -10 },
      calf_R: { flex: 18 },
      foot_R: { flex: -12 },
      upperarm_L: { flex: -8, abduct: 9 },
      upperarm_R: { flex: -3, abduct: 6 },
      forearm_L: { flex: -22 },
      forearm_R: { flex: -12 },
      neck: { turn: 12 },
    },
  },
};

// A posture names bends and straddles; a bone wants x, y and z. Which component
// carries which is per joint, and the limits already record it.
function postureToRotations(posture, limits) {
  const out = {};
  Object.keys(posture.joints).forEach(function (joint) {
    const limit = limits[joint];
    if (!limit) return;
    const named = posture.joints[joint];
    const rotation = (limit.neutral || [0, 0, 0]).slice();
    const axes = { flex: 0, abduct: 1, twist: 2 };
    // Straddle and turn are mirrored on the right, the way mannequin.js mirrors
    // them by leftOrRight. A bend is not: both elbows bend the same way, but
    // both arms straddling "outward" means opposite signs.
    const mirror = joint.endsWith("_R") ? -1 : 1;
    Object.keys(named).forEach(function (term) {
      // "bend" and "turn" are mannequin.js's words for a torso's flex and twist.
      const which = term === "bend" ? "flex" : term === "turn" ? "twist" : term;
      if (!(which in axes)) return;
      const sign = which === "flex" ? 1 : mirror;
      const component = limit.axisOf[axes[which]];
      rotation[component] += (sign * named[term] * Math.PI) / 180;
    });
    out[joint] = rotation;
  });
  return out;
}

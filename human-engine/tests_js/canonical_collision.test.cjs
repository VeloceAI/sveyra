const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const THREE = require('three');

const VIEWER = path.resolve(__dirname, '../viewer/threejs');
const DATA = JSON.parse(fs.readFileSync(path.join(VIEWER, 'canonical_data.json'), 'utf8'));

function viewerApi() {
  const context = vm.createContext({ THREE });
  const sources = [
    fs.readFileSync(path.join(VIEWER, 'poses.js'), 'utf8'),
    fs.readFileSync(path.join(VIEWER, 'constraints.js'), 'utf8'),
    [
      'globalThis.viewerApi = {',
      '  POSES, BodyBoundary, poseTargets, leadFor, modelHead, resolve, worldEnds',
      '};',
    ].join('\n'),
  ].join('\n');
  vm.runInContext(sources, context);
  return context.viewerApi;
}

const api = viewerApi();

function buildFigure(kind) {
  const entry = DATA.figures[kind];
  const table = entry.bones;
  const bones = table.names.map((name, index) => {
    const bone = new THREE.Bone();
    bone.name = name;
    bone.position.fromArray(table.local[index]);
    return bone;
  });
  bones.forEach((bone, index) => {
    const parent = table.parents[index];
    if (parent >= 0) bones[parent].add(bone);
  });
  const root = bones.find((_bone, index) => table.parents[index] < 0);
  const byName = new Map(table.names.map((name, index) => [name, index]));
  const rest = bones.map((bone) => bone.quaternion.clone());
  const boundary = new api.BodyBoundary(entry.volumes, byName, bones, table.restHead);
  root.updateMatrixWorld(true);
  boundary.calibrate();
  return { entry, table, bones, root, byName, rest, boundary };
}

function targetsFor(figure, key) {
  const targets = api.poseTargets(
    api.POSES[key],
    figure.bones,
    figure.byName,
    figure.table.direction,
  );
  return figure.bones.map((bone, index) => {
    const wanted = targets.get(bone);
    return wanted
      ? figure.rest[index].clone().multiply(wanted)
      : figure.rest[index].clone();
  });
}

function applyShare(figure, from, to, share) {
  figure.bones.forEach((bone, index) => {
    bone.quaternion.slerpQuaternions(from[index], to[index], share);
  });
  figure.root.updateMatrixWorld(true);
}

function joint(figure, name) {
  return api.modelHead(figure.bones[figure.byName.get(name)]);
}

function elbowFlexion(figure, suffix) {
  const shoulder = joint(figure, 'upperarm01.' + suffix);
  const elbow = joint(figure, 'lowerarm01.' + suffix);
  const wrist = joint(figure, 'wrist.' + suffix);
  return (
    elbow
      .clone()
      .sub(shoulder)
      .angleTo(wrist.clone().sub(elbow)) *
    (180 / Math.PI)
  );
}

function assertMirrored(left, right, tolerance, label) {
  assert.ok(Math.abs(left.x + right.x) < tolerance, label + ' x');
  assert.ok(Math.abs(left.y - right.y) < tolerance, label + ' y');
  assert.ok(Math.abs(left.z - right.z) < tolerance, label + ' z');
}

test('exported capsules land on the actual bind-pose bones', () => {
  const figure = buildFigure('man');
  const hand = figure.boundary.limbs.find((entry) => entry.name === 'wrist.L');
  const raw = figure.entry.volumes.limb.find((entry) => entry.bone === 'wrist.L');
  const head = new THREE.Vector3();
  const tail = new THREE.Vector3();
  api.worldEnds(hand, head, tail);

  const expected = new THREE.Vector3()
    .fromArray(figure.table.restHead[figure.byName.get('wrist.L')])
    .add(new THREE.Vector3().fromArray(raw.head).multiplyScalar(0.01));
  assert.ok(
    head.distanceTo(expected) < 1e-5,
    JSON.stringify({ actual: head.toArray(), expected: expected.toArray() }),
  );
});

test('reach-up stays outside every fitted body during the whole transition', () => {
  for (const kind of DATA.order) {
    const figure = buildFigure(kind);
    const from = figure.rest.map((rotation) => rotation.clone());
    const to = targetsFor(figure, 'reachUp');
    applyShare(figure, from, to, 1);
    const destinationIntrusion = figure.boundary.intrusion();
    assert.equal(
      figure.boundary.clear(),
      true,
      kind + ' authored reach-up destination intersects: ' +
        JSON.stringify(destinationIntrusion),
    );
    applyShare(figure, from, to, 0);
    let safe = from.map((rotation) => rotation.clone());

    for (let frame = 0; frame <= 60; frame++) {
      const t = frame / 60;
      figure.bones.forEach((bone, index) => {
        const lead = api.leadFor(bone.name);
        const own = Math.max(0, Math.min(1, (t - lead) / (1 - lead)));
        const eased = own * own * (3 - 2 * own);
        bone.quaternion.slerpQuaternions(from[index], to[index], eased);
      });
      figure.root.updateMatrixWorld(true);

      if (!figure.boundary.clear()) {
        const candidate = figure.bones.map((bone) => bone.quaternion.clone());
        api.resolve(figure.boundary, figure.bones, safe, candidate, (share) => {
          applyShare(figure, safe, candidate, share);
        });
      }
      assert.equal(
        figure.boundary.clear(),
        true,
        kind + ' penetrated at animation frame ' + frame,
      );
      safe = figure.bones.map((bone) => bone.quaternion.clone());
    }
  }
});

test('IK reach-up places both hands overhead with stable human elbow geometry', () => {
  for (const kind of DATA.order) {
    const figure = buildFigure(kind);
    applyShare(figure, figure.rest, targetsFor(figure, 'reachUp'), 1);

    const leftShoulder = joint(figure, 'upperarm01.L');
    const rightShoulder = joint(figure, 'upperarm01.R');
    const leftElbow = joint(figure, 'lowerarm01.L');
    const rightElbow = joint(figure, 'lowerarm01.R');
    const leftWrist = joint(figure, 'wrist.L');
    const rightWrist = joint(figure, 'wrist.R');
    const scale = figure.entry.measurements.height_cm / 100;

    assert.ok(leftWrist.y > scale, kind + ' left hand is not overhead');
    assert.ok(rightWrist.y > scale, kind + ' right hand is not overhead');
    assert.ok(leftElbow.y < leftWrist.y, kind + ' left elbow passed the wrist');
    assert.ok(rightElbow.y < rightWrist.y, kind + ' right elbow passed the wrist');
    assert.ok(leftElbow.x > leftShoulder.x, kind + ' left elbow folded inward');
    assert.ok(rightElbow.x < rightShoulder.x, kind + ' right elbow folded inward');
    assert.ok(elbowFlexion(figure, 'L') > 20 && elbowFlexion(figure, 'L') < 45);
    assert.ok(elbowFlexion(figure, 'R') > 20 && elbowFlexion(figure, 'R') < 45);
    assertMirrored(leftElbow, rightElbow, scale * 0.012, kind + ' reach elbows');
    assertMirrored(leftWrist, rightWrist, scale * 0.012, kind + ' reach wrists');
  }
});

test('IK arms-crossed pose crosses the wrists but keeps elbows on their own sides', () => {
  for (const kind of DATA.order) {
    const figure = buildFigure(kind);
    applyShare(figure, figure.rest, targetsFor(figure, 'armsCrossed'), 1);

    const leftElbow = joint(figure, 'lowerarm01.L');
    const rightElbow = joint(figure, 'lowerarm01.R');
    const leftWrist = joint(figure, 'wrist.L');
    const rightWrist = joint(figure, 'wrist.R');
    const scale = figure.entry.measurements.height_cm / 100;

    assert.ok(leftWrist.x < 0, kind + ' left wrist did not cross the centre line');
    assert.ok(rightWrist.x > 0, kind + ' right wrist did not cross the centre line');
    assert.ok(leftElbow.x > 0, kind + ' left elbow crossed into the torso');
    assert.ok(rightElbow.x < 0, kind + ' right elbow crossed into the torso');
    assert.ok(leftWrist.z > scale * 0.12, kind + ' left wrist is not in front of chest');
    assert.ok(rightWrist.z > scale * 0.12, kind + ' right wrist is not in front of chest');
    assert.ok(elbowFlexion(figure, 'L') > 60 && elbowFlexion(figure, 'L') < 130);
    assert.ok(elbowFlexion(figure, 'R') > 60 && elbowFlexion(figure, 'R') < 130);
    assert.ok(
      Math.hypot(leftWrist.y - rightWrist.y, leftWrist.z - rightWrist.z) > scale * 0.035,
      kind + ' crossed wrists were placed on the same depth plane',
    );
    assert.equal(
      figure.boundary.clear(),
      true,
      kind +
        ' crossed arms penetrate: ' +
        JSON.stringify({
          intrusion: figure.boundary.intrusion(),
          shoulders: [joint(figure, 'upperarm01.L'), joint(figure, 'upperarm01.R')],
          elbows: [leftElbow, rightElbow],
          wrists: [leftWrist, rightWrist],
        }),
    );
  }
});

test('the complete arm chain shares one transition phase', () => {
  for (const suffix of ['L', 'R']) {
    const names = [
      'clavicle.' + suffix,
      'shoulder01.' + suffix,
      'upperarm01.' + suffix,
      'upperarm02.' + suffix,
      'lowerarm01.' + suffix,
      'lowerarm02.' + suffix,
      'wrist.' + suffix,
    ];
    const phases = names.map(api.leadFor);
    assert.equal(new Set(phases).size, 1, suffix + ' phases: ' + phases.join(', '));
  }
});

test('reach-to-cross motion stays coordinated, bounded, and collision-free', () => {
  for (const kind of DATA.order) {
    const figure = buildFigure(kind);
    const from = targetsFor(figure, 'reachUp');
    const to = targetsFor(figure, 'armsCrossed');
    applyShare(figure, figure.rest, from, 1);
    let safe = figure.bones.map((bone) => bone.quaternion.clone());
    let previousLeftWrist = joint(figure, 'wrist.L');
    let previousRightWrist = joint(figure, 'wrist.R');
    const scale = figure.entry.measurements.height_cm / 100;

    for (let frame = 0; frame <= 60; frame++) {
      const t = frame / 60;
      figure.bones.forEach((bone, index) => {
        const lead = api.leadFor(bone.name);
        const own = Math.max(0, Math.min(1, (t - lead) / (1 - lead)));
        const eased = own * own * (3 - 2 * own);
        bone.quaternion.slerpQuaternions(from[index], to[index], eased);
      });
      figure.root.updateMatrixWorld(true);

      if (!figure.boundary.clear()) {
        const candidate = figure.bones.map((bone) => bone.quaternion.clone());
        api.resolve(figure.boundary, figure.bones, safe, candidate, (share) => {
          applyShare(figure, safe, candidate, share);
        });
      }

      const leftElbow = joint(figure, 'lowerarm01.L');
      const rightElbow = joint(figure, 'lowerarm01.R');
      const leftWrist = joint(figure, 'wrist.L');
      const rightWrist = joint(figure, 'wrist.R');
      const leftFlexion = elbowFlexion(figure, 'L');
      const rightFlexion = elbowFlexion(figure, 'R');

      assert.equal(figure.boundary.clear(), true, kind + ' collision at frame ' + frame);
      assert.ok(leftFlexion >= 0 && leftFlexion <= 150, kind + ' left elbow at ' + leftFlexion);
      assert.ok(rightFlexion >= 0 && rightFlexion <= 150, kind + ' right elbow at ' + rightFlexion);
      assert.ok(leftElbow.x > 0, kind + ' left elbow crossed the torso at frame ' + frame);
      assert.ok(rightElbow.x < 0, kind + ' right elbow crossed the torso at frame ' + frame);
      assert.ok(
        leftWrist.distanceTo(previousLeftWrist) < scale * 0.06,
        kind + ' wrist jumped at frame ' + frame,
      );
      assert.ok(
        rightWrist.distanceTo(previousRightWrist) < scale * 0.06,
        kind + ' right wrist jumped at frame ' + frame,
      );
      previousLeftWrist = leftWrist;
      previousRightWrist = rightWrist;
      safe = figure.bones.map((bone) => bone.quaternion.clone());
    }
  }
});

test('a hand placed in the chest is detected', () => {
  const figure = buildFigure('man');
  const hand = figure.boundary.limbs.find((entry) => entry.name === 'wrist.L');
  const chest = figure.boundary.trunk.find((entry) => entry.name === 'spine02');
  const chestHead = new THREE.Vector3();
  const chestTail = new THREE.Vector3();
  const handHead = new THREE.Vector3();
  const handTail = new THREE.Vector3();
  api.worldEnds(chest, chestHead, chestTail);
  api.worldEnds(hand, handHead, handTail);

  const desired = chestHead.clone().lerp(chestTail, 0.5);
  const shift = desired.sub(handHead);
  hand.bone.position.add(shift);
  figure.root.updateMatrixWorld(true);

  const intrusion = figure.boundary.intrusion();
  assert.ok(intrusion.depth > 1, intrusion.where);
  assert.match(intrusion.where, /wrist\.L/);
});

test('every authored pose resolves to a collision-free usable pose', () => {
  for (const kind of DATA.order) {
    for (const key of Object.keys(api.POSES)) {
      const figure = buildFigure(kind);
      const from = figure.rest.map((rotation) => rotation.clone());
      const to = targetsFor(figure, key);
      applyShare(figure, from, to, 1);
      const requestedIntrusion = figure.boundary.intrusion();
      applyShare(figure, from, to, 0);
      const share = api.resolve(
        figure.boundary,
        figure.bones,
        from,
        to,
        (amount) => applyShare(figure, from, to, amount),
      );
      assert.equal(figure.boundary.clear(), true, kind + ' ' + key);
      assert.ok(
        share >= 0.3,
        kind + ' ' + key + ' was reduced to ' + share + ': ' +
          JSON.stringify(requestedIntrusion),
      );
    }
  }
});

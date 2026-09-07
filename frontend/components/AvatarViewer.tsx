"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Props = {
  url: string | null;
  height?: number;
  rigged?: boolean;
  studio?: boolean;
};

type MotionBones = {
  left: THREE.Object3D;
  right: THREE.Object3D;
  leftRest: THREE.Quaternion;
  rightRest: THREE.Quaternion;
};

/** Renders a GLB avatar with orbit, rig inspection, and a small skinning test. */
export default function AvatarViewer({ url, height = 520, rigged = false, studio = false }: Props) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const skeletonRef = useRef<THREE.SkeletonHelper | null>(null);
  const motionBonesRef = useRef<MotionBones | null>(null);
  const motionEnabledRef = useRef(false);
  const materialsRef = useRef<THREE.Material[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  const [motionEnabled, setMotionEnabled] = useState(false);
  const [wireframe, setWireframe] = useState(false);

  function toggleSkeleton() {
    const visible = !showSkeleton;
    setShowSkeleton(visible);
    if (skeletonRef.current) skeletonRef.current.visible = visible;
  }

  function toggleMotion() {
    const enabled = !motionEnabledRef.current;
    motionEnabledRef.current = enabled;
    setMotionEnabled(enabled);
    if (!enabled && motionBonesRef.current) {
      motionBonesRef.current.left.quaternion.copy(motionBonesRef.current.leftRest);
      motionBonesRef.current.right.quaternion.copy(motionBonesRef.current.rightRest);
    }
  }

  function toggleWireframe() {
    const enabled = !wireframe;
    setWireframe(enabled);
    for (const material of materialsRef.current) {
      if ("wireframe" in material) {
        (material as THREE.MeshStandardMaterial).wireframe = enabled;
        material.needsUpdate = true;
      }
    }
  }

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !url) return;

    setError(null);
    setLoading(true);
    setShowSkeleton(false);
    setMotionEnabled(false);
    setWireframe(false);
    motionEnabledRef.current = false;
    materialsRef.current = [];

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x14161c);

    const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.HemisphereLight(0xdfe6ff, 0x1a1d25, 2.0));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(2, 3, 2.5);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x93a8ff, 0.7);
    fill.position.set(-2.5, 1, -2);
    scene.add(fill);
    scene.add(new THREE.GridHelper(4, 20, 0x3a4152, 0x272c38));

    let disposed = false;
    let frame = 0;

    new GLTFLoader().load(
      url,
      (gltf) => {
        if (disposed) return;
        scene.add(gltf.scene);
        gltf.scene.traverse((child) => {
          if (!(child as THREE.Mesh).isMesh) return;
          const material = (child as THREE.Mesh).material;
          materialsRef.current.push(...(Array.isArray(material) ? material : [material]));
        });

        const leftArm = gltf.scene.getObjectByName("upperarm01.L");
        const rightArm = gltf.scene.getObjectByName("upperarm01.R");
        if (leftArm && rightArm) {
          motionBonesRef.current = {
            left: leftArm,
            right: rightArm,
            leftRest: leftArm.quaternion.clone(),
            rightRest: rightArm.quaternion.clone(),
          };
          const helper = new THREE.SkeletonHelper(gltf.scene);
          helper.visible = false;
          skeletonRef.current = helper;
          scene.add(helper);
        }

        const box = new THREE.Box3().setFromObject(gltf.scene);
        const size = box.getSize(new THREE.Vector3());
        const centre = box.getCenter(new THREE.Vector3());
        const radius = Math.max(size.x, size.y, size.z);
        controls.target.copy(centre);
        camera.position.set(
          centre.x + radius * 0.6,
          centre.y + radius * 0.1,
          centre.z + radius * 1.9,
        );
        camera.near = radius / 100;
        camera.far = radius * 100;
        camera.updateProjectionMatrix();
        controls.update();
        setLoading(false);
      },
      undefined,
      () => {
        if (!disposed) {
          setError("The avatar could not be loaded.");
          setLoading(false);
        }
      },
    );

    function resize() {
      const width = mount!.clientWidth || 480;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    resize();
    window.addEventListener("resize", resize);

    const motionAxis = new THREE.Vector3(0, 0, 1);
    const leftMotion = new THREE.Quaternion();
    const rightMotion = new THREE.Quaternion();
    function tick() {
      frame = requestAnimationFrame(tick);
      const motionBones = motionBonesRef.current;
      if (motionEnabledRef.current && motionBones) {
        const angle = Math.sin(performance.now() / 550) * 0.32;
        leftMotion.setFromAxisAngle(motionAxis, angle);
        rightMotion.setFromAxisAngle(motionAxis, -angle);
        motionBones.left.quaternion.copy(motionBones.leftRest).multiply(leftMotion);
        motionBones.right.quaternion.copy(motionBones.rightRest).multiply(rightMotion);
      }
      controls.update();
      renderer.render(scene, camera);
    }
    tick();

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      controls.dispose();
      renderer.dispose();
      motionBonesRef.current = null;
      materialsRef.current = [];
      if (skeletonRef.current) {
        skeletonRef.current.geometry.dispose();
        const skeletonMaterial = skeletonRef.current.material;
        if (Array.isArray(skeletonMaterial)) {
          skeletonMaterial.forEach((item) => item.dispose());
        } else {
          skeletonMaterial.dispose();
        }
        skeletonRef.current = null;
      }
      scene.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          mesh.geometry.dispose();
          const material = mesh.material;
          if (Array.isArray(material)) material.forEach((item) => item.dispose());
          else material.dispose();
        }
      });
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [url, height]);

  if (!url) {
    return (
      <div className="viewer-placeholder" style={{ height }}>
        {studio ? "Generate a human to inspect its surface and skeleton." : "Your avatar will appear here."}
      </div>
    );
  }

  return (
    <div>
      <div ref={mountRef} className="viewer" style={{ minHeight: height }} />
      {rigged && !loading && !error && (
        <div className="viewer-toolbar">
          <button type="button" className="secondary" onClick={toggleSkeleton}>
            {showSkeleton ? "Hide skeleton" : "Show 163-joint skeleton"}
          </button>
          <button type="button" className="secondary" onClick={toggleMotion}>
            {motionEnabled ? "Stop motion test" : "Test arm motion"}
          </button>
          {studio && (
            <button type="button" className="secondary" onClick={toggleWireframe}>
              {wireframe ? "Show surface" : "Show wireframe"}
            </button>
          )}
        </div>
      )}
      {loading && <p className="muted">Loading the avatar…</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

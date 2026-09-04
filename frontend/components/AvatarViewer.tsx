"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Props = {
  url: string | null;
  height?: number;
};

/** Renders a GLB avatar with orbit controls. */
export default function AvatarViewer({ url, height = 520 }: Props) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !url) return;

    setError(null);
    setLoading(true);

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

        const box = new THREE.Box3().setFromObject(gltf.scene);
        const size = box.getSize(new THREE.Vector3());
        const centre = box.getCenter(new THREE.Vector3());
        const radius = Math.max(size.x, size.y, size.z);
        controls.target.copy(centre);
        camera.position.set(centre.x + radius * 0.6, centre.y + radius * 0.1, centre.z + radius * 1.9);
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

    function tick() {
      frame = requestAnimationFrame(tick);
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
      scene.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          mesh.geometry.dispose();
          const material = mesh.material;
          if (Array.isArray(material)) material.forEach((m) => m.dispose());
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
        Your avatar will appear here.
      </div>
    );
  }

  return (
    <div>
      <div ref={mountRef} className="viewer" style={{ minHeight: height }} />
      {loading && <p className="muted">Loading the avatar…</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

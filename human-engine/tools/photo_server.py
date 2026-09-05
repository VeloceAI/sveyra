"""Serve the viewer and reconstruct a body from an uploaded photograph.

A development server, not a product surface: it exists so the photo path can be
driven by hand and watched. The backend already owns the real endpoint.

Run it from the repository root:

    python human-engine/tools/photo_server.py --port 8810

Segmentation needs a MediaPipe model. Without one the server still serves the
viewer and says plainly that reconstruction is unavailable, rather than
answering uploads with a body nothing looked at.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import pathlib
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from sveyra_human.api.engine import SveyraHumanEngine  # noqa: E402
from sveyra_human.body.parameters import BodyParameters  # noqa: E402
from sveyra_human.vision.silhouette import silhouette_from_segmentation  # noqa: E402
from sveyra_human.vision.torso_extraction import extract as extract_torso  # noqa: E402

VIEWER = ROOT / "viewer" / "threejs"
SAMPLES = ROOT / "viewer" / "threejs" / "samples"


def build_pose(pose_model: str | None):
    if not pose_model:
        return None, "no pose model given (--pose-model)"
    try:
        from sveyra_human.vision.mediapipe_tasks import MediaPipeTasksPose

        return MediaPipeTasksPose(pose_model), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def build_engine(segmentation_model: str | None):
    if not segmentation_model:
        return None, "no segmentation model given (--segmentation-model)"
    try:
        from sveyra_human.vision.mediapipe_tasks import MediaPipeTasksSegmenter

        segmenter = MediaPipeTasksSegmenter(segmentation_model)
        return SveyraHumanEngine("balanced", segmenter=segmenter), None
    except Exception as exc:  # noqa: BLE001 - reported to the caller verbatim
        return None, f"{type(exc).__name__}: {exc}"


class Handler(SimpleHTTPRequestHandler):
    engine = None
    engine_error = "not initialised"
    pose = None
    pose_error = "not initialised"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(VIEWER), **kwargs)

    def log_message(self, fmt, *args):
        if "reconstruct" in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path != "/reconstruct":
            self._json(404, {"error": "unknown endpoint"})
            return
        if Handler.engine is None:
            self._json(503, {"error": f"reconstruction unavailable: {Handler.engine_error}"})
            return

        try:
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"] or 0)))
            raw = base64.b64decode(payload["image"].split(",")[-1])
            height_cm = float(payload.get("height_cm", 175.0))
            image = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
        except Exception as exc:  # noqa: BLE001
            self._json(400, {"error": f"could not read the upload: {exc}"})
            return

        try:
            self._json(
                200, reconstruct(Handler.engine, Handler.pose, image, height_cm)
            )
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._json(422, {"error": f"{type(exc).__name__}: {exc}"})


def reconstruct(engine, pose, image: np.ndarray, height_cm: float) -> dict:
    """Photograph to a body, reporting what the fit could and could not see."""
    mask = np.squeeze(silhouette_from_segmentation(engine._segmenter.segment(image)))

    landmarks = None
    torso = None
    found = pose.detect(image) if pose is not None else None
    if found is not None:
        landmarks = {
            "points": [[round(float(v), 5) for v in p] for p in found.points],
            "visibility": [round(float(v), 4) for v in found.visibility],
        }
        # Landmarks in image pixels, which is the frame the mask is measured in.
        rows, cols = mask.shape[0], mask.shape[1]
        image_points = np.array(
            [[p[0] * cols, p[1] * rows] for p in found.image_points], dtype=float
        )
        torso = extract_torso(mask, image_points, found.visibility, height_cm)

    # Widths read straight off the silhouette beat the band-profile optimiser
    # here: it takes the widest row per band, which on a standing photograph runs
    # through both arms, so every body came back the same width. Measured widths
    # are used when the arms were clear of the body at all three levels.
    if torso is not None and torso.usable:
        cm = torso.centimetres()
        artifact = engine.build_parametric(
            BodyParameters(
                height=height_cm,
                chest_width=cm["chest"],
                waist_width=cm["waist"],
                hip_width=cm["hip"],
            ),
            with_uv=True,
        )
        source = "measured widths"
    else:
        artifact = engine.build(front=image, height_cm=height_cm)
        source = "silhouette optimiser"
    mesh = artifact._mesh

    verts = (mesh.vertices * 0.01).astype(np.float32)
    verts[:, 0] -= float(verts[:, 0].mean())
    verts[:, 2] -= float(verts[:, 2].mean())

    return {
        "label": f"Photo {height_cm:.0f} cm",
        "landmarks": landmarks,
        "pose_error": None
        if landmarks
        else (Handler.pose_error if pose is None else "no person found"),
        "positions": base64.b64encode(verts.tobytes()).decode(),
        "normals": base64.b64encode(mesh.normals().astype(np.float32).tobytes()).decode(),
        "measurements": {k: round(float(v), 1) for k, v in artifact.measurements.items()},
        "coverage": round(float(mask.mean()), 4),
        # Said out loud rather than left for someone to discover: the fit solves
        # six torso numbers, so anything else in this body is proportion, not
        # measurement, and arms held against the body are read as torso.
        "fitted": ["chest", "waist", "hip"],
        "source": source,
        "torso_cm": torso.centimetres() if torso is not None else None,
        "not_fitted": ["shoulders", "limb lengths", "head"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8810)
    parser.add_argument("--segmentation-model", default=None)
    parser.add_argument("--pose-model", default=None)
    args = parser.parse_args()

    Handler.engine, Handler.engine_error = build_engine(args.segmentation_model)
    Handler.pose, Handler.pose_error = build_pose(args.pose_model)
    if Handler.engine is None:
        print(f"reconstruction disabled: {Handler.engine_error}")
    else:
        print("reconstruction ready")
    print(
        "pose ready" if Handler.pose is not None else f"pose disabled: {Handler.pose_error}"
    )

    print(f"viewer on http://localhost:{args.port}/  (serving {VIEWER})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

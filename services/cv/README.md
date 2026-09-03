# Computer Vision Service

Owns workflows that inspect images and videos.

This service consumes media after object storage exists. It does not store image bytes and does not choose a storage provider. See `docs/architecture/SYSTEM.md` (Media And Object Storage Boundary and Garment Enrichment).

## Backend boundary (current)

Product enrichment is orchestrated in the API backend:

- HTTP: `POST /v1/wardrobe/{item_id}/enrich`
- Contract: `VisionPort.analyze_garment(image: bytes) -> GarmentAnalysis`
- Default adapter: deterministic `StubVision` (`VISION_BACKEND=stub`)
- Bytes path: linked `media_assets.reference` → `StoragePort.get` only

Real providers (Ollama, OpenCV, MediaPipe, SAM, cloud vision) are not integrated yet. When added, they should implement `VisionPort` under `backend/app/vision/` (or a dedicated services/cv adapter that the backend calls), without leaking provider details into routes, handlers, repositories, auth, or GCS code.

## First Jobs

- Wardrobe item image cleanup
- Garment category detection
- Garment segmentation
- Color extraction
- Body, face, and hand landmark extraction

## Likely Dependencies (future)

- OpenCV
- MediaPipe
- SAM 2
- MMPose

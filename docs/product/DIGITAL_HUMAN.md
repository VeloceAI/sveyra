# SVEYRA Digital Human

## Product definition

SVEYRA creates a consent-based, photorealistic, measurable, and fully animatable
digital twin of a real person. The twin preserves identity and body dimensions
across viewpoints and motion. It is the authority used later by sizing, garment
fit, and virtual try-on systems.

The target is not a mannequin, a stylized character, or a plausible person who
only resembles the user. It is a persistent digital representation of that
specific user.

## Order of work

```text
guided capture
  -> calibrated multi-view evidence
  -> canonical human reconstruction
  -> face, skin and hair identity
  -> body and facial rig
  -> photoreal runtime rendering
  -> garment fitting and virtual try-on
```

The 3D human is completed and validated before clothing integration. A try-on
provider must never become the source of truth for the person's body.

## Capture contract

The production path asks for more than one photograph:

- guided full-body turn video or calibrated multi-view images
- a known height, calibration object, or trusted depth scale
- neutral pose in close-fitting clothing
- close face coverage from the front, both profiles, and intermediate angles
- a neutral expression plus a short expression sequence
- explicit consent tied to the resulting biometric asset

A single image may produce a preview, but it cannot pass the photoreal digital
human acceptance gate. Occluded depth, the back of the body, and the body under
loose clothing cannot be honestly measured from one image.

## Durable asset

Every completed person is represented by a versioned `DigitalHumanManifest`.
It describes:

- a canonical, watertight metric body surface
- hands, feet, eyes, mouth cavity, teeth, and tongue
- body, finger, eye, jaw, tongue, and facial controls
- physically based skin, eye, lip, nail, and hair appearance
- measurements in centimetres
- evidence and confidence per anatomical region
- opaque references to stored geometry and textures
- file-level provenance for third-party material

Raw photographs and public object-storage URLs are not embedded in the
manifest. Storage lifecycle and biometric-data retention remain product-layer
responsibilities.

## First acceptance gate

`photoreal_animation_issues()` is the executable definition of the first gate.
A candidate must include:

- at least three body views, metric scale, body capture, and close face capture
- a neutral facial expression
- a watertight body with complete hands, feet, eyes, and speech anatomy
- finger, eye, eyelid, jaw, and tongue controls
- at least 52 facial blendshapes and joint corrective shapes
- base-colour, normal, roughness, and subsurface texture maps
- lighting-neutral appearance and physical skin and eye materials
- hair cards, strands, or a validated neural representation
- height, chest, waist, and hip measurements
- body, face, hands, skin, and hair evidence at or above 0.75 confidence

Passing this gate means the asset contains the required evidence and controls.
It does not by itself prove identity likeness. Dataset evaluation must also
measure novel-view similarity, surface error against scans, measurement error,
animation stability, and demographic performance.

## Milestones

### M1 - Contract and provenance

- versioned manifest and executable acceptance gate
- clean-room reference policy
- baseline report for the current procedural avatar

### M2 - Canonical human topology

- [x] commercially cleared, watertight body topology with stable UVs
- [x] matching 163-joint rest rig and normalized portable skin weights
- [x] topology-preserving, rig-aware deformation from cross-sectional `BodyParameters`
- [ ] complete eyes, mouth cavity, teeth, and tongue submeshes
- [ ] calibrated photo-landmark and surface identity deformation
- [ ] multiple validated runtime LODs

### M3 - Guided reconstruction

- calibrated body and face capture
- multi-view camera and silhouette/depth fitting
- measured-versus-inferred evidence per region
- reproducible reconstruction dataset and numeric evaluation

### M4 - Photoreal identity

- high-resolution facial shape
- lighting-neutral PBR skin and eye materials
- hair geometry and appearance
- novel-view identity and seam evaluation

### M5 - Animation

- full body, fingers, gaze, eyelids, jaw, tongue, and facial blendshapes
- motion retargeting and temporal filtering
- corrective shapes and soft-tissue deformation
- speech and lip-sync evaluation

### M6 - Try-on

- garment geometry, sizing, material, and pattern contract
- collision and cloth simulation against the metric body
- fit and pressure reporting
- optional 2D generated preview providers

## Out of scope until M6

- production clothing or accessory try-on
- claims that a generated 2D image proves garment fit
- checkout or commerce integration
- provider-specific body identity

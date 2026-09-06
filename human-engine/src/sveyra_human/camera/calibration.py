"""Estimate a camera from a photograph. Phase 2.

Will solve pixels-per-centimetre and the vertical body axis from the known
height plus detected head and foot positions, then refine toward a perspective
model. Until then callers use OrthographicCamera.fit_to_height, which assumes
the person is already upright and centred.
"""

"""Tests for the FaceBlur node.

The pure geometry/blur logic and the node's fan-out behavior are tested on
synthetic images with *injected* bounding boxes, so they need no model and no
network — they run in CI. The one test that exercises the real InsightFace
SCRFD detector is gated behind the ``RUN_FACE_MODEL=1`` environment variable
(it downloads a model on first run) and skips otherwise.
"""

import io
import os
from typing import Any, cast

import numpy as np
import pytest
from PIL import Image
from workflow_engine import FloatValue
from workflow_engine.contexts import InMemoryExecutionContext

from aceteam_nodes.nodes.face_blur import (
    BBox,
    DetectedFace,
    FaceBlurInput,
    FaceBlurNode,
    FaceBlurOutput,
    FaceBlurParams,
    ImageFileValue,
    blur_faces,
    order_faces,
)

# ---------------------------------------------------------------------------
# Synthetic-image helpers (no model needed)
# ---------------------------------------------------------------------------

# Known "face" boxes (x1, y1, x2, y2) painted as high-frequency checkerboards on
# a flat background, left-to-right.
FACE_BOXES: list[BBox] = [(10, 20, 70, 80), (110, 20, 170, 80), (210, 20, 270, 80)]
IMAGE_SIZE = (300, 100)  # width, height


def _to_float_box(bbox: BBox) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    return (float(x1), float(y1), float(x2), float(y2))


def _checker(size: int, square: int = 6) -> Image.Image:
    """A high-frequency black/white checkerboard tile (high pixel variance)."""
    arr = np.indices((size, size)).sum(axis=0) // square
    arr = np.where(arr % 2 == 0, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([arr] * 3, axis=-1), mode="RGB")


def _synthetic_faces_image() -> Image.Image:
    img = Image.new("RGB", IMAGE_SIZE, (128, 128, 128))
    for x1, y1, x2, y2 in FACE_BOXES:
        tile = _checker(x2 - x1)
        img.paste(tile, (x1, y1))
    return img


def _region_variance(img: Image.Image, bbox: tuple[int, int, int, int]) -> float:
    x1, y1, x2, y2 = bbox
    gray = np.asarray(img.convert("L"), dtype=np.float64)
    return float(gray[y1:y2, x1:x2].var())


def _decode(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


# ---------------------------------------------------------------------------
# Pure logic: deterministic ordering
# ---------------------------------------------------------------------------


def test_order_faces_is_left_to_right_and_stable():
    # Feed boxes out of order; expect indices assigned left-to-right by x.
    boxes = [
        (210.0, 20.0, 270.0, 80.0),
        (10.0, 20.0, 70.0, 80.0),
        (110.4, 20.0, 170.0, 80.0),
    ]
    faces = order_faces(boxes)
    assert [f.index for f in faces] == [0, 1, 2]
    assert [f.bbox[0] for f in faces] == [10, 110, 210]


def test_order_faces_is_permutation_invariant():
    import itertools

    boxes = [
        (210.0, 20.0, 270.0, 80.0),
        (10.0, 20.0, 70.0, 80.0),
        (110.0, 20.0, 170.0, 80.0),
    ]
    reference = order_faces(boxes)
    for perm in itertools.permutations(boxes):
        assert order_faces(list(perm)) == reference


def test_order_faces_empty():
    assert order_faces([]) == []


# ---------------------------------------------------------------------------
# Pure logic: elliptical feathered blur
# ---------------------------------------------------------------------------


def test_blur_faces_no_boxes_is_identity():
    img = _synthetic_faces_image()
    out = blur_faces(img, [], strength=0.6)
    assert np.array_equal(np.asarray(img), np.asarray(out))


def test_blur_faces_lowers_variance_only_in_target_regions():
    img = _synthetic_faces_image()
    # Blur the first two faces, keep the third sharp.
    to_blur = [_to_int(FACE_BOXES[0]), _to_int(FACE_BOXES[1])]
    out = blur_faces(img, to_blur, strength=0.7)

    # Blurred regions lose most of their variance...
    for bbox in to_blur:
        assert _region_variance(out, bbox) < 0.25 * _region_variance(img, bbox)
    # ...while the untouched region keeps ~all of it.
    kept = _to_int(FACE_BOXES[2])
    assert _region_variance(out, kept) > 0.9 * _region_variance(img, kept)


def _to_int(bbox: BBox) -> BBox:
    x1, y1, x2, y2 = bbox
    return (int(x1), int(y1), int(x2), int(y2))


# ---------------------------------------------------------------------------
# Node fan-out behavior (detector mocked — no model)
# ---------------------------------------------------------------------------


def _mock_detect(faces: list[DetectedFace]):
    def _detect(self, image):
        return faces

    return _detect


async def _run_node(
    node: FaceBlurNode, image: Image.Image
) -> tuple[FaceBlurOutput, InMemoryExecutionContext]:
    context = InMemoryExecutionContext()
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    src = ImageFileValue.from_path("input.png")
    src = await src.write(context, buf.getvalue())
    output = await node.run(
        context=context,
        input_type=FaceBlurInput,
        output_type=FaceBlurOutput,
        input=FaceBlurInput(image=src),
    )
    return output, context


def _node() -> FaceBlurNode:
    return FaceBlurNode(
        id="fb",
        type="FaceBlur",
        params=FaceBlurParams(blur_strength=FloatValue(0.7)),
    )


@pytest.mark.asyncio
async def test_node_emits_one_image_per_face_with_one_sharp_region(monkeypatch):
    faces = order_faces([_to_float_box(b) for b in FACE_BOXES])
    monkeypatch.setattr(FaceBlurNode, "_detect", _mock_detect(faces))
    img = _synthetic_faces_image()

    output, context = await _run_node(_node(), img)

    assert output.count.root == len(FACE_BOXES)
    images = list(output.images)
    assert len(images) == len(FACE_BOXES)

    # Metadata mirrors the images, in stable order. The node produces a
    # list[dict]; narrow the wide JSON `.root` type so it can be indexed.
    meta = cast(list[dict[str, Any]], output.faces.root)
    assert [m["index"] for m in meta] == [0, 1, 2]
    assert [m["bbox"] for m in meta] == [list(f.bbox) for f in faces]

    # Output i keeps exactly face i sharp and blurs the rest.
    for i, image_value in enumerate(images):
        rendered = _decode(await image_value.read(context))
        target_bbox = faces[i].bbox
        target_var = _region_variance(rendered, target_bbox)
        for j, other in enumerate(faces):
            if j == i:
                continue
            other_var = _region_variance(rendered, other.bbox)
            assert other_var < 0.5 * target_var, (
                f"output {i}: face {j} not blurred relative to target {i}"
            )


@pytest.mark.asyncio
async def test_node_zero_faces_returns_original_unchanged(monkeypatch):
    monkeypatch.setattr(FaceBlurNode, "_detect", _mock_detect([]))
    img = _synthetic_faces_image()

    output, context = await _run_node(_node(), img)

    assert output.count.root == 0
    assert output.faces.root == []
    images = list(output.images)
    assert len(images) == 1
    rendered = _decode(await images[0].read(context))
    assert np.array_equal(np.asarray(img), np.asarray(rendered))


@pytest.mark.asyncio
async def test_node_single_face_returns_single_sharp_image(monkeypatch):
    faces = order_faces([_to_float_box(FACE_BOXES[0])])
    monkeypatch.setattr(FaceBlurNode, "_detect", _mock_detect(faces))
    img = _synthetic_faces_image()

    output, context = await _run_node(_node(), img)

    assert output.count.root == 1
    images = list(output.images)
    assert len(images) == 1
    rendered = _decode(await images[0].read(context))
    # The single detected face stays sharp.
    assert _region_variance(rendered, faces[0].bbox) > 0.9 * _region_variance(
        img, faces[0].bbox
    )


# ---------------------------------------------------------------------------
# Full workflow-graph execution (detector mocked — no model)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_execute_sequence_output(monkeypatch):
    """Drive the node through a real Input -> FaceBlur -> Output graph.

    Verifies that ``SequenceValue[ImageFileValue]`` resolves in the value
    registry and flows through an Output node's field schema end-to-end.
    """
    from workflow_engine import (
        Edge,
        IntegerValue,
        JSONValue,
        SequenceValue,
        Workflow,
        WorkflowEngine,
        WorkflowExecutionResultStatus,
    )

    faces = order_faces([_to_float_box(b) for b in FACE_BOXES])
    monkeypatch.setattr(FaceBlurNode, "_detect", _mock_detect(faces))

    engine = WorkflowEngine()
    context = InMemoryExecutionContext()
    buf = io.BytesIO()
    _synthetic_faces_image().save(buf, format="PNG")
    src = ImageFileValue.from_path("input.png")
    src = await src.write(context, buf.getvalue())

    workflow = Workflow(
        input_node=(input_node := engine.create_input_node(image=ImageFileValue)),
        output_node=(
            output_node := engine.create_output_node(
                images=SequenceValue[ImageFileValue],
                faces=JSONValue,
                count=IntegerValue,
            )
        ),
        inner_nodes=[
            fb := engine.create_node(
                FaceBlurNode,
                id="faceblur",
                params=dict(blur_strength=0.7),
            ),
        ],
        edges=[
            Edge.from_nodes(
                source=input_node, source_key="image", target=fb, target_key="image"
            ),
            *[
                Edge.from_nodes(
                    source=fb, source_key=key, target=output_node, target_key=key
                )
                for key in ("images", "faces", "count")
            ],
        ],
    )

    result = await engine.execute(
        context=context, workflow=workflow, input={"image": src}
    )

    assert result.status is WorkflowExecutionResultStatus.SUCCESS
    assert result.output["count"].root == len(FACE_BOXES)
    images = list(result.output["images"])
    assert len(images) == len(FACE_BOXES)
    # Each emitted image decodes and keeps its target face sharp.
    for i, image_value in enumerate(images):
        assert isinstance(image_value, ImageFileValue)
        rendered = _decode(await image_value.read(context))
        assert _region_variance(rendered, faces[i].bbox) > _region_variance(
            rendered, faces[(i + 1) % len(faces)].bbox
        )


# ---------------------------------------------------------------------------
# Real detector (gated: downloads a model, needs a real face image)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("RUN_FACE_MODEL") != "1",
    reason="set RUN_FACE_MODEL=1 to run the InsightFace detector (downloads a model)",
)
@pytest.mark.asyncio
async def test_real_detector_group_photo():
    skimage_data = pytest.importorskip("skimage.data")
    astronaut = Image.fromarray(skimage_data.astronaut()).convert("RGB")
    w, h = astronaut.size
    group = Image.new("RGB", (w * 3, h))
    for i in range(3):
        group.paste(astronaut, (i * w, 0))

    node = _node()
    output, _context = await _run_node(node, group)

    assert output.count.root == 3
    assert len(list(output.images)) == 3
    # Faces are ordered left-to-right.
    meta = cast(list[dict[str, Any]], output.faces.root)
    xs = [m["bbox"][0] for m in meta]
    assert xs == sorted(xs)

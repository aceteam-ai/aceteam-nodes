"""Face-blur node — one photo in, N images out, each keeping one face sharp.

An educator has a group photo of several children but may only reveal the
children whose parents opted in. From one photo of N faces this node produces N
variants: variant ``i`` keeps face ``i`` sharp and elliptically blurs every
other detected face, so each variant is safe to share with exactly one child's
parent.

Everything runs locally. Face detection uses InsightFace's SCRFD detector
(CPU/Apple-Silicon friendly, no VLM, no SAM); the selective blur is a feathered
elliptical Gaussian over each non-target face. No image bytes leave the machine
and no reference/enrollment database is used — a "face id" is simply the index
(and bounding box) of a detected face within *this* image.

The heavy dependency (InsightFace + onnxruntime) is optional and only imported
when detection actually runs, so the pure geometry/blur logic below is
importable and unit-testable without downloading any model.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Type

from overrides import override
from pydantic import Field
from workflow_engine import (
    Data,
    ExecutionContext,
    File,
    FileValue,
    FloatValue,
    IntegerValue,
    JSONValue,
    Node,
    NodeTypeInfo,
    Params,
    SequenceValue,
    StringValue,
    ValidationContext,
    WorkflowException,
)
from workflow_engine.core import StakeholderLevel

if TYPE_CHECKING:
    from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# Bounding box as integer pixel coordinates: (x1, y1, x2, y2).
BBox = tuple[int, int, int, int]

# Cache of loaded InsightFace analyzers, keyed by (model_name, det_size). Loading
# an analyzer is expensive (model init) so we reuse it across node executions.
_ANALYZER_CACHE: dict[tuple[str, int], Any] = {}


class ImageFileValue(FileValue):
    """A Value that represents an image file (PNG)."""

    mime_type: ClassVar[str] = "image/png"


@dataclass(frozen=True)
class DetectedFace:
    """A detected face: a stable ``index`` and its integer pixel ``bbox``."""

    index: int
    bbox: BBox


def order_faces(
    boxes: list[tuple[float, float, float, float]],
) -> list[DetectedFace]:
    """Order detected boxes deterministically and assign stable indices.

    Faces are sorted left-to-right by bbox ``x`` (ties broken top-to-bottom by
    ``y``, then by width/height) so the same photo always yields the same
    index → face mapping regardless of detector output order. Coordinates are
    rounded to integer pixels.
    """
    normalized: list[BBox] = [_to_int_bbox(b) for b in boxes]
    ordered = sorted(normalized, key=lambda b: (b[0], b[1], b[2], b[3]))
    return [DetectedFace(index=i, bbox=b) for i, b in enumerate(ordered)]


def _to_int_bbox(box: tuple[float, float, float, float]) -> BBox:
    x1, y1, x2, y2 = box
    lo_x, hi_x = sorted((int(round(x1)), int(round(x2))))
    lo_y, hi_y = sorted((int(round(y1)), int(round(y2))))
    return (lo_x, lo_y, hi_x, hi_y)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def blur_faces(
    image: "PILImage.Image",
    boxes_to_blur: list[BBox],
    *,
    strength: float = 0.6,
    expand: float = 0.35,
) -> "PILImage.Image":
    """Return a copy of ``image`` with each given bbox elliptically blurred.

    The blur is feathered: a strong Gaussian-blurred copy of the whole image is
    composited back over the original through an elliptical mask that is itself
    Gaussian-blurred, so edges fade smoothly instead of showing a hard oval.
    The ellipse is expanded modestly beyond the tight bbox (``expand``) so jaw
    and hairline are covered. Regions not listed are left pixel-identical.

    Pure PIL + math — no model, no OpenCV — so it is unit-testable in CI.
    """
    from PIL import Image, ImageDraw, ImageFilter

    src = image.convert("RGB")
    if not boxes_to_blur:
        return src.copy()

    width, height = src.size
    # Scale blur/feather to the size of the faces being hidden so a strength
    # value behaves consistently for small and large faces.
    sizes = [min(x2 - x1, y2 - y1) for (x1, y1, x2, y2) in boxes_to_blur]
    ref = max(1, sorted(sizes)[len(sizes) // 2])  # median face short side
    strength = _clamp01(strength)
    blur_radius = max(6.0, strength * ref)
    feather_radius = max(3.0, 0.18 * ref)

    blurred = src.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for x1, y1, x2, y2 in boxes_to_blur:
        ex = (x2 - x1) * expand / 2.0
        ey = (y2 - y1) * expand / 2.0
        draw.ellipse([x1 - ex, y1 - ey, x2 + ex, y2 + ey], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_radius))

    return Image.composite(blurred, src, mask)


def _to_png_bytes(image: "PILImage.Image") -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


class FaceBlurParams(Params):
    blur_strength: FloatValue = Field(
        title="Blur Strength",
        description=(
            "Blur intensity in [0, 1]; higher blurs the non-target faces more "
            "heavily. Scaled to face size internally."
        ),
        default=FloatValue(0.6),
    )
    model_name: StringValue = Field(
        title="Detector Model",
        description=(
            "InsightFace model pack for the SCRFD detector. 'buffalo_sc' is the "
            "small CPU-friendly pack used for the local demo."
        ),
        default=StringValue("buffalo_sc"),
    )
    det_size: IntegerValue = Field(
        title="Detection Size",
        description=(
            "Square input size for the SCRFD detector. Larger finds smaller "
            "faces at more compute cost."
        ),
        default=IntegerValue(640),
    )
    det_threshold: FloatValue = Field(
        title="Detection Threshold",
        description="Minimum detector confidence [0, 1] for a face to count.",
        default=FloatValue(0.5),
    )


class FaceBlurInput(Data):
    image: ImageFileValue = Field(
        title="Image",
        description="The source photo that may contain several faces.",
    )


class FaceBlurOutput(Data):
    images: SequenceValue[ImageFileValue] = Field(
        title="Images",
        description=(
            "One image per detected face, in stable left-to-right index order: "
            "output i keeps face i sharp and blurs every other detected face. "
            "When no faces are detected this is the original image, unchanged."
        ),
    )
    faces: JSONValue = Field(
        title="Faces",
        description=(
            "Auditable face metadata: a list of {index, bbox: [x1, y1, x2, y2]} "
            "in the same stable order as `images`. Empty when no faces found."
        ),
    )
    count: IntegerValue = Field(
        title="Count",
        description="Number of detected faces.",
    )


class FaceBlurNode(Node[FaceBlurInput, FaceBlurOutput, FaceBlurParams]):
    """Detect faces and emit one selectively-blurred image per face.

    Fully local: InsightFace SCRFD detection + feathered elliptical Gaussian
    blur. Index-based identity (no enrollment DB). See module docstring.
    """

    TYPE_INFO: ClassVar[NodeTypeInfo] = NodeTypeInfo.from_parameter_type(
        display_name="Face Blur",
        description=(
            "From one photo, produce N images where each keeps exactly one "
            "detected face sharp and blurs the rest. Runs fully on-device via "
            "InsightFace (SCRFD); no image bytes leave the machine."
        ),
        version="0.1.0",
        parameter_type=FaceBlurParams,
    )

    @classmethod
    @override
    def static_input_type(cls) -> Type[FaceBlurInput]:
        return FaceBlurInput

    @classmethod
    @override
    def static_output_type(cls) -> Type[FaceBlurOutput]:
        return FaceBlurOutput

    def _detect(self, image: "PILImage.Image") -> list[DetectedFace]:
        """Run SCRFD detection and return deterministically ordered faces."""
        import numpy as np

        analyzer = self._get_analyzer()
        # InsightFace expects a BGR ndarray (OpenCV convention).
        rgb = np.asarray(image.convert("RGB"))
        bgr = rgb[:, :, ::-1]
        threshold = float(self.params.det_threshold.root)

        boxes: list[tuple[float, float, float, float]] = []
        for face in analyzer.get(bgr):
            score = float(getattr(face, "det_score", 1.0))
            if score < threshold:
                continue
            x1, y1, x2, y2 = (float(v) for v in face.bbox)
            boxes.append((x1, y1, x2, y2))
        return order_faces(boxes)

    def _get_analyzer(self) -> Any:
        model_name = self.params.model_name.root
        det_size = int(self.params.det_size.root)
        cache_key = (model_name, det_size)
        analyzer = _ANALYZER_CACHE.get(cache_key)
        if analyzer is not None:
            return analyzer

        try:
            from insightface.app import FaceAnalysis
        except ImportError as e:
            raise WorkflowException(
                "InsightFace is not installed. Install the optional dependency: "
                "`pip install 'aceteam-nodes[face-blur]'`.",
                level=StakeholderLevel.OPERATOR,
            ) from e

        try:
            analyzer = FaceAnalysis(
                name=model_name,
                allowed_modules=["detection"],
                providers=["CPUExecutionProvider"],
            )
            analyzer.prepare(ctx_id=-1, det_size=(det_size, det_size))
        except Exception as e:
            raise WorkflowException(
                f"Failed to load the InsightFace detector '{model_name}': {e}",
                level=StakeholderLevel.OPERATOR,
            ) from e

        _ANALYZER_CACHE[cache_key] = analyzer
        return analyzer

    @override
    async def run(
        self,
        *,
        context: ExecutionContext,
        input_type: Type[FaceBlurInput],
        output_type: Type[FaceBlurOutput],
        input: FaceBlurInput,
    ) -> FaceBlurOutput:
        from PIL import Image, UnidentifiedImageError

        raw = await input.image.read(context)
        try:
            source = Image.open(io.BytesIO(raw)).convert("RGB")
        except (UnidentifiedImageError, OSError) as e:
            raise WorkflowException(
                "Could not decode the input image.",
                level=StakeholderLevel.USER,
            ) from e

        strength = _clamp01(self.params.blur_strength.root)
        faces = self._detect(source)
        faces_meta = [
            {"index": face.index, "bbox": list(face.bbox)} for face in faces
        ]
        logger.info("Detected %d face(s) in input image.", len(faces))

        images: list[ImageFileValue] = []
        if not faces:
            # Zero faces: return the original image unchanged, empty metadata.
            out = ImageFileValue(File(path=f"{self.id}.face0.png"))
            out = await out.write(context, _to_png_bytes(source))
            images.append(out)
        else:
            for target in faces:
                others = [f.bbox for f in faces if f.index != target.index]
                rendered = blur_faces(source, others, strength=strength)
                out = ImageFileValue(File(path=f"{self.id}.face{target.index}.png"))
                out = out.write_metadata("kept_face_index", target.index)
                out = out.write_metadata("kept_face_bbox", list(target.bbox))
                out = await out.write(context, _to_png_bytes(rendered))
                images.append(out)

        return output_type(
            images=SequenceValue[ImageFileValue](images),
            faces=JSONValue(faces_meta),
            count=IntegerValue(len(faces)),
        )

    # This node has no dynamic behavior at validation time, but the base class
    # requires the standard hooks be resolvable; static types above suffice.
    @override
    async def dynamic_input_type(
        self, context: ValidationContext
    ) -> Type[FaceBlurInput]:
        return self.static_input_type()


__all__ = [
    "BBox",
    "DetectedFace",
    "FaceBlurInput",
    "FaceBlurNode",
    "FaceBlurOutput",
    "FaceBlurParams",
    "ImageFileValue",
    "blur_faces",
    "order_faces",
]

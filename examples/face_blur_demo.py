#!/usr/bin/env python
"""Face-blur demo: one group photo -> N single-child images, all local.

Runs the FaceBlur node end-to-end on a photo and writes one PNG per detected
face, where each output keeps exactly one face sharp and blurs the rest — the
White Whale / Seahorse "share this photo with one child's parent" workflow.
Everything (detection + blur) runs on-device; no image bytes leave the machine.

Usage:
    # Bring your own group photo:
    uv run python examples/face_blur_demo.py path/to/group_photo.jpg

    # No photo handy? Omit the path to synthesize a 3-face group image from a
    # bundled scikit-image sample (installed with the `face-blur` extra):
    uv run python examples/face_blur_demo.py

Outputs are written to ./face_blur_out/ by default (override with --out-dir).
The first run downloads the small InsightFace SCRFD model (~15 MB) to
~/.insightface; subsequent runs are offline.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
from pathlib import Path

from PIL import Image
from workflow_engine.contexts import InMemoryExecutionContext

from aceteam_nodes.nodes.face_blur import (
    FaceBlurInput,
    FaceBlurNode,
    FaceBlurOutput,
    ImageFileValue,
)


def _load_or_synthesize(photo: str | None) -> Image.Image:
    if photo:
        return Image.open(photo).convert("RGB")
    # Synthesize a group photo by tiling a bundled sample face three times.
    from skimage import data  # provided by the face-blur extra

    face = Image.fromarray(data.astronaut()).convert("RGB")
    w, h = face.size
    group = Image.new("RGB", (w * 3, h))
    for i in range(3):
        group.paste(face, (i * w, 0))
    return group


async def _run(
    image: Image.Image, strength: float
) -> tuple[FaceBlurOutput, InMemoryExecutionContext]:
    context = InMemoryExecutionContext()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    source = ImageFileValue.from_path("input.png")
    source = await source.write(context, buffer.getvalue())

    node = FaceBlurNode(
        id="faceblur", type="FaceBlur", params={"blur_strength": strength}
    )
    output = await node.run(
        context=context,
        input_type=FaceBlurInput,
        output_type=FaceBlurOutput,
        input=FaceBlurInput(image=source),
    )
    return output, context


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("photo", nargs="?", help="Path to a group photo (optional).")
    parser.add_argument("--out-dir", default="face_blur_out", help="Output directory.")
    parser.add_argument(
        "--strength", type=float, default=0.6, help="Blur strength in [0, 1]."
    )
    args = parser.parse_args()

    image = _load_or_synthesize(args.photo)
    output, context = await _run(image, args.strength)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    faces = output.faces.root
    print(f"Detected {output.count.root} face(s).")
    print(json.dumps(faces, indent=2))

    for i, image_value in enumerate(output.images):
        data = await image_value.read(context)
        if faces:
            name = f"face_{faces[i]['index']}_sharp.png"
        else:
            name = "original_no_faces.png"
        (out_dir / name).write_bytes(data)
        print(f"wrote {out_dir / name}")

    metadata_path = out_dir / "faces.json"
    metadata_path.write_text(json.dumps(faces, indent=2))
    print(f"wrote {metadata_path}")


if __name__ == "__main__":
    asyncio.run(main())

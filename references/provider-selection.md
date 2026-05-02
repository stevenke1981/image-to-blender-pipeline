# Provider Selection

## Built-In ChatGPT Image 2 Generation

Use the built-in ChatGPT Image 2 image-generation capability as the required first stage when this skill is invoked. The converter input should be the exported ChatGPT Image 2 output image, even when the user provides only a text description or an original reference image.

Do not use Playwright or browser automation for ChatGPT Image 2. Do not silently switch to another image generator. If the built-in image-generation capability cannot return or save a file artifact, stop and report the exact blocker.

Decision:

- Text-only request: use built-in ChatGPT Image 2 to generate `02_images/source-chatgpt-image2.png`.
- Uploaded reference image: use built-in ChatGPT Image 2 to regenerate a centered, full-body/full-object, conversion-ready source image.
- No uploaded image: proceed from the user's subject description instead of blocking on an upload.
- Built-in ChatGPT Image 2 unavailable: report the blocker and do not continue to image-to-3D with an unapproved substitute image.

## Image-To-3D Converter Types

Use a hosted browser converter when speed matters and user data sensitivity is low. These commonly return GLB/OBJ and are good for concept assets.

Use a category-specific converter when the target is furniture, products, shoes, bags, or decor and part separation matters.

Use a character-capable converter when the target is a humanoid, anime character, game character, or mascot. Prefer tools that preserve texture, hair silhouette, and clothing layers. Expect raw output to need Blender cleanup before animation or close-up rendering.

Use a local model when privacy, reproducibility, or offline operation matters. Expect setup cost, GPU constraints, and more manual repair in Blender.

## Format Choices

Use `glb` for quick Blender import with textures embedded.

Use `gltf` when external texture inspection or web delivery matters.

Use `obj` when the converter provides cleaner mesh interchange, but keep `.mtl` and texture files together.

Use `fbx` for DCC interchange, animation, or pipelines that require it.

Use `stl` only for geometry-oriented workflows such as 3D printing.

## Deliverable Pack

Always aim to return these artifacts:

- Generated image: `02_images/source-chatgpt-image2.png`
- Image-to-3D intermediate: raw converter output in `03_raw_3d/`, preferably `raw-conversion.glb`
- Converter preview or screenshot: `03_raw_3d/raw-conversion-preview.png` when available
- Blender model: `04_blender/model.blend`
- Blender preview render: `05_exports/blender-preview.png`
- Exported model: `05_exports/model.glb`, `model.obj`, or `model.fbx`

## Blender Acceptance Checklist

A converted asset is acceptable when:

- The silhouette matches the source image from the intended view.
- Back and side surfaces are plausible enough for the use case.
- Textures are linked and visible.
- There are no large holes, exploded parts, or inverted normals.
- The model scale and origin are usable for placement.
- The exported file opens in a fresh Blender session.

Reject or regenerate when:

- Important geometry is only painted into the texture.
- The back side is unusable and the asset must be viewed from all angles.
- The mesh is so dense that Blender interaction becomes slow.
- The user needs CAD-accurate dimensions from a single image.
- A humanoid character has fused hands, unreadable face/hair silhouette, missing feet, or clothing that only exists as flat texture.

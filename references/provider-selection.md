# Provider Selection

## Image Generation

Use OpenAI image generation when the task needs controlled concept images, iterative edits, product-style references, or a clean source image for 3D reconstruction.

Current official OpenAI docs list GPT Image models such as `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`, and `chatgpt-image-latest` in some Responses API image-generation contexts. Verify the current model list before implementing API code.

Decision:

- Single image from one prompt: use the Images API.
- Conversational image iteration or mixed text/image workflow: use the Responses API image generation tool.
- User says "ChatGPT image 2": map this to the currently available ChatGPT/OpenAI image model only after checking docs or the local project config.

## Image-To-3D Converter Types

Use a hosted browser converter when speed matters and user data sensitivity is low. These commonly return GLB/OBJ and are good for concept assets.

Use a category-specific converter when the target is furniture, products, shoes, bags, or decor and part separation matters.

Use a local model when privacy, reproducibility, or offline operation matters. Expect setup cost, GPU constraints, and more manual repair in Blender.

## Format Choices

Use `glb` for quick Blender import with textures embedded.

Use `gltf` when external texture inspection or web delivery matters.

Use `obj` when the converter provides cleaner mesh interchange, but keep `.mtl` and texture files together.

Use `fbx` for DCC interchange, animation, or pipelines that require it.

Use `stl` only for geometry-oriented workflows such as 3D printing.

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

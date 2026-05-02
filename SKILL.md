---
name: image-to-blender-pipeline
description: Plan and execute a concept-image to 3D asset pipeline using OpenAI/ChatGPT image generation, an image-to-3D converter, and Blender cleanup/export. Use when the user asks to generate a 3D model from a prompt or image, create Blender-ready assets from AI images, compare image-to-3D tools, prepare GLB/OBJ/FBX files for Blender, or automate a workflow like "ChatGPT image to image-to-3D to Blender".
---

# Image To Blender Pipeline

## Workflow

Use a three-stage pipeline:

1. Generate or refine a source image.
2. Convert the image to a mesh with an image-to-3D service or local model.
3. Import into Blender, clean the asset, assign materials, light the scene, and export.

Keep the workflow artifact-driven. Save each stage under a project folder such as:

```text
project/
  01_prompts/
  02_images/
  03_raw_3d/
  04_blender/
  05_exports/
```

## Stage 1: Source Image

Create images that are easy for image-to-3D systems to reconstruct:

- Use a single centered object, visible silhouette, plain background, soft shadows, and no crop.
- Prefer 3/4 front view for objects; request orthographic or multi-view sheets when exact shape matters.
- Avoid transparent glass, heavy motion blur, strong reflections, tiny cables, dense text, and overlapping props.
- If the user says "ChatGPT image 2", treat it as a user-facing label and confirm the actual available OpenAI image model before API work. Current OpenAI image model names change over time; prefer a configurable model setting over hardcoding.

Prompt pattern:

```text
Create a clean product reference image for image-to-3D reconstruction:
[object], single object, centered, full object visible, plain light gray background,
soft studio lighting, 3/4 front view, clear silhouette, no text, no extra props.
Style: [realistic / low-poly / toy-like / industrial design].
```

For multi-view generation, ask for front, back, left, right, and top views in one consistent sheet. Use this when the converter supports multi-view input or when manual Blender correction is expected.

## Stage 2: Image-To-3D

Choose the converter by output need:

- Fast preview: browser tools that output GLB.
- Editable asset: tools that export OBJ/FBX with texture files.
- Furniture/product parts: category-specific tools with part separation.
- Local/private workflow: local open-source image-to-3D model, accepting slower setup and GPU requirements.

Do not invent API calls for a converter. If an image-to-3D service is selected, check its current docs or UI flow before scripting. Record the chosen tool, input image path, output format, and settings in `01_prompts/asset-notes.md`.

Preferred output order for Blender:

1. `glb` or `gltf` for textured preview and easy import.
2. `obj` plus `mtl` and texture files for broad compatibility.
3. `fbx` when rigging or DCC interchange is required.
4. `stl` only for geometry/printing; it usually loses materials.

## Stage 3: Blender Cleanup

After import, perform these checks before declaring the asset usable:

- Scale: set real-world or project scale.
- Orientation: front faces camera, origin at logical base/center.
- Mesh quality: remove loose geometry, fix normals, reduce excessive polygons if needed.
- Materials: relink missing textures, rename materials clearly, simplify shader nodes if imported messily.
- UVs: inspect obvious stretching or seams on visible surfaces.
- Scene: add camera, key/fill lighting, and a neutral floor only when a render preview is requested.
- Export: save `.blend` and export the requested delivery format from `05_exports/`.

Use Blender Python for repeatable cleanup when possible:

```python
import bpy

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.shade_smooth()
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
        obj.select_set(False)
```

## Quality Gate

Before final response, verify at least one of:

- Blender opens/imports the model without errors.
- A viewport/render screenshot shows non-empty geometry.
- The exported file exists and has a plausible size.

Report known limitations plainly: single-image 3D often produces approximate back sides, messy topology, baked textures, and shapes that need manual cleanup.

## References

Read `references/provider-selection.md` when choosing image generation or image-to-3D tools, deciding file formats, or planning local versus hosted conversion.

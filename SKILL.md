---
name: image-to-blender-pipeline
description: "Execute an end-to-end text-description to Blender asset pipeline using the built-in ChatGPT Image 2 image-generation capability first, then image-to-3D conversion, then Blender cleanup/render/export. Use when the user describes an image, object, character, or scene and wants ready-to-use assets: the generated image, image-to-3D intermediate assets, and Blender model/preview outputs."
---

# Image To Blender Pipeline

## Animation-Only Routing

For walking or gait work on existing prepared rigs, skip source-image generation and image-to-3D stages. Read [gait-animation.md](references/gait-animation.md), validate `schemas/gait.schema.json`, and run the scripts under `scripts/`. Preserve the original asset pipeline below for new model creation. Do not treat raw image-to-3D meshes as rigged assets.

## Workflow

Use a four-stage asset-production pipeline. Do not skip Stage 1: this skill requires generating or regenerating the source image with the built-in ChatGPT Image 2 image-generation capability before conversion.

1. Generate or refine a source image with the built-in ChatGPT Image 2 image-generation capability from the user's text description.
2. Convert the image to a mesh with an image-to-3D service or local model.
3. Import into Blender, clean the asset, assign materials, light the scene, and export.
4. Deliver the complete asset pack: source image, image-to-3D intermediate output, Blender file, and Blender preview image.

Keep the workflow artifact-driven. Save each stage under a project folder such as:

```text
project/
  01_prompts/
  02_images/
  03_raw_3d/
  04_blender/
  05_exports/
```

Expected final files:

```text
02_images/source-chatgpt-image2.png
03_raw_3d/raw-conversion.glb
03_raw_3d/raw-conversion-preview.png
04_blender/model.blend
05_exports/model.glb
05_exports/blender-preview.png
```

## Input Decision

When the user asks to turn an image, subject, object, character, or named reference into a Blender model:

- If the user provides only text, treat the text as the complete input. Use the built-in ChatGPT Image 2 image-generation capability to generate the source image and continue the pipeline.
- If the user uploaded an image, use that image only as the reference for the built-in ChatGPT Image 2 image-generation capability. Generate a cleaner source image before image-to-3D.
- If the user did not upload an image, do not stop to request one. Use the user's subject description as the prompt for the built-in ChatGPT Image 2 image-generation capability and generate the source image from scratch.
- If the user names a copyrighted character or franchise without uploading a reference image, generate a reconstruction-ready image based on the user's described visual traits and avoid claiming commercial usage rights.
- Ask a clarifying question only when the subject is ambiguous enough that the generated source image would likely be the wrong object or character.

## Stage 1: Built-In ChatGPT Image 2 Source Image

Use the built-in ChatGPT Image 2 image-generation capability as the required image-generation step. If the user supplies an existing image, use it as a reference image for ChatGPT Image 2 and generate a cleaner reconstruction-ready source image before sending anything to image-to-3D.

Do not use Playwright or browser automation for this stage. Use the built-in image-generation tool directly, then save or export the generated image as `02_images/source-chatgpt-image2.png`. If the built-in ChatGPT Image 2 capability cannot provide a file artifact in the current environment, report that blocker plainly instead of silently substituting a Blender-script image.

Create ChatGPT Image 2 outputs that are easy for image-to-3D systems to reconstruct:

- Use a single centered object, visible silhouette, plain background, soft shadows, and no crop.
- Prefer 3/4 front view for objects; request orthographic or multi-view sheets when exact shape matters.
- Avoid transparent glass, heavy motion blur, strong reflections, tiny cables, dense text, and overlapping props.
- Save the final ChatGPT Image 2 output in `02_images/source-chatgpt-image2.png` and use that file, not the original prompt/reference image, as the converter input.

Prompt pattern for ChatGPT Image 2:

```text
Create a clean product reference image for image-to-3D reconstruction:
[object], single object, centered, full object visible, plain light gray background,
soft studio lighting, 3/4 front view, clear silhouette, no text, no extra props.
Style: [realistic / low-poly / toy-like / industrial design].
```

Prompt pattern when no image is uploaded:

```text
Generate a clean source image for image-to-3D reconstruction from this subject description:
[subject or character description from the user].
Single subject, centered, full object or full body visible, plain light gray background, soft studio lighting, clear silhouette, no text, no extra props unless requested.
Use a 3/4 front view. Make shape boundaries, important accessories, clothing layers, and surface materials easy to read for 3D reconstruction.
```

For multi-view generation, ask for front, back, left, right, and top views in one consistent sheet. Use this when the converter supports multi-view input or when manual Blender correction is expected.

## Humanoid And Anime Character Flow

Use this flow when the user asks to turn a character image, anime character, game character, or fan-art reference into a Blender model. Treat an uploaded image as reference only; still generate the converter input with built-in ChatGPT Image 2 first.

Input image requirements:

- Prefer full-body, single character, simple background, no crop.
- Prefer front or 3/4 view with visible hands, feet, hair silhouette, clothing outline, and props.
- Warn the user when a half-body or cropped image will likely produce invented legs, broken backs, and poor side views.
- For named/copyrighted characters, focus on a user-controlled reference workflow and do not imply commercial clearance.

Required ChatGPT Image 2 cleanup prompt for a single character source image:

```text
Use this image as the character reference and generate a full-body character reference image for image-to-3D reconstruction.
Single character, full body visible, 3/4 front view, clear silhouette, complete hands and feet, clean hair outline, visible clothing layers and boots, no crop.
Plain light gray background, soft studio lighting, no text, no extra characters, no complex scene.
Style: clean 3D character design reference, preserving the main hairstyle, costume silhouette, color palette, and signature prop shapes from the reference.
```

For a "Frieren / Flamme" style request, adapt the prompt with concrete visual traits from the user's provided image rather than relying only on the character name:

```text
Use this image as the character reference and generate a full-body anime-style mature female mage reference for image-to-3D reconstruction.
Long hair, long robe, boots, staff if present in the reference, single standing pose, 3/4 front view, clear silhouette, complete hands and feet, no crop.
Plain light gray background, soft studio lighting, no text, no extra characters.
Preserve the reference image's hairstyle, robe shape, color palette, and mage accessories.
```

When no character image is uploaded, generate from the user's subject text instead of asking for an upload:

```text
Generate a full-body anime-style mature female mage reference image for image-to-3D reconstruction.
Long hair, long robe, boots, staff, single standing pose, 3/4 front view, clear silhouette, complete hands and feet, no crop.
Plain light gray background, soft studio lighting, no text, no extra characters.
Design the hairstyle, robe shape, color palette, and mage accessories clearly enough for image-to-3D conversion.
```

Recommended ChatGPT Image 2 multi-view prompt:

```text
Using the same character design, generate a 3D modeling turnaround sheet with front view, side view, and back view arranged side by side.
Keep the same hairstyle, body proportions, clothing, boots, and accessories across all views.
Use a neutral standing pose or T-pose, full body visible, plain light gray background, no text, no extra characters.
```

Human character conversion notes:

- Prefer image-to-3D tools that handle characters or humanoids and export `glb`, `obj`, or `fbx`.
- Expect single-image conversion to approximate the back side, merge hair into the head, simplify hands, and bake clothing details into textures.
- If the user needs animation, plan a second pass for retopology, rigging, and weight painting; do not treat raw image-to-3D output as animation-ready.

Blender cleanup for character assets:

- Check hair first; separate or remodel large hair masses when they become a single blob.
- Check robe, cape, sleeves, boots, hands, fingers, staff, and other thin props for holes or fused geometry.
- Add thickness to clothing edges when the converter creates paper-thin surfaces.
- Fix back-side texture smearing before accepting an all-angle model.
- Set origin near the feet or body center, align the character to face the camera, and normalize scale.
- Save `.blend`; export `glb` for preview/web use, `obj` for mesh inspection, or `fbx` when rigging is planned.

## Stage 2: Image-To-3D

Choose the converter by output need:

- Fast preview: browser tools that output GLB.
- Editable asset: tools that export OBJ/FBX with texture files.
- Furniture/product parts: category-specific tools with part separation.
- Local/private workflow: local open-source image-to-3D model, accepting slower setup and GPU requirements.

Do not invent API calls for a converter. If an image-to-3D service is selected, check its current docs or UI flow before scripting. Upload `02_images/source-chatgpt-image2.png` to the converter. Record the chosen tool, input image path, output format, and settings in `01_prompts/asset-notes.md`.

Save the raw converter output and a converter preview:

- Save the raw 3D output under `03_raw_3d/`, preferably as `raw-conversion.glb`.
- Save or screenshot the converter's preview as `03_raw_3d/raw-conversion-preview.png` when the tool provides a preview.
- Keep companion files together for `obj` outputs, including `.mtl` and texture files.

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
- Export: save `04_blender/model.blend`, render `05_exports/blender-preview.png`, and export the requested delivery format from `05_exports/`.

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

## Stage 4: Optional Procedural Gait

After retopology, rigging, and weights are prepared, use `scripts/gait_cli.py` to generate an editable age/proportion/speed/state profile. Use `scripts/check_blender_gaits.py` to create and check three test Actions and previews, or `scripts/blender_gait.py` with a rig mapping to animate a prepared character copy. Follow [gait-animation.md](references/gait-animation.md) for units, mapping, output files, and acceptance checks. Reserve serpentine motion as unsupported in v0.1.0; do not silently substitute a legged walk.

Report Python trajectory validation separately from native Blender validation. Require actual Blender execution and evaluated-pose checks before marking animation PASS. If Blender is absent, deliver scripts, configs, mathematical previews, and a NOT_RUN list; do not invent Actions or rendered previews.

## Quality Gate

Before final response, verify all required deliverables exist unless blocked by a specific external service:

- `02_images/source-chatgpt-image2.png` exists and is the image-to-3D input.
- `03_raw_3d/` contains the raw converter output and, when available, a conversion preview.
- `04_blender/model.blend` opens/imports without errors.
- `05_exports/blender-preview.png` shows non-empty geometry.
- `05_exports/` contains at least one usable model export such as `model.glb`, `model.obj`, or `model.fbx`.

Report known limitations plainly: single-image 3D often produces approximate back sides, messy topology, baked textures, and shapes that need manual cleanup.

## Final Response Contract

Return the final asset paths in this order:

1. Image: `02_images/source-chatgpt-image2.png`
2. Image-to-3D intermediate: `03_raw_3d/raw-conversion.glb` and `03_raw_3d/raw-conversion-preview.png` if available
3. Blender: `04_blender/model.blend`, `05_exports/blender-preview.png`, and any exported model file

If any stage is blocked, report the exact missing requirement or service error and list the files completed so far.

## References

Read `references/provider-selection.md` when choosing image generation or image-to-3D tools, deciding file formats, or planning local versus hosted conversion.

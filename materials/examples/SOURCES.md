# Test files for the materials / names export PR (#133)

All files here were made for these tests and are released under **CC0 1.0** (public domain).

| File | What it is | How it was made |
|---|---|---|
| `build_robot.py` | Agent-channel script (stdlib only) | Builds the toy robot in OpenShape3D: 15 extruded bodies, each renamed with `item.rename` and given a material with `body.setMaterial`. Run with `OS3D_PORT=<port> python3 -I build_robot.py`. |
| `robot.glb` | Robot exported as GLB by this PR | `GET /v1/export?format=glb` after `build_robot.py` |
| `robot_main.glb` | Same robot exported by `main` | `main` plus only the `glb` export route (the GLB exporter is `main`'s) |
| `robot.3mf` | Robot exported as 3MF by this PR | `GET /v1/export?format=3mf` |
| `rocket_blender54.blend` | Toy rocket, Blender 5.4, uncompressed | Modelled in Blender 5.4 with bmesh: 6 objects, 7 Principled BSDF materials (colour only on the node; viewport colour left at the default grey); `Hull` has two materials (white + yellow stripe). Saved with `bpy.data.libraries.write` so it carries no UI or path data. |
| `rocket.glb`, `rocket.obj` + `rocket.mtl` | The rocket exported by Blender 5.4 | `export_scene.gltf` (GLB) and `wm.obj_export` (materials on) |
| `rocket_from_openshape3d.glb` | The rocket after the round trip | `rocket.glb` imported into OpenShape3D (this PR), then `GET /v1/export?format=glb` |

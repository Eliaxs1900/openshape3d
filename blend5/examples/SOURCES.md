# Test files for laanlabs/openshape3d PR #134 (Blender 5 .blend import)

| File | Saved by | Source | Licence | Authors |
|---|---|---|---|---|
| `car0_blender270.blend` | Blender 2.70 (original) | [OpenGameArt: "car 0"](https://opengameart.org/content/car-0) | CC0 | Creomoto |
| `car0_blender54.blend` | Blender 5.4.0 Alpha, uncompressed | the file above, opened and saved | CC0 | Creomoto |
| `house_blender52.blend` | Blender 5.2.3, uncompressed | a two-body house modelled in OpenShape3D for these tests (walls, gable roof, ground) | CC0 | — |
| `ship_pinnace_blender54.blend` | Blender 5.4.0 Alpha, uncompressed | [Poly Haven: Ship Pinnace](https://polyhaven.com/a/ship_pinnace), `ship_pinnace_1k.blend` | CC0 | James Ray Cock, Rico Cilliers, Nicolò Zubbini (original model), Yann Kervran (rigging) |
| *(not hosted, 247 MB)* | Blender 5.4.0 Alpha, uncompressed | [Poly Haven: Coastal Cliff 04](https://polyhaven.com/a/coastal_cliff_04), `coastal_cliff_04_1k.blend` | CC0 | Rob Tuytel, Rico Cilliers |

To reproduce the Blender 5 files from the originals:

```bash
blender -b <original>.blend --python-expr "import bpy; bpy.ops.wm.save_as_mainfile(filepath='<out>.blend', compress=False, copy=True)"
```

Poly Haven ships its `.blend` downloads zstd-compressed; saving with `compress=False` gives the plain Blender 5 container the PR reads (compressed files need #135 too). Textures are not included; they are not needed for the geometry tests.

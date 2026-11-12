#!/usr/bin/env python3
"""Toy robot for the materials/names export test (#133), built over the
OpenShape3D agent channel. 15 bodies, each renamed with item.rename and given
its own material with body.setMaterial (presets and raw colours: plastic,
metal, tinted glass, glow). Y up, millimetres. Stdlib only.
usage: OS3D_PORT=8790 python3 -I build_robot.py  → prints {name: bodyID}"""
import json, os, urllib.request, urllib.error

B = "http://127.0.0.1:" + os.environ.get("OS3D_PORT", "8787")

def post(path, body):
    r = urllib.request.Request(B + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    try:
        return json.load(urllib.request.urlopen(r, timeout=300))
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")

def ex(op, **args):
    d = post("/v1/exec", {"op": op, "args": args})
    if d.get("failed") or d.get("error"):
        raise SystemExit(f"FAILED {op}: {d.get('error')} {d.get('message')} args={json.dumps(args)[:200]}")
    return d

def plan(h): return dict(origin=[0, h, 0], xAxis=[1, 0, 0], yAxis=[0, 0, -1])   # normal +Y
def front(z): return dict(origin=[0, 0, z], xAxis=[1, 0, 0], yAxis=[0, 1, 0])   # normal +Z

def part(name, sketch, entity, seed, height):
    sid = ex("sketch.create", name=name, **sketch)["sketchID"]
    ex("sketch.addEntities", sketchID=sid, entities=[entity])
    body = ex("feature.extrude", sketchID=sid, seedPoint=seed, distance=height,
              boolean="newBody")["producedBodyIDs"][0]
    d = post("/v1/exec", {"op": "item.rename", "args": {"id": body, "name": name}})
    if d.get("error") not in (None, "unknown_op"):      # main has no item.rename
        raise SystemExit(f"FAILED item.rename: {d}")
    return body

def box(name, x0, x1, z0, z1, y0, y1):          # plan rect: v = -z
    return part(name, plan(y0), {"kind": "rect", "min": [x0, -z1], "max": [x1, -z0]},
                [(x0 + x1) / 2, -(z0 + z1) / 2], y1 - y0)

def cyl(name, x, z, r, y0, y1):
    return part(name, plan(y0), {"kind": "circle", "center": [x, -z], "radius": r}, [x, -z], y1 - y0)

def panel(name, x0, x1, y0, y1, z, depth):      # on the front face, sticking out +Z
    return part(name, front(z), {"kind": "rect", "min": [x0, y0], "max": [x1, y1]},
                [(x0 + x1) / 2, (y0 + y1) / 2], depth)

ids = {}
ids["Left foot"] = box("Left foot", -32, -4, -16, 24, 0, 10)
ids["Right foot"] = box("Right foot", 4, 32, -16, 24, 0, 10)
ids["Left leg"] = cyl("Left leg", -18, 0, 8, 10, 50)
ids["Right leg"] = cyl("Right leg", 18, 0, 8, 10, 50)
ids["Torso"] = box("Torso", -35, 35, -22, 22, 50, 120)
ids["Chest light"] = panel("Chest light", -15, 15, 78, 100, 22, 3)
ids["Left arm"] = box("Left arm", -51, -37, -7, 7, 62, 116)
ids["Right arm"] = box("Right arm", 37, 51, -7, 7, 62, 116)
ids["Left hand"] = cyl("Left hand", -44, 0, 9, 48, 62)
ids["Right hand"] = cyl("Right hand", 44, 0, 9, 48, 62)
ids["Neck"] = cyl("Neck", 0, 0, 10, 120, 130)
ids["Head"] = box("Head", -28, 28, -22, 22, 130, 175)
ids["Visor"] = panel("Visor", -21, 21, 145, 163, 22, 3)
ids["Antenna"] = cyl("Antenna", 0, 0, 2, 175, 200)
ids["Antenna light"] = cyl("Antenna light", 0, 0, 6, 200, 210)

def mat(names, **spec): ex("body.setMaterial", bodyIDs=[ids[n] for n in names], **spec)
mat(["Torso"], preset="Plastic Red")
mat(["Head"], preset="Plastic Yellow")
mat(["Left foot", "Right foot"], preset="Anodized Black")
mat(["Left leg", "Right leg", "Neck"], preset="Steel")
mat(["Left arm", "Right arm"], preset="Chrome")
mat(["Left hand", "Right hand"], color=[0.15, 0.62, 0.30], roughness=0.4)
mat(["Visor"], preset="Tinted Glass")
mat(["Chest light"], preset="Glow Blue")
mat(["Antenna"], preset="Gold")
mat(["Antenna light"], preset="Glow Red")
ex("item.setHidden", allSketches=True)
ex("item.select", ids=[])
print(json.dumps(ids, indent=1))

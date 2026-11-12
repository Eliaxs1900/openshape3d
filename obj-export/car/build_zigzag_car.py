#!/usr/bin/env python3
"""Build a 1:10 car in OpenShape3D over the agent channel (http://127.0.0.1:8787).
Deterministic, so the same script runs on the `main` build and the PR build.
usage: python3 -I car.py [stage]   (stages run in order up to and including `stage`)
Millimetres, Y up, car along X (front at +X), width along Z."""
import json, math, sys, urllib.request

import os
B = "http://127.0.0.1:" + os.environ.get("OS3D_PORT", "8787")
LOG = []

def post(path, body):
    r = urllib.request.Request(B + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    try:
        return json.load(urllib.request.urlopen(r, timeout=120))
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")

def get(path):
    return json.load(urllib.request.urlopen(B + path, timeout=120))

def ex(op, **args):
    d = post("/v1/exec", {"op": op, "args": args})
    if not d.get("ok", True) or d.get("failed") or d.get("error"):
        raise SystemExit(f"FAILED {op}: {d.get('error')} {d.get('message')} args={json.dumps(args)[:300]}")
    LOG.append(op)
    return d

def sketch(name, origin=(0, 0, 0), x=(1, 0, 0), y=(0, 0, -1), entities=()):
    """Default axes = ground plane (u = X, v = -Z)."""
    d = ex("sketch.create", name=name, origin=list(origin), xAxis=list(x), yAxis=list(y))
    sid = d["sketchID"]
    if entities:
        ex("sketch.addEntities", sketchID=sid, entities=list(entities))
    return sid

def line(a, b): return {"kind": "line", "a": list(a), "b": list(b)}
def poly(points):
    return [line(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]

def produced(d): return d["producedBodyIDs"][0]

def bodies(): return {b["id"]: b for b in get("/v1/state")["bodies"]}

IDS = {}

# ---------------------------------------------------------------- stages
def body():
    # Side profile in the XY plane: flat floor, spline over hood, roof and tail.
    sid = sketch("Carrocería perfil", origin=(0, 0, 0), x=(1, 0, 0), y=(0, 1, 0), entities=[
        line((-200, 20), (200, 20)),
        line((200, 20), (200, 60)),
        {"kind": "spline", "points": [[200, 60], [150, 84], [80, 90], [40, 118],
                                      [-40, 124], [-120, 106], [-200, 80]], "closed": False},
        line((-200, 80), (-200, 20)),
    ])
    d = ex("feature.extrude", sketchID=sid, seedPoint=[0, 50], distance=80, symmetric=True)
    IDS["body"] = produced(d)

def arches():
    for x in (130, -130):
        sid = sketch(f"Paso rueda {x}", origin=(0, 0, 0), x=(1, 0, 0), y=(0, 1, 0),
                     entities=[{"kind": "circle", "center": [x, 35], "radius": 38}])
        ex("feature.extrude", sketchID=sid, seedPoint=[x, 35], distance=100, symmetric=True,
           boolean="subtract", booleanTargets=[IDS["body"]])

def cockpit():
    # Open cockpit: pocket from y = 45 upward over the cabin.
    sid = sketch("Cabina", origin=(0, 45, 0), entities=[
        {"kind": "rect", "min": [-95, -62], "max": [25, 62]}])
    ex("feature.extrude", sketchID=sid, seedPoint=[-30, 0], distance=120,
       boolean="subtract", booleanTargets=[IDS["body"]])

def doors():
    # Door seams: a 1.2 mm frame grooved 1.5 mm into each side (a face with a hole).
    for side, z in (("izq", 80), ("dcha", -80)):
        sid = sketch(f"Puerta {side}", origin=(0, 0, z), x=(1, 0, 0), y=(0, 1, 0), entities=[
            {"kind": "rect", "min": [-92, 28], "max": [22, 70]},
            {"kind": "rect", "min": [-90.8, 29.2], "max": [20.8, 68.8]}])
        ex("feature.extrude", sketchID=sid, seedPoint=[-91.4, 50], distance=1.5, symmetric=True,
           boolean="subtract", booleanTargets=[IDS["body"]])
        # handle: small bar unioned onto the door
        hid = sketch(f"Tirador {side}", origin=(0, 0, z), x=(1, 0, 0), y=(0, 1, 0),
                     entities=[{"kind": "rect", "min": [-10, 58], "max": [6, 61]}])
        ex("feature.extrude", sketchID=hid, seedPoint=[-2, 59.5], distance=2.5, symmetric=True,
           boolean="union", booleanTargets=[IDS["body"]])

def grille():
    # Zigzag grille recessed 2 mm into the nose (a very concave polygon).
    top, bot = 54, 32
    pts = [(-55, bot)]
    for i in range(11):
        u = -55 + i * 11
        pts += [(u + 5.5, top if i % 2 == 0 else bot + 6), (u + 11, bot + 6 if i % 2 == 0 else top)]
    pts += [(66, bot)]
    pts = [(u * 0.8, v) for u, v in pts]
    sid = sketch("Parrilla zigzag", origin=(200, 0, 0), x=(0, 0, -1), y=(0, 1, 0), entities=poly(pts))
    ex("feature.extrude", sketchID=sid, seedPoint=[0, 34], distance=2, symmetric=True,
       boolean="subtract", booleanTargets=[IDS["body"]])

def headlights():
    for z in (55, -55):
        sid = sketch(f"Faro {z}", origin=(200, 0, 0), x=(0, 0, -1), y=(0, 1, 0),
                     entities=[{"kind": "ellipse", "center": [-z, 48], "radiusX": 14, "radiusY": 7}])
        ex("feature.extrude", sketchID=sid, seedPoint=[-z, 48], distance=6, symmetric=True,
           boolean="union", booleanTargets=[IDS["body"]])

def wheels():
    # Tyre: half cross-section (flat base + round tread arc) revolved about the axle (world Z).
    # Sketch plane: u = world Z, v = world Y, through the front-left wheel centre.
    cx, cy, cz = 130, 35, 70
    sid = sketch("Neumático", origin=(cx, cy, cz), x=(0, 0, 1), y=(0, 1, 0), entities=[
        line((-12, 23), (12, 23)),
        {"kind": "arc", "center": [0, 23], "radius": 12, "startAngle": 0, "endAngle": math.pi}])
    d = ex("feature.revolve", sketchID=sid, seedPoint=[0, 30], axisPoint=[0, 0], axisDirection=[1, 0])
    tyre = produced(d)
    # Rim: disc with five round holes (one sketch, seed outside the holes), overlapping the tyre 1 mm.
    ents = [{"kind": "circle", "center": [cx, cy], "radius": 24}]
    for k in range(5):
        a = 2 * math.pi * k / 5
        ents.append({"kind": "circle", "center": [cx + 14 * math.cos(a), cy + 14 * math.sin(a)], "radius": 4.5})
    rid = sketch("Llanta", origin=(0, 0, cz), x=(1, 0, 0), y=(0, 1, 0), entities=ents)
    d = ex("feature.extrude", sketchID=rid, seedPoint=[cx + 22, cy], distance=4, symmetric=True,
           boolean="union", booleanTargets=[tyre])
    # Lug nuts: one hexagon boss, circular pattern x5 about the axle, unioned.
    nid = sketch("Tuerca", origin=(0, 0, cz + 4), x=(1, 0, 0), y=(0, 1, 0),
                 entities=[{"kind": "polygon", "center": [cx + 7, cy], "radius": 2.2, "sides": 6}])
    d = ex("feature.extrude", sketchID=nid, seedPoint=[cx + 7, cy], distance=3)
    nut = produced(d)
    d = ex("feature.pattern", bodyID=nut, count=5, kind="circular", axis=[0, 0, 1], center=[cx, cy, cz])
    nuts = [nut] + d["producedBodyIDs"]
    ex("feature.boolean", kind="union", targetBodyID=tyre, toolBodyIDs=nuts)
    wheels = [tyre]
    d = ex("feature.mirror", bodyID=tyre, planeOrigin=[0, 0, 0], planeNormal=[1, 0, 0]); wheels += d["producedBodyIDs"]
    for w in list(wheels):
        d = ex("feature.mirror", bodyID=w, planeOrigin=[0, 0, 0], planeNormal=[0, 0, 1]); wheels += d["producedBodyIDs"]
    IDS["wheels"] = wheels

def steering():
    # Ring (revolve a small circle), a bar with hub, a column: unioned, then tilted into the cockpit.
    sid = sketch("Aro volante", origin=(0, 0, 0), x=(1, 0, 0), y=(0, 1, 0),
                 entities=[{"kind": "circle", "center": [16, 0], "radius": 2.2}])
    ring = produced(ex("feature.revolve", sketchID=sid, seedPoint=[16, 0], axisPoint=[0, 0], axisDirection=[0, 1]))
    bid = sketch("Radios", origin=(0, -1.2, 0), entities=[
        {"kind": "rect", "min": [-17, -1.6], "max": [17, 1.6]}, {"kind": "circle", "center": [0, 0], "radius": 4.5}])
    bar = produced(ex("feature.extrude", sketchID=bid, seedPoint=[10, 0], distance=2.4))
    hub = produced(ex("feature.extrude", sketchID=bid, seedPoint=[0, 0], distance=2.4))
    cid = sketch("Columna", origin=(0, -36, 0), entities=[{"kind": "circle", "center": [0, 0], "radius": 1.8}])
    col = produced(ex("feature.extrude", sketchID=cid, seedPoint=[0, 0], distance=36))
    ex("feature.boolean", kind="union", targetBodyID=ring, toolBodyIDs=[bar, hub, col])
    ex("feature.transform", bodyID=ring, rotationDegrees=-62, rotationAxis=[0, 0, 1], rotationCenter=[0, 0, 0])
    ex("feature.transform", bodyID=ring, translation=[2, 92, -32])
    IDS["steering"] = ring

def spring():
    # Coil spring behind the front-left wheel: a circle swept along a helix.
    sid = sketch("Muelle perfil", origin=(150, 20, 52), x=(0, 0, 1), y=(0, 1, 0),
                 entities=[{"kind": "circle", "center": [0, 0], "radius": 1.0}])
    # Profile at the helix start (axis +Y through (140, 20, 52), radius 10): start point (150, 20, 52).
    d = ex("feature.sweep", sketchID=sid, seedPoint=[0, 0],
           helix={"axisPoint": [140, 20, 52], "axisDirection": [0, 1, 0], "radius": 10, "pitch": 6, "turns": 5})
    IDS["spring"] = produced(d)

def finish():
    ex("item.setHidden", allSketches=True)
    ex("item.select", ids=[])
    ex("body.setMaterial", bodyIDs=[IDS["body"]], color=[0.75, 0.08, 0.06], metallic=0.4, roughness=0.35)
    if "wheels" in IDS:
        ex("body.setMaterial", bodyIDs=IDS["wheels"], color=[0.08, 0.08, 0.09], roughness=0.8)
    if "steering" in IDS:
        ex("body.setMaterial", bodyIDs=[IDS["steering"]], color=[0.15, 0.15, 0.17], roughness=0.5)
    if "spring" in IDS:
        ex("body.setMaterial", bodyIDs=[IDS["spring"]], preset="Steel")

STAGES = [body, arches, cockpit, doors, grille, headlights, wheels, steering, spring, finish]

if __name__ == "__main__":
    stop = sys.argv[1] if len(sys.argv) > 1 else STAGES[-1].__name__
    for st in STAGES:
        st()
        bs = bodies()
        print(f"{st.__name__:11s} ok · bodies={len(bs)} · " +
              ", ".join(f"{b['name']}={b['volumeMM3']:.1f}" for b in list(bs.values())[:4]) +
              (" …" if len(bs) > 4 else ""), flush=True)
        if st.__name__ == stop: break
    json.dump(IDS, open("ids.json", "w"))

#!/usr/bin/env python3
"""Replica of the CC0 "car 0" (Creomoto, OpenGameArt) in OpenShape3D over the agent channel.
Same scale and place as the imported reference: app X = width, Y = up, Z = length (front at +Z), mm.
Measurements taken from car_0.blend in Blender (app = (x, z, -y) * 1000).
usage: python3 -I car2.py [last_stage]"""
import json, math, sys, urllib.request

import os
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
    if not d.get("ok", True) or d.get("failed") or d.get("error"):
        raise SystemExit(f"FAILED {op}: {d.get('error')} {d.get('message')} args={json.dumps(args)[:240]}")
    return d

def sk(name, origin, x, y, ents):
    sid = ex("sketch.create", name=name, origin=list(origin), xAxis=list(x), yAxis=list(y))["sketchID"]
    ex("sketch.addEntities", sketchID=sid, entities=ents)
    return sid

SIDE = dict(origin=(0, 0, 0), x=(0, 0, 1), y=(0, 1, 0))      # u = Z (length), v = Y (height); normal X
FRONT = dict(origin=(0, 0, 0), x=(1, 0, 0), y=(0, 1, 0))     # u = X (width),  v = Y; normal Z
def plan_at(h): return dict(origin=(0, h, 0), x=(1, 0, 0), y=(0, 0, -1))  # u = X, v = -Z; normal +Y

def line(a, b): return {"kind": "line", "a": list(a), "b": list(b)}
def poly(pts): return [line(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
def rect(a, b): return {"kind": "rect", "min": list(a), "max": list(b)}
def circle(c, r): return {"kind": "circle", "center": list(c), "radius": r}

def extrude(sid, seed, dist, symmetric=False, **kw):
    d = ex("feature.extrude", sketchID=sid, seedPoint=list(seed), distance=dist, symmetric=symmetric, **kw)
    return d["producedBodyIDs"][0] if d["producedBodyIDs"] else None

def boolean(kind, target, tools):
    return ex("feature.boolean", kind=kind, targetBodyID=target, toolBodyIDs=list(tools))

IDS = {}

# ------------------------------------------------------------------ sketches reused for copies
def sketches():
    side_top = [[3447, 1236], [3160, 1300], [2874, 1430], [2000, 1437], [1157, 1416], [871, 1395],
                [0, 1385], [-1000, 1362], [-1990, 1312], [-2563, 1262], [-3135, 1235], [-3421, 869]]
    IDS["s_side"] = sk("Perfil lateral", ents=[
        line((3447, 381), (3447, 1236)),
        {"kind": "spline", "points": side_top, "closed": False},
        line((-3421, 869), (-3421, 447)),
        line((-3421, 447), (3447, 381))], **SIDE)
    half = [(926, -3447), (1366, -3160), (1430, -2588), (1458, -1500), (1458, 0), (1440, 1500),
            (1427, 1990), (1422, 2563), (1386, 2849), (1329, 3135), (1300, 3421)]
    plan = [list(p) for p in half] + [[-x, v] for x, v in reversed(half)]
    IDS["s_plan"] = sk("Planta", ents=[{"kind": "spline", "points": plan, "closed": True}], **plan_at(0))
    sec = [(0, 368), (1250, 375), (1440, 750), (1395, 1050), (1250, 1380), (0, 1448),
           (-1250, 1380), (-1395, 1050), (-1440, 750), (-1250, 375)]
    IDS["s_front"] = sk("Sección frontal", ents=[{"kind": "spline", "points": [list(p) for p in sec], "closed": True}], **FRONT)
    IDS["s_cab_side"] = sk("Cabina perfil", ents=poly([(1000, 1300), (871, 1391), (299, 2096), (-1704, 2099), (-2000, 1300)]), **SIDE)
    IDS["s_cab_front"] = sk("Cabina sección", ents=poly([(-1235, 1250), (1235, 1250), (1122, 2110), (-1122, 2110)]), **FRONT)

def lower_body():
    side = extrude(IDS["s_side"], (0, 800), 1600, symmetric=True)
    plan = extrude(IDS["s_plan"], (0, 0), 2600)
    front = extrude(IDS["s_front"], (0, 800), 3600, symmetric=True)
    boolean("intersect", side, [plan, front])
    IDS["body"] = side

def cabin_solid():
    a = extrude(IDS["s_cab_side"], (-600, 1700), 1600, symmetric=True)
    b = extrude(IDS["s_cab_front"], (0, 1700), 3600, symmetric=True)
    boolean("intersect", a, [b])
    return a

def cabin_and_glass():
    cabin = cabin_solid()
    skin = cabin_solid()
    ex("feature.shell", bodyID=skin, thickness=25)                      # sealed 25 mm skin
    # window regions: windscreen, rear window (centre), side windows (both sides)
    ws = extrude(sk("Parabrisas zona", ents=[rect((-1000, -905), (1000, -290))], **plan_at(1350)), (0, -600), 800)
    rw = extrude(sk("Luneta zona", ents=[rect((-1000, 1695), (1000, 2060))], **plan_at(1330)), (0, 1850), 800)
    win = [(800, 1425), (335, 2035), (-420, 2035), (-420, 1425)], [(-560, 1425), (-560, 2035), (-1660, 2035), (-1935, 1425)]
    sides = []
    for xs in (1200, -1200):
        sid = sk(f"Ventanas {xs}", origin=(xs, 0, 0), x=(0, 0, 1), y=(0, 1, 0), ents=poly(win[0]) + poly(win[1]))
        sides.append(extrude(sid, (0, 1700), 400, symmetric=True))
        sides.append(extrude(sid, (-1100, 1700), 400, symmetric=True))
    boolean("union", ws, [rw] + sides)
    boolean("intersect", skin, [ws])                                     # skin ∩ window regions = glass
    IDS["glass"] = skin
    copy = ex("feature.mirror", bodyID=skin, planeOrigin=[0, 0, 0], planeNormal=[1, 0, 0])["producedBodyIDs"][0]
    boolean("subtract", cabin, [copy])                                   # pillars + roof in paint
    boolean("union", IDS["body"], [cabin])

def details():
    body = IDS["body"]
    # wheel arches (front z=1962, rear z=-1831, centre height 290)
    for z in (1962, -1831):
        a = extrude(sk(f"Paso {z}", ents=[circle((z, 290), 610)], **SIDE), (z, 290), 1700, symmetric=True)
        boolean("subtract", body, [a])
    # hood scoop: tapered pad on the hood
    sc = sk("Toma aire", ents=poly([(-420, -2650), (420, -2650), (330, -1450), (-330, -1450)]), **plan_at(1380))
    s = extrude(sc, (0, -2000), 150, taperDegrees=25)
    boolean("union", body, [s])
    # front: headlight and grille recesses, then inserts
    nose = dict(origin=(0, 0, 3447), x=(1, 0, 0), y=(0, 1, 0))
    lights = [((520, 1000), (880, 1170)), ((-880, 1000), (-520, 1170))]
    grille = ((-430, 1010), (430, 1160))
    for i, (a, b) in enumerate(lights + [grille]):
        r = extrude(sk(f"Hueco frontal {i}", ents=[rect(a, b)], **nose), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), 60, symmetric=True)
        boolean("subtract", body, [r])
    ins = []
    for i, (a, b) in enumerate(lights):
        ins.append(extrude(sk(f"Faro {i}", origin=(0, 0, 3400), x=(1, 0, 0), y=(0, 1, 0), ents=[rect(a, b)]), ((a[0] + b[0]) / 2, 1085), 30))
    IDS["lights"] = ins
    g = extrude(sk("Parrilla", origin=(0, 0, 3395), x=(1, 0, 0), y=(0, 1, 0), ents=[rect(*grille)]), (0, 1085), 20)
    IDS["grille"] = g
    # bumpers
    bf = extrude(sk("Paragolpes del.", origin=(0, 0, 3380), x=(1, 0, 0), y=(0, 1, 0),
                    ents=[rect((-1000, 420), (1000, 560))]), (0, 490), 140)
    br = extrude(sk("Paragolpes tras.", origin=(0, 0, -3480), x=(1, 0, 0), y=(0, 1, 0),
                    ents=[rect((-1000, 480), (1000, 620))]), (0, 550), 140)
    IDS["bumpers"] = [bf, br]
    # side mirrors
    m = extrude(sk("Retrovisores", ents=[rect((-1540, -640), (-1360, -520)), rect((1360, -640), (1540, -520))], **plan_at(1430)), (1450, -580), 90)
    m2 = extrude(ex("sketch.create", name="tmp", origin=[0, 1430, 0], xAxis=[1, 0, 0], yAxis=[0, 0, -1])["sketchID"] and IDS.get("_none") or m, (0, 0), 0) if False else None
    boolean("union", body, [m])

def wheels():
    cx, cy, cz, w = 1261, 290, 1962, 374
    hw = w / 2
    prof = [line((-hw, 380), (hw, 380)), line((hw, 380), (hw, 509)),
            {"kind": "arc", "center": [hw - 60, 509], "radius": 60, "startAngle": 0, "endAngle": math.pi / 2},
            line((hw - 60, 569), (-hw + 60, 569)),
            {"kind": "arc", "center": [-hw + 60, 509], "radius": 60, "startAngle": math.pi / 2, "endAngle": math.pi},
            line((-hw, 509), (-hw, 380))]
    tyre = ex("feature.revolve", sketchID=sk("Neumático", origin=(cx, cy, cz), x=(1, 0, 0), y=(0, 1, 0), ents=prof),
              seedPoint=[0, 470], axisPoint=[0, 0], axisDirection=[1, 0])["producedBodyIDs"][0]
    ents = [circle((cz, cy), 385)] + [circle((cz + 230 * math.cos(2 * math.pi * k / 6), cy + 230 * math.sin(2 * math.pi * k / 6)), 92) for k in range(6)]
    rim = extrude(sk("Llanta", origin=(cx, 0, 0), x=(0, 0, 1), y=(0, 1, 0), ents=ents), (cz + 360, cy), 150, symmetric=True)
    hub = extrude(sk("Tapacubos", origin=(cx + 150, 0, 0), x=(0, 0, 1), y=(0, 1, 0), ents=[circle((cz, cy), 70)]), (cz, cy), 40, symmetric=True)
    boolean("union", rim, [hub])
    out = [tyre, rim]
    for b in (tyre, rim):
        out.append(ex("feature.mirror", bodyID=b, planeOrigin=[0, 0, 0], planeNormal=[1, 0, 0])["producedBodyIDs"][0])
    for b in list(out):
        out.append(ex("feature.mirror", bodyID=b, planeOrigin=[0, 0, (1962 - 1831) / 2], planeNormal=[0, 0, 1])["producedBodyIDs"][0])
    IDS["tyres"] = out[0::2]; IDS["rims"] = out[1::2]

def paint():
    ex("item.setHidden", allSketches=True)
    ex("item.select", ids=[])
    ex("body.setMaterial", bodyIDs=[IDS["body"]], color=[0.62, 0.06, 0.04], metallic=0.5, roughness=0.3)
    ex("body.setMaterial", bodyIDs=[IDS["glass"]], color=[0.12, 0.15, 0.2, 0.75], metallic=0.0, roughness=0.05)
    ex("body.setMaterial", bodyIDs=IDS["lights"], color=[0.95, 0.95, 0.9], emission=0.4)
    ex("body.setMaterial", bodyIDs=[IDS["grille"]], color=[0.05, 0.05, 0.06], roughness=0.6)
    ex("body.setMaterial", bodyIDs=IDS["bumpers"], preset="Chrome")
    ex("body.setMaterial", bodyIDs=IDS["tyres"], color=[0.06, 0.06, 0.07], roughness=0.85)
    ex("body.setMaterial", bodyIDs=IDS["rims"], preset="Aluminum")

STAGES = [sketches, lower_body, cabin_and_glass, details, wheels, paint]
if __name__ == "__main__":
    stop = sys.argv[1] if len(sys.argv) > 1 else STAGES[-1].__name__
    for st in STAGES:
        st()
        bs = post("/v1/command", {"id": "view.fit"})["bodies"]
        print(f"{st.__name__:16s} ok · bodies={len(bs)} · " + ", ".join(f"{b['name']}={b['volumeMM3']/1e9:.3f} dm³" for b in bs[:3]), flush=True)
        if st.__name__ == stop:
            break
    json.dump(IDS, open("ids2.json", "w"))

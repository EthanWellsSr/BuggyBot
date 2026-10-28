"""Camera Module 3 bracket for the CM5 IO board, written as an STL with no dependencies.

Bolts to mounting hole H7 (M2.5) behind CAM/DISP 0 (J5) with one screw, and to
the camera's two holes on one side with two M2 screws. Positions come from
Hardware/BuggyBot KiCAD/CM5IO.kicad_pcb:
    J5 (CAM/DISP 0) at (90.5, 75.0), courtyard y 70.1-78.0, x 82.0-99.1
    H7              at (90.0, 83.0)
    J3 (Qwiic)      courtyard x 79.5-86.0, y 83.3-91.1
    board edge      y = 70.0

Model frame (mm): origin at the centre of H7 on the top of the PCB.
    +X = board +x, +Y = toward the board edge behind CAM0 (board -y), +Z = up.
The camera faces +Y with its ribbon connector at the bottom.

Run:  python3 camera_bracket.py   ->  camera_bracket.stl next to this file
"""

import math
import struct
from pathlib import Path

SEGMENTS = 32

# Board screw (H7)
BOARD_HOLE_D = 2.7          # matches the KiCad M2.5 hole

# Camera Module 3: holes 21 mm apart horizontally, 12.5 mm vertically,
# 2 mm in from the edges. Board is 25 x 24 mm.
CAM_PILOT_D = 1.8           # M2 self-tapping into plastic
CAM_HOLE_X = 9.5            # hole column; the camera extends +X from here
CAM_LOWER_Z = 26.0          # lower hole; the camera's bottom edge is 9.5 mm below
CAM_HOLE_DZ = 12.5
STANDOFF_D = 5.0
STANDOFF_LEN = 3.0          # gap for parts on the back of the camera

# Foot: stays clear of J5 (Y >= 5) and J3 (X <= -3.97 for Y <= -0.3)
FOOT = (-3.5, 13.0, -6.0, 4.0)      # x0, x1, y0, y1
FOOT_T = 4.0

# Upright sits beside H7 so a screwdriver can reach the board screw
UPRIGHT_X = (6.0, 13.0)
UPRIGHT_Y = (-1.0, 3.0)
UPRIGHT_TOP = CAM_LOWER_Z + CAM_HOLE_DZ + 4.0

# Brace behind the upright
GUSSET_X = (8.0, 11.0)
GUSSET_DEPTH = 5.0
GUSSET_H = 15.0


def circle(cx, cy, r, n=SEGMENTS):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def rect_with_hole(x0, x1, y0, y1, hole):
    """Triangulate a rectangle minus one circle using only the four corners on the outside.

    Each corner fans to the quarter of the circle facing it, so cells stacked
    edge to edge share vertices and join cleanly.
    """
    n = len(hole)
    corners = [(x1, y1), (x0, y1), (x0, y0), (x1, y0)]   # quadrants 0-90, 90-180, ...
    tris = []
    q = n // 4
    for k, c in enumerate(corners):
        for i in range(k * q, (k + 1) * q):
            tris.append((c, hole[(i + 1) % n], hole[i]))
        # gap between this corner's fan and the next corner's fan
        tris.append((c, corners[(k + 1) % 4], hole[((k + 1) * q) % n]))
    return tris


def rect(x0, x1, y0, y1):
    return [((x0, y0), (x1, y0), (x1, y1)), ((x0, y0), (x1, y1), (x0, y1))]


def annulus(cx, cy, r_out, r_in):
    outer, inner = circle(cx, cy, r_out), circle(cx, cy, r_in)
    tris = []
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        tris += [(outer[i], outer[j], inner[j]), (outer[i], inner[j], inner[i])]
    return tris


def extrude(tris2d, z0, z1, to3d):
    """Turn CCW 2D triangles into a closed prism; to3d maps (u, v, w) into the model frame."""
    out = []
    edges = {}
    for a, b, c in tris2d:
        out.append((to3d(*a, z1), to3d(*b, z1), to3d(*c, z1)))
        out.append((to3d(*a, z0), to3d(*c, z0), to3d(*b, z0)))
        for p, q in ((a, b), (b, c), (c, a)):
            edges[(p, q)] = edges.get((p, q), 0) + 1
    # Boundary edges appear once and never reversed; each becomes a wall.
    for (p, q), count in edges.items():
        if (q, p) not in edges:
            out.append((to3d(*p, z0), to3d(*q, z0), to3d(*q, z1)))
            out.append((to3d(*p, z0), to3d(*q, z1), to3d(*p, z1)))
    return out


def xy_plane(u, v, w):      # extrude along Z
    return (u, v, w)


def xz_plane(u, v, w):      # 2D (x, z), extrude along Y
    return (u, -w, v)


def bracket():
    x0, x1, y0, y1 = FOOT
    foot = extrude(rect_with_hole(x0, x1, y0, y1, circle(0, 0, BOARD_HOLE_D / 2)), 0, FOOT_T, xy_plane)

    # Upright, cut into cells with one camera hole each; xz_plane's -w puts
    # the extrusion range (-y1, -y0) at Y = y0..y1.
    ux0, ux1 = UPRIGHT_X
    upper_z = CAM_LOWER_Z + CAM_HOLE_DZ
    split = CAM_LOWER_Z + CAM_HOLE_DZ / 2
    r = CAM_PILOT_D / 2
    cells = (rect(ux0, ux1, 0, FOOT_T)
             + rect_with_hole(ux0, ux1, FOOT_T, split, circle(CAM_HOLE_X, CAM_LOWER_Z, r))
             + rect_with_hole(ux0, ux1, split, UPRIGHT_TOP, circle(CAM_HOLE_X, upper_z, r)))
    upright = extrude(cells, -UPRIGHT_Y[1], -UPRIGHT_Y[0], xz_plane)

    standoffs = []
    for z in (CAM_LOWER_Z, upper_z):
        ring = annulus(CAM_HOLE_X, z, STANDOFF_D / 2, r)
        standoffs += extrude(ring, -(UPRIGHT_Y[1] + STANDOFF_LEN), -UPRIGHT_Y[1] + 0.01, xz_plane)

    # Gusset: triangle in the (Y, Z) plane, extruded along X
    gy = UPRIGHT_Y[0]
    tri = [((gy - GUSSET_DEPTH, 0.0), (gy + 0.01, 0.0), (gy + 0.01, GUSSET_H))]
    gusset = extrude(tri, GUSSET_X[0], GUSSET_X[1], lambda u, v, w: (w, u, v))

    return [foot, upright, standoffs, gusset]


def check_closed(shell):
    """Every edge of a closed, consistently wound shell is used once in each direction."""
    edges = {}
    for tri in shell:
        for i in range(3):
            e = (tri[i], tri[(i + 1) % 3])
            edges[e] = edges.get(e, 0) + 1
    return all(edges.get((q, p)) == 1 and n == 1 for (p, q), n in edges.items())


def write_stl(path, shells):
    tris = [t for s in shells for t in s]
    with open(path, 'wb') as f:
        f.write(b'BuggyBot camera bracket'.ljust(80, b' '))
        f.write(struct.pack('<I', len(tris)))
        for a, b, c in tris:
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            length = math.sqrt(sum(x * x for x in n)) or 1.0
            f.write(struct.pack('<12fH', *(x / length for x in n), *a, *b, *c, 0))
    return len(tris)


if __name__ == '__main__':
    shells = bracket()
    for name, shell in zip(('foot', 'upright', 'standoffs', 'gusset'), shells):
        print(f'{name}: {"closed" if check_closed(shell) else "NOT CLOSED"}')
    out = Path(__file__).with_suffix('.stl')
    print(f'{write_stl(out, shells)} triangles -> {out.name}')

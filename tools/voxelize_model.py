#!/usr/bin/env python3
# ARES // converte um modelo 3D (glTF .glb / .gltf / .zip do Sketchfab) numa grade
# de voxels para o shader do wallpaper.
#
# Saída: home/.config/ares/wallpaper/helmet_vox.bin  (N³ bytes, densidade 0..255)
#        home/.config/ares/wallpaper/helmet_vox.json (N e metadados)
# Depois rode tools/gen_wallpaper_shader.py, que embute os voxels no shader.
#
# Uso: python3 tools/voxelize_model.py ~/Downloads/modelo.glb [--size 96] [--rot-y 0]
# Só lê geometria (posições e índices); nada do arquivo é executado.
# Deps: python-numpy

import argparse
import json
import os
import struct
import tempfile
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "..", "home", ".config", "ares", "wallpaper")

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --- leitura do glTF -----------------------------------------------------------
def load_gltf(path):
    """Retorna (gltf_json, buffers: list[bytes])."""
    if path.endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="ares-model-")
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith((".gltf", ".glb", ".bin"))]
            for n in names:  # extrai só o necessário, sem caminhos relativos perigosos
                target = os.path.join(tmp, os.path.basename(n))
                with z.open(n) as src, open(target, "wb") as dst:
                    dst.write(src.read())
        cand = [f for f in os.listdir(tmp) if f.endswith((".glb", ".gltf"))]
        if not cand:
            raise SystemExit("zip sem .gltf/.glb")
        return load_gltf(os.path.join(tmp, cand[0]))

    data = open(path, "rb").read()
    if data[:4] == b"glTF":  # GLB binário
        _, _, length = struct.unpack_from("<III", data, 0)
        off, js, binchunk = 12, None, b""
        while off < length:
            clen, ctype = struct.unpack_from("<II", data, off)
            chunk = data[off + 8: off + 8 + clen]
            if ctype == 0x4E4F534A:
                js = json.loads(chunk)
            elif ctype == 0x004E4942:
                binchunk = chunk
            off += 8 + clen
        bufs = []
        for b in js.get("buffers", []):
            bufs.append(binchunk if "uri" not in b else open(os.path.join(os.path.dirname(path), b["uri"]), "rb").read())
        return js, bufs

    js = json.loads(data)
    bufs = [open(os.path.join(os.path.dirname(path), b["uri"]), "rb").read() for b in js["buffers"]]
    return js, bufs


def accessor(js, bufs, idx):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a["bufferView"]]
    dtype = np.dtype(COMP[a["componentType"]])
    n = NCOMP[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0) or dtype.itemsize * n
    raw = bufs[bv["buffer"]]
    if stride == dtype.itemsize * n:
        arr = np.frombuffer(raw, dtype, a["count"] * n, start).reshape(a["count"], n)
    else:
        rows = [np.frombuffer(raw, dtype, n, start + i * stride) for i in range(a["count"])]
        arr = np.stack(rows)
    return arr.astype(np.float64 if dtype == np.float32 else np.int64)


def node_matrix(node):
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    t = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
    r = node.get("rotation", [0, 0, 0, 1])
    s = np.array(node.get("scale", [1, 1, 1]), dtype=np.float64)
    x, y, z, w = r
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4)
    M[:3, :3] = R * s
    M[:3, 3] = t
    return M


def collect_triangles(js, bufs):
    verts, faces = [], []
    base = 0

    def visit(ni, parent):
        nonlocal base
        node = js["nodes"][ni]
        M = parent @ node_matrix(node)
        if "mesh" in node:
            for prim in js["meshes"][node["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4 or "POSITION" not in prim["attributes"]:
                    continue
                v = accessor(js, bufs, prim["attributes"]["POSITION"])
                v = (np.c_[v, np.ones(len(v))] @ M.T)[:, :3]
                f = (accessor(js, bufs, prim["indices"]).reshape(-1, 3) if "indices" in prim
                     else np.arange(len(v)).reshape(-1, 3))
                verts.append(v)
                faces.append(f + base)
                base += len(v)
        for c in node.get("children", []):
            visit(c, M)

    scene = js["scenes"][js.get("scene", 0)]
    for ni in scene["nodes"]:
        visit(ni, np.eye(4))
    return np.concatenate(verts), np.concatenate(faces)


# --- voxelização ------------------------------------------------------------------
def voxelize(V, F, N):
    # normaliza: centraliza e cabe em [-1, 1] mantendo a proporção (margem de 2 voxels)
    lo, hi = V.min(0), V.max(0)
    center, extent = (lo + hi) / 2, (hi - lo).max() / 2
    V = (V - center) / extent * (1 - 4 / N)
    g = (V + 1) / 2 * N                      # coordenadas em voxels
    surf = np.zeros((N, N, N), dtype=bool)
    tri = g[F]                               # (T, 3, 3)
    # subdivide triângulos grandes até todos caberem em ~meio voxel
    while len(tri):
        e = np.max(np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2), axis=1)
        small = tri[e <= 0.5]
        pts = np.concatenate([small.reshape(-1, 3), small.mean(1)])
        idx = np.clip(pts.astype(int), 0, N - 1)
        surf[idx[:, 0], idx[:, 1], idx[:, 2]] = True
        big = tri[e > 0.5]
        if not len(big):
            break
        a, b, c = big[:, 0], big[:, 1], big[:, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        tri = np.concatenate([np.stack(t, 1) for t in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
    # inunda o lado de fora; o que sobrar (casco + cavidades fechadas) é sólido
    outside = np.zeros_like(surf)
    outside[0, :, :] = outside[-1, :, :] = outside[:, 0, :] = outside[:, -1, :] = True
    outside[:, :, 0] = outside[:, :, -1] = True
    outside &= ~surf
    while True:
        grow = outside.copy()
        for ax in range(3):
            grow |= np.roll(outside, 1, ax) | np.roll(outside, -1, ax)
        grow &= ~surf
        if grow.sum() == outside.sum():
            break
        outside = grow
    solid = (~outside).astype(np.float32)
    # suaviza (caixa 3x3x3) para o shader ter gradiente e normais bonitas
    dens = np.zeros_like(solid)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                dens += np.roll(np.roll(np.roll(solid, dx, 0), dy, 1), dz, 2)
    dens /= 27.0
    return (np.clip(dens, 0, 1) * 255).astype(np.uint8), surf.sum(), (~outside).sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--rot-y", type=float, default=0.0, help="gira o modelo (graus) para a frente ficar em +Z")
    ap.add_argument("--rot-x", type=float, default=0.0, help="inclina o modelo (graus)")
    args = ap.parse_args()

    path = os.path.expanduser(args.model)
    if not os.path.isfile(path):
        raise SystemExit(f"arquivo não encontrado: {path}\n"
                         "use o caminho do modelo baixado (.glb, .gltf ou .zip do Sketchfab)")
    js, bufs = load_gltf(path)
    V, F = collect_triangles(js, bufs)
    print(f"modelo: {len(V)} vértices, {len(F)} triângulos")
    ry, rx = np.radians(args.rot_y), np.radians(args.rot_x)
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
    V = V @ (Rx @ Ry).T
    vox, nsurf, nsolid = voxelize(V, F, args.size)
    os.makedirs(OUTDIR, exist_ok=True)
    # ordem x mais rápido, depois y, depois z (layout de textura 3D)
    vox.transpose(2, 1, 0).tofile(os.path.join(OUTDIR, "helmet_vox.bin"))
    with open(os.path.join(OUTDIR, "helmet_vox.json"), "w") as f:
        json.dump({"size": args.size, "source": os.path.basename(args.model),
                   "rot_y": args.rot_y, "rot_x": args.rot_x}, f)
    print(f"voxels {args.size}³: superfície {nsurf}, sólido {nsolid} -> {OUTDIR}/helmet_vox.bin")


if __name__ == "__main__":
    main()

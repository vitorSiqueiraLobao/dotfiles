#!/usr/bin/env python3
# ARES // gerador do wallpaper animado (shader GLSL para mpv/mpvpaper)
# Cena: capacete coríntio de Ares em ASCII 3D (estilo "donut ASCII"), girando,
# sobre uma grade em perspectiva + horizonte em ASCII e matriz de códigos no céu.
#
# Duas etapas na GPU:
#   1. ARESCELLS: uma "célula" por caractere (12x16 px). Raymarch do capacete,
#      grade e céu -> escolhe o caractere, a cor e o brilho de cada célula.
#   2. desenha o caractere com uma fonte pixelada 5x7 embutida (escala 2x).
#
# Uso: python3 tools/gen_wallpaper_shader.py  -> home/.config/ares/wallpaper/ares_helmet.glsl

import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "home", ".config", "ares",
                   "wallpaper", "ares_helmet.glsl")

# --- Fonte 5x7 ---------------------------------------------------------------
# Ordem importa: os índices são usados no shader.
RAMP = " .,-~:;=!*#$@"          # 0..12: do escuro ao claro (iluminação do capacete)
GLYPHS = {
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".....", "..#.."],
    ",": [".....", ".....", ".....", ".....", ".....", "..#..", ".#..."],
    "-": [".....", ".....", ".....", ".###.", ".....", ".....", "....."],
    "~": [".....", ".....", ".##.#", "#..#.", ".....", ".....", "....."],
    ":": [".....", "..#..", ".....", ".....", "..#..", ".....", "....."],
    ";": [".....", "..#..", ".....", ".....", "..#..", "..#..", ".#..."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
    "#": [".#.#.", "#####", ".#.#.", ".#.#.", "#####", ".#.#.", "....."],
    "$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
    "@": [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."],
    # dígitos e letras hex (matriz do céu)
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    # grade
    "/": ["....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."],
    "\\": ["#....", ".#...", ".#...", "..#..", "...#.", "...#.", "....#"],
    "|": ["..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
}
ORDER = list(RAMP) + list("0123456789ABCDEF") + ["/", "\\", "|", "_"]
IDX = {c: i for i, c in enumerate(ORDER)}


def glyph_table():
    rows = []
    for ch in ORDER:
        for line in GLYPHS[ch]:
            rows.append(int(line.replace("#", "1").replace(".", "0"), 2))
    return ", ".join(str(r) for r in rows), len(ORDER)


table, nglyphs = glyph_table()

SHADER = r"""// ARES // wallpaper animado: capacete de Ares em ASCII 3D
// GERADO por tools/gen_wallpaper_shader.py — edite o gerador, não este arquivo.

VOXEL_TEXTURE_BLOCK//!HOOK MAIN
//!BIND HOOKED
VOXEL_BIND//!SAVE ARESCELLS
//!WIDTH HOOKED.w 12 /
//!HEIGHT HOOKED.h 16 /
//!COMPONENTS 4
//!DESC ARES cells (cena 3D -> caractere por célula)

// --- Ajustes --------------------------------------------------------------
#define SPIN_SPEED   0.35   // giro do capacete (rad/s)
#define GRID_SPEED   0.25   // velocidade da grade
#define HORIZON      0.70   // altura do horizonte (0 = topo, 1 = base)
#define HELMET_Y     0.40   // centro vertical do capacete
#define HELMET_SIZE  0.26   // tamanho relativo à altura da tela

const vec3 LIGHT = normalize(vec3(-0.5, 0.6, 0.8));

#ifdef ARES_VOXEL
#define VOX_ZOOM     0.25   // zoom da câmera no modelo (menor = maior)
#define CLEAR_RADIUS 1.10
float vox(vec3 p) { return texture(ARESVOX, p * 0.5 + 0.5).r; }
#else
#define CLEAR_RADIUS 1.25
#endif

float T() { return float(frame) / 30.0; }
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

float sdBox(vec3 p, vec3 b) { vec3 q = abs(p) - b; return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0); }
float sdEllipsoid(vec3 p, vec3 r) { float k0 = length(p / r); float k1 = length(p / (r * r)); return k0 * (k0 - 1.0) / k1; }

// material: 1 = casco, 2 = crista, 3 = interior
float helmet(vec3 p, out int mat) {
    vec3 q = p;
    // bochechas afinam para o queixo; nuca abre um pouco para trás
    if (q.y < 0.0) {
        float k = -q.y;
        q.x /= 1.0 - 0.32 * pow(k, 1.2) * smoothstep(-0.3, 0.8, q.z);   // bochechas afinando
        q.z -= 0.45 * max(0.0, -q.z) * max(0.0, k - 0.15);               // nuca abrindo
    }
    float outer = sdEllipsoid(q, vec3(0.9, 1.15, 1.0));
    float shell = abs(outer) - 0.07;
    shell = max(shell, -p.y - 1.20);                       // corte da base
    // abertura em T: fendas dos olhos + boca, com a proteção do nariz
    float nose  = sdBox(p - vec3(0.0, -0.18, 0.8), vec3(0.075, 0.32, 0.7));
    float eyes  = max(sdBox(p - vec3(0.0, 0.03, 0.8), vec3(0.80, 0.13, 0.6)), -nose);
    float mouth = max(sdBox(p - vec3(0.0, -0.80, 0.8), vec3(0.27, 0.62, 0.6)), -nose);
    shell = max(shell, -min(eyes, mouth));
    // crista: lâmina em arco sobre o topo, da testa até a nuca
    vec3 c = p - vec3(0.0, 0.10, -0.05);
    float r = length(c.yz);
    float ang = atan(c.z, c.y);                            // 0 = topo, + frente
    float h = 0.62 * smoothstep(0.80, 0.15, ang) * smoothstep(-2.6, -1.5, ang);
    float band = max(1.10 - r, r - (1.10 + h));
    float crest = max(max(abs(c.x) - 0.11, band), max(ang - 0.80, -2.6 - ang));
    if (crest < shell) { mat = 2; return crest; }
    mat = outer < 0.0 ? 3 : 1;
    return shell;
}

float sceneD(vec3 p) { int m; return helmet(p, m); }

vec3 normalAt(vec3 p) {
    const vec2 e = vec2(0.003, -0.003);
    return normalize(e.xyy * sceneD(p + e.xyy) + e.yyx * sceneD(p + e.yyx) +
                     e.yxy * sceneD(p + e.yxy) + e.xxx * sceneD(p + e.xxx));
}

mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0, -s, 0, 1, 0, s, 0, c); }
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1, 0, 0, 0, c, s, 0, -s, c); }

// saída: x = índice do caractere, y = brilho, z = cor (0 fundo, 1 vermelho, 2 ciano)
vec4 cellOut(int g, float bright, int col) { return vec4(float(g) / 64.0, bright, float(col) / 4.0, 1.0); }

vec4 hook() {
    vec2 cells = floor(HOOKED_size / vec2(12.0, 16.0)); // HOOKED_size = imagem de entrada; uma célula = 12x16 px
    vec2 cell = floor(HOOKED_pos * cells);
    vec2 px = (cell + 0.5) * vec2(12.0, 16.0);     // centro da célula em pixels
    vec2 scr = vec2(cells.x * 12.0, cells.y * 16.0);
    float t = T();

#ifdef ARES_VOXEL
    // --- capacete do modelo 3D (voxels 64³ embutidos) -----------------------
    {
        vec2 uv = (px - vec2(scr.x * 0.5, scr.y * HELMET_Y)) / (scr.y * HELMET_SIZE);
        uv.y = -uv.y;
        vec3 ro = vec3(0.0, 0.0, 4.2);
        vec3 rd = normalize(vec3(uv * VOX_ZOOM, -1.0));
        mat3 R = rotY(t * SPIN_SPEED) * rotX(-0.10 + 0.05 * sin(t * 0.4));
        mat3 Ri = transpose(R);
        vec3 o = Ri * ro, dir = Ri * rd;
        // entra e sai da caixa [-1, 1]³ do modelo
        vec3 inv = 1.0 / dir;
        vec3 t0 = (-1.0 - o) * inv, t1 = (1.0 - o) * inv;
        float tn = max(max(min(t0.x, t1.x), min(t0.y, t1.y)), min(t0.z, t1.z));
        float tf = min(min(max(t0.x, t1.x), max(t0.y, t1.y)), max(t0.z, t1.z));
        if (tf > max(tn, 0.0)) {
            float stp = 1.0 / 128.0;
            for (float d = max(tn, 0.0); d < tf; d += stp) {
                vec3 p = o + dir * d;
                if (vox(p) > 0.5) {
                    // refina o ponto de contato
                    float a0 = d - stp, a1 = d;
                    for (int k = 0; k < 5; k++) { float m = 0.5 * (a0 + a1); if (vox(o + dir * m) > 0.5) a1 = m; else a0 = m; }
                    p = o + dir * a1;
                    const float e = 1.0 / 64.0;
                    vec3 g = vec3(vox(p + vec3(e, 0, 0)) - vox(p - vec3(e, 0, 0)),
                                  vox(p + vec3(0, e, 0)) - vox(p - vec3(0, e, 0)),
                                  vox(p + vec3(0, 0, e)) - vox(p - vec3(0, 0, e)));
                    vec3 nObj = -normalize(g + 1e-6);
                    // superfície interna (vista pelas aberturas): visor aceso em ciano
                    if (p.y < 0.15 && length(p.xz) < 0.75 && dot(nObj, p - vec3(0.0, -0.1, 0.0)) < -0.15)
                        return cellOut(G_AT, 0.9, 2);
                    vec3 n = R * nObj;
                    float L = clamp(dot(n, LIGHT), 0.0, 1.0);
                    int gi = int(clamp(L * 12.0, 1.0, 12.0));
                    return cellOut(gi, 0.30 + 0.70 * L, 1);
                }
            }
        }
    }
#else
    // --- capacete (raymarch) ---------------------------------------------
    vec2 uv = (px - vec2(scr.x * 0.5, scr.y * HELMET_Y)) / (scr.y * HELMET_SIZE);
    uv.y = -uv.y;
    vec3 ro = vec3(0.0, 0.0, 4.2);
    vec3 rd = normalize(vec3(uv * 0.42, -1.0));
    mat3 R = rotY(t * SPIN_SPEED) * rotX(-0.12 + 0.05 * sin(t * 0.4));
    mat3 Ri = transpose(R);
    float d = 0.0;
    if (abs(uv.x) < 1.6 && abs(uv.y) < 1.6) {
        for (int i = 0; i < 120; i++) {
            vec3 p = Ri * (ro + rd * d);
            float s = sceneD(p) * 0.5;
            if (s < 0.002) {
                int mat; helmet(p, mat);
                vec3 n = R * normalAt(p);
                if (dot(n, rd) > 0.0) n = -n;
                float L = clamp(dot(n, LIGHT), 0.0, 1.0);
                // interior visto pelas fendas: olhos brilhando em ciano
                // (aberturas ficam vazadas; só os olhos acendem)
                if (mat == 3) {
                    bool eyeBand = abs(p.y - 0.03) < 0.16 && p.z < 0.35;
                    return eyeBand ? cellOut(G_AT, 1.0, 2) : cellOut(0, 0.0, 0);
                }
                if (mat == 2) L = 0.35 + 0.65 * L;      // crista sempre visível, mesmo de lado
                int g = int(clamp(L * 12.0, 1.0, 12.0));
                float b = 0.30 + 0.70 * L;
                return cellOut(g, mat == 2 ? min(1.0, b + 0.1) : b, 1);
            }
            d += s;
            if (d > 9.0) break;
        }
    }

#endif

    // --- chão: grade em perspectiva ------------------------------------------
    float hy = scr.y * HORIZON;
    if (px.y > hy) {
        float span = scr.y - hy;
        float dy = (px.y - hy) / span;                   // 0 no horizonte, 1 na base
        float fade = 0.25 + 0.75 * smoothstep(0.0, 0.6, dy);
        // linhas que convergem para o centro: x no "mundo" = x na tela / profundidade
        float wx = (px.x - scr.x * 0.5) / scr.y / max(dy, 0.03) * 3.0;
        float cellWX = 12.0 / scr.y / max(dy, 0.03) * 3.0;  // quanto do mundo cabe numa célula
        float nearest = floor(wx + 0.5);
        if (abs(wx - nearest) < 0.5 * cellWX && cellWX < 0.6) {
            float X = nearest;                           // inclinação da linha na tela
            int g = abs(X) < 0.5 ? G_PIPE : (abs(X) > 3.5 ? G_DASH : (X < 0.0 ? G_SLASH : G_BSLASH));
            return cellOut(g, 0.85 * fade, 1);
        }
        // linhas horizontais vindo em direção à tela: profundidade z = 1/dy
        float z = 1.0 / max(dy, 0.02);
        float zrow = 16.0 / span / max(dy * dy, 0.0004);     // quanto de z cabe numa célula
        float zl = fract(z * 0.5 - t * GRID_SPEED);
        if (zrow < 0.45 && zl < zrow * 0.5) return cellOut(G_DASH, fade, 1);   // some perto do horizonte
        return cellOut(0, 0.0, 0);
    }
    // linha do horizonte
    if (abs(px.y - hy) < 9.0) return cellOut(G_UNDER, 0.9, 2);

    // --- céu: matriz de códigos hex à deriva ---------------------------------
    vec2 uvm = (px - vec2(scr.x * 0.5, scr.y * HELMET_Y)) / (scr.y * HELMET_SIZE);
    if (length(uvm * vec2(0.85, 0.75)) < CLEAR_RADIUS) return cellOut(0, 0.0, 0);   // espaço em volta do capacete
    float drift = floor(t * 1.2);
    vec2 tok = vec2(floor((cell.x + drift) / 3.0), cell.y);
    float slot = mod(cell.x + drift, 3.0);
    if (slot < 2.0 && mod(cell.y, 2.0) < 1.0) {
        float hsh = hash(tok + floor(t / 7.0) * 0.13 * step(0.97, hash(tok * 1.7)));
        int code = int(hsh * 6.0);                         // 1C E9 55 BD 7A FF
        int a = code == 0 ? G_1 : code == 1 ? G_E : code == 2 ? G_5 : code == 3 ? G_B : code == 4 ? G_7 : G_F;
        int b = code == 0 ? G_C : code == 1 ? G_9 : code == 2 ? G_5 : code == 3 ? G_D : code == 4 ? G_A : G_F;
        float wave = 0.5 + 0.5 * sin(cell.x * 0.05 + cell.y * 0.35 + t * 0.6);
        float glow = 1.0 - smoothstep(0.0, scr.y * 0.9, length(px - vec2(scr.x * 0.5, hy)));
        float bright = 0.07 + 0.16 * wave + 0.18 * glow;
        bool cyan = hash(tok + floor(t * 0.5)) > 0.995;
        return cellOut(slot < 1.0 ? a : b, bright, cyan ? 2 : 1);
    }
    return cellOut(0, 0.0, 0);
}

//!HOOK MAIN
//!BIND HOOKED
//!BIND ARESCELLS
//!DESC ARES glyphs (desenha os caracteres)

const int GLY[GLYPH_COUNT * 7] = int[](GLYPH_TABLE);

vec4 hook() {
    vec2 px = floor(HOOKED_pos * HOOKED_size);
    vec2 cell = floor(px / vec2(12.0, 16.0));
    vec2 local = px - cell * vec2(12.0, 16.0);
    vec4 c = ARESCELLS_tex((cell + 0.5) / ARESCELLS_size);
    int g = int(c.x * 64.0 + 0.5);
    int col = int(c.z * 4.0 + 0.5);
    vec3 bg = vec3(0.031, 0.024, 0.039);                   // #08060a
    if (col == 0 || g == 0) return vec4(bg, 1.0);
    // glifo 5x7 em escala 2x, com 1 px de margem: 10x14 dentro de 12x16
    int gx = int(local.x - 1.0) / 2, gy = int(local.y - 1.0) / 2;
    if (local.x < 1.0 || local.y < 1.0 || gx > 4 || gy > 6) return vec4(bg, 1.0);
    int bits = GLY[g * 7 + gy];
    bool on = ((bits >> (4 - gx)) & 1) == 1;
    vec3 tint = col == 2 ? vec3(0.0, 0.94, 1.0) : vec3(1.0, 0.12, 0.24);   // ciano / vermelho
    return vec4(on ? mix(bg, tint, c.y) : bg, 1.0);
}
"""

NAMES = {"G_PIPE": "|", "G_SLASH": "/", "G_BSLASH": "\\", "G_UNDER": "_", "G_AT": "@", "G_DOT": ".",
         "G_DASH": "-", **{f"G_{c}": c for c in "0123456789ABCDEF"}}
VOX = os.path.join(os.path.dirname(OUT), "helmet_vox.bin")
if os.path.exists(VOX):
    import json
    meta = json.load(open(os.path.join(os.path.dirname(OUT), "helmet_vox.json")))
    n = meta["size"]
    data = open(VOX, "rb").read()
    assert len(data) == n ** 3
    block = (f"// Modelo: \"3D Spartan Helmet - High Poly\" por Manix3D (Sketchfab), CC BY 4.0\n"
             f"// https://sketchfab.com/3d-models/3d-spartan-helmet-high-poly-25e66a8915254fbc9402b0ef96a90554\n"
             f"// convertido em voxels {n}³ por tools/voxelize_model.py\n"
             f"//!TEXTURE ARESVOX\n//!SIZE {n} {n} {n}\n//!FORMAT r8\n//!FILTER LINEAR\n//!BORDER CLAMP\n"
             f"{data.hex()}\n\n")
    SHADER_SRC = SHADER.replace("VOXEL_TEXTURE_BLOCK", block).replace("VOXEL_BIND", "//!BIND ARESVOX\n")
    SHADER_SRC = SHADER_SRC.replace("const vec3 LIGHT", "#define ARES_VOXEL\nconst vec3 LIGHT", 1)
    print(f"modo modelo 3D: voxels {n}³ embutidos")
else:
    SHADER_SRC = SHADER.replace("VOXEL_TEXTURE_BLOCK", "").replace("VOXEL_BIND", "")
    print("modo procedural (sem helmet_vox.bin)")
shader = SHADER_SRC.replace("GLYPH_TABLE", table).replace("GLYPH_COUNT", str(nglyphs))
for name in sorted(NAMES, key=len, reverse=True):  # G_BSLASH antes de G_B etc.
    shader = shader.replace(name, str(IDX[NAMES[name]]))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    f.write(shader)
print(f"{os.path.relpath(OUT)}: {nglyphs} glifos, {len(shader)} bytes")

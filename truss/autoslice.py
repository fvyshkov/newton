#!/usr/bin/env python3
"""
Автономная нарезка для Bambu H2D без GUI («трюк с проектом-шаблоном»).

Проблема: CLI BambuStudio (≤2.7) не умеет собрать конфиг двухсопельного H2D
из профилей — валится на маппинге филамента. Но он отлично ПЕРЕнарезает
готовый проект .3mf, в котором конфиг уже лежит целиком.

Рецепт:
  1. CLI собирает проект из STL (геометрия + арранж) — это работает;
  2. в собранный .3mf пересаживается Metadata/project_settings.config из
     ШАБЛОНА — проекта, один раз сохранённого из GUI (570 ключей, включая
     filament_map / nozzle_volume_type);
  3. поверх пересаженного конфига применяются overrides (стенки, заполнение,
     поддержки, шов…);
  4. CLI нарезает результат → .gcode.3mf, готовый к заливке на принтер.

⚠️ Грабли CLI: --export-3mf принимает ТОЛЬКО относительное имя (абсолютный
путь склеивается с outputdir), а без --outputdir пишет ВНУТРЬ бандла
приложения и ломает подпись (macOS «damaged»). Тут это учтено.

Пример:
  python3 autoslice.py --out plate3.gcode.3mf \
      --set wall_loops=3 --set sparse_infill_density=30% \
      --set enable_support=0 --set seam_position=random \
      print_queue/07_*.stl print_queue/08_*.stl print_queue/08_*.stl
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

STUDIO = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
PROFILES = Path("/Applications/BambuStudio.app/Contents/Resources/profiles/BBL")
HERE = Path(__file__).parent
TEMPLATE = HERE / "print_queue" / "03_Rocker_ring_segment_x4.3mf"  # GUI-шаблон

MACHINE = PROFILES / "machine" / "Bambu Lab H2D 0.4 nozzle.json"
PROCESS = PROFILES / "process" / "0.20mm Standard @BBL H2D.json"
FILAMENT = PROFILES / "filament" / "Bambu PETG HF @BBL H2D 0.4 nozzle.json"


def run(cmd, workdir):
    r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    fatal = [l for l in (r.stdout + r.stderr).splitlines()
             if "error" in l.lower() and "T command" not in l and "ZFiller" not in l]
    return r.returncode, fatal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stls", nargs="+", help="STL файлы (повтор = ещё экземпляр)")
    ap.add_argument("--out", required=True, help="имя результата *.gcode.3mf")
    ap.add_argument("--template", default=str(TEMPLATE), help="GUI-проект-шаблон")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VAL",
                    help="override ключа конфига (можно многократно)")
    ap.add_argument("--outdir", default=str(HERE / "print_queue" / "sliced"))
    args = ap.parse_args()

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="autoslice_"))

    # 0. посадка на стол (z=0) + РАССТАНОВКА ПО СЕТКЕ с зазором
    #    (авто-arrange BambuStudio кладёт детали внахлёст → конфликт; раскладываем
    #    сами по grid, центрируя каждую в свою ячейку, и отключаем --arrange)
    import trimesh, math
    meshes = [trimesh.load(str(Path(s).resolve())) for s in args.stls]
    n = len(meshes)
    BED_CX, BED_CY = 175.0, 160.0        # центр стола H2D (350×320)
    cols = math.ceil(math.sqrt(n))
    cell = max(max((m.bounds[1] - m.bounds[0])[:2]) for m in meshes) + 12.0
    rows = math.ceil(n / cols)
    if cols * cell > 350 or rows * cell > 320:
        sys.exit(f"НЕ ВЛЕЗЕТ: сетка {cols}×{rows}×{cell:.0f}мм > стол 350×320. "
                 f"Меньше деталей на плиту.")
    grounded = []
    for i, (s, m) in enumerate(zip(args.stls, meshes)):
        c = (m.bounds[0] + m.bounds[1]) / 2.0
        row, col = divmod(i, cols)
        cx = BED_CX + (col - (cols - 1) / 2.0) * cell
        cy = BED_CY + (row - (rows - 1) / 2.0) * cell
        m.apply_translation([cx - c[0], cy - c[1], -m.bounds[0][2]])
        g = tmp / f"grid_{i:02d}_{Path(s).stem}.stl"
        m.export(g)
        grounded.append(str(g))
    print(f"   раскладка: {n} дет., сетка {cols}кол, ячейка {cell:.0f}мм")

    # 1. проект из STL (--arrange 0: не трогать нашу сетку)
    code, errs = run([STUDIO,
                      "--load-settings", f"{MACHINE};{PROCESS}",
                      "--load-filaments", str(FILAMENT),
                      "--arrange", "0", "--orient", "0",
                      "--export-3mf", "raw.3mf", "--outputdir", str(tmp)]
                     + grounded, tmp)
    if not (tmp / "raw.3mf").exists():
        sys.exit(f"сборка проекта не удалась: {errs}")

    # 2+3. пересадка конфига шаблона + overrides
    cfg = json.loads(zipfile.ZipFile(args.template)
                     .read("Metadata/project_settings.config"))
    for kv in args.set:
        k, v = kv.split("=", 1)
        cfg[k] = v
    with zipfile.ZipFile(tmp / "raw.3mf") as zin, \
         zipfile.ZipFile(tmp / "tpl.3mf", "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            data = (json.dumps(cfg).encode()
                    if item == "Metadata/project_settings.config"
                    else zin.read(item))
            zout.writestr(item, data)

    # 4. нарезка
    code, errs = run([STUDIO, "--slice", "0",
                      "--export-3mf", args.out, "--outputdir", str(tmp),
                      str(tmp / "tpl.3mf")], tmp)
    result = tmp / args.out
    if not result.exists():
        sys.exit(f"нарезка не удалась: {errs}")

    final = outdir / args.out
    shutil.copy(result, final)
    z = zipfile.ZipFile(final)
    info = z.read("Metadata/slice_info.config").decode()
    import re
    stats = dict(re.findall(r'"(prediction|weight)" value="([^"]+)"', info))
    mins = int(stats.get("prediction", 0)) // 60
    # превью раскладки — рядом с результатом
    preview = final.with_suffix(".preview.png")
    with open(preview, "wb") as fh:
        fh.write(z.read("Metadata/plate_1.png"))
    print(f"OK → {final}")
    print(f"   ~{mins // 60}ч{mins % 60:02d}м, {stats.get('weight', '?')} г")
    print(f"   превью: {preview}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verificador de integridad de los conjuntos de evidencia (MANIFEST_SHA256.txt).

Uso:
    python3 tools/verificar_integridad.py
    python3 tools/verificar_integridad.py --caso caso-03-fraude-venta-vehiculo
    python3 tools/verificar_integridad.py --json

Codigos de salida:
    0  todos los archivos listados coinciden (y no hay extras, salvo --permitir-extra)
    1  hay archivos alterados o faltantes
    2  error de uso o de E/S
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

RAIZ_REPO = Path(__file__).resolve().parent.parent
CASOS_POR_DEFECTO = RAIZ_REPO / "casos"
MANIFIESTO = "MANIFEST_SHA256.txt"

OK = "OK"
ALTERADO = "ALTERADO"
FALTANTE = "FALTANTE"
SIN_MANIFEST = "SIN_MANIFEST"
ILEGIBLE = "ILEGIBLE"


def sha256_de(archivo: Path, bloque: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with archivo.open("rb") as fh:
        for trozo in iter(lambda: fh.read(bloque), b""):
            h.update(trozo)
    return h.hexdigest()


def leer_manifest(manifest: Path) -> List[Tuple[str, str]]:
    """Devuelve [(hash, ruta_relativa)] ignorando la cabecera y lineas vacias."""
    entradas: List[Tuple[str, str]] = []
    texto = manifest.read_text(encoding="utf-8-sig", errors="replace")
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.upper().startswith("SHA256"):
            continue
        partes = linea.split(None, 1)
        if len(partes) != 2:
            continue
        hash_esperado, ruta = partes[0].strip().lower(), partes[1].strip()
        if len(hash_esperado) != 64:
            continue
        entradas.append((hash_esperado, ruta.replace("\\", "/")))
    return entradas


def resolver(base: Path, ruta: str) -> Optional[Path]:
    """Resuelve una ruta del manifiesto tolerando prefijos heredados.

    El manifiesto del caso 01 se genero desde el directorio padre, por lo que sus
    rutas empiezan con un componente que ya no existe (PROYECTO_CASO_01_...).
    Se eliminan segmentos iniciales hasta que el archivo resuelva, sin tocar
    jamas el contenido del manifiesto (los bytes son evidencia).
    """
    segmentos = [s for s in ruta.split("/") if s not in ("", ".")]
    for i in range(len(segmentos)):
        candidato = base.joinpath(*segmentos[i:])
        if candidato.is_file():
            return candidato
    return None


def archivos_presentes(caso: Path) -> Dict[str, Path]:
    """Todos los archivos del caso (excepto el propio manifiesto), en rutas posix relativas."""
    presentes: Dict[str, Path] = {}
    for f in sorted(caso.rglob("*")):
        if not f.is_file() or f.name == MANIFIESTO:
            continue
        presentes[f.relative_to(caso).as_posix()] = f
    return presentes


def verificar_caso(caso: Path, permitir_extra: bool) -> Dict[str, object]:
    manifest = caso / MANIFIESTO
    resultado: Dict[str, object] = {
        "caso": caso.name,
        "estado": SIN_MANIFEST,
        "entradas": [],
        "totales": {OK: 0, ALTERADO: 0, FALTANTE: 0, ILEGIBLE: 0},
        "extras": [],
        "integridad_ok": False,
    }
    if not manifest.is_file():
        return resultado

    listadas: Dict[str, str] = {}
    for hash_esperado, ruta in leer_manifest(manifest):
        archivo = resolver(caso, ruta)
        if archivo is None:
            estado, hash_real = FALTANTE, ""
        else:
            listadas[archivo.relative_to(caso).as_posix()] = hash_esperado
            try:
                hash_real = sha256_de(archivo)
            except OSError:
                # Un archivo ilegible NO es un archivo integro: se reporta como hallazgo.
                estado, hash_real = ILEGIBLE, ""
            else:
                estado = OK if hash_real == hash_esperado else ALTERADO
        resultado["entradas"].append(
            {"estado": estado, "sha256": hash_real, "ruta": ruta}
        )
        resultado["totales"][estado] += 1  # type: ignore[index]

    presentes = archivos_presentes(caso)
    extras = sorted(p for p in presentes if p not in listadas)
    resultado["extras"] = extras
    resultado["estado"] = "VERIFICADO"
    totales = resultado["totales"]  # type: ignore[assignment]
    resultado["integridad_ok"] = (
        totales[ALTERADO] == 0
        and totales[FALTANTE] == 0
        and totales[ILEGIBLE] == 0
        and (permitir_extra or not extras)
    )
    return resultado


def imprimir_humano(resultados: List[Dict[str, object]]) -> None:
    fallo = False
    for r in resultados:
        nombre = r["caso"]
        print("=" * 78)
        print(f"CASO: {nombre}")
        print("=" * 78)
        if r["estado"] == SIN_MANIFEST:
            print(f"  {SIN_MANIFEST}: no se encontro {MANIFIESTO} en la carpeta.")
            fallo = True
            print()
            continue

        ancho_estado = max(len(e["estado"]) for e in r["entradas"])  # type: ignore[index]
        for e in r["entradas"]:  # type: ignore[index]
            marca = " " if e["estado"] == OK else "!"
            hash_corto = (e["sha256"][:12] + "...") if e["sha256"] else "-" * 15
            print(f" [{marca}] {e['estado']:<{ancho_estado}}  {hash_corto}  {e['ruta']}")

        for extra in r["extras"]:  # type: ignore[index]
            print(f" [!] NO_EN_MANIFEST      {'-' * 15}  {extra}")

        t = r["totales"]  # type: ignore[assignment]
        total = sum(t.values())  # type: ignore[arg-type]
        veredicto = "INTEGRO" if r["integridad_ok"] else "CON HALLAZGOS"
        print("-" * 78)
        print(
            f"  RESULTADO: CASO {veredicto} "
            f"({t[OK]}/{total} OK, {t[ALTERADO]} alterados, "
            f"{t[FALTANTE]} faltantes, {t[ILEGIBLE]} ilegibles, "
            f"{len(r['extras'])} no listados)"  # type: ignore[arg-type]
        )
        print()
        fallo = fallo or not r["integridad_ok"]

    total_casos = len(resultados)
    if fallo:
        print(f"VERIFICACION FALLIDA en {total_casos} caso(s) revisado(s).")
    else:
        print(f"VERIFICACION CORRECTA: {total_casos} caso(s) sin alteraciones.")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Verifica los manifiestos SHA256 de los casos forenses.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--casos-dir", default=str(CASOS_POR_DEFECTO),
                   help="Carpeta que contiene los casos (por defecto: casos/)")
    p.add_argument("--caso", action="append", default=None,
                   help="Nombre de caso a verificar (repetible). Por defecto: todos.")
    p.add_argument("--json", action="store_true", help="Salida JSON")
    p.add_argument("--permitir-extra", action="store_true",
                   help="No fallar si hay archivos que no estan en el manifiesto")
    p.add_argument("--quiet", action="store_true", help="Solo el veredicto final")
    args = p.parse_args(argv)

    base = Path(args.casos_dir).expanduser()
    if not base.is_dir():
        print(f"ERROR: no existe la carpeta de casos: {base}", file=sys.stderr)
        return 2

    casos = sorted(d for d in base.iterdir() if d.is_dir())
    if args.caso:
        seleccion = {c.lower() for c in args.caso}
        casos = [c for c in casos if c.name.lower() in seleccion]
        if not casos:
            print(f"ERROR: ningun caso coincide con {sorted(seleccion)}", file=sys.stderr)
            return 2
    if not casos:
        print(f"ERROR: no hay subcarpetas de caso en {base}", file=sys.stderr)
        return 2

    resultados = [verificar_caso(c, args.permitir_extra) for c in casos]

    if args.json:
        print(json.dumps({"casos": resultados}, indent=2, ensure_ascii=False))
    elif args.quiet:
        for r in resultados:
            t = r["totales"]
            total = sum(t.values())  # type: ignore[arg-type]
            print(f"{r['caso']}: {t[OK]}/{total} OK -> {'INTEGRO' if r['integridad_ok'] else 'HALLAZGOS'}")  # type: ignore[index]
    else:
        imprimir_humano(resultados)

    return 0 if all(r["integridad_ok"] for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())

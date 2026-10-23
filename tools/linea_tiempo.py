#!/usr/bin/env python3
"""Generador de linea de tiempo forense a partir de la evidencia legible por maquina.

Recorre los archivos CSV, JSON, TXT y HTML de cada caso, extrae marcas de tiempo,
las normaliza, las ordena cronologicamente y las exporta en Markdown, CSV o JSON.

Uso:
    python3 tools/linea_tiempo.py
    python3 tools/linea_tiempo.py --caso caso-03-fraude-venta-vehiculo
    python3 tools/linea_tiempo.py --formato csv > cronologia.csv
    python3 tools/linea_tiempo.py --desde 2026-05-09 --hasta 2026-05-13

Por defecto se excluye ARCHIVOS_PERSONALES (ruido sin valor probatorio directo);
use --incluir-ruido para incorporarlo.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

RAIZ_REPO = Path(__file__).resolve().parent.parent
CASOS_POR_DEFECTO = RAIZ_REPO / "casos"

EXTENSIONES = {".csv", ".json", ".txt", ".html", ".htm"}
EXCLUIR_SIEMPRE = {"MANIFEST_SHA256.txt", "00_LEEME_PRIMERO.txt", "INSTRUCCIONES_DEL_CASO.txt"}
RUIDO = "ARCHIVOS_PERSONALES"
COLUMNAS_FECHA = ("fecha_hora", "fecha", "fecha_relevante", "timestamp", "datetime")

RE_CHAT = re.compile(r"^\[(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})\]\s*([^:]{1,60}):\s*(.+)$")
RE_CAMPO_FECHA = re.compile(r"^Fecha:\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})", re.M)
RE_PUBLICADO = re.compile(r"Publicado:\s*(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})")
RE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?$")
RE_DMY = re.compile(r"^(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2}))?$")


def _dt(anio: str, mes: str, dia: str, hora: str = "00", minuto: str = "00") -> Optional[datetime]:
    try:
        return datetime(int(anio), int(mes), int(dia), int(hora), int(minuto))
    except ValueError:
        return None


def _parse_fecha(valor: str) -> Optional[datetime]:
    """Interpreta 'YYYY-MM-DD HH:MM' (ISO) o 'DD/MM/YYYY HH:MM' (espanol)."""
    valor = valor.strip()
    if not valor or " a " in valor:  # rangos como "2026-04-12 a 2026-04-15"
        return None
    m = RE_ISO.match(valor)
    if m:
        a, me, d, h, mi = m.groups()
        return _dt(a, me, d, h or "00", mi or "00")
    m = RE_DMY.match(valor)
    if m:
        d, me, a, h, mi = m.groups()
        return _dt(a, me, d, h or "00", mi or "00")
    return None


def _leer_texto(archivo: Path) -> str:
    return archivo.read_text(encoding="utf-8-sig", errors="replace")


def _evento(caso: str, cuando: datetime, tipo: str, descripcion: str, archivo: Path) -> Dict[str, str]:
    return {
        "caso": caso,
        "fecha_hora": cuando.strftime("%Y-%m-%d %H:%M"),
        "fecha_iso": cuando.isoformat(timespec="minutes"),
        "tipo": tipo,
        "descripcion": " ".join(descripcion.split()),
        "fuente_archivo": archivo.as_posix(),
    }


def eventos_de_csv(caso: str, archivo: Path) -> List[Dict[str, str]]:
    eventos: List[Dict[str, str]] = []
    try:
        filas = list(csv.DictReader(io.StringIO(_leer_texto(archivo))))
    except csv.Error:
        return eventos
    if not filas:
        return eventos
    col_fecha = next((c for c in filas[0] if c and c.strip().lower() in COLUMNAS_FECHA), None)
    if col_fecha is None:
        return eventos
    for fila in filas:
        cuando = _parse_fecha(fila.get(col_fecha) or "")
        if cuando is None:
            continue
        detalle = "; ".join(
            f"{k}={v}" for k, v in fila.items()
            if k != col_fecha and v not in (None, "")
        )
        eventos.append(_evento(caso, cuando, "csv", detalle, archivo))
    return eventos


def eventos_de_json(caso: str, archivo: Path) -> List[Dict[str, str]]:
    eventos: List[Dict[str, str]] = []
    try:
        datos = json.loads(_leer_texto(archivo))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return eventos

    # Contexto heredado de los campos escalares de nivel superior, para que cada
    # evento se pueda leer aislado (p. ej. "vehiculo: Riviera X4 2022").
    contexto = [
        str(valor)
        for valor in (datos.values() if isinstance(datos, dict) else [])
        if isinstance(valor, str) and len(valor) < 80
    ]

    def recorrer(nodo: object) -> None:
        if isinstance(nodo, dict):
            marca = nodo.get("fecha_hora") or nodo.get("fecha")
            if isinstance(marca, str):
                cuando = _parse_fecha(marca)
                if cuando:
                    partes = [
                        f"{k}: {v}" for k, v in nodo.items()
                        if k not in ("fecha_hora", "fecha") and not isinstance(v, (dict, list))
                    ]
                    if contexto:
                        partes.insert(0, "contexto: " + " / ".join(contexto))
                    eventos.append(_evento(caso, cuando, "json", "; ".join(partes), archivo))
                    return
            for valor in nodo.values():
                recorrer(valor)
        elif isinstance(nodo, list):
            for item in nodo:
                recorrer(item)

    recorrer(datos)
    return eventos


def eventos_de_txt(caso: str, archivo: Path) -> List[Dict[str, str]]:
    eventos: List[Dict[str, str]] = []
    texto = _leer_texto(archivo)

    for linea in texto.splitlines():
        m = RE_CHAT.match(linea.strip())
        if m:
            d, me, a, h, mi, autor, mensaje = m.groups()
            cuando = _dt(a, me, d, h, mi)
            if cuando:
                eventos.append(_evento(caso, cuando, "chat", f"{autor.strip()}: {mensaje}", archivo))

    m = RE_CAMPO_FECHA.search(texto)
    if m:
        d, me, a, h, mi = m.groups()
        cuando = _dt(a, me, d, h, mi)
        if cuando:
            remitente = re.search(r"^De:\s*(.+)$", texto, re.M)
            asunto = re.search(r"^Asunto:\s*(.+)$", texto, re.M)
            partes = []
            if remitente:
                partes.append(f"De: {remitente.group(1).strip()}")
            if asunto:
                partes.append(f"Asunto: {asunto.group(1).strip()}")
            eventos.append(_evento(caso, cuando, "correo", " | ".join(partes) or "mensaje", archivo))
    return eventos


def eventos_de_html(caso: str, archivo: Path) -> List[Dict[str, str]]:
    eventos: List[Dict[str, str]] = []
    texto = _leer_texto(archivo)
    for m in RE_PUBLICADO.finditer(texto):
        d, me, a, h, mi = m.groups()
        cuando = _dt(a, me, d, h, mi)
        if not cuando:
            continue
        titulo = re.search(r"<title>(.*?)</title>", texto, re.S | re.I)
        vendedor = re.search(r"Vendedor:\s*([^<]+)", texto, re.I)
        vin = re.search(r"VIN:\s*([^<]+)", texto, re.I)
        partes = []
        if titulo:
            partes.append(f"anuncio: {titulo.group(1).strip()}")
        if vendedor:
            partes.append(f"vendedor: {vendedor.group(1).strip()}")
        if vin:
            partes.append(f"VIN: {vin.group(1).strip()}")
        eventos.append(_evento(caso, cuando, "web", " | ".join(partes) or "pagina guardada", archivo))
    return eventos


EXTRACTORES = {
    ".csv": eventos_de_csv,
    ".json": eventos_de_json,
    ".txt": eventos_de_txt,
    ".html": eventos_de_html,
    ".htm": eventos_de_html,
}


def recolectar(caso_dir: Path, incluir_ruido: bool) -> List[Dict[str, str]]:
    eventos: List[Dict[str, str]] = []
    for archivo in sorted(caso_dir.rglob("*")):
        if not archivo.is_file():
            continue
        if archivo.name in EXCLUIR_SIEMPRE:
            continue
        if not incluir_ruido and RUIDO in archivo.relative_to(caso_dir).parts:
            continue
        extractor = EXTRACTORES.get(archivo.suffix.lower())
        if extractor is None:
            continue
        eventos.extend(extractor(caso_dir.name, archivo.relative_to(RAIZ_REPO)))
    return eventos


def filtrar(eventos: Iterable[Dict[str, str]], desde: Optional[str], hasta: Optional[str]) -> List[Dict[str, str]]:
    limite_inf = _parse_fecha(desde) if desde else None
    limite_sup = _parse_fecha(hasta) if hasta else None
    salida = []
    for e in eventos:
        cuando = datetime.fromisoformat(e["fecha_iso"])
        if limite_inf and cuando < limite_inf:
            continue
        if limite_sup and cuando > limite_sup:
            continue
        salida.append(e)
    return salida


def salida_md(resultados: Dict[str, List[Dict[str, str]]]) -> None:
    for caso, eventos in resultados.items():
        print(f"## {caso}")
        print()
        if not eventos:
            print("_Sin marcas de tiempo legibles._")
            print()
            continue
        print("| Fecha y hora | Tipo | Descripcion | Fuente |")
        print("|---|---|---|---|")
        for e in eventos:
            desc = e["descripcion"].replace("|", "\\|")
            print(f"| {e['fecha_hora']} | {e['tipo']} | {desc} | `{e['fuente_archivo']}` |")
        print()
        por_tipo: Dict[str, int] = {}
        for e in eventos:
            por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
        resumen = ", ".join(f"{k}={v}" for k, v in sorted(por_tipo.items()))
        print(f"- Total de eventos: **{len(eventos)}** ({resumen})")
        print(f"- Rango temporal: **{eventos[0]['fecha_hora']}** a **{eventos[-1]['fecha_hora']}**")
        print()


def salida_csv(resultados: Dict[str, List[Dict[str, str]]]) -> None:
    escritor = csv.writer(sys.stdout)
    escritor.writerow(["caso", "fecha_hora", "fecha_iso", "tipo", "descripcion", "fuente_archivo"])
    for eventos in resultados.values():
        for e in eventos:
            escritor.writerow([e["caso"], e["fecha_hora"], e["fecha_iso"], e["tipo"],
                               e["descripcion"], e["fuente_archivo"]])


def salida_json(resultados: Dict[str, List[Dict[str, str]]]) -> None:
    carga = {"casos": [{"caso": c, "total": len(ev), "eventos": ev} for c, ev in resultados.items()]}
    print(json.dumps(carga, indent=2, ensure_ascii=False))


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Construye la cronologia forense de cada caso a partir de su evidencia.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--casos-dir", default=str(CASOS_POR_DEFECTO))
    p.add_argument("--caso", action="append", default=None, help="Caso a procesar (repetible)")
    p.add_argument("--formato", choices=("md", "csv", "json"), default="md")
    p.add_argument("--desde", help="Filtro inferior (YYYY-MM-DD o DD/MM/YYYY)")
    p.add_argument("--hasta", help="Filtro superior (YYYY-MM-DD o DD/MM/YYYY)")
    p.add_argument("--incluir-ruido", action="store_true",
                   help="Incluir ARCHIVOS_PERSONALES (sin valor probatorio directo)")
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
        print("ERROR: no se selecciono ningun caso valido", file=sys.stderr)
        return 2

    # Un filtro que no se puede interpretar no debe ignorarse en silencio:
    # produciria una cronologia incompleta que parece correcta.
    for etiqueta, valor in (("--desde", args.desde), ("--hasta", args.hasta)):
        if valor and _parse_fecha(valor) is None:
            print(f"ERROR: {etiqueta} no es una fecha valida: {valor!r} "
                  f"(formatos aceptados: YYYY-MM-DD o DD/MM/YYYY)", file=sys.stderr)
            return 2

    resultados: Dict[str, List[Dict[str, str]]] = {}
    for caso_dir in casos:
        eventos = filtrar(recolectar(caso_dir, args.incluir_ruido), args.desde, args.hasta)
        eventos.sort(key=lambda e: (e["fecha_iso"], e["fuente_archivo"]))
        resultados[caso_dir.name] = eventos

    {"md": salida_md, "csv": salida_csv, "json": salida_json}[args.formato](resultados)
    return 0


if __name__ == "__main__":
    sys.exit(main())

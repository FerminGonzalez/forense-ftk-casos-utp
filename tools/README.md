# Herramientas

Dos scripts de línea de comandos, **solo biblioteca estándar** de Python (3.9+). Sin `pip install`.

## `verificar_integridad.py`

Recalcula el SHA-256 de cada archivo listado en `MANIFEST_SHA256.txt` y lo compara con el valor de referencia.

| Estado | Significado |
|---|---|
| `OK` | El archivo es idéntico al adquirido. |
| `ALTERADO` | El archivo cambió después de la adquisición. |
| `FALTANTE` | El manifiesto lo declara, pero no está en la carpeta. |
| `NO_EN_MANIFEST` | Está en la carpeta y nadie lo declaró (evidencia sembrada o filtrada). |
| `ILEGIBLE` | Existe, pero el archivo no se pudo leer (permisos/IO). Se trata como hallazgo, nunca como íntegro. |

```bash
python3 tools/verificar_integridad.py                        # todos los casos
python3 tools/verificar_integridad.py --quiet                # una línea por caso
python3 tools/verificar_integridad.py --json                 # integrable
python3 tools/verificar_integridad.py --caso caso-03-fraude-venta-vehiculo
python3 tools/verificar_integridad.py --permitir-extra       # no fallar por archivos extra
```

Salida esperada en este repositorio: `caso-01 (18/18 OK)` y `caso-03 (21/21 OK)`.
Códigos de salida: `0` íntegro · `1` hallazgos · `2` error de uso.

## `linea_tiempo.py`

Extrae marcas de tiempo de CSV, JSON, TXT y HTML, las normaliza y las ordena.

Formatos reconocidos en los datos de estos casos:

- CSV con columna `fecha_hora` / `fecha` / `fecha_relevante` → `2026-05-12 10:48`
- Chat → `[10/05/2026 07:52] Marco: …`
- Correo → `Fecha: 09/05/2026 08:40` (más `De:` y `Asunto:`)
- Página web guardada → `Publicado: 10/05/2026 08:46`
- JSON con arreglo `eventos` → `fecha_hora` + `ubicacion` / `fuente`

```bash
python3 tools/linea_tiempo.py                                  # Markdown
python3 tools/linea_tiempo.py --formato csv  > cronologia.csv
python3 tools/linea_tiempo.py --formato json
python3 tools/linea_tiempo.py --desde 2026-05-12 --hasta 2026-05-13
python3 tools/linea_tiempo.py --incluir-ruido                  # incluye ARCHIVOS_PERSONALES
```

Por defecto excluye `ARCHIVOS_PERSONALES`: archivos del disco sin relación con el hecho investigado. Incluirlos demuestra por qué el triage previo cambia la conclusión.

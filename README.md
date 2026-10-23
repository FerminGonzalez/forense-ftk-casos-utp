# Forense FTK — Casos 01 y 03 (UTP)

[![Integridad de la evidencia](https://github.com/FerminGonzalez/forense-ftk-casos-utp/actions/workflows/integridad.yml/badge.svg)](https://github.com/FerminGonzalez/forense-ftk-casos-utp/actions/workflows/integridad.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Licencia](https://img.shields.io/badge/c%C3%B3digo-MIT-green)
![Datos](https://img.shields.io/badge/datos-ficticios%20%C2%B7%20uso%20educativo-orange)

Dos casos de informática forense **completamente ficticios**, empaquetados como conjuntos de evidencia con manifiesto SHA-256, más las herramientas que verifican su integridad y reconstruyen su cronología.

El objetivo no es solo entregar dos laboratorios resueltos: es demostrar el flujo de trabajo real de una adquisición forense — **preservar bytes → verificar hashes → triangular fuentes → construir la línea de tiempo → concluir**.

> ⚠️ Todo el contenido es ficticio. Ningún nombre, VIN, placa, cuenta, finca o entidad corresponde a datos reales ni a documentos válidos.

---

## Contenido

```
forense-ftk-casos-utp/
├── casos/
│   ├── caso-01-venta-fraudulenta-propiedad/
│   │   ├── MANIFEST_SHA256.txt          # 18 hashes de referencia
│   │   ├── INSTRUCCIONES_DEL_CASO.txt   # consigna del peritaje
│   │   ├── EVIDENCIAS/                  # 01_Contratos … 07_Inventario
│   │   └── ARCHIVOS_PERSONALES/         # ruido sin valor probatorio directo
│   └── caso-03-fraude-venta-vehiculo/
│       ├── MANIFEST_SHA256.txt          # 21 hashes de referencia
│       ├── INSTRUCCIONES_DEL_CASO.txt
│       ├── EVIDENCIAS/                  # 01_Documentos … 06_Borradores
│       └── ARCHIVOS_PERSONALES/
├── tools/
│   ├── verificar_integridad.py          # valida los manifiestos SHA-256
│   └── linea_tiempo.py                  # cronología forense multi-formato
├── docs/                                # consignas, informe resuelto y guías FTK
└── .github/workflows/integridad.yml     # CI: verifica hashes en cada push
```

Los casos mezclan deliberadamente **formatos distintos** (`.docx`, `.pdf`, `.csv`, `.json`, `.html`, `.jpg`, `.png`, `.txt`) para obligar al analista a no depender de una sola fuente ni de una sola herramienta.

---

## 1. Verificar la integridad

Ningún análisis forense vale nada si la evidencia no es la misma que se adquirió. El verificador recalcula SHA-256 y compara contra el manifiesto.

```bash
python3 tools/verificar_integridad.py
```

```
==============================================================================
CASO: caso-03-fraude-venta-vehiculo
==============================================================================
 [ ] OK  a69aae71bde3...  00_LEEME_PRIMERO.txt
 [ ] OK  8dbb47d7a950...  ARCHIVOS_PERSONALES/Foto_Piscina_Ficticia.jpg
 [ ] OK  ac4c09dc85d9...  EVIDENCIAS/01_Documentos/Contrato_Compraventa_Vehiculo.docx
                                              … 21 archivos …
------------------------------------------------------------------------------
  RESULTADO: CASO INTEGRO (21/21 OK, 0 alterados, 0 faltantes, 0 no listados)

VERIFICACION CORRECTA: 2 caso(s) sin alteraciones.
```

Salida esperada en este repositorio: **39/39 hashes válidos** (18 + 21).

Opciones útiles:

```bash
python3 tools/verificar_integridad.py --quiet        # una línea por caso
python3 tools/verificar_integridad.py --json         # integrable en otro script
python3 tools/verificar_integridad.py --caso caso-03-fraude-venta-vehiculo
```

Códigos de salida: `0` íntegro · `1` hay archivos alterados o faltantes · `2` error de uso.

Además de `ALTERADO` y `FALTANTE`, el verificador marca `NO_EN_MANIFEST`: archivos presentes en la carpeta que nadie declaró. Ese caso — evidencia sembrada o filtrada — es justamente el que un análisis descuidado pasa por alto.

> **Detalle técnico documentado:** el manifiesto del caso 01 fue generado desde el directorio padre, por lo que sus rutas arrastran un prefijo `PROYECTO_CASO_01_VENTA_FRAUDULENTA/` que ya no existe en el árbol. El verificador resuelve la ruta eliminando segmentos iniciales **sin modificar el manifiesto**, porque sus bytes también son evidencia.

## 2. Reconstruir la cronología

```bash
python3 tools/linea_tiempo.py
```

El generador recorre CSV, JSON, TXT y HTML, extrae las marcas de tiempo (`2026-05-12 10:48`, `[10/05/2026 07:52]`, `Fecha: 09/05/2026 08:40`, `Publicado: 10/05/2026 08:46`), normaliza el formato día-primero y ordena todo en una sola tabla.

```
| Fecha y hora | Tipo | Descripcion | Fuente |
|---|---|---|---|
| 2026-05-10 07:55 | chat | Marco: Sí, en el anuncio. En el contrato cambia los dos últimos a 91. | ...Chat_Vendedor_Intermediario.txt |
| 2026-05-10 08:30 | csv | vin_consultado=SIMULADO-VIN-0001; resultado=Propietaria Daniela Torres | ...Consultas_VIN.csv |
| 2026-05-10 08:46 | web | anuncio: Anuncio ficticio; vendedor: Marco Castillo; VIN: SIMULADO-VIN-0001 | ...Anuncio_Guardado.html |
| 2026-05-12 10:15 | csv | vin_consultado=SIMULADO-VIN-0091; resultado=Sin coincidencia | ...Consultas_VIN.csv |
| 2026-05-12 10:48 | csv | referencia=FIC-12051048; descripcion=Anticipo Andrés M.; entrada=9000.00 | ...Movimientos_Cuenta_Vendedor.csv |
| 2026-05-12 13:06 | csv | referencia=RET-FIC-1306; descripcion=Retiro de efectivo; salida=7500.00 | ...Movimientos_Cuenta_Vendedor.csv |
```

Resultado en este repositorio: **13 eventos** en el caso 01 y **15** en el caso 03.

```bash
python3 tools/linea_tiempo.py --formato csv  > cronologia.csv
python3 tools/linea_tiempo.py --formato json
python3 tools/linea_tiempo.py --desde 2026-05-12 --hasta 2026-05-13
python3 tools/linea_tiempo.py --incluir-ruido     # incluye ARCHIVOS_PERSONALES
```

Por defecto **se excluye `ARCHIVOS_PERSONALES`**: son archivos del disco que no se relacionan con el delito. Incluirlos (`--incluir-ruido`) añade eventos que no pertenecen al hecho investigado — útil para demostrar por qué el triage importa.

---

## Hallazgos — Caso 01: venta fraudulenta de propiedad

**Consigna:** determinar si la finca 18427 fue ofrecida a más de una persona, si el vendedor estaba autorizado y qué contradicciones existen en superficie, pagos y fechas.

Una sola finca, dos compradores, cuatro días:

| Fecha | Evento | Fuente |
|---|---|---|
| 2026-04-10 18:14 | «Usa las mismas fotos de la finca 18427 para los dos interesados» | `Chat_Vendedor_Asistente.txt` |
| 2026-04-12 11:05 | Anticipo de Luis H. por B/. 15,000.00 | `Movimientos_Cuenta.csv` |
| 2026-04-14 16:42 | Anticipo de Marta R. por B/. 18,000.00 (saldo acumulado 33,000) | `Movimientos_Cuenta.csv` |
| 2026-04-15 08:20 | Retiro de B/. 28,000.00, dejando B/. 5,000.00 | `Movimientos_Cuenta.csv` |
| 2026-04-15 08:25 | «Retiré casi todo. Guarda los borradores fuera del correo» | `Chat_Vendedor_Asistente.txt` |
| 2026-04-15 10:26 | La notaría confirma que **no existe poder vigente** ni escritura protocolizada a favor de ninguno de los dos | `Correo_Notaria.txt` |

**Conclusión:** la finca fue ofrecida y cobrada dos veces en 48 horas, sin autorización del propietario. El contenido del borrador `Borrador_Reparto_Comisiones.txt` (`15,000 + 18,000 = 33,000`, retiro inmediato de 28,000, comisión de 2,000 al asistente) no es una hipótesis del analista: es la contabilidad del propio sospechoso, y coincide al centavo con los movimientos bancarios.

## Hallazgos — Caso 03: fraude en la venta de un vehículo

**Consigna:** determinar si hay indicios de fraude, cuál VIN está mejor sustentado, quién es el propietario, qué pasó con el dinero y cómo se relacionan imágenes, comunicaciones y registros.

| VIN | Dónde aparece | Valoración |
|---|---|---|
| `SIMULADO-VIN-0001` | Anuncio web, consulta del intermediario, consulta del inspector, correo de la aseguradora | **Sustentado**: coincide con la propietaria registrada (Daniela Torres) y con el reporte de sustracción |
| `SIMULADO-VIN-0091` | Contrato de compraventa, consulta del comprador | **Sin respaldo**: la consulta devuelve «sin coincidencia» |

La secuencia es explícita en el chat del 10/05: se ordena publicar el VIN 0001 en el anuncio y **alterar los dos últimos dígitos a 91 en el contrato**. Cuatro horas antes, la aseguradora ya había confirmado que el vehículo fue reportado como sustraído el 08/05 a las 21:10.

El dinero sigue el mismo patrón que en el caso 01: anticipo de B/. 9,000.00 recibido a las 10:48 y **B/. 7,500.00 retirados en efectivo a las 13:06 del mismo día**. El archivo `Nota_Cambio_Identificacion.txt` enumera el plan completo: sustituir la terminación, cubrir la placa con adhesivo, retirar el anticipo el mismo día, no entregar el registro original.

**Conclusión:** venta de un vehículo con identificación alterada, sobre un bien reportado como sustraído, con el comprador inducido a error mediante documentación divergente. Los ocho archivos citados forman una cadena cerrada: chat → anuncio → consulta → contrato → pago → retiro → inspección → nota.

---

## Metodología

1. **Adquisición** — Imagen del dispositivo con FTK Imager, preservando el original (ver `docs/1_FTK_Imager_Create_Disk_Image_USB.pptx`).
2. **Montaje** — Lectura de la imagen como unidad de solo lectura (ver `docs/3_FTK_Imager_Image_Mounting_USB_Paso_a_Paso.pptx`).
3. **Integridad** — Cálculo y cotejo de SHA-256 contra el manifiesto antes de cualquier análisis (`tools/verificar_integridad.py`).
4. **Triage** — Separación de evidencia relevante y ruido (`ARCHIVOS_PERSONALES`).
5. **Triangulación** — Cruce de al menos seis fuentes independientes por caso, sin asumir que un documento oficial es veraz por ser oficial.
6. **Cronología** — Normalización de fechas heterogéneas en una línea de tiempo única (`tools/linea_tiempo.py`).
7. **Conclusión** — Afirmaciones trazables a archivo y hash.

## Limitaciones declaradas

- **Los datos son ficticios.** Este repositorio sirve para practicar procedimiento, no para acreditar técnicas sobre evidencia real.
- **La extracción de fechas es heurística, no un parser MIME completo.** Reconoce los formatos presentes en estos dos casos; un correo con cabeceras plegadas o adjuntos MIME requeriría `email`/`mailbox` de la biblioteca estándar.
- **El manifiesto del caso 01 conserva un prefijo de ruta heredado** que el verificador tolera en lugar de corregir, para no alterar los bytes del manifiesto original.
- **Los `.docx` y `.pdf` no se indexan automáticamente**: la cronología se construye con la evidencia legible por máquina, y los documentos se revisan manualmente.

## Requisitos y verificación

Solo biblioteca estándar de Python 3.9 o superior. Sin dependencias, sin instalación.

```bash
python3 tools/verificar_integridad.py    # debe terminar con "VERIFICACION CORRECTA"
python3 tools/linea_tiempo.py --formato json > /dev/null
```

GitHub Actions repite ambas comprobaciones en cada push (`.github/workflows/integridad.yml`), de modo que cualquier modificación de la evidencia rompe el build.

## Contexto académico

Universidad Tecnológica de Panamá — Centro Regional de Veraguas
Licenciatura en Ciberseguridad — Ciberinformática, III Año, Semestre II, 2026
Autor: Fermín González (`9-724-2000`)

Los enunciados y el informe resuelto están en [`docs/`](docs/).

## Licencia

Código (`tools/`) bajo licencia MIT — ver [`LICENSE`](LICENSE).
Los conjuntos de evidencia (`casos/`) y la documentación (`docs/`) se publican bajo **CC BY 4.0** con fines educativos. El contenido es ficticio.

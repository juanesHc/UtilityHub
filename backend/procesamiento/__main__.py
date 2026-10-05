import argparse
import sys
from functools import partial
from pathlib import Path

from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.excepciones import ErrorUtilityHub
from comun.modelos import ResultadoProcesamiento
from procesamiento.servicio import ServicioProcesamientoLecturas


def construir_analizador_argumentos() -> argparse.ArgumentParser:
    analizador = argparse.ArgumentParser(
        prog="python -m procesamiento",
        description="Procesa un CSV local de lecturas de UtilityHub contra la base de datos.",
    )
    analizador.add_argument("ruta_archivo_csv", type=Path)
    return analizador


def imprimir_resultado(resultado: ResultadoProcesamiento) -> None:
    print(f"Archivo: {resultado.nombre_archivo}")
    print(f"Torre: {resultado.codigo_torre} | Periodo: {resultado.periodo.como_texto()}")
    print(f"Carga: {resultado.id_carga} | Estado: {resultado.estado_carga.value}")
    if resultado.ids_cargas_reemplazadas:
        print("Cargas reemplazadas: " + ", ".join(str(id_carga) for id_carga in resultado.ids_cargas_reemplazadas))
    print(f"Lecturas aceptadas: {len(resultado.lecturas_aceptadas)}")
    print(f"Filas rechazadas: {len(resultado.filas_rechazadas)}")

    for fila_rechazada in resultado.filas_rechazadas:
        print(
            f"  linea {fila_rechazada.fila_cruda.numero_linea}: "
            f"{fila_rechazada.motivo_rechazo.value} ({fila_rechazada.detalle_rechazo})"
        )

    lecturas_anomalas = [lectura for lectura in resultado.lecturas_aceptadas if lectura.es_anomalo]
    print(f"Consumos anomalos: {len(lecturas_anomalas)}")
    for lectura_anomala in lecturas_anomalas:
        lectura_validada = lectura_anomala.lectura_validada
        print(
            f"  apartamento {lectura_validada.apartamento.numero} {lectura_validada.servicio.codigo}: "
            f"consumo {lectura_anomala.consumo_periodo} {lectura_validada.servicio.unidad_medida} "
            f"frente a promedio {lectura_anomala.promedio_referencia}"
        )


def main() -> int:
    argumentos = construir_analizador_argumentos().parse_args()
    ruta_archivo_csv: Path = argumentos.ruta_archivo_csv
    try:
        contenido_archivo = ruta_archivo_csv.read_bytes()
    except OSError as error:
        print(f"Error: no se pudo leer {ruta_archivo_csv}: {error}", file=sys.stderr)
        return 1

    try:
        configuracion = cargar_configuracion_desde_entorno()
        servicio_procesamiento = ServicioProcesamientoLecturas(partial(abrir_conexion, configuracion))
        resultado = servicio_procesamiento.procesar_archivo(ruta_archivo_csv.name, contenido_archivo)
    except ErrorUtilityHub as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    imprimir_resultado(resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())

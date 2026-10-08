from collections.abc import Callable
from datetime import datetime
from functools import partial

from comun import repositorio
from comun.conexion import Conexion as Connection
from comun.excepciones import ArchivoInvalido, PeriodoAnteriorAlMasReciente, TorreInexistente
from comun.modelos import EstadoSubida
from comun.reloj import obtener_fecha_hora_actual_utc
from comun.transacciones import ejecutar_en_transaccion
from procesamiento.servicio import ServicioProcesamientoLecturas


ERRORES_DEL_ARCHIVO: tuple[type[Exception], ...] = (ArchivoInvalido, TorreInexistente, PeriodoAnteriorAlMasReciente)
LONGITUD_MAXIMA_DETALLE_ERROR: int = 1000


def extraer_nombre_archivo(clave_objeto: str) -> str:
    return clave_objeto.rsplit("/", 1)[-1]


class ReceptorArchivosRecibidos:
    def __init__(
        self,
        abrir_conexion: Callable[[], Connection],
        servicio_procesamiento: ServicioProcesamientoLecturas,
        obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual_utc,
    ) -> None:
        self.abrir_conexion: Callable[[], Connection] = abrir_conexion
        self.servicio_procesamiento: ServicioProcesamientoLecturas = servicio_procesamiento
        self.obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual

    def recibir_objeto(self, clave_objeto: str, contenido_archivo: bytes) -> EstadoSubida:
        try:
            resultado = self.servicio_procesamiento.procesar_archivo(extraer_nombre_archivo(clave_objeto), contenido_archivo)
        except ERRORES_DEL_ARCHIVO as error:
            self.registrar_resultado(clave_objeto, EstadoSubida.FALLIDA, None, str(error)[:LONGITUD_MAXIMA_DETALLE_ERROR])
            return EstadoSubida.FALLIDA
        self.registrar_resultado(clave_objeto, EstadoSubida.PROCESADA, resultado.id_carga, None)
        return EstadoSubida.PROCESADA

    def registrar_resultado(
        self,
        clave_objeto: str,
        estado_subida: EstadoSubida,
        id_carga: int | None,
        detalle_error: str | None,
    ) -> None:
        ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(
                repositorio.registrar_resultado_de_subida,
                clave_objeto=clave_objeto,
                estado_subida=estado_subida,
                id_carga=id_carga,
                detalle_error=detalle_error,
                fecha_procesamiento=self.obtener_fecha_hora_actual(),
            ),
        )

from collections.abc import Callable
from datetime import datetime

from pymysql.connections import Connection
from pymysql.cursors import Cursor

from comun import repositorio
from comun.excepciones import PeriodoAnteriorAlMasReciente, TorreInexistente
from comun.modelos import EstadoCarga, FilaCruda, IdentificacionArchivo, ResultadoProcesamiento
from comun.reloj import obtener_fecha_hora_actual_utc
from procesamiento.calculo import determinar_estado_carga, evaluar_lecturas
from procesamiento.normalizacion import interpretar_nombre_archivo, normalizar_contenido_csv
from procesamiento.validacion import ValidadorFilas


class ServicioProcesamientoLecturas:
    def __init__(
        self,
        abrir_conexion: Callable[[], Connection],
        obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual_utc,
    ) -> None:
        self.abrir_conexion: Callable[[], Connection] = abrir_conexion
        self.obtener_fecha_hora_actual: Callable[[], datetime] = obtener_fecha_hora_actual

    def procesar_archivo(self, nombre_archivo: str, contenido_archivo: bytes) -> ResultadoProcesamiento:
        identificacion_archivo = interpretar_nombre_archivo(nombre_archivo)
        filas_crudas = normalizar_contenido_csv(contenido_archivo)

        conexion = self.abrir_conexion()
        try:
            conexion.begin()
            with conexion.cursor() as cursor:
                resultado = self.procesar_dentro_de_transaccion(
                    cursor,
                    nombre_archivo,
                    identificacion_archivo,
                    filas_crudas,
                )
            conexion.commit()
            return resultado
        except BaseException:
            conexion.rollback()
            raise
        finally:
            conexion.close()

    def procesar_dentro_de_transaccion(
        self,
        cursor: Cursor,
        nombre_archivo: str,
        identificacion_archivo: IdentificacionArchivo,
        filas_crudas: tuple[FilaCruda, ...],
    ) -> ResultadoProcesamiento:
        torre = repositorio.bloquear_torre_por_codigo(cursor, identificacion_archivo.codigo_torre)
        if torre is None:
            raise TorreInexistente(identificacion_archivo.codigo_torre)

        periodo_archivo = identificacion_archivo.periodo
        periodo_mas_reciente = repositorio.buscar_periodo_mas_reciente_con_lecturas(cursor, torre.id_torre)
        if periodo_mas_reciente is not None and periodo_archivo < periodo_mas_reciente:
            raise PeriodoAnteriorAlMasReciente(
                torre.codigo,
                periodo_archivo.como_texto(),
                periodo_mas_reciente.como_texto(),
            )

        cargas_reemplazadas = repositorio.listar_cargas_vigentes_del_periodo(cursor, torre.id_torre, periodo_archivo)
        for carga_reemplazada in cargas_reemplazadas:
            repositorio.eliminar_lecturas_de_carga(cursor, carga_reemplazada.id_carga)
            repositorio.actualizar_estado_carga(cursor, carga_reemplazada.id_carga, EstadoCarga.REEMPLAZADA)

        historial = repositorio.listar_lecturas_anteriores_al_periodo(cursor, torre.id_torre, periodo_archivo)
        validador_filas = ValidadorFilas(
            torre=torre,
            periodo_archivo=periodo_archivo,
            apartamentos_de_la_torre=repositorio.listar_apartamentos_de_torre(cursor, torre.id_torre),
            servicios=repositorio.listar_servicios(cursor),
            historial=historial,
        )
        resultado_validacion = validador_filas.validar_filas(filas_crudas)
        lecturas_evaluadas = evaluar_lecturas(resultado_validacion.lecturas_validadas, historial)
        estado_carga = determinar_estado_carga(len(lecturas_evaluadas), len(resultado_validacion.filas_rechazadas))

        fecha_procesamiento = self.obtener_fecha_hora_actual()
        id_carga = repositorio.insertar_carga(
            cursor,
            torre.id_torre,
            nombre_archivo,
            periodo_archivo,
            fecha_procesamiento,
            estado_carga,
        )
        repositorio.insertar_lecturas(cursor, id_carga, lecturas_evaluadas)
        repositorio.insertar_rechazos(cursor, id_carga, resultado_validacion.filas_rechazadas)

        return ResultadoProcesamiento(
            id_carga=id_carga,
            nombre_archivo=nombre_archivo,
            codigo_torre=torre.codigo,
            periodo=periodo_archivo,
            fecha_procesamiento=fecha_procesamiento,
            estado_carga=estado_carga,
            lecturas_aceptadas=lecturas_evaluadas,
            filas_rechazadas=resultado_validacion.filas_rechazadas,
            ids_cargas_reemplazadas=tuple(carga.id_carga for carga in cargas_reemplazadas),
        )

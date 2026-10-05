from collections.abc import Callable
from functools import partial

from pymysql.connections import Connection
from pymysql.cursors import Cursor

from comun import repositorio
from comun.excepciones import CargaInexistente, LecturaInexistente
from comun.modelos import (
    DetalleLecturaExplicada,
    FiltrosHistoricoLecturas,
    LecturaConsultada,
    PaginaLecturas,
    RechazoRegistrado,
    ResumenCarga,
    Servicio,
    SolicitudPagina,
    Torre,
)
from comun.transacciones import ejecutar_en_transaccion
from procesamiento.calculo import calcular_desviacion_relativa, calcular_rango_consumo_normal


class ServicioConsulta:
    def __init__(self, abrir_conexion: Callable[[], Connection]) -> None:
        self.abrir_conexion: Callable[[], Connection] = abrir_conexion

    def consultar_historico_lecturas(
        self,
        filtros: FiltrosHistoricoLecturas,
        solicitud_pagina: SolicitudPagina,
    ) -> PaginaLecturas:
        return ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(consultar_historico_en_cursor, filtros=filtros, solicitud_pagina=solicitud_pagina),
        )

    def obtener_detalle_lectura(self, id_lectura: int) -> DetalleLecturaExplicada:
        lectura = ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(repositorio.buscar_lectura_consultada, id_lectura=id_lectura),
        )
        if lectura is None:
            raise LecturaInexistente(id_lectura)
        return explicar_lectura(lectura)

    def listar_cargas(self) -> tuple[ResumenCarga, ...]:
        return ejecutar_en_transaccion(self.abrir_conexion, repositorio.listar_resumen_cargas)

    def listar_rechazos_de_carga(self, id_carga: int) -> tuple[RechazoRegistrado, ...]:
        return ejecutar_en_transaccion(
            self.abrir_conexion,
            partial(listar_rechazos_de_carga_existente, id_carga=id_carga),
        )

    def listar_torres(self) -> tuple[Torre, ...]:
        return ejecutar_en_transaccion(self.abrir_conexion, repositorio.listar_torres)

    def listar_servicios(self) -> tuple[Servicio, ...]:
        return ejecutar_en_transaccion(self.abrir_conexion, repositorio.listar_servicios)


def consultar_historico_en_cursor(
    cursor: Cursor,
    filtros: FiltrosHistoricoLecturas,
    solicitud_pagina: SolicitudPagina,
) -> PaginaLecturas:
    return PaginaLecturas(
        lecturas=repositorio.listar_historico_lecturas(cursor, filtros, solicitud_pagina),
        total_resultados=repositorio.contar_historico_lecturas(cursor, filtros),
        solicitud_pagina=solicitud_pagina,
    )


def listar_rechazos_de_carga_existente(cursor: Cursor, id_carga: int) -> tuple[RechazoRegistrado, ...]:
    if not repositorio.existe_carga(cursor, id_carga):
        raise CargaInexistente(id_carga)
    return repositorio.listar_rechazos_de_carga(cursor, id_carga)


def explicar_lectura(lectura: LecturaConsultada) -> DetalleLecturaExplicada:
    if lectura.consumo_periodo is None or lectura.promedio_referencia is None:
        return DetalleLecturaExplicada(lectura=lectura, rango_consumo_normal=None, desviacion_relativa=None)
    return DetalleLecturaExplicada(
        lectura=lectura,
        rango_consumo_normal=calcular_rango_consumo_normal(lectura.promedio_referencia, lectura.umbral_desviacion),
        desviacion_relativa=calcular_desviacion_relativa(lectura.consumo_periodo, lectura.promedio_referencia),
    )

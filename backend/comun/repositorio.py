from datetime import datetime
from typing import Any

from pymysql.cursors import Cursor

from comun.modelos import (
    Apartamento,
    CargaRegistrada,
    EstadoCarga,
    FilaRechazada,
    FiltrosHistoricoLecturas,
    LecturaConsultada,
    LecturaEvaluada,
    LecturaHistorica,
    MotivoRechazo,
    Periodo,
    RechazoRegistrado,
    ResumenCarga,
    Servicio,
    SolicitudPagina,
    Torre,
    Usuario,
)


ESTADOS_CON_LECTURAS: tuple[EstadoCarga, ...] = (EstadoCarga.PROCESADA_COMPLETA, EstadoCarga.PROCESADA_PARCIAL)
LONGITUD_MAXIMA_TEXTO_RECHAZO: int = 255

SELECCION_LECTURA_CONSULTADA: str = (
    "SELECT l.id_lectura, l.id_carga, t.codigo, t.nombre, a.numero, s.codigo, s.nombre, s.unidad_medida, "
    "s.umbral_desviacion, l.periodo, l.lectura_acumulada, l.consumo_periodo, l.fecha_lectura, "
    "l.promedio_referencia, l.es_anomalo "
)
ORIGEN_LECTURA_CONSULTADA: str = (
    "FROM lectura l "
    "JOIN apartamento a ON a.id_apartamento = l.id_apartamento "
    "JOIN torre t ON t.id_torre = a.id_torre "
    "JOIN servicio s ON s.id_servicio = l.id_servicio "
)


def bloquear_torre_por_codigo(cursor: Cursor, codigo_torre: str) -> Torre | None:
    cursor.execute(
        "SELECT id_torre, codigo, nombre FROM torre WHERE codigo = %s FOR UPDATE",
        (codigo_torre,),
    )
    fila_torre = cursor.fetchone()
    if fila_torre is None:
        return None
    return Torre(id_torre=fila_torre[0], codigo=fila_torre[1], nombre=fila_torre[2])


def listar_apartamentos_de_torre(cursor: Cursor, id_torre: int) -> tuple[Apartamento, ...]:
    cursor.execute(
        "SELECT id_apartamento, id_torre, numero FROM apartamento WHERE id_torre = %s",
        (id_torre,),
    )
    return tuple(
        Apartamento(id_apartamento=fila[0], id_torre=fila[1], numero=fila[2])
        for fila in cursor.fetchall()
    )


def listar_servicios(cursor: Cursor) -> tuple[Servicio, ...]:
    cursor.execute("SELECT id_servicio, codigo, nombre, unidad_medida, umbral_desviacion FROM servicio ORDER BY codigo")
    return tuple(
        Servicio(
            id_servicio=fila[0],
            codigo=fila[1],
            nombre=fila[2],
            unidad_medida=fila[3],
            umbral_desviacion=fila[4],
        )
        for fila in cursor.fetchall()
    )


def buscar_periodo_mas_reciente_con_lecturas(cursor: Cursor, id_torre: int) -> Periodo | None:
    cursor.execute(
        "SELECT MAX(periodo) FROM carga WHERE id_torre = %s AND estado IN (%s, %s)",
        (id_torre, *(estado.value for estado in ESTADOS_CON_LECTURAS)),
    )
    fila_maximo = cursor.fetchone()
    if fila_maximo is None or fila_maximo[0] is None:
        return None
    return Periodo.desde_texto(fila_maximo[0])


def listar_cargas_vigentes_del_periodo(cursor: Cursor, id_torre: int, periodo: Periodo) -> tuple[CargaRegistrada, ...]:
    cursor.execute(
        "SELECT id_carga, id_torre, nombre_archivo, periodo, fecha_procesamiento, estado "
        "FROM carga WHERE id_torre = %s AND periodo = %s AND estado <> %s "
        "ORDER BY id_carga FOR UPDATE",
        (id_torre, periodo.como_texto(), EstadoCarga.REEMPLAZADA.value),
    )
    return tuple(convertir_fila_en_carga(fila) for fila in cursor.fetchall())


def convertir_fila_en_carga(fila_carga: tuple[Any, ...]) -> CargaRegistrada:
    return CargaRegistrada(
        id_carga=fila_carga[0],
        id_torre=fila_carga[1],
        nombre_archivo=fila_carga[2],
        periodo=Periodo.desde_texto(fila_carga[3]),
        fecha_procesamiento=fila_carga[4],
        estado=EstadoCarga(fila_carga[5]),
    )


def listar_lecturas_anteriores_al_periodo(cursor: Cursor, id_torre: int, periodo: Periodo) -> tuple[LecturaHistorica, ...]:
    cursor.execute(
        "SELECT l.id_apartamento, l.id_servicio, l.periodo, l.lectura_acumulada, l.consumo_periodo, l.es_anomalo "
        "FROM lectura l JOIN apartamento a ON a.id_apartamento = l.id_apartamento "
        "WHERE a.id_torre = %s AND l.periodo < %s "
        "ORDER BY l.id_apartamento, l.id_servicio, l.periodo",
        (id_torre, periodo.como_texto()),
    )
    return tuple(
        LecturaHistorica(
            id_apartamento=fila[0],
            id_servicio=fila[1],
            periodo=Periodo.desde_texto(fila[2]),
            lectura_acumulada=fila[3],
            consumo_periodo=fila[4],
            es_anomalo=bool(fila[5]),
        )
        for fila in cursor.fetchall()
    )


def eliminar_lecturas_de_carga(cursor: Cursor, id_carga: int) -> int:
    return cursor.execute("DELETE FROM lectura WHERE id_carga = %s", (id_carga,))


def actualizar_estado_carga(cursor: Cursor, id_carga: int, estado_nuevo: EstadoCarga) -> None:
    cursor.execute("UPDATE carga SET estado = %s WHERE id_carga = %s", (estado_nuevo.value, id_carga))


def insertar_carga(
    cursor: Cursor,
    id_torre: int,
    nombre_archivo: str,
    periodo: Periodo,
    fecha_procesamiento: datetime,
    estado_carga: EstadoCarga,
) -> int:
    cursor.execute(
        "INSERT INTO carga (id_torre, nombre_archivo, periodo, fecha_procesamiento, estado) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_torre, nombre_archivo, periodo.como_texto(), fecha_procesamiento, estado_carga.value),
    )
    return cursor.lastrowid


def insertar_lecturas(cursor: Cursor, id_carga: int, lecturas_evaluadas: tuple[LecturaEvaluada, ...]) -> None:
    if not lecturas_evaluadas:
        return
    cursor.executemany(
        "INSERT INTO lectura (id_apartamento, id_servicio, id_carga, periodo, lectura_acumulada, "
        "consumo_periodo, fecha_lectura, promedio_referencia, es_anomalo) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            (
                lectura.lectura_validada.apartamento.id_apartamento,
                lectura.lectura_validada.servicio.id_servicio,
                id_carga,
                lectura.lectura_validada.periodo.como_texto(),
                lectura.lectura_validada.lectura_acumulada,
                lectura.consumo_periodo,
                lectura.lectura_validada.fecha_lectura,
                lectura.promedio_referencia,
                lectura.es_anomalo,
            )
            for lectura in lecturas_evaluadas
        ],
    )


def insertar_rechazos(cursor: Cursor, id_carga: int, filas_rechazadas: tuple[FilaRechazada, ...]) -> None:
    if not filas_rechazadas:
        return
    cursor.executemany(
        "INSERT INTO rechazo (id_carga, numero_fila, apartamento, servicio, periodo, motivo, valor_recibido) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        [
            (
                id_carga,
                fila_rechazada.fila_cruda.numero_linea,
                recortar_texto_de_rechazo(fila_rechazada.fila_cruda.apartamento),
                recortar_texto_de_rechazo(fila_rechazada.fila_cruda.servicio),
                recortar_texto_de_rechazo(fila_rechazada.fila_cruda.periodo),
                fila_rechazada.motivo_rechazo.value,
                recortar_texto_de_rechazo(fila_rechazada.valor_recibido),
            )
            for fila_rechazada in filas_rechazadas
        ],
    )


def recortar_texto_de_rechazo(texto_recibido: str | None) -> str | None:
    if texto_recibido is None or texto_recibido == "":
        return None
    return texto_recibido[:LONGITUD_MAXIMA_TEXTO_RECHAZO]


def listar_torres(cursor: Cursor) -> tuple[Torre, ...]:
    cursor.execute("SELECT id_torre, codigo, nombre FROM torre ORDER BY codigo")
    return tuple(Torre(id_torre=fila[0], codigo=fila[1], nombre=fila[2]) for fila in cursor.fetchall())


def construir_condiciones_historico(filtros: FiltrosHistoricoLecturas) -> tuple[str, list[Any]]:
    condiciones: list[str] = []
    parametros: list[Any] = []
    if filtros.codigo_torre is not None:
        condiciones.append("t.codigo = %s")
        parametros.append(filtros.codigo_torre)
    if filtros.numero_apartamento is not None:
        condiciones.append("a.numero = %s")
        parametros.append(filtros.numero_apartamento)
    if filtros.codigo_servicio is not None:
        condiciones.append("s.codigo = %s")
        parametros.append(filtros.codigo_servicio)
    if filtros.periodo_desde is not None:
        condiciones.append("l.periodo >= %s")
        parametros.append(filtros.periodo_desde.como_texto())
    if filtros.periodo_hasta is not None:
        condiciones.append("l.periodo <= %s")
        parametros.append(filtros.periodo_hasta.como_texto())
    if filtros.solo_anomalos:
        condiciones.append("l.es_anomalo = TRUE")
    if not condiciones:
        return "", parametros
    return "WHERE " + " AND ".join(condiciones) + " ", parametros


def contar_historico_lecturas(cursor: Cursor, filtros: FiltrosHistoricoLecturas) -> int:
    clausula_where, parametros = construir_condiciones_historico(filtros)
    cursor.execute("SELECT COUNT(*) " + ORIGEN_LECTURA_CONSULTADA + clausula_where, parametros)
    return cursor.fetchone()[0]


def listar_historico_lecturas(
    cursor: Cursor,
    filtros: FiltrosHistoricoLecturas,
    solicitud_pagina: SolicitudPagina,
) -> tuple[LecturaConsultada, ...]:
    clausula_where, parametros = construir_condiciones_historico(filtros)
    cursor.execute(
        SELECCION_LECTURA_CONSULTADA + ORIGEN_LECTURA_CONSULTADA + clausula_where
        + "ORDER BY l.periodo DESC, t.codigo, a.numero, s.codigo LIMIT %s OFFSET %s",
        [*parametros, solicitud_pagina.tamano_pagina, solicitud_pagina.cantidad_a_omitir],
    )
    return tuple(convertir_fila_en_lectura_consultada(fila) for fila in cursor.fetchall())


def buscar_lectura_consultada(cursor: Cursor, id_lectura: int) -> LecturaConsultada | None:
    cursor.execute(
        SELECCION_LECTURA_CONSULTADA + ORIGEN_LECTURA_CONSULTADA + "WHERE l.id_lectura = %s",
        (id_lectura,),
    )
    fila_lectura = cursor.fetchone()
    if fila_lectura is None:
        return None
    return convertir_fila_en_lectura_consultada(fila_lectura)


def convertir_fila_en_lectura_consultada(fila_lectura: tuple[Any, ...]) -> LecturaConsultada:
    return LecturaConsultada(
        id_lectura=fila_lectura[0],
        id_carga=fila_lectura[1],
        codigo_torre=fila_lectura[2],
        nombre_torre=fila_lectura[3],
        numero_apartamento=fila_lectura[4],
        codigo_servicio=fila_lectura[5],
        nombre_servicio=fila_lectura[6],
        unidad_medida=fila_lectura[7],
        umbral_desviacion=fila_lectura[8],
        periodo=Periodo.desde_texto(fila_lectura[9]),
        lectura_acumulada=fila_lectura[10],
        consumo_periodo=fila_lectura[11],
        fecha_lectura=fila_lectura[12],
        promedio_referencia=fila_lectura[13],
        es_anomalo=bool(fila_lectura[14]),
    )


def listar_resumen_cargas(cursor: Cursor) -> tuple[ResumenCarga, ...]:
    cursor.execute(
        "SELECT c.id_carga, t.codigo, t.nombre, c.periodo, c.nombre_archivo, c.fecha_procesamiento, c.estado, "
        "(SELECT COUNT(*) FROM lectura l WHERE l.id_carga = c.id_carga), "
        "(SELECT COUNT(*) FROM rechazo r WHERE r.id_carga = c.id_carga) "
        "FROM carga c JOIN torre t ON t.id_torre = c.id_torre "
        "ORDER BY c.fecha_procesamiento DESC, c.id_carga DESC"
    )
    return tuple(
        ResumenCarga(
            id_carga=fila[0],
            codigo_torre=fila[1],
            nombre_torre=fila[2],
            periodo=Periodo.desde_texto(fila[3]),
            nombre_archivo=fila[4],
            fecha_procesamiento=fila[5],
            estado=EstadoCarga(fila[6]),
            cantidad_lecturas_aceptadas=fila[7],
            cantidad_filas_rechazadas=fila[8],
        )
        for fila in cursor.fetchall()
    )


def existe_carga(cursor: Cursor, id_carga: int) -> bool:
    cursor.execute("SELECT 1 FROM carga WHERE id_carga = %s", (id_carga,))
    return cursor.fetchone() is not None


def listar_rechazos_de_carga(cursor: Cursor, id_carga: int) -> tuple[RechazoRegistrado, ...]:
    cursor.execute(
        "SELECT id_rechazo, id_carga, numero_fila, apartamento, servicio, periodo, motivo, valor_recibido "
        "FROM rechazo WHERE id_carga = %s ORDER BY numero_fila, id_rechazo",
        (id_carga,),
    )
    return tuple(
        RechazoRegistrado(
            id_rechazo=fila[0],
            id_carga=fila[1],
            numero_fila=fila[2],
            apartamento=fila[3],
            servicio=fila[4],
            periodo=fila[5],
            motivo_rechazo=MotivoRechazo(fila[6]),
            valor_recibido=fila[7],
        )
        for fila in cursor.fetchall()
    )


def buscar_usuario_por_nombre(cursor: Cursor, nombre_usuario: str) -> Usuario | None:
    cursor.execute(
        "SELECT id_usuario, nombre_usuario, hash_contrasena, ultimo_acceso FROM usuario WHERE nombre_usuario = %s",
        (nombre_usuario,),
    )
    fila_usuario = cursor.fetchone()
    if fila_usuario is None:
        return None
    return Usuario(
        id_usuario=fila_usuario[0],
        nombre_usuario=fila_usuario[1],
        hash_contrasena=fila_usuario[2],
        ultimo_acceso=fila_usuario[3],
    )


def registrar_ultimo_acceso(cursor: Cursor, id_usuario: int, fecha_ultimo_acceso: datetime) -> None:
    cursor.execute(
        "UPDATE usuario SET ultimo_acceso = %s WHERE id_usuario = %s",
        (fecha_ultimo_acceso, id_usuario),
    )

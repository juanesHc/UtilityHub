from datetime import datetime
from typing import Any

from comun.conexion import Cursor
from comun.modelos import (
    Apartamento,
    CargaRegistrada,
    EstadoCarga,
    EstadoSubida,
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
    SubidaRegistrada,
    Torre,
    Usuario,
    UsuarioListado,
)


ESTADOS_CON_LECTURAS: tuple[EstadoCarga, ...] = (EstadoCarga.PROCESADA_COMPLETA, EstadoCarga.PROCESADA_PARCIAL)
LONGITUD_MAXIMA_TEXTO_RECHAZO: int = 255
CARACTER_NUL: str = "\x00"
SUSTITUTO_DE_CARACTER_NUL: str = "�"

SELECCION_LECTURA_CONSULTADA: str = (
    "SELECT l.id_lectura AS id_lectura, l.id_carga AS id_carga, t.codigo AS codigo_torre, "
    "t.nombre AS nombre_torre, a.numero AS numero_apartamento, s.codigo AS codigo_servicio, "
    "s.nombre AS nombre_servicio, s.unidad_medida AS unidad_medida, s.umbral_desviacion AS umbral_desviacion, "
    "l.periodo AS periodo, l.lectura_acumulada AS lectura_acumulada, l.consumo_periodo AS consumo_periodo, "
    "l.fecha_lectura AS fecha_lectura, l.promedio_referencia AS promedio_referencia, l.es_anomalo AS es_anomalo "
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
    return convertir_fila_en_torre(fila_torre)


def convertir_fila_en_torre(fila_torre: dict[str, Any]) -> Torre:
    return Torre(id_torre=fila_torre["id_torre"], codigo=fila_torre["codigo"], nombre=fila_torre["nombre"])


def listar_apartamentos_de_torre(cursor: Cursor, id_torre: int) -> tuple[Apartamento, ...]:
    cursor.execute(
        "SELECT id_apartamento, id_torre, numero FROM apartamento WHERE id_torre = %s",
        (id_torre,),
    )
    return tuple(
        Apartamento(id_apartamento=fila["id_apartamento"], id_torre=fila["id_torre"], numero=fila["numero"])
        for fila in cursor.fetchall()
    )


def listar_servicios(cursor: Cursor) -> tuple[Servicio, ...]:
    cursor.execute("SELECT id_servicio, codigo, nombre, unidad_medida, umbral_desviacion FROM servicio ORDER BY codigo")
    return tuple(
        Servicio(
            id_servicio=fila["id_servicio"],
            codigo=fila["codigo"],
            nombre=fila["nombre"],
            unidad_medida=fila["unidad_medida"],
            umbral_desviacion=fila["umbral_desviacion"],
        )
        for fila in cursor.fetchall()
    )


def buscar_periodo_mas_reciente_con_lecturas(cursor: Cursor, id_torre: int) -> Periodo | None:
    cursor.execute(
        "SELECT MAX(periodo) AS periodo_mas_reciente FROM carga WHERE id_torre = %s AND estado IN (%s, %s)",
        (id_torre, *(estado.value for estado in ESTADOS_CON_LECTURAS)),
    )
    fila_maximo = cursor.fetchone()
    if fila_maximo is None or fila_maximo["periodo_mas_reciente"] is None:
        return None
    return Periodo.desde_texto(fila_maximo["periodo_mas_reciente"])


def listar_cargas_vigentes_del_periodo(cursor: Cursor, id_torre: int, periodo: Periodo) -> tuple[CargaRegistrada, ...]:
    cursor.execute(
        "SELECT id_carga, id_torre, nombre_archivo, periodo, fecha_procesamiento, estado "
        "FROM carga WHERE id_torre = %s AND periodo = %s AND estado <> %s "
        "ORDER BY id_carga FOR UPDATE",
        (id_torre, periodo.como_texto(), EstadoCarga.REEMPLAZADA.value),
    )
    return tuple(convertir_fila_en_carga(fila) for fila in cursor.fetchall())


def convertir_fila_en_carga(fila_carga: dict[str, Any]) -> CargaRegistrada:
    return CargaRegistrada(
        id_carga=fila_carga["id_carga"],
        id_torre=fila_carga["id_torre"],
        nombre_archivo=fila_carga["nombre_archivo"],
        periodo=Periodo.desde_texto(fila_carga["periodo"]),
        fecha_procesamiento=fila_carga["fecha_procesamiento"],
        estado=EstadoCarga(fila_carga["estado"]),
    )


def listar_lecturas_anteriores_al_periodo(cursor: Cursor, id_torre: int, periodo: Periodo) -> tuple[LecturaHistorica, ...]:
    cursor.execute(
        "SELECT l.id_apartamento AS id_apartamento, l.id_servicio AS id_servicio, l.periodo AS periodo, "
        "l.lectura_acumulada AS lectura_acumulada, l.consumo_periodo AS consumo_periodo, l.es_anomalo AS es_anomalo "
        "FROM lectura l JOIN apartamento a ON a.id_apartamento = l.id_apartamento "
        "WHERE a.id_torre = %s AND l.periodo < %s "
        "ORDER BY l.id_apartamento, l.id_servicio, l.periodo",
        (id_torre, periodo.como_texto()),
    )
    return tuple(
        LecturaHistorica(
            id_apartamento=fila["id_apartamento"],
            id_servicio=fila["id_servicio"],
            periodo=Periodo.desde_texto(fila["periodo"]),
            lectura_acumulada=fila["lectura_acumulada"],
            consumo_periodo=fila["consumo_periodo"],
            es_anomalo=bool(fila["es_anomalo"]),
        )
        for fila in cursor.fetchall()
    )


def eliminar_lecturas_de_carga(cursor: Cursor, id_carga: int) -> int:
    cursor.execute("DELETE FROM lectura WHERE id_carga = %s", (id_carga,))
    return cursor.rowcount


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
        "VALUES (%s, %s, %s, %s, %s) RETURNING id_carga",
        (id_torre, nombre_archivo, periodo.como_texto(), fecha_procesamiento, estado_carga.value),
    )
    return cursor.fetchone()["id_carga"]


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
    return texto_recibido.replace(CARACTER_NUL, SUSTITUTO_DE_CARACTER_NUL)[:LONGITUD_MAXIMA_TEXTO_RECHAZO]


def listar_torres(cursor: Cursor) -> tuple[Torre, ...]:
    cursor.execute("SELECT id_torre, codigo, nombre FROM torre ORDER BY codigo")
    return tuple(convertir_fila_en_torre(fila) for fila in cursor.fetchall())


def construir_condiciones_historico(filtros: FiltrosHistoricoLecturas) -> tuple[str, list[Any]]:
    condiciones: list[str] = []
    parametros: list[Any] = []
    if filtros.codigo_torre is not None:
        condiciones.append("t.codigo = UPPER(%s)")
        parametros.append(filtros.codigo_torre)
    if filtros.numero_apartamento is not None:
        condiciones.append("UPPER(a.numero) = UPPER(%s)")
        parametros.append(filtros.numero_apartamento)
    if filtros.codigo_servicio is not None:
        condiciones.append("s.codigo = UPPER(%s)")
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
    cursor.execute("SELECT COUNT(*) AS total_resultados " + ORIGEN_LECTURA_CONSULTADA + clausula_where, parametros)
    return cursor.fetchone()["total_resultados"]


def listar_historico_lecturas(
    cursor: Cursor,
    filtros: FiltrosHistoricoLecturas,
    solicitud_pagina: SolicitudPagina,
) -> tuple[LecturaConsultada, ...]:
    clausula_where, parametros = construir_condiciones_historico(filtros)
    cursor.execute(
        SELECCION_LECTURA_CONSULTADA + ORIGEN_LECTURA_CONSULTADA + clausula_where
        + "ORDER BY l.periodo DESC, t.codigo, LENGTH(a.numero), a.numero, s.codigo LIMIT %s OFFSET %s",
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


def convertir_fila_en_lectura_consultada(fila_lectura: dict[str, Any]) -> LecturaConsultada:
    return LecturaConsultada(
        id_lectura=fila_lectura["id_lectura"],
        id_carga=fila_lectura["id_carga"],
        codigo_torre=fila_lectura["codigo_torre"],
        nombre_torre=fila_lectura["nombre_torre"],
        numero_apartamento=fila_lectura["numero_apartamento"],
        codigo_servicio=fila_lectura["codigo_servicio"],
        nombre_servicio=fila_lectura["nombre_servicio"],
        unidad_medida=fila_lectura["unidad_medida"],
        umbral_desviacion=fila_lectura["umbral_desviacion"],
        periodo=Periodo.desde_texto(fila_lectura["periodo"]),
        lectura_acumulada=fila_lectura["lectura_acumulada"],
        consumo_periodo=fila_lectura["consumo_periodo"],
        fecha_lectura=fila_lectura["fecha_lectura"],
        promedio_referencia=fila_lectura["promedio_referencia"],
        es_anomalo=bool(fila_lectura["es_anomalo"]),
    )


def listar_resumen_cargas(cursor: Cursor) -> tuple[ResumenCarga, ...]:
    cursor.execute(
        "SELECT c.id_carga AS id_carga, t.codigo AS codigo_torre, t.nombre AS nombre_torre, c.periodo AS periodo, "
        "c.nombre_archivo AS nombre_archivo, c.fecha_procesamiento AS fecha_procesamiento, c.estado AS estado, "
        "(SELECT COUNT(*) FROM lectura l WHERE l.id_carga = c.id_carga) AS cantidad_lecturas_aceptadas, "
        "(SELECT COUNT(*) FROM rechazo r WHERE r.id_carga = c.id_carga) AS cantidad_filas_rechazadas "
        "FROM carga c JOIN torre t ON t.id_torre = c.id_torre "
        "ORDER BY c.fecha_procesamiento DESC, c.id_carga DESC"
    )
    return tuple(
        ResumenCarga(
            id_carga=fila["id_carga"],
            codigo_torre=fila["codigo_torre"],
            nombre_torre=fila["nombre_torre"],
            periodo=Periodo.desde_texto(fila["periodo"]),
            nombre_archivo=fila["nombre_archivo"],
            fecha_procesamiento=fila["fecha_procesamiento"],
            estado=EstadoCarga(fila["estado"]),
            cantidad_lecturas_aceptadas=fila["cantidad_lecturas_aceptadas"],
            cantidad_filas_rechazadas=fila["cantidad_filas_rechazadas"],
        )
        for fila in cursor.fetchall()
    )


def existe_carga(cursor: Cursor, id_carga: int) -> bool:
    cursor.execute("SELECT 1 AS existe FROM carga WHERE id_carga = %s", (id_carga,))
    return cursor.fetchone() is not None


def listar_rechazos_de_carga(cursor: Cursor, id_carga: int) -> tuple[RechazoRegistrado, ...]:
    cursor.execute(
        "SELECT id_rechazo, id_carga, numero_fila, apartamento, servicio, periodo, motivo, valor_recibido "
        "FROM rechazo WHERE id_carga = %s ORDER BY numero_fila, id_rechazo",
        (id_carga,),
    )
    return tuple(
        RechazoRegistrado(
            id_rechazo=fila["id_rechazo"],
            id_carga=fila["id_carga"],
            numero_fila=fila["numero_fila"],
            apartamento=fila["apartamento"],
            servicio=fila["servicio"],
            periodo=fila["periodo"],
            motivo_rechazo=MotivoRechazo(fila["motivo"]),
            valor_recibido=fila["valor_recibido"],
        )
        for fila in cursor.fetchall()
    )


SELECCION_USUARIO: str = (
    "SELECT id_usuario, nombre_usuario, hash_contrasena, ultimo_acceso, intentos_fallidos, bloqueado_hasta, "
    "version_credenciales FROM usuario WHERE LOWER(nombre_usuario) = LOWER(%s)"
)


def buscar_usuario_por_nombre(cursor: Cursor, nombre_usuario: str) -> Usuario | None:
    cursor.execute(SELECCION_USUARIO, (nombre_usuario,))
    fila_usuario = cursor.fetchone()
    return None if fila_usuario is None else convertir_fila_en_usuario(fila_usuario)


def bloquear_usuario_por_nombre(cursor: Cursor, nombre_usuario: str) -> Usuario | None:
    cursor.execute(SELECCION_USUARIO + " FOR UPDATE", (nombre_usuario,))
    fila_usuario = cursor.fetchone()
    return None if fila_usuario is None else convertir_fila_en_usuario(fila_usuario)


def convertir_fila_en_usuario(fila_usuario: dict[str, Any]) -> Usuario:
    return Usuario(
        id_usuario=fila_usuario["id_usuario"],
        nombre_usuario=fila_usuario["nombre_usuario"],
        hash_contrasena=fila_usuario["hash_contrasena"],
        ultimo_acceso=fila_usuario["ultimo_acceso"],
        intentos_fallidos=fila_usuario["intentos_fallidos"],
        bloqueado_hasta=fila_usuario["bloqueado_hasta"],
        version_credenciales=fila_usuario["version_credenciales"],
    )


def registrar_inicio_sesion_exitoso(cursor: Cursor, id_usuario: int, fecha_ultimo_acceso: datetime) -> None:
    cursor.execute(
        "UPDATE usuario SET ultimo_acceso = %s, intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id_usuario = %s",
        (fecha_ultimo_acceso, id_usuario),
    )


def registrar_intento_fallido(
    cursor: Cursor,
    id_usuario: int,
    intentos_fallidos: int,
    bloqueado_hasta: datetime | None,
) -> None:
    cursor.execute(
        "UPDATE usuario SET intentos_fallidos = %s, bloqueado_hasta = %s WHERE id_usuario = %s",
        (intentos_fallidos, bloqueado_hasta, id_usuario),
    )


def insertar_usuario(
    cursor: Cursor,
    nombre_usuario: str,
    hash_contrasena: str,
    fecha_creacion: datetime,
    creado_por_id_usuario: int | None,
) -> int:
    cursor.execute(
        "INSERT INTO usuario (nombre_usuario, hash_contrasena, fecha_creacion, creado_por_id_usuario) "
        "VALUES (%s, %s, %s, %s) RETURNING id_usuario",
        (nombre_usuario, hash_contrasena, fecha_creacion, creado_por_id_usuario),
    )
    return cursor.fetchone()["id_usuario"]


def actualizar_clave_e_invalidar_sesiones(cursor: Cursor, id_usuario: int, hash_contrasena: str) -> None:
    cursor.execute(
        "UPDATE usuario SET hash_contrasena = %s, version_credenciales = version_credenciales + 1, "
        "intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id_usuario = %s",
        (hash_contrasena, id_usuario),
    )


def listar_usuarios(cursor: Cursor) -> tuple[UsuarioListado, ...]:
    cursor.execute(
        "SELECT u.id_usuario AS id_usuario, u.nombre_usuario AS nombre_usuario, u.fecha_creacion AS fecha_creacion, "
        "c.nombre_usuario AS nombre_usuario_creador, u.ultimo_acceso AS ultimo_acceso, u.bloqueado_hasta AS bloqueado_hasta "
        "FROM usuario u LEFT JOIN usuario c ON c.id_usuario = u.creado_por_id_usuario "
        "ORDER BY LOWER(u.nombre_usuario)"
    )
    return tuple(
        UsuarioListado(
            id_usuario=fila["id_usuario"],
            nombre_usuario=fila["nombre_usuario"],
            fecha_creacion=fila["fecha_creacion"],
            nombre_usuario_creador=fila["nombre_usuario_creador"],
            ultimo_acceso=fila["ultimo_acceso"],
            bloqueado_hasta=fila["bloqueado_hasta"],
        )
        for fila in cursor.fetchall()
    )


def buscar_torre_por_codigo(cursor: Cursor, codigo_torre: str) -> Torre | None:
    cursor.execute("SELECT id_torre, codigo, nombre FROM torre WHERE codigo = UPPER(%s)", (codigo_torre,))
    fila_torre = cursor.fetchone()
    return None if fila_torre is None else convertir_fila_en_torre(fila_torre)


SELECCION_SUBIDA: str = (
    "SELECT id_subida, clave_objeto, nombre_archivo, fecha_solicitud, estado, id_carga, "
    "detalle_error, fecha_procesamiento FROM subida"
)


def insertar_subida(
    cursor: Cursor,
    clave_objeto: str,
    nombre_archivo: str,
    id_usuario: int,
    fecha_solicitud: datetime,
) -> int:
    cursor.execute(
        "INSERT INTO subida (clave_objeto, nombre_archivo, id_usuario, fecha_solicitud, estado) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id_subida",
        (clave_objeto, nombre_archivo, id_usuario, fecha_solicitud, EstadoSubida.PENDIENTE.value),
    )
    return cursor.fetchone()["id_subida"]


def buscar_subida_por_id(cursor: Cursor, id_subida: int) -> SubidaRegistrada | None:
    cursor.execute(SELECCION_SUBIDA + " WHERE id_subida = %s", (id_subida,))
    fila_subida = cursor.fetchone()
    return None if fila_subida is None else convertir_fila_en_subida(fila_subida)


def convertir_fila_en_subida(fila_subida: dict[str, Any]) -> SubidaRegistrada:
    return SubidaRegistrada(
        id_subida=fila_subida["id_subida"],
        clave_objeto=fila_subida["clave_objeto"],
        nombre_archivo=fila_subida["nombre_archivo"],
        fecha_solicitud=fila_subida["fecha_solicitud"],
        estado=EstadoSubida(fila_subida["estado"]),
        id_carga=fila_subida["id_carga"],
        detalle_error=fila_subida["detalle_error"],
        fecha_procesamiento=fila_subida["fecha_procesamiento"],
    )


def registrar_resultado_de_subida(
    cursor: Cursor,
    clave_objeto: str,
    estado_subida: EstadoSubida,
    id_carga: int | None,
    detalle_error: str | None,
    fecha_procesamiento: datetime,
) -> None:
    cursor.execute(
        "UPDATE subida SET estado = %s, id_carga = %s, detalle_error = %s, fecha_procesamiento = %s "
        "WHERE clave_objeto = %s",
        (estado_subida.value, id_carga, detalle_error, fecha_procesamiento, clave_objeto),
    )

def buscar_subida_por_id_carga(cursor: Cursor, id_carga: int) -> SubidaRegistrada | None:
    cursor.execute(SELECCION_SUBIDA + " WHERE id_carga = %s ORDER BY id_subida DESC LIMIT 1", (id_carga,))
    fila_subida = cursor.fetchone()
    return None if fila_subida is None else convertir_fila_en_subida(fila_subida)

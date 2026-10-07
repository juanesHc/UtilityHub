from functools import partial

from api.servicio_consulta import ServicioConsulta
from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.modelos import FiltrosHistoricoLecturas, SolicitudPagina
from pruebas.base_de_datos_de_pruebas import crear_servicio_procesamiento, ejecutar_y_confirmar


NUMEROS_EN_DESORDEN: tuple[str, ...] = ("1001", "201", "99", "101", "1000", "1102")


def prueba_historico_ordena_los_apartamentos_como_numeros(base_vacia: None) -> None:
    for numero in ("99", "1000", "1001", "1102"):
        ejecutar_y_confirmar(
            "INSERT INTO apartamento (id_torre, numero) SELECT id_torre, %s FROM torre WHERE codigo = 'T01'",
            (numero,),
        )
    contenido = "torre,apartamento,servicio,periodo,lectura_acumulada,fecha_lectura\r\n" + "".join(
        f"T01,{numero},AGUA,2025-10,100,2025-11-02\r\n" for numero in NUMEROS_EN_DESORDEN
    )
    crear_servicio_procesamiento().procesar_archivo("lecturas_T01_2025-10.csv", contenido.encode("utf-8"))

    servicio_consulta = ServicioConsulta(partial(abrir_conexion, cargar_configuracion_desde_entorno()))
    pagina = servicio_consulta.consultar_historico_lecturas(
        FiltrosHistoricoLecturas("T01", None, "AGUA", None, None, False),
        SolicitudPagina(numero_pagina=1, tamano_pagina=50),
    )

    assert [lectura.numero_apartamento for lectura in pagina.lecturas] == ["99", "101", "201", "1000", "1001", "1102"]

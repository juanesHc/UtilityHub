from functools import partial

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.configuracion import cargar_configuracion_api_desde_entorno
from api.rutas import router_autenticacion, router_consulta
from api.servicio_autenticacion import ServicioAutenticacion
from api.servicio_consulta import ServicioConsulta
from api.traduccion import traducir_error_de_dominio
from comun.conexion import abrir_conexion
from comun.configuracion import cargar_configuracion_desde_entorno
from comun.excepciones import ErrorUtilityHub


def crear_aplicacion() -> FastAPI:
    configuracion_base_datos = cargar_configuracion_desde_entorno()
    configuracion_api = cargar_configuracion_api_desde_entorno()
    abrir_conexion_configurada = partial(abrir_conexion, configuracion_base_datos)

    aplicacion = FastAPI(
        title="UtilityHub API",
        version="1.0.0",
        description="Consulta de lecturas de agua y energia, cargas procesadas y consumos anomalos.",
    )
    aplicacion.state.servicio_consulta = ServicioConsulta(abrir_conexion_configurada)
    aplicacion.state.servicio_autenticacion = ServicioAutenticacion(
        abrir_conexion_configurada,
        configuracion_api.clave_firma_token,
    )

    aplicacion.add_middleware(
        CORSMiddleware,
        allow_origins=list(configuracion_api.origenes_cors_permitidos),
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    aplicacion.add_exception_handler(ErrorUtilityHub, traducir_error_de_dominio)
    aplicacion.include_router(router_autenticacion)
    aplicacion.include_router(router_consulta)
    return aplicacion


aplicacion = crear_aplicacion()

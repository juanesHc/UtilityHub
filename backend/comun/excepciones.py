class ErrorUtilityHub(Exception):
    pass


class ConfiguracionIncompleta(ErrorUtilityHub):
    def __init__(self, variables_faltantes: tuple[str, ...]) -> None:
        super().__init__("Faltan variables de entorno: " + ", ".join(variables_faltantes))
        self.variables_faltantes: tuple[str, ...] = variables_faltantes


class ConfiguracionInvalida(ErrorUtilityHub):
    def __init__(self, nombre_variable: str, valor_recibido: str) -> None:
        super().__init__(f"La variable de entorno {nombre_variable} tiene un valor inválido: '{valor_recibido}'")
        self.nombre_variable: str = nombre_variable
        self.valor_recibido: str = valor_recibido


class ErrorConexionBaseDatos(ErrorUtilityHub):
    def __init__(self, descripcion_error: str) -> None:
        super().__init__(f"No fue posible conectarse a la base de datos: {descripcion_error}")
        self.descripcion_error: str = descripcion_error


class PeriodoInvalido(ErrorUtilityHub):
    def __init__(self, texto_periodo: str) -> None:
        super().__init__(f"El periodo '{texto_periodo}' no tiene el formato AAAA-MM o el mes no existe")
        self.texto_periodo: str = texto_periodo


class ArchivoInvalido(ErrorUtilityHub):
    pass


class NombreArchivoInvalido(ArchivoInvalido):
    def __init__(self, nombre_archivo: str) -> None:
        super().__init__(f"El nombre '{nombre_archivo}' no sigue el formato lecturas_T<torre>_<AAAA-MM>.csv")
        self.nombre_archivo: str = nombre_archivo


class CodificacionNoSoportada(ArchivoInvalido):
    def __init__(self) -> None:
        super().__init__("El archivo no está codificado en UTF-8")


class ArchivoVacio(ArchivoInvalido):
    def __init__(self) -> None:
        super().__init__("El archivo no tiene encabezado ni filas")


class EncabezadoInvalido(ArchivoInvalido):
    def __init__(self, columnas_recibidas: tuple[str, ...], columnas_esperadas: tuple[str, ...]) -> None:
        super().__init__(
            "El encabezado no coincide. Esperado: " + ",".join(columnas_esperadas)
            + " | Recibido: " + ",".join(columnas_recibidas)
        )
        self.columnas_recibidas: tuple[str, ...] = columnas_recibidas
        self.columnas_esperadas: tuple[str, ...] = columnas_esperadas


class RangoDePeriodosInvalido(ErrorUtilityHub):
    def __init__(self, periodo_desde: str, periodo_hasta: str) -> None:
        super().__init__(f"El periodo desde {periodo_desde} es posterior al periodo hasta {periodo_hasta}")
        self.periodo_desde: str = periodo_desde
        self.periodo_hasta: str = periodo_hasta


class CredencialesInvalidas(ErrorUtilityHub):
    def __init__(self) -> None:
        super().__init__("Usuario o clave incorrectos")


class CuentaBloqueada(ErrorUtilityHub):
    def __init__(self, segundos_restantes: int) -> None:
        minutos_restantes = max(1, -(-segundos_restantes // 60))
        super().__init__(
            f"Cuenta bloqueada temporalmente por intentos fallidos; intente de nuevo en {minutos_restantes} minuto(s)"
        )
        self.segundos_restantes: int = segundos_restantes


class TokenInvalido(ErrorUtilityHub):
    def __init__(self) -> None:
        super().__init__("Token de acceso ausente, inválido o vencido")


class LecturaInexistente(ErrorUtilityHub):
    def __init__(self, id_lectura: int) -> None:
        super().__init__(f"La lectura {id_lectura} no existe")
        self.id_lectura: int = id_lectura


class CargaInexistente(ErrorUtilityHub):
    def __init__(self, id_carga: int) -> None:
        super().__init__(f"La carga {id_carga} no existe")
        self.id_carga: int = id_carga


class TorreInexistente(ErrorUtilityHub):
    def __init__(self, codigo_torre: str) -> None:
        super().__init__(f"La torre '{codigo_torre}' no existe")
        self.codigo_torre: str = codigo_torre


class PeriodoAnteriorAlMasReciente(ErrorUtilityHub):
    def __init__(self, codigo_torre: str, periodo_archivo: str, periodo_mas_reciente: str) -> None:
        super().__init__(
            f"La torre {codigo_torre} ya tiene lecturas del periodo {periodo_mas_reciente}; "
            f"solo se admite cargar o reprocesar ese periodo o uno posterior, no {periodo_archivo}"
        )
        self.codigo_torre: str = codigo_torre
        self.periodo_archivo: str = periodo_archivo
        self.periodo_mas_reciente: str = periodo_mas_reciente


class NombreUsuarioInvalido(ErrorUtilityHub):
    def __init__(self, nombre_usuario: str, descripcion_problema: str) -> None:
        super().__init__(f"El nombre de usuario '{nombre_usuario}' no es válido: {descripcion_problema}")
        self.nombre_usuario: str = nombre_usuario
        self.descripcion_problema: str = descripcion_problema


class ClaveInsegura(ErrorUtilityHub):
    def __init__(self, descripcion_problema: str) -> None:
        super().__init__(f"La clave no es aceptable: {descripcion_problema}")
        self.descripcion_problema: str = descripcion_problema


class UsuarioYaExiste(ErrorUtilityHub):
    def __init__(self, nombre_usuario: str) -> None:
        super().__init__(f"Ya existe un usuario '{nombre_usuario}' (sin distinguir mayúsculas)")
        self.nombre_usuario: str = nombre_usuario


class UsuarioInexistente(ErrorUtilityHub):
    def __init__(self, nombre_usuario: str) -> None:
        super().__init__(f"El usuario '{nombre_usuario}' no existe")
        self.nombre_usuario: str = nombre_usuario


class SubidaInexistente(ErrorUtilityHub):
    def __init__(self, id_subida: int) -> None:
        super().__init__(f"La subida {id_subida} no existe")
        self.id_subida: int = id_subida


class AlmacenNoConfigurado(ErrorUtilityHub):
    def __init__(self, nombre_variable: str) -> None:
        super().__init__(f"La subida de archivos no está configurada; falta la variable de entorno {nombre_variable}")
        self.nombre_variable: str = nombre_variable


class FirmaDeSubidaInvalida(ErrorUtilityHub):
    def __init__(self) -> None:
        super().__init__("La URL de subida no es válida o ya venció; solicite una nueva")


class ArchivoDemasiadoGrande(ErrorUtilityHub):
    def __init__(self, tamano_maximo_bytes: int) -> None:
        super().__init__(f"El archivo supera el tamaño máximo de {tamano_maximo_bytes // (1024 * 1024)} MB")
        self.tamano_maximo_bytes: int = tamano_maximo_bytes

class ArchivoDeCargaNoDisponible(ErrorUtilityHub):
    def __init__(self, id_carga: int) -> None:
        super().__init__(f"La carga {id_carga} no tiene un archivo guardado en el almacén")
        self.id_carga: int = id_carga


class ObjetoInexistente(ErrorUtilityHub):
    def __init__(self, clave_objeto: str) -> None:
        super().__init__(f"El objeto '{clave_objeto}' no existe en el almacén")
        self.clave_objeto: str = clave_objeto

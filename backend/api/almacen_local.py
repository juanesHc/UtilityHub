import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from comun.excepciones import FirmaDeSubidaInvalida, ObjetoInexistente


CONTEXTO_FIRMA: bytes = b"utilityhub-almacen-local"
TAMANO_MAXIMO_OBJETO_BYTES: int = 5 * 1024 * 1024

MetodoFirmado = Literal["GET", "PUT"]


@dataclass(frozen=True)
class FirmaDeSubida:
    expira: int
    firma: str


def convertir_en_segundos_epoch(fecha_hora_utc: datetime) -> int:
    return int(fecha_hora_utc.replace(tzinfo=UTC).timestamp())


@dataclass(frozen=True)
class AlmacenLocal:
    carpeta_raiz: Path
    clave_firma: str = field(repr=False)

    def firmar(self, metodo: MetodoFirmado, clave_objeto: str, fecha_expiracion: datetime) -> FirmaDeSubida:
        expira = convertir_en_segundos_epoch(fecha_expiracion)
        return FirmaDeSubida(expira=expira, firma=self.calcular_firma(metodo, clave_objeto, expira))

    def verificar_firma(
        self,
        metodo: MetodoFirmado,
        clave_objeto: str,
        expira: int,
        firma: str,
        fecha_actual: datetime,
    ) -> None:
        firma_esperada = self.calcular_firma(metodo, clave_objeto, expira)
        if not hmac.compare_digest(firma_esperada, firma) or expira < convertir_en_segundos_epoch(fecha_actual):
            raise FirmaDeSubidaInvalida()

    def guardar_objeto(self, clave_objeto: str, contenido_objeto: bytes) -> Path:
        ruta_objeto = self.resolver_ruta(clave_objeto)
        ruta_objeto.parent.mkdir(parents=True, exist_ok=True)
        ruta_objeto.write_bytes(contenido_objeto)
        return ruta_objeto

    def leer_objeto(self, clave_objeto: str) -> bytes:
        ruta_objeto = self.resolver_ruta(clave_objeto)
        if not ruta_objeto.is_file():
            raise ObjetoInexistente(clave_objeto)
        return ruta_objeto.read_bytes()

    def resolver_ruta(self, clave_objeto: str) -> Path:
        carpeta_raiz = self.carpeta_raiz.resolve()
        ruta_objeto = (carpeta_raiz / clave_objeto).resolve()
        if not ruta_objeto.is_relative_to(carpeta_raiz) or ruta_objeto == carpeta_raiz:
            raise FirmaDeSubidaInvalida()
        return ruta_objeto

    def calcular_firma(self, metodo: MetodoFirmado, clave_objeto: str, expira: int) -> str:
        mensaje = b"\n".join(
            (CONTEXTO_FIRMA, metodo.encode("ascii"), clave_objeto.encode("utf-8"), str(expira).encode("ascii"))
        )
        return hmac.new(self.clave_firma.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()

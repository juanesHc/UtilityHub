import base64
import hashlib
import hmac
import secrets


ALGORITMO_HASH_CONTRASENA: str = "pbkdf2_sha256"
ITERACIONES_PBKDF2: int = 600_000
BYTES_DE_SAL: int = 16
SEPARADOR_HASH: str = "$"


def generar_hash_contrasena(clave_en_claro: str, iteraciones: int = ITERACIONES_PBKDF2) -> str:
    sal = secrets.token_bytes(BYTES_DE_SAL)
    derivada = derivar_clave(clave_en_claro, sal, iteraciones)
    return SEPARADOR_HASH.join(
        (ALGORITMO_HASH_CONTRASENA, str(iteraciones), codificar_base64(sal), codificar_base64(derivada))
    )


def verificar_contrasena(clave_en_claro: str, hash_almacenado: str) -> bool:
    partes_hash = hash_almacenado.split(SEPARADOR_HASH)
    if len(partes_hash) != 4 or partes_hash[0] != ALGORITMO_HASH_CONTRASENA or not partes_hash[1].isdigit():
        return False
    try:
        sal = decodificar_base64(partes_hash[2])
        derivada_esperada = decodificar_base64(partes_hash[3])
    except ValueError:
        return False
    derivada_calculada = derivar_clave(clave_en_claro, sal, int(partes_hash[1]))
    return hmac.compare_digest(derivada_calculada, derivada_esperada)


def derivar_clave(clave_en_claro: str, sal: bytes, iteraciones: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", clave_en_claro.encode("utf-8"), sal, iteraciones)


def codificar_base64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii")


def decodificar_base64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto.encode("ascii"))

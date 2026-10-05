from datetime import UTC, datetime


def obtener_fecha_hora_actual_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)

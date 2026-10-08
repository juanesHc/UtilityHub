FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY comun ./comun
COPY procesamiento ./procesamiento
COPY api ./api

RUN useradd --system --no-create-home utilityhub
RUN mkdir /almacen && chown utilityhub /almacen
USER utilityhub

EXPOSE 8000
CMD ["uvicorn", "api.main:aplicacion", "--host", "0.0.0.0", "--port", "8000"]

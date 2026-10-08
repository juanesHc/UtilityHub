CREATE TABLE IF NOT EXISTS torre (
    id_torre INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    CONSTRAINT uq_torre_codigo UNIQUE (codigo),
    CONSTRAINT ck_torre_codigo_en_mayusculas CHECK (codigo = UPPER(codigo))
);

CREATE TABLE IF NOT EXISTS apartamento (
    id_apartamento INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_torre INT NOT NULL,
    numero VARCHAR(10) NOT NULL,
    CONSTRAINT fk_apartamento_torre FOREIGN KEY (id_torre) REFERENCES torre (id_torre),
    CONSTRAINT uq_apartamento_torre_numero UNIQUE (id_torre, numero)
);

CREATE TABLE IF NOT EXISTS servicio (
    id_servicio INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    unidad_medida VARCHAR(20) NOT NULL,
    umbral_desviacion DECIMAL(5, 2) NOT NULL,
    CONSTRAINT uq_servicio_codigo UNIQUE (codigo),
    CONSTRAINT ck_servicio_codigo_en_mayusculas CHECK (codigo = UPPER(codigo)),
    CONSTRAINT ck_servicio_umbral_desviacion CHECK (umbral_desviacion > 0)
);

CREATE TABLE IF NOT EXISTS carga (
    id_carga INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_torre INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    periodo CHAR(7) NOT NULL,
    fecha_procesamiento TIMESTAMP NOT NULL,
    estado VARCHAR(20) NOT NULL,
    CONSTRAINT fk_carga_torre FOREIGN KEY (id_torre) REFERENCES torre (id_torre),
    CONSTRAINT ck_carga_periodo CHECK (periodo ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_carga_estado CHECK (
        estado IN ('procesada_completa', 'procesada_parcial', 'rechazada', 'reemplazada')
    )
);

CREATE INDEX IF NOT EXISTS ix_carga_torre_periodo ON carga (id_torre, periodo);

CREATE TABLE IF NOT EXISTS lectura (
    id_lectura BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_apartamento INT NOT NULL,
    id_servicio INT NOT NULL,
    id_carga INT NOT NULL,
    periodo CHAR(7) NOT NULL,
    lectura_acumulada DECIMAL(14, 3) NOT NULL,
    consumo_periodo DECIMAL(14, 3) NULL,
    fecha_lectura DATE NOT NULL,
    promedio_referencia DECIMAL(14, 3) NULL,
    es_anomalo BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_lectura_apartamento FOREIGN KEY (id_apartamento) REFERENCES apartamento (id_apartamento),
    CONSTRAINT fk_lectura_servicio FOREIGN KEY (id_servicio) REFERENCES servicio (id_servicio),
    CONSTRAINT fk_lectura_carga FOREIGN KEY (id_carga) REFERENCES carga (id_carga),
    CONSTRAINT uq_lectura_apartamento_servicio_periodo UNIQUE (id_apartamento, id_servicio, periodo),
    CONSTRAINT ck_lectura_periodo CHECK (periodo ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_lectura_acumulada_no_negativa CHECK (lectura_acumulada >= 0)
);

CREATE INDEX IF NOT EXISTS ix_lectura_carga ON lectura (id_carga);
CREATE INDEX IF NOT EXISTS ix_lectura_servicio ON lectura (id_servicio);

CREATE TABLE IF NOT EXISTS rechazo (
    id_rechazo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_carga INT NOT NULL,
    numero_fila INT NOT NULL,
    apartamento VARCHAR(255) NULL,
    servicio VARCHAR(255) NULL,
    periodo VARCHAR(255) NULL,
    motivo VARCHAR(40) NOT NULL,
    valor_recibido VARCHAR(255) NULL,
    CONSTRAINT fk_rechazo_carga FOREIGN KEY (id_carga) REFERENCES carga (id_carga)
);

CREATE INDEX IF NOT EXISTS ix_rechazo_carga ON rechazo (id_carga);

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_usuario VARCHAR(50) NOT NULL,
    hash_contrasena VARCHAR(255) NOT NULL,
    ultimo_acceso TIMESTAMP NULL,
    CONSTRAINT uq_usuario_nombre_usuario UNIQUE (nombre_usuario)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_nombre_usuario_sin_mayusculas ON usuario (LOWER(nombre_usuario));

ALTER TABLE usuario ADD COLUMN IF NOT EXISTS intentos_fallidos INT NOT NULL DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS bloqueado_hasta TIMESTAMP NULL;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS version_credenciales INT NOT NULL DEFAULT 1;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP NULL;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS creado_por_id_usuario INT NULL
    CONSTRAINT fk_usuario_creado_por REFERENCES usuario (id_usuario);

CREATE TABLE IF NOT EXISTS subida (
    id_subida INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    clave_objeto VARCHAR(512) NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    id_usuario INT NOT NULL,
    fecha_solicitud TIMESTAMP NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    id_carga INT NULL,
    detalle_error VARCHAR(1000) NULL,
    fecha_procesamiento TIMESTAMP NULL,
    CONSTRAINT uq_subida_clave_objeto UNIQUE (clave_objeto),
    CONSTRAINT fk_subida_usuario FOREIGN KEY (id_usuario) REFERENCES usuario (id_usuario),
    CONSTRAINT fk_subida_carga FOREIGN KEY (id_carga) REFERENCES carga (id_carga),
    CONSTRAINT ck_subida_estado CHECK (estado IN ('pendiente', 'procesada', 'fallida'))
);

INSERT INTO servicio (codigo, nombre, unidad_medida, umbral_desviacion) VALUES
    ('AGUA', 'Agua potable', 'm3', 0.50),
    ('ENERGIA', 'Energia electrica', 'kWh', 0.50)
ON CONFLICT DO NOTHING;

INSERT INTO torre (codigo, nombre) VALUES
    ('T01', 'Torre 1'),
    ('T02', 'Torre 2'),
    ('T03', 'Torre 3')
ON CONFLICT DO NOTHING;

INSERT INTO apartamento (id_torre, numero)
SELECT torre.id_torre, CAST(pisos.piso * 100 + posiciones.posicion AS VARCHAR(10))
FROM torre
CROSS JOIN generate_series(1, 5) AS pisos (piso)
CROSS JOIN generate_series(1, 4) AS posiciones (posicion)
WHERE torre.codigo IN ('T01', 'T02', 'T03')
ON CONFLICT DO NOTHING;

INSERT INTO usuario (nombre_usuario, hash_contrasena) VALUES
    ('admin', 'pbkdf2_sha256$600000$cMNbHOE5hvKgXc9xr1DS7w==$4M6TYLOxycQSgcBr2SndHe9CLbtVARcZI_pJIH1WsGc=')
ON CONFLICT DO NOTHING;

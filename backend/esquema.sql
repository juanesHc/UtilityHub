CREATE TABLE IF NOT EXISTS torre (
    id_torre INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    CONSTRAINT uq_torre_codigo UNIQUE (codigo)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS apartamento (
    id_apartamento INT AUTO_INCREMENT PRIMARY KEY,
    id_torre INT NOT NULL,
    numero VARCHAR(10) NOT NULL,
    CONSTRAINT fk_apartamento_torre FOREIGN KEY (id_torre) REFERENCES torre (id_torre),
    CONSTRAINT uq_apartamento_torre_numero UNIQUE (id_torre, numero)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS servicio (
    id_servicio INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    unidad_medida VARCHAR(20) NOT NULL,
    umbral_desviacion DECIMAL(5, 2) NOT NULL,
    CONSTRAINT uq_servicio_codigo UNIQUE (codigo),
    CONSTRAINT ck_servicio_umbral_desviacion CHECK (umbral_desviacion > 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS carga (
    id_carga INT AUTO_INCREMENT PRIMARY KEY,
    id_torre INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    periodo CHAR(7) NOT NULL,
    fecha_procesamiento DATETIME NOT NULL,
    estado VARCHAR(20) NOT NULL,
    CONSTRAINT fk_carga_torre FOREIGN KEY (id_torre) REFERENCES torre (id_torre),
    CONSTRAINT ck_carga_periodo CHECK (periodo REGEXP '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_carga_estado CHECK (
        estado IN ('procesada_completa', 'procesada_parcial', 'rechazada', 'reemplazada')
    ),
    INDEX ix_carga_torre_periodo (id_torre, periodo)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS lectura (
    id_lectura BIGINT AUTO_INCREMENT PRIMARY KEY,
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
    CONSTRAINT ck_lectura_periodo CHECK (periodo REGEXP '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    CONSTRAINT ck_lectura_acumulada_no_negativa CHECK (lectura_acumulada >= 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS rechazo (
    id_rechazo BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_carga INT NOT NULL,
    numero_fila INT NOT NULL,
    apartamento VARCHAR(255) NULL,
    servicio VARCHAR(255) NULL,
    periodo VARCHAR(255) NULL,
    motivo VARCHAR(40) NOT NULL,
    valor_recibido VARCHAR(255) NULL,
    CONSTRAINT fk_rechazo_carga FOREIGN KEY (id_carga) REFERENCES carga (id_carga)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre_usuario VARCHAR(50) NOT NULL,
    hash_contrasena VARCHAR(255) NOT NULL,
    ultimo_acceso DATETIME NULL,
    CONSTRAINT uq_usuario_nombre_usuario UNIQUE (nombre_usuario)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

INSERT IGNORE INTO servicio (codigo, nombre, unidad_medida, umbral_desviacion) VALUES
    ('AGUA', 'Agua potable', 'm3', 0.50),
    ('ENERGIA', 'Energia electrica', 'kWh', 0.50);

INSERT IGNORE INTO torre (codigo, nombre) VALUES
    ('T01', 'Torre 1'),
    ('T02', 'Torre 2'),
    ('T03', 'Torre 3');

INSERT IGNORE INTO apartamento (id_torre, numero)
SELECT torre.id_torre, CAST(pisos.piso * 100 + posiciones.posicion AS CHAR)
FROM torre
CROSS JOIN (SELECT 1 AS piso UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5) AS pisos
CROSS JOIN (SELECT 1 AS posicion UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) AS posiciones
WHERE torre.codigo IN ('T01', 'T02', 'T03');

INSERT IGNORE INTO usuario (nombre_usuario, hash_contrasena) VALUES
    ('admin', 'pbkdf2_sha256$600000$cMNbHOE5hvKgXc9xr1DS7w==$4M6TYLOxycQSgcBr2SndHe9CLbtVARcZI_pJIH1WsGc=');

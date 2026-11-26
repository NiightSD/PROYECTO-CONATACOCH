-- =============================================================================
-- CONATACOCH - Esquema relacional MySQL 8.0 / MariaDB >= 10.4
-- Base de datos: conatacoch  |  Motor: InnoDB  |  Juego: utf8mb4_unicode_ci
--
-- Este DDL refleja las migraciones Django 0001_initial + 0002_add_otp_fields
-- + 0003_cliente del proyecto. Django crea ademas sus tablas propias
-- (auth_*, django_*, sessions); aqui se documentan solo las 7 tablas de
-- negocio: Usuarios, Clientes, Conductores, LineasColectivas, Vehiculos,
-- Paraderos y TransaccionesPago.
--
-- Reglas de integridad:
--   * PK BIGINT AUTO_INCREMENT en todas las tablas.
--   * Claves naturales UNIQUE (RUT, email, patente, UUID de pago).
--   * FK con ON DELETE RESTRICT / ON UPDATE RESTRICT (nunca cascada).
--   * Indices B-Tree para busquedas y reportes.
--   * CHECK constraints (MySQL >= 8.0.16 las aplica; MariaDB >= 10.2).
--
-- Uso:
--   mysql -u root -p < docs/schema_mysql.sql
-- (Ejecutar sobre una base vacia; no incluye DROP de datos existentes.)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `conatacoch`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `conatacoch`;

-- -----------------------------------------------------------------------------
-- 1. USUARIOS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `usuario` (
    `id`                 BIGINT       NOT NULL AUTO_INCREMENT,
    `rut`                VARCHAR(12)  NOT NULL COMMENT 'RUT chileno con formato 11.111.111-1',
    `nombre`             VARCHAR(150) NOT NULL,
    `email`              VARCHAR(254) NOT NULL COMMENT 'credencial de login',
    `password_hash`      VARCHAR(128) NOT NULL COMMENT 'Argon2id',
    `rol`                VARCHAR(10)  NOT NULL DEFAULT 'CLIENTE' COMMENT 'ADMIN | CONDUCTOR | CLIENTE',
    `activo`             TINYINT(1)   NOT NULL DEFAULT 1,
    `intentos_fallidos`  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    `bloqueado_hasta`    DATETIME(6)  NULL DEFAULT NULL,
    `is_staff`           TINYINT(1)   NOT NULL DEFAULT 0,
    `is_superuser`       TINYINT(1)   NOT NULL DEFAULT 0,
    `last_login`         DATETIME(6)  NULL DEFAULT NULL,
    `date_joined`        DATETIME(6)  NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_usuario_rut`   (`rut`),
    UNIQUE KEY `uq_usuario_email` (`email`),
    KEY `idx_usuario_rol_activo`  (`rol`, `activo`),
    KEY `idx_usuario_bloqueado`   (`bloqueado_hasta`),
    CONSTRAINT `chk_usuario_intentos` CHECK (`intentos_fallidos` >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Usuarios: ADMIN, CONDUCTOR y CLIENTE (identidad unica)';

-- -----------------------------------------------------------------------------
-- 2. CLIENTES  (perfil 1:1 del pasajero)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `cliente` (
    `id`             BIGINT       NOT NULL AUTO_INCREMENT,
    `usuario_id`     BIGINT       NOT NULL,
    `telefono`       VARCHAR(20)  NOT NULL DEFAULT '',
    `direccion`      VARCHAR(200) NOT NULL DEFAULT '',
    `comuna`         VARCHAR(100) NOT NULL DEFAULT '',
    `fecha_registro` DATETIME(6)  NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_cliente_usuario` (`usuario_id`),
    KEY `idx_cliente_comuna` (`comuna`),
    CONSTRAINT `fk_cliente_usuario`
        FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Datos de contacto del pasajero (rol CLIENTE)';

-- -----------------------------------------------------------------------------
-- 3. LINEAS COLECTIVAS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `linea_colectiva` (
    `id`                BIGINT       NOT NULL AUTO_INCREMENT,
    `region`            SMALLINT UNSIGNED  NOT NULL,
    `folio`             INT UNSIGNED         NOT NULL,
    `tipo_servicio`     VARCHAR(80)  NOT NULL,
    `nombre_recorrido`  VARCHAR(50)  NOT NULL,
    `tipo_trazado`      VARCHAR(20)  NOT NULL DEFAULT 'PRINCIPAL',
    `nombre_origen`     VARCHAR(150) NOT NULL,
    `comuna_origen`     VARCHAR(100) NOT NULL,
    `domicilio_origen`  VARCHAR(200) NOT NULL,
    `nombre_destino`    VARCHAR(150) NOT NULL,
    `comuna_destino`    VARCHAR(100) NOT NULL,
    `domicilio_destino` VARCHAR(200) NOT NULL,
    `tarifa_actual`     DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'CLP',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_linea_folio_recorrido_traza`
        (`folio`, `nombre_recorrido`, `tipo_trazado`),
    KEY `idx_linea_region_folio`   (`region`, `folio`),
    KEY `idx_linea_comuna_origen`  (`comuna_origen`),
    KEY `idx_linea_comuna_destino` (`comuna_destino`),
    KEY `idx_linea_tipo_servicio`  (`tipo_servicio`),
    CONSTRAINT `chk_linea_region_folio` CHECK (`region` >= 1 AND `folio` >= 1)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Recorridos autorizados (dataset de 660 itinerarios)';

-- -----------------------------------------------------------------------------
-- 4. VEHICULOS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `vehiculo` (
    `id`                 BIGINT       NOT NULL AUTO_INCREMENT,
    `patente`            VARCHAR(10)  NOT NULL,
    `marca_modelo`       VARCHAR(120) NOT NULL,
    `capacidad_pasajeros` SMALLINT UNSIGNED NOT NULL DEFAULT 4,
    `linea_id`           BIGINT       NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_vehiculo_patente` (`patente`),
    KEY `idx_vehiculo_linea` (`linea_id`),
    CONSTRAINT `fk_vehiculo_linea`
        FOREIGN KEY (`linea_id`) REFERENCES `linea_colectiva` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `chk_vehiculo_capacidad`
        CHECK (`capacidad_pasajeros` BETWEEN 1 AND 30)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Vehiculos asignados a una linea';

-- -----------------------------------------------------------------------------
-- 5. CONDUCTORES  (perfil 1:1 del conductor)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conductor` (
    `id`                  BIGINT       NOT NULL AUTO_INCREMENT,
    `usuario_id`          BIGINT       NOT NULL,
    `folio_conatacoch`    VARCHAR(20)  NOT NULL,
    `vehiculo_id`         BIGINT       NOT NULL,
    `en_turno`            TINYINT(1)   NOT NULL DEFAULT 0,
    `cupos_disponibles`   SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    `otp_secreto`         VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'TOTP cifrado (Fernet)',
    `otp_codigo`          VARCHAR(10)  NOT NULL DEFAULT '',
    `otp_codigo_expira`   DATETIME(6)  NULL DEFAULT NULL,
    `token_sesion_activa` VARCHAR(128) NOT NULL DEFAULT '' COMMENT 'SHA-256 del token',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_conductor_usuario` (`usuario_id`),
    KEY `idx_conductor_folio`  (`folio_conatacoch`),
    KEY `idx_conductor_turno`  (`en_turno`, `folio_conatacoch`),
    KEY `idx_conductor_vehiculo` (`vehiculo_id`, `en_turno`),
    CONSTRAINT `fk_conductor_usuario`
        FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `fk_conductor_vehiculo`
        FOREIGN KEY (`vehiculo_id`) REFERENCES `vehiculo` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `chk_conductor_cupos`
        CHECK (`cupos_disponibles` BETWEEN 0 AND 30)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Perfil operativo del conductor y estado de su turno';

-- -----------------------------------------------------------------------------
-- 6. PARADEROS
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `paradero` (
    `id`        BIGINT       NOT NULL AUTO_INCREMENT,
    `nombre`    VARCHAR(160) NOT NULL,
    `comuna`    VARCHAR(100) NOT NULL,
    `latitud`   DECIMAL(9,6) NOT NULL,
    `longitud`  DECIMAL(9,6) NOT NULL,
    `linea_id`  BIGINT       NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_paradero_linea_nombre` (`linea_id`, `nombre`),
    KEY `idx_paradero_comuna_linea` (`comuna`, `linea_id`),
    KEY `idx_paradero_geo` (`latitud`, `longitud`),
    CONSTRAINT `fk_paradero_linea`
        FOREIGN KEY (`linea_id`) REFERENCES `linea_colectiva` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `chk_paradero_latitud`  CHECK (`latitud` BETWEEN -90 AND 90),
    CONSTRAINT `chk_paradero_longitud` CHECK (`longitud` BETWEEN -180 AND 180)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Paraderos georreferenciados de cada linea';

-- -----------------------------------------------------------------------------
-- 7. TRANSACCIONES DE PAGO (QR)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `transaccion_pago` (
    `id`              BIGINT        NOT NULL AUTO_INCREMENT,
    `codigo_qr_uuid`  CHAR(32)      NOT NULL COMMENT 'UUID sin guiones del QR',
    `pasajero_id`     BIGINT        NOT NULL,
    `conductor_id`    BIGINT        NOT NULL,
    `linea_id`        BIGINT        NOT NULL,
    `monto`           DECIMAL(12,2) NOT NULL,
    `fecha_hora`      DATETIME(6)   NOT NULL COMMENT 'UTC',
    `estado`          VARCHAR(10)   NOT NULL DEFAULT 'PENDIENTE'
        COMMENT 'PENDIENTE | PAGADO | ANULADO | EXPIRADO',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_pago_codigo_qr` (`codigo_qr_uuid`),
    KEY `idx_pago_conductor_fecha` (`conductor_id`, `fecha_hora`),
    KEY `idx_pago_linea_fecha`     (`linea_id`, `fecha_hora`),
    KEY `idx_pago_pasajero_fecha`  (`pasajero_id`, `fecha_hora`),
    KEY `idx_pago_estado_fecha`    (`estado`, `fecha_hora`),
    CONSTRAINT `fk_pago_pasajero`
        FOREIGN KEY (`pasajero_id`) REFERENCES `usuario` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `fk_pago_conductor`
        FOREIGN KEY (`conductor_id`) REFERENCES `conductor` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `fk_pago_linea`
        FOREIGN KEY (`linea_id`) REFERENCES `linea_colectiva` (`id`)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `chk_pago_monto_positivo` CHECK (`monto` >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = 'Auditoria de pagos QR realizada por el conductor';

-- =============================================================================
-- Consultas de verificacion rapida (opcionales)
-- =============================================================================
-- SELECT COUNT(*) AS usuarios FROM usuario;
-- SELECT COUNT(*) AS lineas FROM linea_colectiva;
-- SELECT COUNT(*) AS paraderos FROM paradero;
-- SELECT estado, COUNT(*) FROM transaccion_pago GROUP BY estado;
-- SELECT u.email, u.rol, c.comuna FROM usuario u
--   LEFT JOIN cliente c ON c.usuario_id = u.id ORDER BY u.id;

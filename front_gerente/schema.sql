CREATE DATABASE IF NOT EXISTS estok
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE estok;

CREATE TABLE IF NOT EXISTS suprimento (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    codigo_interno  VARCHAR(50)  NULL,
    unidade_medida  VARCHAR(30)  NULL,
    descricao       TEXT         NULL,
    estoque_minimo  INT UNSIGNED NOT NULL DEFAULT 0,
    estoque_atual   INT UNSIGNED NOT NULL DEFAULT 0,
    status          TINYINT(1)   NOT NULL DEFAULT 1,   -- 1 = ativo, 0 = inativo
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_suprimento_codigo (codigo_interno),  -- NULL pode repetir, valor preenchido não
    KEY idx_suprimento_nome (nome),
    KEY idx_suprimento_status (status)
) ENGINE=InnoDB;

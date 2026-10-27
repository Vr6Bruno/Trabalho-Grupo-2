CREATE DATABASE IF NOT EXISTS estok
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE estok;

-- ============================================================================
-- 1. ENTIDADE (Multi-tenancy: clientes / empresas / filiais)
-- ============================================================================
CREATE TABLE IF NOT EXISTS entidade (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(150) NOT NULL,
    identificador   VARCHAR(50)  NULL,   -- CNPJ, código ou sigla
    status          TINYINT(1)   NOT NULL DEFAULT 1, -- 1 = ativa, 0 = inativa
    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_entidade_status (status)
) ENGINE=InnoDB;

-- ============================================================================
-- 2. PERFIL (Perfis de acesso ao sistema)
-- ============================================================================
CREATE TABLE IF NOT EXISTS perfil (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    codigo          VARCHAR(30)  NOT NULL UNIQUE, -- SUPER_ADMIN, GERENTE, ESTOQUISTA, SOLICITANTE
    nome            VARCHAR(50)  NOT NULL,
    descricao       VARCHAR(255) NULL,
    nivel_acesso    INT          NOT NULL DEFAULT 1
) ENGINE=InnoDB;

-- ============================================================================
-- 3. USUARIO (Usuários do sistema autenticados por LOGIN e SENHA - estilo GLPI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS usuario (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entidade_id     INT UNSIGNED NULL,        -- NULL apenas para SUPER_ADMIN global
    perfil_id       INT UNSIGNED NOT NULL,
    login           VARCHAR(50)  NOT NULL UNIQUE, -- Nome de usuário para login (ex: admin, gerente)
    nome            VARCHAR(150) NOT NULL,        -- Nome completo de exibição
    email           VARCHAR(150) NULL,
    senha_hash      VARCHAR(255) NOT NULL,
    status          TINYINT(1)   NOT NULL DEFAULT 1, -- 1 = ativo, 0 = inativo
    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_usuario_login (login),
    KEY idx_usuario_entidade (entidade_id),
    KEY idx_usuario_perfil (perfil_id),
    KEY idx_usuario_status (status),
    CONSTRAINT fk_usuario_entidade FOREIGN KEY (entidade_id) REFERENCES entidade (id) ON DELETE RESTRICT,
    CONSTRAINT fk_usuario_perfil FOREIGN KEY (perfil_id) REFERENCES perfil (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 3.1 USUARIO_PERFIL (Múltiplos perfis associados a um usuário - estilo GLPI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS usuario_perfil (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT UNSIGNED NOT NULL,
    perfil_id  INT UNSIGNED NOT NULL,
    criado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_usuario_perfil (usuario_id, perfil_id),
    CONSTRAINT fk_up_usuario FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE CASCADE,
    CONSTRAINT fk_up_perfil FOREIGN KEY (perfil_id) REFERENCES perfil (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- 4. SUPRIMENTO (Recursos gerenciados isolados por entidade)
-- ============================================================================

CREATE TABLE IF NOT EXISTS suprimento (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entidade_id     INT UNSIGNED NOT NULL,
    nome            VARCHAR(150) NOT NULL,
    codigo_interno  VARCHAR(50)  NULL,
    unidade_medida  VARCHAR(30)  NULL,
    descricao       TEXT         NULL,
    estoque_minimo  INT UNSIGNED NOT NULL DEFAULT 0,
    estoque_atual   INT UNSIGNED NOT NULL DEFAULT 0,
    status          TINYINT(1)   NOT NULL DEFAULT 1,   -- 1 = ativo, 0 = inativo
    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_suprimento_entidade_codigo (entidade_id, codigo_interno),
    KEY idx_suprimento_entidade (entidade_id),
    KEY idx_suprimento_nome (nome),
    KEY idx_suprimento_status (status),
    CONSTRAINT fk_suprimento_entidade FOREIGN KEY (entidade_id) REFERENCES entidade (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================================
-- 5. MOVIMENTAÇÃO DE ESTOQUE (Histórico rastreável de entradas e saídas)
-- ============================================================================
CREATE TABLE IF NOT EXISTS movimentacao_estoque (
    id                  INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entidade_id         INT UNSIGNED NOT NULL,
    suprimento_id       INT UNSIGNED NOT NULL,
    tipo                ENUM('entrada', 'saida', 'ajuste', 'transferencia') NOT NULL,
    quantidade          INT          NOT NULL,
    quantidade_anterior INT          NOT NULL,
    quantidade_posterior INT         NOT NULL,
    solicitacao_id      INT UNSIGNED NULL,
    usuario_id          INT UNSIGNED NOT NULL,
    observacao          TEXT         NULL,
    criado_em           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_mov_entidade (entidade_id),
    KEY idx_mov_suprimento (suprimento_id),
    KEY idx_mov_usuario (usuario_id),
    KEY idx_mov_tipo (tipo),
    CONSTRAINT fk_mov_entidade FOREIGN KEY (entidade_id) REFERENCES entidade (id) ON DELETE CASCADE,
    CONSTRAINT fk_mov_suprimento FOREIGN KEY (suprimento_id) REFERENCES suprimento (id) ON DELETE CASCADE,
    CONSTRAINT fk_mov_usuario FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 6. SOLICITAÇÃO (Pedidos de suprimentos com ciclo de vida de estados)
-- ============================================================================
CREATE TABLE IF NOT EXISTS solicitacao (
    id                      INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entidade_id             INT UNSIGNED NOT NULL,
    solicitante_id          INT UNSIGNED NOT NULL,
    status                  ENUM(
        'solicitada',
        'em_validacao',
        'aprovada',
        'rejeitada',
        'aguardando_estoque',
        'separada',
        'entregue',
        'cancelada'
    ) NOT NULL DEFAULT 'solicitada',
    observacao              TEXT         NULL,
    justificativa_rejeicao  TEXT         NULL,
    validador_id            INT UNSIGNED NULL,
    data_validacao          DATETIME     NULL,
    responsavel_entrega_id  INT UNSIGNED NULL,
    data_entrega            DATETIME     NULL,
    criado_em               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_solicitacao_entidade (entidade_id),
    KEY idx_solicitacao_solicitante (solicitante_id),
    KEY idx_solicitacao_status (status),
    CONSTRAINT fk_solicitacao_entidade FOREIGN KEY (entidade_id) REFERENCES entidade (id) ON DELETE CASCADE,
    CONSTRAINT fk_solicitacao_solicitante FOREIGN KEY (solicitante_id) REFERENCES usuario (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 7. ITENS DA SOLICITAÇÃO
-- ============================================================================
CREATE TABLE IF NOT EXISTS item_solicitacao (
    id                   INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    solicitacao_id       INT UNSIGNED NOT NULL,
    suprimento_id        INT UNSIGNED NOT NULL,
    quantidade_solicitada INT UNSIGNED NOT NULL DEFAULT 1,
    quantidade_atendida  INT UNSIGNED NOT NULL DEFAULT 0,
    status               ENUM('pendente', 'aprovado', 'separado', 'atendido', 'cancelado') NOT NULL DEFAULT 'pendente',
    KEY idx_item_solicitacao (solicitacao_id),
    KEY idx_item_suprimento (suprimento_id),
    CONSTRAINT fk_item_solicitacao FOREIGN KEY (solicitacao_id) REFERENCES solicitacao (id) ON DELETE CASCADE,
    CONSTRAINT fk_item_suprimento FOREIGN KEY (suprimento_id) REFERENCES suprimento (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 8. HISTÓRICO / EVENTOS DA SOLICITAÇÃO (Rastreabilidade)
-- ============================================================================
CREATE TABLE IF NOT EXISTS historico_solicitacao (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    solicitacao_id  INT UNSIGNED NOT NULL,
    usuario_id      INT UNSIGNED NOT NULL,
    estado_anterior VARCHAR(50)  NULL,
    estado_novo     VARCHAR(50)  NOT NULL,
    descricao       TEXT         NULL,
    criado_em       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_hist_solicitacao (solicitacao_id),
    KEY idx_hist_usuario (usuario_id),
    CONSTRAINT fk_hist_solicitacao FOREIGN KEY (solicitacao_id) REFERENCES solicitacao (id) ON DELETE CASCADE,
    CONSTRAINT fk_hist_usuario FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 9. PEDIDOS DE COMPRA (Reposição de estoque inspirada no plugin GLPI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS pedido_compra (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entidade_id     INT UNSIGNED NOT NULL,
    usuario_id      INT UNSIGNED NOT NULL,
    nome            VARCHAR(255) NOT NULL,
    status          ENUM('em_montagem', 'aguardando_cotacao', 'pedido_realizado', 'parcialmente_recebido', 'recebido', 'cancelado') NOT NULL DEFAULT 'em_montagem',
    observacao      TEXT NULL,
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_pedido_entidade (entidade_id),
    KEY idx_pedido_status (status),
    CONSTRAINT fk_pedido_entidade FOREIGN KEY (entidade_id) REFERENCES entidade (id) ON DELETE CASCADE,
    CONSTRAINT fk_pedido_usuario FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 10. ITENS DO PEDIDO DE COMPRA
-- ============================================================================
CREATE TABLE IF NOT EXISTS item_pedido_compra (
    id                    INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    pedido_id             INT UNSIGNED NOT NULL,
    suprimento_id         INT UNSIGNED NOT NULL,
    quantidade_necessaria INT UNSIGNED NOT NULL DEFAULT 1,
    quantidade_pedida     INT UNSIGNED NOT NULL DEFAULT 0,
    quantidade_recebida   INT UNSIGNED NOT NULL DEFAULT 0,
    observacao            TEXT NULL,
    KEY idx_item_pedido (pedido_id),
    KEY idx_item_pedido_suprimento (suprimento_id),
    CONSTRAINT fk_item_pedido FOREIGN KEY (pedido_id) REFERENCES pedido_compra (id) ON DELETE CASCADE,
    CONSTRAINT fk_item_pedido_suprimento FOREIGN KEY (suprimento_id) REFERENCES suprimento (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- SEED DATA (Perfis, Entidade Matriz e Usuários Padrão)
-- ============================================================================

-- Perfis padrão
INSERT INTO perfil (id, codigo, nome, descricao, nivel_acesso) VALUES
(1, 'SUPER_ADMIN', 'Super-Admin',   'Acesso irrestrito a todas as entidades, usuários e configurações', 100),
(2, 'GERENTE',     'Gerente',       'Gerencia catálogo de suprimentos, valida solicitações e consulta relatórios da sua entidade', 50),
(3, 'GESTOR',      'Gestor',        'Responsável pela validação, separação e controle físico de estoque da sua entidade', 30),
(4, 'SOLICITANTE', 'Solicitante',   'Cria e acompanha solicitações de recursos para o seu setor', 10),
(5, 'ADMIN',       'Administrador', 'Administrador da entidade/empresa. Gerencia usuários e recursos da sua entidade', 80)
ON DUPLICATE KEY UPDATE codigo = VALUES(codigo), nome = VALUES(nome), descricao = VALUES(descricao), nivel_acesso = VALUES(nivel_acesso);

-- Entidade Matriz inicial
INSERT INTO entidade (id, nome, identificador, status) VALUES
(1, 'Estok Matriz', 'MATRIZ-01', 1)
ON DUPLICATE KEY UPDATE nome = VALUES(nome);

-- Usuários padrão
-- login: admin / senha: admin123 (Super-Admin)
-- login: admin.entidade / senha: admin123 (Administrador da Entidade)
-- login: gerente / senha: gerente123 (Gerente)
-- login: gestor / senha: gestor123 (Gestor de Estoque)
-- login: solicitante / senha: solicitante123 (Solicitante)
INSERT INTO usuario (id, entidade_id, perfil_id, login, nome, email, senha_hash, status) VALUES
(1, NULL, 1, 'admin', 'Super Administrador', 'admin@estok.com', 'scrypt:32768:8:1$UenUtwdnhGxU2Gi9$296ee8e9dc05c4530f2f1369130acbeeaaf545391a230a6268dea407bb03659d0fbe2697b35b9fe4cbf8b2056e8ffb717c61263a94d0bba9ce64de76cbec2d02', 1),
(2, 1,    2, 'gerente', 'Gerente de Suprimentos', 'gerente@estok.com', 'scrypt:32768:8:1$PXvQDB9q5n5bnHnj$9216e50d35b07612aa1b0de7b5540095378261b21c00afc9bf6191221ec845b5ca1fbb0df99a17d98d700a862b6e4396fd788a2de5f91a842cd0d8f14b00994a', 1),
(4, 1,    5, 'admin.entidade', 'Administrador da Entidade', 'admin.entidade@estok.com', 'scrypt:32768:8:1$UenUtwdnhGxU2Gi9$296ee8e9dc05c4530f2f1369130acbeeaaf545391a230a6268dea407bb03659d0fbe2697b35b9fe4cbf8b2056e8ffb717c61263a94d0bba9ce64de76cbec2d02', 1),
(5, 1,    3, 'gestor', 'Gestor de Estoque', 'gestor@estok.com', 'scrypt:32768:8:1$PXvQDB9q5n5bnHnj$9216e50d35b07612aa1b0de7b5540095378261b21c00afc9bf6191221ec845b5ca1fbb0df99a17d98d700a862b6e4396fd788a2de5f91a842cd0d8f14b00994a', 1),
(6, 1,    4, 'solicitante', 'Solicitante Setor TI', 'solicitante@estok.com', 'scrypt:32768:8:1$PXvQDB9q5n5bnHnj$9216e50d35b07612aa1b0de7b5540095378261b21c00afc9bf6191221ec845b5ca1fbb0df99a17d98d700a862b6e4396fd788a2de5f91a842cd0d8f14b00994a', 1)
ON DUPLICATE KEY UPDATE
    perfil_id = VALUES(perfil_id),
    entidade_id = VALUES(entidade_id),
    nome = VALUES(nome),
    senha_hash = VALUES(senha_hash),
    status = VALUES(status);

-- Associação dos perfis aos usuários
INSERT INTO usuario_perfil (usuario_id, perfil_id) VALUES
(1, 1), (1, 5), (1, 2), (1, 3), (1, 4),
(2, 2), (2, 4),
(4, 5),
(5, 3),
(6, 4)
ON DUPLICATE KEY UPDATE perfil_id = VALUES(perfil_id);

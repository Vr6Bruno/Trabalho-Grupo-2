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
-- ============================================================================
-- SEED DATA COMPLETO (Ambiente Pré-configurado para Demonstração e Testes)
-- ============================================================================
-- OBSERVAÇÃO: A senha de TODOS os usuários cadastrados é '123'
-- Exemplo: login = michel.salles, senha = 123 | login = admin, senha = 123
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- Dados para a tabela `perfil`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `perfil` (`id`, `codigo`, `nome`, `descricao`, `nivel_acesso`) VALUES
(1, 'SUPER_ADMIN', 'Super-Admin', 'Acesso irrestrito a todas as entidades, usuários e configurações', 100),
(2, 'GERENTE', 'Gerente', 'Gerencia catálogo de suprimentos, valida solicitações e consulta relatórios da sua entidade', 50),
(3, 'GESTOR', 'Gestor', 'Responsável pela validação, separação e controle físico de estoque da sua entidade', 30),
(4, 'SOLICITANTE', 'Solicitante', 'Cria e acompanha solicitações de recursos para o seu setor', 10),
(5, 'ADMIN', 'Administrador', 'Administrador da entidade/empresa. Gerencia usuários e recursos da sua entidade.', 80);

-- ----------------------------------------------------------------------------
-- Dados para a tabela `entidade`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `entidade` (`id`, `nome`, `identificador`, `status`, `criado_em`, `atualizado_em`) VALUES
(1, 'Estok Matriz (Vitória)', 'MATRIZ-VIX', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(2, 'UVV - Campus Boa Vista', 'UVV-BOAVISTA', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(3, 'Logística & Distribuição Serra', 'LOG-SERRA', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(4, 'Hospital Santa Maria', 'HOSP-SM', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(5, 'Indústria & Manutenção Cariacica', 'IND-CAR', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `usuario`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `usuario` (`id`, `entidade_id`, `perfil_id`, `login`, `nome`, `email`, `senha_hash`, `status`, `criado_em`, `atualizado_em`) VALUES
(1, NULL, 1, 'admin', 'Super Administrador', 'admin@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(2, 1, 5, 'michel.salles', 'Michel Salles', 'michel.salles@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(3, 1, 5, 'admin.entidade', 'Administrador da Entidade', 'admin.entidade@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(4, 1, 2, 'gerente', 'Gerente de Suprimentos', 'gerente@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(5, 1, 3, 'gestor', 'Gestor de Almoxarifado', 'gestor@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(6, 1, 4, 'solicitante', 'Solicitante Geral', 'solicitante@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(7, 1, 5, 'carla.mendes', 'Carla Mendes', 'carla.mendes@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(8, 1, 2, 'rodrigo.almeida', 'Rodrigo Almeida', 'rodrigo.almeida@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(9, 1, 3, 'felipe.costa', 'Felipe Costa', 'felipe.costa@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(10, 1, 4, 'patricia.souza', 'Patrícia Souza', 'patricia.souza@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(11, 1, 4, 'lucas.ferreira', 'Lucas Ferreira', 'lucas.ferreira@estok.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(12, 2, 5, 'bruno.torres', 'Bruno Torres', 'bruno.torres@uvv.br', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(13, 2, 2, 'marcos.professor', 'Marcos Aurélio', 'marcos.aurelio@uvv.br', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(14, 2, 3, 'mariana.ribeiro', 'Mariana Ribeiro', 'mariana.ribeiro@uvv.br', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(15, 2, 4, 'juliana.lima', 'Juliana Lima', 'juliana.lima@uvv.br', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(16, 2, 4, 'thiago.santos', 'Thiago Santos', 'thiago.santos@uvv.br', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(17, 3, 5, 'marcos.oliveira', 'Marcos Oliveira', 'marcos.oliveira@logserra.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(18, 3, 2, 'aline.castro', 'Aline Castro', 'aline.castro@logserra.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(19, 3, 3, 'andre.martins', 'André Martins', 'andre.martins@logserra.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(20, 3, 4, 'gabriel.duarte', 'Gabriel Duarte', 'gabriel.duarte@logserra.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11');
INSERT IGNORE INTO `usuario` (`id`, `entidade_id`, `perfil_id`, `login`, `nome`, `email`, `senha_hash`, `status`, `criado_em`, `atualizado_em`) VALUES
(21, 4, 5, 'beatriz.nunes', 'Beatriz Nunes', 'beatriz.nunes@hospitalsm.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(22, 4, 2, 'fernando.dias', 'Dr. Fernando Dias', 'fernando.dias@hospitalsm.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(23, 4, 3, 'renata.barbosa', 'Renata Barbosa', 'renata.barbosa@hospitalsm.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(24, 4, 4, 'camila.vieira', 'Enf. Camila Vieira', 'camila.vieira@hospitalsm.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(25, 4, 4, 'diego.moreira', 'Diego Moreira', 'diego.moreira@hospitalsm.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(26, 5, 5, 'eduardo.ramos', 'Eduardo Ramos', 'eduardo.ramos@indcariacica.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(27, 5, 2, 'vanessa.pires', 'Eng. Vanessa Pires', 'vanessa.pires@indcariacica.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(28, 5, 3, 'leandro.gomes', 'Leandro Gomes', 'leandro.gomes@indcariacica.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(29, 5, 4, 'marcelo.teixeira', 'Marcelo Teixeira', 'marcelo.teixeira@indcariacica.com', 'scrypt:32768:8:1$8chdVlp6lNDMcGX9$1c1e483dc83bd3abdf3e2cdc26dfbb0e972d4e8303f4c98fa97ffb7505f410d787a8991f0771cc771b1b991743a09a49d203046031276a9044e6a53324bde59d', 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `usuario_perfil`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `usuario_perfil` (`id`, `usuario_id`, `perfil_id`, `criado_em`) VALUES
(1, 1, 1, '2026-11-05 15:10:11'),
(2, 1, 5, '2026-11-05 15:10:11'),
(3, 1, 2, '2026-11-05 15:10:11'),
(4, 1, 3, '2026-11-05 15:10:11'),
(5, 1, 4, '2026-11-05 15:10:11'),
(6, 2, 5, '2026-11-05 15:10:11'),
(7, 2, 2, '2026-11-05 15:10:11'),
(8, 2, 3, '2026-11-05 15:10:11'),
(9, 2, 4, '2026-11-05 15:10:11'),
(10, 3, 5, '2026-11-05 15:10:11'),
(11, 4, 2, '2026-11-05 15:10:11'),
(12, 5, 3, '2026-11-05 15:10:11'),
(13, 6, 4, '2026-11-05 15:10:11'),
(14, 7, 5, '2026-11-05 15:10:11'),
(15, 8, 2, '2026-11-05 15:10:11'),
(16, 9, 3, '2026-11-05 15:10:11'),
(17, 10, 4, '2026-11-05 15:10:11'),
(18, 11, 4, '2026-11-05 15:10:11'),
(19, 12, 5, '2026-11-05 15:10:11'),
(20, 12, 2, '2026-11-05 15:10:11');
INSERT IGNORE INTO `usuario_perfil` (`id`, `usuario_id`, `perfil_id`, `criado_em`) VALUES
(21, 13, 2, '2026-11-05 15:10:11'),
(22, 14, 3, '2026-11-05 15:10:11'),
(23, 15, 4, '2026-11-05 15:10:11'),
(24, 16, 4, '2026-11-05 15:10:11'),
(25, 17, 5, '2026-11-05 15:10:11'),
(26, 18, 2, '2026-11-05 15:10:11'),
(27, 19, 3, '2026-11-05 15:10:11'),
(28, 20, 4, '2026-11-05 15:10:11'),
(29, 21, 5, '2026-11-05 15:10:11'),
(30, 22, 2, '2026-11-05 15:10:11'),
(31, 23, 3, '2026-11-05 15:10:11'),
(32, 24, 4, '2026-11-05 15:10:11'),
(33, 25, 4, '2026-11-05 15:10:11'),
(34, 26, 5, '2026-11-05 15:10:11'),
(35, 27, 2, '2026-11-05 15:10:11'),
(36, 28, 3, '2026-11-05 15:10:11'),
(37, 29, 4, '2026-11-05 15:10:11');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `suprimento`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `suprimento` (`id`, `entidade_id`, `nome`, `codigo_interno`, `unidade_medida`, `descricao`, `estoque_minimo`, `estoque_atual`, `status`, `criado_em`, `atualizado_em`) VALUES
(1, 1, 'Cabo de Rede UTP Cat6 100% Cobre', 'INF-001', 'cx', 'Caixa com 305 metros cabo azul homologado Anatel', 5, 12, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(2, 1, 'Conector RJ45 Cat6 Macho Blindado', 'INF-002', 'pct', 'Pacote com 100 unidades banhado a ouro', 10, 28, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(3, 1, 'Teclado USB Padrão ABNT2 Preto', 'INF-003', 'un', 'Teclado membrana USB resistente a respingos', 15, 8, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(4, 1, 'Mouse Óptico USB 1200 DPI Preto', 'INF-004', 'un', 'Mouse ergonômico 3 botões com scroll', 15, 6, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(5, 1, 'SSD NVMe 500GB M.2 PCIe 4.0', 'INF-005', 'un', 'Armazenamento alta velocidade para desktops', 8, 14, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(6, 1, 'Toner Compatível HP W1105A / 105A', 'INF-006', 'un', 'Cartucho toner preto rendimento 1.000 páginas', 6, 3, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(7, 1, 'Papel Sulfite A4 75g Caixa 10 Resmas', 'ESC-001', 'cx', 'Caixa com 5.000 folhas brancas 75g/m²', 20, 45, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(8, 1, 'Caneta Esferográfica Azul 1.0mm', 'ESC-002', 'cx', 'Caixa com 50 canetas corpo transparente', 10, 25, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(9, 1, 'Bloco Autoadesivo Amarelo 76x76mm', 'ESC-003', 'pct', 'Bloco tipo Post-it com 100 folhas', 20, 18, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(10, 1, 'Álcool 70% Líquido Galão 5L', 'LIMP-001', 'gl', 'Galão de álcool etílico hidratado 70° INPM', 10, 22, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(11, 1, 'Café em Pó Tradicional 500g', 'COPA-001', 'pct', 'Pacote de café a vácuo torrado e moído', 15, 30, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(12, 1, 'Papel Toalha Interfolhado 2 Dobras', 'LIMP-002', 'fardo', 'Fardo com 1.000 folhas celulose virgem', 12, 10, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(13, 2, 'Papel Sulfite A4 75g Caixa 10 Resmas', 'UVV-ESC-01', 'cx', 'Caixa com 10 resmas para impressões da coordenação', 25, 60, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(14, 2, 'Pincel Atômico para Quadro Branco Azul', 'UVV-ESC-02', 'cx', 'Caixa com 12 marcadores recarregáveis', 15, 40, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(15, 2, 'Apagador para Quadro Branco com Feltro', 'UVV-ESC-03', 'un', 'Apagador magnético com porta-marcador', 10, 25, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(16, 2, 'Cabo HDMI 2.0 Blindado 3 Metros', 'UVV-INF-01', 'un', 'Cabo para ligação de projetores e TVs das salas', 12, 5, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(17, 2, 'Mouse Óptico USB 1200 DPI', 'UVV-INF-02', 'un', 'Para reposição nos laboratórios de informática', 20, 15, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(18, 2, 'Pilha Alcalina AAA Palito (Blister c/ 4)', 'UVV-ELE-01', 'pct', 'Para controles remotos de ar condicionado e laser', 30, 12, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(19, 3, 'Fita Adesiva Transparente 48mm x 100m', 'LOG-EMB-01', 'rolo', 'Fita larga para fechamento de caixas pesadas', 50, 120, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(20, 3, 'Filme Stretch Manual 500mm x 0,25mm', 'LOG-EMB-02', 'bobina', 'Bobina de 3.5kg para paletização de cargas', 20, 15, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11');
INSERT IGNORE INTO `suprimento` (`id`, `entidade_id`, `nome`, `codigo_interno`, `unidade_medida`, `descricao`, `estoque_minimo`, `estoque_atual`, `status`, `criado_em`, `atualizado_em`) VALUES
(21, 3, 'Estilete Profissional com Trava 18mm', 'LOG-FER-01', 'un', 'Estilete reforçado para corte de caixas e filmes', 15, 30, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(22, 3, 'Luva de Proteção Pu Tátil Tamanho G', 'LOG-EPI-01', 'par', 'Luva tricotada banhada em poliuretano na palma', 40, 85, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(23, 3, 'Etiqueta Térmica Adesiva 100x150mm', 'LOG-ETI-01', 'rolo', 'Rolo com 500 etiquetas para envio e despacho', 30, 22, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(24, 4, 'Luva de Procedimento Nitrílica M', 'HOSP-001', 'cx', 'Caixa com 100 luvas sem pó na cor azul', 100, 250, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(25, 4, 'Máscara Descartável Cirúrgica Tripla', 'HOSP-002', 'cx', 'Caixa com 50 máscaras descartáveis com elástico', 80, 180, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(26, 4, 'Álcool em Gel 70% com Dosador 500ml', 'HOSP-003', 'frasco', 'Frasco com pump para bancadas e leitos', 50, 35, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(27, 4, 'Avental Descartável Manga Longa Gr30', 'HOSP-004', 'pct', 'Pacote com 10 aventais TNT hospitalares', 40, 20, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(28, 4, 'Seringa Descartável 10ml com Agulha', 'HOSP-005', 'cx', 'Caixa com 100 seringas bico luer slip', 60, 110, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(29, 5, 'Fita Isolante 3M Scotch 20 Metros', 'IND-ELE-01', 'un', 'Fita isolante antichama classe A até 750V', 30, 70, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(30, 5, 'Óleo Lubrificante Spray WD-40 300ml', 'IND-MAN-01', 'lata', 'Spray desengripante e protetivo antiferrugem', 20, 14, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(31, 5, 'Abraçadeira de Nylon 200x3.6mm Preto', 'IND-ELE-02', 'pct', 'Pacote com 100 abraçadeiras tipo enforca-gato', 25, 60, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11'),
(32, 5, 'Óculos de Proteção Incolor Antirrisco', 'IND-EPI-01', 'un', 'Óculos de segurança com proteção UV', 20, 18, 1, '2026-11-05 15:10:11', '2026-11-05 15:10:11');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `solicitacao`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `solicitacao` (`id`, `entidade_id`, `solicitante_id`, `status`, `observacao`, `justificativa_rejeicao`, `validador_id`, `data_validacao`, `responsavel_entrega_id`, `data_entrega`, `criado_em`, `atualizado_em`) VALUES
(1, 1, 10, 'solicitada', 'Solicitação mensal de materiais para o setor de faturamento e contas a pagar.', NULL, NULL, NULL, NULL, NULL, '2026-11-04 13:10:10', '2026-11-04 13:10:10'),
(2, 1, 11, 'solicitada', 'Cabos e conectores para cabeamento estruturado da nova sala de reuniões.', NULL, NULL, NULL, NULL, NULL, '2026-11-05 07:10:10', '2026-11-05 07:10:10'),
(3, 2, 15, 'solicitada', 'Reposição de papéis e marcadores para início das bancas examinadoras.', NULL, NULL, NULL, NULL, NULL, '2026-11-04 08:10:10', '2026-11-04 08:10:10'),
(4, 4, 24, 'solicitada', 'Solicitação urgente de luvas cirúrgicas e máscaras para a ala de pronto socorro.', NULL, NULL, NULL, NULL, NULL, '2026-11-05 07:10:10', '2026-11-05 07:10:10'),
(5, 1, 6, 'aprovada', 'Reposição de café e insumos de limpeza para copa do segundo andar.', NULL, 4, '2026-11-03 12:10:10', NULL, NULL, '2026-11-03 09:10:10', '2026-11-03 12:10:10'),
(6, 2, 16, 'aprovada', 'Substituição de mouses quebrados no Laboratório 3 de Ciência da Computação.', NULL, 12, '2026-11-03 17:10:10', NULL, NULL, '2026-11-03 14:10:10', '2026-11-03 17:10:10'),
(7, 3, 20, 'aprovada', 'Fitas e estiletes para embalagem de remessa especial para filial.', NULL, 18, '2026-11-02 15:10:10', NULL, NULL, '2026-11-02 12:10:10', '2026-11-02 15:10:10'),
(8, 5, 29, 'aprovada', 'Fitas isolantes e abraçadeiras para reforma do painel elétrico da prensa 02.', NULL, 27, '2026-11-04 12:10:10', NULL, NULL, '2026-11-04 09:10:10', '2026-11-04 12:10:10'),
(9, 1, 11, 'aguardando_estoque', 'Teclados e mouses para montagem dos novos postos de atendimento.', NULL, 4, '2026-11-01 10:10:10', NULL, NULL, '2026-11-01 07:10:10', '2026-11-01 10:10:10'),
(10, 2, 16, 'aguardando_estoque', 'Cabos HDMI para os auditórios 01 e 02.', NULL, 12, '2026-10-31 11:10:10', NULL, NULL, '2026-10-31 08:10:10', '2026-10-31 11:10:10'),
(11, 4, 25, 'aguardando_estoque', 'Aventais descartáveis para equipe do centro cirúrgico ambulatorial.', NULL, 22, '2026-11-02 10:10:10', NULL, NULL, '2026-11-02 07:10:10', '2026-11-02 10:10:10'),
(12, 1, 2, 'separada', 'Toners e papéis especiais para impressão de relatórios de diretoria.', NULL, 4, '2026-11-02 10:10:10', NULL, NULL, '2026-11-02 07:10:10', '2026-11-02 10:10:10'),
(13, 3, 20, 'separada', 'Luvas táteis e estiletes para os novos operadores do turno da noite.', NULL, 18, '2026-11-03 16:10:10', NULL, NULL, '2026-11-03 13:10:10', '2026-11-03 16:10:10'),
(14, 5, 29, 'separada', 'Sprays desengripantes e óculos de proteção para manutenção preventiva.', NULL, 27, '2026-11-03 16:10:10', NULL, NULL, '2026-11-03 13:10:10', '2026-11-03 16:10:10'),
(15, 1, 10, 'entregue', 'Kit mensal de papelaria e suprimentos administrativos de rotina.', NULL, 4, '2026-10-24 16:10:10', 5, '2026-10-24 21:10:10', '2026-10-24 13:10:10', '2026-10-24 21:10:10'),
(16, 1, 11, 'entregue', 'SSDs para upgrade de máquinas do departamento comercial.', NULL, 4, '2026-10-21 15:10:10', 5, '2026-10-21 20:10:10', '2026-10-21 12:10:10', '2026-10-21 20:10:10'),
(17, 2, 15, 'entregue', 'Pilhas e apagadores para o bloco acadêmico C.', NULL, 12, '2026-10-26 16:10:10', 14, '2026-10-26 21:10:10', '2026-10-26 13:10:10', '2026-10-26 21:10:10'),
(18, 4, 24, 'entregue', 'Seringas e luvas de procedimento para o ambulatório geral.', NULL, 22, '2026-10-28 10:10:10', 23, '2026-10-28 15:10:10', '2026-10-28 07:10:10', '2026-10-28 15:10:10'),
(19, 1, 6, 'rejeitada', 'Solicitação extraordinária de 20 teclados mecânicos para testes.', 'Pedido rejeitado pois não há previsão orçamentária para este tipo de equipamento neste trimestre.', 4, '2026-10-30 16:10:10', NULL, NULL, '2026-10-30 13:10:10', '2026-10-30 16:10:10'),
(20, 3, 20, 'cancelada', 'Bobinas de filme stretch para evento externo.', 'Solicitação cancelada pelo próprio solicitante devido ao cancelamento do evento.', NULL, NULL, NULL, NULL, '2026-10-29 08:10:10', '2026-10-29 08:10:10');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `item_solicitacao`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `item_solicitacao` (`id`, `solicitacao_id`, `suprimento_id`, `quantidade_solicitada`, `quantidade_atendida`, `status`) VALUES
(1, 1, 7, 4, 0, 'pendente'),
(2, 1, 8, 2, 0, 'pendente'),
(3, 1, 9, 3, 0, 'pendente'),
(4, 2, 1, 1, 0, 'pendente'),
(5, 2, 2, 2, 0, 'pendente'),
(6, 3, 13, 5, 0, 'pendente'),
(7, 3, 14, 3, 0, 'pendente'),
(8, 4, 24, 15, 0, 'pendente'),
(9, 4, 25, 10, 0, 'pendente'),
(10, 5, 10, 2, 0, 'aprovado'),
(11, 5, 11, 4, 0, 'aprovado'),
(12, 5, 12, 3, 0, 'aprovado'),
(13, 6, 17, 8, 0, 'aprovado'),
(14, 7, 19, 12, 0, 'aprovado'),
(15, 7, 21, 4, 0, 'aprovado'),
(16, 8, 29, 6, 0, 'aprovado'),
(17, 8, 31, 3, 0, 'aprovado'),
(18, 9, 3, 8, 4, 'separado'),
(19, 9, 4, 8, 4, 'separado'),
(20, 10, 16, 8, 3, 'separado');
INSERT IGNORE INTO `item_solicitacao` (`id`, `solicitacao_id`, `suprimento_id`, `quantidade_solicitada`, `quantidade_atendida`, `status`) VALUES
(21, 11, 27, 20, 10, 'separado'),
(22, 12, 6, 2, 2, 'separado'),
(23, 12, 7, 3, 3, 'separado'),
(24, 13, 21, 5, 5, 'separado'),
(25, 13, 22, 10, 10, 'separado'),
(26, 14, 30, 4, 4, 'separado'),
(27, 14, 32, 6, 6, 'separado'),
(28, 15, 7, 6, 6, 'atendido'),
(29, 15, 8, 4, 4, 'atendido'),
(30, 15, 9, 5, 5, 'atendido'),
(31, 16, 5, 4, 4, 'atendido'),
(32, 17, 15, 6, 6, 'atendido'),
(33, 17, 18, 10, 10, 'atendido'),
(34, 18, 24, 25, 25, 'atendido'),
(35, 18, 28, 15, 15, 'atendido'),
(36, 19, 3, 20, 0, 'cancelado'),
(37, 20, 20, 5, 0, 'cancelado');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `historico_solicitacao`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `historico_solicitacao` (`id`, `solicitacao_id`, `usuario_id`, `estado_anterior`, `estado_novo`, `descricao`, `criado_em`) VALUES
(1, 1, 10, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-04 13:10:10'),
(2, 2, 11, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-05 07:10:10'),
(3, 3, 15, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-04 08:10:10'),
(4, 4, 24, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-05 07:10:10'),
(5, 5, 6, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-03 09:10:10'),
(6, 5, 4, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-03 12:10:10'),
(7, 6, 16, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-03 14:10:10'),
(8, 6, 12, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-03 17:10:10'),
(9, 7, 20, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-02 12:10:10'),
(10, 7, 18, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-02 15:10:10'),
(11, 8, 29, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-04 09:10:10'),
(12, 8, 27, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-04 12:10:10'),
(13, 9, 11, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-01 07:10:10'),
(14, 9, 4, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-01 10:10:10'),
(15, 9, 4, 'aprovada', 'aguardando_estoque', 'Separação física parcial realizada. Aguardando reposição de estoque.', '2026-11-01 12:10:10'),
(16, 10, 16, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-31 08:10:10'),
(17, 10, 12, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-10-31 11:10:10'),
(18, 10, 12, 'aprovada', 'aguardando_estoque', 'Separação física parcial realizada. Aguardando reposição de estoque.', '2026-10-31 13:10:10'),
(19, 11, 25, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-02 07:10:10'),
(20, 11, 22, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-02 10:10:10');
INSERT IGNORE INTO `historico_solicitacao` (`id`, `solicitacao_id`, `usuario_id`, `estado_anterior`, `estado_novo`, `descricao`, `criado_em`) VALUES
(21, 11, 22, 'aprovada', 'aguardando_estoque', 'Separação física parcial realizada. Aguardando reposição de estoque.', '2026-11-02 12:10:10'),
(22, 12, 2, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-02 07:10:10'),
(23, 12, 4, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-02 10:10:10'),
(24, 12, 4, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-11-02 12:10:10'),
(25, 13, 20, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-03 13:10:10'),
(26, 13, 18, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-03 16:10:10'),
(27, 13, 18, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-11-03 18:10:10'),
(28, 14, 29, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-11-03 13:10:10'),
(29, 14, 27, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-11-03 16:10:10'),
(30, 14, 27, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-11-03 18:10:10'),
(31, 15, 10, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-24 13:10:10'),
(32, 15, 4, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-10-24 16:10:10'),
(33, 15, 4, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-10-24 18:10:10'),
(34, 15, 5, 'separada', 'entregue', 'Itens entregues ao solicitante com sucesso. Atendimento concluído.', '2026-10-24 21:10:10'),
(35, 16, 11, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-21 12:10:10'),
(36, 16, 4, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-10-21 15:10:10'),
(37, 16, 4, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-10-21 17:10:10'),
(38, 16, 5, 'separada', 'entregue', 'Itens entregues ao solicitante com sucesso. Atendimento concluído.', '2026-10-21 20:10:10'),
(39, 17, 15, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-26 13:10:10'),
(40, 17, 12, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-10-26 16:10:10');
INSERT IGNORE INTO `historico_solicitacao` (`id`, `solicitacao_id`, `usuario_id`, `estado_anterior`, `estado_novo`, `descricao`, `criado_em`) VALUES
(41, 17, 12, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-10-26 18:10:10'),
(42, 17, 14, 'separada', 'entregue', 'Itens entregues ao solicitante com sucesso. Atendimento concluído.', '2026-10-26 21:10:10'),
(43, 18, 24, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-28 07:10:10'),
(44, 18, 22, 'solicitada', 'aprovada', 'Solicitação analisada e aprovada pelo gestor responsável.', '2026-10-28 10:10:10'),
(45, 18, 22, 'aprovada', 'separada', 'Separação física de todos os itens concluída no almoxarifado.', '2026-10-28 12:10:10'),
(46, 18, 23, 'separada', 'entregue', 'Itens entregues ao solicitante com sucesso. Atendimento concluído.', '2026-10-28 15:10:10'),
(47, 19, 6, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-30 13:10:10'),
(48, 19, 4, 'solicitada', 'rejeitada', 'Solicitação rejeitada: Pedido rejeitado pois não há previsão orçamentária para este tipo de equipamento neste trimestre.', '2026-10-30 16:10:10'),
(49, 20, 20, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', '2026-10-29 08:10:10');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `pedido_compra`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `pedido_compra` (`id`, `entidade_id`, `usuario_id`, `nome`, `status`, `observacao`, `criado_em`, `atualizado_em`) VALUES
(1, 1, 4, 'Reposição Periféricos e Toners - Junho', 'pedido_realizado', 'Pedido urgente para recompor estoque de toners e teclados em nível crítico.', '2026-10-31 15:10:11', '2026-11-05 15:10:11'),
(2, 1, 2, 'Aquisição Suprimentos Copa e Papelaria Trimestral', 'parcialmente_recebido', 'Entrega parcial realizada pela distribuidora. Aguardando restante.', '2026-10-31 15:10:11', '2026-11-05 15:10:11'),
(3, 1, 4, 'Compra Emergencial Álcool e Higiene', 'recebido', 'Pedido finalizado e insumos já incorporados ao saldo de estoque.', '2026-10-31 15:10:11', '2026-11-05 15:10:11'),
(4, 1, 5, 'Cotação Cabos e Conectores de Rede', 'aguardando_cotacao', 'Em cotação com 3 fornecedores locais para melhor preço em bobinas de cabo.', '2026-10-31 15:10:11', '2026-11-05 15:10:11'),
(5, 2, 12, 'Reposição de Cabos HDMI e Pilhas - Salas de Aula', 'pedido_realizado', 'Fornecedor confirmou faturamento e entrega prevista para 3 dias.', '2026-10-31 15:10:11', '2026-11-05 15:10:11'),
(6, 3, 18, 'Compra de Filme Stretch e Fitas de Embalagem', 'em_montagem', 'Identificação de demanda para o próximo mês de alta temporada logística.', '2026-10-31 15:10:11', '2026-11-05 15:10:11'),
(7, 4, 22, 'Insumos Hospitalares de Emergência e Descartáveis', 'recebido', 'Lote recebido com laudo técnico e nota fiscal conferida.', '2026-10-31 15:10:11', '2026-11-05 15:10:11');

-- ----------------------------------------------------------------------------
-- Dados para a tabela `item_pedido_compra`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `item_pedido_compra` (`id`, `pedido_id`, `suprimento_id`, `quantidade_necessaria`, `quantidade_pedida`, `quantidade_recebida`, `observacao`) VALUES
(1, 1, 3, 20, 20, 0, NULL),
(2, 1, 4, 20, 20, 0, NULL),
(3, 1, 6, 10, 10, 0, NULL),
(4, 2, 7, 50, 50, 50, NULL),
(5, 2, 9, 30, 30, 15, NULL),
(6, 2, 11, 40, 40, 20, NULL),
(7, 3, 10, 30, 30, 30, NULL),
(8, 3, 12, 25, 25, 25, NULL),
(9, 4, 1, 10, 10, 0, NULL),
(10, 4, 2, 20, 20, 0, NULL),
(11, 5, 16, 15, 15, 0, NULL),
(12, 5, 18, 40, 40, 0, NULL),
(13, 6, 19, 100, 0, 0, NULL),
(14, 6, 20, 30, 0, 0, NULL),
(15, 7, 24, 200, 200, 200, NULL),
(16, 7, 26, 60, 60, 60, NULL);

-- ----------------------------------------------------------------------------
-- Dados para a tabela `movimentacao_estoque`
-- ----------------------------------------------------------------------------
INSERT IGNORE INTO `movimentacao_estoque` (`id`, `entidade_id`, `suprimento_id`, `tipo`, `quantidade`, `quantidade_anterior`, `quantidade_posterior`, `solicitacao_id`, `usuario_id`, `observacao`, `criado_em`) VALUES
(1, 1, 10, 'entrada', 30, 0, 30, NULL, 4, 'Recebimento do Pedido de Compra #3 - Lote NF 88321', '2026-10-30 15:10:10'),
(2, 1, 12, 'entrada', 25, 0, 25, NULL, 4, 'Recebimento do Pedido de Compra #3 - Lote NF 88321', '2026-10-30 15:10:10'),
(3, 1, 7, 'entrada', 50, 10, 60, NULL, 2, 'Recebimento Parcial Pedido #2 - Michel Salles', '2026-11-01 15:10:10'),
(4, 1, 11, 'entrada', 20, 15, 35, NULL, 2, 'Recebimento Parcial Pedido #2 - Café', '2026-11-01 15:10:10'),
(5, 4, 24, 'entrada', 200, 50, 250, NULL, 22, 'Recebimento Pedido #7 - Luvas Nitrílicas Hospitalares', '2026-10-31 15:10:10'),
(6, 1, 7, 'saida', 6, 60, 54, 15, 5, 'Separação para Solicitação #15 - Setor Faturamento', '2026-10-24 15:10:10'),
(7, 1, 8, 'saida', 4, 29, 25, 15, 5, 'Separação para Solicitação #15 - Canetas', '2026-10-24 15:10:10'),
(8, 1, 5, 'saida', 4, 18, 14, 16, 5, 'Separação para Solicitação #16 - SSDs Comercial', '2026-10-21 15:10:10'),
(9, 1, 3, 'saida', 4, 12, 8, 9, 5, 'Separação parcial Solicitação #9 - Novos Postos', '2026-11-01 15:10:10'),
(10, 1, 4, 'saida', 4, 10, 6, 9, 5, 'Separação parcial Solicitação #9 - Mouses', '2026-11-01 15:10:10'),
(11, 1, 6, 'saida', 2, 5, 3, 12, 5, 'Separação para Solicitação #12 - Michel Salles', '2026-11-02 15:10:10'),
(12, 1, 1, 'ajuste', 2, 10, 12, NULL, 4, 'Ajuste de conferência física de prateleira Almoxarifado Central', '2026-10-16 15:10:10'),
(13, 2, 13, 'ajuste', 5, 55, 60, NULL, 12, 'Inventário semestral Campus Boa Vista', '2026-10-18 15:10:10');

SET FOREIGN_KEY_CHECKS = 1;

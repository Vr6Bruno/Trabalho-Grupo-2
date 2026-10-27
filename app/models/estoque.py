from app.db import conectar


def resumo(entidade_id=None):
    """Retorna contadores de saúde do estoque."""
    sql = """
        SELECT
            COUNT(*)                                                    AS total,
            COALESCE(SUM(status = 1 AND estoque_atual > estoque_minimo), 0) AS normais,
            COALESCE(SUM(status = 1 AND estoque_atual <= estoque_minimo AND estoque_atual > 0), 0) AS criticos,
            COALESCE(SUM(status = 1 AND estoque_atual = 0), 0)          AS zerados
        FROM suprimento
        WHERE 1 = 1
    """
    params = []
    if entidade_id is not None:
        sql += " AND entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def listar_saldos(entidade_id=None, busca="", situacao=""):
    """Lista os suprimentos e seus saldos atuais com status de estoque."""
    sql = """
        SELECT s.id, s.entidade_id, s.nome, s.codigo_interno, s.unidade_medida,
               s.estoque_minimo, s.estoque_atual, s.status,
               e.nome AS entidade_nome,
               CASE
                   WHEN s.estoque_atual = 0 THEN 'zerado'
                   WHEN s.estoque_atual <= s.estoque_minimo THEN 'critico'
                   ELSE 'normal'
               END AS situacao_estoque
        FROM suprimento s
        INNER JOIN entidade e ON e.id = s.entidade_id
        WHERE s.status = 1
    """
    params = []

    if entidade_id is not None:
        sql += " AND s.entidade_id = %s"
        params.append(entidade_id)

    if busca:
        sql += " AND (s.nome LIKE %s OR s.codigo_interno LIKE %s)"
        like = f"%{busca}%"
        params.extend([like, like])

    if situacao == "zerado":
        sql += " AND s.estoque_atual = 0"
    elif situacao == "critico":
        sql += " AND s.estoque_atual <= s.estoque_minimo AND s.estoque_atual > 0"
    elif situacao == "normal":
        sql += " AND s.estoque_atual > s.estoque_minimo"

    sql += " ORDER BY s.nome ASC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def buscar_item(id, entidade_id=None):
    """Busca os detalhes de um suprimento para visualização/movimentação."""
    sql = """
        SELECT s.*, e.nome AS entidade_nome,
               CASE
                   WHEN s.estoque_atual = 0 THEN 'zerado'
                   WHEN s.estoque_atual <= s.estoque_minimo THEN 'critico'
                   ELSE 'normal'
               END AS situacao_estoque
        FROM suprimento s
        INNER JOIN entidade e ON e.id = s.entidade_id
        WHERE s.id = %s
    """
    params = [id]
    if entidade_id is not None:
        sql += " AND s.entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def registrar_movimentacao(entidade_id, suprimento_id, tipo, quantidade, usuario_id, observacao=None, solicitacao_id=None):
    """
    Registra entrada, saída ou ajuste de estoque de forma transacional.
    - entrada: soma quantidade ao estoque
    - saida: subtrai quantidade (não permite saldo negativo)
    - ajuste: quantidade representa o novo saldo absoluto
    """
    if tipo not in ("entrada", "saida", "ajuste"):
        return False, "Tipo de movimentação inválido."

    with conectar() as conn, conn.cursor() as cur:
        # Seleciona o suprimento para atualização
        cur.execute("SELECT id, entidade_id, estoque_atual, nome FROM suprimento WHERE id = %s", (suprimento_id,))
        item = cur.fetchone()
        if not item:
            return False, "Suprimento não encontrado."

        if entidade_id and item["entidade_id"] != entidade_id:
            return False, "Suprimento não pertence à entidade indicada."

        qtd_anterior = item["estoque_atual"]

        if tipo == "entrada":
            if quantidade <= 0:
                return False, "Quantidade de entrada deve ser maior que zero."
            qtd_posterior = qtd_anterior + quantidade
            qtd_movimento = quantidade
        elif tipo == "saida":
            if quantidade <= 0:
                return False, "Quantidade de saída deve ser maior que zero."
            if qtd_anterior < quantidade:
                return False, f"Estoque insuficiente ({qtd_anterior}) para saída de {quantidade}."
            qtd_posterior = qtd_anterior - quantidade
            qtd_movimento = quantidade
        elif tipo == "ajuste":
            if quantidade < 0:
                return False, "Novo saldo não pode ser negativo."
            if not observacao or not observacao.strip():
                return False, "Justificativa/observação é obrigatória para ajuste de saldo."
            qtd_posterior = quantidade
            qtd_movimento = abs(qtd_posterior - qtd_anterior)

        # Atualiza o saldo do suprimento
        cur.execute("UPDATE suprimento SET estoque_atual = %s WHERE id = %s", (qtd_posterior, suprimento_id))

        # Registra no histórico de movimentações
        sql_mov = """
            INSERT INTO movimentacao_estoque
                (entidade_id, suprimento_id, tipo, quantidade, quantidade_anterior, quantidade_posterior,
                 solicitacao_id, usuario_id, observacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(sql_mov, (
            item["entidade_id"],
            suprimento_id,
            tipo,
            qtd_movimento,
            qtd_anterior,
            qtd_posterior,
            solicitacao_id,
            usuario_id,
            observacao.strip() if observacao else None
        ))

        return True, "Movimentação registrada com sucesso!"


def listar_movimentacoes(entidade_id=None, suprimento_id=None, limite=50):
    """Lista as últimas movimentações de estoque."""
    sql = """
        SELECT m.id, m.tipo, m.quantidade, m.quantidade_anterior, m.quantidade_posterior,
               m.observacao, m.criado_em, m.solicitacao_id,
               s.nome AS suprimento_nome, s.codigo_interno, s.unidade_medida,
               u.nome AS usuario_nome,
               e.nome AS entidade_nome
        FROM movimentacao_estoque m
        INNER JOIN suprimento s ON s.id = m.suprimento_id
        INNER JOIN usuario u ON u.id = m.usuario_id
        INNER JOIN entidade e ON e.id = m.entidade_id
        WHERE 1 = 1
    """
    params = []

    if entidade_id is not None:
        sql += " AND m.entidade_id = %s"
        params.append(entidade_id)

    if suprimento_id is not None:
        sql += " AND m.suprimento_id = %s"
        params.append(suprimento_id)

    sql += " ORDER BY m.criado_em DESC, m.id DESC LIMIT %s"
    params.append(limite)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def relatorio_consolidado(entidade_id=None):
    """
    Gera o relatório consolidado operacional:
    - Seção 1: Separar do estoque (itens de solicitações aprovadas com estoque disponível)
    - Seção 2: Necessário comprar (itens de solicitações aprovadas sem estoque suficiente)
    """
    sql = """
        SELECT
            s.id AS suprimento_id,
            s.nome AS suprimento_nome,
            s.codigo_interno,
            s.unidade_medida,
            s.estoque_atual,
            e.nome AS entidade_nome,
            SUM(i.quantidade_solicitada) AS total_solicitado,
            SUM(i.quantidade_atendida)   AS total_atendido,
            GROUP_CONCAT(DISTINCT sol.id ORDER BY sol.id SEPARATOR ', ') AS solicitacoes_ids
        FROM item_solicitacao i
        INNER JOIN solicitacao sol ON sol.id = i.solicitacao_id
        INNER JOIN suprimento s ON s.id = i.suprimento_id
        INNER JOIN entidade e ON e.id = s.entidade_id
        WHERE sol.status IN ('aprovada', 'separada')
          AND i.status IN ('pendente', 'aprovado', 'separado')
          AND i.quantidade_solicitada > i.quantidade_atendida
    """
    params = []
    if entidade_id is not None:
        sql += " AND sol.entidade_id = %s"
        params.append(entidade_id)

    sql += " GROUP BY s.id ORDER BY s.nome ASC"

    separar_estoque = []
    necessario_comprar = []

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        linhas = cur.fetchall()

        for row in linhas:
            pendente = max(0, row["total_solicitado"] - row["total_atendido"])
            estoque = row["estoque_atual"]

            qtd_separar = min(pendente, estoque)
            qtd_comprar = max(0, pendente - estoque)

            if qtd_separar > 0:
                item_sep = dict(row)
                item_sep["pendente"] = pendente
                item_sep["qtd_separar"] = qtd_separar
                separar_estoque.append(item_sep)

            if qtd_comprar > 0:
                item_comp = dict(row)
                item_comp["pendente"] = pendente
                item_comp["qtd_comprar"] = qtd_comprar
                necessario_comprar.append(item_comp)

    return {
        "separar_estoque": separar_estoque,
        "necessario_comprar": necessario_comprar
    }

from app.db import conectar


def resumo(entidade_id=None, solicitante_id=None):
    """Contadores das solicitações por estado."""
    sql = """
        SELECT
            COUNT(*)                                                  AS total,
            COALESCE(SUM(status = 'solicitada'), 0)                   AS solicitadas,
            COALESCE(SUM(status = 'aprovada'), 0)                     AS aprovadas,
            COALESCE(SUM(status = 'separada'), 0)                     AS separadas,
            COALESCE(SUM(status = 'entregue'), 0)                     AS entregues,
            COALESCE(SUM(status IN ('rejeitada', 'cancelada')), 0)    AS canceladas
        FROM solicitacao
        WHERE 1 = 1
    """
    params = []
    if entidade_id is not None:
        sql += " AND entidade_id = %s"
        params.append(entidade_id)
    if solicitante_id is not None:
        sql += " AND solicitante_id = %s"
        params.append(solicitante_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def listar(entidade_id=None, solicitante_id=None, status="", busca=""):
    """Lista as solicitações com informações do solicitante e quantidade de itens."""
    sql = """
        SELECT
            s.id, s.entidade_id, s.solicitante_id, s.status, s.observacao, s.criado_em,
            e.nome AS entidade_nome,
            u.nome AS solicitante_nome,
            u.login AS solicitante_login,
            v.nome AS validador_nome,
            COUNT(i.id) AS total_itens,
            COALESCE(SUM(i.quantidade_solicitada), 0) AS total_pecas,
            COALESCE(SUM(i.quantidade_atendida), 0)   AS total_atendidas
        FROM solicitacao s
        INNER JOIN entidade e ON e.id = s.entidade_id
        INNER JOIN usuario u ON u.id = s.solicitante_id
        LEFT JOIN usuario v ON v.id = s.validador_id
        LEFT JOIN item_solicitacao i ON i.solicitacao_id = s.id
        WHERE 1 = 1
    """
    params = []

    if entidade_id is not None:
        sql += " AND s.entidade_id = %s"
        params.append(entidade_id)

    if solicitante_id is not None:
        sql += " AND s.solicitante_id = %s"
        params.append(solicitante_id)

    if status:
        sql += " AND s.status = %s"
        params.append(status)

    if busca:
        sql += " AND (u.nome LIKE %s OR u.login LIKE %s OR s.id = %s)"
        like = f"%{busca}%"
        busca_id = int(busca) if busca.isdigit() else 0
        params.extend([like, like, busca_id])

    sql += " GROUP BY s.id ORDER BY s.criado_em DESC, s.id DESC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def buscar(id, entidade_id=None):
    """Busca uma solicitação específica e seus relacionamentos."""
    sql = """
        SELECT
            s.*,
            e.nome AS entidade_nome,
            u.nome AS solicitante_nome,
            u.login AS solicitante_login,
            v.nome AS validador_nome,
            r.nome AS responsavel_entrega_nome
        FROM solicitacao s
        INNER JOIN entidade e ON e.id = s.entidade_id
        INNER JOIN usuario u ON u.id = s.solicitante_id
        LEFT JOIN usuario v ON v.id = s.validador_id
        LEFT JOIN usuario r ON r.id = s.responsavel_entrega_id
        WHERE s.id = %s
    """
    params = [id]
    if entidade_id is not None:
        sql += " AND s.entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def listar_itens(solicitacao_id):
    """Lista todos os itens de uma solicitação com status de estoque atual."""
    sql = """
        SELECT
            i.id, i.solicitacao_id, i.suprimento_id, i.quantidade_solicitada,
            i.quantidade_atendida, i.status,
            (CAST(i.quantidade_solicitada AS SIGNED) - CAST(i.quantidade_atendida AS SIGNED)) AS pendente,
            s.nome AS suprimento_nome,
            s.codigo_interno,
            s.unidade_medida,
            s.estoque_atual,
            s.estoque_minimo,
            LEAST(GREATEST(0, CAST(i.quantidade_solicitada AS SIGNED) - CAST(i.quantidade_atendida AS SIGNED)), CAST(s.estoque_atual AS SIGNED)) AS pode_separar,
            CASE
                WHEN (CAST(i.quantidade_solicitada AS SIGNED) - CAST(i.quantidade_atendida AS SIGNED)) > CAST(s.estoque_atual AS SIGNED)
                THEN (CAST(i.quantidade_solicitada AS SIGNED) - CAST(i.quantidade_atendida AS SIGNED)) - CAST(s.estoque_atual AS SIGNED)
                ELSE 0
            END AS para_comprar
        FROM item_solicitacao i
        INNER JOIN suprimento s ON s.id = i.suprimento_id
        WHERE i.solicitacao_id = %s
        ORDER BY s.nome ASC
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (solicitacao_id,))
        return cur.fetchall()



def listar_historico(solicitacao_id):
    """Retorna os eventos da solicitação ordenados cronologicamente."""
    sql = """
        SELECT h.*, u.nome AS usuario_nome
        FROM historico_solicitacao h
        INNER JOIN usuario u ON u.id = h.usuario_id
        WHERE h.solicitacao_id = %s
        ORDER BY h.criado_em ASC, h.id ASC
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (solicitacao_id,))
        return cur.fetchall()


def criar(entidade_id, solicitante_id, itens, observacao=None):
    """
    Cria uma nova solicitação com seus itens no status 'solicitada'.
    itens: list de dicts com 'suprimento_id' e 'quantidade'.
    """
    if not itens:
        return False, "Informe pelo menos um item para a solicitação."

    with conectar() as conn, conn.cursor() as cur:
        if not entidade_id:
            cur.execute("SELECT entidade_id FROM suprimento WHERE id = %s", (itens[0]["suprimento_id"],))
            row_ent = cur.fetchone()
            if row_ent:
                entidade_id = row_ent["entidade_id"]
            else:
                cur.execute("SELECT id FROM entidade WHERE status = 1 ORDER BY id ASC LIMIT 1")
                row_ent = cur.fetchone()
                if row_ent:
                    entidade_id = row_ent["id"]

        # Insere a solicitação
        cur.execute("""
            INSERT INTO solicitacao (entidade_id, solicitante_id, status, observacao)
            VALUES (%s, %s, 'solicitada', %s)
        """, (entidade_id, solicitante_id, observacao.strip() if observacao else None))
        solicitacao_id = cur.lastrowid


        # Insere os itens
        for it in itens:
            cur.execute("""
                INSERT INTO item_solicitacao (solicitacao_id, suprimento_id, quantidade_solicitada, quantidade_atendida, status)
                VALUES (%s, %s, %s, 0, 'pendente')
            """, (solicitacao_id, it["suprimento_id"], it["quantidade"]))

        # Registra no histórico
        cur.execute("""
            INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
            VALUES (%s, %s, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os itens requisitados')
        """, (solicitacao_id, solicitante_id))

        return True, solicitacao_id


def aprovar(id, validador_id, entidade_id=None):
    """Aprova a solicitação, liberando seus itens para separação operacional."""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM solicitacao WHERE id = %s", (id,))
        sol = cur.fetchone()
        if not sol:
            return False, "Solicitação não encontrada."
        if sol["status"] != "solicitada":
            return False, f"Apenas solicitações no estado 'Solicitada' podem ser aprovadas (estado atual: {sol['status']})."

        sql_up = "UPDATE solicitacao SET status = 'aprovada', validador_id = %s, data_validacao = NOW() WHERE id = %s"
        params = [validador_id, id]
        if entidade_id:
            sql_up += " AND entidade_id = %s"
            params.append(entidade_id)
        cur.execute(sql_up, params)

        # Atualiza status dos itens pendentes para aprovado
        cur.execute("UPDATE item_solicitacao SET status = 'aprovado' WHERE solicitacao_id = %s AND status = 'pendente'", (id,))

        # Histórico
        cur.execute("""
            INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
            VALUES (%s, %s, 'solicitada', 'aprovada', 'Solicitação aprovada. Itens disponíveis no Compilado Operacional.')
        """, (id, validador_id))

        return True, "Solicitação aprovada com sucesso!"


def rejeitar(id, validador_id, justificativa, entidade_id=None):
    """Rejeita a solicitação com justificativa registrada."""
    if not justificativa or not justificativa.strip():
        return False, "A justificativa de rejeição é obrigatória."

    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM solicitacao WHERE id = %s", (id,))
        sol = cur.fetchone()
        if not sol:
            return False, "Solicitação não encontrada."
        if sol["status"] not in ("solicitada", "em_validacao"):
            return False, f"Esta solicitação não pode mais ser rejeitada (estado atual: {sol['status']})."

        sql_up = """
            UPDATE solicitacao
            SET status = 'rejeitada', justificativa_rejeicao = %s, validador_id = %s, data_validacao = NOW()
            WHERE id = %s
        """
        params = [justificativa.strip(), validador_id, id]
        if entidade_id:
            sql_up += " AND entidade_id = %s"
            params.append(entidade_id)
        cur.execute(sql_up, params)

        # Atualiza itens para cancelado
        cur.execute("UPDATE item_solicitacao SET status = 'cancelado' WHERE solicitacao_id = %s", (id,))

        # Histórico
        cur.execute("""
            INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
            VALUES (%s, %s, %s, 'rejeitada', %s)
        """, (id, validador_id, sol["status"], f"Solicitação rejeitada: {justificativa.strip()}"))

        return True, "Solicitação rejeitada com sucesso."


def cancelar(id, usuario_id, motivo=None, entidade_id=None):
    """Cancela uma solicitação antes de ser entregue."""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM solicitacao WHERE id = %s", (id,))
        sol = cur.fetchone()
        if not sol:
            return False, "Solicitação não encontrada."
        if sol["status"] in ("entregue", "cancelada", "rejeitada"):
            return False, f"Solicitação já finalizada ({sol['status']}) e não pode ser cancelada."

        sql_up = "UPDATE solicitacao SET status = 'cancelada' WHERE id = %s"
        params = [id]
        if entidade_id:
            sql_up += " AND entidade_id = %s"
            params.append(entidade_id)
        cur.execute(sql_up, params)

        cur.execute("UPDATE item_solicitacao SET status = 'cancelado' WHERE solicitacao_id = %s", (id,))

        desc = f"Solicitação cancelada. Motivo: {motivo.strip()}" if motivo else "Solicitação cancelada pelo usuário."
        cur.execute("""
            INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
            VALUES (%s, %s, %s, 'cancelada', %s)
        """, (id, usuario_id, sol["status"], desc))

        return True, "Solicitação cancelada."


def separar_itens(solicitacao_id, itens_separar, operador_id, entidade_id=None):
    """
    Executa a separação física do estoque:
    - Dá baixa no estoque para cada item separado (gera movimentação de saída vinculada à solicitação)
    - Incrementa quantidade_atendida do item
    - Se todos os itens forem atendidos, avança a solicitação para 'separada'
    itens_separar: dict de {item_id: quantidade_a_separar}
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM solicitacao WHERE id = %s", (solicitacao_id,))
        sol = cur.fetchone()
        if not sol:
            return False, "Solicitação não encontrada."
        if sol["status"] not in ("aprovada", "aguardando_estoque"):
            return False, f"Esta solicitação não está pronta para separação (estado atual: {sol['status']})."

        total_separado_nesta_operacao = 0

        for item_id, qtd in itens_separar.items():
            qtd = int(qtd)
            if qtd <= 0:
                continue

            # Busca item e suprimento
            cur.execute("""
                SELECT i.*, s.estoque_atual, s.nome AS suprimento_nome, s.entidade_id
                FROM item_solicitacao i
                INNER JOIN suprimento s ON s.id = i.suprimento_id
                WHERE i.id = %s AND i.solicitacao_id = %s
            """, (item_id, solicitacao_id))
            item = cur.fetchone()
            if not item:
                return False, f"Item #{item_id} não encontrado na solicitação."

            pendente = item["quantidade_solicitada"] - item["quantidade_atendida"]
            if qtd > pendente:
                return False, f"Quantidade a separar ({qtd}) excede o pendente ({pendente}) para {item['suprimento_nome']}."

            if qtd > item["estoque_atual"]:
                return False, f"Estoque insuficiente ({item['estoque_atual']}) para separar {qtd} de {item['suprimento_nome']}."

            # Baixa no estoque
            novo_estoque = item["estoque_atual"] - qtd
            cur.execute("UPDATE suprimento SET estoque_atual = %s WHERE id = %s", (novo_estoque, item["suprimento_id"]))

            # Registra movimentação de saída
            sql_mov = """
                INSERT INTO movimentacao_estoque
                    (entidade_id, suprimento_id, tipo, quantidade, quantidade_anterior, quantidade_posterior,
                     solicitacao_id, usuario_id, observacao)
                VALUES (%s, %s, 'saida', %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_mov, (
                item["entidade_id"],
                item["suprimento_id"],
                qtd,
                item["estoque_atual"],
                novo_estoque,
                solicitacao_id,
                operador_id,
                f"Separação para Solicitação #{solicitacao_id}"
            ))

            # Atualiza item da solicitação
            nova_atendida = item["quantidade_atendida"] + qtd
            novo_status_item = "atendido" if nova_atendida >= item["quantidade_solicitada"] else "separado"
            cur.execute("""
                UPDATE item_solicitacao
                SET quantidade_atendida = %s, status = %s
                WHERE id = %s
            """, (nova_atendida, novo_status_item, item_id))

            total_separado_nesta_operacao += qtd

        if total_separado_nesta_operacao == 0:
            return False, "Nenhum item ou quantidade selecionada para separação."

        # Verifica se todos os itens foram atendidos
        cur.execute("""
            SELECT COUNT(*) AS pendentes
            FROM item_solicitacao
            WHERE solicitacao_id = %s AND quantidade_atendida < quantidade_solicitada
        """, (solicitacao_id,))
        pendencias = cur.fetchone()["pendentes"]

        if pendencias == 0:
            cur.execute("UPDATE solicitacao SET status = 'separada' WHERE id = %s", (solicitacao_id,))
            msg_hist = f"Separação concluída com sucesso ({total_separado_nesta_operacao} itens separados). Solicitação pronta para entrega."
            cur.execute("""
                INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
                VALUES (%s, %s, 'aprovada', 'separada', %s)
            """, (solicitacao_id, operador_id, msg_hist))
            return True, "Todos os itens foram separados! Solicitação pronta para entrega."
        else:
            msg_hist = f"Separação parcial realizada ({total_separado_nesta_operacao} itens separados). Aguardando restante do estoque."
            cur.execute("""
                INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
                VALUES (%s, %s, 'aprovada', 'aprovada', %s)
            """, (solicitacao_id, operador_id, msg_hist))
            return True, f"Separação parcial registrada ({total_separado_nesta_operacao} itens separados)."


def entregar(id, entregador_id, entidade_id=None):
    """Conclui o atendimento da solicitação registrando a entrega ao solicitante."""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM solicitacao WHERE id = %s", (id,))
        sol = cur.fetchone()
        if not sol:
            return False, "Solicitação não encontrada."
        if sol["status"] != "separada":
            return False, f"Apenas solicitações com status 'Separada' podem ser entregues (estado atual: {sol['status']})."

        sql_up = """
            UPDATE solicitacao
            SET status = 'entregue', responsavel_entrega_id = %s, data_entrega = NOW()
            WHERE id = %s
        """
        params = [entregador_id, id]
        if entidade_id:
            sql_up += " AND entidade_id = %s"
            params.append(entidade_id)
        cur.execute(sql_up, params)

        cur.execute("UPDATE item_solicitacao SET status = 'atendido' WHERE solicitacao_id = %s", (id,))

        cur.execute("""
            INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao)
            VALUES (%s, %s, 'separada', 'entregue', 'Itens entregues ao solicitante. Atendimento concluído.')
        """, (id, entregador_id))

        return True, "Entrega registrada com sucesso! Atendimento concluído."


def compilado_operacional(entidade_id=None):
    """
    Retorna a lista de solicitações aprovadas com seus itens organizados para separação.
    Idêntico ao funcionamento do Compilado Operacional.
    """
    sql_tickets = """
        SELECT DISTINCT
            s.id, s.entidade_id, s.solicitante_id, s.criado_em, s.status, s.observacao,
            e.nome AS entidade_nome,
            u.nome AS solicitante_nome
        FROM solicitacao s
        INNER JOIN item_solicitacao i ON i.solicitacao_id = s.id
        INNER JOIN entidade e ON e.id = s.entidade_id
        INNER JOIN usuario u ON u.id = s.solicitante_id
        WHERE s.status IN ('aprovada', 'aguardando_estoque')
          AND i.quantidade_solicitada > i.quantidade_atendida
    """
    params = []
    if entidade_id is not None:
        sql_tickets += " AND s.entidade_id = %s"
        params.append(entidade_id)

    sql_tickets += " ORDER BY s.criado_em ASC, s.id ASC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql_tickets, params)
        solicitacoes = cur.fetchall()

        resultado = []
        for s in solicitacoes:
            itens = listar_itens(s["id"])
            pode_separar_total = sum(item["pode_separar"] for item in itens)
            para_comprar_total = sum(item["para_comprar"] for item in itens)

            item_data = dict(s)
            item_data["itens"] = itens
            item_data["can_separate"] = pode_separar_total
            item_data["needs_purchase"] = para_comprar_total
            resultado.append(item_data)

        return resultado

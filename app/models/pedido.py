from app.db import conectar


def resumo(entidade_id=None):
    """Contadores de pedidos de compra por status."""
    sql = """
        SELECT
            COUNT(*)                                                  AS total,
            COALESCE(SUM(status = 'em_montagem'), 0)                  AS em_montagem,
            COALESCE(SUM(status = 'aguardando_cotacao'), 0)           AS aguardando_cotacao,
            COALESCE(SUM(status IN ('pedido_realizado', 'parcialmente_recebido')), 0) AS em_andamento,
            COALESCE(SUM(status = 'recebido'), 0)                     AS recebidos
        FROM pedido_compra
        WHERE 1 = 1
    """
    params = []
    if entidade_id is not None:
        sql += " AND entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def listar(entidade_id=None, status="", busca=""):
    """Lista pedidos de compra com dados consolidados."""
    sql = """
        SELECT
            p.id, p.entidade_id, p.usuario_id, p.nome, p.status, p.observacao, p.criado_em,
            e.nome AS entidade_nome,
            u.nome AS usuario_nome,
            COUNT(i.id) AS total_itens,
            COALESCE(SUM(i.quantidade_necessaria), 0) AS total_necessario,
            COALESCE(SUM(i.quantidade_recebida), 0)   AS total_recebido
        FROM pedido_compra p
        INNER JOIN entidade e ON e.id = p.entidade_id
        INNER JOIN usuario u ON u.id = p.usuario_id
        LEFT JOIN item_pedido_compra i ON i.pedido_id = p.id
        WHERE 1 = 1
    """
    params = []

    if entidade_id is not None:
        sql += " AND p.entidade_id = %s"
        params.append(entidade_id)

    if status:
        sql += " AND p.status = %s"
        params.append(status)

    if busca:
        sql += " AND (p.nome LIKE %s OR p.id = %s)"
        like = f"%{busca}%"
        pid = int(busca) if busca.isdigit() else 0
        params.extend([like, pid])

    sql += " GROUP BY p.id ORDER BY p.criado_em DESC, p.id DESC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def buscar(id, entidade_id=None):
    """Busca um pedido específico."""
    sql = """
        SELECT p.*, e.nome AS entidade_nome, u.nome AS usuario_nome
        FROM pedido_compra p
        INNER JOIN entidade e ON e.id = p.entidade_id
        INNER JOIN usuario u ON u.id = p.usuario_id
        WHERE p.id = %s
    """
    params = [id]
    if entidade_id is not None:
        sql += " AND p.entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def listar_itens(pedido_id):
    """Lista os itens do pedido com saldos atuais do estoque."""
    sql = """
        SELECT
            i.*,
            s.nome AS suprimento_nome,
            s.codigo_interno,
            s.unidade_medida,
            s.estoque_atual,
            CASE
                WHEN i.quantidade_pedida > 0 THEN i.quantidade_pedida
                ELSE i.quantidade_necessaria
            END AS meta_recebimento,
            GREATEST(0, (CASE WHEN i.quantidade_pedida > 0 THEN CAST(i.quantidade_pedida AS SIGNED) ELSE CAST(i.quantidade_necessaria AS SIGNED) END) - CAST(i.quantidade_recebida AS SIGNED)) AS restante_receber
        FROM item_pedido_compra i
        INNER JOIN suprimento s ON s.id = i.suprimento_id
        WHERE i.pedido_id = %s
        ORDER BY s.nome ASC
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (pedido_id,))
        return cur.fetchall()



def criar(entidade_id, usuario_id, nome, observacao=None, item_inicial=None):
    """Cria um novo pedido de compra no status 'em_montagem'."""
    if not nome or not nome.strip():
        return False, "O nome do pedido é obrigatório."

    with conectar() as conn, conn.cursor() as cur:
        if not entidade_id and item_inicial and item_inicial.get("suprimento_id"):
            cur.execute("SELECT entidade_id FROM suprimento WHERE id = %s", (item_inicial["suprimento_id"],))
            row_ent = cur.fetchone()
            if row_ent:
                entidade_id = row_ent["entidade_id"]
        if not entidade_id:
            cur.execute("SELECT id FROM entidade WHERE status = 1 ORDER BY id ASC LIMIT 1")
            row_ent = cur.fetchone()
            if row_ent:
                entidade_id = row_ent["id"]

        sql = """
            INSERT INTO pedido_compra (entidade_id, usuario_id, nome, status, observacao)
            VALUES (%s, %s, %s, 'em_montagem', %s)
        """
        cur.execute(sql, (entidade_id, usuario_id, nome.strip(), observacao.strip() if observacao else None))
        pedido_id = cur.lastrowid


        if item_inicial and item_inicial.get("suprimento_id") and item_inicial.get("quantidade"):
            cur.execute("""
                INSERT INTO item_pedido_compra (pedido_id, suprimento_id, quantidade_necessaria, observacao)
                VALUES (%s, %s, %s, %s)
            """, (
                pedido_id,
                item_inicial["suprimento_id"],
                item_inicial["quantidade"],
                item_inicial.get("observacao")
            ))

        return True, pedido_id


def adicionar_item(pedido_id, suprimento_id, quantidade_necessaria, observacao=None):
    """Adiciona um suprimento ao pedido de compra."""
    if quantidade_necessaria <= 0:
        return False, "Quantidade deve ser maior que zero."

    with conectar() as conn, conn.cursor() as cur:
        # Verifica se o suprimento já está no pedido
        cur.execute("SELECT id, quantidade_necessaria FROM item_pedido_compra WHERE pedido_id = %s AND suprimento_id = %s", (pedido_id, suprimento_id))
        existente = cur.fetchone()

        if existente:
            nova_qtd = existente["quantidade_necessaria"] + quantidade_necessaria
            cur.execute("UPDATE item_pedido_compra SET quantidade_necessaria = %s WHERE id = %s", (nova_qtd, existente["id"]))
        else:
            cur.execute("""
                INSERT INTO item_pedido_compra (pedido_id, suprimento_id, quantidade_necessaria, observacao)
                VALUES (%s, %s, %s, %s)
            """, (pedido_id, suprimento_id, quantidade_necessaria, observacao))

        return True, "Item adicionado ao pedido de compra."


def remover_item(item_id, pedido_id):
    """Remove um item do pedido."""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM item_pedido_compra WHERE id = %s AND pedido_id = %s", (item_id, pedido_id))
        return True, "Item removido do pedido."


def atualizar_status(id, novo_status, observacao=None, entidade_id=None):
    """Atualiza o status e notas do pedido de compra."""
    status_validos = ("em_montagem", "aguardando_cotacao", "pedido_realizado", "parcialmente_recebido", "recebido", "cancelado")
    if novo_status not in status_validos:
        return False, "Status inválido."

    with conectar() as conn, conn.cursor() as cur:
        # Ao marcar 'pedido_realizado', grava quantidade_pedida = quantidade_necessaria
        if novo_status == "pedido_realizado":
            cur.execute("""
                UPDATE item_pedido_compra
                SET quantidade_pedida = quantidade_necessaria
                WHERE pedido_id = %s AND quantidade_pedida = 0
            """, (id,))

        sql = "UPDATE pedido_compra SET status = %s"
        params = [novo_status]

        if observacao is not None:
            sql += ", observacao = %s"
            params.append(observacao.strip())

        sql += " WHERE id = %s"
        params.append(id)

        if entidade_id:
            sql += " AND entidade_id = %s"
            params.append(entidade_id)

        cur.execute(sql, params)
        return True, "Status do pedido atualizado com sucesso."


def receber_item(pedido_id, item_id, quantidade_recebida, usuario_id, entidade_id=None):
    """
    Registra o recebimento físico de um item de compra:
    - Valida a quantidade recebida
    - Dá entrada automática no estoque do suprimento
    - Atualiza quantidade_recebida do item
    - Promove o status do pedido para 'parcialmente_recebido' ou 'recebido'
    """
    if quantidade_recebida <= 0:
        return False, "Quantidade recebida deve ser maior que zero."

    with conectar() as conn, conn.cursor() as cur:
        # Busca pedido
        cur.execute("SELECT * FROM pedido_compra WHERE id = %s", (pedido_id,))
        ped = cur.fetchone()
        if not ped:
            return False, "Pedido não encontrado."

        if ped["status"] not in ("pedido_realizado", "parcialmente_recebido"):
            return False, f"Recebimento não permitido para pedidos no status '{ped['status']}'."

        # Busca item do pedido e suprimento
        cur.execute("""
            SELECT i.*, s.estoque_atual, s.entidade_id, s.nome AS suprimento_nome
            FROM item_pedido_compra i
            INNER JOIN suprimento s ON s.id = i.suprimento_id
            WHERE i.id = %s AND i.pedido_id = %s
        """, (item_id, pedido_id))
        item = cur.fetchone()
        if not item:
            return False, "Item do pedido não encontrado."

        meta = item["quantidade_pedida"] if item["quantidade_pedida"] > 0 else item["quantidade_necessaria"]
        restante = meta - item["quantidade_recebida"]
        if quantidade_recebida > restante:
            return False, f"Quantidade recebida ({quantidade_recebida}) excede a pendência ({restante}) para {item['suprimento_nome']}."

        # 1. Dá entrada no estoque do suprimento
        novo_estoque = item["estoque_atual"] + quantidade_recebida
        cur.execute("UPDATE suprimento SET estoque_atual = %s WHERE id = %s", (novo_estoque, item["suprimento_id"]))

        # 2. Registra movimentação de entrada
        sql_mov = """
            INSERT INTO movimentacao_estoque
                (entidade_id, suprimento_id, tipo, quantidade, quantidade_anterior, quantidade_posterior,
                 usuario_id, observacao)
            VALUES (%s, %s, 'entrada', %s, %s, %s, %s, %s)
        """
        cur.execute(sql_mov, (
            item["entidade_id"],
            item["suprimento_id"],
            quantidade_recebida,
            item["estoque_atual"],
            novo_estoque,
            usuario_id,
            f"Recebimento de Pedido de Compra #{pedido_id}"
        ))

        # 3. Atualiza o item do pedido
        nova_recebida = item["quantidade_recebida"] + quantidade_recebida
        cur.execute("UPDATE item_pedido_compra SET quantidade_recebida = %s WHERE id = %s", (nova_recebida, item_id))

        # 4. Avalia status geral do pedido
        cur.execute("""
            SELECT
                SUM(quantidade_recebida) AS total_rec,
                SUM(CASE WHEN quantidade_pedida > 0 THEN quantidade_pedida ELSE quantidade_necessaria END) AS total_meta
            FROM item_pedido_compra
            WHERE pedido_id = %s
        """, (pedido_id,))
        totais = cur.fetchone()

        if totais["total_rec"] >= totais["total_meta"]:
            novo_status_ped = "recebido"
        else:
            novo_status_ped = "parcialmente_recebido"

        cur.execute("UPDATE pedido_compra SET status = %s WHERE id = %s", (novo_status_ped, pedido_id))

        return True, f"Recebimento de {quantidade_recebida} un de {item['suprimento_nome']} registrado no estoque!"

from app.db import conectar


def listar(entidade_id=None, busca="", status="", critico=False):
    sql = """
        SELECT s.id, s.entidade_id, s.nome, s.codigo_interno, s.unidade_medida,
               s.estoque_minimo, s.estoque_atual, s.status,
               (s.estoque_atual <= s.estoque_minimo) AS critico,
               e.nome AS entidade_nome
        FROM suprimento s
        INNER JOIN entidade e ON e.id = s.entidade_id
        WHERE 1 = 1
    """
    params = []

    if entidade_id is not None:
        sql += " AND s.entidade_id = %s"
        params.append(entidade_id)

    if busca:
        sql += " AND (s.nome LIKE %s OR s.codigo_interno LIKE %s)"
        like = f"%{busca}%"
        params.extend([like, like])

    if status in ("0", "1"):
        sql += " AND s.status = %s"
        params.append(int(status))

    if critico:
        sql += " AND s.estoque_atual <= s.estoque_minimo"

    sql += " ORDER BY s.nome ASC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def resumo(entidade_id=None):
    sql = """
        SELECT
            COUNT(*)                                              AS total,
            COALESCE(SUM(status = 1), 0)                          AS ativos,
            COALESCE(SUM(status = 0), 0)                          AS inativos,
            COALESCE(SUM(status = 1
                         AND estoque_atual <= estoque_minimo), 0) AS criticos
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


def buscar(id, entidade_id=None):
    sql = "SELECT * FROM suprimento WHERE id = %s"
    params = [id]
    if entidade_id is not None:
        sql += " AND entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def criar(d, entidade_id):
    sql = """
        INSERT INTO suprimento
            (entidade_id, nome, codigo_interno, unidade_medida, descricao, estoque_minimo, estoque_atual, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            entidade_id,
            d["nome"].strip(),
            d.get("codigo_interno"),
            d.get("unidade_medida"),
            d.get("descricao"),
            d["estoque_minimo"],
            d.get("estoque_atual", 0),
            d["status"]
        ))
        return cur.lastrowid


def atualizar(id, d, entidade_id=None):
    sql = """
        UPDATE suprimento
        SET nome = %s, codigo_interno = %s, unidade_medida = %s,
            descricao = %s, estoque_minimo = %s, status = %s
        WHERE id = %s
    """
    params = [
        d["nome"].strip(),
        d.get("codigo_interno"),
        d.get("unidade_medida"),
        d.get("descricao"),
        d["estoque_minimo"],
        d["status"],
        id
    ]

    if entidade_id is not None:
        sql += " AND entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)


def pode_excluir(id):
    """Verifica se o suprimento pode ser excluído sem violar integridade de solicitações ou compras."""
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM item_solicitacao WHERE suprimento_id = %s", (id,))
        if cur.fetchone()["total"] > 0:
            return False, "Este suprimento possui solicitações vinculadas e não pode ser excluído. Considere inativá-lo."
        cur.execute("SELECT COUNT(*) AS total FROM item_pedido_compra WHERE suprimento_id = %s", (id,))
        if cur.fetchone()["total"] > 0:
            return False, "Este suprimento possui pedidos de compra vinculados e não pode ser excluído. Considere inativá-lo."
        return True, ""


def excluir(id, entidade_id=None):
    """Exclui o suprimento caso não possua vínculos impeditivos."""
    pode, motivo = pode_excluir(id)
    if not pode:
        return False, motivo

    sql = "DELETE FROM suprimento WHERE id = %s"
    params = [id]
    if entidade_id is not None:
        sql += " AND entidade_id = %s"
        params.append(entidade_id)

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return True, "Suprimento excluído com sucesso."


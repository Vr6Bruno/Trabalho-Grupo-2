from db import conectar


def listar(busca="", status="", critico=False):
    sql = """
        SELECT id, nome, codigo_interno, unidade_medida,
               estoque_minimo, estoque_atual, status,
               (estoque_atual <= estoque_minimo) AS critico
        FROM suprimento
        WHERE 1 = 1
    """
    params = []

    if busca:
        sql += " AND (nome LIKE %s OR codigo_interno LIKE %s)"
        like = f"%{busca}%"
        params += [like, like]

    if status in ("0", "1"):
        sql += " AND status = %s"
        params.append(int(status))

    if critico:
        sql += " AND estoque_atual <= estoque_minimo"

    sql += " ORDER BY nome"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def resumo():
    sql = """
        SELECT
            COUNT(*)                                              AS total,
            COALESCE(SUM(status = 1), 0)                          AS ativos,
            COALESCE(SUM(status = 0), 0)                          AS inativos,
            COALESCE(SUM(status = 1
                         AND estoque_atual <= estoque_minimo), 0) AS criticos
        FROM suprimento
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()


def buscar(id):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM suprimento WHERE id = %s", (id,))
        return cur.fetchone()


def criar(d):
    sql = """
        INSERT INTO suprimento
            (nome, codigo_interno, unidade_medida, descricao, estoque_minimo, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (d["nome"], d["codigo_interno"], d["unidade_medida"],
                          d["descricao"], d["estoque_minimo"], d["status"]))
        return cur.lastrowid


def atualizar(id, d):
    sql = """
        UPDATE suprimento
        SET nome = %s, codigo_interno = %s, unidade_medida = %s,
            descricao = %s, estoque_minimo = %s, status = %s
        WHERE id = %s
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (d["nome"], d["codigo_interno"], d["unidade_medida"],
                          d["descricao"], d["estoque_minimo"], d["status"], id))

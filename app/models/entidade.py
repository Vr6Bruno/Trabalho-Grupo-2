from app.db import conectar


def listar(busca="", status=""):
    sql = """
        SELECT e.id, e.nome, e.identificador, e.status, e.criado_em,
               (SELECT COUNT(*) FROM usuario u WHERE u.entidade_id = e.id) AS total_usuarios,
               (SELECT COUNT(*) FROM suprimento s WHERE s.entidade_id = e.id) AS total_suprimentos
        FROM entidade e
        WHERE 1 = 1
    """
    params = []

    if busca:
        sql += " AND (e.nome LIKE %s OR e.identificador LIKE %s)"
        like = f"%{busca}%"
        params.extend([like, like])

    if status in ("0", "1"):
        sql += " AND e.status = %s"
        params.append(int(status))

    sql += " ORDER BY e.nome ASC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def buscar(id):
    sql = "SELECT id, nome, identificador, status, criado_em FROM entidade WHERE id = %s"
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (id,))
        return cur.fetchone()


buscar_por_id = buscar


def criar(d):
    sql = """
        INSERT INTO entidade (nome, identificador, status)
        VALUES (%s, %s, %s)
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (d["nome"], d.get("identificador"), d.get("status", 1)))
        return cur.lastrowid


def atualizar(id, d):
    sql = """
        UPDATE entidade
        SET nome = %s, identificador = %s, status = %s
        WHERE id = %s
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (d["nome"], d.get("identificador"), d.get("status", 1), id))

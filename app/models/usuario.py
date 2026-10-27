from werkzeug.security import generate_password_hash, check_password_hash
from app.db import conectar


def gerar_hash(senha):
    return generate_password_hash(senha)


def verificar_senha(senha_hash, senha_plana):
    if not senha_hash or not senha_plana:
        return False
    return check_password_hash(senha_hash, senha_plana)


def listar_perfis_do_usuario(usuario_id):
    """Retorna todos os perfis associados ao usuário na tabela usuario_perfil."""
    sql = """
        SELECT p.id, p.codigo, p.nome, p.descricao, p.nivel_acesso
        FROM usuario_perfil up
        INNER JOIN perfil p ON p.id = up.perfil_id
        WHERE up.usuario_id = %s
        ORDER BY p.nivel_acesso DESC
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (usuario_id,))
        rows = cur.fetchall()
        if not rows:
            # Fallback para o perfil_id registrado na tabela usuario
            cur.execute("""
                SELECT p.id, p.codigo, p.nome, p.descricao, p.nivel_acesso
                FROM usuario u
                INNER JOIN perfil p ON p.id = u.perfil_id
                WHERE u.id = %s
            """, (usuario_id,))
            rows = cur.fetchall()
        return rows


def sincronizar_perfis(usuario_id, perfil_ids):
    """Garante que a tabela associativa usuario_perfil contenha exatamente os perfis selecionados."""
    if not perfil_ids:
        return
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM usuario_perfil WHERE usuario_id = %s", (usuario_id,))
        for pid in perfil_ids:
            cur.execute("INSERT INTO usuario_perfil (usuario_id, perfil_id) VALUES (%s, %s)", (usuario_id, pid))


def buscar_por_login(identificador):
    """
    Busca usuário pelo login (ex: 'admin', 'gerente') ou secundariamente por email.
    Carrega também a lista de todos os perfis do usuário.
    """
    ident = identificador.strip().lower()
    sql = """
        SELECT u.id, u.entidade_id, u.perfil_id, u.login, u.nome, u.email, u.senha_hash, u.status,
               p.codigo AS perfil_codigo, p.nome AS perfil_nome, p.nivel_acesso,
               e.nome AS entidade_nome, e.status AS entidade_status
        FROM usuario u
        INNER JOIN perfil p ON p.id = u.perfil_id
        LEFT JOIN entidade e ON e.id = u.entidade_id
        WHERE LOWER(u.login) = %s OR LOWER(COALESCE(u.email, '')) = %s
        LIMIT 1
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (ident, ident))
        usuario = cur.fetchone()
        if usuario:
            usuario["perfis"] = listar_perfis_do_usuario(usuario["id"])
            usuario["is_super_admin"] = any(p["codigo"] == "SUPER_ADMIN" for p in usuario["perfis"]) or usuario["perfil_codigo"] == "SUPER_ADMIN"
        return usuario


def buscar_por_id(id):
    sql = """
        SELECT u.id, u.entidade_id, u.perfil_id, u.login, u.nome, u.email, u.status, u.criado_em,
               p.codigo AS perfil_codigo, p.nome AS perfil_nome,
               e.nome AS entidade_nome
        FROM usuario u
        INNER JOIN perfil p ON p.id = u.perfil_id
        LEFT JOIN entidade e ON e.id = u.entidade_id
        WHERE u.id = %s
    """
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (id,))
        u = cur.fetchone()
        if u:
            u["perfis"] = listar_perfis_do_usuario(u["id"])
            u["perfil_ids"] = [p["id"] for p in u["perfis"]]
            u["is_super_admin"] = any(p["codigo"] == "SUPER_ADMIN" for p in u["perfis"]) or u["perfil_codigo"] == "SUPER_ADMIN"
        return u


def listar(entidade_id=None, perfil_id=None, busca="", status=""):
    sql = """
        SELECT u.id, u.entidade_id, u.perfil_id, u.login, u.nome, u.email, u.status, u.criado_em,
               p.codigo AS perfil_codigo, p.nome AS perfil_nome,
               COALESCE(e.nome, 'Acesso Global') AS entidade_nome,
               GROUP_CONCAT(DISTINCT p_all.nome ORDER BY p_all.nivel_acesso DESC SEPARATOR ', ') AS todos_perfis
        FROM usuario u
        INNER JOIN perfil p ON p.id = u.perfil_id
        LEFT JOIN entidade e ON e.id = u.entidade_id
        LEFT JOIN usuario_perfil up ON up.usuario_id = u.id
        LEFT JOIN perfil p_all ON p_all.id = up.perfil_id
        WHERE 1 = 1
    """
    params = []

    if entidade_id is not None:
        sql += " AND u.entidade_id = %s"
        params.append(entidade_id)

    if perfil_id:
        sql += " AND (u.perfil_id = %s OR up.perfil_id = %s)"
        params.extend([int(perfil_id), int(perfil_id)])

    if busca:
        sql += " AND (u.login LIKE %s OR u.nome LIKE %s OR u.email LIKE %s)"
        like = f"%{busca}%"
        params.extend([like, like, like])

    if status in ("0", "1"):
        sql += " AND u.status = %s"
        params.append(int(status))

    sql += " GROUP BY u.id ORDER BY u.nome ASC"

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def listar_perfis():
    sql = "SELECT id, codigo, nome, descricao, nivel_acesso FROM perfil ORDER BY nivel_acesso DESC"
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def criar(d):
    perfil_ids = d.get("perfil_ids", [])
    primary_perfil_id = perfil_ids[0] if perfil_ids else d.get("perfil_id", 2)

    sql = """
        INSERT INTO usuario (entidade_id, perfil_id, login, nome, email, senha_hash, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    senha_hash = gerar_hash(d["senha"])
    entidade_id = d.get("entidade_id")
    if entidade_id == "" or entidade_id == 0 or entidade_id == "0":
        entidade_id = None

    email = d.get("email", "").strip().lower() if d.get("email") else None

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            entidade_id,
            primary_perfil_id,
            d["login"].strip().lower(),
            d["nome"].strip(),
            email,
            senha_hash,
            d.get("status", 1)
        ))
        novo_id = cur.lastrowid
        if not perfil_ids:
            perfil_ids = [primary_perfil_id]
        sincronizar_perfis(novo_id, perfil_ids)
        return novo_id


def atualizar(id, d, nova_senha=None):
    perfil_ids = d.get("perfil_ids", [])
    primary_perfil_id = perfil_ids[0] if perfil_ids else d.get("perfil_id")

    entidade_id = d.get("entidade_id")
    if entidade_id == "" or entidade_id == 0 or entidade_id == "0":
        entidade_id = None

    email = d.get("email", "").strip().lower() if d.get("email") else None

    if nova_senha:
        sql = """
            UPDATE usuario
            SET entidade_id = %s, perfil_id = %s, login = %s, nome = %s, email = %s,
                senha_hash = %s, status = %s
            WHERE id = %s
        """
        senha_hash = gerar_hash(nova_senha)
        params = (
            entidade_id,
            primary_perfil_id,
            d["login"].strip().lower(),
            d["nome"].strip(),
            email,
            senha_hash,
            d.get("status", 1),
            id
        )
    else:
        sql = """
            UPDATE usuario
            SET entidade_id = %s, perfil_id = %s, login = %s, nome = %s, email = %s,
                status = %s
            WHERE id = %s
        """
        params = (
            entidade_id,
            primary_perfil_id,
            d["login"].strip().lower(),
            d["nome"].strip(),
            email,
            d.get("status", 1),
            id
        )

    with conectar() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        if perfil_ids:
            sincronizar_perfis(id, perfil_ids)

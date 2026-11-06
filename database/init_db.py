"""
Script para inicialização e migração do banco de dados MySQL do Estok.
Executa o schema.sql e garante que a estrutura de tabelas, perfis e super-admin existam.
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import conectar
from app.config import Config


def inicializar_banco():
    print(f"[*] Conectando ao MySQL em {Config.DB_HOST}:{Config.DB_PORT} no banco '{Config.DB_NAME}'...")
    schema_path = BASE_DIR / "database" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    comandos = [c.strip() for c in sql_content.split(";") if c.strip()]

    with conectar() as conn, conn.cursor() as cur:
        # Se tabela suprimento já existia no banco sem a coluna entidade_id, ajustamos antes
        try:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'suprimento' AND COLUMN_NAME = 'entidade_id'
            """, (Config.DB_NAME,))
            res = cur.fetchone()
            if res and res.get("count", 0) == 0:
                print("[*] Adaptando tabela legada 'suprimento' para multi-tenancy (adicionando entidade_id)...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS entidade (
                        id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        nome VARCHAR(150) NOT NULL,
                        identificador VARCHAR(50) NULL,
                        status TINYINT(1) NOT NULL DEFAULT 1,
                        UNIQUE KEY uq_entidade_identificador (identificador)
                    )
                """)
                cur.execute("INSERT IGNORE INTO entidade (id, nome, identificador) VALUES (1, 'Estok Matriz', 'MATRIZ-01')")
                cur.execute("ALTER TABLE suprimento ADD COLUMN entidade_id INT UNSIGNED NOT NULL DEFAULT 1 AFTER id")
        except Exception:
            pass

        # Garante que a coluna 'identificador' exista na tabela 'entidade'
        try:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'entidade' AND COLUMN_NAME = 'identificador'
            """, (Config.DB_NAME,))
            res = cur.fetchone()
            if res and res.get("count", 0) == 0:
                print("[*] Adicionando coluna 'identificador' na tabela 'entidade'...")
                cur.execute("ALTER TABLE entidade ADD COLUMN identificador VARCHAR(50) NULL AFTER nome")
                cur.execute("ALTER TABLE entidade ADD UNIQUE KEY uq_entidade_identificador (identificador)")
        except Exception:
            pass

        # Se tabela usuario já existia sem a coluna login, adiciona
        try:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuario' AND COLUMN_NAME = 'login'
            """, (Config.DB_NAME,))
            res = cur.fetchone()
            if res and res.get("count", 0) == 0:
                print("[*] Adicionando coluna 'login' na tabela 'usuario'...")
                cur.execute("ALTER TABLE usuario ADD COLUMN login VARCHAR(50) NOT NULL DEFAULT 'user' AFTER perfil_id")
                cur.execute("ALTER TABLE usuario ADD UNIQUE KEY uq_usuario_login (login)")
        except Exception:
            pass

        for cmd in comandos:
            if cmd.upper().startswith("USE ") or cmd.upper().startswith("CREATE DATABASE"):
                continue
            try:
                cur.execute(cmd)
            except Exception as e:
                print(f"[!] Aviso no comando SQL: {e}")

    print("[+] Banco de dados inicializado/atualizado com sucesso!")
    print("[+] Empresas, perfis, catálogo de suprimentos e solicitações importados.")
    print("[+] Usuários disponíveis (SENHA DE TODOS = '123'):")
    print("    - Super-Admin:     login='admin'         / senha='123'")
    print("    - Michel Salles:   login='michel.salles' / senha='123'")
    print("    - Gerente Matriz:  login='gerente'       / senha='123'")
    print("    - Gestor Matriz:   login='gestor'        / senha='123'")
    print("    - Solicitante:     login='solicitante'   / senha='123'")
    print("    - Admin Entidade:  login='admin.entidade'/ senha='123'")


if __name__ == "__main__":
    inicializar_banco()

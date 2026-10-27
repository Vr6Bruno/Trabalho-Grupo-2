from flask import Blueprint, render_template, request, redirect, url_for, abort, flash, session
from pymysql.err import IntegrityError
from app.auth import admin_required, super_admin_required
import app.models.entidade as modelo_entidade
import app.models.usuario as modelo_usuario

bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================================================
# GESTÃO DE ENTIDADES (EXCLUSIVO PARA SUPER-ADMIN)
# ============================================================================

@bp.route("/entidades")
@super_admin_required
def entidades_lista():
    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "")
    entidades = modelo_entidade.listar(busca=busca, status=status)
    return render_template(
        "admin/entidades_lista.html",
        entidades=entidades,
        filtros={"busca": busca, "status": status}
    )


@bp.route("/entidades/novo", methods=["GET", "POST"])
@super_admin_required
def entidades_novo():
    entidade = {"status": 1}
    erros = []

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        identificador = request.form.get("identificador", "").strip() or None
        status = 1 if request.form.get("status") == "1" else 0

        entidade = {
            "nome": nome,
            "identificador": identificador,
            "status": status,
        }

        if not nome:
            erros.append("O nome da entidade é obrigatório.")

        if not erros:
            try:
                modelo_entidade.criar(entidade)
                return redirect(url_for("admin.entidades_lista"))
            except Exception as e:
                erros.append(f"Erro ao cadastrar entidade: {e}")

    return render_template("admin/entidade_form.html", entidade=entidade, editando=False, erros=erros)


@bp.route("/entidades/<int:id>/editar", methods=["GET", "POST"])
@super_admin_required
def entidades_editar(id):
    entidade = modelo_entidade.buscar(id)
    if not entidade:
        abort(404)

    erros = []
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        identificador = request.form.get("identificador", "").strip() or None
        status = 1 if request.form.get("status") == "1" else 0

        dados = {
            "nome": nome,
            "identificador": identificador,
            "status": status,
        }
        entidade.update(dados)

        if not nome:
            erros.append("O nome da entidade é obrigatório.")

        if not erros:
            try:
                modelo_entidade.atualizar(id, dados)
                return redirect(url_for("admin.entidades_lista"))
            except Exception as e:
                erros.append(f"Erro ao atualizar entidade: {e}")

    return render_template("admin/entidade_form.html", entidade=entidade, editando=True, erros=erros)


# ============================================================================
# GESTÃO DE USUÁRIOS (SUPER_ADMIN E ADMINISTRADOR DA ENTIDADE)
# ============================================================================

@bp.route("/usuarios")
@admin_required
def usuarios_lista():
    usuario_logado = session.get("usuario", {})
    perfil_atual = usuario_logado.get("perfil")
    is_super = perfil_atual == "SUPER_ADMIN"

    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "")

    # Se for Administrador da Entidade, restringe os usuários estritamente à sua entidade
    if is_super:
        entidade_id = request.args.get("entidade_id", "")
        ent_id = int(entidade_id) if entidade_id.isdigit() else None
        entidades = modelo_entidade.listar(status="1")
        perfis = modelo_usuario.listar_perfis()
    else:
        ent_id = usuario_logado.get("entidade_id")
        entidades = []
        todos_perfis = modelo_usuario.listar_perfis()
        perfis = [p for p in todos_perfis if p["codigo"] != "SUPER_ADMIN"]

    perfil_id = request.args.get("perfil_id", "")
    perf_id = int(perfil_id) if perfil_id.isdigit() else None

    usuarios = modelo_usuario.listar(
        entidade_id=ent_id,
        perfil_id=perf_id,
        busca=busca,
        status=status
    )

    return render_template(
        "admin/usuarios_lista.html",
        usuarios=usuarios,
        entidades=entidades,
        perfis=perfis,
        is_super_admin=is_super,
        filtros={
            "busca": busca,
            "status": status,
            "entidade_id": str(ent_id or ""),
            "perfil_id": perfil_id
        }
    )


@bp.route("/usuarios/novo", methods=["GET", "POST"])
@admin_required
def usuarios_novo():
    usuario_logado = session.get("usuario", {})
    is_super = usuario_logado.get("perfil") == "SUPER_ADMIN"

    entidades = modelo_entidade.listar(status="1") if is_super else []
    todos_perfis = modelo_usuario.listar_perfis()
    perfis = todos_perfis if is_super else [p for p in todos_perfis if p["codigo"] != "SUPER_ADMIN"]

    usuario = {"status": 1, "perfil_id": 4}  # Padrão: Solicitante
    erros = []

    if request.method == "POST":
        login = request.form.get("login", "").strip().lower()
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        senha = request.form.get("senha", "")
        status = 1 if request.form.get("status") == "1" else 0

        if is_super:
            entidade_id = request.form.get("entidade_id", "").strip() or None
            if entidade_id and entidade_id.isdigit():
                entidade_id = int(entidade_id)
            else:
                entidade_id = None
        else:
            entidade_id = usuario_logado.get("entidade_id")

        # Múltiplos perfis
        perfil_ids = [int(p) for p in request.form.getlist("perfil_ids") if p.isdigit()]
        if not perfil_ids and request.form.get("perfil_id", "").isdigit():
            perfil_ids = [int(request.form.get("perfil_id"))]

        # Bloqueia criação de Super-Admin por Administrador de Entidade
        if not is_super:
            super_admin_perfil = next((p for p in todos_perfis if p["codigo"] == "SUPER_ADMIN"), None)
            if super_admin_perfil and super_admin_perfil["id"] in perfil_ids:
                erros.append("Você não possui permissão para atribuir o perfil Super-Admin.")

        primary_perfil_id = perfil_ids[0] if perfil_ids else 0

        usuario = {
            "login": login,
            "nome": nome,
            "email": email,
            "perfil_id": primary_perfil_id,
            "perfil_ids": perfil_ids,
            "entidade_id": entidade_id,
            "status": status,
        }

        if not login:
            erros.append("O login é obrigatório.")
        if not nome:
            erros.append("O nome do usuário é obrigatório.")
        if not senha or len(senha) < 4:
            erros.append("A senha deve possuir ao menos 4 caracteres.")
        if not perfil_ids:
            erros.append("Selecione ao menos um perfil de acesso para o usuário.")

        # Verifica se possui perfil Super-Admin
        tem_super_admin = any(
            p["codigo"] == "SUPER_ADMIN"
            for p in todos_perfis if p["id"] in perfil_ids
        )
        if not tem_super_admin and not entidade_id:
            erros.append("Usuários vinculados à entidade devem possuir uma entidade associada.")

        if not erros:
            try:
                dados = {
                    "login": login,
                    "nome": nome,
                    "email": email,
                    "senha": senha,
                    "perfil_id": primary_perfil_id,
                    "perfil_ids": perfil_ids,
                    "entidade_id": entidade_id,
                    "status": status,
                }
                modelo_usuario.criar(dados)
                flash(f"Usuário '{login}' criado com sucesso!", "sucesso")
                return redirect(url_for("admin.usuarios_lista"))
            except IntegrityError:
                erros.append("Já existe um usuário cadastrado com este login.")
            except Exception as e:
                erros.append(f"Erro ao criar usuário: {e}")

    return render_template(
        "admin/usuario_form.html",
        usuario_editado=usuario,
        usuario=usuario,
        entidades=entidades,
        perfis=perfis,
        is_super_admin=is_super,
        editando=False,
        erros=erros
    )


@bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def usuarios_editar(id):
    usuario_logado = session.get("usuario", {})
    is_super = usuario_logado.get("perfil") == "SUPER_ADMIN"

    usuario = modelo_usuario.buscar_por_id(id)
    if not usuario:
        abort(404)

    # Administrador de Entidade só pode editar usuários da sua entidade e não pode editar Super-Admin
    if not is_super:
        if usuario.get("entidade_id") != usuario_logado.get("entidade_id"):
            flash("Você só pode gerenciar usuários vinculados à sua entidade.", "alerta")
            return redirect(url_for("admin.usuarios_lista"))
        if usuario.get("perfil_codigo") == "SUPER_ADMIN" or any(p["codigo"] == "SUPER_ADMIN" for p in usuario.get("perfis", [])):
            flash("Você não possui permissão para editar um Super-Administrador.", "alerta")
            return redirect(url_for("admin.usuarios_lista"))

    erros = []
    entidades = modelo_entidade.listar(status="1") if is_super else []
    todos_perfis = modelo_usuario.listar_perfis()
    perfis = todos_perfis if is_super else [p for p in todos_perfis if p["codigo"] != "SUPER_ADMIN"]

    if request.method == "POST":
        login = request.form.get("login", "").strip().lower()
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        nova_senha = request.form.get("senha", "").strip()
        status = 1 if request.form.get("status") == "1" else 0

        if is_super:
            entidade_id = request.form.get("entidade_id", "").strip() or None
            if entidade_id and entidade_id.isdigit():
                entidade_id = int(entidade_id)
            else:
                entidade_id = None
        else:
            entidade_id = usuario_logado.get("entidade_id")

        # Múltiplos perfis
        perfil_ids = [int(p) for p in request.form.getlist("perfil_ids") if p.isdigit()]
        if not perfil_ids and request.form.get("perfil_id", "").isdigit():
            perfil_ids = [int(request.form.get("perfil_id"))]

        # Bloqueia concessão de Super-Admin por Administrador de Entidade
        if not is_super:
            super_admin_perfil = next((p for p in todos_perfis if p["codigo"] == "SUPER_ADMIN"), None)
            if super_admin_perfil and super_admin_perfil["id"] in perfil_ids:
                erros.append("Você não possui permissão para atribuir o perfil Super-Admin.")

        primary_perfil_id = perfil_ids[0] if perfil_ids else usuario["perfil_id"]

        dados = {
            "login": login,
            "nome": nome,
            "email": email,
            "perfil_id": primary_perfil_id,
            "perfil_ids": perfil_ids,
            "entidade_id": entidade_id,
            "status": status,
        }
        usuario.update(dados)

        if not login:
            erros.append("O login é obrigatório.")
        if not nome:
            erros.append("O nome do usuário é obrigatório.")
        if nova_senha and len(nova_senha) < 4:
            erros.append("A nova senha deve possuir ao menos 4 caracteres.")
        if not perfil_ids:
            erros.append("Selecione ao menos um perfil de acesso para o usuário.")

        tem_super_admin = any(
            p["codigo"] == "SUPER_ADMIN"
            for p in todos_perfis if p["id"] in perfil_ids
        )
        if not tem_super_admin and not entidade_id:
            erros.append("Usuários vinculados à entidade devem possuir uma entidade associada.")

        if not erros:
            try:
                modelo_usuario.atualizar(id, dados, nova_senha=nova_senha or None)
                flash(f"Usuário '{login}' atualizado com sucesso!", "sucesso")
                return redirect(url_for("admin.usuarios_lista"))
            except IntegrityError:
                erros.append("Já existe um usuário cadastrado com este login.")
            except Exception as e:
                erros.append(f"Erro ao atualizar usuário: {e}")

    return render_template(
        "admin/usuario_form.html",
        usuario_editado=usuario,
        usuario=usuario,
        entidades=entidades,
        perfis=perfis,
        is_super_admin=is_super,
        editando=True,
        erros=erros
    )


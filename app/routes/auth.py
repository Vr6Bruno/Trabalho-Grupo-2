from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import app.models.usuario as modelo_usuario
import app.models.entidade as modelo_entidade

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario"):
        return redirect(url_for("suprimentos.lista"))

    erro = None
    login_informado = ""

    if request.method == "POST":
        login_informado = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")

        if not login_informado or not senha:
            erro = "Informe o login e a senha para acessar."
        else:
            usuario = modelo_usuario.buscar_por_login(login_informado)
            if not usuario or not modelo_usuario.verificar_senha(usuario["senha_hash"], senha):
                erro = "Login ou senha incorretos."
            elif not usuario["status"]:
                erro = "Este usuário está inativo no sistema. Contate o administrador."
            elif usuario["entidade_id"] and usuario.get("entidade_status") == 0:
                erro = "A entidade vinculada a este usuário está inativa."
            else:
                # Login com sucesso! Grava na sessão
                perfis = usuario.get("perfis", [])
                is_super_admin = bool(usuario.get("is_super_admin"))
                entidade_id = usuario.get("entidade_id")
                entidade_nome = usuario.get("entidade_nome")
                if not entidade_nome:
                    entidade_nome = "Todas as Entidades" if is_super_admin else "Estok"

                session["usuario"] = {
                    "id": usuario["id"],
                    "login": usuario["login"],
                    "nome": usuario["nome"],
                    "email": usuario["email"],
                    "perfil": usuario["perfil_codigo"],
                    "perfil_nome": usuario["perfil_nome"],
                    "perfil_id": usuario.get("perfil_id"),
                    "perfis": perfis,
                    "is_super_admin": is_super_admin,
                    "entidade_id": entidade_id,
                    "entidade_nome": entidade_nome,
                }

                next_url = request.args.get("next")
                if usuario["perfil_codigo"] == "SUPER_ADMIN" and (not next_url or next_url == "/"):
                    return redirect(url_for("admin.entidades_lista"))
                if usuario["perfil_codigo"] == "SOLICITANTE" and (not next_url or next_url == "/"):
                    return redirect(url_for("solicitacoes.lista"))
                return redirect(next_url or url_for("suprimentos.lista"))

    return render_template("auth/login.html", erro=erro, login_informado=login_informado)


@bp.route("/trocar-perfil", methods=["POST"])
def trocar_perfil():
    """
    Alterna o perfil ativo da sessão entre os perfis atribuídos ao usuário.
    Super-Admin tem permissão para alternar para qualquer perfil do sistema.
    """
    usuario_sessao = session.get("usuario")
    if not usuario_sessao:
        return redirect(url_for("auth.login"))

    novo_perfil_id = request.form.get("perfil_id", "").strip()
    if not novo_perfil_id.isdigit():
        flash("Perfil inválido.", "erro")
        return redirect(request.referrer or url_for("suprimentos.lista"))

    novo_perfil_id = int(novo_perfil_id)
    import app.models.usuario as modelo_usuario

    # Se for Super-Admin, pode alternar para qualquer perfil do sistema
    if usuario_sessao.get("is_super_admin") or usuario_sessao.get("perfil") == "SUPER_ADMIN":
        perfis_permitidos = modelo_usuario.listar_perfis()
    else:
        perfis_permitidos = modelo_usuario.listar_perfis_do_usuario(usuario_sessao["id"])

    perfil_encontrado = next((p for p in perfis_permitidos if p["id"] == novo_perfil_id), None)

    if not perfil_encontrado:
        flash("Você não possui permissão para alternar para este perfil.", "erro")
        return redirect(request.referrer or url_for("suprimentos.lista"))

    usuario_sessao["perfil"] = perfil_encontrado["codigo"]
    usuario_sessao["perfil_nome"] = perfil_encontrado["nome"]
    usuario_sessao["perfil_id"] = perfil_encontrado["id"]
    if usuario_sessao.get("is_super_admin"):
        usuario_sessao["is_super_admin"] = True

    session["usuario"] = usuario_sessao
    session.modified = True

    flash(f"Perfil ativo alterado para: {perfil_encontrado['nome']}", "sucesso")
    destino_fallback = url_for("solicitacoes.lista") if usuario_sessao.get("perfil") == "SOLICITANTE" else url_for("suprimentos.lista")
    return redirect(request.referrer or destino_fallback)


@bp.route("/trocar-entidade", methods=["POST"])
def trocar_entidade():
    """
    Alterna a entidade ativa da sessão.
    Exclusivo para Super-Admins, permitindo transitar entre entidades específicas ou visão global.
    """
    usuario_sessao = session.get("usuario")
    if not usuario_sessao:
        return redirect(url_for("auth.login"))

    if not (usuario_sessao.get("is_super_admin") or usuario_sessao.get("perfil") == "SUPER_ADMIN"):
        flash("Apenas Super-Administradores podem alternar entre entidades.", "erro")
        return redirect(request.referrer or url_for("suprimentos.lista"))

    entidade_id_raw = request.form.get("entidade_id", "").strip()

    if not entidade_id_raw or entidade_id_raw in ("", "todas", "0", "None"):
        usuario_sessao["entidade_id"] = None
        usuario_sessao["entidade_nome"] = "Todas as Entidades"
        flash("Contexto alterado para: Todas as Entidades (Visão Global)", "sucesso")
    else:
        try:
            eid = int(entidade_id_raw)
            entidade = modelo_entidade.buscar_por_id(eid)
            if not entidade:
                flash("Entidade não encontrada.", "erro")
                return redirect(request.referrer or url_for("suprimentos.lista"))
            usuario_sessao["entidade_id"] = entidade["id"]
            usuario_sessao["entidade_nome"] = entidade["nome"]
            flash(f"Contexto alterado para a entidade: {entidade['nome']}", "sucesso")
        except ValueError:
            flash("Identificador de entidade inválido.", "erro")

    session["usuario"] = usuario_sessao
    session.modified = True
    return redirect(request.referrer or url_for("suprimentos.lista"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


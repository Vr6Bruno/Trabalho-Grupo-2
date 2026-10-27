from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from app.auth import login_required, roles_required
import app.models.solicitacao as modelo_solicitacao
import app.models.suprimento as modelo_suprimento
import app.models.entidade as modelo_entidade
import app.models.pedido as modelo_pedido

bp = Blueprint("solicitacoes", __name__)


def obter_entidade_do_contexto():
    usuario = session.get("usuario", {})
    if usuario.get("perfil") == "SUPER_ADMIN":
        param_entidade = request.args.get("entidade_id", "")
        if param_entidade.isdigit():
            return int(param_entidade)
        form_entidade = request.form.get("entidade_id", "")
        if form_entidade.isdigit():
            return int(form_entidade)
        return usuario.get("entidade_id")
    return usuario.get("entidade_id")


@bp.route("/solicitacoes")
@login_required
def lista():
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_id = obter_entidade_do_contexto()

    # Se for SOLICITANTE, restringe para ver apenas as suas solicitações
    solicitante_id = usuario["id"] if usuario.get("perfil") == "SOLICITANTE" else None

    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "").strip()

    resumo = modelo_solicitacao.resumo(entidade_id=entidade_id, solicitante_id=solicitante_id)
    solicitacoes = modelo_solicitacao.listar(
        entidade_id=entidade_id,
        solicitante_id=solicitante_id,
        status=status,
        busca=busca
    )

    entidades_filtro = modelo_entidade.listar(status="1") if is_admin else []

    return render_template(
        "solicitacoes/lista.html",
        solicitacoes=solicitacoes,
        resumo=resumo,
        is_admin=is_admin,
        pode_operar=(usuario.get("perfil") != "SOLICITANTE"),
        entidades_filtro=entidades_filtro,
        filtros={
            "busca": busca,
            "status": status,
            "entidade_id": str(entidade_id or "")
        }
    )


@bp.route("/solicitacoes/nova", methods=["GET", "POST"])
@login_required
def nova():
    usuario = session["usuario"]
    is_admin = bool(usuario.get("perfil") == "SUPER_ADMIN")
    entidade_id = obter_entidade_do_contexto()

    erros = []
    suprimentos = modelo_suprimento.listar(entidade_id=entidade_id, status="1")

    if request.method == "POST":
        f = request.form
        observacao = f.get("observacao", "").strip()

        # Lê os itens dinâmicos do formulário
        suprimento_ids = f.getlist("item_suprimento_id[]")
        quantidades = f.getlist("item_quantidade[]")

        itens = []
        for sid, qtd in zip(suprimento_ids, quantidades):
            if sid and qtd:
                try:
                    q = int(qtd)
                    if q > 0:
                        itens.append({"suprimento_id": int(sid), "quantidade": q})
                except ValueError:
                    pass

        if not itens:
            erros.append("Adicione pelo menos um suprimento com quantidade válida.")

        if not erros:
            sucesso, resultado = modelo_solicitacao.criar(
                entidade_id=entidade_id,
                solicitante_id=usuario["id"],
                itens=itens,
                observacao=observacao
            )
            if sucesso:
                flash(f"Solicitação #{resultado} criada com sucesso!", "sucesso")
                return redirect(url_for("solicitacoes.detalhe", id=resultado))
            else:
                erros.append(resultado)

    return render_template(
        "solicitacoes/novo.html",
        suprimentos=suprimentos,
        erros=erros
    )


@bp.route("/solicitacoes/<int:id>")
@login_required
def detalhe(id):
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_restricao = None if is_admin else usuario.get("entidade_id")

    solicitacao = modelo_solicitacao.buscar(id, entidade_id=entidade_restricao)
    if not solicitacao:
        abort(404)

    # Solicitante comum só pode ver suas próprias solicitações
    if usuario.get("perfil") == "SOLICITANTE" and solicitacao["solicitante_id"] != usuario["id"]:
        abort(403)

    itens = modelo_solicitacao.listar_itens(id)
    historico = modelo_solicitacao.listar_historico(id)

    # Identifica se o usuário pode aprovar / rejeitar / separar / entregar de acordo com a UML
    perfil = usuario.get("perfil")
    pode_validar = perfil in ("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR", "ESTOQUISTA") and solicitacao["status"] == "solicitada"
    pode_separar = perfil in ("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR", "ESTOQUISTA") and solicitacao["status"] in ("aprovada", "aguardando_estoque")
    pode_entregar = perfil in ("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR", "ESTOQUISTA") and solicitacao["status"] == "separada"
    pode_cancelar = (
        (perfil in ("SUPER_ADMIN", "ADMIN", "GERENTE")) or
        (solicitacao["solicitante_id"] == usuario["id"] and solicitacao["status"] == "solicitada")
    ) and solicitacao["status"] not in ("entregue", "cancelada", "rejeitada")

    return render_template(
        "solicitacoes/detalhe.html",
        solicitacao=solicitacao,
        itens=itens,
        historico=historico,
        pode_validar=pode_validar,
        pode_separar=pode_separar,
        pode_entregar=pode_entregar,
        pode_cancelar=pode_cancelar
    )


@bp.route("/solicitacoes/<int:id>/aprovar", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def aprovar(id):
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    sucesso, msg = modelo_solicitacao.aprovar(
        id=id,
        validador_id=usuario["id"],
        entidade_id=None if is_admin else usuario.get("entidade_id")
    )
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")

    return redirect(url_for("solicitacoes.detalhe", id=id))


@bp.route("/solicitacoes/<int:id>/rejeitar", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def rejeitar(id):
    usuario = session["usuario"]
    justificativa = request.form.get("justificativa", "").strip()
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"

    sucesso, msg = modelo_solicitacao.rejeitar(
        id=id,
        validador_id=usuario["id"],
        justificativa=justificativa,
        entidade_id=None if is_admin else usuario.get("entidade_id")
    )
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")

    return redirect(url_for("solicitacoes.detalhe", id=id))


@bp.route("/solicitacoes/<int:id>/cancelar", methods=["POST"])
@login_required
def cancelar(id):
    usuario = session["usuario"]
    motivo = request.form.get("motivo", "").strip()
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"

    sucesso, msg = modelo_solicitacao.cancelar(
        id=id,
        usuario_id=usuario["id"],
        motivo=motivo,
        entidade_id=None if is_admin else usuario.get("entidade_id")
    )
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")

    return redirect(url_for("solicitacoes.detalhe", id=id))


@bp.route("/solicitacoes/<int:id>/separar", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def separar(id):
    usuario = session["usuario"]
    # Recebe os campos do form de separação: qtd_separar[item_id]
    itens_separar = {}
    for key, value in request.form.items():
        if key.startswith("qtd_separar_"):
            item_id = int(key.replace("qtd_separar_", ""))
            try:
                qtd = int(value)
                if qtd > 0:
                    itens_separar[item_id] = qtd
            except ValueError:
                pass

    if not itens_separar:
        flash("Nenhuma quantidade informada para separação.", "erro")
        return redirect(url_for("solicitacoes.compilado"))

    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    sucesso, msg = modelo_solicitacao.separar_itens(
        solicitacao_id=id,
        itens_separar=itens_separar,
        operador_id=usuario["id"],
        entidade_id=None if is_admin else usuario.get("entidade_id")
    )
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")

    return redirect(url_for("solicitacoes.compilado"))


@bp.route("/solicitacoes/<int:id>/entregar", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def entregar(id):
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    sucesso, msg = modelo_solicitacao.entregar(
        id=id,
        entregador_id=usuario["id"],
        entidade_id=None if is_admin else usuario.get("entidade_id")
    )
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")

    return redirect(url_for("solicitacoes.detalhe", id=id))


@bp.route("/solicitacoes/compilado")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def compilado():
    usuario = session["usuario"]
    entidade_id = obter_entidade_do_contexto()

    solicitacoes_compilado = modelo_solicitacao.compilado_operacional(entidade_id=entidade_id)

    return render_template(
        "solicitacoes/compilado.html",
        tickets=solicitacoes_compilado
    )

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from app.auth import roles_required
import app.models.pedido as modelo_pedido
import app.models.suprimento as modelo_suprimento
import app.models.entidade as modelo_entidade

bp = Blueprint("pedidos", __name__)


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


@bp.route("/pedidos")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def lista():
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_id = obter_entidade_do_contexto()

    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "").strip()

    resumo = modelo_pedido.resumo(entidade_id=entidade_id)
    pedidos = modelo_pedido.listar(entidade_id=entidade_id, status=status, busca=busca)
    entidades_filtro = modelo_entidade.listar(status="1") if is_admin else []

    return render_template(
        "pedidos/lista.html",
        pedidos=pedidos,
        resumo=resumo,
        is_admin=is_admin,
        entidades_filtro=entidades_filtro,
        filtros={
            "busca": busca,
            "status": status,
            "entidade_id": str(entidade_id or "")
        }
    )


@bp.route("/pedidos/novo", methods=["GET", "POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def novo():
    usuario = session["usuario"]
    is_admin = bool(usuario.get("perfil") == "SUPER_ADMIN")
    entidade_id = obter_entidade_do_contexto()

    suprimento_param = request.args.get("suprimento_id")
    qtd_param = request.args.get("quantidade", "1")
    sol_param = request.args.get("solicitacao_id")

    erros = []
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        observacao = f.get("observacao", "").strip()

        item_inicial = None
        sid = f.get("item_suprimento_id")
        qtd = f.get("item_quantidade")
        if sid and qtd:
            try:
                item_inicial = {
                    "suprimento_id": int(sid),
                    "quantidade": int(qtd),
                    "observacao": f.get("item_observacao")
                }
            except ValueError:
                pass

        sucesso, resultado = modelo_pedido.criar(
            entidade_id=entidade_id,
            usuario_id=usuario["id"],
            nome=nome,
            observacao=observacao,
            item_inicial=item_inicial
        )
        if sucesso:
            flash("Pedido de compra criado com sucesso!", "sucesso")
            return redirect(url_for("pedidos.detalhe", id=resultado))
        else:
            erros.append(resultado)

    suprimentos = modelo_suprimento.listar(entidade_id=entidade_id, status="1")
    return render_template(
        "pedidos/novo.html",
        suprimentos=suprimentos,
        suprimento_param=int(suprimento_param) if suprimento_param and suprimento_param.isdigit() else None,
        qtd_param=qtd_param,
        sol_param=sol_param,
        erros=erros
    )


@bp.route("/pedidos/<int:id>")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def detalhe(id):
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_restricao = None if is_admin else usuario.get("entidade_id")

    pedido = modelo_pedido.buscar(id, entidade_id=entidade_restricao)
    if not pedido:
        abort(404)

    itens = modelo_pedido.listar_itens(id)
    suprimentos = modelo_suprimento.listar(entidade_id=pedido["entidade_id"], status="1")

    pode_gerenciar = usuario.get("perfil") in ("SUPER_ADMIN", "ADMIN", "GERENTE")

    return render_template(
        "pedidos/detalhe.html",
        pedido=pedido,
        itens=itens,
        suprimentos=suprimentos,
        pode_gerenciar=pode_gerenciar
    )


@bp.route("/pedidos/<int:id>/status", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def atualizar_status(id):
    usuario = session["usuario"]
    if usuario.get("perfil") not in ("SUPER_ADMIN", "ADMIN", "GERENTE"):
        flash("Apenas gerentes e administradores podem alterar o status do pedido de compra.", "erro")
        return redirect(url_for("pedidos.detalhe", id=id))

    novo_status = request.form.get("status", "").strip()
    observacao = request.form.get("observacao")
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"

    sucesso, msg = modelo_pedido.atualizar_status(
        id=id,
        novo_status=novo_status,
        observacao=observacao,
        entidade_id=None if is_admin else usuario.get("entidade_id")
    )
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")

    return redirect(url_for("pedidos.detalhe", id=id))


@bp.route("/pedidos/<int:id>/adicionar-item", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def adicionar_item(id):
    usuario = session["usuario"]
    f = request.form
    try:
        suprimento_id = int(f.get("suprimento_id", 0))
        quantidade = int(f.get("quantidade", 0))
    except ValueError:
        suprimento_id = 0
        quantidade = 0

    observacao = f.get("observacao", "").strip()

    if suprimento_id <= 0 or quantidade <= 0:
        flash("Informe um suprimento e quantidade válida.", "erro")
    else:
        sucesso, msg = modelo_pedido.adicionar_item(
            pedido_id=id,
            suprimento_id=suprimento_id,
            quantidade_necessaria=quantidade,
            observacao=observacao
        )
        if sucesso:
            flash(msg, "sucesso")
        else:
            flash(msg, "erro")

    return redirect(url_for("pedidos.detalhe", id=id))


@bp.route("/pedidos/<int:id>/remover-item/<int:item_id>", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def remover_item(id, item_id):
    sucesso, msg = modelo_pedido.remover_item(item_id=item_id, pedido_id=id)
    if sucesso:
        flash(msg, "sucesso")
    else:
        flash(msg, "erro")
    return redirect(url_for("pedidos.detalhe", id=id))


@bp.route("/pedidos/<int:id>/receber-item/<int:item_id>", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def receber_item(id, item_id):
    usuario = session["usuario"]
    if usuario.get("perfil") not in ("SUPER_ADMIN", "ADMIN", "GERENTE"):
        flash("Permissão negada para registrar recebimento de compras.", "erro")
        return redirect(url_for("pedidos.detalhe", id=id))

    try:
        qtd_recebida = int(request.form.get("qtd_recebida", 0))
    except ValueError:
        qtd_recebida = 0

    if qtd_recebida <= 0:
        flash("Informe uma quantidade recebida maior que zero.", "erro")
    else:
        is_admin = usuario.get("perfil") == "SUPER_ADMIN"
        sucesso, msg = modelo_pedido.receber_item(
            pedido_id=id,
            item_id=item_id,
            quantidade_recebida=qtd_recebida,
            usuario_id=usuario["id"],
            entidade_id=None if is_admin else usuario.get("entidade_id")
        )
        if sucesso:
            flash(msg, "sucesso")
        else:
            flash(msg, "erro")

    return redirect(url_for("pedidos.detalhe", id=id))

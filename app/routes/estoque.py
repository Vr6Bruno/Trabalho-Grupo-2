from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from datetime import datetime
from app.auth import roles_required
import app.models.estoque as modelo_estoque
import app.models.suprimento as modelo_suprimento
import app.models.entidade as modelo_entidade

bp = Blueprint("estoque", __name__)


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


@bp.route("/estoque")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def painel():
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_id = obter_entidade_do_contexto()

    busca = request.args.get("busca", "").strip()
    situacao = request.args.get("situacao", "").strip()

    resumo = modelo_estoque.resumo(entidade_id=entidade_id)
    saldos = modelo_estoque.listar_saldos(entidade_id=entidade_id, busca=busca, situacao=situacao)
    movimentacoes = modelo_estoque.listar_movimentacoes(entidade_id=entidade_id, limite=15)

    entidades_filtro = modelo_entidade.listar(status="1") if is_admin else []

    return render_template(
        "estoque/painel.html",
        resumo=resumo,
        saldos=saldos,
        movimentacoes=movimentacoes,
        is_admin=is_admin,
        entidades_filtro=entidades_filtro,
        filtros={
            "busca": busca,
            "situacao": situacao,
            "entidade_id": str(entidade_id or "")
        }
    )


@bp.route("/estoque/historico")
@bp.route("/estoque/historico/<int:suprimento_id>")
@bp.route("/estoque/movimentar")
@bp.route("/estoque/movimentar/<int:suprimento_id>")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def historico(suprimento_id=None):
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_id = obter_entidade_do_contexto()

    item_selecionado = None
    if suprimento_id:
        item_selecionado = modelo_estoque.buscar_item(suprimento_id, entidade_id=entidade_id if not is_admin else None)
        if not item_selecionado:
            abort(404)

    suprimentos_disponiveis = modelo_suprimento.listar(entidade_id=entidade_id, status="1")
    movimentacoes = modelo_estoque.listar_movimentacoes(
        entidade_id=entidade_id if not is_admin else None,
        suprimento_id=suprimento_id,
        limite=100
    )

    return render_template(
        "estoque/historico.html",
        item=item_selecionado,
        suprimentos=suprimentos_disponiveis,
        historico=movimentacoes
    )



@bp.route("/estoque/consolidado")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def consolidado():
    usuario = session["usuario"]
    entidade_id = obter_entidade_do_contexto()

    dados_consolidado = modelo_estoque.relatorio_consolidado(entidade_id=entidade_id)

    return render_template(
        "estoque/consolidado.html",
        separar_estoque=dados_consolidado["separar_estoque"],
        necessario_comprar=dados_consolidado["necessario_comprar"],
        data_hora=datetime.now().strftime("%d/%m/%Y %H:%M"),
        entidade_nome=usuario.get("entidade_nome") or "Todas as Entidades"
    )

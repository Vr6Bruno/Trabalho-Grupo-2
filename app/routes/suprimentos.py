from flask import Blueprint, render_template, request, redirect, url_for, abort
from pymysql.err import IntegrityError
import app.models.suprimento as modelo

bp = Blueprint("suprimentos", __name__)


def ler_formulario(incluir_estoque_atual=False):
    """Lê e limpa os campos do form. Retorna (dados, erros)."""
    f = request.form
    erros = []

    nome = f.get("nome", "").strip()
    if not nome:
        erros.append("O nome é obrigatório.")

    try:
        minimo = int(f.get("estoque_minimo") or 0)  # vazio -> 0
        if minimo < 0:
            raise ValueError
    except ValueError:
        minimo = 0
        erros.append("Estoque mínimo deve ser um número inteiro maior ou igual a 0.")

    dados = {
        "nome": nome,
        "codigo_interno": f.get("codigo_interno", "").strip() or None,
        "unidade_medida": f.get("unidade_medida", "").strip() or None,
        "descricao": f.get("descricao", "").strip() or None,
        "estoque_minimo": minimo,
        "status": 0 if f.get("status") == "0" else 1,
    }

    if incluir_estoque_atual:
        try:
            atual = int(f.get("estoque_atual") or 0)
            if atual < 0:
                raise ValueError
        except ValueError:
            atual = 0
            erros.append("Estoque atual deve ser um número inteiro maior ou igual a 0.")
        dados["estoque_atual"] = atual

    return dados, erros


@bp.route("/")
def inicio():
    return redirect(url_for("suprimentos.lista"))


@bp.route("/suprimentos")
def lista():
    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "1")        # padrão: só ativos
    critico = "critico" in request.args

    return render_template(
        "suprimentos/lista.html",
        suprimentos=modelo.listar(busca, status, critico),
        resumo=modelo.resumo(),
        filtros={"busca": busca, "status": status, "critico": critico},
    )


@bp.route("/suprimentos/novo", methods=["GET", "POST"])
def novo():
    suprimento = {"estoque_minimo": 0, "estoque_atual": 0, "status": 1}
    erros = []

    if request.method == "POST":
        dados, erros = ler_formulario(incluir_estoque_atual=True)
        suprimento.update(dados)
        if not erros:
            try:
                modelo.criar(dados)
                return redirect(url_for("suprimentos.lista"))
            except IntegrityError:
                erros.append("Já existe um suprimento com esse código interno.")

    return render_template("suprimentos/novo.html", suprimento=suprimento,
                           editando=False, erros=erros)


@bp.route("/suprimentos/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    suprimento = modelo.buscar(id)
    if not suprimento:
        abort(404)
    erros = []

    if request.method == "POST":
        dados, erros = ler_formulario(incluir_estoque_atual=False)
        suprimento.update(dados)
        if not erros:
            try:
                modelo.atualizar(id, dados)
                return redirect(url_for("suprimentos.lista"))
            except IntegrityError:
                erros.append("Já existe um suprimento com esse código interno.")

    return render_template("suprimentos/novo.html", suprimento=suprimento,
                           editando=True, erros=erros)

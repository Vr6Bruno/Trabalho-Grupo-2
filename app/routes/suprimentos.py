from flask import Blueprint, render_template, request, redirect, url_for, abort, session, flash
from pymysql.err import IntegrityError
from app.auth import login_required, roles_required
import app.models.suprimento as modelo
import app.models.entidade as modelo_entidade

bp = Blueprint("suprimentos", __name__)


def ler_formulario(incluir_estoque_atual=False):
    """Lê e limpa os campos do form. Retorna (dados, erros)."""
    f = request.form
    erros = []

    nome = f.get("nome", "").strip()
    if not nome:
        erros.append("O nome é obrigatório.")

    try:
        minimo = int(f.get("estoque_minimo") or 0)
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
            erros.append("Estoque inicial deve ser um número inteiro maior ou igual a 0.")
        dados["estoque_atual"] = atual

    return dados, erros


def obter_entidade_do_contexto():
    """
    Retorna a entidade_id aplicável à requisição atual.
    Para clientes (Gerente, Estoquista, etc.), SEMPRE a sua entidade_id da sessão.
    Para SUPER_ADMIN, permite filtrar por entidade ou usar a definida na sessão.
    """
    usuario = session.get("usuario", {})
    if usuario.get("perfil") == "SUPER_ADMIN":
        param_entidade = request.args.get("entidade_id", "")
        if param_entidade.isdigit():
            return int(param_entidade)
        # Se for post em formulário
        form_entidade = request.form.get("entidade_id", "")
        if form_entidade.isdigit():
            return int(form_entidade)
        return usuario.get("entidade_id")  # Pode ser None (todas) ou específico
    return usuario.get("entidade_id")


@bp.route("/")
def inicio():
    usuario = session.get("usuario")
    if not usuario:
        return redirect(url_for("auth.login"))
    if usuario.get("perfil") == "SOLICITANTE":
        return redirect(url_for("solicitacoes.lista"))
    return redirect(url_for("suprimentos.lista"))


@bp.route("/suprimentos")
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE", "GESTOR")
def lista():
    usuario = session["usuario"]
    perfil = usuario.get("perfil")
    is_admin = perfil == "SUPER_ADMIN"
    pode_editar = perfil in ("SUPER_ADMIN", "ADMIN", "GERENTE")
    entidade_id = obter_entidade_do_contexto()

    busca = request.args.get("busca", "").strip()
    status = request.args.get("status", "1")        # padrão: só ativos
    critico = "critico" in request.args

    suprimentos = modelo.listar(entidade_id=entidade_id, busca=busca, status=status, critico=critico)
    resumo = modelo.resumo(entidade_id=entidade_id)

    entidades_filtro = []
    if is_admin:
        entidades_filtro = modelo_entidade.listar(status="1")

    return render_template(
        "suprimentos/lista.html",
        suprimentos=suprimentos,
        resumo=resumo,
        is_admin=is_admin,
        pode_editar=pode_editar,
        entidades_filtro=entidades_filtro,
        filtros={
            "busca": busca,
            "status": status,
            "critico": critico,
            "entidade_id": str(entidade_id or "")
        },
    )


@bp.route("/suprimentos/novo", methods=["GET", "POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def novo():
    usuario = session["usuario"]
    is_admin = bool(usuario.get("perfil") == "SUPER_ADMIN")
    entidades = modelo_entidade.listar(status="1") if is_admin else []

    entidade_id = usuario.get("entidade_id")
    suprimento = {"estoque_minimo": 0, "estoque_atual": 0, "status": 1, "entidade_id": entidade_id}
    erros = []

    if request.method == "POST":
        dados, erros = ler_formulario(incluir_estoque_atual=True)
        suprimento.update(dados)

        if is_admin:
            form_ent = request.form.get("entidade_id", "")
            if not form_ent.isdigit():
                erros.append("Selecione a Entidade para este suprimento.")
            else:
                entidade_id = int(form_ent)
                suprimento["entidade_id"] = entidade_id
        elif not entidade_id:
            erros.append("Usuário não possui entidade associada.")

        if not erros:
            try:
                modelo.criar(dados, entidade_id=entidade_id)
                return redirect(url_for("suprimentos.lista"))
            except IntegrityError:
                erros.append("Já existe um suprimento com esse código interno nesta entidade.")
            except Exception as e:
                erros.append(f"Erro ao salvar suprimento: {e}")

    return render_template(
        "suprimentos/novo.html",
        suprimento=suprimento,
        editando=False,
        is_admin=is_admin,
        entidades=entidades,
        erros=erros
    )


@bp.route("/suprimentos/<int:id>/editar", methods=["GET", "POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def editar(id):
    usuario = session["usuario"]
    is_admin = bool(usuario.get("perfil") == "SUPER_ADMIN")
    entidade_restricao = None if is_admin else usuario.get("entidade_id")

    suprimento = modelo.buscar(id, entidade_id=entidade_restricao)
    if not suprimento:
        abort(404)

    erros = []
    if request.method == "POST":
        dados, erros = ler_formulario(incluir_estoque_atual=False)
        suprimento.update(dados)
        if not erros:
            try:
                modelo.atualizar(id, dados, entidade_id=entidade_restricao)
                return redirect(url_for("suprimentos.lista"))
            except IntegrityError:
                erros.append("Já existe um suprimento com esse código interno nesta entidade.")
            except Exception as e:
                erros.append(f"Erro ao atualizar suprimento: {e}")

    return render_template(
        "suprimentos/novo.html",
        suprimento=suprimento,
        editando=True,
        is_admin=is_admin,
        erros=erros
    )


@bp.route("/suprimentos/<int:id>/excluir", methods=["POST"])
@roles_required("SUPER_ADMIN", "ADMIN", "GERENTE")
def excluir(id):
    usuario = session["usuario"]
    is_admin = usuario.get("perfil") == "SUPER_ADMIN"
    entidade_restricao = None if is_admin else usuario.get("entidade_id")

    sucesso, mensagem = modelo.excluir(id, entidade_id=entidade_restricao)
    if sucesso:
        flash(mensagem, "sucesso")
    else:
        flash(mensagem, "erro")

    return redirect(url_for("suprimentos.lista"))

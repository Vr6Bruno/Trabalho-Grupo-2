from flask import Flask, session
from app.config import Config
from app.routes.auth import bp as auth_bp
from app.routes.admin import bp as admin_bp
from app.routes.suprimentos import bp as suprimentos_bp
from app.routes.estoque import bp as estoque_bp
from app.routes.solicitacoes import bp as solicitacoes_bp
from app.routes.pedidos import bp as pedidos_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Registro de Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(suprimentos_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(solicitacoes_bp)
    app.register_blueprint(pedidos_bp)


    @app.context_processor
    def dados_do_usuario():
        # Injeta dinamicamente os dados do usuário autenticado na sessão
        usuario = session.get("usuario")
        entidades_globais = []
        if not usuario:
            # Padrão para visitante não logado
            usuario_logado = {
                "id": None,
                "nome": "Visitante",
                "entidade_nome": "Estok",
                "perfil_nome": "Não autenticado",
                "perfil": None,
                "perfis": [],
                "is_super_admin": False,
            }
        else:
            usuario_logado = dict(usuario)
            import app.models.usuario as modelo_usuario

            # Super-Admin tem permissão para transitar entre TODOS os perfis do sistema
            if usuario_logado.get("is_super_admin") or usuario_logado.get("perfil") == "SUPER_ADMIN":
                usuario_logado["is_super_admin"] = True
                usuario_logado["perfis"] = modelo_usuario.listar_perfis()
                import app.models.entidade as modelo_entidade
                entidades_globais = modelo_entidade.listar(status="1")
            else:
                # Usuários comuns: recarrega os perfis atribuídos no banco
                usuario_logado["perfis"] = modelo_usuario.listar_perfis_do_usuario(usuario_logado.get("id"))

            session["usuario"] = usuario_logado
            session.modified = True

        return {
            "usuario_logado": usuario_logado,
            "usuario": usuario_logado,
            "entidades_globais": entidades_globais
        }

    return app

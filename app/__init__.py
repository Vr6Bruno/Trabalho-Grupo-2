from flask import Flask
from app.config import Config
from app.routes.suprimentos import bp as suprimentos_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Registro de blueprints
    app.register_blueprint(suprimentos_bp)

    @app.context_processor
    def dados_do_usuario():
        # PROVISÓRIO: trocar pelo usuário logado quando houver login
        return {"usuario": {"nome": "Usuário Teste", "entidade": "Estok", "perfil": "GESTOR"}}

    return app

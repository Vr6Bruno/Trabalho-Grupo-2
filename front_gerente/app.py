from flask import Flask
from config import Config
from rotas_suprimentos import bp as suprimentos_bp

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(suprimentos_bp)


@app.context_processor
def dados_do_usuario():
    # PROVISÓRIO: trocar pelo usuário logado quando houver login
    return {"usuario": {"nome": "Usuário Teste", "entidade": "Estok", "perfil": "GESTOR"}}


if __name__ == "__main__":
    app.run(debug=True)

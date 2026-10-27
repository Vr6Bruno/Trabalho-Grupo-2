from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("usuario"):
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """Exclusivo para Super-Admin (donos do sistema). Usado na gestão global de Entidades."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("auth.login", next=request.path))
        perfil_atual = usuario.get("perfil")
        if perfil_atual != "SUPER_ADMIN":
            flash("Apenas o Super-Administrador possui acesso à gestão de entidades.", "alerta")
            destino = url_for("solicitacoes.lista") if perfil_atual == "SOLICITANTE" else url_for("suprimentos.lista")
            return redirect(destino)
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Exige perfil SUPER_ADMIN ou ADMIN (Administrador da entidade). Usado na gestão de Usuários."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = session.get("usuario")
        if not usuario:
            return redirect(url_for("auth.login", next=request.path))
        perfil_atual = usuario.get("perfil")
        perfis_permitidos = ("SUPER_ADMIN", "ADMIN")
        if perfil_atual not in perfis_permitidos:
            flash("Acesso restrito aos administradores do sistema.", "alerta")
            destino = url_for("solicitacoes.lista") if perfil_atual == "SOLICITANTE" else url_for("suprimentos.lista")
            return redirect(destino)
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*roles):
    """Restringe acesso a rotas para perfis específicos."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            usuario = session.get("usuario")
            if not usuario:
                return redirect(url_for("auth.login", next=request.path))
            
            perfil_atual = usuario.get("perfil")

            # Super-Admin tem permissão universal
            if perfil_atual == "SUPER_ADMIN":
                return f(*args, **kwargs)

            # Normaliza aliases (ex: GESTOR e ESTOQUISTA)
            roles_set = set(roles)
            if "GESTOR" in roles_set:
                roles_set.add("ESTOQUISTA")
            if "ESTOQUISTA" in roles_set:
                roles_set.add("GESTOR")

            if perfil_atual in roles_set:
                return f(*args, **kwargs)

            flash("Seu perfil atual não possui permissão para acessar esta área.", "alerta")
            destino = url_for("solicitacoes.lista") if perfil_atual == "SOLICITANTE" else url_for("suprimentos.lista")
            return redirect(destino)
                
        return decorated_function
    return decorator

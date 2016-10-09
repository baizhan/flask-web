from flask import g
from functools import wraps
from .errors import forbidden

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args,**kwargs):
            if not g.current_user.can(permission):
                return forbidden('没有相应的权限')
            return f(*args,**kwargs)
        return decorated_function
    return decorator
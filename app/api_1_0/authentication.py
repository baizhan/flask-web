from flask.ext.httpauth import HTTPBasicAuth
from flask.ext.login import login_required,current_user
from . import api
from .errors import forbidden
#初始化Flask-HTTPAuth,支持令牌的改进验证回调
auth=HTTPBasicAuth()
@auth.verify_password
def verify_password(email_or_token,password):
    if email_or_token=='':
        g.current_user=AnonymousUser()
        return True
    if password=='':
        g.current_user=User.verify_auth_token(email_or_token)
        g.token_userd=True
        return g.current_user is not None

    user=User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user=user
    g.token_userd=False
    return user.verify_password(password)
#Flask-HTTPAuth错误处理程序
@auth.error_handler
def auth_error():
    return unauthorized('无效的证书')

#在before_request处理程序中进行认证
@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden('没有确认的账户信息')

#生成认证令牌
@api.route('/token/')
def get_token():
    if g.current_user.is_anonymous() or g.token_userd:
        return unauthorized('无效的认证')
    return jsonify({'token':g.current_user.generate_auth_token(expiration=3600),'expiration':3600})
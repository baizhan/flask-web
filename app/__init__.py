from flask import Flask,render_template
from flask.ext.bootstrap import Bootstrap
from flask.ext.moment import Moment
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail
from config import config
from flask.ext.login import LoginManager
from flask.ext.pagedown import PageDown

bootstrap=Bootstrap()
moment=Moment()
mail=Mail()
db=SQLAlchemy()
pagedown=PageDown()
login_manager=LoginManager()
login_manager.session_protection='strong'
login_manager.login_view='main.index'
def create_app(config_name):   #创建app，导入配置
    app=Flask(__name__)
    app.config.from_object(config[config_name])     #从配置文件中，获取配置名称
    config[config_name].init_app(app)       #将配置赋予给app

    bootstrap.init_app(app)
    moment.init_app(app)
    mail.init_app(app)
    db.app=app
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    #注册api蓝本
    from .api_1_0 import api as api_1_0_blueprint
    app.register_blueprint(api_1_0_blueprint,url_prefix='/api/v1.0')
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint) #注册蓝本
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint,url_prefix='/auth')
    return app

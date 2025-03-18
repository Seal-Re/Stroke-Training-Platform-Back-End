from flask import Flask
from application.config import config
from .routes import main_bp
from flask_cors import CORS

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    CORS(app)

    # 注册合并后的蓝图
    app.register_blueprint(main_bp)
    return app
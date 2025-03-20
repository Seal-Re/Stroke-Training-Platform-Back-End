# routes/__init__.py
from flask import Blueprint
from .login import login_bp
from .register import register_bp
from .questions import questions_bp
from .deliverScore import deliverScore_bp
from .submit import submit_bp
from .getLastScore import getLastScore_bp
from .images import images_bp
from .aiapi import aiapi_bp

# 创建一个新的蓝图，用于整合所有的路由
main_bp = Blueprint('main', __name__)

# 注册所有的蓝图
main_bp.register_blueprint(login_bp)
main_bp.register_blueprint(register_bp)
main_bp.register_blueprint(questions_bp)
main_bp.register_blueprint(deliverScore_bp)
main_bp.register_blueprint(submit_bp)
main_bp.register_blueprint(getLastScore_bp)
main_bp.register_blueprint(images_bp)
main_bp.register_blueprint(aiapi_bp)
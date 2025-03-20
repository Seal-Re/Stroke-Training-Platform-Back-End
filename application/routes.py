# routes/__init__.py
from flask import Blueprint
from .login import login_bp
from .register import register_bp
from .questions import questions_bp
from .questions_train import questions_train_bp
from .deliverScore import deliverScore_bp
from .deliverScoreTrain import deliverScore_train_bp
from .submit import submit_bp
from .submitTrain import submit_train_bp
from .getLastScore import getLastScore_bp
from .images import images_bp
from .aiapi import aiapi_bp
from .aiTips import aiTips_bp
from .userinfoSubmit import userinfo_submit_bp
from .userinfoGet import userinfo_get_bp   

# 创建一个新的蓝图，用于整合所有的路由
main_bp = Blueprint('main', __name__)

# 注册所有的蓝图
main_bp.register_blueprint(login_bp)
main_bp.register_blueprint(register_bp)
main_bp.register_blueprint(questions_bp)
main_bp.register_blueprint(questions_train_bp)
main_bp.register_blueprint(deliverScore_bp)
main_bp.register_blueprint(deliverScore_train_bp)
main_bp.register_blueprint(submit_bp)
main_bp.register_blueprint(submit_train_bp)
main_bp.register_blueprint(getLastScore_bp)
main_bp.register_blueprint(images_bp)
main_bp.register_blueprint(aiapi_bp)
main_bp.register_blueprint(aiTips_bp)
main_bp.register_blueprint(userinfo_submit_bp)
main_bp.register_blueprint(userinfo_get_bp)
# application/__init__.py (更新后的内容)

import logging
from flask import Flask
from application.config import config
from .routes import main_bp
from flask_cors import CORS
import os

from .wapp import ASRService 
from .RecordTest import UPLOAD_FOLDER 
from .wapp import logger as asr_logger 

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    CORS(app)

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    app.asr_service = ASRService() 

    # 注册合并后的蓝图
    app.register_blueprint(main_bp)

    if not asr_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        asr_logger.addHandler(handler)
        asr_logger.setLevel(logging.INFO)

    return app
# routes/__init__.py
from flask import Blueprint
from application.user.login import login_bp
from application.user.register import register_bp
from application.question.questions import questions_bp
from application.question.questions_train import questions_train_bp
from application.score.deliverScore import deliverScore_bp
from application.score.deliverScoreTrain import deliverScore_train_bp
from application.score.submit import submit_bp
from application.score.submitTrain import submit_train_bp
from application.score.getLastScore import getLastScore_bp
from application.image.images import images_bp
from application.ai.aiapi import aiapi_bp
from application.ai.aiTips import aiTips_bp
from application.user.userinfoSubmit import userinfo_submit_bp
from application.user.userinfoGet import userinfo_get_bp
from application.ai.aiTrain import aiTrain_bp
from application.doctor_patient.DoctorUserinfo import doctor_usersinfo_bp
from application.doctor_patient.DoctorPair import doctor_pair_bp
from application.doctor_patient.DoctorPatientScore import doctor_patient_score_bp
from application.doctor_patient.DoctorPatientInfo import doctor_patient_info_bp
from application.TTS.TTS import audio_bp
from application.TTS.asr_bp import asr_bp

# 创建一个新的蓝图，用于整合所有的路由*
main_bp = Blueprint('main', __name__)

# 注册所有的蓝图
main_bp.register_blueprint(login_bp)                       #登入
main_bp.register_blueprint(register_bp)                    #注册
main_bp.register_blueprint(questions_bp)                   #不变题目
main_bp.register_blueprint(questions_train_bp)             #训练题目
main_bp.register_blueprint(deliverScore_bp)                #处理不变题目
main_bp.register_blueprint(deliverScore_train_bp)          #处理训练
main_bp.register_blueprint(submit_bp)
main_bp.register_blueprint(submit_train_bp)                #提交
main_bp.register_blueprint(getLastScore_bp)                #最近成绩评估
main_bp.register_blueprint(images_bp)                      #图片处理
main_bp.register_blueprint(aiapi_bp)                       #调用
main_bp.register_blueprint(aiTips_bp)                      #返回
main_bp.register_blueprint(userinfo_submit_bp)
main_bp.register_blueprint(userinfo_get_bp)                #用户信息
main_bp.register_blueprint(aiTrain_bp)                     #训练题目
main_bp.register_blueprint(doctor_usersinfo_bp)            #doctor拿user
main_bp.register_blueprint(doctor_pair_bp)                 #配对
main_bp.register_blueprint(doctor_patient_score_bp)        #拿成绩
main_bp.register_blueprint(doctor_patient_info_bp)         #拿patient
main_bp.register_blueprint(audio_bp)                       #文本转语音
main_bp.register_blueprint(asr_bp)                         #语音转文字
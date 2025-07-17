from flask import Blueprint, jsonify, request
from application.db.utils import userinfo_collection, doctor_patient_collection
import logging

doctor_pair_bp = Blueprint('doctor_pair', __name__)


@doctor_pair_bp.route('/api/doctorpair', methods=['POST'])
def doctor_pair():
    try:
        data = request.get_json()
        doctor_username = data.get('doctorUsername')
        patient_username = data.get('patientUsername')
        user_info = data.get('userInfo')

        if not doctor_username or not patient_username:
            return jsonify({"success": False, "message": "缺少必要的参数"}), 400

        # 检查患者在 userinfo 集合中是否存在记录
        patient_userinfo = userinfo_collection.find_one({"user": patient_username})
        if not patient_userinfo:
            # 如果不存在，则创建一条新记录
            userinfo_collection.insert_one({
                "user": patient_username,
                "doctor": None
            })

        if user_info.get('doctor'):
            userinfo_collection.update_one(
                {"user": patient_username},
                {"$set": {"doctor": user_info.get('doctor')}}
            )

            doctor_patient = doctor_patient_collection.find_one({"doctorUsername": doctor_username})
            if doctor_patient:
                if patient_username not in doctor_patient.get('patientUsernames', []):
                    doctor_patient_collection.update_one(
                        {"doctorUsername": doctor_username},
                        {"$push": {"patientUsernames": patient_username}}
                    )
            else:
                doctor_patient_collection.insert_one({
                    "doctorUsername": doctor_username,
                    "patientUsernames": [patient_username]
                })

            return jsonify({"success": True, "message": "配对成功"})

        else:
            userinfo_collection.update_one(
                {"user": patient_username},
                {"$set": {"doctor": None}}
            )

            doctor_patient = doctor_patient_collection.find_one({"doctorUsername": doctor_username})
            if doctor_patient:
                doctor_patient_collection.update_one(
                    {"doctorUsername": doctor_username},
                    {"$pull": {"patientUsernames": patient_username}}
                )

            return jsonify({"success": True, "message": "取消配对成功"})

    except Exception as e:
        logging.error(f"Error in doctor_pair: {e}")
        return jsonify({"success": False, "message": f"操作时出错: {str(e)}"}), 500
    
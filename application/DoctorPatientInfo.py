from flask import Blueprint, request, jsonify
import logging
from .utils import doctor_patient_collection, userinfo_collection

# 创建蓝图
doctor_patient_info_bp = Blueprint('doctor_patient_info', __name__)


@doctor_patient_info_bp.route('/api/doctor_patient_info', methods=['GET'])
def doctor_patient_info():
    try:
        # 从请求参数中获取医生的用户名
        doctor_username = request.args.get('username')
        if not doctor_username:
            return jsonify({"message": "Missing username parameter"}), 400

        # 根据医生用户名从 doctor_patient 集合中查找该医生管理的病人名单
        doctor_record = doctor_patient_collection.find_one({"doctorUsername": doctor_username})
        if not doctor_record:
            logging.warning(f"No patient records found for doctor: {doctor_username}")
            return jsonify({"message": "No patient records found for the doctor", "data": []})

        patient_usernames = doctor_record.get("patientUsernames", [])

        result = []
        for patient_username in patient_usernames:
            # 根据病人用户名从 user_info 集合中查找用户信息
            user_info_record = userinfo_collection.find_one({"user": patient_username})
            if user_info_record:
                user_info_record.pop("_id", None)  # 移除 _id 字段，因为它不能直接被序列化为 JSON
                result.append({
                    "patient_username": patient_username,
                    "user_info": user_info_record
                })
            else:
                # 病人没有用户信息记录时，构造一个包含病人用户名和空用户信息的数据结构
                result.append({
                    "patient_username": patient_username,
                    "user_info": {}
                })
                logging.warning(f"No user info record found for patient: {patient_username}")

        return jsonify({"message": "成功获取医生管理病人的用户信息", "data": result})

    except Exception as e:
        logging.error(f"Error in doctor_patient_info: {e}")
        return jsonify({"message": f"获取数据时出错: {str(e)}"}), 500
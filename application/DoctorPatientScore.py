from flask import Blueprint, request, jsonify
import logging
from .utils import doctor_patient_collection, deliver_score_train_collection


# 创建蓝图
doctor_patient_score_bp = Blueprint('doctor_patient_score', __name__)


@doctor_patient_score_bp.route('/api/doctor_patient_score', methods=['GET'])
def doctor_patient_score():
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
            # 根据病人用户名从 deliver_score 集合中查找最后一条记录
            # 假设集合中有一个时间字段（如 timestamp）用于排序
            last_record = deliver_score_train_collection.find_one(
                {"username": patient_username},
                sort=[("timestamp", -1)]
            )
            if last_record:
                last_record.pop("_id", None)  # 移除 _id 字段，因为它不能直接被序列化为 JSON
                result.append({
                    "patient_username": patient_username,
                    "score_record": last_record
                })
            else:
                # 病人没有做题记录时，构造一个包含病人用户名和空答题记录的数据结构
                result.append({
                    "patient_username": patient_username,
                    "score_record": {}
                })
                logging.warning(f"No score record found for patient: {patient_username}")

        return jsonify({"message": "成功获取医生管理病人的最后分数记录", "data": result})

    except Exception as e:
        logging.error(f"Error in doctor_patient_score: {e}")
        return jsonify({"message": f"获取数据时出错: {str(e)}"}), 500
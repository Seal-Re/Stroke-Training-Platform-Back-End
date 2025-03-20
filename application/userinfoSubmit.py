from flask import Blueprint, request, jsonify
import logging
from pymongo import MongoClient
from .utils import userinfo_collection, write_mongo_data

userinfo_submit_bp = Blueprint('userinfo_submit', __name__)

@userinfo_submit_bp.route('/api/userinfo_submit', methods=['POST'])
def submit_user_info():
    try:
        data = request.get_json()
        logging.debug(f"Received data: {data}")

        user = data.get('user')
        name = data.get('name')
        email = data.get('email')
        contact = data.get('contact')
        age = data.get('age')
        medical_history = data.get('medicalHistory')

        if not user:
            return jsonify({"message": "用户标识不能为空"}), 400

        # 构建包含用户标识的用户信息
        user_info = {
            "user": user,
            "name": name,
            "email": email,
            "contact": contact,
            "age": age,
            "medicalHistory": medical_history
        }

        # 检查用户信息是否已存在，如果存在则更新，不存在则插入
        existing_user_info = userinfo_collection.find_one({"user": user})
        if existing_user_info:
            userinfo_collection.update_one({"user": user}, {"$set": user_info})
            return jsonify({"message": "用户信息更新到 MongoDB 成功"})
        else:
            # 插入数据到 MongoDB 集合
            userinfo_collection.insert_one(user_info)
            return jsonify({"message": "保存用户信息到 MongoDB 成功"})

    except Exception as e:
        logging.error(f"Error in submit_user_info: {e}")
        return jsonify({"message": f"保存用户信息到 MongoDB 时出错: {str(e)}"}), 500




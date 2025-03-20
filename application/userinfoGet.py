from flask import Blueprint, request, jsonify
import logging
from pymongo import MongoClient
from .utils import userinfo_collection, write_mongo_data

userinfo_get_bp = Blueprint('userinfo_get', __name__)

@userinfo_get_bp.route('/api/userinfo_get', methods=['GET'])
def get_user_info():
    try:
        user = request.args.get('user')
        if not user:
            return jsonify({"message": "用户标识不能为空"}), 400

        user_info = userinfo_collection.find_one({"user": user})
        if user_info:
            user_info.pop('_id', None)
            return jsonify({"message": "获取用户信息成功", "user_info": user_info})
        else:
            # 如果未找到用户信息，返回包含空值的用户信息对象
            empty_user_info = {
                "user": user,
                "name": "",
                "email": "",
                "contact": "",
                "age": "",
                "medicalHistory": ""
            }
            return jsonify({"message": "未找到该用户的信息", "user_info": empty_user_info})

    except Exception as e:
        logging.error(f"Error in get_user_info: {e}")
        return jsonify({"message": f"获取用户信息时出错: {str(e)}"}), 500
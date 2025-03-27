from flask import Blueprint, jsonify
from .utils import users_collection, userinfo_collection
import logging

doctor_usersinfo_bp = Blueprint('doctor_usersinfo', __name__)

@doctor_usersinfo_bp.route('/api/doctor_usersinfo', methods=['GET'])
def doctor_usersinfo():
    try:
        # 查询 users 集合中 class 为 0 的所有用户
        class_0_users = users_collection.find({"class": 0})

        result = []
        for user in class_0_users:
            user_id = user.get("username")  # 假设使用 username 作为关联标识，可按需修改
            user.pop("_id", None)  # 移除 _id 字段，因为它不能直接被序列化为 JSON

            # 根据用户标识查询对应的 usersinfo 信息
            user_info = userinfo_collection.find_one({"user": user_id})
            if user_info:
                user_info.pop("_id", None)  # 移除 _id 字段，因为它不能直接被序列化为 JSON
            else:
                user_info = {}

            combined_data = {
                "user": user,
                "user_info": user_info
            }
            result.append(combined_data)

        return jsonify({"message": "成功获取 class 为 0 的用户数据", "data": result})

    except Exception as e:
        logging.error(f"Error in get_class_0_users: {e}")
        return jsonify({"message": f"获取数据时出错: {str(e)}"}), 500
    
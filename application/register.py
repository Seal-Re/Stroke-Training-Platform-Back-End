import hashlib
from flask import Blueprint, request, jsonify
from .utils import users_collection  # 假设这里已经连接好数据库并获取到用户集合

# 生成 MD5 哈希值
def md5_hash(password):
    md5 = hashlib.md5()
    md5.update(password.encode('utf-8'))
    return md5.hexdigest()

register_bp = Blueprint('register', __name__)

# 注册新用户
@register_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # 检查用户名和密码是否为空
        if not username or username == "":
            return jsonify({"success": False, "message": "Username can't be empty"})
        if not password or password == "":
            return jsonify({"success": False, "message": "Password can't be empty"})

        # 对用户输入的密码进行 MD5 加密
        hashed_password = md5_hash(password)

        # 检查用户名是否已存在
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return jsonify({"success": False, "message": "Username already exists"})

        # 插入新用户到数据库
        new_user = {
            "username": username,
            "password": hashed_password
        }
        result = users_collection.insert_one(new_user)

        if result.inserted_id:
            return jsonify({"success": True, "message": "User registered successfully"})
        else:
            return jsonify({"success": False, "message": "Error saving user"})
    except Exception as e:
        return jsonify({"success": False, "message": f"An unexpected error occurred: {str(e)}"})
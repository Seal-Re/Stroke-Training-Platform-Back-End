import hashlib
import uuid
from flask import Blueprint, request, jsonify, make_response
from .utils import users_collection

login_bp = Blueprint('login', __name__)

# 生成 MD5 哈希值
def md5_hash(password):
    md5 = hashlib.md5()
    md5.update(password.encode('utf-8'))
    return md5.hexdigest()

# 生成令牌
def generate_token():
    return str(uuid.uuid4())

# 登录
@login_bp.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            response = {
                "success": False,
                "error": "用户名和密码均为必填项"
            }
            return make_response(jsonify(response), 400)

        # 对用户输入的密码进行 MD5 加密
        hashed_password = md5_hash(password)

        # 从数据库中查找用户
        user = users_collection.find_one({"username": username, "password": hashed_password})

        if user:
            # 生成令牌
            token = generate_token()
            response = {
                "success": True,
                "token": token,
                "userInfo": {
                    "username": user["username"],
                    "class": user.get("class", 0)  # 获取用户的 class 字段，如果不存在则默认为 0
                    # 这里可以根据需要添加更多用户信息
                }
            }
            status_code = 200
        else:
            response = {
                "success": False,
                "error": "用户名或密码错误"
            }
            status_code = 401
    except Exception as err:
        response = {
            "success": False,
            "error": str(err)
        }
        status_code = 500

    return make_response(jsonify(response), status_code)
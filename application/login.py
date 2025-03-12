from flask import Blueprint, request, jsonify
from .utils import users_collection

login_bp = Blueprint('login', __name__)

# 登录
@login_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 直接从数据库中查找用户
    user = users_collection.find_one({"username": username, "password": password})

    if user:
        response = {
            "success": True,
        }
    else:
        response = {
            "success": False
        }
    return jsonify(response)
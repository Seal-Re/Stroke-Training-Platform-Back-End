from flask import Blueprint, request, jsonify
from .utils import register_user  # 引入新的注册用户函数

register_bp = Blueprint('register', __name__)

# 注册新用户
@register_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if username == '':
        return jsonify({"success": False, "message": "Username can't be empty"})
    if password == '':
        return jsonify({"success": False, "message": "Password can't be empty"})
    
    # 调用注册用户函数
    result = register_user(username, password)
    if result:
        return jsonify({"success": True, "message": "User registered successfully"})
    else:
        return jsonify({"success": False, "message": "Error saving user"})
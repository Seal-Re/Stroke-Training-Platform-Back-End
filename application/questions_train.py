from flask import Blueprint, request, jsonify
from datetime import datetime
from .utils import questions_train
import logging
import os

questions_train_bp = Blueprint('questions_train', __name__)

# 返回题目数据
@questions_train_bp.route('/api/questions_train', methods=['GET'])
def get_questions():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Missing 'username' parameter"}), 400

    user_questions = next((user for user in questions_train if user.get('username') == username), None)
    if user_questions:
        return jsonify(user_questions["questions"])
    else:
        return jsonify({"error": f"No questions found for user {username}"}), 404
    
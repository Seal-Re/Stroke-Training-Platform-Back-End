from flask import Blueprint, jsonify, request
from. import utils

questions_bp = Blueprint('questions', __name__)

# 返回题目数据
@questions_bp.route('/api/questions', methods=['GET'])
def get_questions():
    target_class = request.args.get('class')
    if not target_class:
        return jsonify({"error": "Missing 'class' parameter"}), 400

    result = []
    for item in utils.questions:
        if item.get('class') == target_class:
            content = item.get('content')
    return jsonify(content)
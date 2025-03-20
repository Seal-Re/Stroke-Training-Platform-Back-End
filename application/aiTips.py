from flask import Blueprint, jsonify
from .utils import aiTips
aiTips_bp = Blueprint('aiTips', __name__)

# 返回题目数据
@aiTips_bp.route('/api/aiTips', methods=['GET'])
def get_questions():
    return jsonify(aiTips)
from flask import Blueprint, request, jsonify
from datetime import datetime
from .utils import questions
import logging
import os
questions_bp = Blueprint('questions', __name__)

# 返回题目数据
@questions_bp.route('/api/questions', methods=['GET'])
def get_questions():
    return jsonify(questions)
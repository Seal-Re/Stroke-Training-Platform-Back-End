from flask import Blueprint, request, jsonify
from datetime import datetime
from .utils import questions_train
import logging
import os
questions_train_bp = Blueprint('questions_train', __name__)

# 返回题目数据
@questions_train_bp.route('/api/questions_train', methods=['GET'])
def get_questions():
    return jsonify(questions_train)
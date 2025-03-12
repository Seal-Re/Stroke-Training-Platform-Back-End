from flask import Blueprint, request, jsonify
import logging
from .utils import deliver_score_collection, read_mongo_data

deliverScore_bp = Blueprint('deliverScore', __name__)

# 接口：返回deliverScore数据库中的数据
@deliverScore_bp.route('/api/deliverScoreData', methods=['GET'])
def get_deliver_score_data():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Missing username parameter"}), 400

    try:
        # 直接从数据库中查找指定用户的数据
        data = deliver_score_collection.find_one({"username": username}, {"_id": 0})
        if data:
            # 提取出训练类型的数据，去掉 "username" 键
            training_data = data.copy()
            training_data.pop("username", None)
            return jsonify(training_data)
        else:
            logging.warning(f"No data found for user: {username}")
            return jsonify({})
    except Exception as e:
        logging.error(f"Error getting deliver score data: {e}")
        return jsonify({"message": f"Error getting deliver score data: {str(e)}"}), 500
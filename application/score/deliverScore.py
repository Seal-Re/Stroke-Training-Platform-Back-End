from flask import Blueprint, request, jsonify
import logging
from application.db.utils import deliver_score_collection

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
        processed_data = {}

        if data:
            # 处理 BABRI 数据
            babri_data = data.get('BABRI', [])
            if babri_data:
                processed_data['BABRI'] = babri_data[-1]['score']

            # 处理 MMSE 数据
            mmse_data = data.get('MMSE', [])
            if mmse_data:
                mmse_last_score = mmse_data[-1]['score']
                if mmse_last_score < 27:
                    if mmse_last_score >= 21:
                        mmse_status = "轻度"
                    elif mmse_last_score >= 10:
                        mmse_status = "中度"
                    else:
                        mmse_status = "重度"
                else:
                    mmse_status = "正常"
                processed_data['MMSE'] = mmse_status

            # 处理 MoCA 数据
            moca_data = data.get('MoCA', [])
            if moca_data:
                moca_last_score = moca_data[-1]['score']
                if moca_last_score < 26:
                    moca_status = "异常"
                else:
                    moca_status = "正常"
                processed_data['MoCA'] = moca_status

        return jsonify(processed_data)
    except Exception as e:
        logging.error(f"Error getting deliver score data: {e}")
        return jsonify({"message": f"Error getting deliver score data: {str(e)}"}), 500
from flask import Blueprint, request, jsonify
import logging
from .utils import deliver_score_collection, write_mongo_data

submit_bp = Blueprint('submit', __name__)


@submit_bp.route('/api/submit', methods=['POST'])
def submit_answers():
    try:
        data = request.get_json()
        logging.debug(f"Received data: {data}")
        user = data.get('user')
        table_type = data.get('table')  # 获取测试类型，如MMSE、MoCA、BABRI

        submission_data = data.get('data')[0]
        answer_records = submission_data.get('answerRecords')
        answer_results = submission_data.get('answerResults')
        score = submission_data.get('score')
        date = submission_data.get('date')

        submission = {
            "answerRecords": answer_records,
            "score": score,
            "date": date,
        }
        print(submission)
        # 保存数据到save集合
        save_data = deliver_score_collection.find_one({"username": user})
        if save_data:
            if table_type not in save_data:
                save_data[table_type] = []
            save_data[table_type].append(submission)
            deliver_score_collection.update_one({"username": user}, {"$set": save_data})
        else:
            new_save_data = {
                "username": user,
                table_type: [submission]
            }
            deliver_score_collection.insert_one(new_save_data)

        training_data = data.get('trainingData')
        training_records = []
        if training_data is not None:
            for training_type, details in training_data.items():
                total_value = sum(int(record["value"]) for record in details.get("data", []))
                record = {
                    "training_type": training_type,
                    "value": total_value,
                    "date": date
                }
                training_records.append(record)
    
        return jsonify({"message": "保存数据到MongoDB成功"})
    except Exception as e:
        logging.error(f"Error in submit_answers: {e}")
        return jsonify({"message": f"保存数据到MongoDB时出错: {str(e)}"}), 500
    
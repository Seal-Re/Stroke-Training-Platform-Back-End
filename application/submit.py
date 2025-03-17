from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
from .utils import save_collection, deliver_score_collection, write_mongo_data

submit_bp = Blueprint('submit', __name__)

# 提交
@submit_bp.route('/api/submit', methods=['POST'])
def submit_answers():
    data = request.get_json()
    logging.debug(f"Received data: {data}")
    user = data.get('user')
    submission_data = data.get('data')[0]  # 获取data数组中的第一个元素

    answerRecords = submission_data.get('answerRecords')
    answerResults = submission_data.get('answerResults')
    score = submission_data.get('score')
    # 假设前端传来的日期已经精确到秒，这里直接使用
    date = submission_data.get('date')

    # 根据分数评判认知功能
    if 270 <= score <= 300:
        cognitive_function = "正常"
    elif score < 270:
        if 210 <= score <= 260:
            cognitive_function = "轻度"
        elif 100 <= score <= 200:
            cognitive_function = "中度"
        elif 0 <= score <= 90:
            cognitive_function = "重度"
        else:
            cognitive_function = "未知"
    else:
        cognitive_function = "未知"

    # 构建要保存的单次提交数据（老数据）
    submission = {
        "answerRecords": answerRecords,
        "answerResults": answerResults,
        "score": score,
        "date": date,
        "认知功能": cognitive_function
    }

    try:
        # 保存数据到save集合
        save_data = save_collection.find_one({"username": user})
        if save_data:
            # 如果用户存在，直接在其data列表中添加新数据
            save_data['data'].append(submission)
            save_collection.update_one({"username": user}, {"$set": save_data})
        else:
            # 如果用户不存在，为该用户创建一个新的条目
            new_save_data = {
                "username": user,
                "data": [submission]
            }
            save_collection.insert_one(new_save_data)

        # 构建要保存的训练数据（新数据）
        training_data = data.get('trainingData')  # 直接从请求中获取训练数据

        deliver_score_data = deliver_score_collection.find_one({"username": user})
        if not deliver_score_data:
            deliver_score_data = {
                "username": user,
                "data": {}
            }
        deliver_score_datas = deliver_score_data.get('data', {})
        # 获取该用户所有训练类型的最大id
        max_id = 0
        for training_type in deliver_score_datas:
            for record in deliver_score_datas[training_type]:
                if record["date"][:10] == date[:10]:
                    max_id = max(int(record["id"]), max_id)
        new_id = max_id + 1
        # 这里需要确保date包含秒信息，假设前端传来的格式是'YYYY/MM/DD HH:MM:SS'
        current_date = datetime.strptime(date, '%Y/%m/%d %H:%M:%S')

        value = {
            "失算症训练": {"data": 0},
            "思维障碍训练": {"data": 0},
            "注意障碍训练": {"data": 0},
            "知觉障碍训练": {"data": 0},
            "记忆障碍训练": {"data": 0}
        }
        for training_type in training_data:
            for record in training_data[training_type]["data"]:
                value[training_type]["data"] += int(record["value"])

        for training_type in training_data:
            if training_type not in deliver_score_data['data']:
                deliver_score_data['data'][training_type] = []

            if not training_data[training_type]["data"]:
                # 若该项数据为空，则score为0，日期照常
                new_record = {
                    "id": new_id,
                    "value": "0",
                    "date": current_date.strftime('%Y/%m/%d %H:%M:%S'),
                    "认知功能": cognitive_function
                }
                deliver_score_data['data'][training_type].append(new_record)
            else:
                new_record = {
                    "id": new_id,
                    "value": str(value[training_type]["data"]),
                    "date": current_date.strftime('%Y/%m/%d %H:%M:%S'),
                    "认知功能": cognitive_function
                }
                deliver_score_data['data'][training_type].append(new_record)

        # 保存数据到deliver_score集合
        if deliver_score_collection.find_one({"username": user}):
            deliver_score_collection.update_one({"username": user}, {"$set": deliver_score_data})
        else:
            deliver_score_collection.insert_one(deliver_score_data)

        return jsonify({"message": "保存数据到MongoDB成功"})

    except Exception as e:
        logging.error(f"Error in submit_answers: {e}")
        return jsonify({"message": f"保存数据到MongoDB时出错: {str(e)}"}), 500
from flask import Blueprint, jsonify, request
import logging
from openai import OpenAI
from .utils import deliver_score_collection, read_mongo_data, aiTips_collection, deliver_score_train_collection
import json

aiapi_bp = Blueprint('aiapi', __name__)


@aiapi_bp.route('/api/AI', methods=['GET'])
def get_ai():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Missing username parameter"}), 400

    try:
        data = deliver_score_collection.find_one({"username": username}, {"_id": 0})
        if data:
            training_data = data.copy()
            training_data.pop("username", None)
        else:
            logging.warning(f"No data found for user: {username}")
            return jsonify({"message": f"No data found for user: {username}"}), 404
    except Exception as e:
        logging.error(f"Error getting deliver score data: {e}")
        return jsonify({"message": f"Error getting deliver score data: {str(e)}"}), 500

    training_data_data = training_data.get("data")
    if not training_data_data:
        logging.warning(f"No training data found for user: {username}")
        return jsonify({"message": f"No training data found for user: {username}"}), 404

    training_types = ["失算症训练", "思维障碍训练", "注意障碍训练", "知觉障碍训练", "记忆障碍训练"]

    result += "评估数据:|evaluate:"

    for training_type in training_types:
        data = training_data_data.get(training_type, [])
        pairs = []
        for item in data:
            score_rate = item.get("scoreRate", 0)
            pair = {
                "date": item.get("date"),
                "scoreRate": score_rate
            }
            pairs.append(pair)
        result += f"{training_type}"
        result += json.dumps(pairs, separators=(',', ':'), ensure_ascii=False)
        result += "|"

    result = result.rstrip("|")


    try:
        data = deliver_score_train_collection.find_one({"username": username}, {"_id": 0})
        if data:
            training_data = data.copy()
            training_data.pop("username", None)
        else:
            logging.warning(f"No data found for user: {username}")
            return jsonify({"message": f"No data found for user: {username}"}), 404
    except Exception as e:
        logging.error(f"Error getting deliver score data: {e}")
        return jsonify({"message": f"Error getting deliver score data: {str(e)}"}), 500

    training_data_data = training_data.get("data")
    if not training_data_data:
        logging.warning(f"No training data found for user: {username}")
        return jsonify({"message": f"No training data found for user: {username}"}), 404

    training_types = ["失算症训练", "思维障碍训练", "注意障碍训练", "知觉障碍训练", "记忆障碍训练"]
    result += "||训练数据:|train:"

    for training_type in training_types:
        data = training_data_data.get(training_type, [])
        pairs = []
        for item in data:
            score_rate = item.get("scoreRate", 0)
            pair = {
                "date": item.get("date"),
                "scoreRate": score_rate
            }
            pairs.append(pair)
        result += f"{training_type}"
        result += json.dumps(pairs, separators=(',', ':'), ensure_ascii=False)
        result += "|"

    result = result.rstrip("|")




    try:
        client = OpenAI(api_key="sk-9955b1dd98104518b3577a420fd3a2d2", base_url="https://api.deepseek.com")

        messages = [
            {"role": "system", "content": "You are a Chinese helpful doctor. You should speak Chinese."},
            {"role": "user", "content": "请基于以下提供的类似 json 格式数据，对我的训练情况和病情进行分析，并给出训练建议。数据涵盖 5 种训练类型，每种训练类型下有多个训练记录，每个记录包含日期和得分率。请先分别评价训练数据和评估数据，再进行综合统筹，给出全面合理的建议 。"}
        ]

        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            stream=False
        )

        messages.append({"role": "assistant", "content": response.choices[0].message.content})
        messages.append({"role": "user", "content": "What is the second?"})
        user_record = aiTips_collection.find_one({"username": username})
        if user_record and "data" in user_record and user_record["data"]:
            last_ai_tip = user_record["data"][-1]["ai_tips"]
            messages.append({"role": "assistant", "content": f"这是上一次你给的建议：{last_ai_tip}"})
    
        messages.append({"role": "user", "content": result})

        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            stream=False
        )

        new_data = {
            "training_data": result,
            "ai_tips": response.choices[0].message.content
        }

        user_aiTips = aiTips_collection.find_one({"username": username})
        if user_aiTips and "data" in user_aiTips:
            data_list = user_aiTips["data"]
            new_id = len(data_list) + 1
            new_data["id"] = new_id
            data_list.append(new_data)
            aiTips_collection.update_one({"username": username}, {"$set": {"data": data_list}})
        else:
            new_data["id"] = 1
            aiTips_collection.insert_one({"username": username, "data": [new_data]})

        return jsonify({"message": response.choices[0].message.content})

    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return jsonify({"message": f"Error calling OpenAI API: {str(e)}"}), 500
from flask import Blueprint, jsonify, request
import logging
from openai import OpenAI
from application.db.utils import aiTips_collection, deliver_score_train_collection
import json
from .AIBase import api_key, base_url

aiapi_bp = Blueprint('aiapi', __name__)


@aiapi_bp.route('/api/AI', methods=['GET'])
def get_ai():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Missing username parameter"}), 400

    result = ""

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

    training_types = [
        "MMSE定向力训练",
        "MMSE记忆力训练",
        "MMSE注意力及计算力训练",
        "MMSE回忆能力训练",
        "MMSE语言能力训练",
        "MMSE执行能力训练",
        "MMSE常识认知训练"
    ]
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
        client = OpenAI(api_key=api_key, base_url=base_url)

        # 系统提示，明确 AI 的角色和回答要求
        messages = [
            {
                "role": "system",
                "content": "你是一位和蔼可亲的中国医生，仅围绕用户提供的训练数据和病情相关内容进行分析，给出各个模块的评估分析和合理的训练建议。请避免引入无关的概念，如量子等。回答以病人为对象，避免引入过于高深的概念。回答使用中文。回答时，保证回答的格式和上一次相近"
            }
        ]

        # 询问 AI 对训练数据和病情进行分析的请求
        analysis_request = (
            "请基于以下提供的类似 JSON 格式数据，对我的训练情况和病情进行分析，并给出训练建议。"
            "数据涵盖 7 种训练类型，每种训练类型下有多个训练记录，每个记录包含日期和得分率。"
            "请先分别评价训练数据和评估数据，再进行综合统筹，给出全面合理的建议。"
        )
        messages.append({"role": "user", "content": analysis_request})

        user_record = aiTips_collection.find_one({"username": username})
        if user_record and "data" in user_record and user_record["data"]:
            # 获取上一次的建议
            last_ai_tip = user_record["data"][-1]["ai_tips"]
            # 告知 AI 上一次的建议，让其在此基础上进行分析
            previous_tip_message = f"这是上一次你给出的建议：{last_ai_tip}。请结合此次新数据继续分析。"
            messages.append({"role": "assistant", "content": previous_tip_message})

        # 提供最新的训练数据
        messages.append({"role": "user", "content": result})

        response = client.chat.completions.create(
            model="deepseek-chat",
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
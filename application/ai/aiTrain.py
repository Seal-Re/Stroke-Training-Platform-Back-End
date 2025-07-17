from flask import Blueprint, jsonify, request
from application.db.utils import aiTips, questions_train_collection
from .AIBase import api_key, base_url
import logging
from openai import OpenAI
import json

aiTrain_bp = Blueprint('aiTrain', __name__)


@aiTrain_bp.route('/api/aiTrain', methods=['GET'])
def get_questions():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Missing 'username' parameter"}), 400
    user_tips = [tip for tip in aiTips if tip.get('username') == username]
    if not user_tips:
        return jsonify({"error": f"No tips found for user {username}"}), 404
    latest_tip = max(user_tips, key=lambda x: x.get('id', 0))

    ai_tips = latest_tip['data'][0]['ai_tips']

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        system_prompt = f"""
你是一位专业的中国医生，需要根据以下分析结果 {ai_tips} 生成具有针对性的训练题目,帮助患者恢复。题目仅包含选择题和填空题，选择题的 model 为 "0"，填空题的 model 为 "1"。请按照以下 JSON 数组格式输出 20 道题目数据，同时为每道题目添加 'difficulty' 字段，难度分为 '简单'、'中等'、'困难'：
[
    {{
        "question": "题目内容",
        "options": ["选项 A", "选项 B", "选项 C", "选项 D"],
        "answer": "答案",
        "score": 10,
        "class": "MMSE定向力训练|MMSE记忆力训练|MMSE注意力及计算力训练|MMSE回忆能力训练|MMSE语言能力训练|MMSE执行能力训练|MMSE常识认知训练",
        "model": "0|1",
        "difficulty": "简单|中等|困难"
    }},
    // 其他题目依此类推
]
请输出合法的 JSON 格式，确保符合上述结构，涵盖 MMSE定向力训练、MMSE记忆力训练、MMSE注意力及计算力训练、MMSE回忆能力训练、MMSE语言能力训练、MMSE执行能力训练、MMSE常识认知训练七个方向，题目比例根据上述分析结果进行调整，难度分布也应合理。在题目中避免使用图片。避免引入无关的概念，回答使用中文。
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请按照上述要求生成题目。"}
        ]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
            response_format={'type': 'json_object'},
            max_tokens=4096
        )

        if not response.choices[0].message.content:
            logging.error("API returned empty content.")
            return jsonify({"message": "API returned empty content."}), 500

        try:
            question_data = json.loads(response.choices[0].message.content)
            logging.debug(f"Generated question count: {len(question_data)}")

            existing_doc = questions_train_collection.find_one({"username": username})
            if existing_doc:
                existing_questions = existing_doc.get("questions", [])
                new_questions = existing_questions + question_data
                questions_train_collection.update_one(
                    {"username": username},
                    {"$set": {"questions": new_questions}}
                )
            else:
                questions_train_collection.insert_one({
                    "username": username,
                    "questions": question_data
                })

            return jsonify({"message": question_data})

        except json.JSONDecodeError:
            logging.error("Failed to parse AI response as JSON.")
            return jsonify({"message": "Failed to parse AI response as JSON."}), 500

    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return jsonify({"message": f"Error calling OpenAI API: {str(e)}"}), 500
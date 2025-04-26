from flask import Blueprint, jsonify
from .utils import aiTips, aiTips_collection
aiTips_bp = Blueprint('aiTips', __name__)
from flask import request

# 返回ai提示数据
@aiTips_bp.route('/api/aiTips', methods=['GET'])
def get_questions():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "缺少用户名参数"}), 400

    # 遍历查找用户的提示数据
    for item in aiTips:
        if item.get("username") == username:
            return jsonify({
                "username": username,
                "data": item.get("data", []),
                "found": True  # 用户找到数据，标志位为 True
            }), 200

    # 如果没有找到用户的提示数据，返回 found 为 False
    return jsonify({
        "error": f"未找到用户名为 {username} 的提示数据",
        "found": False  # 没有找到数据，标志位为 False
    }), 200

@aiTips_bp.route('/api/ai_doctor_tips', methods=['POST'])
def post_doctor_tips():
    data = request.get_json()
    username = data.get('username')
    new_tip = data.get('aiTip')

    if not username or not new_tip:
        return jsonify({"error": "缺少参数 username 或 aiTip"}), 400

    # 查询用户记录
    user_record = aiTips_collection.find_one({"username": username})

    if user_record:
        # 如果存在，添加到 data 列表里
        tip_list = user_record.get("data", [])
        new_id = len(tip_list) + 1
        tip_list.append({
            "id": new_id,
            "ai_tips": new_tip,
            "edited": True
        })
        aiTips_collection.update_one(
            {"username": username},
            {"$set": {"data": tip_list}}
        )
        return jsonify({"message": "AI 建议已成功更新"}), 200
    else:
        # 不存在，新增一条记录
        new_record = {
            "username": username,
            "data": [{
                "id": 1,
                "ai_tips": new_tip,
                "edited": True
            }]
        }
        aiTips_collection.insert_one(new_record)
        return jsonify({"message": "AI 建议已成功创建新用户记录"}), 201

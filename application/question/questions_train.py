import random
import logging
from flask import Blueprint, request, jsonify
from application.db.utils import questions_train, deliver_score_train_collection, memory, attention, Recollection, \
    language, ExecutiveCapacity, directiveForce, CommonSense

questions_train_bp = Blueprint('questions_train', __name__)


# 返回题目数据
@questions_train_bp.route('/api/questions_train', methods=['GET'])
def get_questions():
    total_questions = 35  # 题目数量
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Missing 'username' parameter"}), 400
    try:
        data = deliver_score_train_collection.find_one({"username": username})
        if data and data["data"] != {'MMSE定向力训练': [], 'MMSE记忆力训练': [], 'MMSE注意力及计算力训练': [],
                                     'MMSE回忆能力训练': [], 'MMSE语言能力训练': [], 'MMSE执行能力训练': [],
                                     'MMSE常识认知训练': []}:
            value = [0, 0, 0, 0, 0, 0, 0]
            total = 0
            # 修改：添加类型检查和错误处理
            mmse_categories = [
                'MMSE定向力训练', 'MMSE记忆力训练', 'MMSE注意力及计算力训练',
                'MMSE回忆能力训练', 'MMSE语言能力训练', 'MMSE执行能力训练', 'MMSE常识认知训练'
            ]
            for i, category in enumerate(mmse_categories):
                if category in data["data"] and data["data"][category]:
                    try:
                        # 确保value可以转换为整数
                        value[i] = int(data["data"][category][-1]["value"])
                    except (ValueError, TypeError):
                        # 处理无法转换的情况，默认设为0
                        value[i] = 0
                    total += value[i]
                else:
                    value[i] = 0

            levels = []
            for i in range(7):
                if value[i] < 3:  # 正确率<60%
                    levels.append('weak')
                elif value[i] < 5:  # 60%<=正确率<100%
                    levels.append('medium')
                else:  # 正确率100%
                    levels.append('strong')
            second_attempt = []
            for level in levels:
                if level == 'weak':
                    second_attempt.append(8)  # 薄弱题型基础分配8题
                elif level == 'medium':
                    second_attempt.append(6)  # 中等题型基础分配6题
                else:
                    second_attempt.append(2)  # 优势题型基础分配2题

            current_total = sum(second_attempt)
            difference = total_questions - current_total

            # 调整题数以满足总题数要求
            if difference != 0:
                # 创建题型索引列表，按优先级排序（薄弱优先，中等其次，优势最后）
                priority_indices = []
                for i, level in enumerate(levels):
                    if level == 'weak':
                        priority_indices.append(i)
                for i, level in enumerate(levels):
                    if level == 'medium':
                        priority_indices.append(i)
                for i, level in enumerate(levels):
                    if level == 'strong':
                        priority_indices.append(i)

                if difference > 0:
                    # 总题数不足，按优先级增加题目
                    for _ in range(difference):
                        if not priority_indices:
                            break  # 没有可增加的题型
                        # 循环使用优先级列表
                        index = priority_indices[_ % len(priority_indices)]
                        second_attempt[index] += 1
                else:
                    # 总题数过多，按优先级减少题目
                    for _ in range(abs(difference)):
                        if not priority_indices:
                            break  # 没有可减少的题型
                        # 从后往前循环使用优先级列表（优先减少优势题型）
                        index = priority_indices[-((_ % len(priority_indices)) + 1)]
                        if second_attempt[index] > 0:  # 确保不减少到负数
                            second_attempt[index] -= 1

        else:
            data = {
                "MMSE定向力训练": [],
                "MMSE记忆力训练": [],
                "MMSE注意力及计算力训练": [],
                "MMSE回忆能力训练": [],
                "MMSE语言能力训练": [],
                "MMSE执行能力训练": [],
                "MMSE常识认知训练": [],
            }
            # 将 username 和 data 合并为一个文档
            document = {"username": username, "data": data}
            # 使用 insert_one 插入新文档
            deliver_score_train_collection.insert_one(document)
            # 平均分配题目，确保总和为35
            m = total_questions // 7  # 使用整除
            remainder = total_questions % 7
            second_attempt = [m] * 7
            # 将余数均匀分配到前几个题型
            for i in range(remainder):
                second_attempt[i] += 1

        collections = [memory, attention, Recollection, directiveForce, language, ExecutiveCapacity, CommonSense]
        all_questions = []

        # 记录每个集合实际选取的题目数量
        actual_counts = []

        for idx, count in enumerate(second_attempt):
            count = int(count)  # 确保题目数量为整数
            all_docs = list(collections[idx].find())
            all_inner_questions = []
            for doc in all_docs:
                if 'questions' in doc and 'questions' in doc['questions']:
                    all_inner_questions.extend(doc['questions']['questions'])

            # 确保count不会大于题目总数，并且不为负数
            safe_count = min(count, len(all_inner_questions))
            safe_count = max(0, safe_count)
            actual_counts.append(safe_count)

            # 随机选取指定数量的题目
            if safe_count > 0:
                if len(all_inner_questions) >= safe_count:
                    selected_questions = random.sample(all_inner_questions, safe_count)
                else:
                    selected_questions = all_inner_questions
                all_questions.extend(selected_questions)

        # 如果最终题目数量不足，尝试从其他集合补充
        total_selected = sum(actual_counts)
        if total_selected < total_questions:
            needed = total_questions - total_selected
            logging.warning(f"题目数量不足: 需要 {total_questions} 题，但只找到了 {total_selected} 题，尝试补充")

            # 尝试从其他集合补充题目
            for idx, count in enumerate(second_attempt):
                if needed <= 0:
                    break

                all_docs = list(collections[idx].find())
                all_inner_questions = []
                for doc in all_docs:
                    if 'questions' in doc and 'questions' in doc['questions']:
                        all_inner_questions.extend(doc['questions']['questions'])

                # 已经选取的题目
                already_selected = actual_counts[idx]
                # 还可以选取的题目数量
                available = len(all_inner_questions) - already_selected

                if available > 0:
                    # 可以补充的数量
                    to_add = min(available, needed)

                    # 排除已经选取的题目
                    if already_selected > 0:
                        # 假设题目有唯一标识id，需要根据实际情况调整
                        selected_ids = set(q.get('id', '') for q in all_questions if idx == 0 or 'id' in q)
                        remaining_questions = [q for q in all_inner_questions if q.get('id', '') not in selected_ids]
                    else:
                        remaining_questions = all_inner_questions

                    # 随机选取补充题目
                    if remaining_questions and to_add > 0:
                        if len(remaining_questions) >= to_add:
                            more_questions = random.sample(remaining_questions, to_add)
                        else:
                            more_questions = remaining_questions
                        all_questions.extend(more_questions)
                        needed -= len(more_questions)
                        actual_counts[idx] += len(more_questions)

        # 如果补充后题目数量仍然不足，截断到35题
        if len(all_questions) > total_questions:
            all_questions = all_questions[:total_questions]
        elif len(all_questions) < total_questions:
            logging.warning(f"最终题目数量仍不足: 需要 {total_questions} 题，但只找到了 {len(all_questions)} 题")

        random.shuffle(all_questions)
        return jsonify({"questions": all_questions, "count": len(all_questions)}), 200
    except KeyError as e:
        logging.error(f"KeyError: {str(e)}")
        return jsonify({"error": "Invalid data format"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Error fetching questions: {str(e)}"}), 500
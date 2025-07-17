from flask import Blueprint, jsonify, request 
import threading 
import time 
import uuid 
from datetime import datetime 
import logging 

# 创建一个蓝图实例，用于组织 ASR 相关的路由 
asr_bp = Blueprint('asr', __name__) 

# --- 修改开始 ---
# 获取名为 'ASR_Server' 的 logger 实例
logger = logging.getLogger('ASR_Server') 
# 设置 ASR_Server logger 的日志级别为 INFO
logger.setLevel(logging.INFO) 

# 确保 logger 有一个处理器（handler），这样日志才能被输出到控制台
# 只有当 logger 没有处理器时才添加，避免重复添加
if not logger.handlers:
    handler = logging.StreamHandler()
    # 定义日志格式，包括级别、logger名称和消息
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
# --- 修改结束 ---

# 导入 RealTimeASR 类，假设它在 rtasr_p 模块中 
# 请确保 rtasr_p.py 文件在可访问的路径中 
from application.TTS.rtasr_p import RealTimeASR

# 会话管理：存储活跃的 ASR 会话实例 
sessions = {} 
# 会话锁：用于保护 sessions 字典在多线程环境下的并发访问 
sessions_lock = threading.Lock() 
# 会话超时时间，单位秒 (5分钟) 
SESSION_TIMEOUT = 300  

# 连接池管理：控制最大并发连接数 
# 讯飞免费版通常允许5路并发，这里设置最大并发连接数 
MAX_CONCURRENT_CONNECTIONS = 5  
# 连接信号量：用于限制并发 ASR 实例的数量 
connection_semaphore = threading.Semaphore(MAX_CONCURRENT_CONNECTIONS) 

def clean_expired_sessions(): 
    """ 
    清理过期会话的函数。 
    遍历所有会话，如果会话的最后活动时间超过预设的超时时间，则将其清理。 
    清理包括停止 ASR 实例并从 sessions 字典中移除。 
    """ 
    current_time = time.time() 
    with sessions_lock: 
        # 找出所有已过期的会话ID 
        expired_sessions = [ 
            session_id for session_id, session_data in sessions.items() 
            if current_time - session_data['last_activity'] > SESSION_TIMEOUT 
        ] 
        
        # 遍历并清理过期会话 
        for session_id in expired_sessions: 
            session = sessions.pop(session_id) 
            # 如果 ASR 实例仍在运行，则停止它 
            if session['asr_instance'].is_running: 
                session['asr_instance'].stop() 
            logger.info(f"清理过期会话: {session_id}") 

def session_cleaner(): 
    """ 
    后台会话清理线程的入口函数。 
    每隔60秒调用一次 clean_expired_sessions 函数。 
    """ 
    while True: 
        time.sleep(60) # 每分钟检查一次 
        clean_expired_sessions() 

# 启动后台清理线程 
# daemon=True 使得该线程在主程序退出时自动终止 
cleaner_thread = threading.Thread(target=session_cleaner, daemon=True) 
cleaner_thread.start() 

@asr_bp.route('/asr/start', methods=['POST']) 
def start_asr(): 
    """ 
    启动语音识别端点。 
    接收 POST 请求，尝试获取一个连接许可，然后创建一个 RealTimeASR 实例并启动它。 
    成功启动后，生成一个会话ID并存储会话信息。 
    """ 
    # 尝试获取连接许可，如果达到最大连接数则立即返回 429 错误 
    if not connection_semaphore.acquire(blocking=False): 
        return jsonify({ 
            "status": "error", 
            "message": "已达到最大并发连接数，请稍后再试" 
        }), 429 
    
    # 尝试解析 JSON 请求体，如果不是 JSON 或为空，则默认为空字典 
    data = request.get_json(silent=True) or {} 
    
    # 获取超时时间，默认为30秒 
    timeout = data.get('timeout', 30) 
    
    # 创建 RealTimeASR 实例 
    asr_instance = RealTimeASR() 
    asr_instance.timeout_seconds = timeout 
    
    # 启动 ASR 识别 
    success = asr_instance.start() 
    
    # 如果 ASR 启动失败，释放连接许可并返回错误 
    if not success: 
        connection_semaphore.release()  # 释放信号量 
        return jsonify({ 
            "status": "error", 
            "message": "启动语音识别失败" 
        }), 500 
    
    # 生成唯一会话ID 
    session_id = str(uuid.uuid4()) 
    
    # 存储会话信息，包括 ASR 实例、创建时间、最后活动时间 
    with sessions_lock: 
        sessions[session_id] = { 
            'asr_instance': asr_instance, 
            'created_at': time.time(), 
            'last_activity': time.time() 
        } 
    
    logger.info(f"新会话启动: {session_id}") 
    
    # 返回成功响应，包含会话ID和超时时间 
    return jsonify({ 
        "status": "success", 
        "message": "语音识别已启动", 
        "session_id": session_id, 
        "timeout": timeout 
    }) 

@asr_bp.route('/asr/stop', methods=['POST']) 
def stop_asr(): 
    """ 
    结束语音识别并获取所有结果（包括中间结果和最终结果）的端点。 
    接收 POST 请求，根据 session_id 停止对应的 ASR 实例，获取识别结果， 
    并释放连接许可。 
    """ 
    # 尝试解析 JSON 请求体 
    data = request.get_json(silent=True) or {} 
    session_id = data.get('session_id') 
    
    # 检查是否提供了 session_id 
    if not session_id: 
        return jsonify({ 
            "status": "error", 
            "message": "缺少session_id参数" 
        }), 400 
    
    with sessions_lock: 
        # 获取会话 
        session = sessions.get(session_id) 
        if not session: 
            return jsonify({ 
                "status": "error", 
                "message": "无效的session_id" 
            }), 404 
        
        # 更新会话的最后活动时间 
        session['last_activity'] = time.time() 
        asr_instance = session['asr_instance'] 
        
        # 如果 ASR 实例未运行，则返回错误并确保释放信号量 
        if not asr_instance.is_running: 
            connection_semaphore.release()  # 确保释放信号量 
            return jsonify({ 
                "status": "error", 
                "message": "语音识别未运行或已停止" 
            }), 400 
        
        # 停止 ASR 实例并获取所有结果 
        result = asr_instance.stop() 
        
        # 从会话字典中移除已停止的会话 
        if session_id in sessions: 
            del sessions[session_id] 
        
        # 释放连接许可 
        connection_semaphore.release() 
        
        # 根据识别结果返回不同的响应 
        if result: 
            final_text = result.get('final_result', '') 
            intermediate_results = result.get('intermediate_results', []) 
            
            # --- 获取并组合所有中间结果的文本，并输出到日志 ---
            # 即使 intermediate_results 为空，这里也不会报错，combined_log_text 会是空字符串
            combined_log_text = "".join([item['text'] for item in intermediate_results])
            logger.info(f"会话 {session_id} 的所有原始中间结果组合文本: {combined_log_text}")
            # --- 结束 ---

            logger.info(f"会话结束: {session_id} - 最终结果长度: {len(final_text)}, 中间结果数量: {len(intermediate_results)}") 
            return jsonify({ 
                "status": "success", 
                "message": "语音识别已停止，并返回所有结果", 
                "final_result": final_text, 
                "intermediate_results": intermediate_results # 返回所有中间结果 
            }) 
        else: 
            return jsonify({ 
                "status": "error", 
                "message": "获取结果失败" 
            }), 500 

@asr_bp.route('/asr/get_current_transcription', methods=['GET']) 
def get_current_transcription(): 
    """ 
    获取当前会话的实时识别文本（包括中间结果）的端点。 
    客户端可以周期性地调用此端点来获取 ASR 进度。 
    """ 
    session_id = request.args.get('session_id') # 使用 GET 请求的查询参数 
    
    if not session_id: 
        return jsonify({ 
            "status": "error", 
            "message": "缺少session_id参数" 
        }), 400 
    
    with sessions_lock: 
        session = sessions.get(session_id) 
        if not session: 
            return jsonify({ 
                "status": "error", 
                "message": "无效的session_id" 
            }), 404 
        
        session['last_activity'] = time.time() 
        asr_instance = session['asr_instance'] 
        
        if not asr_instance.is_running: 
            return jsonify({ 
                "status": "idle", 
                "message": "语音识别未运行或已停止", 
                "current_transcription": "" # 如果未运行，返回空字符串 
            }) 
        
        # 调用 RealTimeASR 实例的 get_current_transcription() 方法 
        current_text = asr_instance.get_current_transcription()  
        
        return jsonify({ 
            "status": "running", 
            "message": "正在获取实时识别文本", 
            "session_id": session_id, 
            "current_transcription": current_text 
        }) 


@asr_bp.route('/asr/status', methods=['POST']) 
def get_status(): 
    """ 
    获取当前语音识别状态的端点。 
    接收 POST 请求，根据 session_id 返回对应 ASR 实例的运行状态。 
    """ 
    # 尝试解析 JSON 请求体 
    data = request.get_json(silent=True) or {} 
    session_id = data.get('session_id') 
    
    if not session_id: 
        return jsonify({ 
            "status": "error", 
            "message": "缺少session_id参数" 
        }), 400 
    
    with sessions_lock: 
        session = sessions.get(session_id) 
        if not session: 
            return jsonify({ 
                "status": "error", 
                "message": "无效的session_id" 
            }), 404 
        
        session['last_activity'] = time.time() 
        asr_instance = session['asr_instance'] 
        
        # 根据 ASR 实例的运行状态返回不同的响应 
        if asr_instance.is_running: 
            return jsonify({ 
                "status": "running", 
                "message": "语音识别正在进行中", 
                "elapsed_time": time.time() - asr_instance.start_time, # 识别已进行时间 
                "last_activity": time.time() - asr_instance.last_audio_time, # 最后音频活动时间 
                "session_id": session_id 
            }) 
        else: 
            return jsonify({ 
                "status": "idle", 
                "message": "语音识别已停止", 
                "session_id": session_id 
            }) 

@asr_bp.route('/asr/active_sessions', methods=['GET']) 
def get_active_sessions(): 
    """ 
    获取所有活跃会话列表的端点。 
    返回当前所有正在运行或未超时的 ASR 会话信息。 
    """ 
    with sessions_lock: 
        # 遍历所有会话，构建活跃会话列表 
        active_sessions = [ 
            { 
                "session_id": session_id, 
                "created_at": datetime.fromtimestamp(session['created_at']).strftime('%Y-%m-%d %H:%M:%S'), 
                "last_activity": datetime.fromtimestamp(session['last_activity']).strftime('%Y-%m-%d %H:%M:%S'), 
                "status": "running" if session['asr_instance'].is_running else "idle" 
            } 
            for session_id, session in sessions.items() 
        ] 
        
        # 返回活跃会话的数量和详细信息 
        return jsonify({ 
            "status": "success", 
            "active_sessions_count": len(active_sessions), 
            "active_sessions": active_sessions 
        }) 

@asr_bp.route('/asr/connection_status', methods=['GET']) 
def connection_status(): 
    """ 
    获取连接池状态的端点。 
    返回最大并发连接数、可用连接数以及当前活跃会话数。 
    """ 
    return jsonify({ 
        "status": "success", 
        "max_connections": MAX_CONCURRENT_CONNECTIONS, 
        "available_connections": connection_semaphore._value, # _value 是信号量内部的计数器 
        "active_sessions": len(sessions) 
    })
import threading
import time
import uuid
import logging
import io # 用于处理二进制音频数据

# 假设 RealTimeWhisperASR 定义在 application/ten.py 中
# 如果你的 ten.py 在其他位置，请调整导入路径
from .ten import RealTimeWhisperASR 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Whisper_ASR_Service')

class ASRService:
    """
    封装语音识别会话管理逻辑的服务类 (离线模式)。
    在离线模式下，音频数据先被收集，然后在会话结束时一次性进行识别。
    """
    def __init__(self):
        self.sessions = {}
        self.sessions_lock = threading.Lock()
        self.connection_semaphore = threading.Semaphore(10)  # 最大并发连接数 (用于会话创建)
        self.session_timeout = 300  # 5分钟会话超时
        self.logger = logger # 使用外部定义的logger

        # 启动后台会话清理线程
        self._cleaner_thread = threading.Thread(target=self._session_cleaner, daemon=True)
        self._cleaner_thread.start()
        self.logger.info("ASRService 会话清理线程已启动 (离线模式)")

    def _session_cleaner(self):
        """后台清理线程，定期清理过期会话"""
        while True:
            time.sleep(60) # 每分钟检查一次
            self.clean_expired_sessions()

    def start_new_session(self, model_size='base'):
        """
        启动一个新的ASR会话，仅用于开始收集音频数据。
        不在此处启动语音识别实例。
        """
        if not self.connection_semaphore.acquire(blocking=False):
            self.logger.warning("已达到最大并发连接数，无法启动新会话。")
            return None, "已达到最大并发连接数，请稍后再试"

        session_id = str(uuid.uuid4())
        with self.sessions_lock:
            self.sessions[session_id] = {
                'audio_chunks': [], # 用于存储接收到的音频数据块
                'created_at': time.time(),
                'last_activity': time.time(),
                'model_size': model_size,
                'status': 'collecting' # 新增状态，表示正在收集音频
            }
        self.logger.info(f"新会话启动 (收集模式): {session_id} (模型: {model_size})")
        return session_id, None

    def get_session(self, session_id):
        """获取指定session_id的会话数据，并更新活动时间"""
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            if session:
                session['last_activity'] = time.time()
            return session

    def push_audio_data(self, session_id, audio_data):
        """
        向指定会话推送音频数据。
        在离线模式下，音频数据被追加到内存中的列表中。
        """
        session = self.get_session(session_id)
        if not session:
            return False, "无效的session_id或会话已过期"
        
        if session['status'] != 'collecting':
            return False, "会话状态不正确，无法推送音频"

        session['audio_chunks'].append(audio_data)
        self.logger.debug(f"会话 {session_id} 接收到 {len(audio_data)} 字节音频数据。")
        return True, None

    def get_partial_results(self, session_id):
        """
        在离线模式下，此方法不返回实时结果。
        可以返回一个空列表或表示当前状态的信息。
        """
        session = self.get_session(session_id)
        if not session:
            return []
        # 离线模式下没有实时结果，可以返回空列表
        return [] 

    def stop_session(self, session_id):
        """
        停止指定会话，并对收集到的所有音频数据进行一次性识别。
        """
        with self.sessions_lock:
            session = self.sessions.pop(session_id, None) # 从字典中移除会话
            if not session:
                return None, "无效的session_id或会话已过期"
            
            session['status'] = 'processing' # 更新状态为正在处理

        self.logger.info(f"会话停止: {session_id} - 开始离线识别...")

        try:
            # 合并所有音频数据块
            full_audio_data = b''.join(session['audio_chunks'])
            
            if not full_audio_data:
                self.logger.warning(f"会话 {session_id} 没有收集到音频数据。")
                self.connection_semaphore.release() # 释放连接许可
                return {"final_result": ["没有检测到语音"]}, None

            # 实例化 RealTimeWhisperASR 并进行一次性识别
            # 注意：RealTimeWhisperASR 需要能够处理完整的音频数据
            # 这里假设 RealTimeWhisperASR.process_audio() 方法可以接受完整的二进制数据
            # 如果 RealTimeWhisperASR 只有流式接口，你可能需要修改 RealTimeWhisperASR 或使用其他库
            asr_instance = RealTimeWhisperASR(model_size=session['model_size'])
            
            # 假设 RealTimeWhisperASR 有一个用于离线处理的方法
            # 如果没有，你可能需要修改 RealTimeWhisperASR 或模拟其行为
            # 这里的实现取决于 RealTimeWhisperASR 的具体能力
            
            # 模拟离线处理：启动 -> 推送所有数据 -> 停止
            asr_instance.start() # 启动 ASR 实例
            asr_instance.push_audio(full_audio_data) # 推送所有音频数据
            final_result = asr_instance.stop() # 停止并获取最终结果

            self.logger.info(f"会话 {session_id} 离线识别完成。")
            return final_result, None

        except Exception as e:
            self.logger.error(f"会话 {session_id} 离线识别失败: {e}", exc_info=True)
            return None, f"离线识别失败: {str(e)}"
        finally:
            self.connection_semaphore.release() # 无论成功失败，都释放连接许可

    def clean_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        with self.sessions_lock:
            expired_session_ids = [
                session_id for session_id, session_data in self.sessions.items()
                if current_time - session_data['last_activity'] > self.session_timeout
            ]

            for session_id in expired_session_ids:
                session = self.sessions.pop(session_id)
                self.logger.info(f"清理过期会话 (收集模式): {session_id}")
                # 在离线模式下，如果会话过期，我们直接清理，不进行识别
                # 如果需要，可以在这里添加逻辑来处理未完成的识别
                self.connection_semaphore.release() # 释放连接许可

    def get_active_sessions_list(self):
        """获取活跃会话列表（离线模式下显示正在收集的会话）"""
        with self.sessions_lock:
            active_sessions = [
                {
                    "session_id": session_id,
                    "model_size": session['model_size'],
                    "created_at": session['created_at'],
                    "last_activity": session['last_activity'],
                    "status": session['status']
                }
                for session_id, session in self.sessions.items()
            ]
            return {
                "status": "success",
                "active_sessions": active_sessions,
                "count": len(active_sessions)
            }, 200


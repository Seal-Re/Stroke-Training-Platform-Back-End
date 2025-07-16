import threading
import time
import uuid
import logging

from ten import RealTimeWhisperASR 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Whisper_ASR_Service')

class ASRService:
    """
    封装语音识别会话管理逻辑的服务类。
    """
    def __init__(self):
        self.sessions = {}
        self.sessions_lock = threading.Lock()
        self.connection_semaphore = threading.Semaphore(10)  # 最大并发连接数
        self.session_timeout = 300  # 5分钟会话超时
        self.logger = logger # 使用外部定义的logger

        # 启动后台会话清理线程
        self._cleaner_thread = threading.Thread(target=self._session_cleaner, daemon=True)
        self._cleaner_thread.start()
        self.logger.info("ASRService 会话清理线程已启动")

    def _session_cleaner(self):
        """后台清理线程，定期清理过期会话"""
        while True:
            time.sleep(60) # 每分钟检查一次
            self.clean_expired_sessions()

    def start_new_session(self, model_size='base'):
        """启动一个新的ASR会话并返回session_id"""
        if not self.connection_semaphore.acquire(blocking=False):
            self.logger.warning("已达到最大并发连接数，无法启动新会话。")
            return None, "已达到最大并发连接数，请稍后再试"

        try:
            asr_instance = RealTimeWhisperASR(model_size=model_size)
            success = asr_instance.start()
            if not success:
                self.connection_semaphore.release()
                self.logger.error("启动语音识别实例失败。")
                return None, "启动语音识别失败"

            session_id = str(uuid.uuid4())
            with self.sessions_lock:
                self.sessions[session_id] = {
                    'asr_instance': asr_instance,
                    'created_at': time.time(),
                    'last_activity': time.time(),
                    'model_size': model_size
                }
            self.logger.info(f"新会话启动: {session_id} (模型: {model_size})")
            return session_id, None
        except Exception as e:
            self.logger.error(f"启动ASR会话异常: {e}", exc_info=True)
            self.connection_semaphore.release() # 确保在异常时也释放信号量
            return None, f"启动ASR会话时发生错误: {str(e)}"


    def get_session(self, session_id):
        """获取指定session_id的会话数据，并更新活动时间"""
        with self.sessions_lock:
            session = self.sessions.get(session_id)
            if session:
                session['last_activity'] = time.time()
            return session

    def push_audio_data(self, session_id, audio_data):
        """向指定会话推送音频数据"""
        session = self.get_session(session_id)
        if not session:
            return False, "无效的session_id或会话已过期"

        asr_instance = session['asr_instance']
        if not asr_instance.is_running:
            return False, "语音识别未运行或已停止"

        asr_success = asr_instance.push_audio(audio_data)
        if not asr_success:
            return False, "推送音频数据失败"
        return True, None

    def get_partial_results(self, session_id):
        """获取指定会话的实时识别结果"""
        session = self.get_session(session_id)
        if not session:
            return []

        asr_instance = session['asr_instance']
        return asr_instance.get_partial_results() if asr_instance.is_running else []

    def stop_session(self, session_id):
        """停止指定会话并返回最终结果"""
        with self.sessions_lock:
            session = self.sessions.pop(session_id, None)
            if not session:
                return None, "无效的session_id或会话已过期"

            asr_instance = session['asr_instance']
            result = None
            if asr_instance.is_running:
                result = asr_instance.stop()
                self.logger.info(f"会话停止: {session_id} - 识别结果: {len(result['final_result'])}条")
            else:
                self.logger.warning(f"尝试停止已停止的会话: {session_id}")

            self.connection_semaphore.release() # 释放连接许可
            return result, None

    def clean_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        with self.sessions_lock:
            expired_sessions = [
                session_id for session_id, session_data in self.sessions.items()
                if current_time - session_data['last_activity'] > self.session_timeout
            ]

            for session_id in expired_sessions:
                session = self.sessions.pop(session_id)
                if session['asr_instance'].is_running:
                    self.logger.info(f"停止过期会话: {session_id}")
                    session['asr_instance'].stop()
                self.logger.info(f"清理过期会话: {session_id}")
                self.connection_semaphore.release() # 释放连接许可
import time
import numpy as np
from datetime import datetime
import logging
import whisper
from pydub import AudioSegment
import io
import threading
import torch

class RealTimeWhisperASR:
    def __init__(self, model_size="base", device=None):
        self.is_running = False
        self.start_time = None
        self.last_audio_time = None
        self.final_result = []
        self.partial_results = []
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.model_size = model_size
        
        # 自动选择设备
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        self.model = None
        self.sample_rate = 16000
        self.chunk_size = int(self.sample_rate * 0.5)  # 0.5秒的音频块
        
    def start(self):
        if self.is_running:
            return False
            
        try:
            # 加载Whisper模型
            logging.info(f"加载Whisper模型: {self.model_size} (设备: {self.device})")
            self.model = whisper.load_model(
                self.model_size,
                device=self.device
            )
            
            # 启动后台处理线程
            self.is_running = True
            self.start_time = datetime.now()
            self.last_audio_time = datetime.now()
            self.final_result = []
            self.partial_results = []
            self.audio_buffer = np.array([], dtype=np.float32)
            
            # 启动处理线程
            self.processing_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.processing_thread.start()
            
            logging.info("Whisper识别已启动")
            return True
        except Exception as e:
            logging.error(f"启动Whisper识别失败: {str(e)}")
            return False
            
    def push_audio(self, audio_data):
        if not self.is_running:
            return False
            
        try:
            # 转换音频为PCM格式
            if isinstance(audio_data, bytes):
                audio = AudioSegment.from_file(io.BytesIO(audio_data))
                audio = audio.set_frame_rate(self.sample_rate).set_channels(1)
                samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
            else:
                # 假设已经是浮点数组
                samples = audio_data
                
            # 添加到缓冲区
            with self.buffer_lock:
                self.audio_buffer = np.concatenate((self.audio_buffer, samples))
                
            self.last_audio_time = datetime.now()
            return True
        except Exception as e:
            logging.error(f"推送音频失败: {str(e)}")
            return False
            
    def _process_audio(self):
        """后台处理音频的线程函数"""
        logging.info("音频处理线程已启动")
        while self.is_running:
            try:
                # 检查是否有足够的数据处理
                with self.buffer_lock:
                    if len(self.audio_buffer) < self.chunk_size:
                        time.sleep(0.1)
                        continue
                        
                    # 提取一个音频块
                    chunk = self.audio_buffer[:self.chunk_size]
                    self.audio_buffer = self.audio_buffer[self.chunk_size:]
                
                # 使用Whisper进行识别
                result = self.model.transcribe(
                    chunk,
                    language="zh",  # 设置中文识别
                    fp16=False,     # 避免精度问题
                    without_timestamps=True
                )
                
                text = result["text"].strip()
                if text:
                    # 保存结果
                    self.partial_results.append(text)
                    self.final_result.append(text)
                    
                    logging.debug(f"识别结果: {text}")
                    
            except Exception as e:
                logging.error(f"音频处理失败: {str(e)}")
                
            time.sleep(0.05)
            
        logging.info("音频处理线程已停止")
            
    def get_partial_results(self):
        """获取部分识别结果"""
        if not self.is_running or not self.partial_results:
            return []
            
        # 返回最新结果并清空部分结果列表
        results = self.partial_results.copy()
        self.partial_results = []
        return results
        
    def stop(self):
        """停止识别并获取最终结果"""
        if not self.is_running:
            return None
            
        logging.info("停止语音识别...")
        try:
            self.is_running = False
            if self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
            
            # 处理剩余音频
            final_text = ""
            with self.buffer_lock:
                if len(self.audio_buffer) > 0:
                    logging.info(f"处理剩余音频 ({len(self.audio_buffer)} 样本)")
                    result = self.model.transcribe(
                        self.audio_buffer,
                        language="zh",
                        fp16=False
                    )
                    text = result["text"].strip()
                    if text:
                        final_text = text
                        self.final_result.append(text)
            
            return {
                "final_result": self.final_result,
                "partial_results": self.partial_results,
                "final_text": final_text,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration": (datetime.now() - self.start_time).total_seconds()
            }
        except Exception as e:
            logging.error(f"停止识别失败: {str(e)}")
            return None
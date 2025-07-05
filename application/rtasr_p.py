import base64
import hmac
import json
import time
import threading
import pyaudio
import hashlib
import ssl
from urllib.parse import urlencode
import websocket
import logging

logger = logging.getLogger('RealTimeASR_Client')
# 将日志级别设置为 INFO，以便中间结果日志能够被输出
logger.setLevel(logging.INFO)  

# 讯飞开放平台应用配置 (请替换为您的实际信息) 
APPID = "9ca62843"             # 应用ID 
API_KEY = "984a6b0d57138c9e1c4b9404f6000022"  # 接口密钥 

# 音频参数 
AUDIO_FORMAT = pyaudio.paInt16  # 音频格式：16位整型 
CHANNELS = 1                    # 单声道 
RATE = 16000                    # 采样率：16kHz 
CHUNK = 1280                    # 每帧字节数（40ms音频） 
INTERVAL = 0.04                 # 发送间隔（40ms，与CHUNK对应） 

class RealTimeASR: 
    """ 
    实时语音识别客户端类，用于连接讯飞实时语音转写服务。 
    负责音频采集、WebSocket通信、签名生成以及结果处理。 
    """ 
    def __init__(self): 
        self.ws = None  # WebSocket连接对象 
        self.is_running = False  # 标记ASR是否正在运行 
        self.sid = None  # 会话ID，由讯飞服务返回 
        self.last_audio_time = 0  # 记录最后发送音频或接收消息的时间，用于超时检测 
        self.timeout_timer = None  # 超时检测定时器 
        self.timeout_seconds = 60  # 连接超时时间（秒），若长时间无音频或消息，则自动停止 
        
        # 调整：语音活动检测（VAD）中的静音时长，用于控制分段。 
        # 已从 5000 毫秒 (5秒) 增加到 8000 毫秒 (8秒)。 
        self.vad_pause_duration_ms = 8000  

        self.final_result_received = False  # 标记是否已收到最终结果 
        self.final_result = ""  # 存储最终识别结果（通常是最后一个完整句子） 
        self.audio_thread = None  # 音频采集和发送线程 
        self.audio_stream = None  # PyAudio流对象 
        self.p = None  # PyAudio实例 
        self.result_lock = threading.Lock()  # 用于保护结果数据（all_results, full_transcript）的并发访问 
        self.all_results = []  # 存储所有接收到的原始中间和最终结果（字典列表，包含type, text, timestamp） 
        
        # 优化：用于更准确地累积完整转录文本的两个新变量 
        self.finalized_sentences = [] # 存储已最终确定的转录片段（列表） 
        self.current_live_segment = "" # 存储当前正在识别的中间片段（字符串） 

        self.start_time = 0 # 记录ASR实例启动时间 

    def generate_signa(self): 
        """ 
        生成讯飞实时语音转写接口所需的签名。 
        包括时间戳（ts）和签名（signa）。 
        """ 
        ts = str(int(time.time())) # Current timestamp 
        base_string = APPID + ts 
        
        # Calculate MD5 hash of base_string 
        md5_base = hashlib.md5(base_string.encode()).hexdigest().lower() 

        # Generate HMAC-SHA1 signature 
        hmac_obj = hmac.new( 
            API_KEY.encode(),  
            md5_base.encode(),  
            hashlib.sha1 
        ) 
        signa = base64.b64encode(hmac_obj.digest()).decode() 
        
        return ts, signa 
    
    def build_url(self): 
        """ 
        构建WebSocket连接的完整URL，包含认证参数。 
        """ 
        ts, signa = self.generate_signa() 
        params = { 
            "appid": APPID, 
            "ts": ts, 
            "signa": signa, 
            "lang": "cn",      # Chinese recognition 
            "pd": "edu",       # Education domain 
            "vadMdn": 2,       # Near-field mode 
            "roleType": 0,     # No role separation 
            "end_point": self.vad_pause_duration_ms # Control VAD silence duration, in milliseconds 
        } 
        
        url = "wss://rtasr.xfyun.cn/v1/ws?" + urlencode(params) 
        logger.info(f"[URL构建] 最终URL: {url}") 
        
        return url 
    
    def on_open(self, ws): 
        """ 
        WebSocket连接建立时的回调函数。 
        设置运行状态，启动超时检测和音频采集线程。 
        """ 
        self.is_running = True 
        self.final_result_received = False 
        self.final_result = "" 
        self.all_results = [] 
        self.finalized_sentences = [] # Reset finalized transcript parts 
        self.current_live_segment = "" # Reset current intermediate segment 
        logger.info("WebSocket连接已建立，开始发送音频流...") 
        
        self.start_time = time.time() 
        self.last_audio_time = self.start_time 
        
        # 启动超时检测 
        self.start_timeout_check() 
        
        # 启动音频采集线程 
        self.audio_thread = threading.Thread( 
            target=self.send_audio_stream, 
            daemon=True # Set as daemon thread, terminates automatically when main program exits 
        ) 
        self.audio_thread.start() 
    
    def start_timeout_check(self): 
        """ 
        启动或重新启动超时检测定时器。 
        每秒检查一次是否超时。 
        """ 
        if self.timeout_timer and self.timeout_timer.is_alive(): 
            # If timer is already running, do not restart 
            return 
            
        self.timeout_timer = threading.Timer(1.0, self.check_timeout) 
        self.timeout_timer.start() 
    
    def check_timeout(self): 
        """ 
        检查ASR会话是否超时。 
        如果最后活动时间超过预设的timeout_seconds，则自动停止ASR。 
        """ 
        if not self.is_running: 
            return 
            
        current_time = time.time() 
        elapsed = current_time - self.last_audio_time 
        
        # 如果超过设定的超时时间 
        if elapsed > self.timeout_seconds: 
            logger.warning(f"\n超时时间到 ({self.timeout_seconds}秒)，停止识别...") 
            self.stop() 
        else: 
            # Continue checking 
            self.timeout_timer = threading.Timer(1.0, self.check_timeout) 
            self.timeout_timer.start() 
    
    def on_message(self, ws, message): 
        """ 
        接收WebSocket消息时的回调函数。 
        解析消息，处理启动、结果和错误信息。 
        """ 
        try: 
            msg = json.loads(message) 
            action = msg.get("action") 
            
            if action == "started": 
                self.sid = msg.get("sid") 
                logger.info(f"握手成功，会话ID: {self.sid}") 
            
            elif action == "result": 
                data = msg.get("data") 
                if data: 
                    self.process_result(json.loads(data)) 
            
            elif action == "error": 
                code = msg.get("code") 
                desc = msg.get("desc") 
                logger.error(f"WebSocket错误码: {code}，错误信息: {desc}") 
                self.stop() # Stop ASR on error message 
        
        except Exception as e: 
            logger.exception(f"消息处理异常: {e}") 
    
    def process_result(self, data): 
        """ 
        处理讯飞实时语音转写服务返回的转写结果。 
        区分中间结果和最终结果，并累积到 finalized_sentences 和 current_live_segment 中。 
        """ 
        # Update last activity time 
        self.last_audio_time = time.time() 
        
        if "cn" in data: 
            result_type = data["cn"]["st"].get("type") # 0 for final result, 1 for intermediate 
            words = [] 
            for rt in data["cn"]["st"].get("rt", []): 
                for ws_item in rt.get("ws", []): 
                    for cw in ws_item.get("cw", []): 
                        words.append(cw.get("w", "")) 
            
            result_text = "".join(words) 
            
            with self.result_lock: 
                # Add the raw result to the all_results list 
                self.all_results.append({ 
                    "type": "intermediate" if result_type != 0 else "final", 
                    "text": result_text, 
                    "timestamp": time.strftime("%H:%M:%S", time.localtime()) 
                }) 

                if result_type == 0:  # Final segment 
                    # Append the current_live_segment to finalized_sentences if it has content 
                    if self.current_live_segment: 
                        # Ensure it ends with a period if it's a final segment 
                        if not self.current_live_segment.endswith("。"): 
                            self.finalized_sentences.append(self.current_live_segment + "。") 
                        else: 
                            self.finalized_sentences.append(self.current_live_segment) 
                        self.current_live_segment = "" # Clear current intermediate segment as this segment is finalized 
                    
                    # Append the current final result_text 
                    if result_text: 
                        # Ensure the final result itself ends with a period 
                        if not result_text.endswith("。"): 
                            self.finalized_sentences.append(result_text + "。") 
                        else: 
                            self.finalized_sentences.append(result_text) 

                    self.final_result = result_text # Store the last final result for internal tracking 
                    self.final_result_received = True 
                    logger.info(f"[最终结果] {result_text}") 
                    # logger.info("检测到最终结果，停止识别...") # 暂时注释，让 stop 方法统一处理停止逻辑
                    # self.stop() # Stop ASR when final result is received 
                else:  # Intermediate segment prediction 
                    # Remove leading punctuation from intermediate result text 
                    cleaned_result_text = result_text.lstrip("，。？！、；：") 
                    
                    # Directly update current_live_segment with the latest, most complete intermediate result 
                    self.current_live_segment = cleaned_result_text 
                    logger.info(f"[中间结果] {cleaned_result_text}") # Output cleaned intermediate result to log 
    
    def send_audio_stream(self): 
        """ 
        音频采集和发送线程的入口函数。 
        从麦克风读取音频数据并通过WebSocket发送。 
        """ 
        self.p = pyaudio.PyAudio() 
        self.audio_stream = self.p.open( 
            format=AUDIO_FORMAT, 
            channels=CHANNELS, 
            rate=RATE, 
            input=True, 
            frames_per_buffer=CHUNK 
        ) 
        
        try: 
            while self.is_running and not self.final_result_received: 
                # Read audio data from microphone 
                audio_data = self.audio_stream.read(CHUNK, exception_on_overflow=False) 
                # Update last activity time 
                self.last_audio_time = time.time()              
                # Send audio data (Binary Message) 
                if self.ws and self.is_running:  
                    self.ws.send(audio_data, opcode=websocket.ABNF.OPCODE_BINARY) 
                # Control sending interval 
                time.sleep(INTERVAL) 
        except Exception as e: 
            logger.exception(f"音频采集异常: {e}") 
        finally: 
            # Send end flag 
            if self.ws and self.is_running:  
                try: 
                    # Send end signal to server to get final result 
                    self.ws.send(json.dumps({"end": True}), opcode=websocket.ABNF.OPCODE_TEXT) 
                    logger.info("已发送结束信号，等待最终结果...") 
                    # Wait for a period to receive the final result 
                    wait_start = time.time() 
                    while not self.final_result_received and time.time() - wait_start < 3: # Wait up to 3 seconds 
                        time.sleep(0.1) 
                except Exception as e: 
                    logger.error(f"发送结束信号异常: {e}") 
            
            # Close audio stream 
            if self.audio_stream: 
                self.audio_stream.stop_stream() 
                self.audio_stream.close() 
            if self.p: 
                self.p.terminate() 
            logger.info("音频采集已停止") 
    
    def on_error(self, ws, error): 
        """ 
        WebSocket错误时的回调函数。 
        """ 
        logger.error(f"WebSocket错误: {error}") 
        self.stop() 
    
    def on_close(self, ws, close_status_code, close_msg): 
        """ 
        WebSocket连接关闭时的回调函数。 
        """ 
        self.is_running = False 
        if self.timeout_timer: 
            self.timeout_timer.cancel() # Cancel timeout timer 
        
        if close_status_code != 1000: 
            logger.error(f"连接异常关闭，状态码: {close_status_code}, 原因: {close_msg}") 
        else: 
            logger.info("连接已正常关闭") 
    
    def start(self): 
        """ 
        启动实时转写。 
        初始化WebSocket连接并启动其运行线程。 
        """ 
        self.final_result = "" 
        self.all_results = [] 
        self.finalized_sentences = [] # Ensure reset on each start 
        self.current_live_segment = "" # Ensure reset on each start 
        self.final_result_received = False 
        url = self.build_url() 
        logger.info(f"正在连接: {url}") 
        
        # Create WebSocket client 
        self.ws = websocket.WebSocketApp( 
            url, 
            on_open=self.on_open, 
            on_message=self.on_message, 
            on_error=self.on_error, 
            on_close=self.on_close 
        ) 
        
        # Configure SSL context to skip SSL certificate verification (for development/testing only, verify certificates in production) 
        ssl_context = ssl.create_default_context() 
        ssl_context.check_hostname = False 
        ssl_context.verify_mode = ssl.CERT_NONE 
        
        try: 
            # Start WebSocket service thread 
            self.ws_thread = threading.Thread( 
                target=self.ws.run_forever, 
                kwargs={"sslopt": {"context": ssl_context}} 
            ) 
            self.ws_thread.daemon = True # Set as daemon thread 
            self.ws_thread.start() 
            logger.info("语音识别已启动") 
            return True 
        except Exception as e: 
            logger.exception(f"启动异常: {e}") 
            self.stop() # Stop ASR on failed start 
            return False 
    
    def stop(self): 
        """ 
        停止实时语音转写服务，并返回所有收集到的结果。 
        包括最终识别文本、所有中间结果列表和所有中间结果的直接组合文本。 
        """ 
        if self.is_running: 
            self.is_running = False 
            
            # Close WebSocket connection 
            if self.ws: 
                self.ws.close() 

            # Wait for audio thread and WebSocket thread to finish 
            if self.audio_thread and self.audio_thread.is_alive(): 
                self.audio_thread.join(2.0) # Wait up to 2 seconds 
            
            if self.ws_thread and self.ws_thread.is_alive(): 
                self.ws_thread.join(2.0) # Wait up to 2 seconds 
            
            logger.info("语音识别已停止") 
            
        # On stop, append any remaining current_live_segment to finalized_sentences 
        if self.current_live_segment: 
            with self.result_lock: 
                if not self.current_live_segment.endswith("。"): 
                    self.finalized_sentences.append(self.current_live_segment + "。") 
                else: 
                    self.finalized_sentences.append(self.current_live_segment) 
                self.current_live_segment = "" # Clear 

        # Concatenate all finalized sentences to form the complete transcript 
        full_transcript_assembled = "".join(self.finalized_sentences) 
        
        # Clean up trailing punctuation from the complete transcript 
        if full_transcript_assembled.endswith("。"): 
            full_transcript_assembled = full_transcript_assembled.rstrip("。") 
            
        # --- 新增代码部分：组合所有原始接收到的中间和最终文本 ---
        # 遍历 all_results 列表，将每个字典中的 'text' 值拼接起来
        combined_raw_intermediate_text = "".join([res["text"] for res in self.all_results])
        # --- 新增代码部分结束 ---

        # Return all results 
        return { 
            "final_result": full_transcript_assembled,  # Return the complete transcript as the final result 
            "intermediate_results": self.all_results, # Return the list of all raw intermediate and final results 
            "combined_raw_intermediate_text": combined_raw_intermediate_text # 新增此字段
        } 

    def get_current_transcription(self): 
        """ 
        获取当前累积的实时转录文本。 
        客户端可以调用此方法来获取ASR的实时进度。 
        """ 
        with self.result_lock: 
            # Combine finalized prefix and current intermediate segment 
            return "".join(self.finalized_sentences) + self.current_live_segment 


def start_recognition(): 
    """开始语音识别""" 
    global asr 
    asr = RealTimeASR() 
    # asr.timeout_seconds = 30  # <<<--- 请确保这行已被删除或注释掉，否则它将覆盖通过 API 传入的 timeout
    return asr.start() 

def stop_recognition(): 
    """结束语音识别并返回结果""" 
    global asr 
    if 'asr' in globals() and asr: 
        result = asr.stop() 
        return result 
    else: 
        print("没有正在进行的识别任务") 
        return None
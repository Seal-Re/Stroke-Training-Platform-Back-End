from flask import Blueprint, request, send_from_directory
import os
import re
from application.base import SERVER_HOST

audio_bp = Blueprint('audio', __name__)

voiceMap = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "yunyang": "zh-CN-YunyangNeural",
    "xiaobei": "zh-CN-liaoning-XiaobeiNeural",
    "xiaoni": "zh-CN-shaanxi-XiaoniNeural",
    "hiugaai": "zh-HK-HiuGaaiNeural",
    "hiumaan": "zh-HK-HiuMaanNeural",
    "wanlung": "zh-HK-WanLungNeural",
    "hsiaochen": "zh-TW-HsiaoChenNeural",
    "hsioayu": "zh-TW-HsiaoYuNeural",
    "yunjhe": "zh-TW-YunJheNeural",
}

def getVoiceById(voiceId):
    return voiceMap.get(voiceId)

def remove_html(string):
    regex = re.compile(r'<[^>]+>')
    cleaned = regex.sub('', string)
    return cleaned

def createAudio(text, file_name, voiceId):
    new_text = remove_html(text)
    print(f"Text without html tags: {new_text}")
    voice = getVoiceById(voiceId)
    if not voice:
        return "error params"

    pwdPath = os.getcwd()
    filePath = os.path.join(pwdPath, "tts", file_name)
    relativePath = f"/tts/{file_name}"
    dirPath = os.path.dirname(filePath)
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)
    if not os.path.exists(filePath):
        open(filePath, 'a').close()

    try:
        script = [
            'edge-tts',
            '--voice', voice,
            '--text', new_text,
            '--write-media', filePath
        ]
        import subprocess
        subprocess.run(script, check=True)
        url = f'{SERVER_HOST}{relativePath}' 
        return url
    except subprocess.CalledProcessError as e:
        import logging
        logging.error(f"创建音频失败: {e}")
        return "创建音频失败"
    except Exception as e:
        import logging
        logging.error(f"处理音频时发生其他错误: {e}")
        return "处理音频时发生错误"

def getParameter(request, paramName):
    if request.args.__contains__(paramName):
        return request.args[paramName]
    return ""

@audio_bp.route('/dealAudio', methods=['POST', 'GET'])
def dealAudio():
    text = getParameter(request, 'text')
    file_name = getParameter(request, 'file_name')
    voice = getParameter(request, 'voice')
    return createAudio(text, file_name, voice)

@audio_bp.route('/static/<path:filename>')
def serve_static(filename):
    from flask import current_app
    return send_from_directory(current_app.static_folder, filename)

@audio_bp.route('/tts/<path:filename>')
def serve_tts(filename):
    tts_dir = os.path.join(os.getcwd(), 'tts')
    return send_from_directory(tts_dir, filename)

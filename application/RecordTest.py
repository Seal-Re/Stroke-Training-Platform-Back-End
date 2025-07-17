import time
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
import logging

from .wapp import ASRService 
from .wapp import logger as asr_logger 

UPLOAD_FOLDER = 'RecordingData'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER) 

RecordTest_bp = Blueprint('recordTest', __name__)


@RecordTest_bp.route('/api/receiveRecordingDataTest', methods=['POST'])
def receiveRecordingDataTest():
    asr_service = current_app.asr_service 
    main_logger = asr_logger 

    if 'audioFile' not in request.files:
        return jsonify({'error': 'No audio file found in the request'}), 400

    audio_file = request.files['audioFile']
    session_id = request.form.get('session_id') 

    if audio_file.filename == '':
        return jsonify({'error': 'No selected audio file'}), 400

    filepath = None 

    try:
        filename_base, file_extension = os.path.splitext(audio_file.filename)
        unique_filename = f"recording_{uuid.uuid4().hex}{file_extension}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename) 

        audio_file.save(filepath)
        main_logger.info(f"File saved successfully at: {filepath}")

        with open(filepath, 'rb') as f:
            audio_data_for_asr = f.read()

        if not session_id:
            session_id, error_message = asr_service.start_new_session(model_size=request.form.get('model_size', 'base'))
            if error_message:
                return jsonify({"status": "error", "message": error_message}), 429 if "最大并发连接数" in error_message else 500
            
            push_success, push_error = asr_service.push_audio_data(session_id, audio_data_for_asr)
            if not push_success:
                asr_service.stop_session(session_id) 
                return jsonify({"status": "error", "message": push_error}), 500

        else:
            push_success, push_error = asr_service.push_audio_data(session_id, audio_data_for_asr)
            if not push_success:
                return jsonify({"status": "error", "message": push_error}), 404 if "无效的session_id" in push_error else 400

        return jsonify({
            'message': 'Recording received and saved for ASR processing!',
            'filename': unique_filename,
            'path': filepath,
            'session_id': session_id, 
            'partial_results': [] 
        }), 200

    except Exception as e:
        main_logger.error(f"Error saving file or processing with ASR: {e}", exc_info=True)
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 500
    finally:
        pass


@RecordTest_bp.route('/api/stopASR', methods=['POST'])
def stop_asr_from_recordtest():
    """结束语音识别并获取最终结果的端点 (触发离线识别)"""
    asr_service = current_app.asr_service 
    main_logger = asr_logger 

    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({
            "status": "error",
            "message": "缺少session_id参数"
        }), 400

    result, error_message = asr_service.stop_session(session_id)

    if error_message:
        return jsonify({"status": "error", "message": error_message}), 404 if "无效的session_id" in error_message else 500
    
    if result:
        return jsonify({
            "status": "success",
            "message": "语音识别已完成",
            "results": result 
        })
    else:
        return jsonify({
            "status": "error",
            "message": "获取结果失败或ASR处理异常"
        }), 500

@RecordTest_bp.route('/api/asr_status', methods=['POST'])
def get_asr_status():
    """获取指定会话的当前状态（离线模式下，例如已收集的音频大小）"""
    asr_service = current_app.asr_service
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"status": "error", "message": "缺少session_id参数"}), 400
    
    session_data = asr_service.get_session(session_id)
    if not session_data:
        return jsonify({"status": "error", "message": "无效的session_id"}), 404
    
    audio_size = sum(len(chunk) for chunk in session_data.get('audio_chunks', []))
    
    return jsonify({
        "status": session_data['status'],
        "message": f"会话正在收集音频，已收集 {audio_size} 字节。",
        "session_id": session_id,
        "collected_audio_size": audio_size,
        "last_activity": session_data['last_activity']
    }), 200

@RecordTest_bp.route('/api/active_asr_sessions', methods=['GET'])
def get_active_asr_sessions():
    """获取所有活跃会话的列表 (离线模式下显示正在收集的会话)"""
    asr_service = current_app.asr_service
    response_data, status_code = asr_service.get_active_sessions_list() # ASRService 已经提供了这个方法
    return jsonify(response_data), status_code

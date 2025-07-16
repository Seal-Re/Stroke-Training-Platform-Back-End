import time
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
import logging

UPLOAD_FOLDER = 'RecordingData'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER) 

RecordTest_bp = Blueprint('recordTest', __name__)

from wapp import logger as asr_logger 

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
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)

        audio_file.save(filepath)
        main_logger.info(f"File saved successfully at: {filepath}")

        with open(filepath, 'rb') as f:
            audio_data_for_asr = f.read()

        if not session_id:
            # If no session_id , it indicates it is a new session ,need to ccreate
            session_id, error_message = asr_service.start_new_session(model_size=request.form.get('model_size', 'base'))
            if error_message:
                return jsonify({"status": "error", "message": error_message}), 429 if "最大并发连接数" in error_message else 500
            
            push_success, push_error = asr_service.push_audio_data(session_id, audio_data_for_asr)
            if not push_success:
                asr_service.stop_session(session_id)# Clean up
                return jsonify({"status": "error", "message": push_error}), 500

        else:
            push_success, push_error = asr_service.push_audio_data(session_id, audio_data_for_asr)
            if not push_success:
                return jsonify({"status": "error", "message": push_error}), 404 if "无效的session_id" in push_error else 400

        partial_results = asr_service.get_partial_results(session_id)

        return jsonify({
            'message': 'Recording received, saved, and processed by ASR!',
            'filename': unique_filename,
            'path': filepath,
            'session_id': session_id, 
            'partial_results': partial_results 
        }), 200

    except Exception as e:
        main_logger.error(f"Error saving file or processing with ASR: {e}", exc_info=True)
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 500
    finally:
        pass


@RecordTest_bp.route('/api/stopASR', methods=['POST'])
def stop_asr_from_recordtest():
    """结束语音识别并获取最终结果的端点"""
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
        return jsonify({"status": "error", "message": error_message}), 404 

    if result:
        return jsonify({
            "status": "success",
            "message": "语音识别已停止",
            "results": result 
        })
    else:
        return jsonify({
            "status": "error",
            "message": "获取结果失败或ASR已停止"
        }), 500

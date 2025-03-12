from flask import Blueprint, request, jsonify
import logging
from .utils import save_collection

getLastScore_bp = Blueprint('getLastScore', __name__)

@getLastScore_bp.route('/api/getLastScore', methods=['GET'])
def get_last_score():
    username = request.args.get('username')
    if not username:
        return jsonify({"message": "Missing username parameter"}), 400

    try:
        save_data = save_collection.find_one({"username": username})
        if save_data and save_data.get('data'):
            last_submission = save_data['data'][-1]
            return jsonify({"score": last_submission["score"]})
        else:
            return jsonify({"score": 0})
    except Exception as e:
        logging.error(f"Error getting last score: {e}")
        return jsonify({"message": f"Error getting last score: {str(e)}"}), 500
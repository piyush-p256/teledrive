# Render Web Service for TeleStore File Upload
# Deploy this as a Web Service on Render

from flask import Flask, request, jsonify
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Configuration - only set BACKEND_URL, credentials will be fetched automatically
CONFIG = {
    'BACKEND_URL': os.environ.get('BACKEND_URL', 'https://your-telestore-backend.com'),
    'MAX_FILE_SIZE': 2000 * 1024 * 1024,
    'CACHE_DURATION': 3600,  # 1 hour in seconds
}

# In-memory cache for credentials
credentials_cache = {
    'data': None,
    'timestamp': None,
    'user_id': None
}

def get_credentials(user_id, auth_token):
    """Fetch credentials from backend or return cached version"""
    now = datetime.now()
    
    # Return cached credentials if still valid and for same user
    if (credentials_cache['data'] and 
        credentials_cache['user_id'] == user_id and
        credentials_cache['timestamp'] and
        (now - credentials_cache['timestamp']).total_seconds() < CONFIG['CACHE_DURATION']):
        return credentials_cache['data']
    
    # Fetch fresh credentials from backend
    try:
        response = requests.get(
            f"{CONFIG['BACKEND_URL']}/api/worker/credentials",
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch credentials: {response.text}")
        
        credentials = response.json()
        
        # Cache the credentials
        credentials_cache['data'] = credentials
        credentials_cache['timestamp'] = now
        credentials_cache['user_id'] = user_id
        
        return credentials
    except Exception as e:
        # If cache exists, use it even if expired (fallback)
        if credentials_cache['data'] and credentials_cache['user_id'] == user_id:
            print(f'Using expired cache due to fetch error: {e}')
            return credentials_cache['data']
        raise e

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    # Handle CORS
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    try:
        file = request.files.get('file')
        user_id = request.form.get('userId')
        auth_token = request.form.get('authToken')  # User's auth token for fetching credentials
        file_name = request.form.get('fileName') or file.filename
        
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        if not auth_token:
            return jsonify({'error': 'Auth token required'}), 400
        
        # Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > CONFIG['MAX_FILE_SIZE']:
            return jsonify({'error': 'File too large (max 2GB)'}), 400
        
        # Fetch credentials from backend (or use cache)
        credentials = get_credentials(user_id, auth_token)
        
        # Upload to Telegram
        files = {
            'document': (file_name, file.read(), file.content_type)
        }
        data = {
            'chat_id': credentials['channel_id'],
            'caption': f'Uploaded: {file_name}'
        }
        
        telegram_response = requests.post(
            f"https://api.telegram.org/bot{credentials['bot_token']}/sendDocument",
            files=files,
            data=data
        )
        
        telegram_result = telegram_response.json()
        
        if not telegram_result.get('ok'):
            raise Exception(telegram_result.get('description', 'Telegram upload failed'))
        
        message_id = telegram_result['result']['message_id']
        file_id = telegram_result['result']['document']['file_id']
        
        # Notify backend
        requests.post(
            f"{CONFIG['BACKEND_URL']}/api/webhook/upload",
            json={
                'userId': user_id,
                'fileName': file_name,
                'messageId': message_id,
                'fileId': file_id,
                'size': file_size,
                'mimeType': file.content_type,
            }
        )
        
        response = jsonify({
            'success': True,
            'messageId': message_id,
            'fileId': file_id,
            'fileName': file_name,
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        response = jsonify({'error': str(e)})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS
import os
import uuid
import time
import requests
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
CORS(app)

# 설정
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# AI 서버 URL 설정
AI_SERVER_URL = 'https://jungduri.github.io/cineai'

# 필요한 폴더 생성
for folder in [UPLOAD_FOLDER, DOWNLOAD_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 처리 중인 작업 상태 저장
jobs = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': '파일이 없습니다.'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'MP4 파일만 업로드 가능합니다.'}), 400
    
    # 파일 저장
    filename = secure_filename(file.filename)
    timestamp = int(time.time())
    saved_filename = f"{timestamp}-{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)
    
    # 작업 ID 생성 및 상태 초기화
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'status': 'processing',
        'filepath': filepath,
        'start_time': time.time()
    }
    
    # AI 서버로 파일 전송
    try:
        with open(filepath, 'rb') as f:
            files = {'video': (filename, f, 'video/mp4')}
            response = requests.post(f'{AI_SERVER_URL}/process', files=files)
            
            if response.status_code == 200:
                result = response.json()
                jobs[job_id]['ai_job_id'] = result.get('ai_job_id')
            else:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['error'] = 'AI 서버 처리 실패'
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
    
    return jsonify({'jobId': job_id})

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': '작업을 찾을 수 없습니다.'}), 404
    
    job = jobs[job_id]
    
    # AI 서버에서 상태 확인
    if job['status'] == 'processing' and 'ai_job_id' in job:
        try:
            response = requests.get(f'{AI_SERVER_URL}/status/{job["ai_job_id"]}')
            if response.status_code == 200:
                ai_status = response.json()
                if ai_status['status'] == 'completed':
                    # AI 서버에서 결과 파일 다운로드
                    result_filename = ai_status['result_url'].split('/')[-1]
                    result_path = os.path.join(app.config['DOWNLOAD_FOLDER'], result_filename)
                    
                    # AI 서버에서 결과 파일 가져오기
                    ai_result_url = f"{AI_SERVER_URL}{ai_status['result_url']}"
                    result_response = requests.get(ai_result_url, stream=True)
                    
                    if result_response.status_code == 200:
                        with open(result_path, 'wb') as f:
                            for chunk in result_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        job['status'] = 'completed'
                        job['result_url'] = f"/download/{result_filename}"
                    else:
                        job['status'] = 'error'
                        job['error'] = '결과 파일 다운로드 실패'
                elif ai_status['status'] == 'error':
                    job['status'] = 'error'
                    job['error'] = ai_status.get('error', 'AI 처리 중 오류 발생')
        except Exception as e:
            job['status'] = 'error'
            job['error'] = str(e)
    
    return jsonify({
        'status': job['status'],
        'resultUrl': job.get('result_url'),
        'error': job.get('error')
    })

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True) 
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 설정
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 업로드 폴더가 없으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
    
    # 테스트용 처리 시뮬레이션 (10초 후 완료)
    def process_video():
        time.sleep(10)  # 10초 대기
        if job_id in jobs:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['result_url'] = f'/uploads/{saved_filename}'
    
    # 비동기 처리 시작
    from threading import Thread
    thread = Thread(target=process_video)
    thread.start()
    
    return jsonify({'jobId': job_id})

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': '작업을 찾을 수 없습니다.'}), 404
    
    job = jobs[job_id]
    return jsonify({
        'status': job['status'],
        'resultUrl': job.get('result_url')
    })

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True) 
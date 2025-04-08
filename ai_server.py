from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import time
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
CORS(app)

# 설정
UPLOAD_FOLDER = 'ai_uploads'
RESULT_FOLDER = 'ai_results'
ALLOWED_EXTENSIONS = {'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

# 필요한 폴더 생성
for folder in [UPLOAD_FOLDER, RESULT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 처리 중인 작업 상태 저장
jobs = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/process', methods=['POST'])
def process_video():
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
        'input_file': filepath,
        'start_time': time.time()
    }
    
    # 테스트용 처리 시뮬레이션 (10초 후 완료)
    def simulate_processing():
        time.sleep(10)  # 10초 대기
        if job_id in jobs:
            # 결과 파일 생성 (테스트용으로는 입력 파일을 복사)
            result_filename = f"result-{saved_filename}"
            result_filepath = os.path.join(app.config['RESULT_FOLDER'], result_filename)
            shutil.copy2(filepath, result_filepath)
            
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['result_file'] = result_filepath
            jobs[job_id]['result_url'] = f'/results/{result_filename}'
    
    # 비동기 처리 시작
    from threading import Thread
    thread = Thread(target=simulate_processing)
    thread.start()
    
    return jsonify({'ai_job_id': job_id})

@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': '작업을 찾을 수 없습니다.'}), 404
    
    job = jobs[job_id]
    return jsonify({
        'status': job['status'],
        'result_url': job.get('result_url')
    })

@app.route('/results/<filename>')
def get_result(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
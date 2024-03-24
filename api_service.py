from flask import Flask, request, jsonify
import jwt
import datetime
import time
import mysql.connector
import oss2
import os
from oss2.credentials import EnvironmentVariableCredentialsProvider
from werkzeug.utils import secure_filename
import uuid
import requests
import json
from hashlib import md5
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许所有的跨域请求

endpoint = 'http://oss-cn-guangzhou.aliyuncs.com' 
def upload_file(file_local_path, oos_file_name):
    auth = oss2.Auth('xxx', 'xxx')
    bucket = oss2.Bucket(auth, endpoint, 'xxx')
    result = bucket.put_object_from_file(oos_file_name, file_local_path)
    print("result id = ".format(result.request_id))
    print("Upload video success!")
    return "https://xxx.oss-cn-guangzhou.aliyuncs.com/" + str(oos_file_name)

def upload_video(file_local_path, oos_file_name):
    auth = oss2.Auth('xxx', 'xxx')
    bucket = oss2.Bucket(auth, endpoint, 'xxx2')
    result = bucket.put_object_from_file(oos_file_name, file_local_path)
    print("result id = ".format(result.request_id))
    print("Upload video success!")
    return "https://xxx.oss-cn-guangzhou.aliyuncs.com/" + str(oos_file_name)

def generate_uuid():
    return str(uuid.uuid4()).replace('-', '')

jwt_secret_key = "your_secret_key_test"
# 校验 accessToken
def verify_accessToken(accessToken):
    secret_key = jwt_secret_key  # 用于签名的密钥
    try:
        payload = jwt.decode(accessToken, secret_key, algorithms=['HS256'])
        # 在这里可以根据需要进行进一步的校验，比如检查用户权限等
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False

def get_user_uuid_from_token(accessToken, secret_key):
    try:
        payload = jwt.decode(accessToken, secret_key, algorithms=['HS256'])
        user_uuid = payload.get('user_uuid')
        return user_uuid
    except jwt.ExpiredSignatureError:
        # 处理token过期的情况
        return None
    except jwt.InvalidTokenError:
        # 处理无效token的情况
        return None

# 统一处理 accessToken
@app.before_request
def before_request():
    if request.path != '/discovery/v1/login' and not request.path.startswith('/local'):  # 排除登录接口
        accessToken = request.headers.get('accessToken')
        if not accessToken or not verify_accessToken(accessToken):
            res_json = {"accessToken": "", "login_res": "未登录"}
            return init_ok_data(3401, res_json)

# 生成token
def generate_accessToken(user_uuid, user_name):
    payload = {
        'user_uuid': user_uuid,
        'user_name': user_name,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=3)
    }
    secret_key = jwt_secret_key  # 用于签名的密钥
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token

def init_ok_data(result_code, data=None):
    response = {
        "result": result_code,
        "msg": "^-^",
        "data": data if data is not None else {}
    }
    return response

## 上下文管理器
class Database:
    def __enter__(self):
        self.cnx = mysql.connector.connect(user='db_username', password='db_pwd',
                                  host='db_host', database='db_t')
        return self.cnx

    def __exit__(self, exc_type, exc_value, traceback):
        self.cnx.close()

def fetch_user_uuid(user_name, user_pwd):
    print("user_name="+str(user_name) + ", user_pwd="+str(user_pwd))
    with Database() as cnx:
        cursor = cnx.cursor()
        query = ("SELECT uuid FROM t_user WHERE user_name = %s AND user_pwd = %s")
        cursor.execute(query, (user_name, user_pwd))
        result = cursor.fetchone()
        return result[0] if result else None

def insert_user_login_log(user_uuid):
    try:
        with Database() as cnx:
            cursor = cnx.cursor()
            excute_sql = ("INSERT INTO t_user_login_log (user_uuid, create_time) VALUES (%s, %s)")
            cursor.execute(excute_sql, (user_uuid, int(time.time())))
            cnx.commit()  # Commit the changes to the database
            print("ex success")
            return True
    except Exception as e:
        print("Error occurred while inserting user login log:", e)
    return False

@app.route('/discovery/v1/login', methods=['POST'])
def login():
    user_name = request.json.get('user_name')
    user_pwd = request.json.get('user_pwd')
    try:
        user_uuid = fetch_user_uuid(user_name, user_pwd)
        print("user_uuid="+str(user_uuid))
        if user_uuid is not None:
            accessToken = generate_accessToken(user_uuid, user_name)
            res_json = {"accessToken": accessToken, "login_res": "success"}
            insert_user_login_log(user_uuid)
            return init_ok_data(200, res_json)
        else:
            res_json = {"accessToken": "", "login_res": "账号不存在"}
            return init_ok_data(200, res_json)
    except Exception as e:
        print("e:"+str(e))
        res_json = {"accessToken": "", "login_res": "服务端报错，请联系管理员"}
        return init_ok_data(3000, res_json)

@app.route('/discovery/digital/my_human_list', methods=['GET'])
def get_human_list():
    accessToken = request.headers.get('accessToken')
    user_uuid = get_user_uuid_from_token(accessToken, jwt_secret_key)
    if user_uuid:
        with Database() as cnx:
            cursor = cnx.cursor()
            query = ("SELECT uuid, digital_human_name FROM t_my_digital_humans_table WHERE user_uuid = %s")
            cursor.execute(query, (user_uuid,))
            result = cursor.fetchall()

            human_list = [{"human_uuid": row[0], "human_name": row[1]} for row in result]
            res_json = {"human_list": human_list}
            return init_ok_data(200, res_json)
    else:
        return init_ok_data(200, [])

@app.route('/discovery/digital/upload_files', methods=['POST'])
def upload_files():
    accessToken = request.headers.get('accessToken')
    user_uuid = get_user_uuid_from_token(accessToken, jwt_secret_key)
    multi_files = request.files.getlist('file')  # Get the list of files from the request
    file_locations = []
    for file in multi_files:
        filename = file.filename
        filename = filename.replace(" ", "")
        file.save(filename)  # Save the file locally
        current_time_second = int(time.time())
        # audio_url = upload_file("C:\\Users\\29650\\.cursor-tutor\\digital-human-video\\"+str(filename), "digital/" + str(user_uuid) + "/" + str(filename))
        audio_url = upload_file("/root/digital-human-video/" +str(filename), 
        "digital/" + str(user_uuid) + "/" + str(current_time_second) + "_" + str(filename))
        file_locations.append(audio_url)
    return init_ok_data(200, {"audio_urls": file_locations})

@app.route('/discovery/digital/make_video', methods=['POST'])
def make_video():
    try:
        accessToken = request.headers.get('accessToken')
        user_uuid = get_user_uuid_from_token(accessToken, jwt_secret_key)
        print("user_uuid="+str(user_uuid))
        human_uuid = request.json.get('human_uuid')
        audio_urls = request.json.get('audio_urls')
        if not audio_urls:
            return init_ok_data(200, "音频参数不能为空")
        for audio_url in audio_urls:
            train_sub_video_file_url = """https://xxx.oss-cn-guangzhou.aliyuncs.com/digital/%s/%s/%s.mp4"""  % (user_uuid, human_uuid, "37s")
            print(audio_url)
            print(train_sub_video_file_url)
            api_make_video_local(train_sub_video_file_url, audio_url, user_uuid, human_uuid)
            #api_make_video(train_sub_video_file_url, audio_url, user_uuid)
        return init_ok_data(200, "success")
    except Exception as e:
        print("Error occurred while make_video:", e)
        return init_ok_data(200, "Error occurred while make_video")

def insert_video_task(user_uuid, live_code, make_status, background_url, live_sound_url, human_uuid):
    try:
        file_name_with_extension  = os.path.basename(live_sound_url)
        video_file_name, file_extension = os.path.splitext(file_name_with_extension)
        with Database() as cnx:
            cursor = cnx.cursor()
            uuid = generate_uuid()
            current_time_second = int(time.time())
            query = ("INSERT INTO t_digital_human_video_task_table (uuid, user_uuid, live_code, make_status, background_url, live_sound_url, create_time, update_time, video_name, human_uuid) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            cursor.execute(query, (uuid, user_uuid, live_code, make_status, background_url, live_sound_url, current_time_second, current_time_second, video_file_name, human_uuid))
            cnx.commit()  # Commit the changes to the database
            return True
    except Exception as e:
        print("Error occurred while inserting video task:", e)
        # handle the exception as needed
        return False

def api_make_video_local(train_sub_video_file_url, audio_url, user_uuid, human_uuid):
    live_code = ""
    insert_video_task(user_uuid, live_code, 0, train_sub_video_file_url, audio_url, human_uuid)
    return

## 三方测试接口，可以接入别人api
def api_make_video(train_sub_video_file_url, audio_url, user_uuid):
    url = 'http://119.23.64.239:9638/digital/auth/token'
    data = {
        'apiKey': "62530500670",
        'apiSecret':'7f8d5683887f9a3232a1088c0332a039'
    }
    response = requests.post(url, data=data)
    data = json.loads(response.content.decode('utf-8'))
    print(data)
    access_token = data['data']['access_token']
    store_id = data['data']['store_id']
    user_id = data['data']['userId']
    _time = int(time.time())
    md5_str = str(access_token) + str(_time) + str(user_id) + str(store_id) 
    secret = md5(md5_str.encode()).hexdigest()
    print("secret="+str(secret))

    url = 'http://119.23.64.239:9638/digital/video/re/make?live_sound_url='+audio_url+"&background_url="+train_sub_video_file_url+"&access_token="+access_token+"&store_id="+store_id+"&time="+str(_time)+"&secret="+str(secret)
    response = requests.post(url)
    data = json.loads(response.content.decode('utf-8'))
    print(data)

    if data['resultCode'] == 1:
        live_code = data['data']['live_code']
        print("视频制作任务提交成功！live_code="+str(live_code))
        insert_video_task(user_uuid, live_code, 0, train_sub_video_file_url, audio_url)
    else:
        print("视频生成失败！")
        print("错误信息:", response.text)

@app.route('/discovery/digital/video_list', methods=['GET'])
def get_video_list():
    try:
        accessToken = request.headers.get('accessToken')
        user_uuid = get_user_uuid_from_token(accessToken, jwt_secret_key)
        with Database() as cnx:
            cursor = cnx.cursor()
            query = ("SELECT make_status, video_url, cover_img, create_time, update_time, video_name FROM t_digital_human_video_task WHERE user_uuid = %s ORDER BY update_time DESC limit 10")
            cursor.execute(query, (user_uuid,))
            result = cursor.fetchall()
            #print(result)
            video_list = []
            for row in result:
                make_status = row[0]
                video_url = row[1]
                cover_img = row[2]
                create_time = row[3]
                update_time = row[4]
                video_name = row[5]
                video_name = '_'.join(video_name.split('_')[1:])
                video_info = {
                    "video_name": video_name,
                    "make_status_code": make_status,
                    "make_status": exchange_make_status(make_status),
                    "cover_img": cover_img,
                    "oss_url": video_url,
                    "created_at": datetime.datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S'),
                    "updated_at": datetime.datetime.fromtimestamp(update_time).strftime('%Y-%m-%d %H:%M:%S')
                }
                video_list.append(video_info)
            return init_ok_data(200, {"video_list": video_list})

    except Exception as e:
        print("Error occurred while fetching video list:", e)
        return init_ok_data(200, str(e))
        # handle the exception as needed

@app.route('/discovery/digital/video_creations', methods=['GET'])
def get_video_creations():
    try:
        accessToken = request.headers.get('accessToken')
        user_uuid = get_user_uuid_from_token(accessToken, jwt_secret_key)
        with Database() as cnx:
            cursor = cnx.cursor()
            query = ("SELECT make_status, video_url, cover_img, create_time, update_time, video_name FROM t_digital_human_video_task_table WHERE user_uuid = %s ORDER BY update_time DESC")
            cursor.execute(query, (user_uuid,))
            result = cursor.fetchall()
            video_list = []
            for row in result:
                make_status = row[0]
                video_url = row[1]
                cover_img = row[2]
                create_time = row[3]
                update_time = row[4]
                video_name = row[5]
                video_name = '_'.join(video_name.split('_')[1:])
                video_info = {
                    "video_name": video_name,
                    "make_status_code": make_status,
                    "make_status": exchange_make_status(make_status),
                    "cover_img": cover_img,
                    "oss_url": video_url,
                    "created_at": datetime.datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S'),
                    "updated_at": datetime.datetime.fromtimestamp(update_time).strftime('%Y-%m-%d %H:%M:%S')
                }
                video_list.append(video_info)
            return init_ok_data(200, {"video_list": video_list})

    except Exception as e:
        print("Error occurred while fetching video list:", e)
        return init_ok_data(200, str(e))
        # handle the exception as needed

def exchange_make_status(make_status_code):
    if make_status_code == 0:
        return "制作中"
    elif make_status_code == 1:
        return "制作成功"
    else:
        return "制作中_v2"

##  local start
@app.route('/local/upload_video', methods=['POST'])
def local_upload_video():
    print("start local_upload_video:")
    user_uuid = "test_local"
    multi_files = request.files.getlist('file')  # Get the list of files from the request
    file_locations = []
    for file in multi_files:
        filename = file.filename
        filename = filename.replace(" ", "")
        file.save(filename)  # Save the file locally
        current_time_second = int(time.time())
        #audio_url = upload_video("C:\\Users\\29650\\.cursor-tutor\\digital-human-video\\"+str(filename), "digital/" + str(user_uuid) + "/" + str(filename))
        video_url = upload_video("/root/digital-human-video/" +str(filename), 
        "digital/" + str(user_uuid) + "/" + str(current_time_second) + "_" + str(filename))
        file_locations.append(video_url)
    return init_ok_data(200, {"video_urls": file_locations})

@app.route('/local/fetch_unmake_task', methods=['GET'])
def local_fetch_unmake_task():
    try:
        user_uuid = "42912312321942aa9eeed512312312"
        with Database() as cnx:
            cursor = cnx.cursor()
            query = ("SELECT make_status, video_name, live_sound_url, uuid, human_uuid FROM t_digital_human_video_task_table WHERE user_uuid = %s and make_status = 0 ORDER BY update_time DESC limit 10")
            cursor.execute(query, (user_uuid,))
            result = cursor.fetchall()
            print(result)
            video_list = []
            for row in result:
                make_status = row[0]
                video_name = row[1]
                live_sound_url = row[2]
                uuid = row[3]
                human_uuid = row[4]
                video_info = {
                    "make_status_code": make_status,
                    "video_name": video_name,
                    "live_sound_url": live_sound_url,
                    "uuid": uuid,
                    "human_uuid": human_uuid
                }
                video_list.append(video_info)
            return init_ok_data(200, {"video_list": video_list})

    except Exception as e:
        print("Error occurred while fetching video list:", e)
        return init_ok_data(200, str(e))
        # handle the exception as needed

@app.route('/local/update_task', methods=['POST'])
def local_update_task():
    video_oss_url = request.json.get('video_oss_url')
    uuid = request.json.get('video_uuid')
    cover_img = request.json.get('cover_img')
    print("video_oss_url="+str(video_oss_url) + ", uuid="+str(uuid))
    try:
        with Database() as cnx:
            cursor = cnx.cursor()
            current_time_second = int(time.time())
            query = ("update t_digital_human_video_task_table set video_url =  %s, update_time = %s, cover_img = %s, make_status = 1 where uuid = %s")
            cursor.execute(query, (video_oss_url, current_time_second, cover_img, uuid))
            cnx.commit()
            return init_ok_data(200, "")
    except Exception as e:
        print("Error occurred while inserting video task:", e)
        # handle the exception as needed
        return False

##  local end

if __name__ == '__main__':
    app.run(port=18399)
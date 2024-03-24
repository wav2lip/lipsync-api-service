import requests
import os

blue_oldman_audio_root_path = "G:\\2013VS\\digital-wavlipgfp\\inputs\\blue_oldman\\source_audio"
blue_oldman_glasses_audio_root_path = "G:\\2013VS\\digital-wavlipgfp\\inputs\\blue_oldman_glasses\\source_audio"
glasses_oldman_audio_root_path = "G:\\2013VS\\digital-wavlipgfp\\inputs\\glasses_oldman\\source_audio"
franklin_audio_root_path = "G:\\2013VS\\digital-wavlipgfp\\inputs\\franklin\\source_audio"

def upload_video(local_file_path):
    print("local_file_path = "+ str(local_file_path))
    url = "http://xxx.com/local/upload_video"
    ## file_path = "C:\\Users\\29650\\.cursor-tutor\\digital-human-video\\0222_pure_v3.mp4"
    try:
        with open(local_file_path, "rb") as file:
            files = {"file": (file)}
            response = requests.post(url, files=files)
            res = response.text
            return response.text
    except Exception as e:
        return str(e)

def remote_fetch_unmake_task(api_url):
    try:
        response = requests.get(api_url)
        response_data = response.json()
        if response_data["result"] == 200 and "video_list" in response_data["data"]:
            return response_data["data"]["video_list"]
        else:
            print("Failed to fetch unmake task:", response_data.get("msg"))
            return []
    except Exception as e:
        print("Error occurred while fetching unmake task:", e)
        return None

def download_audio_to_local(audio_url, dist_path):
    try:
        response = requests.get(audio_url)
        os.makedirs(os.path.dirname(dist_path), exist_ok=True)
        # 写入文件
        with open(dist_path, 'wb') as f:
            f.write(response.content)
        
        print(f"文件已下载到：{dist_path}")
        return True
    except Exception as e:
        print(f"下载文件失败: {e}")
        return False

def fetch_video_list_and_download_audio():
    api_url = "http://xxx.com/local/fetch_unmake_task"
    video_list = remote_fetch_unmake_task(api_url)
    res = []
    if video_list:
        for video_info in video_list:
            video_name = video_info["video_name"]
            video_uuid = video_info["uuid"]
            audio_url = video_info["live_sound_url"]
            human_uuid = video_info["human_uuid"]
            print("Video Name:", video_name + ", human_uuid:" + str(human_uuid))
            dist_path_root = blue_oldman_audio_root_path
            if human_uuid == "c5e32c1231271231c123122d5c2e":
                dist_path_root = blue_oldman_glasses_audio_root_path
            elif human_uuid == "d563212312c2d5e3a":
                dist_path_root = glasses_oldman_audio_root_path
            elif human_uuid == "e2332c6651231296c2d5e2c":
                dist_path_root = franklin_audio_root_path
            print("---------------------------")
            
            local_audio_name = video_uuid + "_" + video_name + ".mp3"
            download_status = download_audio_to_local(audio_url, dist_path_root + "\\" + local_audio_name)
            if download_status:
                res.append(video_info)
        return res      
    else:
        print("No unmake task found.")
        return res

def delete_mp3_files_in_directory(dist_directory):
    try:
        if not os.listdir(dist_directory):
            print("目录为空，无需删除 .mp3 文件")
            return 0
        count = 0
        for file_name in os.listdir(dist_directory):
            if file_name.endswith(".mp3"):
                file_path = os.path.join(dist_directory, file_name)
                os.remove(file_path)
                count += 1
        print(f"已删除 {count} 个 .mp3 文件")
        return count
    except Exception as e:
        print(f"删除文件时出错：{e}")
        return 0

def update_video_task_by_video_uuid(video_uuid, video_oss_url):
    api_url = "http://xxx.com/local/update_task"

def rest_update_task(video_uuid, video_oss_url, cover_img):
    print("rest_update_task, video_uuid="+str(video_uuid) + "video_url="+str(video_oss_url) + "cover_img="+str(cover_img))
    api_url = "http://xxx.com/local/update_task"
    try:
        payload = {
            "video_oss_url": video_oss_url,
            "video_uuid": video_uuid,
            "cover_img": cover_img
        }

        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            return response.json()  # 如果接口返回 JSON 数据，你可能需要根据实际情况进行处理
        else:
            print(f"远程更新任务失败，HTTP 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"远程更新任务失败: {e}")
        return False

def excute_task():
    ## 清除目录的音频；
    # delete_mp3_files_in_directory("G:\\2013VS\\digital-wavlipgfp\\inputs\\test\\source_audio")
    delete_mp3_files_in_directory(blue_oldman_audio_root_path)
    delete_mp3_files_in_directory(blue_oldman_glasses_audio_root_path)
    delete_mp3_files_in_directory(glasses_oldman_audio_root_path)
    delete_mp3_files_in_directory(franklin_audio_root_path)
    ## 下载等待制作的音频
    task_list_info = fetch_video_list_and_download_audio()
    print("task_list_info="+str(task_list_info))
    return task_list_info

#excute_task()

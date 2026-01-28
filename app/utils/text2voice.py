# -*- coding: utf-8 -*-
# 腾讯云TTS API客户端完整封装
# 支持语音合成任务创建和状态查询

import os
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime, timezone
if sys.version_info[0] <= 2:
    from httplib import HTTPSConnection
else:
    from http.client import HTTPSConnection

import requests
from urllib.parse import urlparse
import tempfile
import os



class TencentCloudTTSClient:
    """
    腾讯云语音合成(TTS)API客户端
    封装了任务创建和状态查询的完整功能
    """
    
    def __init__(self, secret_id=None, secret_key=None, token="", region="ap-shanghai"):
        """
        初始化TTS客户端
        
        Args:
            secret_id: 腾讯云SecretId，从环境变量TENCENTCLOUD_SECRET_ID读取
            secret_key: 腾讯云SecretKey，从环境变量TENCENTCLOUD_SECRET_KEY读取
            token: 临时安全令牌，默认为空
            region: 地域参数，默认ap-shanghai
        """
        self.secret_id = secret_id or os.getenv("TENCENTCLOUD_SECRET_ID")
        self.secret_key = secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY")
        self.token = token
        self.region = region
        self.service = "tts"
        self.host = "tts.tencentcloudapi.com"
        self.version = "2019-08-23"
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("SecretId和SecretKey必须提供，可通过参数传入或设置环境变量TENCENTCLOUD_SECRET_ID和TENCENTCLOUD_SECRET_KEY")
    
    def _sign(self, key, msg):
        """HMAC-SHA256签名工具方法"""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    
    def _generate_signature(self, action, payload, timestamp=None):
        """
        生成TC3-HMAC-SHA256签名
        
        Args:
            action: 接口动作，如CreateTtsTask或DescribeTtsTaskStatus
            payload: 请求参数，JSON字符串
            timestamp: 时间戳，默认为当前时间
            
        Returns:
            dict: 包含签名和请求头信息的字典
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        #date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
        algorithm = "TC3-HMAC-SHA256"
        
        # ************* 步骤 1：拼接规范请求串 *************
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (
            ct, self.host, action.lower())
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        canonical_request = (http_request_method + "\n" +
                           canonical_uri + "\n" +
                           canonical_querystring + "\n" +
                           canonical_headers + "\n" +
                           signed_headers + "\n" +
                           hashed_request_payload)
        
        # ************* 步骤 2：拼接待签名字符串 *************
        credential_scope = date + "/" + self.service + "/" + "tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (algorithm + "\n" +
                         str(timestamp) + "\n" +
                         credential_scope + "\n" +
                         hashed_canonical_request)
        
        # ************* 步骤 3：计算签名 *************
        secret_date = self._sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = self._sign(secret_date, self.service)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        
        # ************* 步骤 4：拼接 Authorization *************
        authorization = (algorithm + " " +
                        "Credential=" + self.secret_id + "/" + credential_scope + ", " +
                        "SignedHeaders=" + signed_headers + ", " +
                        "Signature=" + signature)
        
        # 构造请求头
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version
        }
        
        if self.region:
            headers["X-TC-Region"] = self.region
        if self.token:
            headers["X-TC-Token"] = self.token
        
        return {
            "headers": headers,
            "payload": payload,
            "timestamp": timestamp,
            "authorization": authorization
        }
    
    def _call_api(self, action, payload):
        """
        调用腾讯云TTS API接口
        
        Args:
            action: 接口动作
            payload: 请求参数，字典或JSON字符串
            
        Returns:
            dict: API响应结果解析后的字典
        """
        # 确保payload是JSON字符串
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False)
        
        # 生成签名和请求头
        signature_info = self._generate_signature(action, payload)
        
        try:
            # 发送请求
            conn = HTTPSConnection(self.host)
            conn.request("POST", "/", 
                        body=payload.encode("utf-8"), 
                        headers=signature_info["headers"])
            response = conn.getresponse()
            result_data = response.read().decode("utf-8")
            conn.close()
            
            # 解析JSON响应
            return json.loads(result_data)
            
        except Exception as e:
            raise Exception(f"TTS API调用失败: {str(e)}")
    
    def create_tts_task(self, text, voice_type=1, codec="mp3", 
                       speed=0, volume=0, sample_rate=16000, model_type=1):
        """
        创建语音合成任务
        
        Args:
            text: 要合成的文本，最大300字符
            voice_type: 音色类型(0:女声1, 1:男声1, 2:男声2, 3:女声2, 4:童声)
            codec: 音频编码(mp3, pcm)
            speed: 语速范围[-2, 2]，默认0
            volume: 音量范围[-6, 6]，默认0
            sample_rate: 采样率(16000, 8000)
            model_type: 模型类型(1:默认, 3:精品)
            
        Returns:
            dict: 任务创建响应，包含TaskId等信息
        """
        payload = {
            "Text": text,
            "VoiceType": voice_type,
            "Codec": codec,
            "SampleRate": sample_rate,
            "Speed": speed,
            "Volume": volume,
            "ModelType": model_type
        }
        
        return self._call_api("CreateTtsTask", payload)
    
    def describe_tts_task_status(self, task_id):
        """
        查询语音合成任务状态
        
        Args:
            task_id: 任务ID，从create_tts_task返回结果中获取
            
        Returns:
            dict: 任务状态信息，包含任务状态、结果URL等
        """
        payload = {
            "TaskId": task_id
        }
        
        return self._call_api("DescribeTtsTaskStatus", payload)
    
    def text_to_speech(self, text, voice_type=1, codec="mp3", 
                      wait_for_complete=True, check_interval=1, timeout=60):
        """
        文本转语音的便捷方法，支持同步等待任务完成
        
        Args:
            text: 要合成的文本
            voice_type: 音色类型
            codec: 音频编码
            wait_for_complete: 是否等待任务完成
            check_interval: 检查间隔(秒)
            timeout: 超时时间(秒)
            
        Returns:
            dict: 最终的任务结果，包含音频URL
        """
        # if session_id is None:
        #     session_id = f"session_{int(time.time())}"
        
        # 创建任务
        create_result = self.create_tts_task(
            text=text,
            voice_type=voice_type,
            codec=codec
        )
        
        # 检查创建结果
        if create_result.get("Response", {}).get("Error"):
            return create_result
        
        task_id = create_result["Response"]["Data"]["TaskId"]
        
        # 如果不等待完成，直接返回创建结果
        if not wait_for_complete:
            return create_result
        
        # 等待任务完成
        start_time = time.time()
        while time.time() - start_time < timeout:
            status_result = self.describe_tts_task_status(task_id)
            
            if status_result.get("Response", {}).get("Error"):
                return status_result
            
            task_status = status_result["Response"]["Data"]["Status"]
            
            if task_status == 2:  # 任务成功
                return status_result
            elif task_status == 3:  # 任务失败
                return status_result
            
            #time.sleep(check_interval)
            time.sleep(0.5)
         
        # 超时处理
        raise TimeoutError(f"TTS任务执行超时，任务ID: {task_id}")



    def download_audio_data(self, result_url, timeout=30):
        """
        从ResultUrl下载音频数据
        
        Args:
            result_url: 音频文件的URL地址
            timeout: 下载超时时间(秒)，默认30秒
            
        Returns:
            dict: 包含下载结果和音频数据的字典
                - success: 是否下载成功
                - audio_data: 音频二进制数据(成功时)
                - error_message: 错误信息(失败时)
                - file_size: 文件大小(字节)
                - content_type: 内容类型
        """
        if not result_url:
            return {
                "success": False,
                "error_message": "ResultUrl为空，无法下载音频数据"
            }
        
        try:
            # 验证URL格式
            parsed_url = urlparse(result_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return {
                    "success": False, 
                    "error_message": f"无效的音频URL: {result_url}"
                }
            
            # 设置请求头，模拟浏览器请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "audio/*, */*",
                "Referer": "https://cloud.tencent.com/"
            }
            
            # 发送GET请求下载音频数据
            response = requests.get(
                result_url, 
                headers=headers, 
                timeout=timeout,
                stream=True  # 支持流式下载，避免大文件内存溢出
            )
            
            # 检查响应状态
            if response.status_code != 200:
                return {
                    "success": False,
                    "error_message": f"下载失败，HTTP状态码: {response.status_code}"
                }
            
            # 获取音频数据并进行base64编码，解决JSON序列化问题
            import base64
            audio_data_bytes = response.content
            audio_data = base64.b64encode(audio_data_bytes).decode('utf-8')  # 转换为base64字符串
            content_type = response.headers.get('Content-Type', 'audio/mpeg')
            file_size = len(audio_data_bytes)
            
            if file_size == 0:
                return {
                    "success": False,
                    "error_message": "下载的音频数据为空"
                }
            
            return {
                "success": True,
                "audio_data": audio_data,  # 已base64编码的音频数据
                "file_size": file_size,
                "content_type": content_type,
                "audio_encoding": "base64",  # 添加编码格式标识
                "error_message": None
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error_message": f"下载超时，超过{timeout}秒"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error_message": "网络连接错误，请检查网络连接"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error_message": f"下载请求异常: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": f"下载过程发生未知错误: {str(e)}"
            }
    
    def download_audio_to_file(self, result_url, file_path=None, timeout=30):
        """
        下载音频数据并保存到文件
        
        Args:
            result_url: 音频文件的URL地址
            file_path: 保存文件路径，如果为None则生成临时文件
            timeout: 下载超时时间(秒)
            
        Returns:
            dict: 包含保存结果信息的字典
                - success: 是否成功
                - file_path: 保存的文件路径
                - error_message: 错误信息
                - file_size: 文件大小
        """
        # 下载音频数据
        download_result = self.download_audio_data(result_url, timeout)
        
        if not download_result["success"]:
            return download_result
        
        try:
            # 确定文件路径
            if file_path is None:
                # 根据内容类型确定文件扩展名
                content_type = download_result.get("content_type", "audio/mpeg")
                if "mp3" in content_type or "mpeg" in content_type:
                    ext = ".mp3"
                elif "wav" in content_type:
                    ext = ".wav"
                elif "pcm" in content_type:
                    ext = ".pcm"
                else:
                    ext = ".audio"
                
                # 创建临时文件
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=ext, 
                    delete=False,
                    prefix="tts_audio_"
                )
                file_path = temp_file.name
                temp_file.close()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入文件
            with open(file_path, 'wb') as f:
                f.write(download_result["audio_data"])
            
            return {
                "success": True,
                "file_path": file_path,
                "file_size": download_result["file_size"],
                "content_type": download_result["content_type"],
                "error_message": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error_message": f"文件保存失败: {str(e)}"
            }
    



    def text_to_speech_with_audio_data(self, text, voice_type=1, codec="mp3", 
                                      wait_for_complete=True, check_interval=2, 
                                      timeout=60, download_timeout=30):
        """
        文本转语音的增强方法，同步返回音频数据
        
        Args:
            text: 要合成的文本
            voice_type: 音色类型
            codec: 音频编码
            wait_for_complete: 是否等待任务完成
            check_interval: 状态检查间隔(秒)
            timeout: 任务超时时间(秒)
            download_timeout: 下载超时时间(秒)
            
        Returns:
            dict: 完整的合成结果，包含音频数据
        """
        # 调用原有的文本转语音方法
        tts_result = self.text_to_speech(
            text=text,
            voice_type=voice_type,
            codec=codec,
            wait_for_complete=wait_for_complete,
            check_interval=check_interval,
            timeout=timeout
        )
        
        # 检查任务是否成功完成
        if (tts_result.get("Response", {}).get("Error") or 
            tts_result.get("Response", {}).get("Data", {}).get("Status") != 2):
            # 任务失败或未完成，直接返回原结果
            tts_result["audio_data"] = None
            tts_result["audio_download_success"] = False
            return tts_result
        
        # 获取音频URL并下载
        result_url = tts_result["Response"]["Data"].get("ResultUrl")
        if not result_url:
            tts_result["audio_data"] = None
            tts_result["audio_download_success"] = False
            tts_result["download_error"] = "ResultUrl为空"
            return tts_result
        
        # 下载音频数据
        download_result = self.download_audio_data(result_url, download_timeout)
        
        # 将下载结果合并到返回数据中
        tts_result.update(download_result)
        tts_result["audio_download_success"] = download_result["success"]
        
        return tts_result


    




def main1():
    """
    演示TencentCloudTTSClient的使用方法
    测试文本转语音接口的创建任务、查询状态和等待完成功能
    """
    try:
        # 初始化TTS客户端
        print("初始化TencentCloudTTSClient...")
        # 注意：确保已设置环境变量 TENCENTCLOUD_SECRET_ID 和 TENCENTCLOUD_SECRET_KEY
        client = TencentCloudTTSClient(
            # secret_id="your_secret_id",  # 可选：直接传入
            # secret_key="your_secret_key"  # 可选：直接传入
            region="ap-shanghai"
        )
        print("客户端初始化成功！")
        
        # 测试1: 创建TTS任务
        print("\n===== 测试1: 创建TTS任务 =====")
        test_text = "你好，这是一个腾讯云语音合成服务的测试示例。"
        print(f"待转换文本: {test_text}")
        
        create_result = client.create_tts_task(
            text=test_text,
            voice_type=101008,  # 女声
            codec="mp3",
            speed=0,
            volume=0,
            sample_rate=16000,
            model_type=1
        )
        
        print("\n创建任务响应结果：")
        print(json.dumps(create_result, ensure_ascii=False, indent=2))
        
        # 检查任务创建是否成功
        if "Response" in create_result and "Error" not in create_result["Response"]:
            task_id = create_result["Response"].get("Data", {}).get("TaskId")
            if task_id:
                print(f"\n任务创建成功！任务ID: {task_id}")
                
                # 测试2: 查询任务状态
                print("\n===== 测试2: 查询任务状态 =====")
                status_result = client.describe_tts_task_status(task_id)
                print("查询任务状态结果：")
                print(json.dumps(status_result, ensure_ascii=False, indent=2))
                
                # 测试3: 使用便捷方法（同步等待完成）
                print("\n===== 测试3: 便捷方法 - 同步等待完成 =====")
                print("开始执行文本转语音（同步等待完成）...")
                try:
                    result = client.text_to_speech(
                        text=test_text,
                        voice_type=101008,
                        codec="mp3",
                        wait_for_complete=True,
                        check_interval=2,
                        timeout=60
                    )
                    
                    print("\n文本转语音完成，最终结果：")
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    
                    # 检查是否成功生成音频URL
                    if "Response" in result and "Error" not in result["Response"]:
                        task_status = result["Response"].get("Data", {}).get("Status")
                        if task_status == 2:  # 任务成功
                            audio_url = result["Response"].get("Data", {}).get("ResultUrl")
                            if audio_url:
                                print(f"\n✅ 语音合成成功！音频URL: {audio_url}")
                            else:
                                print("\n❌ 语音合成成功，但未获取到音频URL")
                        else:
                            print(f"\n❌ 语音合成任务状态: {task_status}")
                except TimeoutError as e:
                    print(f"\n⚠️ {str(e)}")
                except Exception as e:
                    print(f"\n❌ 便捷方法调用失败: {str(e)}")
            else:
                print("\n❌ 任务创建成功但未获取到TaskId")
        else:
            error_msg = create_result.get("Response", {}).get("Error", {}).get("Message", "未知错误")
            print(f"\n❌ 任务创建失败: {error_msg}")
            
    except ValueError as e:
        print(f"初始化失败: {str(e)}")
        print("\n解决方法：")
        print("1. 设置环境变量 TENCENTCLOUD_SECRET_ID 和 TENCENTCLOUD_SECRET_KEY")
        print("2. 或者在初始化TencentCloudTTSClient时直接传入secret_id和secret_key参数")
    except Exception as e:
        print(f"执行失败: {str(e)}")


def main():
    """
    演示增强的TencentCloudTTSClient使用方法
    包括音频数据下载功能
    """
    try:
        # 初始化TTS客户端
        print("初始化TencentCloudTTSClient...")
        client = TencentCloudTTSClient(region="ap-shanghai")
        print("客户端初始化成功！")
        
        # 使用增强方法：直接获取音频数据
        print("\n===== 测试增强方法：文本转语音并下载音频数据 =====")
        test_text = "你好，这是一个腾讯云语音合成服务的测试示例，现在支持直接下载音频数据。"
        print(f"待转换文本: {test_text}")
        
        try:
            result = client.text_to_speech_with_audio_data(
                text=test_text,
                voice_type=101008,
                codec="mp3",
                wait_for_complete=True,
                timeout=60,
                download_timeout=30
            )
            
            if result.get("audio_download_success"):
                audio_data = result.get("audio_data")
                file_size = result.get("file_size", 0)
                content_type = result.get("content_type", "unknown")
                
                print(f"✅ 语音合成并下载成功！")
                print(f"   音频大小: {file_size} 字节")
                print(f"   内容类型: {content_type}")
                print(f"   音频数据前100字节: {audio_data[:100].hex()}...")
                
                # 保存到文件示例
                save_result = client.download_audio_to_file(
                    result_url=result["Response"]["Data"]["ResultUrl"],
                    file_path="/home/syl/kid-english10271/teaching-agent-backend/app/utils/record"
                )
                
                if save_result["success"]:
                    print(f"   音频已保存至: {save_result['file_path']}")
                else:
                    print(f"   文件保存失败: {save_result['error_message']}")
                    
                # 此时可以将audio_data发送给前端
                # 例如：websocket.send(audio_data) 或通过HTTP响应返回
                
            else:
                print("❌ 音频下载失败")
                if result.get("error_message"):
                    print(f"   错误信息: {result['error_message']}")
                    
        except Exception as e:
            print(f"❌ 增强方法调用失败: {str(e)}")
            
    except ValueError as e:
        print(f"初始化失败: {str(e)}")
    except Exception as e:
        print(f"执行失败: {str(e)}")


if __name__ == "__main__":
    #main1()
    main()
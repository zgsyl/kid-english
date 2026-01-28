# -*- coding: utf-8 -*-
# 腾讯云API签名v3封装类
# 封装后提供更安全、易用的接口，支持多种腾讯云服务

import os
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime
import base64
if sys.version_info[0] <= 2:
    from httplib import HTTPSConnection
else:
    from http.client import HTTPSConnection


class TencentCloudAPIV3:
    """
    腾讯云API签名v3封装类
    提供安全、易用的API调用接口，支持自动签名生成
    """
    
    def __init__(self, secret_id=None, secret_key=None, token=""):
        """
        初始化腾讯云API客户端
        
        Args:
            secret_id: 腾讯云密钥ID，如为None则从环境变量读取
            secret_key: 腾讯云密钥Key，如为None则从环境变量读取
            token: 临时安全令牌，可选
        """
        self._secret_id = secret_id or os.getenv("TENCENTCLOUD_SECRET_ID")
        self._secret_key = secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY")
        self._token = token
        
        if not self._secret_id or not self._secret_key:
            raise ValueError("Secret ID和Secret Key不能为空，请设置环境变量或直接传入参数")
    
    def _sign(self, key, msg):
        """生成HMAC-SHA256签名[6](@ref)"""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    
    def _generate_authorization(self, service, host, action, payload, region="", version=""):
        """
        生成API请求的Authorization头[1](@ref)
        
        Args:
            service: 服务名称，如asr、tts等
            host: API端点主机名
            action: API动作名称
            payload: 请求参数（字典）
            region: 区域代码，可选
            version: API版本，可选
            
        Returns:
            dict: 包含所有请求头信息的字典
        """
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        payload_str = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        
        # ************* 步骤 1：拼接规范请求串 *************
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (ct, host, action.lower())
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        
        canonical_request = (http_request_method + "\n" +
                           canonical_uri + "\n" +
                           canonical_querystring + "\n" +
                           canonical_headers + "\n" +
                           signed_headers + "\n" +
                           hashed_request_payload)

        # ************* 步骤 2：拼接待签名字符串 *************
        credential_scope = date + "/" + service + "/" + "tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = ("TC3-HMAC-SHA256" + "\n" +
                         str(timestamp) + "\n" +
                         credential_scope + "\n" +
                         hashed_canonical_request)

        # ************* 步骤 3：计算签名 *************
        secret_date = self._sign(("TC3" + self._secret_key).encode("utf-8"), date)
        secret_service = self._sign(secret_date, service)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # ************* 步骤 4：拼接 Authorization *************
        authorization = ("TC3-HMAC-SHA256" + " " +
                       "Credential=" + self._secret_id + "/" + credential_scope + ", " +
                       "SignedHeaders=" + signed_headers + ", " +
                       "Signature=" + signature)

        # ************* 步骤 5：构造请求头 *************
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version
        }
        
        if region:
            headers["X-TC-Region"] = region
        if self._token:
            headers["X-TC-Token"] = self._token
            
        return headers, payload_str
    
    def call_api(self, service, host, action, payload, region="", version="2019-06-14"):
        """
        调用腾讯云API[1](@ref)
        
        Args:
            service: 服务名称，如asr、tts等
            host: API端点主机名
            action: API动作名称
            payload: 请求参数（字典）
            region: 区域代码，可选
            version: API版本，默认为2019-06-14
            
        Returns:
            str: API响应内容
        """
        try:
            headers, payload_str = self._generate_authorization(service, host, action, payload, region, version)
            
            conn = HTTPSConnection(host)
            conn.request("POST", "/", headers=headers, body=payload_str.encode("utf-8"))
            response = conn.getresponse()
            result = response.read().decode('utf-8')
            conn.close()
            
            return result
            
        except Exception as e:
            raise Exception(f"API调用失败: {str(e)}")
    
    def speech_recognition(self, audio_data, engine_model_type="16k_zh", voice_format=1, filter_dirty=0, 
                          filter_modal=0, filter_punc=0, convert_num_mode=1, word_info=0):
        """
        语音识别API的便捷方法[1](@ref)
        
        Args:
            audio_data: 音频数据（base64编码）
            engine_model_type: 引擎模型类型
            voice_format: 音频格式
            其他参数参考腾讯云语音识别API文档
            
        Returns:
            str: 识别结果
        """
        payload = {
            "EngineModelType": engine_model_type,
            "VoiceFormat": voice_format,
            "UsrAudioKey": str(int(time.time())),
            "Data": audio_data,
            "FilterDirty": filter_dirty,
            "FilterModal": filter_modal,
            "FilterPunc": filter_punc,
            "ConvertNumMode": convert_num_mode,
            "WordInfo": word_info
        }
        
        return self.call_api(
            service="asr",
            host="asr.tencentcloudapi.com",
            action="SentenceRecognition",
            payload=payload,
            version="2019-06-14"
        )
    
    @property
    def secret_id(self):
        """获取Secret ID（只读属性）[6](@ref)"""
        return self._secret_id[:8] + "****" if self._secret_id else None
    
    @property
    def has_valid_credentials(self):
        """检查凭证是否有效[8](@ref)"""
        return bool(self._secret_id and self._secret_key)


    def recognize_mp3_file(self, file_path, engine_model_type="8k_zh", SourceType=1, voice_format="mp3"):
        """
        MP3文件语音识别测试方法
        
        Args:
            file_path: MP3文件路径
            engine_model_type: 引擎模型类型，默认16k_zh（16k中文普通话）
            voice_format: 音频格式，1表示mp3
            其他参数为可选的语音识别参数
            
        Returns:
            dict: 识别结果
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"音频文件不存在: {file_path}")
            
            # 检查文件大小（一句话识别限制为600KB）
            file_size = os.path.getsize(file_path)
            if file_size > 600 * 1024:  # 600KB限制
                raise ValueError(f"文件大小超过600KB限制: {file_size/1024:.2f}KB")
            
            # 读取音频文件并转换为base64
            with open(file_path, "rb") as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            # 构建识别参数
            payload = {
                "EngSerViceType": engine_model_type,
                "SourceType": SourceType,
                "VoiceFormat": voice_format,
                "Data": audio_data,
                "DataLen": file_size,
            }
            
            print(f"开始识别MP3文件: {file_path}")
            print(f"文件大小: {file_size/1024:.2f}KB")
            print(f"使用引擎: {engine_model_type}")
            print(f"音频格式: {voice_format}")
            
            # 调用语音识别API
            result = self.call_api(
                service="asr",
                host="asr.tencentcloudapi.com",
                action="SentenceRecognition",
                payload=payload,
                version="2019-06-14"
            )
            
            return json.loads(result)
            
        except Exception as e:
            print(f"MP3文件识别失败: {str(e)}")
            return {"Error": str(e)}
    
    def recognize_pcm_base64(self, pcm_base64_data, engine_model_type="16k_zh", voice_format="pcm", 
                            sample_rate=16000, channels=1, bits_per_sample=16):
        """
        识别base64编码的PCM音频数据
        
        Args:
            pcm_base64_data: base64编码的PCM音频数据字符串
            engine_model_type: 引擎模型类型，默认16k_zh（16k中文普通话）
            voice_format: 音频格式，默认为pcm
            sample_rate: 采样率，默认16000Hz
            channels: 声道数，默认1（单声道）
            bits_per_sample: 位深度，默认16位
            
        Returns:
            dict: 识别结果，包含识别的文字和相关信息
        """
        try:
            # 验证输入参数
            if not pcm_base64_data:
                raise ValueError("PCM数据不能为空")
            
            # 解码base64数据以获取实际数据长度
            try:
                pcm_bytes = base64.b64decode(pcm_base64_data)
                data_length = len(pcm_bytes)
            except Exception as e:
                raise ValueError(f"Base64解码失败: {str(e)}")
            
            # 检查数据大小（一句话识别限制为600KB）
            if data_length > 600 * 1024:  # 600KB限制
                raise ValueError(f"PCM数据大小超过600KB限制: {data_length/1024:.2f}KB")
            
            print(f"开始识别PCM音频数据")
            print(f"数据大小: {data_length/1024:.2f}KB")
            print(f"使用引擎: {engine_model_type}")
            print(f"音频格式: {voice_format}")
            print(f"采样率: {sample_rate}Hz")
            print(f"声道数: {channels}")
            print(f"位深度: {bits_per_sample}位")
            
            # 构建识别参数
            payload = {
                "EngSerViceType": engine_model_type,
                "SourceType": 1,  # 1表示语音数据
                "VoiceFormat": voice_format,
                "Data": pcm_base64_data,
                "DataLen": data_length
                # PCM格式的额外参数
                # "SampleRate": sample_rate,
                # "ChannelNum": channels,
                # "BitsPerSample": bits_per_sample
            }
            
            # 调用语音识别API
            result = self.call_api(
                service="asr",
                host="asr.tencentcloudapi.com",
                action="SentenceRecognition",
                payload=payload,
                version="2019-06-14"
            )
            
            response_data = json.loads(result)
            
            # 解析识别结果
            if "Response" in response_data:
                response = response_data["Response"]
                
                if "Result" in response:
                    # 识别成功
                    recognition_result = response["Result"]
                    print("✅ PCM音频识别成功！")
                    print(f"📝 识别结果: {recognition_result}")
                    
                    return {
                        "success": True,
                        "text": recognition_result,
                        "request_id": response.get("RequestId", ""),
                        "data_size": data_length,
                        "audio_info": {
                            "format": voice_format,
                            "sample_rate": sample_rate,
                            "channels": channels,
                            "bits_per_sample": bits_per_sample
                        }
                    }
                else:
                    # 识别失败，返回错误信息
                    error_info = response.get("Error", {})
                    error_code = error_info.get("Code", "Unknown")
                    error_message = error_info.get("Message", "未知错误")
                    
                    print(f"❌ PCM音频识别失败: {error_message}")
                    print(f"🔧 错误代码: {error_code}")
                    
                    return {
                        "success": False,
                        "error_code": error_code,
                        "error_message": error_message,
                        "request_id": response.get("RequestId", ""),
                        "data_size": data_length
                    }
            else:
                raise Exception("API响应格式异常")
            
        except Exception as e:
            error_msg = f"PCM音频识别失败: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error_message": error_msg,
                "error_code": "PROCESSING_ERROR"
            }


# 使用示例
def main():
    """
    腾讯云语音识别API测试示例
    """
    print("=== 腾讯云语音识别API测试 ===")
    
    # 1. 创建API客户端实例
    try:
        client = TencentCloudAPIV3()
        print("✅ API客户端创建成功")
        print(f"✅ 凭证状态: {'有效' if client.has_valid_credentials else '无效'}")
    except Exception as e:
        print(f"❌ 客户端创建失败: {e}")
        print("请检查环境变量 TENCENTCLOUD_SECRET_ID 和 TENCENTCLOUD_SECRET_KEY 是否设置正确")
        return
    
    # 2. 测试用例1: 直接测试API连通性
    # print("\n--- 测试1: API连通性测试 ---")
    # try:
    #     test_payload = {
    #         "EngSerViceType": "8k_zh",
    #         "SourceType": 1,
    #         "VoiceFormat": "mp3"
    #     }
        
    #     # 快速测试API调用
    #     result = client.call_api(
    #         service="asr",
    #         host="asr.tencentcloudapi.com",
    #         action="SentenceRecognition", 
    #         payload=test_payload,
    #         version="2019-06-14"
    #     )
        
    #     response_data = json.loads(result)
    #     if "Response" in response_data:
    #         print("✅ API连通性测试成功")
    #         print(f"响应内容: {result}")
    #         print(f"✅ 请求ID: {response_data['Response'].get('RequestId', '未知')}")
    #     else:
    #         print("❌ API响应格式异常")
    #         print(f"响应内容: {result}")
            
    # except Exception as e:
    #     print(f"❌ API连通性测试失败: {e}")
    
    # 3. 测试用例2: MP3文件识别测试
    print("\n--- 测试2: MP3文件识别测试 ---")
    
    # 这里替换为您实际的MP3文件路径
    test_mp3_path = "test.mp3"  # 修改为您的MP3文件路径
    
    # 检查测试文件是否存在，如果不存在则创建一个模拟测试
    if not os.path.exists(test_mp3_path):
        print(f"⚠️  测试文件 {test_mp3_path} 不存在，进行模拟API调用测试")
           
    else:
        # 实际MP3文件测试
        try:
            result = client.recognize_mp3_file(test_mp3_path)
            
            if "Response" in result:
                response_data = result["Response"]
                
                if "Result" in response_data:
                    # 识别成功
                    recognition_result = response_data["Result"]
                    print("✅ 语音识别成功！")
                    print(f"📝 识别结果: {recognition_result}")
                else:
                    # 显示错误信息
                    error_info = response_data.get("Error", {})
                    print(f"❌ 识别失败: {error_info.get('Message', '未知错误')}")
                    print(f"🔧 错误代码: {error_info.get('Code', '未知')}")
                
                print(f"📋 请求ID: {response_data.get('RequestId', '未知')}")
                
            else:
                print("❌ 响应格式异常")
                print(f"完整响应: {result}")
                
        except Exception as e:
            print(f"❌ MP3文件识别测试失败: {e}")
    

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
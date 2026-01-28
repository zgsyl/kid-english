# -*- coding: utf-8 -*-
# 腾讯云API签名v3封装类
# 封装成类便于重复使用和管理

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


class TencentCloudAPIClient:
    """
    腾讯云API客户端封装类
    提供统一的API调用接口，支持TC3-HMAC-SHA256签名算法
    """
    
    def __init__(self, secret_id=None, secret_key=None, token="", region=""):
        """
        初始化腾讯云API客户端
        
        Args:
            secret_id: 腾讯云SecretId，从环境变量TENCENTCLOUD_SECRET_ID读取
            secret_key: 腾讯云SecretKey，从环境变量TENCENTCLOUD_SECRET_KEY读取
            token: 临时安全令牌，默认为空
            region: 地域参数，默认为空
        """
        self.secret_id = secret_id or os.getenv("TENCENTCLOUD_SECRET_ID")
        self.secret_key = secret_key or os.getenv("TENCENTCLOUD_SECRET_KEY")
        self.token = token
        self.region = region
        
        if not self.secret_id or not self.secret_key:
            raise ValueError("SecretId和SecretKey必须提供，可通过参数传入或设置环境变量")
    
    def sign(self, key, msg):
        """HMAC-SHA256签名工具方法"""
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    
    def generate_signature(self, service, host, action, version, payload, timestamp=None):
        """
        生成TC3-HMAC-SHA256签名
        
        Args:
            service: 服务名，如tts
            host: 接口域名，如tts.tencentcloudapi.com
            action: 接口动作，如CreateTtsTask
            version: API版本，如2019-08-23
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
            ct, host, action.lower())
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        canonical_request = (http_request_method + "\n" +
                           canonical_uri + "\n" +
                           canonical_querystring + "\n" +
                           canonical_headers + "\n" +
                           signed_headers + "\n" +
                           hashed_request_payload)
        
        # ************* 步骤 2：拼接待签名字符串 *************
        credential_scope = date + "/" + service + "/" + "tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (algorithm + "\n" +
                         str(timestamp) + "\n" +
                         credential_scope + "\n" +
                         hashed_canonical_request)
        
        # ************* 步骤 3：计算签名 *************
        secret_date = self.sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = self.sign(secret_date, service)
        secret_signing = self.sign(secret_service, "tc3_request")
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
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version
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
    
    def call_api(self, service, host, action, version, payload, method="POST"):
        """
        调用腾讯云API接口
        
        Args:
            service: 服务名
            host: 接口域名
            action: 接口动作
            version: API版本
            payload: 请求参数，字典或JSON字符串
            method: HTTP方法，默认为POST
            
        Returns:
            str: API响应内容
        """
        # 确保payload是JSON字符串
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False)
        
        # 生成签名和请求头
        signature_info = self.generate_signature(service, host, action, version, payload)
        
        try:
            # 发送请求
            conn = HTTPSConnection(host)
            conn.request(method, "/", 
                        body=payload.encode("utf-8"), 
                        headers=signature_info["headers"])
            response = conn.getresponse()
            result = response.read().decode("utf-8")
            conn.close()
            
            return result
            
        except Exception as e:
            raise Exception(f"API调用失败: {str(e)}")
    
    def tts_create_task(self, text, voice_type=1, codec="mp3", speed=0, volume=0):
        """
        创建TTS任务的便捷方法[1](@ref)
        
        Args:
            text: 要合成的文本
            session_id: 会话ID
            voice_type: 音色类型，默认为1
            codec: 音频编码，默认为mp3
            speed: 语速，默认为0
            volume: 音量，默认为0
            
        Returns:
            str: API响应结果
        """
        payload = {
            "Text": text,
            "VoiceType": voice_type,
            "Codec": codec,
            "Speed": speed,
            "Volume": volume
        }
        
        return self.call_api(
            service="tts",
            host="tts.tencentcloudapi.com",
            action="CreateTtsTask",
            version="2019-08-23",
            payload=payload
        )


def main():
    """
    演示文本转语音接口调用的主函数
    """
    try:
        # 初始化API客户端
        # 注意：需要确保设置了正确的环境变量 TENCENTCLOUD_SECRET_ID 和 TENCENTCLOUD_SECRET_KEY
        # 或者直接传入这些参数
        client = TencentCloudAPIClient(
            # secret_id="your_secret_id",  # 可选：直接传入
            # secret_key="your_secret_key"  # 可选：直接传入
        )
        
        # 准备要转换的文本
        text = "你好，这是一个文本转语音的测试示例。"
        
        print(f"开始调用腾讯云TTS接口...")
        print(f"待转换文本: {text}")
        
        # 调用TTS接口
        response = client.tts_create_task(
            text=text,
            voice_type=101008,  # 标准女声
            codec="mp3",
            speed=0,  # 默认语速
            volume=0  # 默认音量
        )
        
        # 解析并打印响应结果
        response_data = json.loads(response)
        print("\nAPI调用成功，响应结果：")
        print(json.dumps(response_data, ensure_ascii=False, indent=2))
        
        # 检查API调用是否成功
        if "Response" in response_data:
            # 检查是否包含Error字段
            if "Error" in response_data["Response"]:
                print(f"\n错误信息: {response_data['Response']['Error']['Message']}")
            # 检查是否包含RequestId和Data中的TaskId
            elif "RequestId" in response_data["Response"] and "Data" in response_data["Response"]:
                task_id = response_data["Response"]["Data"].get("TaskId")
                if task_id:
                    print("\n文本转语音任务创建成功！")
                    print(f"请求ID: {response_data['Response']['RequestId']}")
                    print(f"任务ID: {task_id}")
                else:
                    print(f"\nAPI响应中未找到TaskId")
            else:
                print(f"\nAPI响应格式不符合预期")
        else:
            print(f"\nAPI响应格式不符合预期")
    
    except Exception as e:
        print(f"调用失败: {str(e)}")
        # 打印错误详情和解决方案提示
        if "SecretId和SecretKey必须提供" in str(e):
            print("\n解决方法：")
            print("1. 设置环境变量 TENCENTCLOUD_SECRET_ID 和 TENCENTCLOUD_SECRET_KEY")
            print("2. 或者在初始化TencentCloudAPIClient时直接传入secret_id和secret_key参数")
        elif "API调用失败" in str(e):
            print("\n可能的原因：")
            print("1. 网络连接问题")
            print("2. API密钥无效或权限不足")
            print("3. 请求参数格式错误")


if __name__ == "__main__":
    main()



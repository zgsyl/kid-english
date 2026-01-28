import requests
import json

# 测试配置
BASE_URL = "http://localhost:8000/api/v1/users"

def test_user_registration():
    """测试用户注册"""
    
    test_cases = [
        {
            "name": "正常注册",
            "data": {
                "wechat_openid": "wx_test_normal_001",
                "nickname": "正常宝宝",
                "age": 5,
                "avatar_url": "https://example.com/avatar/normal.jpg"
            },
            "expected_status": 201
        },
        {
            "name": "最小化注册", 
            "data": {
                "wechat_openid": "wx_test_minimal_001",
                "nickname": "最小用户"
            },
            "expected_status": 201
        },
        {
            "name": "重复注册",
            "data": {
                "wechat_openid": "wx_test_duplicate_001", 
                "nickname": "第一次注册"
            },
            "expected_status": 201
        },
        {
            "name": "缺失必填字段",
            "data": {
                "nickname": "缺失openid用户",
                "age": 5
            },
            "expected_status": 422  # 验证错误
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n=== 测试用例 {i+1}: {test_case['name']} ===")
        
        try:
            response = requests.post(
                f"{BASE_URL}/register",
                json=test_case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")
            
            if response.status_code == test_case["expected_status"]:
                print("✅ 测试通过")
            else:
                print("❌ 测试失败")
                
            if response.status_code == 201:
                user_data = response.json()
                print(f"注册成功 - 用户ID: {user_data.get('id')}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")

def test_duplicate_registration():
    """测试重复注册行为"""
    print("\n=== 测试重复注册 ===")
    
    test_openid = "wx_dup_test_123"
    
    # 第一次注册
    response1 = requests.post(
        f"{BASE_URL}/register",
        json={
            "wechat_openid": test_openid,
            "nickname": "原始昵称",
            "age": 5
        }
    )
    print(f"第一次注册 - 状态码: {response1.status_code}")
    if response1.status_code == 201:
        user1 = response1.json()
        print(f"第一次注册用户: {user1['nickname']}")
    
    # 第二次注册（相同openid，不同信息）
    response2 = requests.post(
        f"{BASE_URL}/register", 
        json={
            "wechat_openid": test_openid,
            "nickname": "更新昵称",  # 昵称不同
            "age": 6,  # 年龄不同
            "avatar_url": "https://new.avatar.url"  # 头像不同
        }
    )
    print(f"第二次注册 - 状态码: {response2.status_code}")
    if response2.status_code == 200 or response2.status_code == 201:
        user2 = response2.json()
        print(f"第二次注册结果: {user2['nickname']} (年龄: {user2.get('age')})")
        print("注意：这里应该返回现有用户，可能更新了信息")

if __name__ == "__main__":
    test_user_registration()
    #test_duplicate_registration()
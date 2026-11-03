import requests

# 모든 KIS HTTP 호출의 (connect, read) 타임아웃. 주문 POST 타임아웃은
# "상태 불명"으로 취급한다(접수됐을 수 있으므로 자동 재시도 금지).
REQ_TIMEOUT = (5.0, 30.0)

import json
 
APP_KEY = ""
APP_SECRET = ""
ACCESS_TOKEN = ""
URL_BASE = "https://openapi.koreainvestment.com:9443" #실전투자

# Auth
def auth():
    headers = {"content-type":"application/json"}
    body = {
        "grant_type":"client_credentials",
        "appkey":APP_KEY, 
        "appsecret":APP_SECRET
        }
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body), timeout=REQ_TIMEOUT)
    
    global ACCESS_TOKEN
    ACCESS_TOKEN = res.json()["access_token"]

# 주식현재가 시세
def get_current_price(stock_no):
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"

    # 헤더 설정
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"FHKST01010100"}

    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd": stock_no
    }

    # 호출
    res = requests.get(URL, headers=headers, params=params, timeout=REQ_TIMEOUT)

    if res.status_code == 200 and res.json()["rt_cd"] == "0" :
        return(res.json())
    # 토큰 만료 시
    elif res.status_code == 200 and res.json()["msg_cd"] == "EGW00123" :
        auth()
        get_current_price(stock_no)
    else:
        print("Error Code : " + str(res.status_code) + " | " + res.text)
        return None

get_current_price("005930")

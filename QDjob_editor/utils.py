import re, time
import requests
from enctrypt_qidian import *
from logger import LoggerManager

# 安全获取已配置的logger实例
try:
    logger = LoggerManager().logger
except RuntimeError:
    logger = LoggerManager().setup_basic_logger()
    logger.info("utils模块: 初始化日志系统")

def check_user_status(tokenid, usertype):
    '''检查用户状态'''
    url = 'https://janiquiz.dpdns.org/user/status'
    params = {
        'tokenid': tokenid,
        'usertype': usertype
    }
    response = requests.get(url, params=params)
    res_text = response.text
    logger.info(f"[check_user_status] 响应: {res_text}")
    res = response.json()
    if response.status_code != 200:
        logger.error(f"[check_user_status] 获取用户状态失败")
        return None
    logger.info(f"[check_user_status] 获取用户状态成功")
    return res

def solve_user(user_agent, cookies):
    '''处理用户数据'''
    # 初始化参数
    match = re.search(r'QDReaderAndroid/(\d+\.\d+\.\d+)/(\d+)/', user_agent)
    if match:
        version = match.group(1)
        versioncode = match.group(2)
        
        if not version: 
            logger.error('无法获取版本号，请检查UA')
            return False
        logger.info(f'当前UA版本：{version}')

        if not versioncode: 
            logger.error('无法获取版本编号，请检查UA')
            return False
        logger.info(f'当前UA版本编号：{versioncode}')
    else:
        logger.error('无法匹配User-Agent格式，请检查UA内容')
        return False
    
    qid = cookies.get('qid', '')
    if not qid: 
        logger.error('无法获取qid，请检查Cookies')
        return False
    QDInfo = cookies.get('QDInfo', '')
    if not QDInfo: 
        logger.error('无法获取QDInfo，请检查Cookies')
        return False
    userid = getuserid_from_QDInfo(QDInfo)

    user_data = {
        'version': version,
        'versioncode': versioncode,
        'qid': qid,
        'QDInfo': QDInfo,
        'userid': userid,
        'user_agent': user_agent,
        'cookies': cookies,
    }
    return user_data
    
def check_login_status(user_agent, cookies):
    '''检查登录状态'''
    user_data = solve_user(user_agent, cookies)
    if not user_data: 
        logger.error('无法处理用户数据，请检查Cookies')
        return False
    version = user_data.get('version', '')
    versioncode = user_data.get('versioncode', '')
    qid = user_data.get('qid', '')
    QDInfo = user_data.get('QDInfo', '')
    userid = user_data.get('userid', '')

    url = 'https://druidv6.if.qidian.com/argus/api/v1/user/getprofile'
    headers = {
        'Cache-Control': 'max-stale=0',
        'tstamp': '',
        'QDInfo': '',
        'User-Agent': user_agent,
        'QDSign': '',
        'Host': 'druidv6.if.qidian.com',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }
    params = {}
    ts = str(int(time.time() * 1000))
    params_encrypt = {}
    QDSign = getQDSign(ts, params_encrypt, version, qid, userid=userid)
    QDInfo = getQDInfo_byQDInfo(ts, QDInfo)
    borgus = getborgus(ts, params_encrypt, versioncode, qid)
    headers.update({
        'tstamp': ts,
        'QDInfo': QDInfo,
        'QDSign': QDSign,
        'borgus': borgus
    })
    cookies['QDInfo'] = QDInfo

    try:
        response = requests.get(url, params=params, cookies=cookies, headers=headers)
        res_text = response.text
        logger.info(f"[check_login_status] 登录检测: {res_text}")
        result = response.json()
        
        if result.get('Data', {}).get('Nickname'):
            nickname = result['Data']['Nickname']
            logger.info(f"[check_login_status] 登录成功: {nickname}")
            return True
        return False
    except Exception as e:
        logger.error(f"登录检测异常: {e}")
        return False
    
def check_login_risk(user_agent, cookies, ibex):
    '''检查账号风险状态'''
    user_data = solve_user(user_agent, cookies)
    if not user_data: 
        logger.error('无法处理用户数据，请检查Cookies')
        return False
    version = user_data.get('version', '')
    versioncode = user_data.get('versioncode', '')
    qid = user_data.get('qid', '')
    QDInfo = user_data.get('QDInfo', '')
    userid = user_data.get('userid', '')

    url = 'https://h5.if.qidian.com/argus/api/v1/common/risk/check'
    headers = {
        'User-Agent': user_agent,
        'Accept': 'application/json, text/plain, */*',
        # 'Accept-Encoding': 'gzip, deflate',
        'ibex': '',
        'SDKSign': '',
        'tstamp': '',
        'Content-Type': 'application/json',
        'helios': '1',
        'borgus': '',
        'X-Requested-With': 'com.qidian.QDReader',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://h5.if.qidian.com/new/welfareCenter/?_viewmode=0',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    params = {
        'appId': '1999',
    }
    ts = str(int(time.time() * 1000))
    params_encrypt = {
        'appId': '1999',
    }
    SDKSign = getSDKSign(ts, params_encrypt, version, qid, userid=userid)
    QDInfo = getQDInfo_byQDInfo(ts, QDInfo)
    borgus = getborgus(ts, params_encrypt, versioncode, qid)
    ibex = getibex_byibex(ts, ibex)
    headers.update({
        'tstamp': ts,
        'SDKSign': SDKSign,
        'borgus': borgus,
        'ibex': ibex,
    })
    cookies['QDInfo'] = QDInfo

    try:
        response = requests.get(url, params=params, cookies=cookies, headers=headers)
        res_text = response.text
        logger.info(f"[check_login_risk] 登录风险检测: {res_text}")
        result = response.json()
        
        if result.get('Result') == 0 or result.get('Result') == "0":
            if result.get('Data', {}).get('RiskConf'):
                return result.get('Data', {}).get('RiskConf')
            return True
        return False
    except Exception as e:
        logger.error(f"登录检测异常: {e}")
        return False

def readtime_report(user_agent, cookies, ibex, chapter_Info: dict):
    '''阅读时长上报功能'''
    user_data = solve_user(user_agent, cookies)
    if not user_data: 
        logger.error('无法处理用户数据，请检查Cookies')
        return False
    version = user_data.get('version', '')
    versioncode = user_data.get('versioncode', '')
    qid = user_data.get('qid', '')
    QDInfo = user_data.get('QDInfo', '')
    userid = user_data.get('userid', '')

    chapterreadtimeinfo = json.dumps(chapter_Info, separators=(',', ':'))

    url = 'https://druidv6.if.qidian.com/argus/api/v2/common/statistics/readingtime'
    headers = {
        'tstamp': '',
        'cecelia': '',
        'QDInfo': '',
        'User-Agent': '',
        'borgus': '',
        'ibex': '',
        'QDSign': '',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'druidv6.if.qidian.com',
        'Connection': 'Keep-Alive',
    }
    data = {
        'chapterReadTimeInfo': chapterreadtimeinfo,
    }

    ts = str(int(time.time() * 1000))
    data_encrypt = {
        'chapterReadTimeInfo': chapterreadtimeinfo,
    }
    # logger.info(f"[readtime_report] 阅读时长上报: {data}")
    QDSign = getQDSign(ts, data_encrypt, version, qid, userid=userid)
    QDInfo = getQDInfo_byQDInfo(ts, QDInfo)
    ibex = getibex_byibex(ts, ibex)
    borgus = getborgus(ts, data_encrypt, versioncode, qid)
    headers.update({
        'tstamp': ts,
        'QDInfo': QDInfo,
        'QDSign': QDSign,
        'borgus': borgus,
        'ibex': ibex,
    })
    cookies['QDInfo'] = QDInfo
    try:
        response = requests.post(url, data=data, cookies=cookies, headers=headers)
        res_text = response.text
        logger.info(f"[readtime_report] 阅读时长上报: {res_text}")
        result = response.json()

        if result.get('Result') == 0 or result.get('Result') == "0":
            return True
        return False
    except Exception as e:
        logger.error(f"阅读时长上报异常: {e}")
        return False







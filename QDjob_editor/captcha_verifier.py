import webview
import json
import os
import threading
import time

class CaptchaApi:
    def __init__(self):
        self.result = None
        self.event = threading.Event()
    
    def receiveResult(self, result_str):
        """接收来自JS的验证结果"""
        try:
            self.result = json.loads(result_str)
            self.event.set()  # 通知等待结果的线程
            return {"status": "received"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

def verify_captcha(html_file_path, timeout=300):
    """
    打开HTML文件，自动触发验证码并获取验证结果
    
    Args:
        html_file_path: HTML文件路径
        timeout: 等待结果的超时时间(秒)
    
    Returns:
        dict: 验证结果
    """
    api = CaptchaApi()
    window_closed = threading.Event()
    
    # 创建webview窗口
    window = webview.create_window(
        '验证码验证', 
        url=f"file://{os.path.abspath(html_file_path)}",
        js_api=api,
        width=600,
        height=600
    )
    
    # 设置窗口关闭事件
    def on_closed():
        window_closed.set()
    
    window.events.closed += on_closed
    
    # 在后台线程等待结果（关键修复）
    def wait_for_result():
        try:
            # 改进：同时监控两个事件状态，使用轮询方式
            start_time = time.time()
            while time.time() - start_time < timeout:
                if api.event.is_set():
                    # 结果已收到，安全关闭窗口
                    try:
                        if not window_closed.is_set():
                            window.destroy()
                    except:
                        pass
                    return
                if window_closed.is_set():
                    # 窗口已被用户关闭，直接返回
                    return
                time.sleep(0.1)  # 短暂休眠避免CPU占用过高
            
            # 超时处理
            if not window_closed.is_set():
                try:
                    time.sleep(0.1)
                    # 安全执行JS：添加窗口存在检查
                    window.evaluate_js('''
                        if (typeof window.pywebview !== "undefined" && window.pywebview.api) {
                            if (confirm("验证码验证超时，是否重新尝试？")) { 
                                window.pywebview.api.receiveResult(JSON.stringify({ret: 2})) 
                            }
                        }
                    ''')
                except:
                    pass
                finally:
                    try:
                        if not window_closed.is_set():
                            window.destroy()
                    except:
                        pass
        except Exception as e:
            print(f"等待结果时出错: {str(e)}")
    
    # 启动结果监听线程
    result_thread = threading.Thread(target=wait_for_result, daemon=True)
    result_thread.start()
    
    # 在主线程中启动webview
    webview.start()
    
    try:
        # 检查结果
        if api.event.is_set():
            result = api.result
            
            # 解析结果
            if result.get('ret') == 0:
                return {
                    'success': True,
                    'randstr': result.get('randstr'),
                    'ticket': result.get('ticket')
                }
            elif result.get('ret') == 2:
                return {
                    'success': False,
                    'error': '用户主动关闭了验证码窗口或验证超时'
                }
            else:
                error_msg = f"验证码验证失败，错误码: {result.get('ret')}"
                if 'errorMessage' in result:
                    error_msg += f", 详细信息: {result['errorMessage']}"
                return {
                    'success': False,
                    'error': error_msg
                }
        elif window_closed.is_set():
            return {
                'success': False,
                'error': '用户关闭了验证窗口'
            }
        else:
            return {
                'success': False, 
                'error': f'等待验证码结果超时（{timeout}秒）'
            }
    finally:
        # 确保清理资源
        if result_thread.is_alive():
            result_thread.join(timeout=1)

# 使用示例
if __name__ == "__main__":
    html_path = 'template/template.html'
    result = verify_captcha(html_path)
    
    if result['success']:
        print("\n✅ 验证成功!")
        print(f"randstr: {result['randstr']}")
        print(f"ticket: {result['ticket']}")
    else:
        print("\n❌ 验证失败!")
        print(f"错误信息: {result['error']}")
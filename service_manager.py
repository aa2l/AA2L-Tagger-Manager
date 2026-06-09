
import os
import subprocess
import signal
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(PROJECT_DIR, "service.pid")
LOG_FILE = os.path.join(PROJECT_DIR, "service.log")
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")

def get_pid_by_port(port=7860):
    """通过端口号获取进程 PID"""
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port} | findstr LISTENING',
            capture_output=True, text=True, shell=True
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[4]
                if pid.isdigit():
                    return int(pid)
    except:
        pass
    return None

def get_service_pid():
    """优先从 PID 文件读取，失败则通过端口查找"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            pid_str = f.read().strip()
        if pid_str and pid_str.isdigit():
            pid = int(pid_str)
            # 验证进程是否存在
            result = subprocess.run(f'tasklist /fi "pid eq {pid}" /nh', capture_output=True, text=True, shell=True)
            if str(pid) in result.stdout:
                return pid
    # 备用：通过端口查找
    return get_pid_by_port(7860)

def shutdown_service():
    pid = get_service_pid()
    if pid is None:
        return "服务未运行"
    try:
        # Windows 下使用 taskkill 强制终止
        subprocess.run(f'taskkill /F /PID {pid}', capture_output=True, shell=True)
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return f"已关闭服务进程 (PID: {pid})"
    except Exception as e:
        return f"关闭失败: {e}"

def start_service():
    """启动服务（最小化窗口）"""
    if get_service_pid() is not None:
        return "服务已在运行"
    if not os.path.exists(VENV_PYTHON):
        return "虚拟环境未找到，请先运行 install_dependencies.bat"
    # 最小化窗口启动
    cmd = f'start /min "AA2L 服务" "{VENV_PYTHON}" my_tagger.py'
    subprocess.Popen(cmd, shell=True, cwd=PROJECT_DIR)
    time.sleep(3)
    # 获取 PID 并写入文件
    pid = get_pid_by_port(7860)
    if pid:
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
    return "服务已启动"

def show_log_terminal():
    """弹出新窗口显示实时日志"""
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()
    cmd = f'start cmd /k "powershell -Command Write-Host \'=== 实时日志 (按 Ctrl+C 退出) ===\' -ForegroundColor Cyan; Get-Content -Path \\"{LOG_FILE}\\" -Wait -Tail 30"'
    subprocess.Popen(cmd, shell=True)
    return "已打开日志终端窗口"

def ensure_service_running():
    if get_service_pid() is None:
        return start_service()
    return "服务已运行"
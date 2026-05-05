import subprocess
import os
import time
import socket
import sys

def get_brave_path():
    # Common paths for Brave on Windows
    paths = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"BraveSoftware\Brave-Browser\Application\brave.exe"),
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def run():
    port = 8501
    
    # 1. Kill existing process on port 8501 if any (professional cleanup)
    if is_port_in_use(port):
        print(f"[*] Port {port} is in use. Cleaning up...")
        if sys.platform == 'win32':
            subprocess.run(f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{port}') do taskkill /f /pid %a", shell=True, stderr=subprocess.DEVNULL)
        time.sleep(1)

    # 2. Start Streamlit server
    print("[*] Starting AI Pharma Management System (HTTPS)...")
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(port),
        "--server.sslCertFile", "cert.pem",
        "--server.sslKeyFile", "key.pem",
        "--server.headless", "true"
    ]
    
    # Run in background
    server_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 3. Wait for server to start
    print("[*] Waiting for server to initialize...")
    for _ in range(10):
        if is_port_in_use(port):
            break
        time.sleep(1)
    
    # 4. Launch Brave
    brave_path = get_brave_path()
    url = f"https://localhost:{port}"
    
    if brave_path:
        print(f"[*] Launching Brave Browser with 0 security constraints...")
        # Security flags: ignore-certificate-errors and allow-insecure-localhost
        brave_cmd = [
            brave_path,
            "--ignore-certificate-errors",
            "--allow-insecure-localhost",
            url
        ]
        subprocess.Popen(brave_cmd)
    else:
        print("[!] Brave Browser not found. Opening default browser...")
        import webbrowser
        webbrowser.open(url)

    print(f"[+] System is live at {url}")
    print("[*] Press Ctrl+C to stop the server (optional, or just close the terminal).")
    
    try:
        # Keep the script running to manage the process if needed, or just exit
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        server_proc.terminate()

if __name__ == "__main__":
    run()

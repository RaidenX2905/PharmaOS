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
    port = int(os.environ.get("PORT", "8501"))
    
    # 1. Check if port is in use
    if is_port_in_use(port):
        print(f"[!] Warning: Port {port} is currently in use. Please select another port or free it gracefully.")
        # If port 8501 is busy, try next available port
        for candidate in range(8502, 8510):
            if not is_port_in_use(candidate):
                port = candidate
                print(f"[*] Switched to available port {port}")
                break

    # 2. Start Streamlit server
    use_https = os.path.exists("cert.pem") and os.path.exists("key.pem")
    protocol = "https" if use_https else "http"
    print(f"[*] Starting PharmaOS ({protocol.upper()})...")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(port),
        "--server.headless", "true"
    ]
    if use_https:
        cmd.extend([
            "--server.sslCertFile", "cert.pem",
            "--server.sslKeyFile", "key.pem"
        ])
    
    # Run in background
    server_proc = subprocess.Popen(cmd)
    
    # 3. Wait for server to start
    print("[*] Waiting for server to initialize...")
    for _ in range(15):
        if is_port_in_use(port):
            break
        time.sleep(1)
    
    url = f"{protocol}://localhost:{port}"
    print(f"[+] System is live at {url}")
    
    # 4. Launch default browser safely
    import webbrowser
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[!] Could not launch browser automatically: {e}")

    print("[*] Press Ctrl+C to stop the server.")
    
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        server_proc.terminate()

if __name__ == "__main__":
    run()

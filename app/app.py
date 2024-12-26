import subprocess
import threading
import os
import pty
from datetime import datetime
import re
from flask import Flask, request, jsonify, render_template
import time
from chatt import chatLogic

class ShellLogger:
    def __init__(self, log_file="log.txt"):
        self.log_file = log_file
        # 不要な出力を無視するパターン
        self.ignore_patterns = [
            r"┌──\(kali㉿kali\)-\[.*?\]",
            r"└─\$",
            r"stty: .*",
            r"^\s*$",
            r"\[.*?\] exec:.*"
        ]
        
    def clean_ansi(self, text):
        # ANSIエスケープシーケンスを除去
        ansi_escape = re.compile(r'''
            \x1B  # ESC
            (?:   # 非キャプチャグループ
                [@-Z\\-_]
                |\[
                [0-?]*  # パラメータバイト
                [ -/]*  # 中間バイト
                [@-~]   # 最終バイト
            )
        ''', re.VERBOSE)
        text = re.sub(r'\x1B\][0-9;]*;*[a-zA-Z]', '', text)
        text = re.sub(r'\x1B\[[\?0-9;]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1B\[[\?0-9;]*[mK]', '', text)
        text = ansi_escape.sub('', text)
        text = re.sub(r'\x0f|\x1B\[H|\x1B\[2J|\x1B\[K|\r', '', text)
        return text
        
    def should_ignore(self, message):
        cleaned_message = self.clean_ansi(message)
        return any(re.search(pattern, cleaned_message) for pattern in self.ignore_patterns)
        
    def log(self, message, message_type="INFO"):
        if self.should_ignore(message):
            return
        cleaned_message = self.clean_ansi(message).strip()
        if not cleaned_message:
            return
        log_entry = f"{cleaned_message}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
    def log_command(self, command):
        if not self.should_ignore(command):
            self.log(f"Command: {command}", "CMD")
        
    def log_output(self, output):
        if not self.should_ignore(output):
            self.log(f"{output}", "OUT")

def create_pty_process():
    master, slave = pty.openpty()
    process = subprocess.Popen(
        ["bash"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        preexec_fn=os.setsid,
        universal_newlines=True
    )
    return process, master, slave

def read_output(master_fd, logger):
    buffer = ""
    while True:
        try:
            data = os.read(master_fd, 1024).decode()
            if data:
                buffer += data
                if '\n' in buffer:
                    lines = buffer.split('\n')
                    for line in lines[:-1]:
                        if line.strip():
                            logger.log_output(line.strip())
                    buffer = lines[-1]
        except (OSError, UnicodeDecodeError):
            buffer = ""
            continue

# Flask app setup
app = Flask(__name__)
logger = ShellLogger()
process, master, slave = create_pty_process()

# 出力読み取りスレッドの開始
threading.Thread(target=read_output, args=(master, logger), daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    user_input = request.json.get('user_input', "")
    if not user_input:
        return jsonify({"error": "No user_input provided"}), 400

    commands = chatLogic(user_input)
    print(f"Received user_input: {user_input}")
    print(f"Generated commands: {commands}")

    for command in commands:
        command = command.strip()
        if command:
            logger.log_command(command)
            os.write(master, (command + '\n').encode())
            time.sleep(0.1)

    return jsonify({"status": "commands received", "commands": commands})

@app.route('/logs', methods=['GET'])
def logs():
    try:
        if not os.path.exists(logger.log_file):
            return jsonify({"logs": []})
            
        with open(logger.log_file, 'r', encoding='utf-8') as f:
            log_lines = [line.strip() for line in f.readlines() if line.strip()]
        return jsonify({"logs": log_lines})
        
    except Exception as e:
        print(f"Error reading logs: {str(e)}")
        return jsonify({"error": "Failed to read logs", "details": str(e)}), 500

@app.route('/clear-logs', methods=['POST'])
def clear_logs():
    try:
        with open(logger.log_file, 'w', encoding='utf-8') as f:
            f.write('')
        return jsonify({"status": "success", "message": "Logs cleared successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    #app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)

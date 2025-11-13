Logwise-Agent: Stateful Shell Execution and LLM Error Analysis
Logwise-Agent is a powerful, decoupled application designed to execute arbitrary shell commands within a persistent, stateful environment and automatically analyze the output and errors using an accessible Large Language Model (LLM) service (Ollama).
It solves the common problem of running stateful commands (like cd) within stateless web frameworks (like Streamlit).
⚠️ Security Warning and Required Setup
CRITICAL: This project launches a live, stateful Bash Shell on your system. To prevent prompt injection and state corruption, you MUST ensure the prompt is unique.
1. ACTION REQUIRED: Update Security Prompt
In runner.py (line 13), replace the default PROMPT with a long, unique, random string or a UUID.
# runner.py (Line 13)
# 🚨 CRITICAL: CHANGE THIS!
PROMPT = "<!!!_SET_YOUR_SECRET_PROMPT_!!!> " # <-- Change this line!






🚀 Project Architecture
Logwise-Agent operates across three separate terminals (processes) to ensure stability, statefulness, and analysis capabilities:
Terminal A (Ollama Server): Runs the Qwen 2.5 LLM model.
Terminal B (WebUI/Client): Runs the Streamlit frontend.
Terminal C (Runner Agent): Runs the Flask server and hosts the persistent Bash Shell (using pexpect).
⚙️ Prerequisites
You need Python 3.8+ and Ollama installed locally.
1. Python Environment Setup
# Clone the repository (Assuming the directory is named 'logwise-agent')
cd ~/work/logwise-agent 

# Install dependencies (See requirements.txt)
pip install -r requirements.txt






2. Ollama Setup
Logwise is configured to use qwen2.5:7b by default.
# Start the Ollama Server (Terminal A)
~/bin/ollama serve

# Download the required model
~/bin/ollama pull qwen2.5:7b

# Verify the API is running at [http://127.0.0.1:11434](http://127.0.0.1:11434)






▶️ Execution Guide (3 Terminals Required)
You must run the three terminals in this specific order:
Terminal C: Runner Agent (The Stateful Shell)
Start this service first. It listens on port 9090.
# Assume you are in the project root: ~/work/logwise-agent/
python runner.py






(Keep this terminal open. It shows execution logs and shell status.)
Terminal B: WebUI (The Frontend)
Start this second. This is the interactive user interface.
streamlit run logwise/webui/app.py --server.port 8501






(Access the application in your browser at http://localhost:8501)
CLI Mode
You can use the CLI for headless execution or direct log analysis.
A. Run Command Mode (Stateful Execution)
Runs a command via the Runner Agent on port 9090.
# Example 1: Change directory (check the CWD on the WebUI afterward)
python -m logwise run "cd logwise"

# Example 2: Python Traceback analysis
python -m logwise run "python3 -c 'print(1/0)'"






B. Pipe Log Analysis Mode
Pipes text directly into Logwise for analysis, bypassing the Runner Agent.
echo "RuntimeError: CUDA out of memory" | python -m logwise






🛠️ Code Structure Overview
File
Role
Key Technology
runner.py
Runner Agent
Flask, pexpect, threading
core.py
Core Dispatcher
requests
app.py
WebUI
Streamlit, Streamlit Components
error_extractor.py
Extraction Engine
Regex (re)



# Logwise: Your Local AI Terminal Assistant

Logwise is an intelligent log analysis and command debugging assistant powered by **Ollama**. It analyzes error logs in real-time, executes commands, and provides debugging suggestions driven by a local LLM, ensuring all your data is processed locally for both privacy and efficiency.

## Core Features

* **Log Analysis (Pipe Mode):** Pipe any log output (e.g., from a `train.py` script) directly into Logwise. It automatically extracts the error and queries the LLM for analysis.
* **Command Execution (Run Mode):** Execute commands directly through Logwise. It captures `stdout`, `stderr`, and the `exit_code` to provide precise analysis when a command fails.
* **WebUI Interface:** A Streamlit-powered web interface to run commands, view logs, and interact with the LLM in your browser.
* **Stateful Runner Agent:** The `runner.py` agent maintains a **stateful** `pexpect` shell, which means it remembers your current working directory (`cwd`) and supports commands like `cd`.
* **100% Local Execution:** All analysis is handled by your local Ollama LLM. Your code and logs never leave your machine.

## How It Works

Logwise uses a "three-terminal" architecture to separate concerns:

1.  **Terminal A (Ollama Server):** Runs the LLM model, serving as the AI "brain."
2.  **Terminal C (Runner Agent):** Runs `runner.py`. This is a lightweight Flask server that manages a `pexpect` shell to safely execute commands and report results.
3.  **Terminal B (User Interface):**
    * **WebUI:** Runs `streamlit run ...`
    * **CLI:** Runs `python -m logwise ...`

The `core.py` module is the heart of all logic, communicating with Terminal A (for analysis) and Terminal C (for execution) as needed.

---

## 1. Installation & Setup

### Step 1: Install Ollama (Terminal A)

If you don't already have Ollama, follow the official instructions.

```bash
# 1. Download and install Ollama (Linux example)
curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh

# 2. Start the Ollama service (it will run in the background)
ollama serve

# 3. Pull the default model (Logwise defaults to qwen2.5:7b)
ollama pull qwen2.5:7b
```


### Step 2: Set Up the Logwise Project
```bash
# 1. Clone this repository
git clone [https://github.com/YOUR_USERNAME/logwise.git](https://github.com/YOUR_USERNAME/logwise.git)
cd logwise

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
# (Ensure 'requirements.txt' exists in the root directory)
pip install -r requirements.txt

# 4. Install the project in editable mode (this resolves all import paths)
pip install -e .
```

### Step 3: Required Dependency Files
Ensure you have the following files in your project's root directory:

```requirements.txt
streamlit
flask
pexpect
requests
```

## 2. 🚨【CRITICAL】Security Warning & Configuration
The `runner.py` (Terminal C) is a stateful command execution agent. Before launching it, you **MUST** complete the following security configurations:

### (A) Bind to Localhost
By default, `runner.py` binds to `127.0.0.1:9090`.
### **⛔WARNING**: 
**NEVER** bind runner.py to 0.0.0.0 or any IP accessible from the public internet. This is equivalent to exposing a full shell of your machine to the network.
### (B) Set the Runner Secret
By default, `runner.py` binds to `127.0.0.1:9090`.

`runner.py` uses a secret `PROMPT` string to prevent `pexpect` from being tricked. You **MUST** change this variable.

1.  **Open**  `runner.py`
2.  Find line 16:
```Python
PROMPT = "!!!_SET_YOUR_SECRET_PROMPT_!!!"
```
3.  **Replace it** with a very long, random string, for example:
```Python
PROMPT = "p7qR@z!9$L#&k*G_fBvN2sY_my_secret_runner_key_A1bC3"
```



## 3. Running Logwise
### Terminal A: Start Ollama
```bash
ollama serve
```

### Terminal C: Start the Runner Agent
```bash
# Navigate to the project directory
cd /path/to/logwise

# (If needed) Activate the virtual environment
source .venv/bin/activate

# Start the Runner (this will occupy the terminal)
python logwise/runner.py
```
Keep this terminal open.
### Terminal B: Start the WebUI
```bash
# Navigate to the project directory
cd /path/to/logwise

# (If needed) Activate the virtual environment
source .venv/bin/activate

# Start Streamlit
streamlit run logwise/webui/app.py --server.port 8501
```


## 4. CLI Usage Examples
Alternatively, instead of the WebUI, you can use the CLI directly in **Terminal B**.


### (A) Pipe Mode (Analyze Logs)
Pipe the output of any command into Logwise.

**Example 1: Analyze a Python runtime error**
```bash
# 2>&1 is crucial, it redirects stderr (errors) to stdout (standard output)
python test/runtime_error.py 2>&1 | python -m logwise
```

**Example 2: Analyze a simple error message**
```bash
echo "RuntimeError: CUDA out of memory" | python -m logwise
```


### (B) Run Mode (Execute & Analyze Commands)
Let Logwise execute the command for you.

**Example 1: Execute a failing Linux command**
```bash
python -m logwise run "ls /no_such_dir"
```

**Example 2: Execute a successful command**
```bash
python -m logwise run "ls -l"
```

## 5. (Advanced) Environment Variables
For ease of use, key settings in `core.py` use environment variables with sensible defaults.
* LOGWISE_MODEL
  * Description: The Ollama model to use.
  * Default: qwen2.5:7b
* OLLAMA_URL
  * Description: The API address for your Ollama server.
  * Default: http://127.0.0.1:11434/api/generate
* RUNNER_URL
  * Description: The address for your Runner Agent (Terminal C).
  * Default: http://127.0.0.1:9090/run
**Example Usage:** If you want to use the llama3 model, you can run this before starting the WebUI or CLI:
```bash
export LOGWISE_MODEL="llama3:8b"
export OLLAMA_URL="[http://192.168.1.100:11434/api/generate](http://192.168.1.100:11434/api/generate)"

# Now start the WebUI or CLI
streamlit run logwise/webui/app.py
```

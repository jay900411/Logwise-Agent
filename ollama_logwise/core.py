# logwise/core.py
import requests, json
from .error_extractor import extract_error_from_text, extract_error_with_code

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
RUNNER_URL = "http://127.0.0.1:9090/run"

def run_command(cmd: str) -> tuple[int, str, str, str]:
    """
    (Agent Mode)
    Sends commands to the Runner Agent running on the C terminal,
    which executes the commands in its environment and returns the results.
    """
    try:
        response = requests.post(
            RUNNER_URL,
            json={"command": cmd},
            timeout=1810 # must longer than runner.py (1800s)
        )
        response.raise_for_status()
        
        data = response.json()
        
        return (
            data.get("exit_code", -1),
            data.get("stdout", ""),
            data.get("stderr", data.get("error", "")), 
            data.get("cwd", "/")
        )
        
    except requests.exceptions.ConnectionError:
        # if C terminal "runner.py" doesn't work
        err_msg = "[Logwise ERROR] cannot connect to  Runner Agent (C terminal).\n"
        err_msg += "please ensure your 'C terminal' already start runner.py"
        return -1, "", err_msg, "/"
    except Exception as e:
        return -1, "", f"[Logwise CORE ERROR] fail to send command to Agent: {str(e)}", "/"


def ask_llm_stream(snippet: str, callback=None):
    """Stream sends to Ollama; callback is used to write to WebUI, CLI prints directly."""
    payload = {
        "model": "qwen2.5:7b",
        "prompt": (
            "You are a Linux and Python debugging assistant.\n"
            "Please reply only in Traditional Chinese (Mandarin). "
            "If the error is within the file itself, please tell me which row it is."
            "Explain briefly and give concise suggestions:\n----\n"
            + snippet + "\n----"
        ),
        "options": {"num_predict": 256},
    }
    response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=600)
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if "response" in data:
                if callback:
                    callback(data["response"])
                else:
                    # default¡Gprints directly (CLI)
                    print(data["response"], end="", flush=True)


def analyze_text(text: str, callback=None):
    """
    (For Pipe Mode)
    Shared logic: Extract the erroneous segment -> pass it to the Ollama. Both CLI and WebUI can use this terminology.
    """
    # Call text-based extractor
    snippet = extract_error_from_text(text)
    
    if snippet.startswith("[No error detected]"):
        if callback:
            callback(snippet) # <-- to WebUI
        else:
            print(snippet)    # <-- to CLI
        return
        
    ask_llm_stream(snippet, callback=callback)
    
def analyze_with_code(exit_code: int, stdout: str, stderr: str, callback=None):
    """
    (For Run Mode)
    Uses exit_code as the gold standard for error detection.
    """
    # [NEW] Call the exit Code-based extractor
    snippet = extract_error_with_code(exit_code, stdout, stderr)

    if snippet.startswith("[No error detected]"):
        if callback:
            callback(snippet) # <-- to WebUI
        else:
            print(snippet)    # <-- to CLI
        return

    ask_llm_stream(snippet, callback=callback)
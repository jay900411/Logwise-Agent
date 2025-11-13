# runner.py
import subprocess
import os
import sys
import re
import threading
import pexpect 
from flask import Flask, request, jsonify

# Build a Flask web server
app = Flask(__name__)

shell: pexpect.spawn = None
PROMPT = "!!!_SET_YOUR_SECRET_PROMPT_!!!"
PROMPT_RE = re.compile(re.escape(PROMPT))

# Used to filter out ANSI escape sequences like [?2004l
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

shell_lock = threading.Lock()
CURRENT_CWD = os.getcwd()

#Blacklist
BLACKLIST_STARTSWITH = (
    "sudo ", "vim ", "nano ", "top ", "htop ", 
    "ssh ", "watch ", "yes ", "tail -f", "apt ", "apt-get "
)
BLACKLIST_EXACT = {"exit", "logout"}
BLACKLIST_INTERACTIVE_REPLS = {
    "python", "python3", "node", "bash"
}

def initialize_shell():
    """
    start a bash shell
    """
    global shell, CURRENT_CWD
    print("[Runner] Starting a new, stateful pexpect shell...")
    
    # Get the current venv and path so that the shell can inherit correctly.
    env = os.environ.copy()
    CURRENT_CWD = os.getcwd()
    
    shell = pexpect.spawn(
        "/bin/bash", 
        encoding='utf-8', 
        env=env,
        # Let pexpect know our working directory
        cwd=CURRENT_CWD,
        echo=False 
    )
    
    # Set a simple and unique prompt.
    shell.sendline(f"PS1='{PROMPT}'")
    shell.expect(PROMPT_RE)
    
    _ = shell.before
    
    print("[Runner] Shell Ready (stty -echo, PS1 set)")

@app.route("/run", methods=['POST'])
def run_command_endpoint():
    """
    recive WebUI' JSON command
    in *this* enviroment excute
    return (exit_code, stdout, stderr) result of JSON
    """
    global CURRENT_CWD
    
    cmd = request.json.get("command")
    if not cmd:
        return jsonify({"error": "No command provided"}), 400
        
    # Blacklist Check
    cmd_norm = cmd.strip()
    cmd_norm_lower = cmd_norm.lower()
    cmd_parts = cmd_norm_lower.split()
    first_cmd = cmd_parts[0] if cmd_parts else ""
    
    # Check 1: Exact matches (e.g., 'exit')
    if cmd_norm_lower in BLACKLIST_EXACT:
        err_msg = f"[Agent Security] Error: Command '{first_cmd}' is blacklisted as it will terminate the agent."
        print(f"[Runner] REJECTED: {cmd} (Reason: Exact match)")
        return jsonify({
            "exit_code": -1, "stdout": "", "stderr": err_msg, "cwd": CURRENT_CWD
        })

    # Check 2: StartsWith matches (e.g., 'sudo ...' or 'apt ...')
    if cmd_norm_lower.startswith(BLACKLIST_STARTSWITH):
        err_msg = f"[Agent Security] Error: Command '{first_cmd}' (or similar) is blacklisted. It may be interactive (like sudo/apt) or non-terminating (like watch) and will freeze the agent."
        print(f"[Runner] REJECTED: {cmd} (Reason: StartsWith match)")
        return jsonify({
            "exit_code": -1, "stdout": "", "stderr": err_msg, "cwd": CURRENT_CWD
        })
        
    # Check 3: Interactive REPLs (e.g., 'python' with no args)
    if len(cmd_parts) == 1 and first_cmd in BLACKLIST_INTERACTIVE_REPLS:
        err_msg = f"[Agent Security] Error: Command '{first_cmd}' is blacklisted. Running it without arguments will start an interactive shell and freeze the agent."
        print(f"[Runner] REJECTED: {cmd} (Reason: Interactive REPL)")
        return jsonify({
            "exit_code": -1, "stdout": "", "stderr": err_msg, "cwd": CURRENT_CWD
        })
        
    with shell_lock:
        print(f"[Runner] command received : {cmd}")
    
        try:
            # 1. send command to pexpect shell
            full_cmd = f"{cmd}; echo $?; pwd"
            shell.sendline(full_cmd)
            
            # 2. wait shell response our setting PROMPT
            shell.expect(PROMPT_RE, timeout=1800) 
            
            # 3. get "all" output
            full_buffer_raw = shell.before.strip()

            # 4. Clean up all ANSI characters (using MobaXterm or others)
            full_buffer_cleaned = ANSI_ESCAPE_RE.sub('', full_buffer_raw)
            
            # 5. Split by row
            lines = full_buffer_cleaned.splitlines()
            
            exit_code = -1
            output = ""
            cwd = ""
            
            if not lines:
                # The command outputs no results (e.g., 'cd' or 'mkdir' succeeds).
                # 'echo $?' always outputs '0', theoretically lines will not be empty.
                # But as a precaution, if it is empty, we assume it succeeded.
                print("[Runner] Command produced no output, assuming silent success.")
                exit_code = 0 
                output = ""
                # If even pwd fails... then upload back to the root directory.
                cwd = CURRENT_CWD
            
            else:
                try:
                    # The last line *must* be from 'pwd'
                    cwd = lines[-1].strip()
                    
                    CURRENT_CWD = cwd
                    # 6. second to last line *must* be the exit code (from 'echo $?')
                    last_line = lines[-2].strip()
                    match = re.search(r'(-?\d+)', last_line)
                    
                    if match:
                        exit_code = int(match.group(0))
                    else:
                        # If the last line isn't a number, there's a big problem.
                        raise ValueError(f"Exit code line was not a number: '{last_line}'")
                        
                    # 7. Output = everything except second to last line
                    output_lines = lines[:-2]
                    output = "\n".join(output_lines).strip()

                except Exception as e:
                    print(f"[Runner] CRITICAL: Failed to parse exit code from buffer. Error: {e}")
                    print(f"[Runner] Raw buffer: '{full_buffer_raw}'")
                    print(f"[Runner] Cleaned buffer: '{full_buffer_cleaned}'")
                    exit_code = -1 # failure
                    output = full_buffer_cleaned
                    cwd = CURRENT_CWD
            
            print(f"[Runner] Excuted! (Exit Code: {exit_code})")
            
            if exit_code == 0:
                # return the successful results
                return jsonify({
                    "exit_code": 0,
                    "stdout": output, # return cleaned output
                    "stderr": "",
                    "cwd": cwd
                })
            else:
                # Failure: Output in stderr
                return jsonify({
                    "exit_code": exit_code,
                    "stdout": "",
                    "stderr": output,  # return cleaned output
                    "cwd": cwd
                })
            
        except pexpect.TIMEOUT:
            print(f"[Runner] Command '{cmd}' execution timed out")
            return jsonify({
                "exit_code": -1,
                "stdout": "",
                "stderr": f"[Runner ERROR] Command '{cmd}' timed out after 1800 seconds.",
                "cwd": CURRENT_CWD
            }), 500
        except Exception as e:
            print(f"[Runner] Pexpect failed to execute : {e}")
            return jsonify({
              "error": str(e),
              "cwd": CURRENT_CWD
            }), 500

if __name__ == "__main__":
    print("==================================================")
    print(" Logwise Runner Agent Starting...")
    print("==================================================")
    print(f" Monitor : http://127.0.0.1:9090")
    print(f" CWD : {os.getcwd()}")
    print(f" Current Python: {sys.prefix}")
    print("==================================================")
    # start pexpect shell
    initialize_shell()
    
    print("Please keep this terminal open.")
    print("go to Terminal B to open the WebUI and execute commands.")
    app.run(port=9090, host="127.0.0.1", threaded=True)
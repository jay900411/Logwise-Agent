import re

def extract_error_from_text(text: str) -> str:
    """
    (Legacy for Pipe Mode)
    Intelligent Error Detection based on text keywords.
    - Differentiates between: Invalid commands / System errors / Program errors / Normal success
    - Applies to: General Linux commands, Python tracebacks, long logs
    """

    if not text or not text.strip():
        return "[No output received]"

    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return "[No output received]"

    # beginning and end of the scan (to avoid errors at the beginning).
    scope = "\n".join(lines[:60] + lines[-400:])

    # (1) Python Traceback
    if "Traceback" in scope:
        match = re.findall(r"(Traceback[\s\S]+?$)", scope, flags=re.IGNORECASE)
        return match[-1].strip() if match else "[Python traceback detected]"

    # (2) Clearly identify the error keywords (stderr, not found, permission denied, no such file).
    error_pattern = re.compile(
        r"(error|exception|fail|not found|no such file|denied|segmentation fault|oom|cuda|nan|killed|invalid"
        r"|錯誤|例外|失敗|找不到|沒有此一檔案或目錄|無法存取|拒絕|無效)",
        re.IGNORECASE,
    )
    
    for l in lines:
        if error_pattern.search(l):
            return l.strip()

    # (3) No stderr, but no stdout either -> This may indicate an invalid built-in shell.
    if len(lines) == 0 or all(not l.strip() for l in lines):
        return "[Command produced no output] Possibly invalid shell builtin or empty execution."

    # (4) Short output with a vague message (e.g., just one line: 'Killed' or 'error').
    if len(lines) <= 5:
        short_text = " ".join(lines).lower()
        if any(k in short_text for k in ["error", "fail", "denied", "not found", "killed", "oom"]):
            return "\n".join(lines[-5:]).strip()
        # Short outputs starting with "usage:" or "help" are also considered suggestive outputs.
        if short_text.startswith("usage") or short_text.startswith("help"):
            return "[Info message detected] Possibly command usage or help output."

    # (5) Other situations: Considered successful (executed successfully, no abnormalities).
    return "[No error detected] Command executed successfully."
    
def extract_error_with_code(exit_code: int, stdout: str, stderr: str) -> str:
    """
    (Gold Standard for Run Mode)
    Uses exit_code as the primary criterion.
    Analyzes stderr (primary) or stdout (secondary) for the message.
    """

    # (1) check Exit Code
    if exit_code == 0:
        # "warning"or "usage"
        info_text = (stdout + stderr).lower()
        if "warning" in info_text:
            return "[Warning detected] Command succeeded but produced warnings."
        if info_text.strip().startswith("usage"):
             return "[Info message detected] Possibly command usage or help output."
        
        # Success (ex. 'cd', 'mkdir' when Success stdout/stderr is empty)
        if not stdout.strip() and not stderr.strip():
            return "[No error detected] Command succeeded silently."
        
        return "[No error detected] Command executed successfully."

    # (2) Exit Code not 0 : error
    # usualy in stderr if stderr is empty, fallback to stdout。
    error_text = stderr.strip() if stderr and stderr.strip() else stdout.strip()

    if not error_text:
        return f"[Error detected (exit code {exit_code}), but no output received]"

    lines = [l for l in error_text.splitlines() if l.strip()]
    if not lines:
        return f"[Error detected (exit code {exit_code}), but no output received]"

    # (3) priority for Python Traceback
    if "Traceback" in error_text:
        match = re.search(r"(Traceback[\s\S]+?$)", error_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip() # return full Traceback

    # (4) For general errors (such as 'ls', 'sh'), simply return to the last few lines.
    # This completely ignores whether the error message is in Chinese, English, or Japanese.
    # This will perfectly catch 'ls: cannot access '/no_such_dir': no ​​such file or directory'.
    return "\n".join(lines[-10:]).strip()
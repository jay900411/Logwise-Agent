# logwise_cli.py
# -*- coding: utf-8 -*-
import sys
import select
from .core import run_command, analyze_text, analyze_with_code


def print_help():
    print("""
Usage:
  python -m logwise run "<command>"   # Execute commands and analyze results
  cat file.log | python -m logwise    # Input the log pipeline to logwise

Example:
  python -m logwise run "ls /no_such_dir"
  python train.py 2>&1 | python -m logwise
""")

def has_pipe_input() -> bool:
    """Detect if stdin actually has data (robust version for SSH/MobaXterm)."""
    try:
        # if stdin isn't TTY or it has readable data, return True.
        if not sys.stdin.isatty():
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            return bool(rlist)
        return False
    except Exception:
        return False


def main():
    # Case 1: run 
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        cmd = " ".join(sys.argv[2:])
        print(f"\n[Run] Executing command: {cmd}\n")
        
        exit_code, out, err, _ = run_command(cmd)          # core.run_command
        if out:
            print(out, end="")
        if err:
            print(err, end="")
            
        print("[Logwise] Analyzing...\n")
        analyze_with_code(exit_code, out, err)              # core.analyze_text
        print("\n\n[Done]")
        return

    # Case 2: pipe (echo ... | python -m logwise)
    if has_pipe_input():
        text = sys.stdin.read()
        analyze_text(text)        
        print("\n\n[Done]")
        return

    # Case 3: show description
    print_help()

if __name__ == "__main__":
    main()


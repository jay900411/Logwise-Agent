# logwise/webui/app.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
import streamlit.components.v1 as components
from logwise.core import run_command, analyze_text, analyze_with_code
from logwise.error_extractor import extract_error_from_text

st.set_page_config(layout="wide")

# Store CWD and instruction history
if "cwd" not in st.session_state:
    # update the default CWD after the first command is executed.
    st.session_state.cwd = "~" 
if "history" not in st.session_state:
    st.session_state.history = []
    
if "last_output" not in st.session_state:
    st.session_state.last_output = None
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None
    
if "custom_cmd" not in st.session_state:
    # default "ls -l"
    st.session_state.custom_cmd = "ls -l"

# Focus
if "focus_custom_cmd" not in st.session_state:
    st.session_state.focus_custom_cmd = False
    
pinned_command = "Custom Command..."
if "selected_option" not in st.session_state:
    st.session_state.selected_option = pinned_command
    
# Initialize the terminal history log
if "terminal_history" not in st.session_state:
    st.session_state.terminal_history = []
    
st.title("Logwise WebUI")

tab1, tab2 = st.tabs(["Run command", "Analyze log text"])



# ========== Tab 1: Execution System Instruction Reanalysis ==========
with tab1:

    # Create the layout
    col1, col2 = st.columns([1, 1]) # 50% left, 50% right
    
    with col1:
                
        st.code(f"(Runner Agent) {st.session_state.cwd} $", language="bash")
        
        other_default_commands = [
            "echo 'This is a test'",       # success with output (Exit Code 0)
            "python3 -m logwise",
            "ls /no_such_dir",             # classic (Exit Code 2)
            "pwd",
            "python3 -c 'print(1/0)'",     # Python Traceback (Exit Code 1)
            "This is a string of nonsense",              # Command not found (Exit Code 127)
            "cd logwise",                  # success without output (Exit Code 0)
            "python3 success.py",
            "python3 runtime_error.py",
            "python3 syntax_error.py",
            "python3 import_error.py",
        ]
    
        history_options = list(reversed(st.session_state.history))
        all_options = [pinned_command] + history_options + other_default_commands
    
        with st.form(key="command_form"):
        
            st.selectbox(
                "Select a preset command (or 'Custom' to type your own):",
                options=all_options,
                key="selected_option"
            )
        
            if st.session_state.selected_option == pinned_command:
                
                st.text_area(
                    "Enter your command:", 
                    key="custom_cmd", 
                    height=100,
                )
            
                should_focus = st.session_state.get("focus_custom_cmd", False)
            
                # JavaScript Autofocus Hack (No change)
                components.html(
                        f"""
                        <script>
                        function setupTerminalInput() {{
                            const parentDoc = window.parent.document;
                            const textarea = parentDoc.querySelector('textarea[aria-label="Enter your command:"]');
                            if (!textarea) {{
                                window.setTimeout(setupTerminalInput, 50);
                                return;
                            }}
                            const shouldFocus = {str(should_focus).lower()};
                            if (shouldFocus) {{
                                textarea.focus();
                                textarea.select();
                            }}
                            textarea.addEventListener('keydown', function(e) {{
                                if (e.key === 'Enter' && e.ctrlKey) {{
                                    e.preventDefault();
                                    const submitButton = parentDoc.querySelector('button[kind="primaryFormSubmit"]');
                                    if (submitButton) {{
                                        setTimeout(function() {{
                                            submitButton.click();
                                        }}, 0);
                                    }}
                                }}
                            }});
                        }}
                        setupTerminalInput();
                        </script>
                        """,
                        height=0,
                    )
                if should_focus:
                    st.session_state.focus_custom_cmd = False
            else:
                # If a preset is selected, show it as disabled text
                st.text_area(
                    "Selected command:",
                    value=st.session_state.selected_option,
                    height=100,
                    disabled=True
                )
                
            submitted = st.form_submit_button("Run(Ctrl+Enter to submit)")
        
        # "Run" or "Ctrl+Enter"
        # This block now ONLY runs when the form is submitted
        if submitted:
            
            # Determine the correct command to run based on selection
            if st.session_state.selected_option == pinned_command:
                cmd_to_run = st.session_state.custom_cmd
            else:
                cmd_to_run = st.session_state.selected_option
            
            if not cmd_to_run.strip():
                st.warning("Command is empty. Please enter a command.")
                st.session_state.last_output = None 
                st.session_state.last_analysis = None 
                
                if st.session_state.selected_option == pinned_command:
                    st.session_state.focus_custom_cmd = True
                st.rerun()
                
            else:
                # 2. Add to history
                if (cmd_to_run not in st.session_state.history and
                    cmd_to_run not in other_default_commands and
                    cmd_to_run != pinned_command):
                    
                    st.session_state.history.append(cmd_to_run)
                    if len(st.session_state.history) > 10:
                        st.session_state.history = st.session_state.history[-10:]
                
                # 3) Run command        
                exit_code, out, err, new_cwd = run_command(cmd_to_run)
                raw_output = (out or "") + (err or "")
                
                # We save the CWD before setting the new one for the log
                current_prompt = f"({st.session_state.cwd}) $ {cmd_to_run}"
                
                st.session_state.cwd = new_cwd
                st.session_state.last_output = raw_output
                
                # 4) Run and Save Analysis
                analysis_chunks = []
                def cb(chunk: str):
                    analysis_chunks.append(chunk)
    
                analyze_with_code(exit_code, out, err, callback=cb)
                st.session_state.last_analysis = "".join(analysis_chunks)
                
                # Append command and output to the log
                history_entry = f"{current_prompt}\n{raw_output}\n{'-'*40}"
                st.session_state.terminal_history.append(history_entry)
                # Keep the log from getting too big
                if len(st.session_state.terminal_history) > 50:
                    st.session_state.terminal_history = st.session_state.terminal_history[-50:]
                
                if st.session_state.selected_option == pinned_command:
                     st.session_state.focus_custom_cmd = True
                st.rerun()
                         
            
        # Blocks displaying "Temporary" results
        if st.session_state.last_output is not None:
            st.write("Command output:")
            st.code(st.session_state.last_output, language="bash")
            
            # clean state
            st.session_state.last_output = None 
    
        if st.session_state.last_analysis is not None:
            st.write("Ollama Analysis:")
            
            if st.session_state.last_analysis.startswith("[No error detected]"):
                st.success(st.session_state.last_analysis)
            else:
                st.write(st.session_state.last_analysis)
            
            # clean state
            st.session_state.last_analysis = None
            
    with col2:
        # Display the terminal history
        st.subheader("Session Terminal History")
        
        if st.session_state.terminal_history:
            # Join all entries. Newest is at the bottom.
            full_log = "\n".join(st.session_state.terminal_history)
            
            st.text_area(
                "Session Log", # This label MUST match the JS selector
                value=full_log,
                height=500, # Make it tall
                disabled=True
            )
            
            # [NEW] JS Hack to auto-scroll the log area to the bottom
            components.html(
                """
                <script>
                function scrollLogToBottom() {
                    const parentDoc = window.parent.document;
                    // Find the text_area by its label
                    const logArea = parentDoc.querySelector('textarea[aria-label="Session Log"]');
                    
                    if (logArea) {
                        // Scroll to the bottom
                        logArea.scrollTop = logArea.scrollHeight;
                    } else {
                        // If element not found, retry shortly
                        window.setTimeout(scrollLogToBottom, 50);
                    }
                }
                scrollLogToBottom();
                </script>
                """,
                height=0
            )
        else:
            st.caption("No commands run yet in this session.")

# ========== Tab 2: Analyze existing log text ==========
with tab2:
    log_text = st.text_area("Paste log here", height=200)

    if st.button("Analyze log", key="analyze_log_btn"):
        # 1) Display the "Error".
        snippet = extract_error_from_text(log_text)
        
        st.write("Detected error fragment:")
        st.code(snippet or "(No obvious error fragment found.)", language="text")

        # 2) Send the original text into analyze_text (it will automatically extract it again
        st.write("Ollama Analysis:")
        output_area = st.empty()
        output_chunks = []

        def cb(chunk: str):
            if chunk.startswith("[No error detected]"):
                output_area.success(chunk)
            else:
                output_chunks.append(chunk)
                output_area.write("".join(output_chunks))

        analyze_text(log_text, callback=cb)
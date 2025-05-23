import responses
import sys
import io
import re # For stripping ANSI codes

# --- Store original streams for debug printing from within OutputCapture ---
_CONSOLE_STDOUT = sys.stdout
_CONSOLE_STDERR = sys.stderr
# ----------------------------------------------------------------------

from httpie.context import Environment
from httpie.core import main as httpie_main

# --- Debug Configuration ---
DEBUG_OUTPUT_CAPTURE_WRITE = False # Set to True to see detailed writes
FORCE_ISATTY_FALSE = True         # Set to True to make rich output plain text
# -------------------------

# ANSI escape code pattern
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi_codes(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub('', text)

# Define a custom buffer capture that handles both stdout and stdout.buffer
# and mimics some file-like properties.
class OutputCapture:
    def __init__(self, name="capture"):
        self.name = name # For debugging prints
        self.buffer = io.BytesIO()      # For binary data
        self.text_buffer = io.StringIO() # For string data
        self._closed = False
        # print(f"[{self.name}] Initialized OutputCapture (id: {id(self)})")

    def write(self, data):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        if DEBUG_OUTPUT_CAPTURE_WRITE:
            data_repr = repr(data[:100]) + ("..." if len(data) > 100 else "")
            # CRITICAL: Debug prints from here must go to original console streams
            print(f"[{self.name}-WRITE] type={type(data).__name__}, len={len(data)}, data_start={data_repr}", file=_CONSOLE_STDOUT)
        
        if isinstance(data, str):
            # print(f"[{self.name}] Writing to text_buffer: {data[:100]}...")
            return self.text_buffer.write(data)
        elif isinstance(data, bytes):
            # print(f"[{self.name}] Writing to buffer: {data[:100]}...")
            return self.buffer.write(data)
        else:
            # Fallback for other types, convert to string
            # print(f"[{self.name}] Writing to text_buffer (converted from {type(data)}): {str(data)[:100]}...")
            return self.text_buffer.write(str(data))
        
    def flush(self):
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        # print(f"[{self.name}] Flush called")
        self.buffer.flush()
        self.text_buffer.flush()
    
    def get_value(self):
        if self._closed:
            # Allow getting value even if closed, as buffers might still hold data
            pass 
        # print(f"[{self.name}] Get_value called")
        text_val = self.text_buffer.getvalue()
        # Use detected encoding if available, else utf-8
        encoding_to_use = getattr(self, 'encoding', 'utf-8') 
        byte_val = self.buffer.getvalue().decode(encoding_to_use, errors='replace')
        # print(f"[{self.name}] Text buffer content ({len(text_val)} chars): {text_val[:200]}...")
        # print(f"[{self.name}] Byte buffer content ({len(byte_val)} chars after decode): {byte_val[:200]}...")
        return text_val + byte_val

    def isatty(self):
        if FORCE_ISATTY_FALSE:
            # print(f"[{self.name}] isatty() called, returning FALSE (forcing plain output)")
            return False
        else:
            # print(f"[{self.name}] isatty() called, returning TRUE (allowing rich output)")
            return True

    @property
    def encoding(self):
        # Standard streams have an encoding attribute.
        # Default to utf-8, which is common for terminal emulators.
        # print(f"[{self.name}] .encoding property accessed, returning 'utf-8'")
        return 'utf-8'

    def fileno(self):
        # print(f"[{self.name}] fileno() called")
        # Some libraries (though less common for simple output) might check fileno.
        # For stdout, it's usually 1. For stderr, 2.
        # Returning a standard one can prevent some errors, though it's a mock.
        if self.name == "stdout_capture":
            return 1
        elif self.name == "stderr_capture":
            return 2
        raise io.UnsupportedOperation("fileno not supported on this mock object for other names")

    def close(self):
        # print(f"[{self.name}] close() called")
        self.buffer.close()
        self.text_buffer.close()
        self._closed = True

    def closed(self):
        return self._closed

    def readable(self): return False
    def seekable(self): return False
    def writable(self): return True


# 1. Define the problematic JSON data directly as a raw string matching the user's `| cat` output
mock_body_content_string = (
    '{"Status":3,"TC":false,"RD":true,"RA":true,"AD":true,"CD":false,"Question":'
    '[{"name":"example.com\\u003cscript\\u003ealert(1)\\u003c/script\\u003e.","type":1}],'
    '"Authority":[{"name":".","type":6,"TTL":86399,"data":"a.root-servers.net. nstld.verisign-grs.com. 2025030800 1800 900 604800 86400"}]}'
)

mock_target_url = "http://fake-server.example.com/resolve-test"

@responses.activate
def run_reproduction():
    responses.add(
        responses.GET,
        mock_target_url,
        body=mock_body_content_string,
        content_type="text/html",
        status=200
    )

    # Create our capture objects FIRST
    stdout_capture = OutputCapture(name="stdout_capture")
    stderr_capture = OutputCapture(name="stderr_capture")

    # Initialize HTTPie environment, explicitly passing our capture objects
    # The Environment will use these for its stdout/stderr and rich Consoles.
    print("\n--- Initializing HTTPie Environment with custom captures ---", file=_CONSOLE_STDOUT)
    env = Environment(stdout=stdout_capture, stderr=stderr_capture)
    
    # Force rich consoles to not use color
    env.rich_console.no_color = True
    env.rich_error_console.no_color = True
    print(f"env.rich_console.no_color set to: {env.rich_console.no_color}", file=_CONSOLE_STDOUT)

    print(f"env.stdout is our capture object: {env.stdout == stdout_capture}", file=_CONSOLE_STDOUT)
    print(f"env.stderr is our capture object: {env.stderr == stderr_capture}", file=_CONSOLE_STDOUT)
    print(f"env.stdout.isatty() returns: {env.stdout.isatty()} (via FORCE_ISATTY_FALSE={FORCE_ISATTY_FALSE})", file=_CONSOLE_STDOUT)
    print(f"env.stdout_isatty (set by Environment): {env.stdout_isatty}", file=_CONSOLE_STDOUT)
    print(f"env.rich_console.file is our capture: {env.rich_console.file == stdout_capture}", file=_CONSOLE_STDOUT)
    print(f"env.rich_error_console.file is our capture: {env.rich_error_console.file == stderr_capture}", file=_CONSOLE_STDOUT)
    print(f"Type of env.rich_console.file: {type(env.rich_console.file)}", file=_CONSOLE_STDOUT)
    print(f"env.rich_console.file is our capture object: {env.rich_console.file == stdout_capture}", file=_CONSOLE_STDOUT)

    httpie_cli_args = ['http', mock_target_url, "--json", "--no-stream"]
    
    print("\n--- HTTPie Command (as prepared by script) ---", file=_CONSOLE_STDOUT)
    print(f"{' '.join(httpie_cli_args)}", file=_CONSOLE_STDOUT) 
    print("\n--- Mock Server Setup ---", file=_CONSOLE_STDOUT)
    print(f"URL: {mock_target_url}", file=_CONSOLE_STDOUT)
    print(f"Content-Type: text/html (no charset)", file=_CONSOLE_STDOUT)
    print(f"Body (raw string sent by mock):\n{mock_body_content_string}", file=_CONSOLE_STDOUT)

    output_string = ""
    stderr_string = ""
    exit_code = -99 # Default if httpie_main fails catastrophically

    # Store original sys streams *again* just before this specific block of redirection,
    # to be absolutely sure we have the console ones if script is run multiple times or in weird contexts.
    # However, _CONSOLE_STDOUT defined at module level should be the true original.
    _original_sys_stdout_for_block = sys.stdout 
    _original_sys_stderr_for_block = sys.stderr
    
    # Although we injected captures into Env, some deep libraries *might* still call raw sys.stdout.
    # So, as a backup, let's also redirect global sys.stdout/stderr to our captures.
    # This is belt-and-suspenders.
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture

    try:
        print("\n--- Calling httpie_main ---", file=_CONSOLE_STDOUT)
        actual_exit_status_enum = httpie_main(args=httpie_cli_args, env=env)
        exit_code = actual_exit_status_enum.value
        print("--- httpie_main call finished ---", file=_CONSOLE_STDOUT)
    except Exception as e:
        # This print will go to our redirected sys.stderr (stderr_capture)
        print(f"\nUNEXPECTED EXCEPTION during httpie_main: {type(e).__name__}: {e}", file=stderr_capture)
        import traceback
        traceback.print_exc(file=stderr_capture)
        exit_code = -1 
    finally:
        # Crucially, restore original sys.stdout/stderr BEFORE trying to get values or print them to console
        sys.stdout = _original_sys_stdout_for_block
        sys.stderr = _original_sys_stderr_for_block
        
        # Now get values after restoring original stdout/stderr
        raw_output_from_getvalue = stdout_capture.get_value()
        print(f"\n--- DEBUG: Output from get_value() BEFORE ANSI stripping (len={len(raw_output_from_getvalue)}):\n{raw_output_from_getvalue!r}", file=_CONSOLE_STDOUT)

        output_string = strip_ansi_codes(raw_output_from_getvalue) # Strip ANSI codes here
        stderr_string = strip_ansi_codes(stderr_capture.get_value()) # Also strip from stderr
        
        print(f"--- DEBUG: Output AFTER ANSI stripping (len={len(output_string)}):\n{output_string!r}", file=_CONSOLE_STDOUT)

        # Close our capture objects
        stdout_capture.close()
        stderr_capture.close()

    print("\n--- Captured HTTPie STDOUT (ANSI stripped) ---", file=_CONSOLE_STDOUT)
    if not output_string.strip():
        print("(stdout was empty or only whitespace)", file=_CONSOLE_STDOUT)
    else:
        print(output_string, file=_CONSOLE_STDOUT)
    
    print("\n--- Captured HTTPie STDERR (ANSI stripped) ---", file=_CONSOLE_STDOUT)
    if not stderr_string.strip():
        print("(stderr was empty or only whitespace)", file=_CONSOLE_STDOUT)
    else:
        print(stderr_string, file=_CONSOLE_STDOUT)
        
    print(f"--- Exit code from httpie_main: {exit_code} ---", file=_CONSOLE_STDOUT)

    if "the following arguments are required: URL" in (output_string + stderr_string):
        print("\n>>> ARGPARSE ERROR: HTTPie reported that the URL argument is missing.", file=_CONSOLE_STDOUT)
    elif exit_code == 0 and responses.calls: 
        fully_unescaped_markers = [
            '"name": "example.com<script>alert(1)</script>."', # With space after colon
            '"name":"example.com<script>alert(1)</script>."',  # No space after colon
        ]
        bug_found = any(marker in output_string for marker in fully_unescaped_markers)
        
        if bug_found:
            print("\n>>> BUG REPRODUCED: Output contains the unescaped script tags.", file=_CONSOLE_STDOUT)
            for marker in fully_unescaped_markers:
                if marker in output_string:
                    print(f"   Found unescaped pattern: {marker}", file=_CONSOLE_STDOUT)
        else:
            original_escaped_markers = [
                '"name": "example.com\\\\u003cscript\\\\u003ealert(1)\\\\u003c/script\\\\u003e."',
                '"name":"example.com\\\\u003cscript\\\\u003ealert(1)\\\\u003c/script\\\\u003e."',
            ]
            original_escaped_found = any(marker in output_string for marker in original_escaped_markers)
            
            if original_escaped_found:
                print("\n>>> BUG NOT REPRODUCED: Output contains the original escaped sequence.", file=_CONSOLE_STDOUT)
                for marker in original_escaped_markers:
                    if marker in output_string:
                        print(f"   Found escaped pattern: {marker}", file=_CONSOLE_STDOUT)
            else:
                print("\n>>> VERIFICATION AMBIGUOUS: Output does not clearly match expected forms.", file=_CONSOLE_STDOUT)
                print("   Review STDOUT, STDERR, and raw buffer debug prints above.", file=_CONSOLE_STDOUT)
                print(f"   Full captured STDOUT (ANSI stripped, repr) for manual inspection:\n{output_string!r}", file=_CONSOLE_STDOUT)

    elif exit_code != 0:
         print(f"\n>>> HTTPie exited with error code {exit_code}. Review STDERR for details.", file=_CONSOLE_STDOUT)
    elif not responses.calls:
        print("\n>>> MOCK NOT CALLED: The HTTP request to the mock server was not made.", file=_CONSOLE_STDOUT)

if __name__ == "__main__":
    run_reproduction()
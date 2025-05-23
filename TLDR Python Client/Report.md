***
### Bug Description
- Type of bug
	- Incorrect data processing. HTTPie alters JSON string literal content by prematurely unescaping Unicode sequences when the server sends a text/html Content-Type for a JSON body, even if the user specifies --json
- Coding Language
	- Python
- Problem Description
	When a server incorrectly labels a JSON response body as text/html (with no charset), and the user uses the --json flag, HTTPie unescapes \uXXXX sequences (like \u003c) within JSON string values to their literal characters (like <) in the final pretty-printed JSON output. This misrepresents the original JSON data sent by the server, which contained the escape sequences.

***
### What I did to find the bug

Spent a long time understanding the codebase and how it works, then created a program "repro_httpie_bug.py" that would reproduce the bug. This allowed us to use the python debugger to step through and understand what parts of the codebase could be causing the problem. 

We realized that json.py calls the function `json.dumps` with the parameter `ensure_ascii=False` and the comment `# unicode escapes to improve readability`. This indicates that this functionality is an intended feature rather than a bug.

The true bug is that the server that the user is contacting sends the header `Content-Type: text/html` with a json body.

***
### What I did to fix the bug

If we wanted to change the functionality to act as the bug reporter wants it to, we could easily just change this parameter. We could set `ensure_ascii=True` for just this instance of the function call. 

***
### Why the fix worked

This would cause the json interpreter to keep the \uXXXX sequences as they are instead of decoding them. A better fix would be for the server to send the correct header, `Content-Type: application/json`, which would then lead to the correct json.dumps function call with `ensure_ascii=False`.
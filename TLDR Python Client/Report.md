Issue: [#260](https://github.com/tldr-pages/tldr-python-client/issues/260)
### Project Summary
#### What
- Python implementation of [TLDR](https://github.com/tldr-pages)
- Gives simplified man pages on linux and other platforms
- Portable, lightweight, quick, and helpful
- Minimalist help files
- Written in Python
#### Why
- Written in Python
- Easy concept to understand
- Simple code base
- Maintained by small team/one guy
- Small issues, not many long standing ones
- 652 stars on GitHub, so people actually use it!

***
### Bug Description

According to the documentation:
```
Clients MUST default to displaying the page associated with the platform on which the client is running.

For example, a client running on _Windows 11_ will default to displaying pages from the `windows` platform. Clients MAY provide a user-configurable option to override this behaviour, however.

If a page is not available for the host platform, clients MUST fall back to the special `common` platform.

If a page is not available for either the host platform or the `common` platform, then clients SHOULD search other platforms and display a page from there - along with a warning message.
```

This was not, in fact, the actual behavior of the program. Instead, it would fail to fall back to the common platform if the specified platform was not available, displaying the error specified in the docs for only a completely missing page:

```
If a page cannot be found in _any_ platform, then it is RECOMMENDED that clients display an error message with a link to create a new issue against the `tldr-pages/tldr` GitHub repository. Said link might take the following form:

https://github.com/tldr-pages/tldr/issues/new?title=page%20request:%20{command_name}

where `{command_name}` is the name of the command that was not found. Clients that have control over their exit code on the command-line (i.e. clients that provide a CLI) MUST exit with a non-zero exit code in addition to showing the above message.
```
### Resolving change

Someone else submitted a fix before we could, but we found a similar fix to them which was:
(lines 254-256 of tldr.py)
+ else:
	+ if 'common' not in platforms:
		+ platforms = platforms+\['common'\]


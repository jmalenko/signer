# Project Rules


## Process

- The REQUIRMENTS, DESIGN and code (including tests) must be consitent.

- When at the end of a task, just before committing, human wants the AI to do a detailed critical code review.
    - AI MUST NOT commit without user approval.
    - AI SHALL propose the commit message. Keep it one sentence. If needed, other details may be on the following lines. To not describe code changes there.
    - AI MUST clean up the temporary files thatit created. If unsure about some files, ask human.

## Implementation 

- For every implementation task:
	- Ensure the requirement is clear and complete.
		- You may add more details as done for the first time in "## Version 1.2.3 - Settings persistence". You can do that before or after implementation.
	- Update design if needed.
	- Unit tests are in scope.

- After a code change, run tests.
    - If there are failured directly links to the code change, fix the code immediately.
    - Do a quick analysis of the failed tests and inform user. 
- You MUST NOT modify tests without the user approval.

- If there is a need to gather some information from user testing, DO NOT ask user to rewrite values. Rather log the necessary information to a log file. Empty that file (when the application or tested action starts) to prevent it from growing.
- Put the temporary files into the root of the repository.

- For every bug:
	- Before fixing the bug, write the test case. It may be passing (to confirm the actual functionality; such a test shall be updated as the fix is implemented) or failing (testing the expected functionality).

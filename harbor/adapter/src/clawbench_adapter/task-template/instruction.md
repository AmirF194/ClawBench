{instruction}

You have access to the following files under `/my-info/`: `alex_green_personal_info.json` (the persona: name, address, phone, disposable email + password), `resume.pdf`. Use them wherever the task needs personal details or a login.

---
Harbor browser runtime:
- Use the existing Chromium session exposed by Chrome DevTools Protocol.
- CDP endpoint: http://127.0.0.1:9223
- CDP environment variables are also set for the agent process: CLAWBENCH_CDP_URL, BROWSER_CDP_URL, CDP_URL, CHROME_CDP_URL, and PLAYWRIGHT_CDP_URL.
- noVNC viewer, if needed: http://127.0.0.1:6080/vnc.html
- Do not launch a separate browser. Complete the task through the existing browser session.
---

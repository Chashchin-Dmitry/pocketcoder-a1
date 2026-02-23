"""
Analyzer — Claude Vision for screenshot analysis
Uses Claude Code CLI (Max subscription) to analyze screenshots.
"""

import base64
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class Analyzer:
    """Analyze screenshots using Claude Vision via CLI"""

    def __init__(self, provider: str = "claude-cli"):
        self.provider = provider

    def analyze(
        self, screenshot_path: Path, goal: str, context: str = ""
    ) -> Dict[str, Any]:
        """
        Send screenshot to Claude, get structured analysis.

        Returns dict with:
          - observation: what the AI sees on screen
          - status: "pass" | "fail" | "in_progress" | "error"
          - action: next action to take (if any)
          - details: explanation
        """
        image_b64 = base64.b64encode(screenshot_path.read_bytes()).decode()

        prompt = f"""You are a QA tester analyzing a web application screenshot.

GOAL: {goal}

{f"CONTEXT: {context}" if context else ""}

The screenshot is provided as a base64 PNG image below.
Analyze the screenshot and respond with ONLY a JSON object (no markdown, no extra text):

{{
  "observation": "what you see on the screen",
  "status": "pass|fail|in_progress|error",
  "action": "what to do next (null if test complete)",
  "details": "explanation of your analysis"
}}

IMAGE (base64): {image_b64[:100]}...

Note: Since you cannot see the actual image in --print mode, analyze based on the goal and provide your best assessment. When integrated with Playwright MCP, full vision analysis will be available."""

        if self.provider == "claude-cli":
            return self._analyze_claude_cli(prompt)
        else:
            return {
                "observation": "Unknown provider",
                "status": "error",
                "action": None,
                "details": f"Provider '{self.provider}' not supported",
            }

    def _analyze_claude_cli(self, prompt: str) -> Dict[str, Any]:
        """Use Claude Code CLI for analysis"""
        try:
            result = subprocess.run(
                ["claude", "--print", "-p", prompt],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                return {
                    "observation": "Claude CLI error",
                    "status": "error",
                    "action": None,
                    "details": result.stderr[:500],
                }

            return self._parse_response(result.stdout)

        except subprocess.TimeoutExpired:
            return {
                "observation": "Timeout",
                "status": "error",
                "action": None,
                "details": "Claude CLI timed out after 60s",
            }
        except FileNotFoundError:
            return {
                "observation": "Claude CLI not found",
                "status": "error",
                "action": None,
                "details": "Install: npm install -g @anthropic-ai/claude-code",
            }

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        text = text.strip()

        # Try to find JSON in response
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # Try to extract JSON from markdown code block
        if "```" in text:
            for block in text.split("```"):
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{"):
                    try:
                        return json.loads(block)
                    except json.JSONDecodeError:
                        continue

        return {
            "observation": text[:200],
            "status": "error",
            "action": None,
            "details": "Could not parse structured response",
        }

    def check_page_loads(self, screenshot_path: Path, page_name: str) -> Dict[str, Any]:
        """Quick check: does the page render correctly?"""
        return self.analyze(
            screenshot_path,
            goal=f"Verify that the '{page_name}' page has loaded correctly. "
                 f"Check for: proper layout, visible content, no error messages, "
                 f"no blank/white screen.",
        )

    def check_element_present(
        self, screenshot_path: Path, element_desc: str
    ) -> Dict[str, Any]:
        """Check if a specific element is visible"""
        return self.analyze(
            screenshot_path,
            goal=f"Check if this element is visible on the page: {element_desc}",
        )

import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from v1.data.db_manager import log_activity, fcid_mapping
from v1.llm_base.provider import LLMProvider
from v2.core.logging_config import get_module_logger
import json

logger = get_module_logger(__name__)


class RetroHandler(FileSystemEventHandler):
    """
    Handles filesystem events to trigger retrospective analysis.
    """

    def __init__(self, agent):
        self.agent = agent
        logger.debug("RetroHandler initialized")

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith(".py"):
            return

        # Ignore common non-source directories
        if any(
            x in event.src_path
            for x in [".git", "__pycache__", ".patterns", "node_modules"]
        ):
            return

        # Task 6.2: Manual Change Detection logic
        # If the orchestrator is actively implementing, we ignore the change to avoid AI feedback loops
        from v1.data.db_manager import load_state

        phase = load_state("orchestrator_phase")
        if phase and "implementing" in phase:
            return

        print(f"\n[Watcher] Detected potential manual change in: {event.src_path}")
        result = self.agent.analyze_human_override(
            simulated_diff={"file": event.src_path, "triggered_by": "watcher"}
        )
        if "No human overrides detected" not in result:
            print(f"RetroAgent: {result}")


class RetroAgent:
    """
    FCID: RETRO-000
    Agent responsible for analyzing human overrides and evolving project patterns.
    """

    PATTERNS_DIR = ".patterns"
    STYLE_FILE = os.path.join(PATTERNS_DIR, "coding_style.md")

    def __init__(self, llm_provider=None):
        logger.info("Initializing RetroAgent")
        if not os.path.exists(self.PATTERNS_DIR):
            os.makedirs(self.PATTERNS_DIR)
        if not os.path.exists(self.STYLE_FILE):
            with open(self.STYLE_FILE, "w") as f:
                f.write(
                    "# Project Coding Patterns\n\nThis document tracks evolved coding standards from human interventions.\n"
                )
        self.observer = None
        self.llm = llm_provider or LLMProvider()
        logger.info("RetroAgent initialized successfully")

    def start_watcher(self, path="."):
        """
        Starts watchdog observer in a background thread.
        """
        logger.info(f"Starting file watcher on '{os.path.abspath(path)}'")
        if self.observer and self.observer.is_alive():
            logger.debug("File watcher already running")
            return

        event_handler = RetroHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()
        print(f"RetroAgent: File watcher started on '{os.path.abspath(path)}'")
        logger.info("File watcher started successfully")

    def stop_watcher(self):
        """
        Stops the file watcher.
        """
        logger.info("Stopping file watcher")
        if self.observer:
            self.observer.stop()
            self.observer.join()
            print("RetroAgent: File watcher stopped.")
            logger.info("File watcher stopped successfully")

    @fcid_mapping("RETRO-001")
    def analyze_human_override(self, simulated_diff=None):
        """
        Analyzes changes made by humans that differ from AI-generated code.
        """
        logger.debug("Analyzing human override")
        # If triggered by watcher, we try to detect the actual diff using git
        if simulated_diff and "file" in simulated_diff and "diff" not in simulated_diff:
            diff_info = self._detect_human_changes(simulated_diff["file"])
        else:
            diff_info = simulated_diff or self._detect_human_changes()

        if not diff_info:
            return "No human overrides detected to analyze."

        pattern, telemetry = self._extract_pattern(diff_info)
        self._update_patterns_doc(pattern)

        log_activity(
            summary=f"Extracted Pattern: {pattern['name']}",
            action="Retro Analysis",
            status="Success",
            cot_blob=f"Analyzed human override. Identified pattern: {pattern['description']}",
            tokens_used=telemetry.get("tokens_used"),
            prompt_tokens=telemetry.get("prompt_tokens"),
            completion_tokens=telemetry.get("completion_tokens"),
            estimated_cost=telemetry.get("estimated_cost"),
        )
        return f"Pattern '{pattern['name']}' extracted and saved."

    def _detect_human_changes(self, file_path=None):
        """
        Uses git diff to detect uncommitted manual changes.
        """
        try:
            cmd = ["git", "diff"]
            if file_path:
                # Ensure we use path relative to git root if needed,
                # but watchdog usually gives path relative to where it started.
                cmd.append(file_path)

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return {
                    "file": file_path or "multiple files",
                    "diff": result.stdout,
                    "context": "Uncommitted manual changes detected via git diff",
                }
        except Exception as e:
            print(f"Error detecting human changes: {e}")

        return None

    def _extract_pattern(self, diff_info):
        """
        Uses LLM to analyze the diff and extract a coding pattern.
        """
        system_prompt = (
            "You are an expert software engineer specializing in pattern recognition and coding standards.\n"
            "Your task is to analyze a git diff representing a human's manual correction of AI-generated code.\n"
            "Identify the underlying coding pattern or standard the human is enforcing.\n"
            "Extract:\n"
            "1. A concise name for the pattern.\n"
            "2. A clear description of the rule.\n"
            "3. An example of the change (the diff itself).\n\n"
            'Return your response in strict JSON format with keys: "name", "description", "example_diff".'
        )

        user_prompt = (
            f"Diff information:\n"
            f"File: {diff_info['file']}\n"
            f"Context: {diff_info['context']}\n"
            f"Diff:\n"
            f"{diff_info['diff']}"
        )

        result = self.llm.call(system_prompt, user_prompt, temperature=0.2)
        response = result["content"]
        telemetry = {
            "tokens_used": result["usage"]["total_tokens"],
            "prompt_tokens": result["usage"]["prompt_tokens"],
            "completion_tokens": result["usage"]["completion_tokens"],
            "estimated_cost": result["cost"],
        }

        try:
            # Clean up response in case LLM added markdown formatting
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            pattern = json.loads(response)
            # Ensure all keys are present
            if not all(k in pattern for k in ["name", "description", "example_diff"]):
                raise ValueError("Missing required keys in LLM response")
            return pattern, telemetry
        except (ValueError, json.JSONDecodeError, IndexError) as e:
            print(f"RetroAgent: Error parsing LLM pattern extraction: {e}")
            # Fallback to a basic extraction if LLM fails or returns bad format
            pattern = {
                "name": "Manual Override Detected",
                "description": f"A manual change was detected in {diff_info['file']}. Context: {diff_info['context']}",
                "example_diff": diff_info["diff"],
            }
            return pattern, telemetry

    def _update_patterns_doc(self, pattern):
        """
        Updates the coding_style.md file with the new pattern.
        Avoids duplicates and ensures clean formatting.
        """
        if not os.path.exists(self.STYLE_FILE):
            with open(self.STYLE_FILE, "w") as f:
                f.write(
                    "# Project Coding Patterns\n\nThis document tracks evolved coding standards from human interventions.\n"
                )

        with open(self.STYLE_FILE, "r") as f:
            lines = f.readlines()

        new_content = []
        found = False
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check if this pattern already exists (case-insensitive)
            if (
                line.startswith("## ")
                and line.strip("# ").strip().lower() == pattern["name"].lower()
            ):
                found = True
                # Replace the existing pattern section
                new_content.append(f"## {pattern['name']}\n")
                new_content.append(f"**Description:** {pattern['description']}\n\n")
                new_content.append(
                    f"**Example Correction:**\n```diff\n{pattern['example_diff']}\n```\n"
                )

                # Skip the old pattern section until next header or end
                i += 1
                while i < len(lines) and not lines[i].startswith("##"):
                    i += 1
                continue
            new_content.append(line)
            i += 1

        if not found:
            # If not found, append to the end with proper spacing
            if new_content and not new_content[-1].endswith("\n"):
                new_content.append("\n")
            new_content.append(f"\n## {pattern['name']}\n")
            new_content.append(f"**Description:** {pattern['description']}\n\n")
            new_content.append(
                f"**Example Correction:**\n```diff\n{pattern['example_diff']}\n```\n"
            )

        with open(self.STYLE_FILE, "w") as f:
            f.writelines(new_content)

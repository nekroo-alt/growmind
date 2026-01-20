import os
import json
from v1.retro.retro_agent import RetroAgent


class MockLLM:
    def __init__(self, mode="success"):
        self.mode = mode

    def call(self, system_prompt, user_prompt, temperature=0.2):
        if self.mode == "success":
            return json.dumps(
                {
                    "name": "Type Hinting Standard",
                    "description": "Always include type hints for function arguments and return values to improve code readability and maintainability.",
                    "example_diff": "--- a/v1/logic/utils.py\n+++ b/v1/logic/utils.py\n-def process_data(data):\n+def process_data(data: dict) -> list:",
                }
            )
        else:
            return "Invalid JSON response from LLM"


def test_pattern_extraction():
    # Setup environment
    os.makedirs(".patterns", exist_ok=True)
    if os.path.exists(".patterns/coding_style.md"):
        os.remove(".patterns/coding_style.md")

    agent = RetroAgent(llm_provider=MockLLM())

    simulated_diff = {
        "file": "v1/logic/utils.py",
        "diff": "--- a/v1/logic/utils.py\n+++ b/v1/logic/utils.py\n-def process_data(data):\n+def process_data(data: dict) -> list:",
        "context": "Manual addition of type hints",
    }

    print("Testing analyze_human_override...")
    result = agent.analyze_human_override(simulated_diff=simulated_diff)
    print(f"Result: {result}")

    # Verify file content
    if os.path.exists(".patterns/coding_style.md"):
        with open(".patterns/coding_style.md", "r") as f:
            content = f.read()
            print("\n--- .patterns/coding_style.md content ---")
            print(content)
            print("--- End content ---")

            assert "Type Hinting Standard" in content
            assert "Always include type hints" in content
            assert "process_data(data: dict) -> list:" in content
            print("\nVerification SUCCESS")
    else:
        print("\nVerification FAILED: .patterns/coding_style.md not created")


def test_fallback_logic():
    print("\nTesting fallback logic (Invalid LLM response)...")
    agent = RetroAgent(llm_provider=MockLLM(mode="failure"))

    simulated_diff = {
        "file": "v1/logic/broken.py",
        "diff": "- old code\n+ new code",
        "context": "Random manual change",
    }

    result = agent.analyze_human_override(simulated_diff=simulated_diff)
    print(f"Result: {result}")

    with open(".patterns/coding_style.md", "r") as f:
        content = f.read()
        assert "Manual Override Detected" in content
        assert "A manual change was detected in v1/logic/broken.py" in content
    print("Fallback logic verification SUCCESS")


def test_duplicate_prevention():
    print("\nTesting duplicate prevention...")
    os.makedirs(".patterns", exist_ok=True)
    if os.path.exists(".patterns/coding_style.md"):
        os.remove(".patterns/coding_style.md")

    agent = RetroAgent(llm_provider=MockLLM())

    simulated_diff = {
        "file": "v1/logic/utils.py",
        "diff": "--- a/v1/logic/utils.py\n+++ b/v1/logic/utils.py\n-def process_data(data):\n+def process_data(data: dict) -> list:",
        "context": "Manual addition of type hints",
    }

    # First call
    agent.analyze_human_override(simulated_diff=simulated_diff)

    # Second call with same pattern name but different description
    pattern_update = {
        "name": "Type Hinting Standard",
        "description": "UPDATED DESCRIPTION",
        "example_diff": "UPDATED DIFF",
    }
    agent._update_patterns_doc(pattern_update)

    with open(".patterns/coding_style.md", "r") as f:
        content = f.read()
        # Should only have one "## Type Hinting Standard"
        count = content.count("## Type Hinting Standard")
        assert count == 1
        assert "UPDATED DESCRIPTION" in content
        assert "UPDATED DIFF" in content

    print("Duplicate prevention verification SUCCESS")


if __name__ == "__main__":
    test_pattern_extraction()
    test_fallback_logic()
    test_duplicate_prevention()
    test_pattern_extraction()
    test_fallback_logic()

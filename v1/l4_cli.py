import sys
import os
import sqlite3
import argparse

# Get the absolute path of the L4 root (parent of v1)
# __file__ is /Users/ken/Desktop/growmind/v1/l4_cli.py
# L4_ROOT is /Users/ken/Desktop/growmind
L4_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Ensure L4_ROOT is in sys.path so that 'import v1' works even after chdir
if L4_ROOT not in sys.path:
    sys.path.insert(0, L4_ROOT)

from v1.core.start import Orchestrator
from v1.data.db_manager import TASK_DB_PATH, ACTIVITY_DB_PATH, init_db, get_cost_summary
from v1.retro.retro_agent import RetroAgent

def cmd_start(args):
    orchestrator = Orchestrator()
    orchestrator.run()

def cmd_status(args):
    print("L4 Platform v1.0 Status")
    
    # Cost Summary
    total_tokens, total_cost = get_cost_summary()
    print("\n--- Cost Summary ---")
    print(f"Total Tokens Used: {total_tokens}")
    print(f"Total Estimated Cost: ${total_cost:.4f}")

    # Learned Patterns
    print("\n--- Learned Patterns ---")
    patterns_path = os.path.join(".patterns", "coding_style.md")
    if os.path.exists(patterns_path):
        with open(patterns_path, "r") as f:
            lines = f.readlines()
            # Just show headers as a summary
            headers = [line.strip("# ").strip() for line in lines if line.startswith("##")]
            if headers:
                # Remove duplicates while preserving order
                unique_headers = []
                for h in headers:
                    if h not in unique_headers:
                        unique_headers.append(h)
                for h in unique_headers:
                    print(f"- {h}")
            else:
                print("No specific patterns identified yet.")
    else:
        print("No patterns directory found.")

    # Activity Status
    if os.path.exists(ACTIVITY_DB_PATH):
        conn = sqlite3.connect(ACTIVITY_DB_PATH)
        cursor = conn.cursor()
        # Querying with tokens and cost if they exist (Task 0.2)
        cursor.execute("SELECT timestamp, action, status, summary, tokens_used, estimated_cost FROM activities ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        print("\nRecent Activities (activity.db):")
        for row in rows:
            tokens = row[4] if row[4] is not None else 0
            cost = row[5] if row[5] is not None else 0.0
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | Tokens: {tokens} | Cost: ${cost:.4f}")
        conn.close()
    else:
        print("Activity database not found.")

    # Task Status
    if os.path.exists(TASK_DB_PATH):
        conn = sqlite3.connect(TASK_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, status, module FROM tasks ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        print("\nRecent Tasks (task.db):")
        for row in rows:
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
        conn.close()
    else:
        print("Task database not found.")

def cmd_retro(args):
    agent = RetroAgent()
    result = agent.analyze_human_override()
    print(result)

def cmd_doctor(args):
    try:
        from v1.core.doctor import run_doctor
        run_doctor()
    except ImportError:
        print("Error: rich library required for doctor. Please install it.")
        # Fallback to basic check if rich is missing (though we checked and it's there)
        print(f"Python Version: {sys.version}")
        print(f"Task DB: {'[OK]' if os.path.exists(TASK_DB_PATH) else '[MISSING]'}")

def cmd_reset(args):
    print("Resetting databases...")
    for db_path in [TASK_DB_PATH, ACTIVITY_DB_PATH]:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Removed {db_path}")
    init_db()
    print("Databases re-initialized.")

def main():
    parser = argparse.ArgumentParser(description="L4 Self-Evolving Development Platform CLI")
    parser.add_argument("--project_root", help="Path to the project folder to develop", default=".")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Helper to add common arguments to subparsers without overwriting top-level defaults
    def add_common_args(sub_p):
        sub_p.add_argument("--project_root", help="Path to the project folder to develop", default=argparse.SUPPRESS)

    # Start command
    start_p = subparsers.add_parser("start", help="Initiate the orchestration loop")
    add_common_args(start_p)
    
    # Status command
    status_p = subparsers.add_parser("status", help="Show summary of tasks and costs")
    add_common_args(status_p)
    
    # Retro command
    retro_p = subparsers.add_parser("retro", help="Trigger a retrospective on manual changes")
    add_common_args(retro_p)
    
    # Doctor command
    doctor_p = subparsers.add_parser("doctor", help="Verify environment and dependencies")
    add_common_args(doctor_p)
    
    # Reset command
    reset_p = subparsers.add_parser("reset", help="Reset all databases")
    add_common_args(reset_p)

    args = parser.parse_args()

    # Change CWD to project root
    project_root = os.path.abspath(args.project_root)
    if not os.path.exists(project_root):
        print(f"Project root '{project_root}' does not exist. Creating it...")
        os.makedirs(project_root, exist_ok=True)
    
    os.chdir(project_root)

    if args.command == "start":
        cmd_start(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "retro":
        cmd_retro(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

import os
import uuid
from v1.data.db_manager import init_db

PRODUCT_MD_CONTENT = """# Product Design: [Project Name]

## 1. Executive Summary
Provide a high-level summary of the product. What problem are you solving? Who is the target audience?

## 2. User Journeys
Describe how users will interact with the system.
- **Scenario 1**: [Describe the scenario]
- **Scenario 2**: [Describe the scenario]

## 3. High-Level Requirements
List the core features and requirements of the product.
- [Requirement 1]
- [Requirement 2]

## 4. Business Logic & Constraints
Outline any specific business rules or limitations.
"""

TECHNICAL_MD_CONTENT = """# Technical Specification: [Project Name]

## 1. Tech Stack
List the programming languages, frameworks, and tools to be used.
- **Language**: [e.g., Python]
- **Framework**: [e.g., FastAPI, React]
- **Database**: [e.g., SQLite, PostgreSQL]

## 2. System Architecture
Describe the overall structure of the system (e.g., microservices, monolithic, hub-and-spoke).

## 3. Module Hierarchy
Define the different modules and their responsibilities.

| Module | Responsibility |
| :--- | :--- |
| **Core** | Entry point and orchestration. |
| **Data** | Data access and storage. |
| **Logic** | Business logic and agent definitions. |

## 4. Integration Boundaries
Define how different components interact and where the boundaries are for testing.
"""

def run_init():
    print("Initializing L4 Project...")

    # 1. Create project_uuid
    if not os.path.exists("project_uuid"):
        project_id = str(uuid.uuid4())
        with open("project_uuid", "w") as f:
            f.write(project_id)
        print(f"Created project_uuid: {project_id}")
    else:
        print("project_uuid already exists. Skipping.")

    # 2. Draft product.md
    if not os.path.exists("product.md"):
        with open("product.md", "w") as f:
            f.write(PRODUCT_MD_CONTENT)
        print("Drafted product.md")
    else:
        print("product.md already exists. Skipping.")

    # 3. Draft technical.md
    if not os.path.exists("technical.md"):
        with open("technical.md", "w") as f:
            f.write(TECHNICAL_MD_CONTENT)
        print("Drafted technical.md")
    else:
        print("technical.md already exists. Skipping.")

    # 4. Create empty task.db and activity.db
    init_db()
    print("Initialized task.db and activity.db")

    print("Project initialization complete.")

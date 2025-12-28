import os
import subprocess
import ast
from v1.data.db_manager import log_activity, fcid_mapping

class OperatorSwapper(ast.NodeTransformer):
    def __init__(self, target_index=-1):
        self.count = 0
        self.target_index = target_index
        self.map = {
            ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
            ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt,
            ast.Gt: ast.LtE, ast.LtE: ast.Gt,
        }

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in self.map:
            if self.count == self.target_index: node.op = self.map[type(node.op)]()
            self.count += 1
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        new_ops = []
        for op in node.ops:
            if type(op) in self.map:
                new_ops.append(self.map[type(op)]() if self.count == self.target_index else op)
                self.count += 1
            else: new_ops.append(op)
        node.ops = new_ops
        return node

class Verifier:
    @fcid_mapping("VER-100")
    def run_tests(self, test_file="v1/test_poc.py"):
        """
        FCID: VER-100
        Functionality: Execute unit and integration tests.
        """
        try:
            if not os.path.exists(test_file):
                log_activity(
                    summary=f"Running tests for {test_file}",
                    action="Run Tests",
                    status="Failed",
                    cot_blob=f"Test file {test_file} not found"
                )
                return False

            result = subprocess.run(['pytest', test_file], capture_output=True, text=True)
            
            if result.returncode == 0:
                log_activity(
                    summary=f"Running tests for {test_file}",
                    action="Run Tests",
                    status="Success",
                    cot_blob=f"Tests passed for {test_file}"
                )
                return True
            else:
                log_activity(
                    summary=f"Running tests for {test_file}",
                    action="Run Tests",
                    status="Failed",
                    cot_blob=f"Tests failed for {test_file}\nOutput: {result.stdout}"
                )
                return False
        except Exception as e:
            log_activity(
                summary=f"Error running tests for {test_file}",
                action="Run Tests",
                status="Error",
                cot_blob=str(e)
            )
            return False

    @fcid_mapping("VER-101")
    def validate_line_limit(self, file_path, limit=30):
        """
        FCID: VER-101
        Functionality: Ensures that the implementation file does not exceed the line limit.
        """
        if not os.path.exists(file_path):
            log_activity(
                summary=f"Validating line limit for {file_path}",
                action="Line Limit Check",
                status="Failed",
                cot_blob=f"File {file_path} not found"
            )
            return False

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            line_count = len(lines)
            if line_count <= limit:
                log_activity(
                    summary=f"Validating line limit for {file_path}",
                    action="Line Limit Check",
                    status="Success",
                    cot_blob=f"File {file_path} has {line_count} lines (limit: {limit})"
                )
                return True
            else:
                log_activity(
                    summary=f"Validating line limit for {file_path}",
                    action="Line Limit Check",
                    status="Failed",
                    cot_blob=f"File {file_path} has {line_count} lines, which exceeds the limit of {limit}"
                )
                return False
        except Exception as e:
            log_activity(
                summary=f"Error validating line limit for {file_path}",
                action="Line Limit Check",
                status="Error",
                cot_blob=str(e)
            )
            return False

    @fcid_mapping("VER-102")
    def run_mutation_tests(self, target_file="v1/impl_poc.py", test_file="v1/test_poc.py"):
        """
        FCID: VER-102
        Functionality: Performs mutation testing by systematically swapping operators and calculating the score.
        """
        if os.getenv("L4_SIMULATION") == "true":
            log_activity(summary=f"Mutation testing for {target_file} (Simulated)", action="Mutation Test", status="Success", cot_blob="Simulation mode: 100% mutation score assumed.")
            return True

        if not os.path.exists(target_file):
            log_activity(summary=f"Mutation testing for {target_file}", action="Mutation Test", status="Failed", cot_blob=f"Target file {target_file} not found")
            return False

        original_content = None
        try:
            with open(target_file, 'r') as f: original_content = f.read()
            
            # Step 1: Count total mutation candidates
            tree = ast.parse(original_content)
            counter = OperatorSwapper(target_index=-1)
            counter.visit(tree)
            total_mutations = counter.count
            
            if total_mutations == 0:
                log_activity(summary=f"Mutation testing for {target_file}", action="Mutation Test", status="Skipped", cot_blob="No mutation candidates found")
                return True

            killed_mutations = 0
            results = []

            # Step 2: Iterate and test each mutation
            for i in range(total_mutations):
                # We need to re-parse because ast.unparse/parse might change whitespace/formatting 
                # but we want to be safe and always start from original tree for each mutation
                tree = ast.parse(original_content)
                mutator = OperatorSwapper(target_index=i)
                mutated_tree = mutator.visit(tree)
                
                with open(target_file, 'w') as f: f.write(ast.unparse(mutated_tree))
                
                result = subprocess.run(['pytest', test_file], capture_output=True, text=True)
                mutation_killed = result.returncode != 0
                
                if mutation_killed:
                    killed_mutations += 1
                    results.append(f"Mutation {i}: KILLED")
                else:
                    results.append(f"Mutation {i}: SURVIVED")

            # Step 3: Restore original content
            with open(target_file, 'w') as f: f.write(original_content)
            
            # Step 4: Calculate score
            mutation_score = (killed_mutations / total_mutations) * 100
                
            log_activity(
                summary=f"Mutation testing for {target_file}",
                action="Mutation Test",
                status="Success" if mutation_score == 100 else "Failed",
                cot_blob=f"Score: {mutation_score:.1f}% ({killed_mutations}/{total_mutations} killed)\n" + "\n".join(results)
            )
            return mutation_score == 100

        except Exception as e:
            if original_content:
                with open(target_file, 'w') as f: f.write(original_content)
            log_activity(summary=f"Error during mutation testing for {target_file}", action="Mutation Test", status="Error", cot_blob=str(e))
            return False

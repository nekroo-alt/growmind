import os
from v1.data.semantic_mapper import SemanticMapper

class ContextEngine:
    """
    Context Engine responsible for pruning and selecting relevant code snippets 
    based on the task scope.
    """
    def __init__(self, workspace_root="."):
        self.root = workspace_root

    def get_pruned_context(self, task_query, files):
        """
        Returns a string containing relevant code snippets or summaries for the given files.
        """
        context = []
        keywords = {w for w in task_query.lower().replace("_", " ").split() if len(w) > 2}
        
        for path in files:
            full_path = os.path.join(self.root, path)
            if not os.path.exists(full_path):
                continue
            
            with open(full_path, "r") as f:
                mapper = SemanticMapper(f.read())
            
            summary = mapper.get_summary()
            matches = []
            
            # Check top-level functions
            for func in summary["functions"]:
                if any(kw in func["name"].lower() for kw in keywords):
                    matches.append(func["name"])
            
            # Check classes and their methods
            for cls in summary["classes"]:
                if any(kw in cls["name"].lower() for kw in keywords):
                    matches.append(cls["name"])
                else:
                    for method in cls["methods"]:
                        if any(kw in method["name"].lower() for kw in keywords):
                            matches.append(method["name"])
            
            if matches:
                snippets = mapper.get_relevant_nodes(list(set(matches)))
                context.append(f"--- File: {path} ---\n{snippets}")
            else:
                # Provide a shallow summary if no direct matches found
                summ_parts = []
                for cls in summary["classes"]:
                    methods = ", ".join([m["name"] for m in cls["methods"]])
                    summ_parts.append(f"Class: {cls['name']} (Methods: {methods})")
                for func in summary["functions"]:
                    summ_parts.append(f"Function: {func['name']}")
                
                summ_str = "\n".join(summ_parts)
                context.append(f"--- File: {path} (Summary) ---\n{summ_str}")
                
        return "\n\n".join(context)

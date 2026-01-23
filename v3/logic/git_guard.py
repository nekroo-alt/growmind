import subprocess
from v3.data.db_manager import log_activity, fcid_mapping


class GitGuard:
    STABLE_FILES = ["v1/data/db_manager.py", "product.md", "technical.md"]

    @fcid_mapping("GIT-100")
    def is_clean(self):
        """
        Pre-flight check: Ensure the git workspace is clean.
        Returns True if clean, False otherwise.
        """
        try:
            # Check for modified files and staged changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            is_clean = len(result.stdout.strip()) == 0

            status = "Clean" if is_clean else "Dirty"
            log_activity(
                summary="Git Guard Pre-flight Check",
                action="is_clean",
                status=status,
                cot_blob=f"Git status porcelain output length: {len(result.stdout.strip())}",
            )

            return is_clean
        except subprocess.CalledProcessError as e:
            log_activity(
                summary="Git Guard Pre-flight Error",
                action="is_clean",
                status="Error",
                cot_blob=str(e),
            )
            return False

    @fcid_mapping("GIT-101")
    def check_policy(self):
        """
        Enforce line limit and Open-Closed principle.
        Returns (is_valid, error_message).
        """
        line_count = self._get_line_diff_count()
        line_limit = 100
        line_check = line_count <= line_limit
        oc_check = self._check_open_closed()

        errors = []
        if not line_check:
            errors.append(f"Lines changed: {line_count} exceeds limit of {line_limit}.")
        if not oc_check:
            errors.append(
                "Open-Closed Principle violation: Modified stable files (e.g., db_manager.py, product.md, technical.md)."
            )

        is_valid = len(errors) == 0
        status = "Passed" if is_valid else "Failed"
        error_msg = "; ".join(errors) if errors else ""

        log_activity(
            summary="Git Policy Check",
            action="check_policy",
            status=status,
            cot_blob=f"Lines changed: {line_count} (Limit: {line_limit}), Open-Closed: {oc_check}. Errors: {error_msg}",
        )
        return is_valid, error_msg

    def _get_line_diff_count(self):
        try:
            # Get per-file diff stats (additions, deletions, filename)
            result = subprocess.run(
                ["git", "diff", "--cached", "--numstat"],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            if not output:
                return 0

            total = 0
            for line in output.split("\n"):
                if not line.strip():
                    continue
                parts = line.split(None, 2)
                if len(parts) < 3:
                    continue

                add, delete, filename = parts[0], parts[1], parts[2]

                # Skip non-functional files: Markdown and Test scripts
                basename = filename.split("/")[-1]
                if filename.endswith(".md"):
                    continue
                if (
                    basename.startswith("test_")
                    or basename.endswith("_test.py")
                    or "/tests/" in filename
                    or filename.startswith("tests/")
                ):
                    continue

                # Add up additions and deletions for functional files
                # Handle binary files where add/delete might be '-'
                try:
                    total += int(add) if add != "-" else 0
                    total += int(delete) if delete != "-" else 0
                except ValueError:
                    continue

            return total
        except Exception:
            return 999  # Fail safe

    def _check_open_closed(self):
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
            )
            changed_files = [f for f in result.stdout.strip().split("\n") if f]
            for f in changed_files:
                if f in self.STABLE_FILES:
                    return False
            return True
        except Exception:
            return False

    @fcid_mapping("GIT-102")
    def commit(
        self,
        fcid,
        summary,
        files=None,
        cot="",
        tokens_used=None,
        prompt_tokens=None,
        completion_tokens=None,
        estimated_cost=None,
    ):
        """
        Finalize commit and record CoT in activity log.
        If files are provided, they are staged before commit.
        """
        if files:
            if isinstance(files, str):
                files = [files]
            try:
                subprocess.run(["git", "add"] + files, check=True)
            except subprocess.CalledProcessError as e:
                log_activity(
                    summary=summary,
                    action="Git Add",
                    status="Failed",
                    cot_blob=f"Error staging files {files}: {str(e)}",
                )
                return False, f"Error staging files: {str(e)}"

        is_valid, error_msg = self.check_policy()
        if not is_valid:
            return False, error_msg

        commit_msg = f"[{fcid}] {summary}"
        try:
            # Commit all staged changes atomically
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            hash_res = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True
            )
            commit_hash = hash_res.stdout.strip()

            log_activity(
                summary=summary,
                action="Git Commit",
                status="Success",
                cot_blob=cot,
                commit_hash=commit_hash,
                tokens_used=tokens_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost=estimated_cost,
            )
            return True, ""
        except subprocess.CalledProcessError as e:
            log_activity(
                summary=summary, action="Git Commit", status="Failed", cot_blob=str(e)
            )
            return False, str(e)

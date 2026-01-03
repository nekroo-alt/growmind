import subprocess
from v1.data.db_manager import log_activity, fcid_mapping


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
        """
        line_count = self._get_line_diff_count()
        line_limit = 100
        line_check = line_count <= line_limit
        oc_check = self._check_open_closed()

        is_valid = line_check and oc_check
        status = "Passed" if is_valid else "Failed"
        log_activity(
            summary="Git Policy Check",
            action="check_policy",
            status=status,
            cot_blob=f"Lines changed: {line_count} (Limit: {line_limit}), Open-Closed: {oc_check}",
        )
        return is_valid

    def _get_line_diff_count(self):
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--shortstat"],
                capture_output=True,
                text=True,
            )
            output = result.stdout.strip()
            if not output:
                return 0
            parts = output.split(",")
            total = 0
            for p in parts:
                if "insertion" in p or "deletion" in p:
                    total += int(p.split()[0].replace(",", ""))
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
                return False

        if not self.check_policy():
            return False

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
            return True
        except subprocess.CalledProcessError as e:
            log_activity(
                summary=summary, action="Git Commit", status="Failed", cot_blob=str(e)
            )
            return False

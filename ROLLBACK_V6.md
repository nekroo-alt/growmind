# V6 Rollback Plan

## Overview

This document outlines the procedures for rolling back from V6 to V5 in case critical issues are discovered after deployment.

**Target Rollback Time**: < 10 minutes  
**Last Updated**: 2026-01-27

---

## 1. Prerequisites for Rollback

### 1.1 Verify Rollback Readiness

Before attempting rollback, verify:

- [ ] Git repository is clean (no uncommitted changes)
- [ ] Current git commit is known (check `git log --oneline -1`)
- [ ] V6 commit hash is documented
- [ ] V5 commit hash is documented
- [ ] Database backups are available (if applicable)
- [ ] Configuration backups are available
- [ ] Team is notified of rollback

### 1.2 Required Tools

- Git CLI
- Python 3.8+ (for running tests)
- SQLite3 (if using task.db, telemetry.db, etc.)
- 10 minutes of uninterrupted time

---

## 2. V5 Commit Reference

### 2.1 Last Stable V5 Commit

**Commit Hash**: `3db8a5f85e65f36135ba719dec7c792c6b8761e4`  
**Message**: Last known stable V5 commit before V6 restructuring  
**Date**: 2026-01-26

### 2.2 V6 Commit Range

**Start Commit**: `3db8a5f85e65f36135ba719dec7c792c6b8761e4` (V5 baseline)  
**Latest V6 Commit**: `HEAD`  
**Commits in V6**: See CHANGELOG.md for detailed list

---

## 3. Rollback Procedures

### 3.1 Procedure A: Full Git Rollback (Recommended)

**When to Use**: All V6 changes need to be reverted

**Steps**:

1. **Stash or commit current changes** (if any)
   ```bash
   git status
   # If there are uncommitted changes:
   git stash save "Pre-rollback changes"
   # OR commit them if needed:
   git add .
   git commit -m "Pre-rollback checkpoint"
   ```

2. **Reset to V5 commit**
   ```bash
   git reset --hard 3db8a5f85e65f36135ba719dec7c792c6b8761e4
   ```

3. **Verify rollback**
   ```bash
   git log --oneline -3
   git diff HEAD~1..HEAD
   ```

4. **Run tests to verify V5 is working**
   ```bash
   pytest v5/tests/unit/ -v
   ```

5. **Reinstall dependencies if needed**
   ```bash
   pip install -e .
   ```

6. **Verify CLI commands work**
   ```bash
   l4-dev --help
   ```

**Estimated Time**: 5-7 minutes

---

### 3.2 Procedure B: Selective Rollback (Advanced)

**When to Use**: Only specific V6 changes need to be reverted

**Steps**:

1. **Identify V6 commits to revert**
   ```bash
   git log --oneline 3db8a5f..HEAD
   ```

2. **Revert specific commits** (reverse chronological order)
   ```bash
   git revert <commit-hash-1>
   git revert <commit-hash-2>
   # etc.
   ```

3. **Resolve conflicts if any**
   - Review conflicts carefully
   - Merge manually
   - `git add <resolved-files>`
   - `git revert --continue`

4. **Verify and test**
   ```bash
   pytest v5/tests/unit/ -v
   ```

**Estimated Time**: 10-20 minutes (depends on number of commits)

---

### 3.3 Procedure C: Branch-Based Rollback (Alternative)

**When to Use**: Want to preserve V6 changes for later recovery

**Steps**:

1. **Create backup branch of V6**
   ```bash
   git checkout -b v6-backup-$(date +%Y%m%d-%H%M%S)
   git push origin v6-backup-$(date +%Y%m%d-%H%M%S)
   ```

2. **Reset to V5 commit**
   ```bash
   git checkout main  # or your branch
   git reset --hard 3db8a5f85e65f36135ba719dec7c792c6b8761e4
   ```

3. **Push V5 to main**
   ```bash
   git push --force origin main
   ```

4. **Verify and test**
   ```bash
   pytest v5/tests/unit/ -v
   ```

**Estimated Time**: 7-10 minutes

---

## 4. Data Migration Considerations

### 4.1 Database Considerations

**V6 Databases**:
- `task.db` - Task tracking (V6 schema may differ)
- `activity.db` - Activity logs (V6 schema may differ)
- `telemetry.db` - Telemetry data (V6 only, new in V6)
- `snapshots.db` - Checkpoint data (V6 only, new in V6)
- `sessions.db` - Session data (V6 only, new in V6)

**Rollback Strategy**:

1. **Backup V6 databases** before rollback
   ```bash
   cp task.db task.db.v6-backup
   cp activity.db activity.db.v6-backup
   cp telemetry.db telemetry.db.v6-backup  # if exists
   cp snapshots.db snapshots.db.v6-backup    # if exists
   cp sessions.db sessions.db.v6-backup      # if exists
   ```

2. **After rollback to V5**:
   - V5 will use V5 schema for `task.db` and `activity.db`
   - V6-specific databases (`telemetry.db`, `snapshots.db`, `sessions.db`) are not used by V5
   - Data in V6-specific databases will be preserved but inaccessible in V5

3. **If data migration is critical**:
   - Export V6 data to CSV/JSON before rollback
   - Re-import to V5 if compatible
   - **Warning**: Complex migrations may require manual intervention

### 4.2 Configuration Migration

**V6 Configuration Variables** (if using V6-specific settings):
- V6 may have added new environment variables
- V6 may have modified existing variable defaults

**Rollback Strategy**:

1. **Backup V6 configuration**
   ```bash
   cp .env .env.v6-backup  # if using .env
   env | grep L4_ > v6-env-backup.txt
   ```

2. **After rollback to V5**:
   - V5 will use V5 configuration defaults
   - Remove V6-specific variables from `.env` or environment
   - Restore V5-specific variables if needed

### 4.3 Cache Data

**V6 Cache**:
- `.l4_cache/` directory
- May contain V6-specific cache data

**Rollback Strategy**:
- Option 1: Delete cache directory (V5 will rebuild)
  ```bash
  rm -rf .l4_cache/
  ```
- Option 2: Keep cache (V5 may or may not work with V6 cache)
  ```bash
  mv .l4_cache/ .l4_cache.v6-backup/
  ```

**Recommendation**: Delete cache directory to ensure clean V5 state

---

## 5. Testing After Rollback

### 5.1 Critical Tests to Run

1. **CLI Commands**
   ```bash
   l4-dev --help
   l4-dev start --help
   l4-dev status --help
   ```

2. **Unit Tests**
   ```bash
   pytest v5/tests/unit/core/ -v
   pytest v5/tests/unit/data/ -v
   pytest v5/tests/unit/logic/ -v
   ```

3. **Database Operations**
   ```bash
   python -c "from v5.data.db_manager import DBManager; db = DBManager(); print('DB OK')"
   ```

4. **Git Operations**
   ```bash
   git status
   git log --oneline -1
   ```

### 5.2 Expected V5 Behavior

- Single CLI file: `v5/l4_cli.py`
- Test structure: Tests in `v5/tests/unit/` (no subdirectories)
- No V6 features: No telemetry, checkpointing, session management
- V5 CLI commands: V3, V4 commands only (no V5 commands)

---

## 6. Known Issues That May Require Rollback

### 6.1 Critical Issues

**Rollback Trigger**: Any of these issues should trigger immediate rollback

1. **Data Loss**: V6 causes data corruption or loss in `task.db` or `activity.db`
2. **Total Test Failure**: < 70% of tests passing after V6 deployment
3. **CLI Breakage**: Critical CLI commands fail (start, status, logs)
4. **Git Integration Failure**: V6 causes git operations to fail
5. **Performance Degradation**: V6 slows down operations by > 50%

### 6.2 Non-Critical Issues (Do NOT Rollback)

**These issues do NOT require rollback**:

1. Cosmetic UI issues (color codes, progress bars)
2. Missing optional features (V5-specific commands)
3. Test failures in non-critical modules (< 20% of tests)
4. Documentation discrepancies
5. Configuration warnings

### 6.3 Common V6 Issues

**Issue**: Import errors after V6 restructuring  
**Solution**: Check import paths in `v5/__init__.py` and subdirectories

**Issue**: CLI commands not found  
**Solution**: Verify `setup.py` entry point points to `v5.l4_cli:main`

**Issue**: Tests not found after reorganization  
**Solution**: Run `pytest v5/tests/unit/` with `-v` flag to see discovery details

---

## 7. Rollback Validation Checklist

After completing rollback, verify:

- [ ] Git commit shows V5 hash (3db8a5f)
- [ ] `l4-dev --help` shows V3/V4 commands only
- [ ] Unit tests pass (> 90%)
- [ ] Database operations work (task.db, activity.db)
- [ ] No V6-specific features accessible
- [ ] Configuration uses V5 defaults
- [ ] Team notified of rollback completion

---

## 8. Recovery After Rollback

### 8.1 Document the Issue

- Document why rollback was necessary
- File bug report for V6 issue
- Include logs, error messages, reproduction steps
- Tag issue as "V6-critical"

### 8.2 Fix V6 Issue

- Create feature branch from V6 backup
- Fix the issue
- Test thoroughly
- Get code review
- Re-deploy V6 fix

### 8.3 Re-deploy V6

After fix is verified:

1. Test V6 fix in staging environment
2. Merge fix to main branch
3. Deploy to production
4. Monitor for 24-48 hours
5. Keep rollback plan ready

---

## 9. Rollback Best Practices

### 9.1 Before V6 Deployment

- Create V6 backup branch
- Backup all databases
- Backup configuration
- Run full test suite on V6
- Document V6 changes
- Notify team of deployment

### 9.2 During Rollback

- Stay calm and follow procedure
- Communicate with team
- Document rollback process
- Keep backup branch safe
- Verify each step

### 9.3 After Rollback

- Analyze what went wrong
- Document lessons learned
- Fix V6 issue
- Test V6 fix thoroughly
- Update rollback plan if needed

---

## 10. Emergency Contacts

**Lead Developer**: [Name] - [Email] - [Phone]  
**DevOps**: [Name] - [Email] - [Phone]  
**Product Owner**: [Name] - [Email] - [Phone]  
**On-Call Rotation**: [Name] - [Phone]

---

## 11. References

- **V5 Last Stable Commit**: 3db8a5f85e65f36135ba719dec7c792c6b8761e4
- **V6 Documentation**: See `v5/v6_tasks.md` for all V6 changes
- **V6 Changelog**: See `CHANGELOG.md` for detailed V6 changes
- **V5 Architecture**: See `meta/tech.md` for V5 architecture
- **Migration Guide**: See `v5/docs/MIGRATION_V5_TO_V6.md` for V5→V6 migration

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-27  
**Maintainer**: L4D Development Team
# Git Push & Remote Hostinger Staging Invariant

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: ATOMIC GIT PUSH (HOSTINGER REFLECTION) 🚨
> Every single code modification, bug fix, view adjustment, or refactor executed in this workspace MUST be pushed to `origin main` before concluding the turn.

### Protocol:
1. Complete local validation:
   - `docker exec odoo19_garage odoo -u <modules> -d garage_db --stop-after-init` -> 0 error / warning.
   - Python ORM view compilation test (`get_views`) -> OK.
   - Deprecated pattern grep check -> 0 matches.
   - AST knowledge graph update: `graphify update .`.
2. Stage and commit all modified files:
   ```bash
   git add <modified_files>
   git commit -m "feat/fix: <clear description>"
   ```
3. Push to remote repository:
   ```bash
   git push origin main
   ```
4. Confirm remote reception:
   The Hostinger VPS staging server (`167.233.156.220`) pulls from `origin main`. Unpushed changes leave the live server in an outdated state and prevent the user from seeing live reflections.

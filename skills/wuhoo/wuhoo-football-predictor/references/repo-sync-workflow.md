# Repo Sync Workflow (老规矩)

After any code changes to the football predictor skill, follow this commit-and-sync workflow:

## Step 1: Commit in wuhoo-workspace

```bash
cd /home/admin/wuhoo-workspace
git add skills/wuhoo/wuhoo-football-predictor/
git commit -m "<descriptive message>"
```

## Step 2: Push wuhoo-workspace

```bash
git push origin hermes-agent
```

## Step 3: Sync to wuhoo-skills

```bash
cp -r /home/admin/wuhoo-workspace/skills/wuhoo/wuhoo-football-predictor/* \
      /home/admin/wuhoo-skills/wuhoo-football-predictor/
```

## Step 4: Commit and push wuhoo-skills

```bash
cd /home/admin/wuhoo-skills
git add wuhoo-football-predictor/
git commit -m "<message> — sync from wuhoo-workspace"
git push origin master
```

## Notes

- Both repos must be pushed — cron jobs reference skills from the skill registry
- wuhoo-skills is a standalone repo (not a submodule)
- Use the same commit message prefix for traceability across repos
- SKILL.md must be kept in sync between both copies

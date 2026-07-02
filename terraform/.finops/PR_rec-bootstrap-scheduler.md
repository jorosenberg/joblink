# chore(finops): bootstrap instance-scheduler (scheduler_bootstrap) for cost optimization

## Description

- **Target Resource:** instance-scheduler (`(new infrastructure)`)
- **Current Configuration:** scheduler=not deployed
- **Optimized Configuration:** scheduler=finops Lambda scheduler, schedules=mon-fri-08-18, mon-fri-07-20, daily-08-18, daily-00-03, timezone=America/New_York
- **Projected Savings:** $0.00/month (~$0.00/year)
- **Justification:** Finding **SchedulerMissing** — note = enables Schedule tags drafted by draft_schedule over a 0-day lookback.

## Changes

- `finops-scheduler.tf` line 1: `(new file)` → `finops-scheduler.tf (95 lines)`
- `finops_scheduler_lambda.py` line 1: `(new file)` → `finops_scheduler_lambda.py (75 lines)`

## Verification Logs

Verification passed: **True** · Diff-scope guard: **True** (only allowlisted attributes touched)

### HCL syntax lint (terraform binary unavailable in this environment)

```
E:\job scraper\terraform\finops-scheduler.tf: ok
E:\job scraper\terraform\finops_scheduler_lambda.py: ok
```

### Diff

```diff

```

---
*Generated automatically by finops-mcp. Review and merge — changes are never applied directly to the cloud environment.*

# Claude Code Entry Guide

Follow all repository rules and hard boundaries in [AGENTS.md](AGENTS.md).

## Common Workflows

- **Real-to-Sim Photo/Video Reconstruction & Out-of-Domain Scene Factory**:
  1. Start with the step-by-step quickstart and prompt templates in [docs/operations/real2sim-and-scene-factory-quickstart.md](docs/operations/real2sim-and-scene-factory-quickstart.md).
  2. Read the orchestration skill at [skills/agentic-scene-factory/SKILL.md](skills/agentic-scene-factory/SKILL.md) and the articulated CAD OpenUSD skill at [skills/hunyuan-isaac-articulation-assets/SKILL.md](skills/hunyuan-isaac-articulation-assets/SKILL.md).
  3. Read applicable scene-authoring standards (`GEN-001`..`GEN-010`) starting from [docs/standards/README.md](docs/standards/README.md).
  4. Never self-grade visual renders: delegate blind visual review to the isolated subagent in [.claude/agents/visual-critic.md](.claude/agents/visual-critic.md) and validate the resulting JSON with `skills/agentic-scene-factory/scripts/run_independent_visual_critic.py`.

## Verification Commands

- Standalone / CI check (no local `/cpfs` artifacts or Isaac Sim required):
  ```bash
  make ci-check
  ```
- Full internal check (when `/cpfs` fixtures are mounted):
  ```bash
  make check
  ```

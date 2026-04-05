---
name: testing-agents
description: List of AI agent personas from agency-agents repo for the Testing domain
tags: [agents, Testing]
---

# Testing Agents

## Available Agents
| Agent | Description |
|-------|-------------|
| accessibility-auditor | Expert accessibility specialist who audits interfaces against WCAG standards, tests with assistive technologies, and ensures inclusive design. Defaults to finding barriers — if it's not tested with a screen reader, it's not accessible. |
| api-tester | Expert API testing specialist focused on comprehensive API validation, performance testing, and quality assurance across all systems and third-party integrations |
| evidence-collector | Screenshot-obsessed, fantasy-allergic QA specialist - Default to finding 3-5 issues, requires visual proof for everything |
| performance-benchmarker | Expert performance testing and optimization specialist focused on measuring, analyzing, and improving system performance across all applications and infrastructure |
| reality-checker | Stops fantasy approvals, evidence-based certification - Default to "NEEDS WORK", requires overwhelming proof for production readiness |
| test-results-analyzer | Expert test analysis specialist focused on comprehensive test result evaluation, quality metrics analysis, and actionable insight generation from testing activities |
| tool-evaluator | Expert technology assessment specialist focused on evaluating, testing, and recommending tools, software, and platforms for business use and productivity optimization |
| workflow-optimizer | Expert process improvement specialist focused on analyzing, optimizing, and automating workflows across all business functions for maximum productivity and efficiency |
## Quick Reference
- Total agents: 8
- Run any with: agent_view('testing/agent-name') or delegate_task(goal='...', context='Load skill testing/agent-name first')

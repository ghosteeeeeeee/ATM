---
name: engineering-agents
description: List of AI agent personas from agency-agents repo for the Engineering domain
tags: [agents, Engineering]
---

# Engineering Agents

## Available Agents
| Agent | Description |
|-------|-------------|
| ai-data-remediation-engineer | Specialist in self-healing data pipelines — uses air-gapped local SLMs and semantic clustering to automatically detect, classify, and fix data anomalies at scale. Focuses exclusively on the remediation layer: intercepting bad data, generating deterministic fix logic via Ollama, and guaranteeing zero data loss. Not a general data engineer — a surgical specialist for when your data is broken and the pipeline can't stop. |
| ai-engineer | Expert AI/ML engineer specializing in machine learning model development, deployment, and integration into production systems. Focused on building intelligent features, data pipelines, and AI-powered applications with emphasis on practical, scalable solutions. |
| autonomous-optimization-architect | Intelligent system governor that continuously shadow-tests APIs for performance while enforcing strict financial and security guardrails against runaway costs. |
| backend-architect | Senior backend architect specializing in scalable system design, database architecture, API development, and cloud infrastructure. Builds robust, secure, performant server-side applications and microservices |
| cms-developer | Drupal and WordPress specialist for theme development, custom plugins/modules, content architecture, and code-first CMS implementation |
| code-reviewer | Expert code reviewer who provides constructive, actionable feedback focused on correctness, maintainability, security, and performance — not style preferences. |
| database-optimizer | Expert database specialist focusing on schema design, query optimization, indexing strategies, and performance tuning for PostgreSQL, MySQL, and modern databases like Supabase and PlanetScale. |
| data-engineer | Expert data engineer specializing in building reliable data pipelines, lakehouse architectures, and scalable data infrastructure. Masters ETL/ELT, Apache Spark, dbt, streaming systems, and cloud data platforms to turn raw data into trusted, analytics-ready assets. |
| devops-automator | Expert DevOps engineer specializing in infrastructure automation, CI/CD pipeline development, and cloud operations |
| email-intelligence-engineer | Expert in extracting structured, reasoning-ready data from raw email threads for AI agents and automation systems |
| embedded-firmware-engineer | Specialist in bare-metal and RTOS firmware - ESP32/ESP-IDF, PlatformIO, Arduino, ARM Cortex-M, STM32 HAL/LL, Nordic nRF5/nRF Connect SDK, FreeRTOS, Zephyr |
| feishu-integration-developer | Full-stack integration expert specializing in the Feishu (Lark) Open Platform — proficient in Feishu bots, mini programs, approval workflows, Bitable (multidimensional spreadsheets), interactive message cards, Webhooks, SSO authentication, and workflow automation, building enterprise-grade collaboration and automation solutions within the Feishu ecosystem. |
| filament-optimization-specialist | Expert in restructuring and optimizing Filament PHP admin interfaces for maximum usability and efficiency. Focuses on impactful structural changes — not just cosmetic tweaks. |
| frontend-developer | Expert frontend developer specializing in modern web technologies, React/Vue/Angular frameworks, UI implementation, and performance optimization |
| git-workflow-master | Expert in Git workflows, branching strategies, and version control best practices including conventional commits, rebasing, worktrees, and CI-friendly branch management. |
| incident-response-commander | Expert incident commander specializing in production incident management, structured response coordination, post-mortem facilitation, SLO/SLI tracking, and on-call process design for reliable engineering organizations. |
| mobile-app-builder | Specialized mobile application developer with expertise in native iOS/Android development and cross-platform frameworks |
| rapid-prototyper | Specialized in ultra-fast proof-of-concept development and MVP creation using efficient tools and frameworks |
| security-engineer | Expert application security engineer specializing in threat modeling, vulnerability assessment, secure code review, security architecture design, and incident response for modern web, API, and cloud-native applications. |
| senior-developer | Premium implementation specialist - Masters Laravel/Livewire/FluxUI, advanced CSS, Three.js integration |
| software-architect | Expert software architect specializing in system design, domain-driven design, architectural patterns, and technical decision-making for scalable, maintainable systems. |
| solidity-smart-contract-engineer | Expert Solidity developer specializing in EVM smart contract architecture, gas optimization, upgradeable proxy patterns, DeFi protocol development, and security-first contract design across Ethereum and L2 chains. |
| sre | Expert site reliability engineer specializing in SLOs, error budgets, observability, chaos engineering, and toil reduction for production systems at scale. |
| technical-writer | Expert technical writer specializing in developer documentation, API references, README files, and tutorials. Transforms complex engineering concepts into clear, accurate, and engaging docs that developers actually read and use. |
| threat-detection-engineer | Expert detection engineer specializing in SIEM rule development, MITRE ATT&CK coverage mapping, threat hunting, alert tuning, and detection-as-code pipelines for security operations teams. |
| wechat-mini-program-developer | Expert WeChat Mini Program developer specializing in 小程序 development with WXML/WXSS/WXS, WeChat API integration, payment systems, subscription messaging, and the full WeChat ecosystem. |
## Quick Reference
- Total agents: 26
- Run any with: agent_view('engineering/agent-name') or delegate_task(goal='...', context='Load skill engineering/agent-name first')

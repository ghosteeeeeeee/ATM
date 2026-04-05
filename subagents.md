# Subagents

Repository of 150+ AI agent personas organized by domain. Each agent is a markdown file defining role, instructions, and expertise — used with `delegate_task` for specialized sub-agents.

**Location:** `/root/.hermes/subagents/`

---

## Quick Index

| Category | Count | Agents |
|----------|-------|--------|
| [Academic](#academic) | 5 | anthropologist, geographer, historian, narratologist, psychologist |
| [Design](#design) | 8 | brand-guardian, image-prompt-engineer, inclusive-visuals-specialist, ui-designer, ux-architect, ux-researcher, visual-storyteller, whimsy-injector |
| [Engineering](#engineering) | 26 | ai-data-remediation-engineer, ai-engineer, autonomous-optimization-architect, backend-architect, cms-developer, code-reviewer, data-engineer, database-optimizer, devops-automator, email-intelligence-engineer, embedded-firmware-engineer, feishu-integration-developer, filament-optimization-specialist, frontend-developer, git-workflow-master, incident-response-commander, mobile-app-builder, rapid-prototyper, security-engineer, senior-developer, software-architect, solidity-smart-contract-engineer, sre, technical-writer, threat-detection-engineer, wechat-mini-program-developer |
| [Examples](#examples) | 5 | nexus-spatial-discovery, workflow-book-chapter, workflow-landing-page, workflow-startup-mvp, workflow-with-memory |
| [Game Development](#game-development) | 5 | game-audio-engineer, game-designer, level-designer, narrative-designer, technical-artist |
| [Integrations](#integrations) | 1 | INTEGRATIONS-README |
| [Marketing](#marketing) | 29 | ai-citation-strategist, app-store-optimizer, baidu-seo-specialist, bilibili-content-strategist, book-co-author, carousel-growth-engine, china-ecommerce-operator, china-market-localization-strategist, content-creator, cross-border-ecommerce, douyin-strategist, growth-hacker, instagram-curator, kuaishou-strategist, linkedin-content-creator, livestream-commerce-coach, podcast-strategist, private-domain-operator, reddit-community-builder, seo-specialist, short-video-editing-coach, social-media-strategist, tiktok-strategist, twitter-engager, video-optimization-specialist, wechat-official-account, weibo-strategist, xiaohongshu-specialist, zhihu-strategist |
| [Paid Media](#paid-media) | 7 | auditor, creative-strategist, paid-social-strategist, ppc-strategist, programmatic-buyer, search-query-analyst, tracking-specialist |
| [Product](#product) | 5 | behavioral-nudge-engine, feedback-synthesizer, manager, sprint-prioritizer, trend-researcher |
| [Project Management](#project-management) | 6 | experiment-tracker, jira-workflow-steward, project-manager-senior, project-shepherd, studio-operations, studio-producer |
| [Sales](#sales) | 8 | account-strategist, coach, deal-strategist, discovery-coach, engineer, outbound-strategist, pipeline-analyst, proposal-strategist |
| [Spatial Computing](#spatial-computing) | 6 | macos-spatial-metal-engineer, terminal-integration-specialist, visionos-spatial-engineer, xr-cockpit-interaction-specialist, xr-immersive-developer, xr-interface-architect |
| [Specialized](#specialized) | 28 | accounts-payable-agent, agentic-identity-trust, agents-orchestrator, automation-governance-architect, blockchain-security-auditor, civil-engineer, compliance-auditor, corporate-training-designer, cultural-intelligence-strategist, data-consolidation-agent, developer-advocate, document-generator, french-consulting-market, government-digital-presales-consultant, healthcare-marketing-compliance, identity-graph-operator, korean-business-navigator, lsp-index-engineer, mcp-builder, model-qa, recruitment-specialist, report-distribution-agent, sales-data-extraction-agent, salesforce-architect, study-abroad-advisor, supply-chain-strategist, workflow-architect, zk-steward |
| [Strategy](#strategy) | 3 | EXECUTIVE-BRIEF, QUICKSTART, nexus-strategy |
| [Support](#support) | 6 | analytics-reporter, executive-summary-generator, finance-tracker, infrastructure-maintainer, legal-compliance-checker, support-responder |
| [Testing](#testing) | 8 | accessibility-auditor, api-tester, evidence-collector, performance-benchmarker, reality-checker, test-results-analyzer, tool-evaluator, workflow-optimizer |

**Total: 155 agents across 16 categories**

---

## Academic (5 agents)

Expert agents in scholarly disciplines for research, analysis, and domain knowledge.

- **anthropologist** — Expert in cultural systems, rituals, kinship, belief systems
- **geographer** — Expert in spatial analysis, human geography, GIS
- **historian** — Expert in historical research, source analysis, chronology
- **narratologist** — Expert in narrative structures, storytelling, plot analysis
- **psychologist** — Expert in cognitive/behavioral psychology, research methods

## Design (8 agents)

Visual and UX design agents for brand, product, and content design work.

- **brand-guardian** — Expert brand strategist specializing in brand identity protection and consistency
- **image-prompt-engineer** — Expert at crafting prompts for AI image generation (Midjourney, DALL-E, Stable Diffusion)
- **inclusive-visuals-specialist** — Expert in accessible and inclusive visual content
- **ui-designer** — Expert in user interface design for web and mobile
- **ux-architect** — Expert in end-to-end user experience architecture and information design
- **ux-researcher** — Expert in user research methodologies, usability testing, persona development
- **visual-storyteller** — Expert in visual narrative and infographic design
- **whimsy-injector** — Creative specialist for adding personality, humor, and delight to designs

## Engineering (26 agents)

Full-spectrum software engineering agents across backend, frontend, DevOps, security, and specialized domains.

- **ai-data-remediation-engineer** — Specialist in self-healing data pipelines, data quality, ETL remediation
- **ai-engineer** — Expert AI/ML engineer for building and integrating AI systems
- **autonomous-optimization-architect** — Architect for self-optimizing autonomous systems
- **backend-architect** — Expert in scalable backend systems, APIs, microservices
- **cms-developer** — Expert in content management system development and customization
- **code-reviewer** — Expert in thorough code review with security and performance focus
- **data-engineer** — Expert in data pipelines, warehousing, and ETL/ELT
- **database-optimizer** — Expert in database performance tuning, indexing, query optimization
- **devops-automator** — Expert in CI/CD, infrastructure automation, containerization
- **email-intelligence-engineer** — Expert in email systems, intelligence, and automation
- **embedded-firmware-engineer** — Expert in embedded systems and firmware development
- **feishu-integration-developer** — Expert in Feishu (Lark) platform integration development
- **filament-optimization-specialist** — Expert in Filament (Laravel) optimization
- **frontend-developer** — Expert in modern frontend development (React, Vue, etc.)
- **git-workflow-master** — Expert in Git workflows, branching strategies, and team git hygiene
- **incident-response-commander** — Expert in incident management and post-mortem analysis
- **mobile-app-builder** — Expert in mobile application development (iOS, Android, cross-platform)
- **rapid-prototyper** — Expert in quickly turning ideas into functional prototypes
- **security-engineer** — Expert in application security, penetration testing, secure coding
- **senior-developer** — Senior generalist software developer for complex problem solving
- **software-architect** — Expert in system architecture, design patterns, tech stack selection
- **solidity-smart-contract-engineer** — Expert in Solidity, EVM, DeFi smart contracts
- **sre** — Expert in Site Reliability Engineering, monitoring, on-call
- **technical-writer** — Expert in technical documentation, API docs, developer guides
- **threat-detection-engineer** — Expert in security monitoring, threat detection, SIEM
- **wechat-mini-program-developer** — Expert in WeChat Mini Program development

## Examples (5 agents)

Multi-agent workflow demonstrations showing orchestration patterns.

- **nexus-spatial-discovery** — Full agency discovery exercise using multiple agents
- **workflow-book-chapter** — Multi-agent workflow for book chapter development
- **workflow-landing-page** — Multi-agent landing page sprint workflow
- **workflow-startup-mvp** — Multi-agent startup MVP development workflow
- **workflow-with-memory** — Multi-agent workflow with persistent memory

## Game Development (5 agents)

Specialized agents for game design, audio, narrative, and technical art.

- **game-audio-engineer** — Expert in interactive audio, sound design, Wwise, FMOD
- **game-designer** — Expert in game mechanics, balance, progression systems
- **level-designer** — Expert in level design, environment creation, flow
- **narrative-designer** — Expert in game narrative, dialogue, world-building
- **technical-artist** — Expert in game technical art, shaders, pipeline tools

## Integrations (1 agent)

- **INTEGRATIONS-README** — Directory containing The Agency integration agents

## Marketing (29 agents)

Comprehensive marketing agents covering China platforms, content, social media, SEO, and growth.

- **ai-citation-strategist** — Expert in AI recommendation engine optimization and citation strategies
- **app-store-optimization** — Expert in ASO, app store listing optimization
- **baidu-seo-specialist** — Expert in Baidu SEO and Chinese search engine optimization
- **bilibili-content-strategist** — Expert in Bilibili content strategy and video marketing
- **book-co-author** — Expert in co-authoring books and long-form content
- **carousel-growth-engine** — Expert in carousel content for social growth (Instagram, LinkedIn)
- **china-ecommerce-operator** — Expert in Chinese e-commerce platform operations (Taobao, JD, etc.)
- **china-market-localization-strategist** — Expert in China market localization and go-to-market
- **content-creator** — Expert in marketing content creation across formats
- **cross-border-ecommerce** — Expert in cross-border e-commerce operations
- **douyin-strategist** — Expert in Douyin (TikTok China) marketing and commerce
- **growth-hacker** — Expert in growth hacking, viral loops, acquisition experiments
- **instagram-curator** — Expert in Instagram content curation and growth
- **kuaishou-strategist** — Expert in Kuaishou short video platform strategy
- **linkedin-content-creator** — Expert in LinkedIn content creation and thought leadership
- **livestream-commerce-coach** — Expert in live commerce strategy and execution
- **podcast-strategist** — Expert in podcast strategy, production, distribution
- **private-domain-operator** — Expert in private domain (WeChat ecosystem) operations
- **reddit-community-builder** — Expert in Reddit community building and engagement
- **seo-specialist** — Expert in SEO strategy, technical SEO, link building
- **short-video-editing-coach** — Expert in short-form video editing and optimization
- **social-media-strategist** — Expert in social media strategy across platforms
- **tiktok-strategist** — Expert in TikTok marketing and creator economy
- **twitter-engager** — Expert in X/Twitter engagement, growth, community management
- **video-optimization-specialist** — Expert in video SEO and platform optimization
- **wechat-official-account** — Expert in WeChat Official Account operations
- **weibo-strategist** — Expert in Weibo marketing and social engagement
- **xiaohongshu-specialist** — Expert in Xiaohongshu (RED) platform marketing
- **zhihu-strategist** — Expert in Zhihu (Chinese Quora) content and marketing strategy

## Paid Media (7 agents)

Paid advertising agents across search, social, programmatic, and display.

- **auditor** — Comprehensive paid media auditor for systematic campaign audits
- **creative-strategist** — Expert in paid ad creative strategy and copywriting
- **paid-social-strategist** — Expert in paid social advertising (Meta, LinkedIn, etc.)
- **ppc-strategist** — Expert in PPC campaign strategy (Google, Bing)
- **programmatic-buyer** — Expert in programmatic advertising and display buying
- **search-query-analyst** — Expert in paid search query analysis and optimization
- **tracking-specialist** — Expert in paid media tracking, attribution, and measurement

## Product (5 agents)

Product management agents for strategy, prioritization, and research.

- **behavioral-nudge-engine** — Behavioral psychology specialist for product nudges and engagement
- **feedback-synthesizer** — Expert in synthesizing product feedback from multiple sources
- **manager** — Expert product manager for strategy, roadmap, stakeholder alignment
- **sprint-prioritizer** — Expert in agile sprint prioritization and backlog refinement
- **trend-researcher** — Expert in product trend research and competitive analysis

## Project Management (6 agents)

Project and program management agents across methodologies.

- **experiment-tracker** — Expert in experiment tracking, A/B test management, statistical rigor
- **jira-workflow-steward** — Expert in Jira workflows, tickets, and sprint management
- **project-manager-senior** — Senior PM for complex multi-team projects
- **project-shepherd** — Agent focused on shepherding projects to completion
- **studio-operations** — Expert in creative studio operations and production management
- **studio-producer** — Expert in creative production, timelines, resource management

## Sales (8 agents)

Sales agents covering the full cycle from prospecting to deal closure.

- **account-strategist** — Expert in post-sale account strategy and expansion
- **coach** — Expert sales coach for methodology and skills development
- **deal-strategist** — Expert in deal strategy, negotiation, and closing
- **discovery-coach** — Expert in sales discovery call preparation and techniques
- **engineer** — Expert sales engineer for technical sales support
- **outbound-strategist** — Expert in outbound prospecting and pipeline generation
- **pipeline-analyst** — Expert in sales pipeline analysis and forecasting
- **proposal-strategist** — Expert in proposal and RFP response strategy

## Spatial Computing (6 agents)

Specialized agents for XR/AR/VR, visionOS, and spatial computing development.

- **macos-spatial-metal-engineer** — Expert in macOS spatial computing with Metal
- **terminal-integration-specialist** — Expert in terminal integration for spatial interfaces
- **visionos-spatial-engineer** — Expert in visionOS app development (Apple Vision Pro)
- **xr-cockpit-interaction-specialist** — Expert in XR cockpit UI/UX design and interaction
- **xr-immersive-developer** — Expert in immersive XR application development
- **xr-interface-architect** — Expert in spatial interface design and human-XR interaction

## Specialized (28 agents)

Domain-specific agents for compliance, blockchain, healthcare, language markets, and more.

- **accounts-payable-agent** — Autonomous payment processing specialist
- **agentic-identity-trust** — Architect for agentic identity and trust frameworks
- **agents-orchestrator** — Orchestrator for managing multiple AI agents
- **automation-governance-architect** — Architect for automation governance frameworks
- **blockchain-security-auditor** — Expert in blockchain and smart contract security auditing
- **civil-engineer** — Expert in civil engineering analysis and documentation
- **compliance-auditor** — Expert in regulatory compliance auditing
- **corporate-training-designer** — Expert in corporate training program design
- **cultural-intelligence-strategist** — Expert in cross-cultural business strategy
- **data-consolidation-agent** — Agent for consolidating data from multiple sources
- **developer-advocate** — Expert developer advocate for community and developer relations
- **document-generator** — Expert in automated document generation
- **french-consulting-market** — Expert in French-speaking consulting market
- **government-digital-presales-consultant** — Expert in government digital transformation sales
- **healthcare-marketing-compliance** — Expert in healthcare marketing regulations (FDA, HIPAA)
- **identity-graph-operator** — Expert in identity resolution and identity graph management
- **korean-business-navigator** — Expert in Korean market business navigation
- **lsp-index-engineer** — Expert in LSP/indexing systems
- **mcp-builder** — Expert in building MCP (Model Context Protocol) integrations
- **model-qa** — Specialist in LLM/model quality assurance
- **recruitment-specialist** — Expert in technical recruitment and talent acquisition
- **report-distribution-agent** — Agent for automated report generation and distribution
- **sales-data-extraction-agent** — Agent for extracting and structuring sales data
- **salesforce-architect** — Expert in Salesforce architecture and customization
- **study-abroad-advisor** — Expert study abroad program advisor
- **supply-chain-strategist** — Expert in supply chain strategy and optimization
- **workflow-architect** — Expert in workflow design and automation architecture
- **zk-steward** — Expert in zero-knowledge proofs and ZK technology stewardship

## Strategy (3 agents)

Strategic planning agents, including the NEXUS agency framework.

- **EXECUTIVE-BRIEF** — Executive brief template for NEXUS agency engagements
- **QUICKSTART** — Quick-start guide for the NEXUS multi-agent framework
- **nexus-strategy** — NEXUS: Network of EXperts, Unified in Strategy — coordination layer for orchestrating multiple specialized agents

## Support (6 agents)

Customer support and operations agents.

- **analytics-reporter** — Expert data analyst for support metrics and reporting
- **executive-summary-generator** — Agent for generating executive summaries
- **finance-tracker** — Agent for financial tracking and reporting
- **infrastructure-maintainer** — Agent for infrastructure monitoring and maintenance
- **legal-compliance-checker** — Agent for legal compliance verification
- **support-responder** — Expert in customer support response composition

## Testing (8 agents)

QA and testing agents for code, APIs, accessibility, performance, and workflows.

- **accessibility-auditor** — Expert accessibility specialist (WCAG, ADA compliance)
- **api-tester** — Expert in API testing, contract testing, integration testing
- **evidence-collector** — QA agent for evidence gathering and documentation
- **performance-benchmarker** — Expert in performance testing and benchmarking
- **reality-checker** — Integration agent for reality verification
- **test-results-analyzer** — Expert in test results analysis and reporting
- **tool-evaluator** — Specialist in evaluating and comparing tools
- **workflow-optimizer** — Expert in optimizing AI agent workflows

---

## Usage

Each agent is a markdown file loaded with `delegate_task`. See individual SKILL.md files in each category for per-domain agent listings with full descriptions.

## Adding New Agents

Place new `.md` files in the appropriate category directory under `/root/.hermes/subagents/`. Each file should have:
- A clear `# Agent Name` title
- Role/instructions in the body
- A frontmatter `---` block with name, description, tags

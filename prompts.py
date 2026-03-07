SYSTEM_PROMPT = """You are an expert Project Management AI Agent specialized in building AI-powered trading bots.
Your role is to plan, organize, and guide the implementation of the Trading Bot project
with Claude API integration, sentiment analysis, and geopolitical risk assessment.

PROJECT CONTEXT:
- Building: AI-powered trading bot analyzing stocks, ETFs, and gold
- Timeline: 9 weeks total (Phase 1: 5 weeks, Phase 2: 4 weeks, Phase 3: 8+ weeks)
- Team: 7-9 people (backend, frontend, DevOps, QA, analysis)
- Budget: $310k-410k for Phase 1
- Tech Stack: Node.js API, Python Bot, React Dashboard, PostgreSQL, Redis
- Architecture: Microservices (stateless API + Bot Engine + Services)

YOUR RESPONSIBILITIES:
1. Break down the project into concrete, actionable steps
2. Create detailed implementation roadmaps with timelines
3. Identify dependencies and critical path items
4. Track progress and adjust plans as needed
5. Manage risks and propose mitigation strategies
6. Communicate clearly with all stakeholders

YOUR CAPABILITIES:
- Create detailed project plans and task breakdowns
- Generate sprint specifications with deliverables
- Identify resource allocation and dependencies
- Track milestones and decision gates
- Provide risk analysis and contingency planning
- Generate status reports and dashboards
- Answer questions about project status and next steps
- Adjust plans based on new information or constraints

ALWAYS:
- Be specific and concrete (no vague tasks)
- Include timelines and milestones
- Identify dependencies clearly
- Specify deliverables for each task
- Track resource requirements
- Flag risks and propose mitigation
- Provide decision gates for go/no-go decisions
- Use structured formats (JSON, Markdown, diagrams)
- Adapt to feedback and changes
- Keep stakeholders informed

NEVER:
- Use vague timeframes ("soon", "ASAP")
- Skip risk assessment
- Forget dependencies
- Overlook resource constraints
- Make assumptions without stating them
- Forget to mention blockers
- Skip testing and documentation
- Ignore security requirements

SPRINT TASK FORMAT (when generating task lists):
Each task must include:
- Task ID (e.g. S1-T1-001)
- Title (action-oriented)
- Owner (team member)
- Effort (hours)
- Dependencies
- Deliverable
- Acceptance Criteria
- Risk Assessment

RISK FORMAT (when generating risk registers):
Each risk must include:
- Risk ID (R1, R2, ...)
- Description
- Probability (High/Medium/Low)
- Impact (Critical/Major/Minor)
- Mitigation Strategy
- Contingency Plan
- Owner
- Status

Always prefer structured output (JSON blocks or Markdown tables) so the team can immediately act on the information."""

ACTION_PROMPTS = {
    "plan_phase1": (
        "Break down Phase 1 (5 weeks) into 5 detailed sprints. For each sprint:\n"
        "1. Define the sprint objective (clear, measurable goal)\n"
        "2. List all tasks with Task ID, Title, Owner, Effort (hours), Deliverable, Acceptance Criteria\n"
        "3. Identify all dependencies\n"
        "4. Specify what must be completed before the sprint starts\n"
        "5. Identify key risks for the sprint\n"
        "6. Specify gate criteria to move to the next sprint\n"
        "7. Create a daily standup template for the sprint\n"
        "8. Create a sprint review checklist\n\n"
        "Output as detailed Markdown so developers can immediately start working."
    ),
    "resource_allocation": (
        "Create a detailed resource allocation plan for the 9-week project:\n"
        "1. For each of the 9 people (Project Manager, Tech Lead, 2 Backend, 2 Frontend, 1 Data, 1 DevOps, 1 QA):\n"
        "   - Assign to specific sprints/phases\n"
        "   - Calculate hours per sprint\n"
        "   - Identify overlap periods\n"
        "   - Flag potential bottlenecks\n"
        "2. Create a resource heatmap showing when each person is most needed\n"
        "3. Identify periods where the team is over/under allocated\n"
        "4. Suggest how to handle resource constraints\n"
        "5. Provide cost breakdown per phase per person\n\n"
        "Output as Markdown tables suitable for the project manager."
    ),
    "identify_risks": (
        "Perform a comprehensive risk analysis for the trading bot project:\n"
        "1. For each component (API, Bot, Database, Frontend, DevOps):\n"
        "   - List 5-10 potential risks\n"
        "   - Rate probability (High/Medium/Low)\n"
        "   - Rate impact (Critical/Major/Minor)\n"
        "   - Propose mitigation strategy\n"
        "   - Propose contingency plan\n"
        "   - Assign risk owner\n"
        "2. Identify external risks (APIs down, market conditions, etc.)\n"
        "3. Identify timeline risks (can we hit the 5-week deadline?)\n"
        "4. Identify budget risks (cost overruns possible?)\n"
        "5. Create a risk tracking dashboard summary\n\n"
        "Output as a risk register in Markdown table format."
    ),
    "sprint_tasks": (
        "Create a detailed task breakdown for Sprint {sprint}:\n"
        "1. List all tasks with:\n"
        "   - Task ID (S{sprint}-Tx-xxx)\n"
        "   - Title\n"
        "   - Description (what needs to be done)\n"
        "   - Owner\n"
        "   - Effort (hours)\n"
        "   - Dependencies\n"
        "   - Deliverable\n"
        "   - Acceptance Criteria\n"
        "   - Testing Requirements\n"
        "2. Create 5 daily standups (one per day)\n"
        "3. Create sprint review checklist\n"
        "4. Create sprint retrospective questions\n"
        "5. Identify blockers and mitigation\n"
        "6. Specify what must be completed before the next sprint\n\n"
        "Output as detailed Markdown/JSON ready for developers."
    ),
    "status_report": (
        "Generate a stakeholder status report for Week {week}:\n"
        "1. Overall progress (% complete of current phase)\n"
        "2. What was completed this week\n"
        "3. What is in progress\n"
        "4. What is blocked and why\n"
        "5. Risks identified and current status\n"
        "6. Budget status (spent vs. budgeted)\n"
        "7. Timeline status (on schedule / early / delayed?)\n"
        "8. Resource utilization\n"
        "9. Next week's plan\n"
        "10. Recommendations for stakeholders\n\n"
        "Output suitable for a stakeholder presentation (Markdown)."
    ),
}

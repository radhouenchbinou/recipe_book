MODEL = "claude-sonnet-4-6"
HISTORY_FILE = "conversation_history.json"
MAX_HISTORY_TURNS = 20  # rolling window (each turn = 1 user + 1 assistant message)

ACTIONS = {
    "plan_phase1": "Break down Phase 1 (5 weeks) into 5 detailed sprints with tasks, owners, effort, deliverables, and gate criteria",
    "resource_allocation": "Create a detailed resource allocation plan for the 9-week project across all 9 team members",
    "identify_risks": "Perform comprehensive risk analysis for all project components with mitigation strategies",
    "sprint_tasks": "Create a detailed task breakdown for a specific sprint (requires --sprint N)",
    "status_report": "Generate a stakeholder status report for a specific week (requires --week N)",
}

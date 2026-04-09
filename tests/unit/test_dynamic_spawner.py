"""Quick smoke test for dynamic agent spawner."""
import sys
print(f"Python: {sys.executable} {sys.version}")

# 1. Import spawner
from src.agents.dynamic_spawner import (
    AgentSpawner, AgentRole, AgentPool, SpawnedAgent,
    PoolResult, AgentResult, aggregate_votes,
    synthesise_outputs, best_result_by_score,
)
print("1. Spawner imports OK")

# 2. Data structures
role = AgentRole(
    name="Test Agent", role_description="Test role",
    expertise="Testing", focus_areas=["unit", "integration"],
    temperature=0.5, model_profile="fast", weight=1.2,
)
assert role.name == "Test Agent"
assert role.model_profile == "fast"
print(f"2. AgentRole OK: {role.name}")

# 3. Spawner + default roles
spawner = AgentSpawner()
debate = spawner._default_roles_for_phase("debate", 5)
assert len(debate) == 5
codegen = spawner._default_roles_for_phase("codegen", 3)
assert len(codegen) == 3
review = spawner._default_roles_for_phase("review", 4)
test_r = spawner._default_roles_for_phase("test", 3)
print(f"3. Default roles: debate={[r.name for r in debate]}")
print(f"   codegen={[r.name for r in codegen]}")
print(f"   review={[r.name for r in review]}")
print(f"   test={[r.name for r in test_r]}")

# 4. Resource adjustment (no monitor)
assert spawner._resource_adjusted_max(7) == 7
print("4. Resource scaling OK (no monitor → passthrough)")

# 5. State fields
from src.langraph_pipeline.state import create_initial_state
state = create_initial_state("Test idea")
assert "spawned_agent_roles" in state
assert "agent_pool_log" in state
assert "spawn_coordination_mode" in state
assert state["spawned_agent_roles"] is None
assert state["agent_pool_log"] == []
print("5. State fields OK")

# 6. Workflow build
from src.langraph_pipeline.workflow_enhanced import build_workflow
wf = build_workflow()
print(f"6. Workflow build OK: {type(wf).__name__}")

# 7. Aggregation helpers
results = [
    AgentResult(agent_id="a1", agent_name="A1", role=debate[0],
                output={"recommendation": "accept"}, success=True),
    AgentResult(agent_id="a2", agent_name="A2", role=debate[1],
                output={"recommendation": "accept"}, success=True),
    AgentResult(agent_id="a3", agent_name="A3", role=debate[2],
                output={"recommendation": "revise"}, success=True),
]
votes = aggregate_votes(results)
assert "accept" in votes
assert "revise" in votes
# accept: 1.0(w) + 1.2(w) = 2.2, revise: 1.3(w)
print(f"7. Weighted votes: {votes}")

results_with_text = [
    AgentResult(agent_id="a1", agent_name="A1", role=debate[0],
                output={"recommendation": "accept"}, raw_text="Solution A1 output", success=True),
    AgentResult(agent_id="a2", agent_name="A2", role=debate[1],
                output={"recommendation": "accept"}, raw_text="Solution A2 output", success=True),
]
synth = synthesise_outputs(results_with_text)
assert len(synth) > 0 and "A1" in synth
print(f"8. Output synthesis OK ({len(synth)} chars)")

print("\n✅ ALL SMOKE TESTS PASSED")

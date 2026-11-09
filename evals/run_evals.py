"""Case 4 (optional module): evaluate DaMi with Strands Evals.

    python evals/run_evals.py

Two kinds of evaluators:
- deterministic: "did DaMi call the tools we expected?" (no LLM needed, always the same result)
- LLM-as-judge: a model reads the question, the expected answer and DaMi's answer, and gives a score.

Add your own cases. Then ask: how often do you agree with the judge?
"""

from strands_evals import Case, Experiment
from strands_evals.evaluators import Evaluator, OutputEvaluator
from strands_evals.types import EvaluationData, EvaluationOutput

from dami.agent import build_agent


class UsedExpectedTools(Evaluator):
    """Pass if every tool in `expected_trajectory` appears in the tools that DaMi called."""

    def evaluate(self, case: EvaluationData) -> list[EvaluationOutput]:
        expected = set(case.expected_trajectory or [])
        actual = set(case.actual_trajectory or [])
        missing = sorted(expected - actual)
        return [EvaluationOutput(score=1.0 if not missing else 0.0, test_pass=not missing,
                                 reason=f"missing: {missing}" if missing else "all expected tools were called")]

    async def evaluate_async(self, case: EvaluationData) -> list[EvaluationOutput]:
        return self.evaluate(case)


CASES = [
    Case(
        name="list-tables",
        input="Which tables do we have?",
        expected_output="Five tables: customers, products, marketing, sensors, transactions.",
        expected_trajectory=["list_tables"],
    ),
    Case(
        name="customer-segments",
        input="How many customer segments are there?",
        expected_output="Five segments of age and income (after scaling the features).",
        expected_trajectory=["kmeans"],
    ),
    # TODO: add at least 6 more cases, for example about outliers in the sensors table.
]


def task(case: Case) -> dict:
    agent = build_agent(session="evals")
    try:
        answer = str(agent(case.input))
        tools = [t["name"] for t in (agent.dami_recorder.last_run or {}).get("tools", [])]
    finally:
        agent.cleanup()
    return {"output": answer, "trajectory": tools}


judge = OutputEvaluator(
    rubric=(
        "Score 1.0 if the answer contains the same facts as the expected output, "
        "0.5 if it is partly right, 0.0 if it is wrong or invents facts."
    ),
)

if __name__ == "__main__":
    experiment = Experiment(cases=CASES, evaluators=[UsedExpectedTools(), judge])
    report = experiment.run_evaluations(task)
    report.display(include_actual_output=True, include_actual_trajectory=True)
    for case, passed, reason in zip(report.cases, report.test_passes, report.reasons):
        print(f"{'PASS' if passed else 'FAIL'}  {case.get('name')}  [{case.get('evaluator')}]  {reason[:200]}")

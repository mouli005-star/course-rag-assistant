import json
import re
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app import Advisor


EVAL_SET_PATH = BASE_DIR / "evaluation" / "eval_set.json"
RESULTS_PATH = BASE_DIR / "evaluation" / "results.json"
REPORT_PATH = BASE_DIR / "evaluation" / "REPORT.md"
TRANSCRIPTS_PATH = BASE_DIR / "evaluation" / "EXAMPLE_TRANSCRIPTS.md"


def load_eval_set():
    return json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))


def has_real_citations(response_text):
    lower_text = str(response_text or "").lower()
    if "citations:" not in lower_text:
        return False

    has_url = "url:" in lower_text or "http://" in lower_text or "https://" in lower_text
    has_ref = "ref:" in lower_text or "chunk" in lower_text or "section:" in lower_text
    return has_url and has_ref


def extract_decision(response_text):
    match = re.search(r"Decision:\s*(Eligible|Not eligible|Need more info)", response_text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def normalize_decision(value):
    return str(value or "").strip().lower()


def is_abstention(response_text):
    phrases = [
        "i don’t have",
        "i don't have",
        "not available in the provided",
        "not confirmed",
        "could not find",
        "not in catalog",
    ]
    lower_text = response_text.lower()
    return any(phrase in lower_text for phrase in phrases)


def run_case(case):
    advisor = Advisor()
    advisor.set_completed_courses(case.get("completed_courses", []))
    profile = case.get("profile", {})
    if profile:
        advisor.set_profile(**profile)

    response = advisor.handle(case["question"])

    result = {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "response": response,
        "has_citations": has_real_citations(response),
        "decision": extract_decision(response),
        "abstained": is_abstention(response),
    }

    if "expected_decision" in case:
        result["expected_decision"] = case["expected_decision"]
        result["decision_correct"] = normalize_decision(result["decision"]) == normalize_decision(case["expected_decision"])

    if "expected_abstain" in case:
        result["expected_abstain"] = case["expected_abstain"]
        result["abstention_correct"] = bool(result["abstained"]) == bool(case["expected_abstain"])

    if "expected_contains" in case:
        lower_response = response.lower()
        result["contains_expected_items"] = all(item.lower() in lower_response for item in case["expected_contains"])

    if "expected_keywords" in case:
        lower_response = response.lower()
        result["contains_expected_keywords"] = all(keyword.lower() in lower_response for keyword in case["expected_keywords"])

    return result


def summarize(results):
    total = len(results)
    citation_coverage = sum(1 for item in results if item["has_citations"]) / total * 100

    prereq_cases = [item for item in results if item["category"] == "prereq_check"]
    prereq_correct = sum(1 for item in prereq_cases if item.get("decision_correct"))
    prereq_accuracy = (prereq_correct / len(prereq_cases) * 100) if prereq_cases else 0.0

    abstain_cases = [item for item in results if item["category"] == "not_in_docs"]
    abstain_correct = sum(1 for item in abstain_cases if item.get("abstention_correct"))
    abstention_accuracy = (abstain_correct / len(abstain_cases) * 100) if abstain_cases else 0.0

    return {
        "total_cases": total,
        "citation_coverage_rate": round(citation_coverage, 2),
        "eligibility_correctness_rate": round(prereq_accuracy, 2),
        "abstention_accuracy_rate": round(abstention_accuracy, 2),
        "prereq_correct_cases": prereq_correct,
        "prereq_total_cases": len(prereq_cases),
        "abstain_correct_cases": abstain_correct,
        "abstain_total_cases": len(abstain_cases),
    }


def write_results(results, summary):
    payload = {"summary": summary, "results": results}
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_report(summary):
    report = f"""# Evaluation Report

## Summary

- Total queries: {summary['total_cases']}
- Citation coverage rate: {summary['citation_coverage_rate']}%
- Eligibility correctness on prerequisite checks: {summary['eligibility_correctness_rate']}% ({summary['prereq_correct_cases']}/{summary['prereq_total_cases']})
- Abstention accuracy on not-in-docs queries: {summary['abstention_accuracy_rate']}% ({summary['abstain_correct_cases']}/{summary['abstain_total_cases']})

## Rubric

- Citation coverage: response includes a `Citations:` section with grounded catalog citations including source URL/reference plus section/chunk context.
- Eligibility correctness: `Decision:` line matches the expected eligible/not-eligible outcome for the prerequisite test case.
- Abstention accuracy: response clearly refuses to invent missing information for schedule, instructor, seat-count, or preference questions.

## Notes

- Prerequisite cases are graded automatically from the structured decision output.
- Program requirement questions are included in the dataset for coverage and transcript review.
- Manual review is still recommended before submission, especially for nuanced policy wording.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def write_example_transcripts(results):
    def find_case(case_id):
        for item in results:
            if item["id"] == case_id:
                return item
        return None

    examples = [
        ("Correct eligibility decision with citations", find_case("prereq_01")),
        ("Course plan output with justification and citations", find_case("program_plan_placeholder")),
        ("Correct abstention with guidance", find_case("trick_01")),
    ]

    plan_example = Advisor()
    plan_example.set_completed_courses(["COSC1336", "COSC1337"])
    plan_example.set_profile(
        major="Computer Science",
        target_term="Fall",
        max_credits=6,
        max_courses=2,
        catalog_year="2025-2026",
        transfer_credits=False,
        transfer_credit_details_provided=True,
    )
    plan_response = plan_example.handle("Recommend courses for next term.")
    examples[1] = (
        "Course plan output with justification and citations",
        {"question": "Recommend courses for next term.", "response": plan_response},
    )

    lines = ["# Example Transcripts", ""]
    for title, example in examples:
        if not example:
            continue
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"**User:** {example['question']}")
        lines.append("")
        lines.append("**Assistant:**")
        lines.append("")
        lines.append("```text")
        lines.append(example["response"])
        lines.append("```")
        lines.append("")

    TRANSCRIPTS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    cases = load_eval_set()
    results = [run_case(case) for case in cases]
    summary = summarize(results)
    write_results(results, summary)
    write_report(summary)
    write_example_transcripts(results)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

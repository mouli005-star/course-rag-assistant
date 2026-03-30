# Evaluation Report

## Summary

- Total queries: 25
- Citation coverage rate: 100.0%
- Eligibility correctness on prerequisite checks: 70.0% (7/10)
- Abstention accuracy on not-in-docs queries: 100.0% (5/5)

## Rubric

- Citation coverage: response includes a `Citations:` section with grounded catalog citations including source URL/reference plus section/chunk context.
- Eligibility correctness: `Decision:` line matches the expected eligible/not-eligible outcome for the prerequisite test case.
- Abstention accuracy: response clearly refuses to invent missing information for schedule, instructor, seat-count, or preference questions.

## Notes

- Prerequisite cases are graded automatically from the structured decision output.
- Program requirement questions are included in the dataset for coverage and transcript review.
- Manual review is still recommended before submission, especially for nuanced policy wording.

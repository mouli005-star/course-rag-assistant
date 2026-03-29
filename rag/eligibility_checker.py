import json


GRAPH_FILE = "data/processed/course_graph.json"


def load_graph():

    with open(GRAPH_FILE, "r") as f:
        return json.load(f)


def normalize(code):

    return code.upper().replace(" ", "").replace("-", "")


def find_missing_prereqs(graph, target, completed, visited=None):

    if visited is None:
        visited = set()

    target = normalize(target)

    if target in visited:
        return []

    visited.add(target)

    prereqs = graph.get(target, [])

    missing = []

    for p in prereqs:

        if p not in completed:

            missing.append(p)

            deeper = find_missing_prereqs(graph, p, completed, visited)

            missing.extend(deeper)

    return list(set(missing))


def check_eligibility(completed_courses, target_course):

    graph = load_graph()

    completed_courses = [normalize(c) for c in completed_courses]

    missing = find_missing_prereqs(
        graph,
        target_course,
        completed_courses
    )

    if not missing:
        return {
            "decision": "Eligible",
            "target_course": normalize(target_course),
            "missing_prereqs": [],
            "why": f"All listed prerequisite courses for {normalize(target_course)} are satisfied based on the completed-course list provided.",
            "next_step": f"You can plan to enroll in {normalize(target_course)}.",
        }

    return {
        "decision": "Not eligible",
        "target_course": normalize(target_course),
        "missing_prereqs": sorted(missing),
        "why": f"{normalize(target_course)} still has unmet prerequisite requirements.",
        "next_step": "Complete the missing prerequisite courses first, then re-check eligibility.",
    }


if __name__ == "__main__":

    completed = []

    target = "DMAT0314"

    print(check_eligibility(completed, target))

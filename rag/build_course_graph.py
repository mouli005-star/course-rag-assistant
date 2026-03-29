import json
import os


INPUT_FILE = "data/processed/courses.json"
OUTPUT_FILE = "data/processed/course_graph.json"


def normalize_course_name(name):
    """
    tries to standardize course codes
    example:
    CS 101 -> CS101
    CSE-220 -> CSE220
    """

    if not name:
        return ""

    return (
        name.upper()
        .replace("-", "")
        .replace(" ", "")
    )


def build_graph():

    if not os.path.exists(INPUT_FILE):
        raise Exception("courses.json not found")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        courses = json.load(f)

    graph = {}

    for c in courses:

        code = normalize_course_name(c.get("course_code"))

        prereqs = [
            normalize_course_name(p)
            for p in c.get("prerequisites", [])
        ]

        if code:
            graph[code] = prereqs

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    print("\nGraph created")
    print(f"Total courses in graph: {len(graph)}")


if __name__ == "__main__":
    build_graph()
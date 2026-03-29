import json
from pathlib import Path
import re
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from rag.course_search import search_course
from rag.eligibility_checker import check_eligibility
from rag.output_formatter import format_assignment_response
from rag.retriever import ask as grounded_answer
from rag.retriever import retrieve_context
from rag.source_catalog import build_source_citation
from rag.verifier import verify_response


COURSES_FILE = BASE_DIR / "data" / "processed" / "courses.json"
MEMORY_FILE = BASE_DIR / "data" / "chat_memory.json"
MAX_MEMORY = 20

KNOWN_MAJORS = [
    "computer science",
    "data science",
    "engineering",
    "chemistry",
    "business",
    "networking",
    "mathematics",
    "math",
]

MAJOR_FIELD_HINTS = {
    "computer science": {"programming", "ai", "networking"},
    "data science": {"data_science", "math", "ai", "programming"},
    "engineering": {"math", "programming", "networking"},
    "chemistry": {"math"},
    "business": {"other"},
    "networking": {"networking", "programming"},
    "mathematics": {"math"},
    "math": {"math"},
}

MAJOR_CODE_HINTS = {
    "computer science": {"COSC", "ITSC", "CPMT"},
    "data science": {"COSC", "MATH", "STAT"},
    "engineering": {"ENGR", "MATH", "PHYS", "COSC"},
    "chemistry": {"CHEM", "BIOL", "MATH"},
    "business": {"BUSI", "ACCT", "BMGT", "ECON"},
    "networking": {"ITNW", "COSC", "CDEC"},
    "mathematics": {"MATH"},
    "math": {"MATH"},
}

POLICY_KEYWORDS = [
    "policy",
    "grade",
    "repeat",
    "residency",
    "elective",
    "degree requirement",
    "program requirement",
    "credit limit",
    "catalog year",
    "transfer credit",
]

GENERIC_COURSE_DISCOVERY_PHRASES = [
    "what courses does the college offer",
    "what are courses does the college offers",
    "what are all courses does this college offers",
    "what are all courses this college offers",
    "all courses this college offers",
    "all courses does this college offer",
    "what courses are available",
    "what courses does cisco college offer",
    "show all courses",
    "list all courses",
]


def load_courses():
    with open(COURSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_course_code(value):
    return str(value or "").upper().replace(" ", "").replace("-", "")


def parse_credit_value(raw_value):
    match = re.search(r"(\d+)", str(raw_value or ""))
    return int(match.group(1)) if match else 3


def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)


def load_profile():
    return {
        "major": None,
        "target_term": None,
        "max_credits": None,
        "max_courses": None,
        "catalog_year": None,
        "transfer_credits": None,
        "transfer_credit_details_provided": False,
    }


def detect_intent(question):
    q = question.lower()

    if any(keyword in q for keyword in POLICY_KEYWORDS):
        return "policy"

    if "can i take" in q or "eligible" in q or "prerequisite" in q:
        return "eligibility"

    if "what can i take" in q or "recommend" in q or "plan" in q:
        return "recommend"

    if "show" in q or "list" in q or "course" in q:
        return "search"

    return "search"


def extract_completed_from_text(text):
    tokens = text.split()
    completed = []

    for token in tokens:
        normalized = normalize_course_code(token)
        if len(normalized) > 5 and any(char.isdigit() for char in normalized):
            completed.append(normalized)

    return completed


def build_course_lookup():
    lookup = {}
    for course in load_courses():
        code = normalize_course_code(course.get("course_code", ""))
        if code and code not in lookup:
            lookup[code] = course
    return lookup


def format_course_citation(course):
    page = course.get("page")
    page_number = page + 1 if isinstance(page, int) else "unknown"
    course_name = course.get("course_name") or f"Page {page_number}"
    code = course.get("course_code", "unknown course")
    return build_source_citation(
        course.get("source", "unknown"),
        f"page {page_number}",
        None,
    )


def format_chunk_citation(chunk):
    metadata = chunk.get("metadata", {})
    page = metadata.get("page")
    page_number = page + 1 if isinstance(page, int) else "unknown"
    return build_source_citation(
        metadata.get("source", "unknown"),
        f"page {page_number}",
        None,
    )


def detect_major(text):
    lower_text = text.lower()
    for major in KNOWN_MAJORS:
        if major in lower_text:
            return major.title() if major != "math" else "Mathematics"

    patterns = [
        r"(?:major|program)\s+(?:is\s+)?([a-z][a-z &/-]+?)(?:[,.;]| for | with | and |$)",
        r"for\s+the\s+([a-z][a-z &/-]+?)\s+(?:major|program)(?:[,.;]|$)",
        r"major\s+in\s+([a-z][a-z &/-]+?)(?:[,.;]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower_text)
        if match:
            candidate = " ".join(match.group(1).split())
            if len(candidate) >= 3:
                return candidate.title()

    return None


def extract_profile_updates(text):
    lower_text = text.lower()
    updates = {}

    major = detect_major(text)
    if major:
        updates["major"] = major

    for term in ["fall", "spring", "summer", "winter"]:
        if term in lower_text:
            updates["target_term"] = term.title()
            break

    credit_match = re.search(r"(\d+)\s*credits?", lower_text)
    if credit_match:
        updates["max_credits"] = int(credit_match.group(1))

    course_match = re.search(r"(\d+)\s*courses?", lower_text)
    if course_match:
        updates["max_courses"] = int(course_match.group(1))

    catalog_match = re.search(r"(20\d{2}(?:\s*-\s*20\d{2})?)", text)
    if catalog_match and "catalog" in lower_text:
        updates["catalog_year"] = catalog_match.group(1).replace(" ", "")

    if "no transfer credit" in lower_text or "no transfer credits" in lower_text:
        updates["transfer_credits"] = False
        updates["transfer_credit_details_provided"] = True
    elif "transfer credit" in lower_text or "transfer credits" in lower_text or "transferred" in lower_text:
        updates["transfer_credits"] = True
        if extract_completed_from_text(text):
            updates["transfer_credit_details_provided"] = True

    return updates


def merge_profile(profile, updates):
    for key, value in updates.items():
        profile[key] = value


def missing_planning_questions(profile, completed_courses):
    questions = []

    if not completed_courses:
        questions.append("Which courses have you already completed?")

    if not profile["major"]:
        questions.append("What is your target major or program?")

    if not profile["target_term"]:
        questions.append("Which term are you planning for?")

    if profile["max_credits"] is None and profile["max_courses"] is None:
        questions.append("What is your maximum course or credit load for the term?")

    if not profile["catalog_year"]:
        questions.append("Which catalog year should I use?")

    if profile["transfer_credits"] is None:
        questions.append("Do you have any transfer credits that count toward the program?")
    elif profile["transfer_credits"] and not profile["transfer_credit_details_provided"]:
        questions.append("Which transfer credits have already been accepted as equivalent courses?")

    return questions[:5]


def major_field_hints(major):
    return MAJOR_FIELD_HINTS.get(str(major or "").lower(), set())


def major_code_hints(major):
    return MAJOR_CODE_HINTS.get(str(major or "").lower(), set())


def score_course_for_plan(course, completed_set, profile, requirement_text):
    course_code = normalize_course_code(course.get("course_code", ""))
    prereqs = [normalize_course_code(item) for item in course.get("prerequisites", [])]

    if not course_code or course_code in completed_set:
        return None

    if not all(prereq in completed_set for prereq in prereqs):
        return None

    score = 0
    major = str(profile.get("major") or "").lower()
    course_text = " ".join(
        [
            str(course.get("course_name", "")),
            str(course.get("description", "")),
            str(course.get("course_code", "")),
        ]
    ).lower()

    if major and major in course_text:
        score += 6

    if course.get("field") in major_field_hints(profile.get("major")):
        score += 4

    code_prefix = re.match(r"[A-Z]+", course_code)
    if code_prefix and code_prefix.group(0) in major_code_hints(profile.get("major")):
        score += 6

    if course_code in requirement_text:
        score += 10

    course_name = str(course.get("course_name", "")).lower()
    if course_name and course_name in requirement_text:
        score += 8

    if prereqs:
        score += 2

    if score < 4:
        return None

    return score


def recommend_courses(completed, profile, requirement_chunks):
    courses = load_courses()
    completed_set = {normalize_course_code(code) for code in completed}
    requirement_text = " ".join(chunk.get("text", "").lower() for chunk in requirement_chunks)

    scored = []
    for course in courses:
        score = score_course_for_plan(course, completed_set, profile, requirement_text)
        if score is None:
            continue
        scored.append((score, course))

    scored.sort(
        key=lambda item: (
            -item[0],
            parse_credit_value(item[1].get("credits")),
            item[1].get("course_code") or "",
        )
    )

    max_courses = profile.get("max_courses") or 4
    max_credits = profile.get("max_credits") or 12

    selected = []
    total_credits = 0
    for score, course in scored:
        course_credits = parse_credit_value(course.get("credits"))
        if len(selected) >= max_courses:
            break
        if total_credits + course_credits > max_credits:
            continue
        selected.append((score, course))
        total_credits += course_credits

    return selected, total_credits


def build_plan_requirements_context(profile):
    query = (
        f"{profile.get('major', '')} degree requirements electives residency policies "
        f"catalog {profile.get('catalog_year', '')}"
    ).strip()
    chunks, _ = retrieve_context(query, k=4)
    return chunks


def build_broad_catalog_context():
    chunks, _ = retrieve_context("academic programs course descriptions catalog offerings", k=4)
    return chunks


class Advisor:
    def __init__(self):
        self.completed_courses = []
        self.memory = load_memory()
        self.course_lookup = build_course_lookup()
        self.profile = load_profile()

    def remember(self, user_msg, bot_msg):
        self.memory.append({"user": user_msg, "assistant": bot_msg})
        self.memory = self.memory[-MAX_MEMORY:]
        save_memory(self.memory)

    def set_completed_courses(self, completed_courses):
        normalized = []
        for course in completed_courses:
            code = normalize_course_code(course)
            if code and code not in normalized:
                normalized.append(code)
        self.completed_courses = normalized

    def set_profile(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.profile and value not in ("", None):
                self.profile[key] = value
            elif key in self.profile and value in ("", None):
                self.profile[key] = None

    def reset(self):
        self.completed_courses = []
        self.profile = load_profile()
        self.memory = []
        save_memory(self.memory)

    def show_memory(self):
        print("\nRecent conversation:")
        for message in self.memory[-5:]:
            print("You:", message["user"])
            print("Assistant:", message["assistant"])

    def _eligibility_response(self, question):
        matches = search_course(question)

        if not matches:
            return format_assignment_response(
                answer="Decision: Need more info",
                why="I could not confidently match the question to a course in the current catalog extract.",
                citations=[],
                clarifying_questions=["Which exact course name or course code are you asking about?"],
                assumptions=[],
            )

        course = matches[0]
        canonical_course = self.course_lookup.get(normalize_course_code(course.get("course_code", "")), course)
        result = check_eligibility(
            completed_courses=self.completed_courses,
            target_course=canonical_course["course_code"],
        )

        citations = [format_course_citation(canonical_course)]
        evidence_lines = []

        for prereq in result["missing_prereqs"]:
            prereq_course = self.course_lookup.get(prereq)
            if prereq_course:
                citations.append(format_course_citation(prereq_course))
                evidence_lines.append(f"- Missing prerequisite evidence: {prereq_course.get('course_code')} is required before {course.get('course_code')}.")
            else:
                evidence_lines.append(f"- Missing prerequisite evidence: {prereq} is listed as unmet.")

        if not result["missing_prereqs"]:
            listed_prereqs = canonical_course.get("prerequisites", [])
            if listed_prereqs:
                evidence_lines.append(
                    "- Evidence: the course's listed prerequisites are all present in the recorded completed-course list."
                )
            else:
                evidence_lines.append("- Evidence: no prerequisite courses are listed in the extracted course record.")

        why_lines = [
            f"Decision: {result['decision']}",
            *evidence_lines,
            f"Next step: {result['next_step']}",
        ]

        assumptions = []
        if not canonical_course.get("prerequisites"):
            assumptions.append("This decision is based on the extracted course record and may miss prerequisite text that was not captured in the course extraction output.")

        return format_assignment_response(
            answer=f"Decision: {result['decision']}\nNext step: {result['next_step']}",
            why=why_lines,
            citations=sorted(set(citations)),
            clarifying_questions=[],
            assumptions=assumptions,
        )

    def _recommendation_response(self, question):
        clarifying_questions = missing_planning_questions(self.profile, self.completed_courses)

        if clarifying_questions:
            return format_assignment_response(
                answer="I need a few planning details before I can build a next-term course plan.",
                why="The planner waits for the student profile fields required by the assignment before generating a term plan.",
                citations=[],
                clarifying_questions=clarifying_questions,
                assumptions=["No course plan was generated until the missing planning inputs are provided."],
            )

        requirement_chunks = build_plan_requirements_context(self.profile)
        plan, total_credits = recommend_courses(self.completed_courses, self.profile, requirement_chunks)

        citations = [format_chunk_citation(chunk) for chunk in requirement_chunks]
        answer_lines = []
        why_lines = []

        for _, course in plan:
            course_credits = parse_credit_value(course.get("credits"))
            answer_lines.append(
                f"- {course['course_name']} ({course['course_code']}) - {course_credits} credits"
            )

            prereqs = [normalize_course_code(item) for item in course.get("prerequisites", [])]
            prereq_text = ", ".join(prereqs) if prereqs else "No listed prerequisite"
            why_lines.append(
                f"- {course['course_code']}: selected for the {self.profile['major']} plan because prerequisites are satisfied and it aligns with retrieved program-requirement context. Listed prerequisites: {prereq_text}."
            )
            citations.append(format_course_citation(course))

        assumptions = [
            f"Target term used for planning: {self.profile['target_term']}.",
            f"Planning cap used: {self.profile.get('max_courses') or 'N/A'} courses and {self.profile.get('max_credits') or 'N/A'} credits.",
            f"Catalog year used: {self.profile['catalog_year']}.",
            "Course offering availability by semester is not confirmed unless explicitly stated in the catalog excerpts.",
        ]

        if self.profile["transfer_credits"]:
            assumptions.append("Transfer credits were assumed to be reflected in the completed-course list you provided.")
        else:
            assumptions.append("No transfer credits were applied in the plan.")

        if not plan:
            return format_assignment_response(
                answer="I could not assemble a next-term plan from the current completed-course list and planning constraints.",
                why="No candidate courses fit the prerequisite checks and planning limits at the same time.",
                citations=sorted(set(citations)),
                clarifying_questions=[],
                assumptions=assumptions,
            )

        answer = "\n".join(answer_lines)
        answer += f"\nTotal planned credits: {total_credits}"

        return format_assignment_response(
            answer=answer,
            why=why_lines,
            citations=sorted(set(citations)),
            clarifying_questions=[],
            assumptions=assumptions,
        )

    def _policy_response(self, question):
        return grounded_answer(question)

    def _search_response(self, question):
        lower_question = question.lower().strip()
        if any(phrase in lower_question for phrase in GENERIC_COURSE_DISCOVERY_PHRASES):
            return grounded_answer(question)

        explicit_code = re.search(r"\b[A-Za-z]{3,4}\s*-?\s*\d{4}\b", question)
        explicit_course_lookup = bool(explicit_code) or any(
            token in lower_question for token in ["course code", "course title", "find course", "show course"]
        )

        if not explicit_course_lookup:
            return grounded_answer(question)

        matches = search_course(question)
        if not matches:
            return grounded_answer(question)

        citations = []
        answer_lines = []

        for match in matches[:5]:
            answer_lines.append(f"- {match['course_name']} ({match['course_code']})")
            course = self.course_lookup.get(normalize_course_code(match.get("course_code", "")))
            if course:
                citations.append(format_course_citation(course))

        return format_assignment_response(
            answer=(
                "Here are the catalog-listed courses that best match your question:\n" + "\n".join(answer_lines)
                if answer_lines
                else "I could not find a matching course in the current catalog extract."
            ),
            why=(
                "These results come from course titles and extracted catalog records that align most closely with the wording of your question."
                if answer_lines
                else "No course name or course code match was found for the query."
            ),
            citations=sorted(set(citations)),
            clarifying_questions=[],
            assumptions=[] if answer_lines else ["Try asking with a course code, subject area, or a more specific course title."],
        )

    def handle(self, question):
        intent = detect_intent(question)

        profile_updates = extract_profile_updates(question)
        merge_profile(self.profile, profile_updates)

        new_completed = extract_completed_from_text(question)
        if new_completed:
            merged = list(self.completed_courses)
            for course in new_completed:
                if course not in merged:
                    merged.append(course)
            self.completed_courses = merged
            if self.profile["transfer_credits"]:
                self.profile["transfer_credit_details_provided"] = True

        if intent == "eligibility":
            response = self._eligibility_response(question)
        elif intent == "recommend":
            response = self._recommendation_response(question)
        elif intent == "policy":
            response = self._policy_response(question)
        else:
            response = self._search_response(question)

        response = verify_response(response)

        print("\nAssistant:")
        print(response)
        self.remember(question, response)
        return response


if __name__ == "__main__":
    advisor = Advisor()

    print("\nAcademic Advisor Ready")
    print("Type 'exit' to stop\n")

    while True:
        question = input("\nYou: ")
        if question.lower() == "exit":
            break
        advisor.handle(question)

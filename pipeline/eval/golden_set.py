"""
golden_set.py -- The curated test set for AI-3 Session 1.2 evaluation.

This set was validated against the Northbrook corpus during the Session 1.1
enrichment correctness fix (see decisions/012-enrichment-correctness-fix.md).
It is the seed the class starts with. Students will grow it in Lab 2 by
adding adversarial queries, feedback-derived cases, and out-of-scope checks.

Structure of each entry:
    id               -- Short stable identifier, snake_case
    question         -- The query string (verbatim from student-facing materials)
    expected_answer  -- Ground-truth canonical answer, corpus-grounded, 1-2 sentences
    expected_source  -- List of source filenames that should be retrieved
                        (multi-doc queries may list several)
    category         -- policy_lookup | multi_doc | compound | procedural | out_of_scope
    difficulty       -- easy | medium | hard
    history          -- list[dict] of prior {role, content} messages.
                        Empty [] for single-turn cases. For multi-turn cases,
                        the followup `question` should be UNANSWERABLE without
                        this prior history — that is what makes contextualize_query
                        a measurable lever.

The `expected_answer` strings are short and declarative — they mirror how the
source documents write the information. An LLM judge compares the generated
answer against these strings (see pipeline/eval/evaluators.py).

To explore: print `len(GOLDEN_SET)`, inspect `[q["category"] for q in GOLDEN_SET]`,
or filter by difficulty: `[q for q in GOLDEN_SET if q["difficulty"] == "easy"]`.
"""

import os


def get_dataset_name(base: str = "northbrook_golden_v1") -> str:
    """Return the per-student Phoenix dataset name.

    Phoenix datasets live at the WORKSPACE level, not the project level — so
    classmates sharing a workspace would collide on any hardcoded name. We
    suffix with PHOENIX_PROJECT_NAME so each student gets their own isolated
    dataset.

    Example:
        PHOENIX_PROJECT_NAME="ai3-tyler" → "northbrook_golden_v1__tyler"
        PHOENIX_PROJECT_NAME unset       → "northbrook_golden_v1__local"

    Using a helper (rather than hardcoding the suffix everywhere) means the
    naming scheme lives in one place — easy to change if we version the set.
    """
    project = os.environ.get("PHOENIX_PROJECT_NAME", "local")
    suffix = project.removeprefix("ai3-") if project.startswith("ai3-") else project
    return f"{base}__{suffix}"


GOLDEN_SET = [
    # 1. Single-topic lookup in vacation_policy_2025.md (HyDE winner in 1.1)
    {
        "id": "vacation_policy",
        "question": "What is the vacation policy?",
        "expected_answer": (
            "Eligible full-time employees receive 20 vacation days per calendar "
            "year, with up to 10 days allowed to carry over. Requests require at "
            "least two weeks' advance notice, or 30 days for five or more "
            "consecutive days."
        ),
        "expected_source": ["vacation_policy_2025.md"],
        "category": "policy_lookup",
        "difficulty": "easy",
        "history": [],
    },

    # 2. Single-topic lookup in expense_policy.md (HyDE winner in 1.1)
    {
        "id": "expense_reimbursement",
        "question": "What are the expense reimbursement rules?",
        "expected_answer": (
            "Expenses must be business-related and submitted within 30 days with "
            "itemized receipts. Meals are capped at $65 per day for travel and "
            "$50 per person for team meals. Reimbursements are processed bi-weekly "
            "aligned with payroll."
        ),
        "expected_source": ["expense_policy.md"],
        "category": "policy_lookup",
        "difficulty": "easy",
        "history": [],
    },

    # 3. Enumeration from single policy doc (HyDE winner in 1.1)
    {
        "id": "pto_types",
        "question": "What are the three main types of paid time off Northbrook offers?",
        "expected_answer": (
            "The three main types are vacation days (20 per year), unlimited "
            "sick days, and personal days (3 per year). Northbrook also offers "
            "Recharge Days (2 per year) as a new 2025 benefit."
        ),
        "expected_source": ["vacation_policy_2025.md"],
        "category": "policy_lookup",
        "difficulty": "easy",
        "history": [],
    },

    # 4. Multi-topic single doc (enrichment winner: Q4 board meeting)
    {
        "id": "q4_board_meeting",
        "question": "What happened at the Q4 board meeting?",
        "expected_answer": (
            "The board reviewed strong Q4 financials ($14.1M revenue, $2.9M net "
            "income), approved a $2.1M AI initiative called Project Meridian, "
            "and confirmed the office relocation to 250 Innovation Drive for "
            "March 2025."
        ),
        "expected_source": ["board_meeting_q4_2024.md"],
        "category": "multi_doc",
        "difficulty": "medium",
        "history": [],
    },

    # 5. Cross-document synthesis (enrichment winner: office move across 3 docs)
    {
        "id": "office_relocation",
        "question": "What was discussed about office relocation?",
        "expected_answer": (
            "Northbrook is relocating from 100 Main Street to 250 Innovation "
            "Drive in March 2025. The new 45,000-square-foot space includes 60 "
            "private focus rooms, a café, 180 parking spaces, and an event space. "
            "The current office no longer accommodates the 320-person workforce."
        ),
        "expected_source": [
            "memo_office_relocation.md",
            "board_meeting_q3_2024.md",
            "board_meeting_q4_2024.md",
        ],
        "category": "multi_doc",
        "difficulty": "medium",
        "history": [],
    },

    # 6. Multi-part / compound question (enrichment winner: timeline + prep)
    {
        "id": "office_move_timeline",
        "question": "What's the timeline for the office move and what do I need to do to prepare?",
        "expected_answer": (
            "The move happens March 1-2, 2025. Prepare by packing personal items "
            "the week of Feb 10, receiving your desk assignment by Feb 7, "
            "cleaning shared spaces by Feb 21, and updating your address in the "
            "HR portal by March 1. Do not pack IT equipment; IT handles all "
            "technology setup."
        ),
        "expected_source": ["memo_office_relocation.md"],
        "category": "compound",
        "difficulty": "medium",
        "history": [],
    },

    # 7. Two-part compound across docs (enrichment winner: CEO + priorities)
    {
        "id": "ceo_priorities",
        "question": "Who is the CEO and what are their priorities?",
        "expected_answer": (
            "Sarah Chen is the CEO. Her 2025 priorities are AI-First Services "
            "(Project Meridian, $2.1M investment), market expansion into Seattle, "
            "Atlanta, and Boston, and a $60M revenue target representing 23% growth."
        ),
        "expected_source": ["memo_ceo_annual_kickoff.md"],
        "category": "compound",
        "difficulty": "medium",
        "history": [],
    },

    # 8. Procedural / how-to (enrichment winner)
    {
        "id": "vpn_setup",
        "question": "How do I set up VPN access?",
        "expected_answer": (
            "Download the new Cloudflare Zero Trust VPN client from the IT "
            "self-service portal (available Jan 27). It replaces SecureLink and "
            "offers faster speeds and MFA integration. Company laptops deploy "
            "automatically; personal devices require manual install per IT's "
            "support page."
        ),
        "expected_source": ["memo_security_update.md"],
        "category": "procedural",
        "difficulty": "easy",
        "history": [],
    },

    # 9. Policy lookup (enrichment winner: performance review)
    {
        "id": "performance_review",
        "question": "What are the performance review procedures?",
        "expected_answer": (
            "Northbrook conducts quarterly performance reviews run by direct "
            "managers using a rubric covering quality of work, collaboration, "
            "client satisfaction, initiative, and values alignment. Mid-year and "
            "year-end reviews include self-assessments and peer feedback. "
            "Compensation adjustments happen in the December year-end cycle."
        ),
        "expected_source": ["employee_handbook.md"],
        "category": "policy_lookup",
        "difficulty": "medium",
        "history": [],
    },

    # 10. Policy lookup (enrichment winner: remote work)
    {
        "id": "remote_work",
        "question": "How does the company handle remote work requests?",
        "expected_answer": (
            "Northbrook operates a hybrid model: eligible full-time employees "
            "work 3 days in-office (Tuesday, Wednesday, Thursday) and 2 days "
            "remotely. Fully remote arrangements require VP-level approval and "
            "are limited to regions without a Northbrook office. Remote workers "
            "receive a $1,500 equipment stipend and must use the company VPN."
        ),
        "expected_source": ["remote_work_policy.md"],
        "category": "policy_lookup",
        "difficulty": "easy",
        "history": [],
    },

    # ─── MULTI-TURN CASES (Session 2.2 — context-management evaluation) ───
    # These five entries test contextualize_query. Each `question` is a
    # follow-up that is UNANSWERABLE on its own — retrieval against the raw
    # question would miss the right document. The synthetic assistant turn
    # in each `history` is plausible-but-not-perfect (mimics a real chat
    # state, not a textbook answer).

    # 11. Pronoun reference — "days" only resolves with vacation context
    {
        "id": "vacation_days_followup",
        "question": "How many days do I get?",
        "expected_answer": (
            "Eligible full-time employees receive 20 vacation days per calendar "
            "year, with up to 10 days allowed to carry over."
        ),
        "expected_source": ["vacation_policy_2025.md"],
        "category": "multi_turn",
        "difficulty": "medium",
        "history": [
            {
                "role": "user",
                "content": "Can you tell me about Northbrook's vacation policy?",
            },
            {
                "role": "assistant",
                "content": (
                    "Northbrook offers paid vacation to eligible full-time "
                    "employees. Requests need advance notice and are subject to "
                    "manager approval."
                ),
            },
        ],
    },

    # 12. Topic narrowing — "travel" is the qualifier; expense doc is the source
    {
        "id": "expense_travel_narrowing",
        "question": "What about for travel specifically?",
        "expected_answer": (
            "For business travel, meals are capped at $65 per person per day. "
            "Travel expenses must be submitted within 30 days with itemized "
            "receipts and processed through the standard reimbursement workflow."
        ),
        "expected_source": ["expense_policy.md"],
        "category": "multi_turn",
        "difficulty": "medium",
        "history": [
            {
                "role": "user",
                "content": "What are the rules for getting expenses reimbursed?",
            },
            {
                "role": "assistant",
                "content": (
                    "All expenses need to be business-related and submitted with "
                    "receipts within a set window. There are per-meal caps that "
                    "vary by context."
                ),
            },
        ],
    },

    # 13. Implicit subject switch — "the same thing" = VPN install
    {
        "id": "vpn_mac_implicit",
        "question": "And how do I do the same thing on my Mac?",
        "expected_answer": (
            "On a Mac, install the Cloudflare Zero Trust client manually from "
            "the IT self-service portal. Personal/non-managed devices follow "
            "the manual install instructions on IT's support page; company-"
            "managed laptops get the client deployed automatically."
        ),
        "expected_source": ["memo_security_update.md"],
        "category": "multi_turn",
        "difficulty": "medium",
        "history": [
            {
                "role": "user",
                "content": "How do I get VPN set up on my work laptop?",
            },
            {
                "role": "assistant",
                "content": (
                    "Northbrook moved to Cloudflare Zero Trust for VPN. Most "
                    "company laptops have the client pushed automatically — "
                    "check your apps folder before installing manually."
                ),
            },
        ],
    },

    # 14. Cross-doc pivot — "that" = office move; question forces pivot to parking
    {
        "id": "relocation_parking_pivot",
        "question": "Does that affect my parking benefit?",
        "expected_answer": (
            "The new 250 Innovation Drive office includes 180 parking spaces, "
            "expanding capacity over the current location. Existing parking "
            "benefits carry over with the move; specific assignment details "
            "are coordinated through the relocation FAQ."
        ),
        "expected_source": ["memo_office_relocation.md"],
        "category": "multi_turn",
        "difficulty": "hard",
        "history": [
            {
                "role": "user",
                "content": "What's happening with the office relocation in March?",
            },
            {
                "role": "assistant",
                "content": (
                    "Northbrook is moving to 250 Innovation Drive in March 2025. "
                    "The new space is larger and includes updated amenities."
                ),
            },
        ],
    },

    # 15. Demonstrative clarification — "that" = self-assessment
    {
        "id": "review_deadline_clarify",
        "question": "What's the deadline for the self-assessment?",
        "expected_answer": (
            "Self-assessments are part of the mid-year and year-end review "
            "cycles. Employees submit their self-assessment ahead of the "
            "scheduled review meeting with their manager, with year-end "
            "self-assessments feeding into the December compensation cycle."
        ),
        "expected_source": ["employee_handbook.md"],
        "category": "multi_turn",
        "difficulty": "hard",
        "history": [
            {
                "role": "user",
                "content": "How do performance reviews work here?",
            },
            {
                "role": "assistant",
                "content": (
                    "Northbrook runs quarterly reviews with your direct manager. "
                    "Mid-year and year-end cycles also include a self-assessment "
                    "and peer feedback component."
                ),
            },
        ],
    },

    # ─── LAB 2 EXTENSIONS (Mazgaj) ─────────────────────────────────────
    # Three new golden cases targeting gaps in the v1 set:
    #   16. Out-of-scope refusal — measures whether the hardened prompt
    #       actually refuses non-corpus questions.
    #   17. Hard cross-document synthesis — forces retrieval to cover two
    #       independent policy docs in a single answer (where naive often
    #       drops one); a key win condition for the reranker.
    #   18. Numeric precision — answer hinges on a specific dollar figure;
    #       lets us measure whether HyDE+rerank surfaces the exact chunk.

    # 16. Out-of-scope refusal (no source — the answer should refuse)
    {
        "id": "out_of_scope_stock_price",
        "question": "What is Northbrook Partners' current stock price?",
        "expected_answer": (
            "I don't have enough information to answer that question. The "
            "Northbrook documents do not contain stock price information."
        ),
        "expected_source": [],  # nothing should be retrieved with high confidence
        "category": "out_of_scope",
        "difficulty": "easy",
        "history": [],
    },

    # 17. Hard cross-document synthesis — expense_policy + remote_work_policy
    {
        "id": "remote_home_office_expense",
        "question": (
            "Can a fully remote employee expense their home office internet, "
            "and what's the equipment stipend they receive?"
        ),
        "expected_answer": (
            "Fully remote employees receive a $1,500 equipment stipend per "
            "the remote work policy. Expense reimbursement requires expenses "
            "to be business-related and submitted within 30 days with itemized "
            "receipts; home internet is not listed among the explicitly covered "
            "categories, so it would need to be handled through the standard "
            "business-expense rules."
        ),
        "expected_source": ["remote_work_policy.md", "expense_policy.md"],
        "category": "multi_doc",
        "difficulty": "hard",
        "history": [],
    },

    # 18. Numeric precision — exact dollar figure ($1,500 stipend)
    {
        "id": "remote_stipend_exact",
        "question": "How much is the remote work equipment stipend?",
        "expected_answer": (
            "The remote work equipment stipend is $1,500 for eligible remote "
            "employees, per the remote work policy."
        ),
        "expected_source": ["remote_work_policy.md"],
        "category": "policy_lookup",
        "difficulty": "easy",
        "history": [],
    },
]


# Quick sanity checks — also useful for students to explore
assert len(GOLDEN_SET) == 18, (
    "Golden set must have exactly 18 queries "
    "(10 single-turn + 5 multi-turn + 3 Lab 2 extensions)"
)
assert all("expected_answer" in q for q in GOLDEN_SET), "Every query needs an expected answer"
assert all(isinstance(q["expected_source"], list) for q in GOLDEN_SET), \
    "expected_source must be a list (even if it has one element)"
assert all("history" in q and isinstance(q["history"], list) for q in GOLDEN_SET), \
    "Every query needs a history field (list, possibly empty)"

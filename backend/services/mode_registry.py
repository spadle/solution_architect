from dataclasses import dataclass

from backend.engine.prompts import MODE_PROMPTS


@dataclass
class ConsultationMode:
    id: str
    name: str
    description: str
    icon: str
    system_prompt: str
    question_categories: list[str]
    initial_question: str
    max_depth: int = 50


MODES: dict[str, ConsultationMode] = {
    "software_architecture": ConsultationMode(
        id="software_architecture",
        name="Software Architecture",
        description="Design a software system from requirements to architecture",
        icon="building",
        system_prompt=MODE_PROMPTS["software_architecture"],
        question_categories=[
            "business_context",
            "functional_requirements",
            "non_functional",
            "constraints",
            "architecture_proposal",
        ],
        initial_question=(
            "What problem are you trying to solve, and who are the primary users of this system?"
        ),
    ),
    "api_design": ConsultationMode(
        id="api_design",
        name="API Design",
        description="Design RESTful or GraphQL APIs from use cases",
        icon="plug",
        system_prompt=MODE_PROMPTS["api_design"],
        question_categories=[
            "use_cases",
            "data_model",
            "auth",
            "api_style",
            "documentation",
        ],
        initial_question=(
            "What is the primary purpose of this API, and who will consume it?"
        ),
    ),
    "data_pipeline": ConsultationMode(
        id="data_pipeline",
        name="Data Pipeline",
        description="Design data ingestion, transformation, and storage pipelines",
        icon="database",
        system_prompt=MODE_PROMPTS["data_pipeline"],
        question_categories=[
            "data_sources",
            "transformations",
            "storage",
            "orchestration",
            "monitoring",
        ],
        initial_question=(
            "What data sources do you need to process, and what is the expected volume?"
        ),
    ),
    "cloud_migration": ConsultationMode(
        id="cloud_migration",
        name="Cloud Migration",
        description="Plan migration from on-premise to cloud infrastructure",
        icon="cloud",
        system_prompt=MODE_PROMPTS["cloud_migration"],
        question_categories=[
            "current_state",
            "target_state",
            "dependencies",
            "risk",
            "migration_strategy",
        ],
        initial_question=(
            "Describe your current infrastructure and what is driving the migration decision."
        ),
    ),
    "security_review": ConsultationMode(
        id="security_review",
        name="Security Review",
        description="Conduct a security assessment of an existing or planned system",
        icon="shield",
        system_prompt=MODE_PROMPTS["security_review"],
        question_categories=[
            "system_overview",
            "threat_model",
            "data_classification",
            "controls",
            "compliance",
        ],
        initial_question=(
            "What system are we reviewing, and what is the most sensitive data it handles?"
        ),
    ),
}


def get_mode(mode_id: str) -> ConsultationMode:
    if mode_id not in MODES:
        raise ValueError(f"Unknown mode: {mode_id}")
    return MODES[mode_id]


def list_modes() -> list[ConsultationMode]:
    return list(MODES.values())

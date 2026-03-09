"""Consultation mode definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConsultationMode:
    id: str
    name: str
    description: str
    icon: str
    categories: list[str]
    initial_question: str
    system_instructions: str


MODES: dict[str, ConsultationMode] = {
    "software_architecture": ConsultationMode(
        id="software_architecture",
        name="Software Architecture",
        description="Design a software system from requirements to architecture",
        icon="building",
        categories=[
            "business_context",
            "functional_requirements",
            "non_functional_requirements",
            "technical_constraints",
            "architecture_proposal",
        ],
        initial_question="What problem are you trying to solve, and who are the primary users of this system?",
        system_instructions="""You are conducting a Software Architecture consultation.

PHASES (follow this order):
1. Business Context — What problem, who are the users, what scale
2. Functional Requirements — Core features, integrations, data models
3. Non-Functional Requirements — Performance, security, compliance, availability
4. Technical Constraints — Budget, timeline, team skills, existing systems
5. Architecture Proposal — Propose options with trade-offs

Start with understanding the business problem before diving into technical details.
Focus on scalability, maintainability, and technology choices.""",
    ),
    "api_design": ConsultationMode(
        id="api_design",
        name="API Design",
        description="Design RESTful or GraphQL APIs from use cases",
        icon="plug",
        categories=[
            "use_cases",
            "data_model",
            "authentication",
            "api_style",
            "developer_experience",
        ],
        initial_question="What is the primary purpose of this API, and who will consume it?",
        system_instructions="""You are conducting an API Design consultation.

PHASES:
1. Use Cases — Who consumes the API, primary operations, data flow
2. Data Model — Core entities, relationships, data formats
3. Authentication & Authorization — Auth method, roles, scopes
4. API Style — REST vs GraphQL vs gRPC, versioning strategy
5. Developer Experience — Documentation, SDKs, error handling

Focus on consumer needs and developer experience.""",
    ),
    "data_pipeline": ConsultationMode(
        id="data_pipeline",
        name="Data Pipeline",
        description="Design data ingestion, transformation, and storage pipelines",
        icon="database",
        categories=[
            "data_sources",
            "transformations",
            "storage",
            "orchestration",
            "monitoring",
        ],
        initial_question="What data sources do you need to process, and what is the expected volume?",
        system_instructions="""You are conducting a Data Pipeline Design consultation.

PHASES:
1. Data Sources — Input sources, formats, volumes, frequencies
2. Transformations — Processing requirements, business rules, validation
3. Storage — Target storage, schema design, partitioning strategy
4. Orchestration — Scheduling, dependencies, error handling
5. Monitoring — Data quality, alerting, SLAs

Focus on data quality, reliability, and scalability.""",
    ),
    "cloud_migration": ConsultationMode(
        id="cloud_migration",
        name="Cloud Migration",
        description="Plan migration from on-premise to cloud infrastructure",
        icon="cloud",
        categories=[
            "current_state",
            "target_state",
            "dependencies",
            "risk_assessment",
            "migration_strategy",
        ],
        initial_question="Describe your current infrastructure and what is driving the migration decision.",
        system_instructions="""You are conducting a Cloud Migration Planning consultation.

PHASES:
1. Current State — Existing infrastructure, applications, dependencies
2. Target State — Cloud provider preferences, target architecture
3. Dependencies — Inter-service dependencies, data flows, external integrations
4. Risk Assessment — Compliance, data residency, downtime tolerance
5. Migration Strategy — Lift-and-shift vs re-architect, phased approach

Focus on risk mitigation and business continuity.""",
    ),
    "security_review": ConsultationMode(
        id="security_review",
        name="Security Review",
        description="Conduct a security assessment of an existing or planned system",
        icon="shield",
        categories=[
            "system_overview",
            "threat_model",
            "data_classification",
            "security_controls",
            "compliance",
        ],
        initial_question="What system are we reviewing, and what is the most sensitive data it handles?",
        system_instructions="""You are conducting a Security Architecture Review consultation.

PHASES:
1. System Overview — Architecture components, data flow, trust boundaries
2. Threat Model — Attack surfaces, threat actors, asset classification
3. Data Classification — Data types, sensitivity levels, retention policies
4. Security Controls — Current controls, gaps, compensating measures
5. Compliance — Regulatory requirements, audit needs, certification goals

Focus on risk-based prioritization and defense in depth.""",
    ),
    "qa_helper": ConsultationMode(
        id="qa_helper",
        name="Q&A Helper",
        description="Get structured answers to complex questions through guided exploration",
        icon="help-circle",
        categories=[
            "problem_definition",
            "context_gathering",
            "constraints",
            "options_analysis",
            "recommendation",
        ],
        initial_question="What question or problem are you trying to solve?",
        system_instructions="""You are conducting a structured Q&A consultation.

PHASES:
1. Problem Definition — Clarify the exact question or problem
2. Context Gathering — Understand background, stakeholders, and constraints
3. Constraints — Budget, timeline, resources, and limitations
4. Options Analysis — Explore possible solutions or answers with trade-offs
5. Recommendation — Provide structured recommendation with reasoning

Focus on understanding the full context before jumping to answers.""",
    ),
    "wedding_planner": ConsultationMode(
        id="wedding_planner",
        name="Wedding Planner",
        description="Plan your wedding with structured decisions on venue, catering, timeline, and more",
        icon="heart",
        categories=[
            "vision_and_style",
            "budget_and_guests",
            "venue_and_date",
            "vendors_and_services",
            "timeline_and_logistics",
        ],
        initial_question="Tell me about your dream wedding — what's the overall vision and who is getting married?",
        system_instructions="""You are conducting a Wedding Planning consultation.

PHASES:
1. Vision & Style — Theme, color palette, formality level, cultural traditions
2. Budget & Guest List — Total budget range, guest count, priority allocations
3. Venue & Date — Indoor/outdoor, location preferences, season, date flexibility
4. Vendors & Services — Catering, photography, music, flowers, attire, cake
5. Timeline & Logistics — Day-of timeline, transportation, accommodation, rehearsal

Focus on making decisions that align with the couple's vision and budget.""",
    ),
    "product_launch": ConsultationMode(
        id="product_launch",
        name="Product Launch",
        description="Plan a product launch strategy from positioning to go-to-market execution",
        icon="rocket",
        categories=[
            "product_positioning",
            "target_audience",
            "marketing_strategy",
            "launch_timeline",
            "success_metrics",
        ],
        initial_question="What product are you launching, and what problem does it solve?",
        system_instructions="""You are conducting a Product Launch Planning consultation.

PHASES:
1. Product Positioning — Value proposition, competitive differentiation, pricing strategy
2. Target Audience — Primary personas, market segments, customer pain points
3. Marketing Strategy — Channels, messaging, content plan, PR strategy
4. Launch Timeline — Pre-launch, launch day, post-launch activities and milestones
5. Success Metrics — KPIs, targets, measurement tools, feedback loops

Focus on creating a clear, actionable launch plan with measurable goals.""",
    ),
    "event_planning": ConsultationMode(
        id="event_planning",
        name="Event Planning",
        description="Plan conferences, parties, corporate events, or community gatherings",
        icon="calendar",
        categories=[
            "event_concept",
            "budget_and_scale",
            "venue_and_logistics",
            "program_and_content",
            "promotion_and_experience",
        ],
        initial_question="What type of event are you planning, and what's the occasion?",
        system_instructions="""You are conducting an Event Planning consultation.

PHASES:
1. Event Concept — Type, theme, goals, target audience, formality
2. Budget & Scale — Budget range, expected attendance, duration
3. Venue & Logistics — Location, layout, A/V needs, catering, accessibility
4. Program & Content — Schedule, speakers, activities, entertainment
5. Promotion & Experience — Invitations, marketing, attendee experience, follow-up

Focus on creating a memorable event that meets objectives within budget.""",
    ),
    "business_strategy": ConsultationMode(
        id="business_strategy",
        name="Business Strategy",
        description="Develop business strategy including market analysis, competitive positioning, and growth plans",
        icon="trending-up",
        categories=[
            "business_model",
            "market_analysis",
            "competitive_landscape",
            "growth_strategy",
            "execution_plan",
        ],
        initial_question="What business are you building or growing, and what's your current situation?",
        system_instructions="""You are conducting a Business Strategy consultation.

PHASES:
1. Business Model — Revenue model, value proposition, customer segments
2. Market Analysis — Market size, trends, opportunities, threats
3. Competitive Landscape — Key competitors, differentiation, barriers to entry
4. Growth Strategy — Acquisition channels, partnerships, scaling approach
5. Execution Plan — Priorities, milestones, team needs, resource allocation

Focus on actionable strategies grounded in market reality.""",
    ),
}


MODE_TRANSLATIONS: dict[str, dict[str, dict[str, str]]] = {
    "ko": {
        "software_architecture": {
            "name": "소프트웨어 아키텍처",
            "description": "요구사항부터 아키텍처까지 소프트웨어 시스템을 설계합니다",
        },
        "api_design": {
            "name": "API 설계",
            "description": "사용 사례를 기반으로 RESTful 또는 GraphQL API를 설계합니다",
        },
        "data_pipeline": {
            "name": "데이터 파이프라인",
            "description": "데이터 수집, 변환 및 저장 파이프라인을 설계합니다",
        },
        "cloud_migration": {
            "name": "클라우드 마이그레이션",
            "description": "온프레미스에서 클라우드 인프라로의 마이그레이션을 계획합니다",
        },
        "security_review": {
            "name": "보안 검토",
            "description": "기존 또는 계획된 시스템의 보안 평가를 수행합니다",
        },
        "qa_helper": {
            "name": "Q&A 도우미",
            "description": "체계적인 탐색을 통해 복잡한 질문에 대한 답을 찾습니다",
        },
        "wedding_planner": {
            "name": "웨딩 플래너",
            "description": "장소, 케이터링, 일정 등 웨딩을 체계적으로 계획합니다",
        },
        "product_launch": {
            "name": "제품 출시",
            "description": "포지셔닝부터 시장 진출 전략까지 제품 출시를 계획합니다",
        },
        "event_planning": {
            "name": "이벤트 기획",
            "description": "컨퍼런스, 파티, 기업 행사 또는 커뮤니티 모임을 계획합니다",
        },
        "business_strategy": {
            "name": "비즈니스 전략",
            "description": "시장 분석, 경쟁 포지셔닝, 성장 전략을 수립합니다",
        },
    },
}


def get_mode(mode_id: str) -> ConsultationMode:
    if mode_id not in MODES:
        raise ValueError(f"Unknown mode: {mode_id}. Available: {', '.join(MODES.keys())}")
    return MODES[mode_id]


def list_modes(language: str = "en") -> list[dict]:
    """Return modes with optional translation overlay."""
    result = []
    translations = MODE_TRANSLATIONS.get(language, {})
    for mode in MODES.values():
        tr = translations.get(mode.id, {})
        result.append({
            "id": mode.id,
            "name": tr.get("name", mode.name),
            "description": tr.get("description", mode.description),
            "icon": mode.icon,
        })
    return result

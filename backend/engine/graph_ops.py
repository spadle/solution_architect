from uuid import uuid4


def calculate_node_position(
    depth: int, sibling_index: int, total_siblings: int
) -> tuple[float, float]:
    """Calculate node position based on tree depth and sibling index.

    Uses a simple tree layout: x based on depth, y spread across siblings.
    """
    x = depth * 250.0
    y_spread = 150.0
    y_center = (total_siblings - 1) * y_spread / 2
    y = sibling_index * y_spread - y_center
    return x, y


def generate_node_id() -> str:
    return str(uuid4())


def sanitize_mermaid_label(label: str) -> str:
    """Escape special characters for Mermaid syntax."""
    label = label.replace('"', "'")
    label = label.replace("[", "(")
    label = label.replace("]", ")")
    label = label.replace("{", "(")
    label = label.replace("}", ")")
    if len(label) > 60:
        label = label[:57] + "..."
    return label


def nodes_edges_to_mermaid(nodes: list[dict], edges: list[dict]) -> str:
    """Convert node and edge data to Mermaid flowchart syntax."""
    lines = ["flowchart TD"]

    node_type_shapes = {
        "start": ("([", "])"),
        "end": ("([", "])"),
        "question": ("{", "}"),
        "decision": ("{", "}"),
        "answer": ("[", "]"),
        "info": ("(", ")"),
        "research": ("[[", "]]"),
        "summary": ("([", "])"),
    }

    for node in nodes:
        nid = node["id"].replace("-", "_")
        label = sanitize_mermaid_label(node["label"])
        ntype = node.get("node_type", "info")
        open_b, close_b = node_type_shapes.get(ntype, ("[", "]"))
        lines.append(f"    {nid}{open_b}\"{label}\"{close_b}")

    for edge in edges:
        src = edge["source_node_id"].replace("-", "_")
        tgt = edge["target_node_id"].replace("-", "_")
        label = edge.get("label", "")
        is_taken = edge.get("is_taken", True)

        if label:
            label_safe = sanitize_mermaid_label(label)
            if is_taken:
                lines.append(f"    {src} -->|\"{label_safe}\"| {tgt}")
            else:
                lines.append(f"    {src} -.->|\"{label_safe}\"| {tgt}")
        else:
            if is_taken:
                lines.append(f"    {src} --> {tgt}")
            else:
                lines.append(f"    {src} -.-> {tgt}")

    # Styling
    lines.append("")
    lines.append("    classDef question fill:#4F46E5,stroke:#3730A3,color:#fff")
    lines.append("    classDef answer fill:#059669,stroke:#047857,color:#fff")
    lines.append("    classDef info fill:#0891B2,stroke:#0E7490,color:#fff")
    lines.append("    classDef start fill:#7C3AED,stroke:#6D28D9,color:#fff")
    lines.append("    classDef summary fill:#D97706,stroke:#B45309,color:#fff")
    lines.append("    classDef skipped fill:#9CA3AF,stroke:#6B7280,color:#fff")
    lines.append("    classDef research fill:#EC4899,stroke:#DB2777,color:#fff")

    for node in nodes:
        nid = node["id"].replace("-", "_")
        ntype = node.get("node_type", "info")
        status = node.get("status", "")
        if status == "skipped":
            lines.append(f"    class {nid} skipped")
        elif ntype in node_type_shapes:
            lines.append(f"    class {nid} {ntype}")

    return "\n".join(lines)

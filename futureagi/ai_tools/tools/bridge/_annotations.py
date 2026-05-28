"""Bridge registration for AnnotationsLabelsViewSet + AnnotationsViewSet."""

from ai_tools.drf_bridge import expose_to_mcp
from model_hub.views.develop_annotations import (
    AnnotationsLabelsViewSet,
    AnnotationsViewSet,
)

# entity 'annotations_labels' is awkward — use 'annotation_label' for the LLM
expose_to_mcp(
    category="annotations",
    tools={
        "list": {"name": "list_annotation_labels"},
        "retrieve": {"name": "get_annotation_label"},
        "create": {"name": "create_annotation_label"},
        "update": {"name": "update_annotation_label"},
        "destroy": {"name": "delete_annotation_label"},
    },
)(AnnotationsLabelsViewSet)

expose_to_mcp(
    category="annotations",
    tools={
        "list": {"name": "list_annotations"},
        "retrieve": {"name": "get_annotation"},
    },
)(AnnotationsViewSet)

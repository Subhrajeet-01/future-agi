import uuid

from model_hub.models.ai_model import AIModel
from model_hub.models.evals_metric import EvalTemplate
from tracer.models.custom_eval_config import CustomEvalConfig
from tracer.models.project import Project
from tracer.models.trace import Trace


def create_observe_project(*, organization, workspace, user=None, name=None):
    return Project.no_workspace_objects.create(
        name=name or f"Observe {uuid.uuid4().hex[:8]}",
        organization=organization,
        workspace=workspace,
        user=user,
        model_type=AIModel.ModelTypes.GENERATIVE_LLM,
        trace_type="observe",
    )


def create_trace(*, project, name=None, with_payload=True):
    payload = {"value": "private"} if with_payload else None
    return Trace.no_workspace_objects.create(
        project=project,
        name=name or f"Trace {uuid.uuid4().hex[:8]}",
        input=payload,
        output=payload,
    )


def create_custom_eval(*, organization, workspace, project, name=None):
    template = EvalTemplate.no_workspace_objects.create(
        name=name or f"quality-{uuid.uuid4().hex[:8]}",
        organization=organization,
        workspace=workspace,
    )
    return CustomEvalConfig.no_workspace_objects.create(
        name=name or f"quality-{uuid.uuid4().hex[:8]}",
        eval_template=template,
        project=project,
    )

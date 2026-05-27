import uuid

from model_hub.models.ai_model import AIModel
from model_hub.models.evals_metric import EvalTemplate
from model_hub.models.run_prompt import (
    PromptEvalConfig,
    PromptTemplate,
    PromptVersion,
)
from tracer.models.custom_eval_config import CustomEvalConfig
from tracer.models.project import Project
from tracer.models.trace import Trace


def create_observe_project(
    *, organization, workspace, user=None, name=None, metadata=None
):
    return Project.no_workspace_objects.create(
        name=name or f"Observe {uuid.uuid4().hex[:8]}",
        organization=organization,
        workspace=workspace,
        user=user,
        model_type=AIModel.ModelTypes.GENERATIVE_LLM,
        trace_type="observe",
        metadata=metadata,
    )


def create_trace(*, project, name=None, with_payload=True, metadata=None, error=None):
    payload = {"value": "private"} if with_payload else None
    return Trace.no_workspace_objects.create(
        project=project,
        name=name or f"Trace {uuid.uuid4().hex[:8]}",
        metadata=metadata,
        input=payload,
        output=payload,
        error=error,
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


def create_prompt_template(
    *, organization, workspace, user=None, name=None, is_sample=False
):
    template = PromptTemplate.no_workspace_objects.create(
        name=name or f"Prompt {uuid.uuid4().hex[:8]}",
        organization=organization,
        workspace=workspace,
        created_by=user,
        is_sample=is_sample,
    )
    if user:
        template.collaborators.add(user)
    return template


def create_prompt_version(
    *,
    template,
    version="v1",
    is_draft=True,
    is_default=False,
    commit_message="",
    output=None,
):
    return PromptVersion.no_workspace_objects.create(
        original_template=template,
        template_version=version,
        prompt_config_snapshot={
            "messages": [{"role": "user", "content": "Say hello"}],
            "configuration": {"model": "gpt-4o-mini"},
        },
        variable_names={},
        metadata={},
        output=[] if output is None else output,
        is_draft=is_draft,
        is_default=is_default,
        commit_message=commit_message,
    )


def create_prompt_eval_config(*, organization, workspace, template, name=None):
    eval_template = EvalTemplate.no_workspace_objects.create(
        name=name or f"prompt-quality-{uuid.uuid4().hex[:8]}",
        organization=organization,
        workspace=workspace,
    )
    return PromptEvalConfig.no_workspace_objects.create(
        name=name or f"prompt-quality-{uuid.uuid4().hex[:8]}",
        eval_template=eval_template,
        prompt_template=template,
    )

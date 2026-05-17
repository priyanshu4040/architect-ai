"""
Compile greenfield requirements from guided answers or templates.
"""

from typing import Any, Dict, List

from agents.greenfield_templates import get_template
from agents.output_schemas import RequirementCompileOutput


def compile_from_guided(answers: Dict[str, Any]) -> RequirementCompileOutput:
    project_type = str(answers.get("project_type") or answers.get("app_type") or "Web Application")
    users = _as_list(answers.get("users"))
    features = _as_list(answers.get("features") or answers.get("main_features"))
    auth = str(answers.get("authentication") or answers.get("auth") or "Not specified")
    database = str(answers.get("database") or "Not sure")
    level = str(answers.get("project_level") or "Mini Project")
    stack = str(answers.get("preferred_technology") or answers.get("preferred_stack") or "Not sure")
    deploy = str(answers.get("deployment") or answers.get("deployment_preference") or "Not sure")

    fr = features or ["Core CRUD for main entities", "User-facing dashboard"]
    nfr = [
        f"Authentication: {auth}",
        f"Database: {database}",
        f"Project level: {level}",
        f"Deployment: {deploy}",
    ]

    summary = (
        f"Build a {project_type} web application.\n\n"
        f"Users/Roles: {', '.join(users) if users else 'General users'}.\n\n"
        f"Main features:\n" + "\n".join(f"- {f}" for f in fr) + "\n\n"
        f"Authentication approach: {auth}.\n"
        f"Database: {database}.\n"
        f"Target level: {level}.\n"
        f"Preferred technology: {stack}.\n"
        f"Deployment: {deploy}.\n"
    )

    return RequirementCompileOutput(
        requirement_source="guided",
        project_type=project_type,
        users=users,
        functional_requirements=fr,
        non_functional_requirements=nfr,
        preferred_stack=stack,
        project_level=level,
        deployment_preference=deploy,
        generated_requirement_summary=summary.strip(),
    )


def compile_from_template(template_id: str, overrides: Dict[str, Any] | None = None) -> RequirementCompileOutput:
    tpl = get_template(template_id)
    if not tpl:
        raise ValueError(f"Unknown template: {template_id}")
    data = {**tpl, **(overrides or {})}

    summary = (
        f"Project: {data.get('name', template_id)}\n"
        f"Domain: {data.get('project_type', '')}\n\n"
        f"Users: {', '.join(data.get('users', []))}\n\n"
        f"Functional requirements:\n"
        + "\n".join(f"- {x}" for x in data.get("functional_requirements", []))
        + "\n\nNon-functional requirements:\n"
        + "\n".join(f"- {x}" for x in data.get("non_functional_requirements", []))
        + f"\n\nModules: {', '.join(data.get('modules', []))}\n"
        + f"Entities: {', '.join(data.get('database_entities', []))}\n"
        + f"Preferred stack: {data.get('preferred_stack', '')}\n"
        + f"Level: {data.get('project_level', '')}\n"
        + f"Deployment: {data.get('deployment_preference', '')}\n"
    )

    return RequirementCompileOutput(
        requirement_source="template",
        project_type=str(data.get("project_type", "")),
        users=list(data.get("users", [])),
        functional_requirements=list(data.get("functional_requirements", [])),
        non_functional_requirements=list(data.get("non_functional_requirements", [])),
        preferred_stack=str(data.get("preferred_stack", "")),
        project_level=str(data.get("project_level", "")),
        deployment_preference=str(data.get("deployment_preference", "")),
        generated_requirement_summary=summary.strip(),
    )


def _as_list(val) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        return [x.strip() for x in val.replace("\n", ",").split(",") if x.strip()]
    return [str(val)]

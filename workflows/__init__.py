from importlib import import_module

# flake8: noqa: F401
# pylint: disable=W0611


def import_extensions(workflow_type: str):
    """Import workflow modules by workflow_type to trigger NimbusWorkFlow.register.

    - Real simulation projects can extend this with more branches
    - This repo currently only ships a built-in mock demo: "MockWorkFlow"
    """
    if workflow_type == "MockWorkFlow":
        import_module("workflows.mock_workflow")
    else:
        raise ValueError(f"Unsupported workflow type: {workflow_type}")


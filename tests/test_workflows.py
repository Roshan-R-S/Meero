from pathlib import Path


def test_model_workflows_use_full_training_default():
    workflow_paths = [
        Path(".github/workflows/eval-on-main.yml"),
        Path(".github/workflows/publish-model.yml"),
    ]

    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        assert "--epochs 5" not in workflow
        assert "MODEL_EPOCHS:-5" not in workflow

    eval_workflow = workflow_paths[0].read_text(encoding="utf-8")
    assert "MODEL_EPOCHS: ${{ vars.MODEL_EPOCHS || '100' }}" in eval_workflow

    publish_workflow = workflow_paths[1].read_text(encoding="utf-8")
    assert 'MODEL_EPOCHS:-100' in publish_workflow

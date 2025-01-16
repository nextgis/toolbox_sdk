from toolbox_sdk import TaskResult


def test_task_result():
    task_id = "1571686e-bcd6-42e2-a101-5fe270dd7a65"
    state = "SUCCESS"
    tr = TaskResult(
        outputs=[
            {
                "name": "hello",
                "title": "hello",
                "type": "unicode",
                "value": "Hello, Natalia!",
            }
        ],
        task_id=task_id,
        state=state,
    )
    assert tr.task_id == task_id
    assert tr.state == state
    assert tr.value == "Hello, Natalia!"
    assert tr["hello"] == "Hello, Natalia!"

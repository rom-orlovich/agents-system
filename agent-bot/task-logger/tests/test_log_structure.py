import json

from logger import TaskLogger


class TestLogDirectoryStructure:
    def test_task_directory_created_atomically(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        assert logger.log_dir.exists()
        assert logger.log_dir == tmp_path / "task-001"

    def test_each_task_has_separate_directory(self, tmp_path):
        logger1 = TaskLogger("task-001", tmp_path)
        logger2 = TaskLogger("task-002", tmp_path)

        assert logger1.log_dir != logger2.log_dir
        assert logger1.log_dir.exists()
        assert logger2.log_dir.exists()


class TestJsonFileValidity:
    def test_metadata_json_is_valid_json(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)
        metadata = {
            "task_id": "task-001",
            "source": "webhook",
            "assigned_agent": "executor",
        }

        logger.write_metadata(metadata)

        metadata_file = tmp_path / "task-001" / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            loaded = json.load(f)
            assert loaded == metadata

    def test_input_json_is_valid_json(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)
        input_data = {"message": "Fix the authentication bug"}

        logger.write_input(input_data)

        input_file = tmp_path / "task-001" / "01-input.json"
        assert input_file.exists()

        with open(input_file) as f:
            loaded = json.load(f)
            assert loaded == input_data

    def test_final_result_json_is_valid_json(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)
        result = {
            "success": True,
            "result": "Bug fixed",
            "metrics": {"cost_usd": 0.05},
            "completed_at": "2026-01-31T12:00:00Z",
        }

        logger.write_final_result(result)

        result_file = tmp_path / "task-001" / "06-final-result.json"
        assert result_file.exists()

        with open(result_file) as f:
            loaded = json.load(f)
            assert loaded == result


class TestJsonlFileValidity:
    """Tests for JSONL file validity."""

    def test_webhook_flow_jsonl_valid(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        events = [
            {"timestamp": "2026-01-31T12:00:00Z", "stage": "received", "data": {}},
            {"timestamp": "2026-01-31T12:00:01Z", "stage": "validated", "data": {}},
            {"timestamp": "2026-01-31T12:00:02Z", "stage": "task_created", "data": {}},
        ]

        for event in events:
            logger.append_webhook_event(event)

        webhook_file = tmp_path / "task-001" / "03-webhook-flow.jsonl"
        assert webhook_file.exists()

        with open(webhook_file) as f:
            lines = f.readlines()
            assert len(lines) == 3
            for i, line in enumerate(lines):
                loaded = json.loads(line)
                assert loaded == events[i]

    def test_agent_output_jsonl_valid(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        outputs = [
            {
                "timestamp": "2026-01-31T12:00:00Z",
                "type": "output",
                "content": "Analyzing...",
            },
            {
                "timestamp": "2026-01-31T12:00:01Z",
                "type": "output",
                "content": "Found issue",
            },
        ]

        for output in outputs:
            logger.append_agent_output(output)

        output_file = tmp_path / "task-001" / "04-agent-output.jsonl"
        assert output_file.exists()

        with open(output_file) as f:
            lines = f.readlines()
            assert len(lines) == 2
            for i, line in enumerate(lines):
                loaded = json.loads(line)
                assert loaded == outputs[i]

    def test_user_inputs_jsonl_valid(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        user_input = {
            "timestamp": "2026-01-31T12:00:00Z",
            "type": "user_response",
            "question_type": "approval",
            "content": "yes",
        }

        logger.append_user_input(user_input)

        user_input_file = tmp_path / "task-001" / "02-user-inputs.jsonl"
        assert user_input_file.exists()

        with open(user_input_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            loaded = json.loads(lines[0])
            assert loaded == user_input

    def test_knowledge_interactions_jsonl_valid(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        interaction = {
            "timestamp": "2026-01-31T12:00:00Z",
            "tool_name": "knowledge_query",
            "query": "authentication bug",
            "source_types": ["code", "jira"],
            "results_count": 5,
            "query_time_ms": 150.5,
        }

        logger.append_knowledge_interaction(interaction)

        knowledge_file = tmp_path / "task-001" / "05-knowledge-interactions.jsonl"
        assert knowledge_file.exists()

        with open(knowledge_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            loaded = json.loads(lines[0])
            assert loaded == interaction


class TestCompleteLogStructure:
    def test_complete_log_structure(self, tmp_path):
        task_id = "task-001"
        logger = TaskLogger(task_id, tmp_path)

        logger.write_metadata(
            {
                "task_id": task_id,
                "source": "webhook",
                "assigned_agent": "executor",
            }
        )

        logger.write_input({"message": "Fix bug"})

        logger.append_user_input(
            {
                "timestamp": "2026-01-31T12:00:00Z",
                "type": "user_response",
                "question_type": "approval",
                "content": "yes",
            }
        )

        logger.append_webhook_event(
            {
                "timestamp": "2026-01-31T12:00:01Z",
                "stage": "received",
                "data": {},
            }
        )

        logger.append_agent_output(
            {
                "timestamp": "2026-01-31T12:00:02Z",
                "type": "output",
                "content": "Working...",
            }
        )

        logger.append_knowledge_interaction(
            {
                "timestamp": "2026-01-31T12:00:03Z",
                "tool_name": "code_search",
                "query": "authentication",
                "results_count": 3,
            }
        )

        logger.write_final_result(
            {
                "success": True,
                "result": "Done",
                "completed_at": "2026-01-31T12:00:04Z",
            }
        )

        task_dir = tmp_path / task_id
        assert (task_dir / "metadata.json").exists()
        assert (task_dir / "01-input.json").exists()
        assert (task_dir / "02-user-inputs.jsonl").exists()
        assert (task_dir / "03-webhook-flow.jsonl").exists()
        assert (task_dir / "04-agent-output.jsonl").exists()
        assert (task_dir / "05-knowledge-interactions.jsonl").exists()
        assert (task_dir / "06-final-result.json").exists()


class TestLogFileNaming:
    def test_file_naming_convention(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        logger.write_metadata({"task_id": "task-001"})
        logger.write_input({"message": "test"})
        logger.append_user_input({"type": "test"})
        logger.append_webhook_event({"stage": "test"})
        logger.append_agent_output({"type": "test"})
        logger.append_knowledge_interaction({"tool_name": "test"})
        logger.write_final_result({"success": True})

        task_dir = tmp_path / "task-001"
        expected_files = [
            "metadata.json",
            "01-input.json",
            "02-user-inputs.jsonl",
            "03-webhook-flow.jsonl",
            "04-agent-output.jsonl",
            "05-knowledge-interactions.jsonl",
            "06-final-result.json",
        ]

        for filename in expected_files:
            assert (task_dir / filename).exists(), f"Missing: {filename}"

    def test_file_order_reflects_workflow(self, tmp_path):
        logger = TaskLogger("task-001", tmp_path)

        logger.write_input({"message": "test"})
        logger.append_user_input({"type": "approval"})
        logger.append_webhook_event({"stage": "received"})
        logger.append_agent_output({"type": "output"})
        logger.append_knowledge_interaction({"tool_name": "search"})
        logger.write_final_result({"success": True})

        task_dir = tmp_path / "task-001"
        files = sorted([f.name for f in task_dir.iterdir()])

        assert files == [
            "01-input.json",
            "02-user-inputs.jsonl",
            "03-webhook-flow.jsonl",
            "04-agent-output.jsonl",
            "05-knowledge-interactions.jsonl",
            "06-final-result.json",
        ]

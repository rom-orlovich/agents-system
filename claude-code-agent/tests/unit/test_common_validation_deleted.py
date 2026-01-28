"""TDD tests to verify common/validation.py and bash script are deleted (Phase 5)."""

import pytest
import os
from pathlib import Path


class TestCommonValidationDeleted:
    """Test that common/validation.py is deleted."""

    def test_cannot_import_from_common_validation(self):
        """Importing from common.validation should fail."""
        with pytest.raises(ImportError):
            from api.webhooks.common.validation import validate_response_format

    def test_common_validation_file_does_not_exist(self):
        """common/validation.py file should not exist."""
        validation_path = Path("api/webhooks/common/validation.py")
        assert not validation_path.exists(), f"File {validation_path} should be deleted"

    def test_bash_script_does_not_exist(self):
        """scripts/validate-response-format.sh should not exist."""
        script_path = Path("scripts/validate-response-format.sh")
        assert not script_path.exists(), f"Script {script_path} should be deleted"

    def test_common_init_is_empty_or_deleted(self):
        """common/__init__.py should be empty or deleted if no other files exist."""
        common_init = Path("api/webhooks/common/__init__.py")
        common_dir = Path("api/webhooks/common")

        if common_dir.exists():
            py_files = list(common_dir.glob("*.py"))
            if py_files == [common_init] or not py_files:
                if common_init.exists():
                    content = common_init.read_text().strip()
                    assert content == "", f"common/__init__.py should be empty, but contains: {content}"

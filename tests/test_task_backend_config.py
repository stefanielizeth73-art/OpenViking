# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

import pytest

from openviking.service.task_store import PersistentTaskStore
from openviking.service.task_tracker import TaskTracker
from openviking_cli.utils.config import storage_config as storage_config_module
from openviking_cli.utils.config.storage_config import StorageConfig


class _FakeAgfs:
    def mkdir(self, path: str, mode: str = "755"):
        return {"message": "created", "mode": mode}

    def write(self, path: str, data):
        return "OK"

    def read(self, path: str, offset: int = 0, size: int = -1, stream: bool = False):
        raise FileNotFoundError(path)

    def ls(self, path: str = "/"):
        return []

    def rm(self, path: str, recursive: bool = False, force: bool = True):
        return {"message": "deleted"}


def test_storage_config_has_no_task_tracker_config():
    config = StorageConfig()
    assert not hasattr(config, "task_tracker")


def test_storage_config_ignores_deprecated_task_tracker_config(monkeypatch):
    warnings = []
    monkeypatch.setattr(storage_config_module.logger, "warning", warnings.append)

    config = StorageConfig(task_tracker={"backend": "memory"})

    assert not hasattr(config, "task_tracker")
    assert any("task_tracker" in message for message in warnings)
    assert any("deprecated and ignored" in message for message in warnings)


def test_storage_config_defaults_skip_process_lock_to_false():
    config = StorageConfig()
    assert config.skip_process_lock is False


def test_storage_config_accepts_skip_process_lock():
    config = StorageConfig(skip_process_lock=True)
    assert config.skip_process_lock is True


def test_storage_config_builds_persistent_task_tracker():
    tracker = StorageConfig().build_task_tracker(_FakeAgfs())
    assert isinstance(tracker, TaskTracker)
    assert isinstance(tracker._store, PersistentTaskStore)


@pytest.mark.parametrize("backend", ["agfs", "vectordb"])
@pytest.mark.parametrize("dump", [False, True])
def test_storage_paths_warn_only_when_overridden(tmp_path, monkeypatch, backend, dump):
    warnings = []
    monkeypatch.setattr(storage_config_module.logger, "warning", warnings.append)
    workspace = str(tmp_path / "workspace")
    config = StorageConfig(workspace=workspace)
    for _ in range(2):
        config = StorageConfig.model_validate(config.model_dump() if dump else config)
        assert config.agfs.path == config.vectordb.path == config.workspace
    assert not any(".path'" in message for message in warnings)

    config = StorageConfig(workspace=workspace, **{backend: {"path": str(tmp_path / "old")}})
    assert config.agfs.path == config.vectordb.path == config.workspace
    assert len([message for message in warnings if f"'{backend}.path'" in message]) == 1
    warnings.clear()
    StorageConfig.model_validate(config.model_dump())
    assert not any(".path'" in message for message in warnings)

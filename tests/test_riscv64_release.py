from pathlib import Path
import unittest


class TestRiscv64Release(unittest.TestCase):

    def test_host_local_network_guard_uses_network_name(self):
        repository = Path(__file__).resolve().parents[1]
        tasks = (
            repository
            / "onecloud/roles/primary-master-node/setup_cloud/tasks/main.yml"
        ).read_text(encoding="utf-8")
        task = tasks.split(
            "- name: add default host-local network", 1
        )[1].split("\n- name:", 1)[0]

        self.assertIn("network-show vhl0", task)
        self.assertIn("network-show vh0", task)
        self.assertNotIn("network-show __host_local__", task)
        self.assertIn(
            "network-create3 --server-type hostlocal __host_local__ vh0",
            task,
        )

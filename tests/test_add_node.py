import unittest
from unittest import mock

from lib.service import AddNodesConfig


class FakeNode:

    def __init__(self, hostname, ip):
        self.hostname = hostname
        self.ip = ip

    def get_hostname(self):
        return self.hostname

    def get_ip(self):
        return self.ip


class FakeCluster:

    def __init__(self, node):
        self.node = node
        self.k8s_nodes = [node]
        self.ssh_client = mock.Mock()
        self.ssh_client.exec_command.return_value = ""

    def find_node_by_ip_or_hostname(self, target):
        if target in (self.node.get_ip(), self.node.get_hostname()):
            return self.node
        return None

    def get_current_version(self):
        return "v4.0.3-riscv64.6"

    def get_cluster_controlplane_host(self):
        return "10.213.6.187"

    def get_primary_master_node_ip(self):
        return "10.213.6.187"

    def get_repository(self):
        return "ghcr.io/yinjiayi", False

    def get_image_repository(self):
        return "ghcr.io/yinjiayi"

    def is_using_k3s(self):
        return True


class TestAddNodesConfig(unittest.TestCase):

    @mock.patch(
        "lib.service.resolve_ssh_private_file",
        return_value="/tmp/ocboot-test-id_ed25519",
    )
    @mock.patch("lib.service.SSHClient")
    def test_allows_idempotent_retry_for_the_same_node(
            self, ssh_client, _resolve_ssh_private_file):
        existing = FakeNode("openeuler-riscv64-188", "10.213.6.188")
        ssh_client.return_value.get_hostname.return_value = existing.hostname

        config = AddNodesConfig(
            FakeCluster(existing),
            [existing.ip],
            "root",
            "/root/.ssh/id_ed25519",
            22,
            22,
            runtime="qemu",
        )

        self.assertEqual(config.worker_config.nodes[0].host, existing.ip)

    @mock.patch(
        "lib.service.resolve_ssh_private_file",
        return_value="/tmp/ocboot-test-id_ed25519",
    )
    @mock.patch("lib.service.SSHClient")
    def test_rejects_an_existing_ip_with_a_different_hostname(
            self, ssh_client, _resolve_ssh_private_file):
        existing = FakeNode("openeuler-riscv64-188", "10.213.6.188")
        ssh_client.return_value.get_hostname.return_value = "unexpected-host"

        with self.assertRaisesRegex(Exception, "already exists"):
            AddNodesConfig(
                FakeCluster(existing),
                [existing.ip],
                "root",
                "/root/.ssh/id_ed25519",
                22,
                22,
                runtime="qemu",
            )

    @mock.patch(
        "lib.service.resolve_ssh_private_file",
        return_value="/tmp/ocboot-test-id_ed25519",
    )
    @mock.patch("lib.service.SSHClient")
    def test_rejects_a_new_ip_with_an_existing_hostname(
            self, ssh_client, _resolve_ssh_private_file):
        existing = FakeNode("openeuler-riscv64-188", "10.213.6.188")
        ssh_client.return_value.get_hostname.return_value = existing.hostname

        with self.assertRaisesRegex(Exception, "Duplicate hostname"):
            AddNodesConfig(
                FakeCluster(existing),
                ["10.213.6.183"],
                "root",
                "/root/.ssh/id_ed25519",
                22,
                22,
                runtime="qemu",
            )

    @mock.patch(
        "lib.service.resolve_ssh_private_file",
        return_value="/tmp/ocboot-test-id_ed25519",
    )
    @mock.patch("lib.service.SSHClient")
    def test_rejects_duplicate_hostnames_in_the_same_batch(
            self, ssh_client, _resolve_ssh_private_file):
        existing = FakeNode("openeuler-riscv64", "10.213.6.187")
        ssh_client.return_value.get_hostname.return_value = "duplicate-worker"

        with self.assertRaisesRegex(Exception, "Duplicate hostname"):
            AddNodesConfig(
                FakeCluster(existing),
                ["10.213.6.183", "10.213.6.184"],
                "root",
                "/root/.ssh/id_ed25519",
                22,
                22,
                runtime="qemu",
            )

    @mock.patch(
        "lib.service.resolve_ssh_private_file",
        return_value="/tmp/ocboot-test-id_ed25519",
    )
    @mock.patch("lib.service.SSHClient")
    def test_passes_postflight_options_to_ansible(
            self, ssh_client, _resolve_ssh_private_file):
        existing = FakeNode("openeuler-riscv64", "10.213.6.187")
        ssh_client.return_value.get_hostname.return_value = "new-worker"

        config = AddNodesConfig(
            FakeCluster(existing),
            ["10.213.6.183"],
            "root",
            "/root/.ssh/id_ed25519",
            22,
            22,
            runtime="qemu",
            enable_host_after_ready=True,
            skip_postflight=True,
        )

        self.assertTrue(config.get_vars()["enable_host_after_ready"])
        self.assertTrue(config.get_vars()["skip_add_node_postflight"])


if __name__ == "__main__":
    unittest.main()

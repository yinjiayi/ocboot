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

    def test_openeuler_riscv64_keeps_the_vendor_kernel(self):
        repository = Path(__file__).resolve().parents[1]
        kernel_tasks = (
            repository
            / "onecloud/roles/utils/kernel-check/tasks/openeuler-24-riscv64.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("Keep the openEuler vendor kernel on RISC-V", kernel_tasks)
        self.assertNotIn("reboot:", kernel_tasks)
        self.assertNotIn("dnf:", kernel_tasks)
        self.assertNotIn("yum:", kernel_tasks)

    def test_helm_job_image_is_only_configured_on_k3s_servers(self):
        repository = Path(__file__).resolve().parents[1]
        config_template = (
            repository
            / "onecloud/roles/k3s/config/templates/config.yaml.j2"
        ).read_text(encoding="utf-8")

        riscv_image_block = config_template.split(
            "{% if ansible_architecture == 'riscv64' %}", 1
        )[1].split("{% else %}", 1)[0]

        self.assertIn("pause-image: {{ k3s_pause_image }}", riscv_image_block)
        self.assertIn("{% if is_k3s_server %}", riscv_image_block)
        self.assertIn(
            "helm-job-image: {{ k3s_helm_job_image }}",
            riscv_image_block,
        )

    def test_worker_node_retries_an_inactive_k3s_agent(self):
        repository = Path(__file__).resolve().parents[1]
        worker_tasks = (
            repository
            / "onecloud/roles/worker-node/tasks/k3s.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("systemctl is-active --quiet k3s-agent", worker_tasks)
        self.assertNotIn(
            "test -f /etc/systemd/system/k3s-agent.service",
            worker_tasks,
        )

    def test_worker_skips_ceph_image_cache_on_riscv64(self):
        repository = Path(__file__).resolve().parents[1]
        worker_tasks = (
            repository
            / "onecloud/roles/worker-node/tasks/main.yml"
        ).read_text(encoding="utf-8")
        ceph_cache_task = worker_tasks.split(
            "- name: cache ceph docker image", 1
        )[1]

        self.assertIn("ansible_architecture != 'riscv64'", ceph_cache_task)

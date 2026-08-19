from pathlib import Path
import unittest


class TestRiscv64Release(unittest.TestCase):

    def test_release_entrypoints_pin_the_current_ocboot_image(self):
        repository = Path(__file__).resolve().parents[1]
        launcher = (repository / "ocboot.sh").read_text(encoding="utf-8")
        implementation = (repository / "docs/riscv64.md").read_text(
            encoding="utf-8")
        customer = (
            repository / "docs/customer-deployment-openeuler-riscv64.md"
        ).read_text(encoding="utf-8")

        version = "v4.0.3-riscv64.16"
        self.assertIn("DEFAULT_VERSION=" + version, launcher)
        self.assertIn("ghcr.io/yinjiayi/ocboot:" + version, implementation)
        self.assertIn("--branch " + version, customer)

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

    def test_riscv64_pins_the_separately_released_kubeserver_image(self):
        repository = Path(__file__).resolve().parents[1]
        os_vars = (
            repository
            / "onecloud/roles/utils/detect-os/vars/openeuler-riscv64.yml"
        ).read_text(encoding="utf-8")
        manifest = (
            repository
            / "onecloud/roles/primary-master-node/setup_cloud/templates/onecloud-manifests.yaml.j2"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "cloudpods_kubeserver_tag: v4.0.3-riscv64.5",
            os_vars,
        )
        riscv_block = manifest.split(
            "{% if ansible_architecture == 'riscv64' %}", 1
        )[1].split("{% endif %}", 1)[0]
        self.assertIn("kubeserver:", riscv_block)
        self.assertIn('tag: "{{ cloudpods_kubeserver_tag }}"', riscv_block)

    def test_add_node_has_customer_grade_postflight_checks(self):
        repository = Path(__file__).resolve().parents[1]
        playbook = (repository / "onecloud/add-node.yml").read_text(
            encoding="utf-8")
        tasks = (
            repository
            / "onecloud/roles/utils/add-node-postflight/tasks/main.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("utils/add-node-postflight", playbook)
        self.assertIn("condition=Ready node/", tasks)
        self.assertIn("onecloud.yunion.io/host", tasks)
        self.assertIn("ovs-vsctl br-exists br0", tasks)
        self.assertIn("qemu-system-riscv64", tasks)
        self.assertIn("host_status", tasks)
        self.assertIn("host-enable", tasks)

    def test_optional_services_are_checked_before_disabling(self):
        repository = Path(__file__).resolve().parents[1]
        prereq = (
            repository / "onecloud/roles/k3s/prereq/tasks/main.yml"
        ).read_text(encoding="utf-8")
        agent = (
            repository / "onecloud/roles/k3s/k3s_agent/tasks/main.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("'nm-cloud-setup.service' in", prereq)
        self.assertIn("'k3s.service' in", agent)

    def test_common_os_include_uses_a_dedicated_loop_variable(self):
        repository = Path(__file__).resolve().parents[1]
        common = (
            repository / "onecloud/roles/common/tasks/main.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("loop_var: ocboot_os_task_file", common)
        self.assertIn('include_tasks: "{{ ocboot_os_task_file }}"', common)

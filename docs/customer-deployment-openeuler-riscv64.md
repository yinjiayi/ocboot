# Cloudpods RISC-V 单机部署手册

适用于一台全新安装的 openEuler 24.03 LTS SP3 `riscv64` 服务器。该方案由
ocboot 自动安装自建 K3s 发行物，不安装原生 Kubernetes。

## 1. 部署前检查

服务器建议不少于 16 核、32 GiB 内存和 200 GiB 可用磁盘，并配置固定管理
IP、DNS 和时间同步。服务器需要访问 GitHub、GHCR 和 GitHub Pages 的 HTTPS
地址；管理网络需放通 TCP 22、80、443 和 6443。

以 `root` 执行：

```bash
set -euo pipefail
test "$(uname -m)" = riscv64
grep -q '24.03' /etc/openEuler-release
test -c /dev/kvm
test -c /dev/net/tun
! command -v kubeadm >/dev/null
dnf install -y git buildah curl
buildah --version
```

如果检查发现 `kubeadm`，请改用干净系统，不要与已有 Kubernetes 混装。默认
Pod 网段为 `10.40.0.0/16`，Service 网段为 `10.96.0.0/12`，两者不能与现场
网络重叠。

## 2. 准备配置

```bash
git clone --depth 1 --branch v4.0.3-riscv64.8 \
  https://github.com/yinjiayi/ocboot.git
cd ocboot
cp config-example-openeuler-riscv64.yml config.yml
vi config.yml
```

在 `config.yml` 中完成以下替换：

- 将全部 `192.0.2.10` 替换为服务器固定管理 IP；
- 设置 `db_password` 和 `onecloud_user_password`；
- 如默认 Pod/Service 网段冲突，修改对应两项；
- 保持 `target_architecture: riscv64`、`image_repository: ghcr.io/yinjiayi`
  以及交付版本号不变。

ocboot 通过 SSH 管理目标节点。目标节点可以使用 root 免密 SSH；如果现场只允许
密码登录，不要创建额外的持久私钥，安装时按下一节启用交互式密码提示。

## 3. 安装

```bash
./ocboot.sh install config.yml
```

仅配置了 SSH 密码时执行：

```bash
ANSIBLE_ASK_PASS=true ./ocboot.sh install config.yml
```

按提示输入目标节点 SSH 密码。该密码只进入本次 Ansible 进程，不写入
`config.yml`、inventory 或容器镜像。

如果机器当前使用 legacy cgroup，ocboot 会为 openEuler RISC-V 内核启用统一
cgroup v2 并自动重启一次。从独立管理机执行时，Ansible 会在目标机恢复 SSH 后
继续安装；如果在目标机本机执行 ocboot，本机重启会终止安装进程，请重新登录并
原样再次执行本节安装命令。ocboot 的安装任务可幂等重入。

ocboot 会从 GitHub Pages 镜像校验并下载 `yinjiayi/k3s` 的 `riscv64` 二进制
和离线镜像包，安装同一 Pages 仓库中的 QEMU 10.0.7-6、Open vSwitch、
executor 和 RISC-V 固件，然后从 `ghcr.io/yinjiayi` 部署 Cloudpods。

## 4. 验收

重新登录服务器后执行：

```bash
systemctl is-active k3s cloudpods-executor
/usr/local/bin/k3s --version
/usr/local/bin/k3s kubectl get nodes -o wide
/usr/local/bin/k3s kubectl -n onecloud get pods
source ~/.onecloud_rcadmin
climc host-list
curl -kI https://SERVER_IP/
```

验收标准：K3s 版本包含 `v1.28.5+k3s1-riscv64.4`；节点为 `Ready`；
`onecloud` 命名空间 Pod 均为 `Running` 或已完成；`host-list` 可看到本机；
浏览器可通过
`https://SERVER_IP/` 使用配置中的管理员账号登录。

# Cloudpods RISC-V 部署手册

适用于全新安装的 openEuler 24.03 LTS SP3 `riscv64` 服务器。ocboot
自动部署自建 K3s 发行物，不安装原生 Kubernetes。本手册包含首台控制节点安装和
后续计算节点加入。

## 1. 环境准备

每台服务器建议不少于 16 核、32 GiB 内存和 200 GiB 可用磁盘，并满足：

- 使用固定 IP 或 DHCP 保留地址，各节点 hostname 必须唯一；
- 存在 `/dev/kvm` 和 `/dev/net/tun`，且没有安装过其他 Kubernetes；
- 能访问 GitHub、GHCR 和 `yinjiayi.github.io`；
- 部署机的 root 公钥已加入所有节点的 `/root/.ssh/authorized_keys`；
- 计算节点物理网络允许一个端口出现多个 MAC 地址，虚拟机所在网段提供 DHCP。

节点间防火墙至少放通：

| 方向 | 协议/端口 | 用途 |
| --- | --- | --- |
| 部署机到所有节点 | TCP 22 | SSH |
| 所有节点到控制节点 | TCP 6443 | K3s API |
| 节点之间 | TCP 10250、UDP 8472 | Kubelet、Flannel VXLAN |
| 计算节点之间 | UDP 6081 | OVN Geneve |
| 计算节点到集群节点 | TCP 32241-32242 | OVN North/South DB |
| 管理网到控制节点 | TCP 80、443 | Web |
| 控制节点或管理端到计算节点 | TCP 8885 | Host API |

在每台服务器执行检查：

```bash
set -euo pipefail
test "$(uname -m)" = riscv64
grep -Fq '24.03 (LTS-SP3)' /etc/os-release
test -c /dev/kvm
test -c /dev/net/tun
! command -v kubeadm >/dev/null
hostnamectl hostname
ip -brief address
```

Pod 网段默认为 `10.40.0.0/16`，Service 网段默认为 `10.96.0.0/12`，不得与
现场网络重叠。

如尚未配置 root 免密 SSH，在部署机执行：

```bash
test -f ~/.ssh/id_ed25519 || ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519
ssh-copy-id root@目标节点IP
ssh root@目标节点IP hostnamectl hostname
```

## 2. 安装首台节点

在首台节点或独立部署机以 root 执行：

```bash
dnf install -y git buildah curl
git clone --depth 1 --branch v4.0.3-riscv64.16 \
  https://github.com/yinjiayi/ocboot.git
cd ocboot
cp config-example-openeuler-riscv64.yml config.yml
vi config.yml
```

将 `config.yml` 中全部 `192.0.2.10` 替换为首台节点固定 IP，设置
`db_password` 和 `onecloud_user_password`。保持 `target_architecture: riscv64`、
`image_repository: ghcr.io/yinjiayi` 和交付版本号不变，然后执行：

```bash
./ocboot.sh install config.yml
```

如果 ocboot 为系统启用 cgroup v2，目标机会自动重启。从目标机本机执行时，重新
登录后原样再次执行安装命令；任务支持幂等重入。

## 3. 加入 RISC-V 计算节点

先在新节点设置唯一 hostname，并确认其管理 IP、物理网卡和磁盘目录：

```bash
hostnamectl set-hostname compute-rv-02
mkdir -p /opt/cloud/workspace/disks
ip -brief address
```

从已有 ocboot 目录执行，替换三个变量：

```bash
PRIMARY_IP=192.0.2.10
NODE_IP=192.0.2.11
NODE_NIC=eth0

./ocboot.sh add-node \
  --runtime qemu \
  --host-network "$NODE_NIC" \
  --disk-path /opt/cloud/workspace/disks \
  --enable-host-after-ready \
  "$PRIMARY_IP" "$NODE_IP"
```

ocboot 会等待节点、Host DaemonSet、OVS、QEMU/KVM 和 Cloudpods Host 全部
就绪，再显式启用 Host。镜像下载较慢时此阶段可能持续几十分钟，请勿中断。

执行过程中，管理 IP 会从物理网卡迁移到 OVS `br0`，SSH 可能短暂重连；这是
宿主机直连物理网络并让虚拟机使用同网段 DHCP 的正常行为。若不希望自动启用
Host，删除 `--enable-host-after-ready`，验收后手工执行：

```bash
source ~/.onecloud_rcadmin
climc host-enable compute-rv-02
```

只有在已经部署本地镜像仓库的离线集群中，才使用
`--offline-data-path /ABSOLUTE/RPM_REPO`。该目录必须已存在于新节点并包含
`repodata/repomd.xml`；集群私有仓库必须已经包含对应 Cloudpods 镜像。

## 4. 验收

在控制节点执行：

```bash
systemctl is-active k3s cloudpods-executor
k3s --version
k3s kubectl get nodes -o wide
k3s kubectl -n onecloud get daemonsets
source ~/.onecloud_rcadmin
climc host-list
curl -kI https://127.0.0.1/
```

在新增计算节点执行：

```bash
systemctl is-active k3s-agent cloudpods-executor
ovs-vsctl br-exists br0
/usr/local/qemu-10.0.7/bin/qemu-system-riscv64 --version
```

验收标准：K3s 版本包含 `v1.28.5+k3s1-riscv64.4`；所有节点均为 `Ready`；
`onecloud` DaemonSet 的期望数与就绪数一致；新增 Host 为 `running/online/enabled`；
浏览器可通过 `https://控制节点IP/` 使用 `config.yml` 中配置的管理员密码登录。

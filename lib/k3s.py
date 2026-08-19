import os
import hashlib
import platform
import shlex

from lib import consts
from lib.cmd import run_cmd
from lib.ssh import StderrException

def GET_AIRGAP_DIR():
    default_dir = os.path.join(os.getcwd(), "airgap_assets")
    if os.environ.get('K3S_AIRGAP_DIR', None):
        return os.environ.get('K3S_AIRGAP_DIR')
    return default_dir


VERSION_V1_28_5_K3S_1 = "v1.28.5+k3s1"
VERSION_V1_28_5_K3S_1_RISCV64_4 = "v1.28.5+k3s1-riscv64.4"

UPSTREAM_RELEASE_URL = (
    "https://github.com/k3s-io/k3s/releases/download/"
    "v1.28.5%2Bk3s1"
)
RISCV64_RELEASE_URL = (
    "https://yinjiayi.github.io/cloudpods-riscv64-releases/k3s/"
    "v1.28.5-k3s1-riscv64.4"
)

'''
from:

- https://github.com/k3s-io/k3s/releases/download/v1.29.0%2Bk3s1/sha256sum-amd64.txt
- https://github.com/k3s-io/k3s/releases/download/v1.29.0%2Bk3s1/sha256sum-arm64.txt
'''
SHA256_CHECK_SUM = {
    VERSION_V1_28_5_K3S_1: {
        'k3s': '38fadb2baf75cb516d59f7f4a40c1950fdc0dce5ebe7251aae235527b7de4083',
        'k3s-airgap-images-amd64.tar.zst': 'e259a812e77219f8436938d7ee871945549956defe12bd210ca206597198cd67',
        'k3s-arm64': 'ce46081904d461175f152493814d2f2ac1d5e40992d6b2b2b819eb6532c413f9',
        'k3s-airgap-images-arm64.tar.zst': '896a80cdfa8131efba625775c60c79a5525ef22b6d5a6c87560afed50b8a630b'
    }
}


ARCH_ALIASES = {
    'amd64': 'amd64',
    'x86_64': 'amd64',
    'arm64': 'arm64',
    'aarch64': 'arm64',
    'riscv64': 'riscv64',
}

ARCH_ASSETS = {
    'amd64': ('k3s', 'k3s-airgap-images-amd64.tar.zst'),
    'arm64': ('k3s-arm64', 'k3s-airgap-images-arm64.tar.zst'),
    'riscv64': ('k3s-riscv64', 'k3s-airgap-images-riscv64.tar.zst'),
}


def cal_file_sha256(filename):
    sha256_hash = hashlib.sha256()
    with open(filename,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def normalize_architecture(architecture):
    normalized = ARCH_ALIASES.get(architecture)
    if normalized is None:
        raise ValueError("unsupported K3s architecture: %s" % architecture)
    return normalized


def parse_checksum_manifest(content):
    checksums = {}
    for line in content.splitlines():
        fields = line.split()
        if len(fields) != 2 or len(fields[0]) != 64:
            continue
        checksums[fields[1].lstrip('*')] = fields[0].lower()
    return checksums


def _download_file(asset_url, target_path):
    temporary_path = "%s.part" % target_path
    run_cmd(
        'curl --fail --location --retry 5 --retry-all-errors '
        '--retry-delay 5 --connect-timeout 20 --max-time 1800 '
        '--speed-limit 1024 --speed-time 60 '
        '--output %s %s' % (
            shlex.quote(temporary_path),
            shlex.quote(asset_url)),
        no_strip=True,
        realtime_output=True)
    os.replace(temporary_path, target_path)


def download_asset(dest_dir, asset_url, expect_checksum, target_name=None):
    asset_name = target_name or os.path.basename(asset_url)
    target_path = os.path.join(dest_dir, asset_name)
    if os.path.exists(target_path):
        exists_checksum = cal_file_sha256(target_path)
        if exists_checksum == expect_checksum:
            print(f"{target_path} already exists, skip download.")
            return
        else:
            print(f"{target_path}'s sha256 checksum {exists_checksum} != {expect_checksum}, redownload it.")
    _download_file(asset_url, target_path)
    downloaded_checksum = cal_file_sha256(target_path)
    if downloaded_checksum != expect_checksum:
        os.unlink(target_path)
        raise ValueError(
            "%s's sha256 checksum %s != %s" % (
                asset_name, downloaded_checksum, expect_checksum))


def _riscv64_checksums(dest_dir, release_url):
    manifest_name = 'sha256sum-riscv64.txt'
    manifest_path = os.path.join(dest_dir, manifest_name)
    _download_file('%s/%s' % (release_url, manifest_name), manifest_path)
    with open(manifest_path) as manifest:
        checksums = parse_checksum_manifest(manifest.read())
    required = set(ARCH_ASSETS['riscv64']) | {'install.sh'}
    missing = required.difference(checksums)
    if missing:
        raise ValueError(
            "RISC-V K3s checksum manifest misses: %s" %
            ', '.join(sorted(missing)))
    return checksums


NO_SUCH_FILE_OR_DIR_ERR = [
    'No such file or directory',
    '没有那个文件或目录',
]


def is_using_k3s(ssh_client=None, use_sudo=False):
    if ssh_client is None:
        if os.environ.get(consts.ENV_K8S_V115) == consts.ENV_VAL_TRUE:
            return False
        return True
    else:
        try:
            kubelet_config = '/etc/kubernetes/kubelet.conf'
            ret = ssh_client.exec_command(f'ls -alh {kubelet_config}', use_sudo)
            if kubelet_config in ret:
                return False
            return True
        except StderrException as e:
            for err in NO_SUCH_FILE_OR_DIR_ERR:
                if err in str(e):
                    return True
            raise e
        except Exception as e:
            raise e


def init_airgap_assets(dest_dir, k3s_version=VERSION_V1_28_5_K3S_1,
                       architectures=None):
    # usage: K3S_URL_PREFIX=http://LOCAL_k3s_host_url
    # in order to speed up testing.
    if not is_using_k3s():
        return

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    if architectures is None:
        configured = os.environ.get('K3S_ASSET_ARCHITECTURES', '')
        architectures = configured.split(',') if configured else [platform.machine()]
    architectures = {
        normalize_architecture(architecture.strip())
        for architecture in architectures if architecture.strip()
    }

    upstream_url = os.environ.get('K3S_URL_PREFIX', UPSTREAM_RELEASE_URL)
    riscv64_url = os.environ.get(
        'K3S_RISCV64_URL_PREFIX', RISCV64_RELEASE_URL)

    for architecture in sorted(architectures.difference({'riscv64'})):
        for asset_name in ARCH_ASSETS[architecture]:
            download_asset(
                dest_dir,
                '%s/%s' % (upstream_url, asset_name),
                SHA256_CHECK_SUM[k3s_version][asset_name])

    if 'riscv64' in architectures:
        checksums = _riscv64_checksums(dest_dir, riscv64_url)
        for asset_name in ARCH_ASSETS['riscv64']:
            download_asset(
                dest_dir,
                '%s/%s' % (riscv64_url, asset_name),
                checksums[asset_name])
        download_asset(
            dest_dir,
            '%s/install.sh' % riscv64_url,
            checksums['install.sh'],
            target_name='k3s-install.sh')

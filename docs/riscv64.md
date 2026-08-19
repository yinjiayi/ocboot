# openEuler riscv64 support

This branch installs Cloudpods on openEuler 24.03 LTS SP3 with the self-built
`yinjiayi/k3s` RISC-V distribution. Native Kubernetes is not installed.

The RISC-V path is selected with `target_architecture: riscv64`. It uses:

- checksum-verified K3s release assets mirrored through
  `yinjiayi.github.io/cloudpods-riscv64-releases`
- runtime images from `ghcr.io/yinjiayi`
- RPMs from the `yinjiayi/cloudpods-riscv64-releases` GitHub Pages repository
- Flannel VXLAN for the K3s pod network
- QEMU 10.0.7, Open vSwitch, Cloudpods executor/climc, and RISC-V UEFI firmware

Copy `config-example-openeuler-riscv64.yml`, replace the example IP and both
passwords, then run:

```bash
./ocboot.sh install config-openeuler-riscv64.yml
```

The RISC-V ocboot container is `ghcr.io/yinjiayi/ocboot:v4.0.3-riscv64.13`.
It is published by the pinned-source workflow in
`yinjiayi/cloudpods-riscv64-releases`; this repository's tag workflow performs
the native build and runtime checks without requiring cross-repository package
write access.

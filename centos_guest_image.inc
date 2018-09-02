# List of packages to be included/installed in guest image
# If these have dependencies, they will be pulled in automatically
#

# build-info
build-info

# kernel
perf

#
# Network Drivers
#

# i40evf-kmod
kmod-i40evf

# i40e-kmod
kmod-i40e

# ixgbevf-kmod
kmod-ixgbevf

# ixgbe-kmod
kmod-ixgbe

# qat17
qat17

#
# TPM2 libs to enable vTPM on Guest
#

# tpm-kmod
kmod-tpm

# tss2
tss2

# tpm2-tools
tpm2-tools

#
# ima support
#

# rpm
rpm-plugin-systemd-inhibit

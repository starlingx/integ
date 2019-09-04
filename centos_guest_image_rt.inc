# List of packages to be included/installed in RT guest image
# If these have dependencies, they will be pulled in automatically
#


#
# Network Drivers
#

# i40evf-kmod
kmod-i40evf-rt

# i40e-kmod
kmod-i40e-rt

# ixgbevf-kmod
kmod-ixgbevf-rt

# ixgbe-kmod
kmod-ixgbe-rt

# qat17
qat17-rt

#
# TPM2 libs to enable vTPM on Guest
#

# tpm-kmod
kmod-tpm-rt

# tss2
tss2

# tpm2-tools
tpm2-tools

#
# ima support
#

# rpm
rpm-plugin-systemd-inhibit

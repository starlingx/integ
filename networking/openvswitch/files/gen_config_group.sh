#!/bin/bash

source configlib.sh

# Generates arch configurations in the current directory based on
# 1. an openvswitch.spec file
# 2. an expanded dpdk tree

if (( $# != 2 )); then
    echo "$0: openvswitch.spec dpdk_tree" >&2
    exit 1
fi

OVSSPEC="$1"
DPDKDIR="$2"

# accumulate all arch + name triples
OVS_DPDK_CONF_MACH_ARCH=()
for arch in $(grep %define\ dpdk_mach_arch "$OVSSPEC" | sed 's@%define dpdk_mach_arch @@'); do
    OVS_DPDK_CONF_MACH_ARCH+=($arch)
done

OVS_DPDK_CONF_MACH_TMPL=()
for tmpl in $(grep %define\ dpdk_mach_tmpl "$OVSSPEC" | sed 's@%define dpdk_mach_tmpl @@'); do
    OVS_DPDK_CONF_MACH_TMPL+=($tmpl)
done

OVS_DPDK_CONF_MACH=()
for mach in $(grep %define\ dpdk_mach\  "$OVSSPEC" | sed 's@%define dpdk_mach @@'); do
    OVS_DPDK_CONF_MACH+=($mach)
done

OVS_DPDK_TARGETS=()
for ((i=0; i < ${#OVS_DPDK_CONF_MACH[@]}; i++)); do
    OVS_DPDK_TARGETS+=("${OVS_DPDK_CONF_MACH_ARCH[$i]}-${OVS_DPDK_CONF_MACH_TMPL[$i]}-linuxapp-gcc")
    echo "DPDK-target: ${OVS_DPDK_TARGETS[$i]}"
done

OUTPUT_DIR=$(pwd)
pushd "$DPDKDIR"
for ((i=0; i < ${#OVS_DPDK_TARGETS[@]}; i++)); do
    echo "For ${OVS_DPDK_TARGETS[$i]}:"

    echo "     a. Generating initial config"
    echo "        make V=1 T=${OVS_DPDK_TARGETS[$i]} O=${OVS_DPDK_TARGETS[$i]}"
    make V=1 T=${OVS_DPDK_TARGETS[$i]} O=${OVS_DPDK_TARGETS[$i]} -j8 config
    ORIG_SHA=""
    OUTDIR="${OVS_DPDK_TARGETS[$i]}"

    echo "     b. calculating and applying sha"
    calc_sha ORIG_SHA "${OUTDIR}/.config"
    if [ "$ORIG_SHA" == "" ]; then
        echo "ERROR: Unable to get sha for arch ${OVS_DPDK_TARGETS[$i]}"
        exit 1
    fi
    echo "# -*- cfg-sha: ${ORIG_SHA}" > ${OUTDIR}/.config.new
    cat "${OUTDIR}/.config" >> "${OUTDIR}/.config.new"
    cp "${OUTDIR}/.config" "${OUTDIR}/.config.orig"
    mv -f "${OUTDIR}/.config.new" "${OUTDIR}/.config"

    echo "     c. setting initial configurations"
    # these are the original setconf values from openvswitch.spec
    set_conf "${OUTDIR}" CONFIG_RTE_MACHINE "\\\"${OVS_DPDK_CONF_MACH[$i]}\\\""

    # Disable DPDK libraries not needed by OVS
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_TIMER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_CFGFILE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_JOBSTATS n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_LPM n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_ACL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_POWER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_DISTRIBUTOR n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_REORDER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PORT n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_TABLE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PIPELINE n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_KNI n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_CRYPTODEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_SECURITY n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_FLOW_CLASSIFY n

    # Disable virtio user as not used by OVS
    set_conf "${OUTDIR}" CONFIG_RTE_VIRTIO_USER n

    # Enable DPDK libraries needed by OVS
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VHOST_NUMA y

    # start by disabling ALL PMDs
    for pmd in $(grep _PMD= "${OUTDIR}/.config" | sed 's@=\(y\|n\)@@g'); do
        set_conf "${OUTDIR}" $pmd n
    done

    # PMDs which have their own naming scheme
    # the default for this was 'n' at one point.  Make sure we keep it
    # as such
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_QAT n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_OCTEONTX_SSOVF n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_VHOST n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_KNI n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_XENVIRT n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_NULL_CRYPTO n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_NULL n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_TAP n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_CRYPTO_SCHEDULER n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_SKELETON_EVENTDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_SW_EVENTDEV n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_PCAP n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_BOND n
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_AF_PACKET n

    # whitelist of enabled PMDs
    # Soft PMDs to enable
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_PMD_RING y
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_VIRTIO_PMD y

    # HW PMDs
    set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_I40E_PMD y
    case "${OVS_DPDK_CONF_MACH_ARCH[i]}" in
    x86_64)
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_ENIC_PMD y
        ;&
    arm64)
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_IXGBE_PMD y
        set_conf "${OUTDIR}" CONFIG_RTE_LIBRTE_IGB_PMD y
        ;;
    esac

    # Disable kernel modules
    set_conf "${OUTDIR}" CONFIG_RTE_EAL_IGB_UIO n
    set_conf "${OUTDIR}" CONFIG_RTE_KNI_KMOD n

    # Disable experimental stuff
    set_conf "${OUTDIR}" CONFIG_RTE_NEXT_ABI n

    cp "${OUTDIR}/.config" "${OUTPUT_DIR}/${OVS_DPDK_TARGETS[$i]}-config"
done
popd >/dev/null

echo -n "For each arch ( "
for ((i=0; i < ${#OVS_DPDK_CONF_MACH_ARCH[@]}; i++)); do
    echo -n "${OVS_DPDK_CONF_MACH_ARCH[i]} "
done
echo "):"
echo "1. ensure you enable the requisite hw"

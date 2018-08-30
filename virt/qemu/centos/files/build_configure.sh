#!/bin/sh

_prefix=$1
shift
_libdir=$1
shift
_sysconfdir=$1
shift
_localstatedir=$1
shift
_libexecdir=$1
shift
pkgname=$1
shift
arch=$1
shift
nvr=$1
shift
optflags=$1
shift
have_fdt=$1
shift
have_gluster=$1
shift
have_guest_agent=$1
shift
have_numa=$1
shift
have_rbd=$1
shift
have_rdma=$1
shift
have_seccomp=$1
shift
have_spice=$1
shift
have_usbredir=$1
shift
have_tcmalloc=$1
shift


if [ "$have_rbd" == "enable" ]; then
    rbd_driver=rbd,
fi

if [ "$have_gluster" == "enable" ]; then
    gluster_driver=gluster,
fi

./configure \
    --prefix=${_prefix} \
    --libdir=${_libdir} \
    --sysconfdir=${_sysconfdir} \
    --interp-prefix=${_prefix}/qemu-%M \
    --localstatedir=${_localstatedir} \
    --libexecdir=${_libexecdir} \
    --extra-ldflags="$extraldflags -pie -Wl,-z,relro -Wl,-z,now" \
    --extra-cflags="${optflags} -fPIE -DPIE -O2" \
    --with-pkgversion=${nvr} \
    --with-confsuffix=/${pkgname} \
    --with-coroutine=ucontext \
    --with-system-pixman \
    --disable-bluez \
    --disable-brlapi \
    --enable-cap-ng \
    --enable-coroutine-pool \
    --disable-curl \
    --enable-curses \
    --disable-debug-tcg \
    --enable-docs \
    --disable-gtk \
    --enable-kvm \
    --disable-libiscsi \
    --disable-libnfs \
    --disable-libssh2 \
    --disable-libusb \
    --disable-bzip2 \
    --enable-linux-aio \
    --enable-live-block-migration \
    --disable-lzo \
    --disable-opengl \
    --enable-pie \
    --disable-qom-cast-debug \
    --disable-sdl \
    --enable-snappy \
    --disable-sparse \
    --disable-strip \
    --enable-tpm \
    --enable-trace-backend=nop \
    --disable-uuid \
    --disable-vde \
    --disable-vhdx \
    --disable-vhost-scsi \
    --enable-vhost-net \
    --enable-virtfs \
    --disable-vnc-jpeg \
    --disable-vnc-png \
    --disable-vnc-sasl \
    --disable-vte \
    --enable-werror \
    --disable-xen \
    --disable-xfsctl \
    --enable-attr \
    --${have_fdt}-fdt \
    --${have_gluster}-glusterfs \
    --${have_guest_agent}-guest-agent \
    --${have_numa}-numa \
    --${have_rbd}-rbd \
    --${have_rdma}-rdma \
    --${have_seccomp}-seccomp \
    --${have_spice}-spice \
    --${have_usbredir}-usb-redir \
    --${have_tcmalloc}-tcmalloc \
    --audio-drv-list=pa,alsa \
    --block-drv-rw-whitelist=qcow2,raw,file,host_device,nbd,iscsi,${gluster_driver}${rbd_driver}blkdebug \
    --block-drv-ro-whitelist=vmdk,vhdx,vpc,https,ssh \
    "$@"

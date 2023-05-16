The containerd.service file and config.toml were pulled in
from the upstream Debian package
containerd_1.6.20~ds1-1+b1_amd64.deb downloaded from
http://ftp.ca.debian.org/debian/pool/main/c/containerd/

The config.toml file is identical to what we were using previously
with the older version of containerd, and is unchanged in the
newer version of the package.  It will get overwritten by
ansible/puppet anyways during system bringup.

The containerd.service file is identical to the version from
the containerd github source tag "v1.6.21" except that the
containerd binary is in /usr/bin/ instead of /usr/local/bin.
The only difference from what we had before is that LimitNOFILE
is now set to "infinity" to align with both Debian and containerd
upstream.

The binaries that get pulled in at build time are from the
containerd upstream binary release
containerd-1.6.21-linux-amd64.tar.gz downloaded from
https://github.com/containerd/containerd/releases/tag/v1.6.21

The rationale for using the upstream binaries rather than the
Debian "bookworm" package is that the Debian package requires
a lot of other dependencies including newer glibc and python3,
which would be too intrusive for our purposes.

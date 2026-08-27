# Build multus-cni thick plugin from source
# Base: v4.3.0 + PR#1521 (IP leak fix for conflist delegates)
# Commit 1688144 = v4.3.0 + 2 commits (the complete IP leak fix)
# Note: This can be removed once commits 6597fa6 and 1688144 are in an
# official multus release.
FROM golang:1.26 AS build

WORKDIR /usr/src/multus-cni
RUN git clone https://github.com/k8snetworkplumbingwg/multus-cni.git . && \
    git checkout 16881445687c9a445cb97ff6450f0719393fd10b

RUN ./hack/build-go.sh

FROM debian:stable-slim
LABEL org.opencontainers.image.source=https://github.com/k8snetworkplumbingwg/multus-cni
COPY --from=build /usr/src/multus-cni/bin /usr/src/multus-cni/bin
COPY --from=build /usr/src/multus-cni/LICENSE /usr/src/multus-cni/LICENSE
COPY --from=build /usr/src/multus-cni/bin/cert-approver /
WORKDIR /
ENTRYPOINT ["/usr/src/multus-cni/bin/multus-daemon"]
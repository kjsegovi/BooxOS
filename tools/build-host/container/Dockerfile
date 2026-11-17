FROM docker.io/library/ubuntu@sha256:8a2321a92b438238f93b4346fff61bc4259c99fdd4d9b52ee86f153fee0c344f

LABEL org.opencontainers.image.title="BOOX Android build environment"
LABEL project="BooxOS"
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Build dependencies live only in this image. Android's branch-specific JDK,
# Go, Rust and Clang must come from its pinned source manifest.
RUN apt-get update && apt-get install -y --no-install-recommends \
    bc bison build-essential ca-certificates ccache curl file flex \
    g++-multilib gcc-multilib git git-lfs gnupg gperf \
    lib32ncurses-dev lib32readline-dev lib32z1-dev libelf-dev liblz4-tool \
    libncurses5 libncurses5-dev libsdl1.2-dev libssl-dev libxml2 \
    libxml2-utils lzop patchelf python3 rsync schedtool squashfs-tools \
    unzip xsltproc zip zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash builder && \
    mkdir -p /work && chown builder:builder /work

USER builder
WORKDIR /work
CMD ["/bin/bash"]

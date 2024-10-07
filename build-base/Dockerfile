FROM debian:bookworm
ENV DEBIAN_FRONTEND noninteractive

# APT Update, Upgrade, and Install packages
RUN apt-get --allow-releaseinfo-change update && \
    apt-get upgrade -y && \
    apt-get install -y \
    build-dep \
    build-essential \
    ca-certificates \
    clang-format \
    cmake \
    cppcheck \
    curl \
    dirmngr \
    doxygen \
    gdb \
    git \
    gnupg \
    graphviz \
    libboost-all-dev \
    libssl-dev \
    locales \
    netbase \
    ninja-build \
    openssh-client \
    pkg-config \
    python3-pip \
    rpm \
    sshpass \
    unzip \
    valgrind \
    wget \
    zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install cpplint via pip
RUN pip3 install --no-cache-dir cpplint --break-system-packages

# Set the locale to en_US.UTF-8
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Install vcpkg and packages
ENV VCPKG_FORCE_SYSTEM_BINARIES 1
ENV VCPKG_ROOT /vcpkg
ENV PATH $VCPKG_ROOT:$PATH
RUN git clone https://github.com/microsoft/vcpkg.git && \
    ./vcpkg/bootstrap-vcpkg.sh && \
    vcpkg install protobuf asio-grpc libunifex catch2 spdlog hiredis redis-plus-plus

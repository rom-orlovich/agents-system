FROM rust:1.75-alpine AS gkg-builder

RUN apk add --no-cache musl-dev curl bash git cmake make g++ pkgconf openssl-dev

WORKDIR /build

RUN curl -fsSL https://gitlab.com/gitlab-org/rust/knowledge-graph/-/raw/main/install.sh -o install.sh && \
    chmod +x install.sh && \
    HOME=/build bash install.sh

FROM rust:1.75-alpine AS app-builder

RUN apk add --no-cache musl-dev cmake make g++ pkgconf

WORKDIR /app

COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release 2>/dev/null || true
RUN rm -rf src

COPY . .
RUN cargo build --release

FROM alpine:3.19

RUN apk add --no-cache ca-certificates bash git curl python3 py3-pip

WORKDIR /app

COPY --from=gkg-builder /build/.local/bin/gkg /usr/local/bin/gkg
COPY --from=app-builder /app/target/release/knowledge-graph /app/knowledge-graph

COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

ENV PORT=4000
ENV GKG_DATA_DIR=/data/graphs
ENV REPOS_DIR=/data/repos
ENV PATH="/usr/local/bin:${PATH}"

RUN mkdir -p /data/graphs /data/repos

VOLUME ["/data"]

EXPOSE 4000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]


# ==========================================

# Stage 1: 自己用 ubuntu + 官方 Node 二進位檔組 builder

# ==========================================

FROM ubuntu:22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive

ARG NODE_VERSION=20.20.2

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl xz-utils ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 下載官方預編譯 Node（約 25MB），裝到 /usr/local，含 npm

# --retry 8：斷了自動重試最多 8 次

RUN curl -fSL --retry 8 --retry-delay 5 --retry-all-errors \
      -o /tmp/node.tar.xz \
      https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz && \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
    rm /tmp/node.tar.xz && \
    node -v && npm -v
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmjs.org/ && \
    npm config set maxsockets 3 && \
    npm config set fetch-timeout 600000 && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# ==========================================

# Stage 2: 最終 Nginx 執行環境

# ==========================================

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/dist /opt/IEI_claude_using_analysis/frontend/dist

COPY nginx/iei_claude /etc/nginx/sites-available/iei_claude

RUN ln -sf /etc/nginx/sites-available/iei_claude /etc/nginx/sites-enabled/iei_claude && \
    rm -f /etc/nginx/sites-enabled/default

CMD ["nginx", "-g", "daemon off;"]


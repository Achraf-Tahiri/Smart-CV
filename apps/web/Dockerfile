# --- Étape build ---
FROM node:24-slim AS builder
WORKDIR /app

# pnpm (gestionnaire de paquets Node)
RUN npm install -g pnpm@9

# Dépendances d'abord (couche mise en cache tant que package.json ne change pas)
COPY package.json ./
RUN pnpm install

# URL de l'API injectée au BUILD (variables NEXT_PUBLIC_* figées dans le bundle client)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Code + build de production
COPY . .
RUN pnpm build

# --- Étape runtime (image minimale via la sortie "standalone" de Next) ---
FROM node:24-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]

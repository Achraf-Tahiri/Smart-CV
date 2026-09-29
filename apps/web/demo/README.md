# Synthetic portfolio preview

Every profile in `candidates.json` was invented for this demonstration. Names,
organizations, education, career histories, and counts do not represent real
candidates or customers. Contact addresses use `example.com`; phone numbers and
original CV documents are deliberately absent.

From `apps/web`, run `pnpm preview:demo`, then open http://127.0.0.1:3105.
Sign in with `demo@example.com` / `demo-only`.

The preview runs the actual Next.js interface against a separate, read-only
fixture server bound to loopback. It does not connect to PostgreSQL, Redis,
MinIO, Google Drive, or language-model providers. Its synthetic tokens cannot
log in to the real FastAPI application. The frontend build output is kept in
`.preview-next`, separate from normal development and production output.

To regenerate the README screenshots while the preview is running:

```bash
pnpm exec playwright install chromium
pnpm screenshots
```

The capture script checks the preview identity and rejects unexpected network
requests. Only these synthetic profiles may be used for repository screenshots.

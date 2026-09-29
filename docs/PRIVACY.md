# Demo data and repository hygiene

The portfolio preview contains eight invented profiles. Its names, organizations,
career histories, education, and metrics are fictional. Emails use `example.com`;
there are no telephone numbers, profile photos, or original CV documents.
Backend and frontend tests use synthetic fixtures. Test documents are generated
in memory during the tests, rather than committed as candidate files.

The preview is isolated from the application's database and integrations. See
[the preview documentation](../apps/web/demo/README.md) for its scope and screenshot
reproduction instructions.

## Adding examples safely

- Invent sample profiles from scratch. Do not copy or anonymize a real person's CV.
- Use reserved `example.com` addresses and fictional employers and schools.
- Capture screenshots only through the synthetic preview.
- Keep uploaded documents, exports, database backups, `.env` files, and service
  account credentials outside Git. Common formats and directories are ignored.
- Run `python3 scripts/check_public_repo.py` before publishing. The same guard
  runs in CI. It detects common sensitive file types and token patterns, but
  cannot determine whether arbitrary names or free text describe real people.

The application can process personal information when configured with a real
backend. Its audit, export, and retention features are technical controls;
using them does not by itself establish legal compliance. The local Docker
configuration is intended for development, not an Internet-facing deployment.

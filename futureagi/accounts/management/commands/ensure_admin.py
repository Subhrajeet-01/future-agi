import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Idempotently seed the first admin account from FAGI_ADMIN_* env vars "
        "(or --email/--name/--password). Safe to run on every boot: it does "
        "nothing if the account already exists or if no credentials are "
        "configured, and never raises in a way that would block startup. "
        "The container entrypoint calls this so a plain `docker compose up` "
        "yields a usable login without running the installer."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email", help="Admin email (default: $FAGI_ADMIN_EMAIL)"
        )
        parser.add_argument(
            "--name", help="Full name (default: $FAGI_ADMIN_NAME, else 'Admin')"
        )
        parser.add_argument(
            "--password", help="Password (default: $FAGI_ADMIN_PASSWORD)"
        )

    def handle(self, *args, **options):
        email = (
            options.get("email") or os.getenv("FAGI_ADMIN_EMAIL") or ""
        ).strip().lower()
        name = (options.get("name") or os.getenv("FAGI_ADMIN_NAME") or "").strip()
        password = options.get("password") or os.getenv("FAGI_ADMIN_PASSWORD") or ""

        # No credentials configured: this is the normal case when the operator
        # creates the account some other way. Quietly no-op so boot continues.
        if not email or not password:
            self.stdout.write(
                "ensure_admin: FAGI_ADMIN_EMAIL / FAGI_ADMIN_PASSWORD not set — "
                "skipping admin seed (create one later with "
                "`python manage.py create_user`)."
            )
            return

        if len(password) < 8:
            self.stderr.write(
                "ensure_admin: FAGI_ADMIN_PASSWORD must be at least 8 characters "
                "— skipping admin seed."
            )
            return

        if not name:
            name = "Admin"

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(
                f"ensure_admin: account '{email}' already exists — nothing to do."
            )
            return

        # Import here so a missing/half-built app never breaks `manage.py` itself.
        from accounts.utils import first_signup

        try:
            user = first_signup(
                {
                    "email": email,
                    "full_name": name,
                    "password": password,
                    "allow_email": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 — seed must never block boot
            msg = str(exc)
            self.stderr.write(f"ensure_admin: could not create admin '{email}': {msg}")
            if "work email" in msg.lower():
                self.stderr.write(
                    "  Personal email domains are rejected unless "
                    "ALLOW_ANY_EMAIL=true (the default in the OSS compose). "
                    "Set ALLOW_ANY_EMAIL=true and restart the backend."
                )
            self.stderr.write(
                "  Create the account manually instead: "
                "`python manage.py create_user`."
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f"ensure_admin: created admin account '{user.email}'.")
        )

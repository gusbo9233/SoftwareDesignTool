import secrets
from datetime import datetime
from types import SimpleNamespace

from flask import current_app, has_request_context, session
from gotrue._sync.storage import SyncSupportedStorage
from supabase import create_client
from supabase.client import ClientOptions
from werkzeug.security import check_password_hash, generate_password_hash

import app as _app


def _parse_dt(s):
    if not s or not isinstance(s, str):
        return s
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s


def _user(d):
    d = dict(d)
    for field in ("created_at", "updated_at"):
        if field in d:
            d[field] = _parse_dt(d[field])
    d.setdefault("name", "")
    return SimpleNamespace(**d)


class AuthenticationError(RuntimeError):
    pass


def _is_empty_maybe_single_error(exc):
    return getattr(exc, "code", None) == "204" and getattr(exc, "message", "") == "Missing response"


def _is_missing_users_table_error(exc):
    return getattr(exc, "code", None) == "PGRST205" and "public.users" in getattr(exc, "message", "")


def _maybe_single(builder):
    try:
        res = builder.execute()
    except Exception as exc:
        if _is_empty_maybe_single_error(exc):
            return None
        raise
    if res is None:
        return None
    return res.data


def _looks_like_legacy_jwt_key(value):
    return bool(value and value.count(".") == 2)


class _SessionStorage(SyncSupportedStorage):
    def get_item(self, key: str):
        return session.get(key)

    def set_item(self, key: str, value: str) -> None:
        session[key] = value

    def remove_item(self, key: str) -> None:
        session.pop(key, None)


class AuthService:
    @staticmethod
    def _auth_client():
        auth_key = current_app.config.get("SUPABASE_ANON_KEY")
        # supabase-py 2.15.x validates keys as JWTs and rejects the newer
        # `sb_publishable_...` format. When only a publishable key is available,
        # fall back to the service key for the server-side OAuth handshake.
        if not _looks_like_legacy_jwt_key(auth_key):
            auth_key = current_app.config.get("SUPABASE_SERVICE_KEY")

        if not auth_key:
            raise AuthenticationError(
                "Supabase auth keys are not configured. Set SUPABASE_ANON_KEY "
                "or SUPABASE_PUBLISHABLE_KEY, and keep SUPABASE_SERVICE_KEY available "
                "for older supabase-py compatibility."
            )
        return create_client(
            current_app.config["SUPABASE_URL"],
            auth_key,
            options=ClientOptions(
                flow_type="pkce",
                storage=_SessionStorage(),
                auto_refresh_token=False,
                persist_session=True,
            ),
        )

    @staticmethod
    def _oauth_password_hash():
        return generate_password_hash(secrets.token_urlsafe(32))

    @staticmethod
    def get(user_id):
        try:
            data = _maybe_single(_app.supabase.table("users").select("*").eq("id", user_id).maybe_single())
        except Exception as exc:
            if _is_missing_users_table_error(exc):
                raise AuthenticationError(
                    "Authentication storage is not ready yet. Apply the users/project ownership migration first."
                ) from exc
            raise
        return _user(data) if data else None

    @staticmethod
    def get_by_email(email):
        try:
            data = _maybe_single(
                _app.supabase.table("users")
                .select("*")
                .eq("email", email.strip().lower())
                .maybe_single()
            )
        except Exception as exc:
            if _is_missing_users_table_error(exc):
                raise AuthenticationError(
                    "Authentication storage is not ready yet. Apply the users/project ownership migration first."
                ) from exc
            raise
        return _user(data) if data else None

    @staticmethod
    def create_user(email, password, name=""):
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise AuthenticationError("Email is required.")
        if len(password or "") < 8:
            raise AuthenticationError("Password must be at least 8 characters.")
        if AuthService.get_by_email(normalized_email):
            raise AuthenticationError("An account with that email already exists.")

        try:
            res = _app.supabase.table("users").insert({
                "email": normalized_email,
                "password_hash": generate_password_hash(password),
                "name": name.strip(),
            }).execute()
        except Exception as exc:
            if _is_missing_users_table_error(exc):
                raise AuthenticationError(
                    "Authentication storage is not ready yet. Apply the users/project ownership migration first."
                ) from exc
            raise
        return _user(res.data[0])

    @staticmethod
    def get_or_create_oauth_user(auth_user):
        email = (getattr(auth_user, "email", None) or "").strip().lower()
        if not email:
            raise AuthenticationError("Google account did not provide an email address.")

        existing = AuthService.get_by_email(email)
        if existing:
            updates = {}
            if existing.id != auth_user.id:
                updates["id"] = auth_user.id
            display_name = (
                (getattr(auth_user, "user_metadata", {}) or {}).get("full_name")
                or (getattr(auth_user, "user_metadata", {}) or {}).get("name")
                or existing.name
            )
            if display_name and display_name != existing.name:
                updates["name"] = display_name
            if updates:
                try:
                    res = _app.supabase.table("users").update(updates).eq("email", email).execute()
                except Exception as exc:
                    if _is_missing_users_table_error(exc):
                        raise AuthenticationError(
                            "Authentication storage is not ready yet. Apply the users/project ownership migration first."
                        ) from exc
                    raise
                if res.data:
                    return _user(res.data[0])
            return existing

        try:
            res = _app.supabase.table("users").insert({
                "id": auth_user.id,
                "email": email,
                "password_hash": AuthService._oauth_password_hash(),
                "name": (
                    (getattr(auth_user, "user_metadata", {}) or {}).get("full_name")
                    or (getattr(auth_user, "user_metadata", {}) or {}).get("name")
                    or ""
                ),
            }).execute()
        except Exception as exc:
            if _is_missing_users_table_error(exc):
                raise AuthenticationError(
                    "Authentication storage is not ready yet. Apply the users/project ownership migration first."
                ) from exc
            raise
        return _user(res.data[0])

    @staticmethod
    def authenticate(email, password):
        user = AuthService.get_by_email(email)
        if not user or not check_password_hash(user.password_hash, password):
            raise AuthenticationError("Invalid email or password.")
        return user

    @staticmethod
    def google_sign_in_url(redirect_to):
        client = AuthService._auth_client()
        response = client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_to},
        })
        return response.url

    @staticmethod
    def complete_google_sign_in(auth_code, redirect_to):
        client = AuthService._auth_client()
        response = client.auth.exchange_code_for_session({
            "auth_code": auth_code,
            "redirect_to": redirect_to,
        })
        if not response or not response.user:
            raise AuthenticationError("Google sign-in did not return a user.")
        user = AuthService.get_or_create_oauth_user(response.user)
        AuthService.login_user(user)
        return user

    @staticmethod
    def login_user(user):
        if not has_request_context():
            return
        session["user_id"] = user.id
        session["user_email"] = user.email
        session["user_name"] = getattr(user, "name", "") or ""

    @staticmethod
    def logout_user():
        if not has_request_context():
            return
        session.pop("user_id", None)
        session.pop("user_email", None)
        session.pop("user_name", None)

    @staticmethod
    def current_user():
        if not has_request_context():
            return None
        user_id = session.get("user_id")
        user_email = session.get("user_email")
        if not user_id or not user_email:
            return None
        return SimpleNamespace(
            id=user_id,
            email=user_email,
            name=session.get("user_name", ""),
        )

    @staticmethod
    def current_user_id():
        user = AuthService.current_user()
        return user.id if user else None

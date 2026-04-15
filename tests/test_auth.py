from app.services.auth_service import AuthService
from app.services.project_service import ProjectService


class TestAuthRoutes:
    def test_login_required_redirects_html_requests(self, anonymous_client):
        response = anonymous_client.get("/", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_login_required_returns_401_for_api_requests(self, anonymous_client, project):
        response = anonymous_client.get(f"/api/projects/{project.id}/export")

        assert response.status_code == 401
        assert response.get_json()["error"] == "Authentication required"

    def test_signup_creates_session(self, anonymous_client):
        response = anonymous_client.post(
            "/signup",
            data={
                "name": "Alice",
                "email": "alice@example.com",
                "password": "password123",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Account created." in response.data
        user = AuthService.get_by_email("alice@example.com")
        assert user is not None

    def test_login_accepts_valid_credentials(self, anonymous_client, user):
        response = anonymous_client.post(
            "/login",
            data={"email": user.email, "password": "password123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Signed in successfully." in response.data

    def test_login_page_shows_google_entry(self, anonymous_client):
        response = anonymous_client.get("/login")

        assert response.status_code == 200
        assert b"Continue with Google" in response.data

    def test_google_login_route_is_reachable_when_signed_out(self, anonymous_client, monkeypatch):
        monkeypatch.setattr(
            "app.routes.auth.AuthService.google_sign_in_url",
            lambda _redirect_to: "https://example.com/google-oauth",
        )

        response = anonymous_client.get("/auth/google?next=/", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"] == "https://example.com/google-oauth"

    def test_other_users_cannot_open_foreign_project(self, anonymous_client, user):
        owned_project = ProjectService.create(name="Private", user_id=user.id)
        other_user = AuthService.create_user("other@example.com", "password123", name="Other")

        with anonymous_client.session_transaction() as sess:
            sess["user_id"] = other_user.id
            sess["user_email"] = other_user.email
            sess["user_name"] = other_user.name

        response = anonymous_client.get(f"/projects/{owned_project.id}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Project not found." in response.data


class TestAuthService:
    def test_get_by_email_treats_postgrest_204_as_missing_user(self, monkeypatch):
        from postgrest.exceptions import APIError

        class FakeQuery:
            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def maybe_single(self):
                return self

            def execute(self):
                raise APIError({
                    "message": "Missing response",
                    "code": "204",
                    "hint": "Please check traceback of the code",
                    "details": "Postgrest couldn't retrieve response",
                })

        class FakeSupabase:
            def table(self, name):
                assert name == "users"
                return FakeQuery()

        monkeypatch.setattr("app.services.auth_service._app.supabase", FakeSupabase())

        assert AuthService.get_by_email("nobody@example.com") is None

    def test_get_by_email_handles_none_execute_result(self, monkeypatch):
        class FakeQuery:
            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def maybe_single(self):
                return self

            def execute(self):
                return None

        class FakeSupabase:
            def table(self, name):
                assert name == "users"
                return FakeQuery()

        monkeypatch.setattr("app.services.auth_service._app.supabase", FakeSupabase())

        assert AuthService.get_by_email("nobody@example.com") is None

    def test_google_sign_in_url_uses_supabase_oauth(self, app):
        with app.test_request_context():
            url = AuthService.google_sign_in_url("http://localhost/auth/callback")

        assert "provider=google" in url
        assert "redirect_to=http%3A%2F%2Flocalhost%2Fauth%2Fcallback" in url

    def test_google_sign_in_uses_service_key_when_publishable_key_is_new_format(self, app):
        app.config["SUPABASE_ANON_KEY"] = "sb_publishable_example"
        app.config["SUPABASE_SERVICE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.signature"

        with app.test_request_context():
            url = AuthService.google_sign_in_url("http://localhost/auth/callback")

        assert "provider=google" in url

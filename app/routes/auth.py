from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.services.auth_service import AuthService, AuthenticationError

auth_bp = Blueprint("auth", __name__)


def _redirect_target():
    next_url = request.args.get("next") or request.form.get("next")
    if next_url and next_url.startswith("/"):
        return next_url
    return url_for("projects.index")


def _google_callback_url():
    return url_for("auth.google_callback", _external=True)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if AuthService.current_user():
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            user = AuthService.authenticate(email, password)
            AuthService.login_user(user)
            flash("Signed in successfully.", "success")
            return redirect(_redirect_target())
        except AuthenticationError as exc:
            flash(str(exc), "error")
            return render_template("auth/login.html", email=email, next_url=_redirect_target())

    return render_template("auth/login.html", email="", next_url=_redirect_target())


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if AuthService.current_user():
        return redirect(url_for("projects.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            user = AuthService.create_user(email=email, password=password, name=name)
            AuthService.login_user(user)
            flash("Account created.", "success")
            return redirect(_redirect_target())
        except AuthenticationError as exc:
            flash(str(exc), "error")
            return render_template("auth/signup.html", name=name, email=email, next_url=_redirect_target())

    return render_template("auth/signup.html", name="", email="", next_url=_redirect_target())


@auth_bp.route("/auth/google")
def google_login():
    if AuthService.current_user():
        return redirect(url_for("projects.index"))

    next_url = _redirect_target()
    try:
        session_key = "auth_next_url"
        from flask import session
        session[session_key] = next_url
        return redirect(AuthService.google_sign_in_url(_google_callback_url()))
    except AuthenticationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/auth/callback")
def google_callback():
    from flask import session

    error = request.args.get("error_description") or request.args.get("error")
    if error:
        flash(f"Google sign-in failed: {error}", "error")
        return redirect(url_for("auth.login"))

    auth_code = request.args.get("code")
    if not auth_code:
        flash("Google sign-in did not return an authorization code.", "error")
        return redirect(url_for("auth.login"))

    next_url = session.pop("auth_next_url", url_for("projects.index"))
    try:
        AuthService.complete_google_sign_in(auth_code, _google_callback_url())
        flash("Signed in with Google.", "success")
        return redirect(next_url)
    except AuthenticationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    AuthService.logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))

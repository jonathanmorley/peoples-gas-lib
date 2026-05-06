from nox import Session, options
from nox_uv import session

options.default_venv_backend = "uv"
options.stop_on_first_error = True


@session(uv_all_groups=True)
def ty(session: Session) -> None:
    """Typecheck using ty."""
    session.run("ty", "check", "src/")


@session(uv_groups=["test"])
def pytest(session: Session) -> None:
    """Run unit tests."""
    session.run("pytest")


@session(uv_groups=["test"])
def fest(session: Session) -> None:
    """Run mutation tests using fest."""
    session.run("fest", "run", "--progress=plain")

from app.main import create_app


def test_health_route_exists():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/health" in paths

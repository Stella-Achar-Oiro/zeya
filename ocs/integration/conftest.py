# Re-export Open Chat Studio's shared fixtures (team, experiment, environment
# setup). Loaded after pytest-django has configured settings.
from apps.conftest import *  # noqa: F403

"""Tests for the environment parsing helpers used by settings."""

import os
from unittest import mock

from django.apps import apps
from django.test import SimpleTestCase, override_settings

from quiz_app_api.env import env_bool, env_int, env_list, env_str


def with_env(**values):
    return mock.patch.dict(os.environ, values, clear=False)


class EnvStrTests(SimpleTestCase):
    def test_returns_default_when_unset(self):
        self.assertEqual(env_str("QUIZ_TEST_UNSET", "fallback"), "fallback")

    def test_strips_whitespace(self):
        with with_env(QUIZ_TEST_STR="  value  "):
            self.assertEqual(env_str("QUIZ_TEST_STR"), "value")

    def test_blank_value_falls_back_to_default(self):
        with with_env(QUIZ_TEST_STR="   "):
            self.assertEqual(env_str("QUIZ_TEST_STR", "fallback"), "fallback")


class EnvBoolTests(SimpleTestCase):
    def test_truthy_values(self):
        for value in ("1", "true", "TRUE", "yes", "on"):
            with with_env(QUIZ_TEST_BOOL=value):
                self.assertTrue(env_bool("QUIZ_TEST_BOOL"), value)

    def test_falsy_values(self):
        for value in ("0", "false", "No", "off"):
            with with_env(QUIZ_TEST_BOOL=value):
                self.assertFalse(env_bool("QUIZ_TEST_BOOL", default=True), value)

    def test_typo_raises_rather_than_silently_defaulting(self):
        with with_env(QUIZ_TEST_BOOL="ture"), self.assertRaises(ValueError):
            env_bool("QUIZ_TEST_BOOL")


class EnvIntTests(SimpleTestCase):
    def test_parses_an_integer(self):
        with with_env(QUIZ_TEST_INT=" 42 "):
            self.assertEqual(env_int("QUIZ_TEST_INT", 0), 42)

    def test_garbage_raises(self):
        with with_env(QUIZ_TEST_INT="lots"), self.assertRaises(ValueError):
            env_int("QUIZ_TEST_INT", 0)


class EnvListTests(SimpleTestCase):
    def test_splits_and_strips(self):
        with with_env(QUIZ_TEST_LIST="a, b ,c"):
            self.assertEqual(env_list("QUIZ_TEST_LIST"), ["a", "b", "c"])

    def test_empty_entries_are_dropped(self):
        with with_env(QUIZ_TEST_LIST="a,,b,"):
            self.assertEqual(env_list("QUIZ_TEST_LIST"), ["a", "b"])

    def test_default_is_copied_not_shared(self):
        default = ["x"]
        result = env_list("QUIZ_TEST_LIST_UNSET", default)
        result.append("y")

        self.assertEqual(default, ["x"])


class AppConfigTests(SimpleTestCase):
    """The app refuses to start with a scoring strategy that does not exist."""

    def test_ready_accepts_the_configured_strategy(self):
        apps.get_app_config("quiz").ready()  # does not raise

    @override_settings(QUIZ_SCORING_STRATEGY="no-such-strategy")
    def test_ready_rejects_an_unknown_strategy(self):
        with self.assertRaises(LookupError):
            apps.get_app_config("quiz").ready()


class StaticFileServingTests(SimpleTestCase):
    """The admin has to be styled when gunicorn, not runserver, is serving.

    Django's staticfiles app only serves files itself under ``runserver`` with
    ``DEBUG`` on, so a container deployment needs something in the WSGI stack
    that does it. These assert the wiring, not WhiteNoise's own behaviour.
    """

    def test_whitenoise_runs_directly_after_the_security_middleware(self):
        from django.conf import settings

        middleware = settings.MIDDLEWARE
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", middleware)
        self.assertEqual(
            middleware.index("whitenoise.middleware.WhiteNoiseMiddleware"),
            middleware.index("django.middleware.security.SecurityMiddleware") + 1,
        )

    def test_staticfiles_storage_does_not_require_a_manifest(self):
        """A manifest backend 500s every admin page if collectstatic is skipped."""
        from django.conf import settings

        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedStaticFilesStorage",
        )


class ProxySslHeaderTests(SimpleTestCase):
    """``SECURE_PROXY_SSL_HEADER`` is opt-in.

    Trusting ``X-Forwarded-Proto`` with nothing in front to overwrite it lets
    any client claim its plain-HTTP request arrived over TLS.
    """

    def test_not_trusted_by_default(self):
        from django.conf import settings

        self.assertIsNone(getattr(settings, "SECURE_PROXY_SSL_HEADER", None))

    def test_opt_in_is_parsed_as_a_boolean(self):
        with with_env(DJANGO_TRUST_PROXY_SSL_HEADER="yes"):
            self.assertTrue(env_bool("DJANGO_TRUST_PROXY_SSL_HEADER"))
        with (
            with_env(DJANGO_TRUST_PROXY_SSL_HEADER="nope"),
            self.assertRaises(ValueError),
        ):
            env_bool("DJANGO_TRUST_PROXY_SSL_HEADER")

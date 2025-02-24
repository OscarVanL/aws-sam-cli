"""
Testing local lambda runner
"""
from unittest import TestCase
from mock import Mock, patch
from parameterized import parameterized, param

from samcli.commands.local.lib.local_lambda import LocalLambdaRunner
from samcli.commands.local.lib.provider import Function
from samcli.local.lambdafn.exceptions import FunctionNotFound
from samcli.commands.local.lib.exceptions import OverridesNotWellDefinedError


class TestLocalLambda_get_aws_creds(TestCase):
    def setUp(self):
        self.region = "region"
        self.key = "key"
        self.secret = "secret"
        self.token = "token"

        self.runtime_mock = Mock()
        self.function_provider_mock = Mock()
        self.cwd = "cwd"
        self.env_vars_values = {}
        self.debug_context = None
        self.aws_profile = "myprofile"
        self.aws_region = "region"

        self.local_lambda = LocalLambdaRunner(
            self.runtime_mock,
            self.function_provider_mock,
            self.cwd,
            env_vars_values=self.env_vars_values,
            debug_context=self.debug_context,
            aws_profile=self.aws_profile,
            aws_region=self.aws_region,
        )

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_get_from_boto_session(self, boto3_mock):
        creds = Mock()
        creds.access_key = self.key
        creds.secret_key = self.secret
        creds.token = self.token

        mock_session = Mock()
        mock_session.region_name = self.region

        boto3_mock.session.Session.return_value = mock_session
        mock_session.get_credentials.return_value = creds

        expected = {"region": self.region, "key": self.key, "secret": self.secret, "sessiontoken": self.token}

        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called_with(profile_name=self.aws_profile, region_name=self.aws_region)

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_work_with_no_region_name(self, boto3_mock):
        creds = Mock()
        creds.access_key = self.key
        creds.secret_key = self.secret
        creds.token = self.token

        mock_session = Mock()
        del mock_session.region_name  # Ask mock to return AttributeError when 'region_name' is accessed

        boto3_mock.session.Session.return_value = mock_session
        mock_session.get_credentials.return_value = creds

        expected = {"key": self.key, "secret": self.secret, "sessiontoken": self.token}

        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called_with(profile_name=self.aws_profile, region_name=self.aws_region)

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_work_with_no_access_key(self, boto3_mock):
        creds = Mock()
        del creds.access_key  # No access key
        creds.secret_key = self.secret
        creds.token = self.token

        mock_session = Mock()
        mock_session.region_name = self.region

        boto3_mock.session.Session.return_value = mock_session
        mock_session.get_credentials.return_value = creds

        expected = {"region": self.region, "secret": self.secret, "sessiontoken": self.token}

        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called_with(profile_name=self.aws_profile, region_name=self.aws_region)

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_work_with_no_secret_key(self, boto3_mock):
        creds = Mock()
        creds.access_key = self.key
        del creds.secret_key  # No secret key
        creds.token = self.token

        mock_session = Mock()
        mock_session.region_name = self.region

        boto3_mock.session.Session.return_value = mock_session
        mock_session.get_credentials.return_value = creds

        expected = {"region": self.region, "key": self.key, "sessiontoken": self.token}

        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called_with(profile_name=self.aws_profile, region_name=self.aws_region)

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_work_with_no_session_token(self, boto3_mock):
        creds = Mock()
        creds.access_key = self.key
        creds.secret_key = self.secret
        del creds.token  # No Token

        mock_session = Mock()
        mock_session.region_name = self.region

        boto3_mock.DEFAULT_SESSION = None
        boto3_mock.session.Session.return_value = mock_session
        mock_session.get_credentials.return_value = creds

        expected = {"region": self.region, "key": self.key, "secret": self.secret}

        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called()

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_work_with_no_credentials(self, boto3_mock):
        boto3_mock.DEFAULT_SESSION = None
        mock_session = Mock()
        boto3_mock.session.Session.return_value = mock_session
        mock_session.get_credentials.return_value = None

        expected = {}
        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called()

    @patch("samcli.commands.local.lib.local_lambda.boto3")
    def test_must_work_with_no_session(self, boto3_mock):
        boto3_mock.DEFAULT_SESSION = None
        boto3_mock.session.Session.return_value = None

        expected = {}
        actual = self.local_lambda.get_aws_creds()
        self.assertEquals(expected, actual)

        boto3_mock.session.Session.assert_called()


class TestLocalLambda_make_env_vars(TestCase):
    def setUp(self):
        self.runtime_mock = Mock()
        self.function_provider_mock = Mock()
        self.cwd = "/my/current/working/directory"
        self.debug_context = None
        self.aws_profile = "myprofile"
        self.aws_region = "region"
        self.env_vars_values = {}

        self.environ = {"Variables": {"var1": "value1"}}

        self.local_lambda = LocalLambdaRunner(
            self.runtime_mock,
            self.function_provider_mock,
            self.cwd,
            env_vars_values=self.env_vars_values,
            debug_context=self.debug_context,
        )

        self.aws_creds = {"key": "key"}
        self.local_lambda.get_aws_creds = Mock()
        self.local_lambda.get_aws_creds.return_value = self.aws_creds

    @parameterized.expand(
        [
            # Override for the function exists
            ({"function_name": {"a": "b"}}, {"a": "b"}),
            # Override for the function does *not* exist
            ({"otherfunction": {"c": "d"}}, None),
            # Using a CloudFormation parameter file format
            ({"Parameters": {"p1": "v1"}}, {"p1": "v1"}),
        ]
    )
    @patch("samcli.commands.local.lib.local_lambda.EnvironmentVariables")
    @patch("samcli.commands.local.lib.local_lambda.os")
    def test_must_work_with_override_values(
        self, env_vars_values, expected_override_value, os_mock, EnvironmentVariablesMock
    ):
        os_environ = {"some": "value"}
        os_mock.environ = os_environ

        function = Function(
            name="function_name",
            runtime="runtime",
            memory=1234,
            timeout=12,
            handler="handler",
            codeuri="codeuri",
            environment=self.environ,
            rolearn=None,
            layers=[],
        )

        self.local_lambda.env_vars_values = env_vars_values

        self.local_lambda._make_env_vars(function)

        EnvironmentVariablesMock.assert_called_with(
            function.memory,
            function.timeout,
            function.handler,
            variables={"var1": "value1"},
            shell_env_values=os_environ,
            override_values=expected_override_value,
            aws_creds=self.aws_creds,
        )

    @parameterized.expand(
        [
            # Using a invalid file format
            ({"a": "b"}, OverridesNotWellDefinedError),
            ({"a": False}, OverridesNotWellDefinedError),
            ({"a": [True, False]}, OverridesNotWellDefinedError),
        ]
    )
    @patch("samcli.commands.local.lib.local_lambda.os")
    def test_must_not_work_with_invalid_override_values(self, env_vars_values, expected_exception, os_mock):
        os_environ = {"some": "value"}
        os_mock.environ = os_environ

        function = Function(
            name="function_name",
            runtime="runtime",
            memory=1234,
            timeout=12,
            handler="handler",
            codeuri="codeuri",
            environment=self.environ,
            rolearn=None,
            layers=[],
        )

        self.local_lambda.env_vars_values = env_vars_values

        with self.assertRaises(expected_exception):
            self.local_lambda._make_env_vars(function)

    @parameterized.expand(
        [
            param({"a": "b"}),  # Does not have the "Variables" Key
            param("somestring"),  # Must be a dict type
            param(None),
        ]
    )
    @patch("samcli.commands.local.lib.local_lambda.EnvironmentVariables")
    @patch("samcli.commands.local.lib.local_lambda.os")
    def test_must_work_with_invalid_environment_variable(self, environment_variable, os_mock, EnvironmentVariablesMock):
        os_environ = {"some": "value"}
        os_mock.environ = os_environ

        function = Function(
            name="function_name",
            runtime="runtime",
            memory=1234,
            timeout=12,
            handler="handler",
            codeuri="codeuri",
            environment=environment_variable,
            rolearn=None,
            layers=[],
        )

        self.local_lambda.env_vars_values = {}

        self.local_lambda._make_env_vars(function)

        EnvironmentVariablesMock.assert_called_with(
            function.memory,
            function.timeout,
            function.handler,
            variables=None,
            shell_env_values=os_environ,
            override_values=None,
            aws_creds=self.aws_creds,
        )


class TestLocalLambda_get_invoke_config(TestCase):
    def setUp(self):
        self.runtime_mock = Mock()
        self.function_provider_mock = Mock()
        self.cwd = "/my/current/working/directory"
        self.aws_profile = "myprofile"
        self.debug_context = None
        self.env_vars_values = {}
        self.aws_region = "region"

        self.local_lambda = LocalLambdaRunner(
            self.runtime_mock,
            self.function_provider_mock,
            self.cwd,
            env_vars_values=self.env_vars_values,
            debug_context=self.debug_context,
        )

    @patch("samcli.commands.local.lib.local_lambda.resolve_code_path")
    @patch("samcli.commands.local.lib.local_lambda.LocalLambdaRunner.is_debugging")
    @patch("samcli.commands.local.lib.local_lambda.FunctionConfig")
    def test_must_work(self, FunctionConfigMock, is_debugging_mock, resolve_code_path_patch):
        is_debugging_mock.return_value = False

        env_vars = "envvars"
        self.local_lambda._make_env_vars = Mock()
        self.local_lambda._make_env_vars.return_value = env_vars

        codepath = "codepath"
        resolve_code_path_patch.return_value = codepath

        layers = ["layer1", "layer2"]

        function = Function(
            name="function_name",
            runtime="runtime",
            memory=1234,
            timeout=12,
            handler="handler",
            codeuri="codeuri",
            environment=None,
            rolearn=None,
            layers=layers,
        )

        config = "someconfig"
        FunctionConfigMock.return_value = config
        actual = self.local_lambda._get_invoke_config(function)
        self.assertEquals(actual, config)

        FunctionConfigMock.assert_called_with(
            name=function.name,
            runtime=function.runtime,
            handler=function.handler,
            code_abs_path=codepath,
            layers=layers,
            memory=function.memory,
            timeout=function.timeout,
            env_vars=env_vars,
        )

        resolve_code_path_patch.assert_called_with(self.cwd, function.codeuri)
        self.local_lambda._make_env_vars.assert_called_with(function)

    @patch("samcli.commands.local.lib.local_lambda.resolve_code_path")
    @patch("samcli.commands.local.lib.local_lambda.LocalLambdaRunner.is_debugging")
    @patch("samcli.commands.local.lib.local_lambda.FunctionConfig")
    def test_timeout_set_to_max_during_debugging(self, FunctionConfigMock, is_debugging_mock, resolve_code_path_patch):
        is_debugging_mock.return_value = True

        env_vars = "envvars"
        self.local_lambda._make_env_vars = Mock()
        self.local_lambda._make_env_vars.return_value = env_vars

        codepath = "codepath"
        resolve_code_path_patch.return_value = codepath

        function = Function(
            name="function_name",
            runtime="runtime",
            memory=1234,
            timeout=36000,
            handler="handler",
            codeuri="codeuri",
            environment=None,
            rolearn=None,
            layers=[],
        )

        config = "someconfig"
        FunctionConfigMock.return_value = config
        actual = self.local_lambda._get_invoke_config(function)
        self.assertEquals(actual, config)

        FunctionConfigMock.assert_called_with(
            name=function.name,
            runtime=function.runtime,
            handler=function.handler,
            code_abs_path=codepath,
            layers=[],
            memory=function.memory,
            timeout=function.timeout,
            env_vars=env_vars,
        )

        resolve_code_path_patch.assert_called_with(self.cwd, function.codeuri)
        self.local_lambda._make_env_vars.assert_called_with(function)


class TestLocalLambda_invoke(TestCase):
    def setUp(self):
        self.runtime_mock = Mock()
        self.function_provider_mock = Mock()
        self.cwd = "/my/current/working/directory"
        self.debug_context = None
        self.aws_profile = "myprofile"
        self.aws_region = "region"
        self.env_vars_values = {}

        self.local_lambda = LocalLambdaRunner(
            self.runtime_mock,
            self.function_provider_mock,
            self.cwd,
            env_vars_values=self.env_vars_values,
            debug_context=self.debug_context,
        )

    def test_must_work(self):
        name = "name"
        event = "event"
        stdout = "stdout"
        stderr = "stderr"
        function = Mock()
        invoke_config = "config"

        self.function_provider_mock.get.return_value = function
        self.local_lambda._get_invoke_config = Mock()
        self.local_lambda._get_invoke_config.return_value = invoke_config

        self.local_lambda.invoke(name, event, stdout, stderr)

        self.runtime_mock.invoke.assert_called_with(
            invoke_config, event, debug_context=None, stdout=stdout, stderr=stderr
        )

    def test_must_raise_if_function_not_found(self):
        function = Mock()
        function.name = "FunctionLogicalId"

        self.function_provider_mock.get.return_value = None  # function not found
        self.function_provider_mock.get_all.return_value = [function]
        with self.assertRaises(FunctionNotFound):
            self.local_lambda.invoke("name", "event")


class TestLocalLambda_is_debugging(TestCase):
    def setUp(self):
        self.runtime_mock = Mock()
        self.function_provider_mock = Mock()
        self.cwd = "/my/current/working/directory"
        self.debug_context = Mock()
        self.aws_profile = "myprofile"
        self.aws_region = "region"
        self.env_vars_values = {}

        self.local_lambda = LocalLambdaRunner(
            self.runtime_mock,
            self.function_provider_mock,
            self.cwd,
            env_vars_values=self.env_vars_values,
            debug_context=self.debug_context,
        )

    def test_must_be_on(self):
        self.assertTrue(self.local_lambda.is_debugging())

    def test_must_be_off(self):

        self.local_lambda = LocalLambdaRunner(
            self.runtime_mock,
            self.function_provider_mock,
            self.cwd,
            env_vars_values=self.env_vars_values,
            debug_context=None,
        )

        self.assertFalse(self.local_lambda.is_debugging())

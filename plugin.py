from __future__ import annotations

from LSP.plugin import LspPlugin
from LSP.plugin import LspWindowCommand
from LSP.plugin import Notification
from LSP.plugin import notification_handler
from LSP.plugin import Request
from LSP.plugin.core.open import open_externally
from LSP.plugin.core.protocol import Error
from typing import cast
from typing import final
from typing import TypedDict
import sublime


class DeploymentInfo(TypedDict):
    """Result of the `semgrep/loginStatus` and `semgrep/loginFinish` requests. `null` when not logged in."""

    deploymentName: str
    deploymentId: int
    authToken: str


class LoginStartResponse(TypedDict):
    """Result of the `semgrep/loginStart` request. Also the params of the `semgrep/loginFinish` request."""

    url: str
    sessionId: str


@final
class LspSemgrepPlugin(LspPlugin):

    deployment_info: DeploymentInfo | None = None
    """The deployment the user is logged in to, or `None` when not logged in."""

    def on_initialized_async(self) -> None:
        if session := self.weaksession():
            request: Request[None, DeploymentInfo | None] = Request('semgrep/loginStatus')
            session.send_request_task(request).then(self._on_login_status_async)

    def _on_login_status_async(self, deployment_info: DeploymentInfo | Error | None) -> None:
        if isinstance(deployment_info, Error):
            print(f'{self.name}: semgrep/loginStatus request failed: {deployment_info}')
            return
        self.set_deployment_info_async(deployment_info)

    def set_deployment_info_async(self, deployment_info: DeploymentInfo | None) -> None:
        self.deployment_info = deployment_info
        status = 'not logged in'
        if deployment_info:
            # `authToken` is deliberately not exposed as it's a secret.
            status = 'logged-in, deployment "{}", id: {}'.format(
                deployment_info['deploymentName'], deployment_info['deploymentId'])
        if session := self.weaksession():
            session.set_config_status_async(status)

    @notification_handler('semgrep/rulesRefreshed')
    def on_rules_refreshed(self, _: None) -> None:
        """Sent by the server after rules have been loaded - on startup, after a login and on a manual refresh."""
        print(f'{self.name}: rules loaded')


class LspSemgrepWindowCommand(LspWindowCommand):

    def plugin(self) -> LspSemgrepPlugin | None:
        if (session := self.session()) and session.plugin:
            return cast(LspSemgrepPlugin, session.plugin)
        return None


class LspSemgrepLoginCommand(LspSemgrepWindowCommand):

    def is_enabled(self) -> bool:
        plugin = self.plugin()
        return plugin is not None and plugin.deployment_info is None

    def run(self) -> None:
        sublime.set_timeout_async(self._run_async)

    def _run_async(self) -> None:
        if session := self.session():
            request: Request[None, LoginStartResponse | None] = Request('semgrep/loginStart')
            session.send_request_task(request).then(self._on_login_start_async)

    def _on_login_start_async(self, result: LoginStartResponse | Error | None) -> None:
        if isinstance(result, Error):
            print(f'{self.session_name}: semgrep/loginStart request failed: {result}')
            return
        if not result:
            return
        open_externally(result['url'])
        if session := self.session():
            # The server responds to this request only once the login has been completed in the browser.
            request: Request[LoginStartResponse, DeploymentInfo | None] = Request('semgrep/loginFinish', result)
            session.send_request_task(request).then(self._on_login_finish_async)

    def _on_login_finish_async(self, deployment_info: DeploymentInfo | Error | None) -> None:
        if isinstance(deployment_info, Error):
            print(f'{self.session_name}: semgrep/loginFinish request failed: {deployment_info}')
            return
        if deployment_info and (plugin := self.plugin()):
            plugin.set_deployment_info_async(deployment_info)


class LspSemgrepLogoutCommand(LspSemgrepWindowCommand):

    def is_enabled(self) -> bool:
        plugin = self.plugin()
        return plugin is not None and plugin.deployment_info is not None

    def run(self) -> None:
        sublime.set_timeout_async(self._run_async)

    def _run_async(self) -> None:
        if session := self.session():
            session.send_notification(Notification('semgrep/logout'))
        if plugin := self.plugin():
            plugin.set_deployment_info_async(None)


def plugin_loaded() -> None:
    LspSemgrepPlugin.register()


def plugin_unloaded() -> None:
    LspSemgrepPlugin.unregister()

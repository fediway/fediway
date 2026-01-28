from urllib.parse import quote

from pydantic import ConfigDict, SecretStr
from pydantic_settings import BaseSettings

from modules.mastodon import paperclip


class BaseConfig(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")


class FilesConfig(BaseConfig):
    """Media file URL construction config (Mastodon Paperclip)."""

    paperclip_root_url: str = "/system"

    s3_alias_host: str = ""
    s3_protocol: str = "https"
    s3_region: str | None = None
    s3_enabled: bool = False

    def build_file_url(
        self,
        class_name: str,
        attachment: str,
        instance_id: int,
        file_name: str,
        cache: bool = True,
        style: str = "original",
    ) -> str:
        """
        Given the file name and attachment details, build the complete URL.
        Adjusts based on whether S3 is enabled.
        """

        if not file_name:
            return ""

        # Get the interpolated path, e.g.
        # "cache/accounts/avatar/000/000/123/original/my_avatar.png" or without prefix for local.
        path = self.interpolate_file_path(
            class_name, file_name, attachment, instance_id, style=style, cache=cache
        )

        if self.s3_enabled:
            if self.s3_alias_host:
                domain = f"{self.s3_protocol}://{self.s3_alias_host}"
            elif S3_HOST_NAME:
                domain = f"{self.s3_protocol}://{self.s3_alias_host}"
            else:
                domain = f"{self.s3_protocol}://s3.amazonaws.com"
            return f"{domain}/{path}"
        else:
            # For local file storage, use the PAPERCLIP_ROOT_URL
            # PAPERCLIP_ROOT_URL is typically something like '/system'
            return f"{self.paperclip_root_url}/{path}"

    def prefix_url(self, cache: bool = True) -> str:
        return "cache/" if self.s3_enabled and cache else ""

    def interpolate_file_path(
        self,
        class_name: str,
        file_name: str,
        attachment: str,
        instance_id: int,
        cache: bool = True,
        style: str = "original",
    ) -> str:
        """
        Interpolate a file path matching the Mastodon Paperclip config:
        ':prefix_url:class/:attachment/:id_partition/:style/:filename'
        """

        prefix_url = self.prefix_url(cache)
        partition = paperclip.id_partition(instance_id)

        return f"{prefix_url}{class_name}/{attachment}/{partition}/{style}/{file_name}"


class TasksConfig(BaseConfig):
    """Background task worker config."""

    worker_host: str = "localhost"
    worker_port: int = 6379
    worker_pass: SecretStr = ""

    @property
    def worker_url(self):
        password = quote(self.worker_pass.get_secret_value())
        return f"redis://:{password}@{self.worker_host}:{self.worker_port}/0"

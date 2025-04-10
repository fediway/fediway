
from .base import BaseConfig

from modules import paperclip

# We need to construct the url to media files which are handled by the package Paperclip in Mastodon.
# For more details, refer to the Mastodon configuration:
# https://github.com/mastodon/mastodon/blob/e74d682b218096578d59f9a310a85e315dac1b6a/config/initializers/paperclip.rb#L6

class FilesConfig(BaseConfig):
    paperclip_root_url: str = '/system'

    s3_alias_host: str      = ""
    s3_protocol: str        = "https"
    s3_region: str | None   = None
    s3_enabled: bool        = False

    def build_file_url(self, 
                       class_name: str,
                       attachment: str,
                       instance_id: int, 
                       file_name: str, 
                       style: str = "original") -> str:
        """
        Given the file name and attachment details, build the complete URL.
        Adjusts based on whether S3 is enabled.
        """

        if not file_name:
            return ""

        # Get the interpolated path, e.g.
        # "cache/accounts/avatar/000/000/123/original/my_avatar.png" or without prefix for local.
        path = self.interpolate_file_path(class_name, file_name, attachment, instance_id, style)

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

    def prefix_url(self) -> str:
        return ""

    def interpolate_file_path(self, 
                              class_name: str, 
                              file_name: str, 
                              attachment: str, 
                              instance_id: int, 
                              style: str = "original") -> str:
        """
        Interpolate a file path matching the Mastodon Paperclip config:
        ':prefix_url:class/:attachment/:id_partition/:style/:filename'
        """

        prefix_url = self.prefix_url()
        partition = paperclip.id_partition(instance_id)

        return f"{prefix_url}{class_name}/{attachment}/{partition}/{style}/{file_name}"
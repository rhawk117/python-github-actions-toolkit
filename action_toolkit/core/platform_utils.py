import dataclasses
import platform


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class PlatformInfo:
    name: str
    version: str
    arch: str

    def is_windows(self) -> bool:
        """Check if the platform is Windows."""
        return self.name.lower() == 'windows'

    def is_linux(self) -> bool:
        """Check if the platform is Linux."""
        return self.name.lower() == 'linux'

    def is_mac(self) -> bool:
        """Check if the platform is macOS."""
        return self.name.lower() == 'darwin' or self.name.lower() == 'macos'


def get_platform() -> PlatformInfo:
    """Get information about the current platform.

    Returns
    -------
    PlatformInfo
        _metadata about the platform of the runner_
    """
    return PlatformInfo(
        name=platform.system(),
        version=platform.version(),
        arch=platform.machine()
    )

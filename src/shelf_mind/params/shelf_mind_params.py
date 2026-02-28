"""ShelfMind project params.

Parameters are actual value of the config.

The class is a singleton, so it can be accessed from anywhere in the code.

There is a parameter regarding the environment type (stage and location), which
is used to load different paths and other parameters based on the environment.
"""

from loguru import logger as lg

from shelf_mind.metaclasses.singleton import Singleton
from shelf_mind.params.env_type import EnvType
from shelf_mind.params.sample_params import SampleParams
from shelf_mind.params.shelf_mind_paths import ShelfMindPaths
from shelf_mind.params.webapp import WebappParams


class ShelfMindParams(metaclass=Singleton):
    """ShelfMind project parameters."""

    def __init__(self) -> None:
        """Load the ShelfMind params."""
        lg.info("Loading ShelfMind params")
        self.set_env_type()

    def set_env_type(self, env_type: EnvType | None = None) -> None:
        """Set the environment type.

        Args:
            env_type (EnvType | None): The environment type.
                If None, it will be set from the environment variables.
                Defaults to None.
        """
        if env_type is not None:
            self.env_type = env_type
        else:
            self.env_type = EnvType.from_env_var()
        self.load_config()

    def load_config(self) -> None:
        """Load the shelf_mind configuration."""
        self.paths = ShelfMindPaths(env_type=self.env_type)
        self.sample = SampleParams()
        self.webapp = WebappParams(
            stage=self.env_type.stage,
            location=self.env_type.location,
        )

    def __str__(self) -> str:
        """Return the string representation of the object."""
        s = "ShelfMindParams:"
        s += f"\n{self.paths}"
        s += f"\n{self.sample}"
        s += f"\n{self.webapp}"
        return s

    def __repr__(self) -> str:
        """Return the string representation of the object."""
        return str(self)


def get_shelf_mind_params() -> ShelfMindParams:
    """Get the shelf_mind params."""
    return ShelfMindParams()


def get_shelf_mind_paths() -> ShelfMindPaths:
    """Get the shelf_mind paths."""
    return get_shelf_mind_params().paths


def get_webapp_params() -> WebappParams:
    """Get the webapp params."""
    return get_shelf_mind_params().webapp

"""Allow ``python -m opensmell`` with the installed package."""

from .cli import main

raise SystemExit(main())

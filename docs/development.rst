Development
===========

This section provides information for developers who want to contribute to the project.

.. toctree::
    :maxdepth: 2


Setting Up the Development Environment
----------------------------------------
You can use `uv` to set up a virtual environment for development.


Running Tests
----------------
To run the test suite, use the following command::

    uv run pytest tests/


Documentation
-----------------

The documentation is built using Sphinx.

To build the documentation In the docs directory, execute the following command::
    uv run make html

Or to get live updates while editing the documentation::
    uv run make livehtml

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

The documentation is built using Sphinx. To build the documentation, navigate to the docs directory and run::

    uv run make html


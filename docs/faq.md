# FAQ

## What is the difference with Mitmproxy?

Mitmproxy is a full-featured, standalone interactive proxy server with a rich user interface and extensive features for intercepting and modifying traffic. It is designed to be run as a separate application and does not embed directly into other applications.

Mitmproxy is a development tools it's not designed to be used for production environments.

## What is the difference with proxy.py?

Proxy.py is a lightweight, standalone HTTP proxy server, it can be extended with plugins and can be embedded into other applications. However, it is not specifically designed for embedding. ayncio-https-proxy is built from the ground up to be an embeddable component with only asyncio support.

## Can I use this in a production environment?

This library is designed for embedding into applications and can be used in production.

## What is the license?

This project is licensed under the Apache 2.0 License. See the license for details: https://www.apache.org/licenses/LICENSE-2.0


## How AI was used to develop this project?

Claude code have been used for:
* Challenge the API naming
* Help improve documentation
* Help improve test quality
* Generate example usage
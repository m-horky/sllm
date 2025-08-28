import logging

import requests

import sllm.common


logger = logging.getLogger(__name__)


def ok() -> bool:
    """Send a healthcheck.

    Models can go crazy when their runtime misconfigures them.
    This should be good enough indicator to determine whether the
    model is good or not.

    :returns: True if the model is able to respond.
    """
    logger.debug("Sending health/sanity check request.")

    try:
        req: requests.Response = requests.post(
            f"{sllm.common.API_URL}/api/chat",
            json={
                "model": sllm.common.MODEL,
                "temperature": 0.0,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": "Reply with the string 'pong'.",
                    }
                ],
            },
            timeout=(0.5, 5),
        )
    except requests.exceptions.Timeout:
        logger.error("Model didn't respond on time.")
        return False

    response: dict = req.json()
    pong: str = response["message"]["content"].strip()
    if pong != "pong":
        logger.error(
            f"Model didn't respond properly: wanted 'pong', got '{pong}'."
        )
        return False

    logger.debug("Model seems to be sane and healthy.")
    return True


class Request:
    def __init__(
        self,
        prompt: str = "You are a helpful assistant.",
        query: str = "Tell me a short joke.",
        *,
        example_input_header: str = "",
        example_response_header: str = "",
        temperature: float = 0.8,
    ):
        """Build an API request.

        :param prompt: The system message for the model.
        :param query: User input.
        :param example_input_header:
            In case the prompt is structured, and contains examples
            of interaction, this is the header for user input.
        :param example_response_header:
            In case the prompt is structured, and contains examples
            of interaction, this is the header for LLM output.
        :param temperature:
            Model temperature. Conservative between 0.6 and 1.0,
            creative between 1.0 and 2.0.
        """
        self.prompt: str = prompt
        self.query: str = query
        self.temperature: float = temperature
        self.example_input_header: str = example_input_header
        self.example_response_header: str = example_response_header

    def _build(self) -> dict:
        return {
            "model": sllm.common.MODEL,
            "temperature": self.temperature,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.prompt},
                {
                    "role": "user",
                    "content": "{}\n{}\n{}".format(
                        self.example_input_header,
                        self.query,
                        self.example_response_header,
                    ),
                },
            ],
        }

    def send(self, *, timeout: int = 120) -> str:
        """Request an answer from the LLM.

        Expects ramalama to be serving OpenAPI-compatible API on
        localhost on a well-known port.

        :param timeout: REST call timeout, in seconds.
        :raises TimeoutError: Model works fine, but response timed out.
        :raises RuntimeError: Model is malfunctioning.
        """
        logger.debug("Sending API request.")

        if not ok():
            raise RuntimeError(
                "Model is malfunctioning. "
                "Run again with '--debug', or execute 'ramalama' yourself to investigate."
            )

        try:
            req: requests.Response = requests.post(
                f"{sllm.common.API_URL}/api/chat",
                json=self._build(),
                # connection timeout can be very low, we're on localhost
                timeout=(0.5, timeout),
            )
        except requests.exceptions.Timeout:
            logger.debug("Model timed out.")
            raise TimeoutError("Model didn't respond on time.")

        response: dict = req.json()
        content: str = response["message"]["content"].strip()
        return content

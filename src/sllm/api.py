import logging

import requests

import sllm.common


logger = logging.getLogger(__name__)


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

    def send(self, *, timeout: int = 120) -> dict:
        """Request an answer from the LLM.

        Expects ramalama to be serving OpenAPI-compatible API on
        localhost on a well-known port.

        :param timeout: REST call timeout, in seconds.
        """
        logger.debug("Sending API request.")

        req: requests.Response = requests.post(
            f"{sllm.common.API_URL}/v1/chat/completions",
            json=self._build(),
            # connection timeout can be very low, we're on localhost
            timeout=(0.5, timeout),
        )
        response: dict = req.json()

        logger.debug(
            "Spent {delta:.2f} seconds on prompt ({size} tokens).".format(
                delta=response["timings"]["prompt_ms"] / 1000,
                size=response["usage"]["prompt_tokens"],
            )
        )
        logger.debug(
            "Spend {delta:.2f} seconds on inference ({speed:.2f} tokens/second).".format(
                delta=response["timings"]["predicted_ms"] / 1000,
                speed=response["timings"]["predicted_per_second"],
            )
        )

        return response

    # TODO Streaming via iterators

# sllm

My repository for managing small large language models. Yep.

![Demo of `sllm-git-message`](demo.gif)

## Installation

Dependencies: `systemd`, `podman`.

```shell
$ pipx install git+https://github.com/m-horky/sllm.git
```

## Setting up

```shell
$ sllm
usage: sllm [-h] [--init | --status | --start | --stop] [--debug]

options:
  -h, --help  show this help message and exit
  --init      ensure runtime
  --status    runtime status
  --start     start the runtime
  --stop      stop the runtime
  --debug     nerd information
```

The default model is `ollama://llama3.2:3b`, which is able to run reasonably well on a CPU.
You can overwrite it by setting `SLLM_MODEL=` environment variable.
You can find a variety of models [here](https://ollama.com/search).

```shell
$ sllm --init
```

```shell
$ sllm --status
INFO Runtime is present (2.11 GB).
INFO API is present (http://127.0.0.1:6574, version 0.11.7).
INFO Model is present (Q4_K_M, 1.88 GB).
INFO Container shutdown is scheduled (2025-08-28 09:59:33).
```

By default, the model shuts itself down after 15 minutes to save resources. You can manage this interval by seting `SLLM_SHUTDOWN_INTERVAL` to systemd-compatible value.

## Using the git commit message review tool

Dependencies: `git`.

```shell
$ sllm-git-message --help
usage: sllm-git-message [-h] [--ref REF | --file FILE] [--debug]

options:
  -h, --help   show this help message and exit
  --ref REF    load from commit
  --file FILE  load from file
  --debug      nerd information
```

```shell
$ sllm-git-message --ref HEAD
INFO Starting the container.
| chore: Let ramalama automatically determine CPU/GPU
INFO Rating...
1. Title: CPU/GPU auto-determination.
2. What: Ramalama will automatically determine CPU/GPU.
3. Why: Meh, I do not know.
WARNING You should use '--amend' to rewrite the message.
```

To use this automatically for every commit in your repository:

- Create `.git/hooks/commit-msg` and set it as executable.
- In it, call `sllm-git-message --file $1`.

## Using local translation tool

```shell
$ sllm-translate --help
usage: sllm-translate [-h] [--debug] [input ...]

Translate text into English. Leaving the input empty will open $EDITOR window.
```

```shell
$ sllm-translate Potřebuji poradit jak povolit program v SELinuxu
| Potřebuji poradit jak povolit program v SELinuxu
INFO Translating...
I need advice on how to enable the program in SELinux
```

## Configuration

Configuration is done through environment variables. Set them in your `.profile`.

- `SLLM_OLLAMA`: ollama image to use. Defaults to `docker.io/ollama/ollama:latest`.
- `SLLM_MODEL`: LLM to use. Defaults to `llama3.2:3b`.
- `SLLM_SHUTDOWN_INTERVAL`: Timeout after which ramalama should shut down itself.

## Why

**Why do anything?**

I believe that there are use-cases for locally running models. I wanted to explore them.

From time to time, I need to translate text that cannot be put into Google Translate, and a locally running model is perfect for that. I don't need the exact precise translation, all I need is to understand the technical problem the other party is describing.

**Why does `sllm-git-message` respond with 'Meh'?**

It is a word that LLMs do not usually emit. During development, this made it very simple to determine whether the output is good or not, and it stuck.

**Aren't you boiling the oceans by this?**

There's been a lot of debate online against LLMs in general. One of the arguments against them is that they require a lot of power to operate, and all that compute heat is boiling the oceans through climate change.

Well. This is running locally, you are boiling your own bathtub at most. Have you tried looking at the power consumption of the nearest gaming computer? You can afford to run a LLM for a few dozen queries a day, it's not as bad as it might seem.

## License

MIT

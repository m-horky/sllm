# sllm

My repository for managing small large language models. Yep.

## Installation

Dependencies: `systemd`, `podman`, `ramalama`.

```shell
$ pipx install git+https://github.com/m-horky/sllm.git
```

## Setting up

```shell
$ sllm
usage: sllm [-h] [--debug] [--init] [--status]

options:
  -h, --help  show this help message and exit
  --init      ensure runtime
  --status    runtime status
  --debug     nerd information
```

```shell
$ sllm --init
```

```shell
$ sllm --status
INFO Runtime is present (1.03 GB).
INFO Model is present (1.88 GB).
INFO API is present (http://127.0.0.1:6574).
INFO Container shutdown is scheduled (2025-04-08 12:41:24).
```

By default, the model shuts itself down after 15 minutes to save resources. You can manage this interval by seting `SLLM_SHUTDOWN_INTERVAL` to systemd-compatible value.

## Using the git commit message review tool

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
usage: sllm-translate [-h] [--pipe | --edit | --file FILE] [--debug]

options:
  -h, --help   show this help message and exit
  --pipe       read from pipe (default)
  --edit       open editor
  --file FILE  read from file
  --debug      nerd information
```

```shell
$ echo 'Potřebuji poradit jak povolit program v SELinuxu' | sllm-translate
| Potřebuji poradit jak povolit program v SELinuxu
INFO Translating...
I need advice on how to enable the program in SELinux
```

## Why

**Why do anything?**

I believe that there are use-cases for locally running models. I wanted to explore them.

From time to time, I need to translate text that cannot be put into Google Translate, and a locally running model is perfect for that. I don't need the exact precise translation, all I need is to understand the technical problem the other party is describing.

**Why 'Meh'?**

It is a word that LLMs do not usually emit. During development, this made it very simple to determine whether the output is good or not, and it stuck.

## License

MIT

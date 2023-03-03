# Polish with ChatGPT API 

This code is a simple polishing tool for personal use. Automatically read the input txt file and output it to the file.


## Requirements 

Python 3.7+

You can install other software packages with the following command:

```
$ pip install openai sqlite3
```

## Usage

First you need to have an API key in [openai platform website](https://platform.openai.com/). Click your account button in the top-right corner and "View API Keys". Then you can create your API keys through "Create new secret key" button and copy it to your clipboard.

Paste the API key in the `polish.py` line 7:

```
openai.api_key = "sk-***********"
    
```

Next put your text in the `input.txt` file and run the following command:
```
$ python polish.py
```

Then you can see your polished text in the `output.txt`.

You can also change your language by `--lang` arguments.

## Notes

The code is partially based on [CAI](https://github.com/sanxing-chen/cai) and [Awesome-chatgpt-prompts](https://github.com/f/awesome-chatgpt-prompts).
import openai
import argparse
from cai.chatgpt import ChatGPT
import shutil

if __name__ == "__main__":   
    openai.api_key = "sk-**"
    
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--lang", type=str, default="English", help="the output language")
    argparser.add_argument("--input_file", type=str, default="input.txt", help="input file path")
    argparser.add_argument("--polish_times", type=int, default=1, help="polish times")
    argparser.add_argument("--output_file", type=str, default="output.txt", help="output file path")
    
    args = argparser.parse_args()
    if args.lang == "en":
        language = "English"
    elif args.lang == "zh":
        language = "Chinese"
    else:
        language = args.lang.capitalize()
        print(f"The output language is {language}. Please check if it is full name and correct. For example, if you want to translate to Chinese, please use --lang zh.")
        
    prompts = f"I want you to act as an {language} translator, spelling corrector and improver. " + \
        f"I will speak to you in any language and you will detect the language, translate it and answer in the corrected and improved version of my text, in {language}. " + \
        f"I want you to replace my simplified A0-level words and sentences with more beautiful and elegant, upper level {language} words and sentences. " + \
        "Keep the meaning same, but make them more literary. I want you to only reply the correction, the improvements and nothing else, do not write explanations."
    
    chatgpt = ChatGPT(resume=False, debug=False)
    init_response = chatgpt.get_chat_response(prompts, "ctx_chat")
    
    chatgpt = ChatGPT(resume=True, debug=False)   
    with open(args.input_file, "r") as f:
        with open(args.output_file, "w") as f2:
            for line in f:
                line = line.strip()
                if line == "":
                    continue
                response = chatgpt.get_chat_response(line, "ctx_chat")
                f2.write(response.lstrip() + "\n")
    
    if args.polish_times > 1:
        with open(args.output_file, "r") as f:
            with open(args.output_file + ".tmp", "w") as f2:
                for line in f:
                    line = line.strip()
                    if line == "":
                        continue
                    response = chatgpt.get_chat_response(line, "ctx_chat")
                    f2.write(response.lstrip() + "\n")
        shutil.move(args.output_file + ".tmp", args.output_file)        
    chatgpt.close()
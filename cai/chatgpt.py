import openai
import sqlite3
import json
import csv
import argparse

# $0.002 per 1k tokens
TOKEN_COST = 0.002 / 1000
DEFAULT_CHAT_MODEL = "gpt-3.5-turbo"
FAKE_RESPONSE = {
    "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "content": "\n\nAhoy, me hearties! Listen up, fer I've got news that'll make ye cheer like a salty dog with a bone. There be an API known as ChatGPT that's gonna change the way ye communicate with yer mates online.\n\nWith the ChatGPT API, ye can send and receive text messages like ye be chattin' with another pirate right next to ye. And the best part be that ye don't even need to know how to code like Davy Jones. It be easy to use, and ye can integrate it with yer website or app in no time.\n\nThe ChatGPT API be like havin' yer own parrot that talks with ye! Whether ye be runnin' an online store or a gaming app, ChatGPT be a lifesaver fer when ye wanna communicate with yer customers or players.\n\nSo drop anchor, and give ChatGPT a try. Ye won't be disappointed, me hearties! Arrr!",
                        "role": "assistant"
                    }
                }
    ],
    "created": 1677772996,
    "id": "chatcmpl-6pfgiYYMyoA9DzTJDORtLjaicIj6w",
    "model": "gpt-3.5-turbo-0301",
    "object": "chat.completion",
    "usage": {
        "completion_tokens": 197,
        "prompt_tokens": 23,
        "total_tokens": 220
    }
}

def str2date(s):
    if s == None:
        return None
    else:
        # convert ("2021-01-01", "h", "d", "w", "m") to timestamp
        if s == "h":
            s = "datetime('now', '-1 Hour')"
        elif s == "d":
            s = "date('now')"
        elif s == "w":
            s = "date('now', '-7 days')"
        elif s == "m":
            s = "date('now', '-30 days')"
        else:
            s = "date('" + s + "')"
        return s


class ChatGPT:

    def __init__(self, resume=False, debug=False):
        """
        resume: whether to resume the previous chat session.
                If False, a new session will be started, otherwise the previous session will be resumed and the chat history will be printed
        debug: whether to enable debug mode.
                In debug mode, no API calls will be made, no records will be saved to the database
        """
        self.debug = debug
        self._init_db()
        self._get_session_history()
        if not resume:
            self.new_session()
        else:
            self._print_session_history()

    def _init_db(self):
        # use chat.db to store chat history
        conn = sqlite3.connect('chat.db')
        self.c = conn.cursor()

        # create a table to save raw responses, if it doesn't exist
        self.c.execute("CREATE TABLE IF NOT EXISTS raw_chat (response TEXT)")

        # create a table to save parsed responses, if it doesn't exist
        """ table schema:
         id (int): the id of the response
         timestamp (int): the timestamp of the response
         prompt (str): the prompt that was sent to the API
         reply (str): the reply that was sent by the API
         prompt_tokens (int): the number of tokens used for the prompt
         completion_tokens (int): the number of tokens used for the reply
         total_tokens (int): the total number of tokens used for the prompt and reply
         model (str): the model used to generate the reply
        """
        self.c.execute("CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY, timestamp INTEGER, prompt TEXT, reply TEXT, prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER, model TEXT)")

        # create a table to save mapping between chat id and session id (many to one), if it doesn't exist
        """ table schema:
            chat_id (int): the id of the response
            session_id (int): the id of the session
        """
        self.c.execute("CREATE TABLE IF NOT EXISTS chat_session (chat_id INTEGER, session_id INTEGER)")

    def _get_session_history(self):
        """
        resume the previous chat session by loading from the database, if it exists
        """
        # get the last session id
        self.c.execute("SELECT session_id FROM chat_session ORDER BY session_id DESC LIMIT 1")
        res = self.c.fetchone()
        if res:
            self.session_id = res[0]
            # get all chat history (prompt, reply) of the last session, ordered by timestamp
            self.c.execute(
                "SELECT prompt, reply FROM chat WHERE id IN (SELECT chat_id FROM chat_session WHERE session_id = ?) ORDER BY timestamp", (self.session_id,))
            res = self.c.fetchall()
            if res:
                pr_pairs = []
                for r in res:
                    pr_pairs.extend([
                        {"role": "user", "content": r[0]},
                        {"role": "assistant", "content": r[1]}])
                self.session_history = pr_pairs
            else:
                # this is an unexpected case, but we can still start a new session after cleaning up the session table
                err_msg = "No chat history found, starting a new session"
                print(err_msg)
                # delete all records associated with the last session in chat_session
                self.c.execute("DELETE FROM chat_session WHERE session_id = ?", (self.session_id,))
        else:
            # the session table is empty, start a new session
            self.session_id = 0
            self.session_history = []

    def _print_session_history(self):
        """
        print the chat history of the current session
        """
        if len(self.session_history) > 0:
            print("Session history:")
            for i in range(len(self.session_history)):
                print(self.session_history[i]["role"] + ": " + self.session_history[i]["content"].lstrip())

    def new_session(self):
        """
        start a new chat session
        """
        # if the session is empty, we don't need to create a new session
        if len(self.session_history) > 0:
            self.session_id += 1
            self.session_history = []

    def get_response_by_type(self, prompt, type="chat"):
        if self.debug:
            revised_prompt = "[DEBUG] " + prompt
            res = FAKE_RESPONSE
        elif type == "ctx_chat":
            revised_prompt = prompt
            res = openai.ChatCompletion.create(
                model=DEFAULT_CHAT_MODEL,
                messages=self.session_history + [{"role": "user", "content": revised_prompt}]
            )
        elif type == "chat":
            revised_prompt = prompt
            res = openai.ChatCompletion.create(
                model=DEFAULT_CHAT_MODEL,
                messages=[{"role": "user", "content": revised_prompt}]
            )
        elif type == "revise":
            revised_prompt = "Please revise the following paragraph to improve the flow and fix any grammatical errors, typos, etc., without changing the meaning. Only return the revised texts.\n\n" + prompt
            res = openai.ChatCompletion.create(
                model=DEFAULT_CHAT_MODEL,
                messages=[
                    # {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": revised_prompt},
                ]
            )
        elif type == "search":
            revised_prompt = "Tell me what you know about \"" + prompt + "\"?"
            res = openai.ChatCompletion.create(
                model=DEFAULT_CHAT_MODEL,
                messages=[
                    # {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": revised_prompt},
                ]
            )

        return res, revised_prompt

    def get_chat_response(self, prompt, type="chat"):
        response, revised_prompt = self.get_response_by_type(prompt, type)
        self.save_chat_response(revised_prompt, response)
        response_content = response['choices'][0]['message']['content']
        self.session_history.extend([
            {"role": "user", "content": revised_prompt},
            {"role": "assistant", "content": response_content}])
        return response_content

    def save_chat_response(self, prompt, response):
        # save the parsed response to the database
        self.c.execute("INSERT INTO chat VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
                       (response['created'],
                        prompt,
                        response['choices'][0]['message']['content'],
                        response['usage']['prompt_tokens'],
                        response['usage']['completion_tokens'],
                        response['usage']['total_tokens'],
                        response['model']))

        # save the entire json response to the database
        json_response = json.dumps(response)
        self.c.execute("INSERT INTO raw_chat VALUES (?)", (json_response,))

        # save the mapping between chat id and session id
        self.c.execute("SELECT id FROM chat ORDER BY id DESC LIMIT 1")
        chat_id = self.c.fetchone()[0]
        self.c.execute("INSERT INTO chat_session VALUES (?, ?)", (chat_id, self.session_id))

    def get_total_tokens(self, since=None):
        # get the total number of tokens used starting from a certain timestamp
        if since == None:
            self.c.execute("SELECT SUM(total_tokens) FROM chat")
        else:
            since = str2date(since)
            self.c.execute("SELECT SUM(total_tokens) FROM chat WHERE DATETIME(timestamp, 'unixepoch') > " + since)
        total_tokens = self.c.fetchone()[0]
        return total_tokens

    def print_total_bill(self):
        # print the total bill (in dollars) for the chat API
        # by this hour, today, this week, this month, and all time
        total_tokens = [self.get_total_tokens(since) for since in [None, "h", "d", "w", "m"]]
        total_dollars = [tokens * TOKEN_COST for tokens in total_tokens]
        print("Total bill (in dollars) for the chat API:")
        # print with 3 decimal places
        print("This hour: " + "{:.3f}".format(total_dollars[1]))
        print("Today: " + "{:.3f}".format(total_dollars[2]))
        print("This week: " + "{:.3f}".format(total_dollars[3]))
        print("This month: " + "{:.3f}".format(total_dollars[4]))
        print("All time: " + "{:.3f}".format(total_dollars[0]))

    def clean_db(self):
        # clear the chat history
        self.c.execute("DELETE FROM chat")
        self.c.execute("DELETE FROM raw_chat")

    def export_chat_history(self, since=None):
        # export the chat history to a csv file
        if since == None:
            self.c.execute("SELECT * FROM chat")
        else:
            date = str2date(since)
            self.c.execute("SELECT * FROM chat WHERE DATETIME(timestamp, 'unixepoch') > " + date)
        file_suffix = since if since != None else "all"
        with open('chat_history_' + file_suffix + '.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow([i[0] for i in self.c.description])
            writer.writerows(self.c)

    def close(self):
        # save the changes
        if not self.debug:
            self.c.connection.commit()
        # close the database connection
        self.c.close()


def main_interactive(debug=False):
    chatgpt = ChatGPT(True, debug)
    while True:
        try:
            prompt = input("user: ")
        except KeyboardInterrupt:
            print("Exiting...")
            break
        if prompt.startswith("!"):
            if prompt == "!exit":
                break
            if prompt == "!cleandb":
                chatgpt.clean_db()
                continue
            if prompt == "!export":
                chatgpt.export_chat_history()
                continue
            if prompt == "!bill":
                chatgpt.print_total_bill()
                continue
            if prompt == "!new" or prompt == "!clear":
                chatgpt.new_session()
                print("New session started.")
                continue
            if prompt == "!help":
                print("Available commands:")
                print("!exit: exit the program")
                print("!new or !clear: start a new session, by default the assistant keeps the previous session's context")
                print("!cleandb: clear the chat history in the database")
                print("!export: export the chat history to a csv file")
                print("!bill: print the total bill (in dollars) for the chat API")
                print("!help: print this message")
                continue
            print("Invalid command. Please try again.")
        else:
            response = chatgpt.get_chat_response(prompt, "ctx_chat")
            print('assistant:', response)

    chatgpt.close()


def main_one_shot(prompt, type, debug=False):
    chatgpt = ChatGPT(True if type == "ctx_chat" else False,
                      debug=debug)
    response = chatgpt.get_chat_response(prompt, type)
    if type == "ctx_chat":
        print('user:', chatgpt.session_history[-2]['content'])
        print('assistant:', response.lstrip())
    else:
        print(response.lstrip())
    chatgpt.close()


def main_export():
    chatgpt = ChatGPT()
    for since in [None, "h", "d", "w", "m"]:
        chatgpt.export_chat_history(since)
    chatgpt.close()


def main_bill():
    chatgpt = ChatGPT()
    chatgpt.print_total_bill()
    chatgpt.close()


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--mode', type=str, default='interactive',
                           choices=['interactive', 'oneshot', 'export', 'bill'],
                           help='mode of the program')
    argparser.add_argument('--debug', action='store_true', help='use fake response for debugging')
    argparser.add_argument('--prompt', type=str, default='', help='prompt for oneshot mode')
    argparser.add_argument('--type', type=str, default='chat',
                           choices=['chat', 'ctx_chat', 'revise', 'search'],
                           help='type of one shot mode')
    args = argparser.parse_args()

    if args.mode == 'interactive':
        main_interactive(args.debug)
    elif args.mode == 'oneshot':
        assert args.prompt != '', "Please provide a prompt for oneshot mode"
        main_one_shot(args.prompt, args.type, args.debug)
    elif args.mode == 'export':
        main_export()
    elif args.mode == 'bill':
        main_bill()

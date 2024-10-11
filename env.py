import os
from dotenv import load_dotenv, dotenv_values
import gradio as gr
print(gr.__version__)

load_dotenv(".env", override=False)  # take environment variables from ..env.
print(f"setting environment variables: {dotenv_values('.env')}")


def get_app_root():
    return os.getcwd()


def get_env_value(key):
    return os.environ.get(key)


if __name__ == '__main__':
    print("app root is: " +get_app_root())
    print("your API key is: "+ get_env_value('LLM_API_KEY'))
    print("your url is: "+get_env_value('MODEL_NAME'))
   # print("DEBUG is: " + os.environ.get('PY_DEBUG'))
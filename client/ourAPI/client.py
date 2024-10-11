from openai import OpenAI
from client.LLMclientgeneric import LLMclientgeneric

class OurAPI(LLMclientgeneric):
    def __init__(self,*args,**krgs):
        super().__init__(*args,**krgs)
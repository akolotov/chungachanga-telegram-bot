import google.generativeai as genai

def initialize(api_key: str):
    genai.configure(api_key=api_key)

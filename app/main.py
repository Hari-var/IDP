import pandas as pd
import time
from app.helpers.llm import get_gemini_response_with_context
from sql import *
import random
import os
table_exists()
from process import main
file_path=input("enter file path")
main(file_path)
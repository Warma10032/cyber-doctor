from typing import Tuple,List,Dict
from model.KG.search_model import INSTANCE

def search(query:str) -> Tuple[int,List[Dict]|None]:
    result = INSTANCE.search(query)
    if result is not None:
        return 0 , result
    else:
        return -1 , None
    

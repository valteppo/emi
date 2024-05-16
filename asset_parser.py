"""
Parses inventory and corp assets copy-paste to sum of volume and est price(+ 10%).
For courier contracts.
"""

import pyperclip
import math
import time

def to_number(string_input)-> float:
    num_str = ""
    for char in string_input:
        if char.isdigit():
            num_str += char
        elif char == ",":
            num_str += "."
    return float(num_str)

def summarize_assets():
    clipboard = pyperclip.paste()
    if len(clipboard) == 0:
        return
    
    try:
        data = clipboard.split("\n")
        line_element_count = len(data[0].split("\t"))
    except:
        return
    
    total_volume = 0
    total_price_est = 0
    match line_element_count:
        case 8: # Corporation assets
            try:
                for line in data:
                    name, amount, item_group, item_category, size, slot, volume, est_price = line.split("\t")
                    total_volume += to_number(volume[:-1]) # -1 cuts out the "3" from tailing "m3"
                    total_price_est += to_number(est_price)

                pyperclip.copy(f"{math.ceil(total_volume):,}\t{math.ceil(total_price_est*1.1):,}")
                return
            except:
                return
        
        case 5: # Inventory
            try:
                for line in data:
                    name, amount, item_category, volume, est_price = line.split("\t")
                    total_volume += to_number(volume[:-1]) # -1 cuts out the "3" from tailing "m3"
                    total_price_est += to_number(est_price)

                pyperclip.copy(f"{math.ceil(total_volume):,}\t{math.ceil(total_price_est*1.1):,}")
                return
            except:
                return

        case _:
            return

while True:
    summarize_assets()
    time.sleep(0.25)
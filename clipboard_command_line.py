"""
Parses inventory and corp assets copy-paste to sum of volume and est price(+ 10%).
For courier contracts.
"""

import pyperclip
import math
import time
import os
import sqlite3

import data_handling
import pi_scp

cwd = os.getcwd()

class Clipboard_command:
    def __init__(self) -> None:
        self.clipboard_memory = [None]
        self.current_clipboard = ""
        self.command_prompt = ""
        self.command_prompt_history = ["start"]
        self.jita_prices = data_handling.get_region_prices(10000002)
        self.item_translator = data_handling.translator_items()
        self.item_size = data_handling.get_size()

    def to_number(string_input)-> float:
        num_str = ""
        for char in string_input:
            if char.isdigit():
                num_str += char
            elif char == ",":
                num_str += "."
        return float(num_str)
    
    def courier_volume_and_collateral(self, formatted_list_input) -> list:
        """
        Given split lines, returns courier volume and cost summary.
        """
        total_volume = 0
        total_price_est = 0

        if len(formatted_list_input[0].split("\t")) == 8:# Corporation assets window
            for line in formatted_list_input:
                print(line)
                name, amount, item_group, item_category, size, slot, volume, est_price = line.split("\t")
                total_volume += Clipboard_command.to_number(volume[:-1]) # -1 cuts out the "3" from tailing "m3"
                if self.item_translator[name] in self.jita_prices:
                    total_price_est += self.jita_prices[self.item_translator[name]]["sell"]
                else: 
                    total_price_est += Clipboard_command.to_number(est_price)
            return [math.ceil(total_volume), math.ceil(total_price_est*1.1)]
                
        if len(formatted_list_input[0].split("\t")) == 5:# Inventory
            for line in formatted_list_input:
                name, amount, item_category, volume, est_price = line.split("\t")
                total_volume += Clipboard_command.to_number(volume[:-1]) # -1 cuts out the "3" from tailing "m3"
                if self.item_translator[name] in self.jita_prices:
                    total_price_est += self.jita_prices[self.item_translator[name]]["sell"]
                else:
                    total_price_est += Clipboard_command.to_number(est_price)
            return [math.ceil(total_volume), math.ceil(total_price_est*1.1)]
        

    def evaluate_clipboard(self, clipboard_raw):
        if self.clipboard_memory[-1] == clipboard_raw:
            return # Clipboard unchanged
        else: 
            self.current_clipboard = clipboard_raw
            self.clipboard_memory.append(self.current_clipboard)
            Clipboard_command.operate(self)
    
    def operate(self):
        """
        Evaluates what to do with clipboard.
        """
        command_families = ["tr", "cr", "sys"]
        tokens = self.current_clipboard.split(" ")
        if tokens[0] in command_families:
            self.command_prompt = self.current_clipboard
        if self.command_prompt == "" or self.command_prompt == self.command_prompt_history[-1]:
            return
        
        # If command is set and new, operate on clipboard
        command_tokens = self.command_prompt.split(" ")
        command_tokens = [i.lower() for i in command_tokens]
        print(command_tokens)
        match command_tokens[0]:
            ########################
            case "cr": # Courier family commands
                match command_tokens[1]:
                    case "sum":
                        # Summarizes volume and prices estimates for items selected from Items hangar or Corporation Deliveries.
                        try:
                            volume, price = Clipboard_command.courier_volume_and_collateral(self, formatted_list_input=self.current_clipboard.split("\n"))
                            pyperclip.copy(f"{volume:,}\t{price:,}")
                        except:
                            pass
                    
                    case "ex": 
                        # Select export to a region
                        try:
                            destination = command_tokens[2]
                        except:
                            pass
                        
                        try:
                            files = os.listdir(cwd+f"/output/courier/")
                            data = ""
                            for file in files:
                                file_lower = file.lower()
                                if destination in file_lower and "export" in file_lower:
                                    with open(cwd+f"/output/courier/{file}", "r") as target:
                                        data = target.read()
                            
                            if len(data) > 0:
                                pyperclip.copy(data)
                        except:
                            pass
                    
                    case "im":
                        # Select import from a region
                        try:
                            destination = command_tokens[2]
                        except:
                            pass
                        
                        try:
                            files = os.listdir(cwd+f"/output/courier/")
                            data = ""
                            for file in files:
                                file_lower = file.lower()
                                if destination in file_lower and "import" in file_lower:
                                    with open(cwd+f"/output/courier/{file}", "r") as target:
                                        data = target.read()
                            
                            if len(data) > 0:
                                pyperclip.copy(data)
                        except:
                            pass
                
            
            ########################
            case "tr": # Station trade family commands
                match command_tokens[1]:
                    case "jita":
                        try:
                            with open(cwd+f"/output/station/Jita_station_trade.txt","r") as file:
                                data = file.read()
                            pyperclip.copy(data)
                        except:
                            pass

                    case "ig": # Add items to ignore list
                        try:
                            typeIDs_to_ignore = []
                            for item_name in self.current_clipboard.split("\n"):
                                if item_name in self.item_translator[item_name]:
                                    typeIDs_to_ignore.append(self.item_translator[item_name])
                            Clipboard_command.ignore_these_items(item_id_list=typeIDs_to_ignore,
                                                                 prompt_family=command_tokens[0],
                                                                 prompt_command=command_tokens[1],
                                                                 file="jita")
                        except:
                            pass

            ########################
            case "sys": # Data handling and system prompts
                match command_tokens[1]:
                    case "re": # Refresh volumes and orders from raspberry, may take several minutes
                        pyperclip.copy("Downloading orders and volumes and trades, may take several moments. 'Done' in clipboard when finished.")
                        pi_scp.get_orders_volumes()
                        pi_scp.get_trades
                        pyperclip.copy("Done.")
        
        self.command_prompt_history.append(self.command_prompt) # Mark as done            

ccmd = Clipboard_command()
while True:
    ccmd.evaluate_clipboard(pyperclip.paste())
    time.sleep(0.25)
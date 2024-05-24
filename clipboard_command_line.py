"""
Parses inventory and corp assets copy-paste to sum of volume and est price(+ 10%).
For courier contracts.
"""

import pyperclip
import math
import time
import os

import data_handling
import pi_scp

cwd = os.getcwd()
COMMAND_FAMILIES = ["tr", "cr", "sys"]

class Clipboard_shell:
    def __init__(self) -> None:
        self.clipboard_memory = [None]
        self.current_clipboard = ""
        self.command_prompt = ""
        self.jita_prices = data_handling.get_region_prices(10000002)
        self.item_translator = data_handling.translator_items()
        self.location_translator = data_handling.translator_location()
        self.item_size = data_handling.get_size()

    def to_number(self, string_input)-> float:
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

        if len(formatted_list_input[0].split("\t")) == 8:
            # Corporation assets window
            for line in formatted_list_input:
                name, amount, item_group, item_category, size, slot, volume, est_price = line.split("\t")
                if self.item_translator[name] in self.item_size:
                    total_volume += self.item_size[self.item_translator[name]] * int(math.ceil(self.to_number(amount)))
                else:
                    total_volume += self.to_number(volume[:-1]) * int(math.ceil(self.to_number(amount))) # -1 cuts out the "3" from tailing "m3"
                if self.item_translator[name] in self.jita_prices:
                    total_price_est += self.jita_prices[self.item_translator[name]]["sell"]* int(math.ceil(self.to_number(amount)))
                else: 
                    total_price_est += self.to_number(est_price) 
            return [math.ceil(total_volume), math.ceil(total_price_est*1.15)] 
                
        if len(formatted_list_input[0].split("\t")) == 5:
            # Inventory 
            for line in formatted_list_input:
                name, amount, item_category, volume, est_price = line.split("\t")
                if self.item_translator[name] in self.item_size:
                    total_volume += self.item_size[self.item_translator[name]] * int(math.ceil(self.to_number(amount)))
                else:
                    total_volume += self.to_number(volume[:-1]) * int(math.ceil(self.to_number(amount))) # -1 cuts out the "3" from tailing "m3"
                if self.item_translator[name] in self.jita_prices:
                    total_price_est += self.jita_prices[self.item_translator[name]]["sell"] * int(math.ceil(self.to_number(amount)))
                else:
                    total_price_est += self.to_number(est_price)
            return [math.ceil(total_volume), math.ceil(total_price_est*1.15)]
        
   
    def jita_station_trading(self):
        with open(cwd+f"/output/station/Jita_station_trade.txt","r") as file:
            data = file.read()
        return data
    
    def search_location_courier_buy_list(self, destination, export_or_import):
        files = os.listdir(cwd+f"/output/courier/")
        data = ""
        for file in files:
            file_lower = file.lower()
            if destination.lower() in file_lower and export_or_import.lower() in file_lower:
                with open(cwd+f"/output/courier/{file}", "r") as target:
                    data = target.read()
                break
        
        if len(data) > 0:
            return data
        
    def redownload_raspberry_data(self):
        pyperclip.copy("Downloading ... please do not exit script until clipboard reads 'Done.' This takes a couple moments.")
        pi_scp.get_orders_volumes()
        pi_scp.get_trades()
        pyperclip.copy("Done.")

    def immediate(self, prompt):
        """
        These commands do not require additional clipboard data and are run at once.
        """
        immediate_prompts = [
            "tr jita",

            "cr ex",
            "cr im",
            "cr ind",

            "sys re",
            "sys clr",
            "sys exit",
            "sys quit"
        ]
        for instance in immediate_prompts:
            if prompt in instance:
                return True
        return False

    def evaluate_clipboard(self, clipboard_raw):
        if self.clipboard_memory[-1] == clipboard_raw:
            # Clipboard unchanged
            return 
        
        else: 
            self.current_clipboard = clipboard_raw
            self.clipboard_memory.append(self.current_clipboard)

            tokens = self.current_clipboard.split(" ")
            if tokens[0] in COMMAND_FAMILIES and len(tokens) > 1:
                self.command_prompt = self.current_clipboard
                if self.immediate(self.command_prompt):
                    self.operate()
                    self.command_prompt = ""
                self.current_clipboard = ""

            
            if self.command_prompt != "" and self.command_prompt != self.current_clipboard: 
                # Else if there are commands, execute those commands on clipboard. 
                self.operate()
            else: 
                # No commands, pass 
                pass 
    
    def operate(self): 
        """
        Executes command prompt on the clipboard data.
        """
        commands = self.command_prompt.split(" ")
        match commands[0]: 
            case "tr": # Trade family commands
                match commands[1]:
                    case "jita": # Jita station trade
                        jita_quickbar = self.jita_station_trading()
                        pyperclip.copy(jita_quickbar)
            
            case "cr": # Courier family commands
                match commands[1]:
                    case "ex": # Export to region
                        try:
                            data = self.search_location_courier_buy_list(destination = commands[2], export_or_import="EXPORT")
                            pyperclip.copy(data)
                        except:
                            pyperclip.copy("None")
                    case "im": # Import from region
                        try:
                            data = self.search_location_courier_buy_list(destination = commands[2], export_or_import="IMPORT")
                            pyperclip.copy(data)
                        except:
                            pyperclip.copy("None")
                    case "sum": # Sum selection volumes and Jita prices, actuates on next copypaste
                        try:
                            volume, cost = self.courier_volume_and_collateral(self.current_clipboard.strip().split("\n"))
                            self.clipboard_memory.append(f"{volume:,}\t{cost:,}")
                            pyperclip.copy(f"{volume:,}\t{cost:,}")
                        except:
                            pass
                    case "ind": # Return the import/export index
                        try:
                            with open(cwd+f"/output/courier/index.txt", "r") as file:
                                pyperclip.copy(file.read())
                        except:
                            pass 

            case "sys": # System family commands 
                match commands[1]:
                    case "quit":
                        exit()
                    case "exit":
                        exit()
                    case "re": # Refresh data from raspberry pi 
                        self.redownload_raspberry_data()
                    case "clr": # Clears memory
                        self.current_clipboard = ""
                        self.clipboard_memory = [None]
                        self.command_prompt = ""
                        pyperclip.copy("")


cs = Clipboard_shell()
while True:
    cs.evaluate_clipboard(pyperclip.paste())
    time.sleep(0.25)
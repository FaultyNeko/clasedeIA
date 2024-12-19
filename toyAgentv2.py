from osbrain import run_nameserver, run_agent, Agent
import csv
import random
from datetime import datetime
import time
import logging
from threading import Thread
from merchants import BasicMerchant, RichMerchant, PoorMerchant
from operators import OperatorInfinite, OperatorFinite, OperatorInfiniteQuality, OperatorFiniteQuality



# Set logging level to DEBUG for osBrain
logging.getLogger('osbrain').setLevel(logging.DEBUG)



def read_config_file(file_path):
    """
    Reads and parses the configuration file.
    """
    config = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):  # Ignore comments and empty lines
                    key, value = line.split(":")
                    config[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        exit(1)
    return config


def log_merchants_inventory(merchants):
    """
    Logs each merchant's inventory details to a plain text file.
    """
    date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f'merchant_inventory_{date_str}.txt'
    
    with open(filename, 'w', encoding='utf-8') as file:
        file.write("=== Merchant Inventory Report ===\n\n")
        for merchant in merchants:
            merchant_name = merchant.get_name()  # Use the exposed method
            merchant_budget = merchant.get_attr('budget')
            inventory = merchant.get_attr('inventory')

            # Write Merchant Header
            file.write(f"Merchant: {merchant_name}\n")
            file.write(f"Remaining Budget: {merchant_budget}\n")
            file.write("Inventory:\n")
            
            # Check if inventory is empty
            if not inventory:
                file.write("  - No items in inventory\n")
            else:
                # Write each fish in the inventory
                for product_number, details in inventory.items():
                    fish_type = details.get('type', 'Unknown')
                    quality = details.get('quality', 'N/A')
                    price = details.get('price', 'N/A')
                    file.write(f"  - Product {product_number}: Type {fish_type}, Quality {quality}, Price {price}\n")
            
            file.write("\n")  # Add spacing between merchants
        file.write("=== End of Report ===\n")
    
    print(f"Merchant inventory report saved to '{filename}'.")







def log_transactions(transactions):
    date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    with open(f'log_{date_str}.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['Product', 'SellPrice', 'Merchant'])
        writer.writeheader()
        for transaction in transactions:
            writer.writerow(transaction)


def log_setup(merchants_info):
    date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    with open(f'setup_{date_str}.csv', mode='w', newline='', encoding='utf-8') as file:
        # Include 'Type' in the fieldnames
        writer = csv.DictWriter(file, fieldnames=['Merchant', 'Type', 'Preference', 'Budget'])
        writer.writeheader()
        for info in merchants_info:
            writer.writerow(info)




    # Main program execution


if __name__ == '__main__':
    ns = run_nameserver()

    # Read configuration file
    config_file = "config.txt"
    config = read_config_file(config_file)

    # Extract inputs
    operator_type = int(config.get('operator_type', 1))
    total_fish_to_sell = int(config.get('total_fish_to_sell', 10))
    num_basic_merchants = int(config.get('num_basic_merchants', 0))
    num_rich_merchants = int(config.get('num_rich_merchants', 0))
    num_poor_merchants = int(config.get('num_poor_merchants', 0))

    operator = None
    use_quality = False

    # Initialize the operator based on configuration
    if operator_type == 1:
        operator = run_agent('OperatorInfinite', base=OperatorInfinite)
    elif operator_type == 2:
        operator = run_agent(
            'OperatorFinite',
            base=OperatorFinite,
            attributes={'total_fish_to_sell': total_fish_to_sell}
        )
    elif operator_type == 3:
        operator = run_agent('OperatorInfiniteQuality', base=OperatorInfiniteQuality)
        use_quality = True
    elif operator_type == 4:
        operator = run_agent(
            'OperatorFiniteQuality',
            base=OperatorFiniteQuality,
            attributes={'total_fish_to_sell': total_fish_to_sell}
        )
        use_quality = True
    else:
        print("Invalid operator type in configuration file.")
        ns.shutdown()
        exit()

    print("Quality logic is enabled for merchants.") if use_quality else None

    # Create merchants
    merchants = []  # List to hold all merchant agents
    merchants_info = []  # List to log merchant details

    publish_address = operator.addr('publish_channel')
    bid_address = operator.addr('bid_channel')

    def create_merchants(num_merchants, merchant_class, budget):
        """Creates a specified number of merchants and connects them to the operator."""
        for i in range(1, num_merchants + 1):
            merchant_name = f'{merchant_class.__name__}_{i}'
            merchant = run_agent(merchant_name, base=merchant_class)
            merchant.set_attr(budget=budget)
            merchant.connect(publish_address, handler='on_operator_message')
            merchant.bind('PUSH', alias='bid_channel')
            merchant.connect(bid_address, alias='bid_channel')
            merchants.append(merchant)
            merchants_info.append({
                'Merchant': merchant_name,
                'Type': merchant_class.__name__,
                'Preference': merchant.get_attr('preference'),
                'Budget': merchant.get_attr('budget')
            })

    # Use inputs from the config file
    create_merchants(num_basic_merchants, BasicMerchant, 100)
    create_merchants(num_rich_merchants, RichMerchant, 500)
    create_merchants(num_poor_merchants, PoorMerchant, 50)

    # Log setup and start auction
    log_setup(merchants_info)
    operator.start_auction()

    # Wait for the auction to finish
    while operator.get_attr('running'):
        time.sleep(1)

    log_merchants_inventory(merchants)

    # Shutdown all agents
    operator.shutdown()
    for merchant in merchants:
        merchant.shutdown()
    ns.shutdown()


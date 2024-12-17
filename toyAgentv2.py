from osbrain import run_nameserver, run_agent, Agent
import csv
import random
from datetime import datetime
import time
import logging
from threading import Thread

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


class Operator(Agent):
    def on_init(self):
        # PUB socket to broadcast auction info and confirmations
        self.publish_address = self.bind('PUB', alias='publish_channel')
        # PULL socket to receive bids from merchants
        self.bid_address = self.bind('PULL', alias='bid_channel', handler=self.on_bid)
        self.fish_types = ['H', 'S', 'T']
        self.fish_index = 0
        self.transactions = []
        self.current_auction = None
        self.running = True  # Indicates whether the auction is running


    def start_auction(self):
        self.auction_next_fish()

    def auction_next_fish(self):
        # To be implemented in subclasses
        pass

    def send_fish_info(self):
        auction = self.current_auction
        if not auction['sold']:
            self.log_info(
                f"Auctioning Fish {auction['product_number']}: Type {auction['fish_type']}, Price {auction['current_price']}."
            )
            product_info = {
                'message_type': 'auction_info',
                "product_number": auction['product_number'],
                "product_type": auction['fish_type'],
                "price": auction['current_price']
            }
            self.send('publish_channel', product_info)
            self.timer = self.after(1, self.check_for_replies, alias='price_decrement_timer')

    def on_bid(self, bid):
        self.log_info(f"Received bid: {bid}")
        merchant_id = bid.get('merchant_id')
        auction = self.current_auction
        if auction and not auction['sold']:
            if bid.get('product_number') == auction['product_number']:
                # Sell the fish
                self.log_info(f"Fish {auction['product_number']} sold to Merchant {merchant_id} at price {auction['current_price']}.")
                auction['sold'] = True
                self.transactions.append({
                    'Product': auction['product_number'],
                    'SellPrice': auction['current_price'],
                    'Merchant': merchant_id
                })
                # Stop the timer
                self.stop_timer('price_decrement_timer')
                # Send confirmation
                confirmation = {
                    'message_type': 'confirmation',
                    'status': 'confirmed',
                    'product_number': auction['product_number'],
                    'merchant_id': merchant_id,
                    'price': auction['current_price'],
                    'product_type': auction['fish_type']
                }
                self.send('publish_channel', confirmation)
                # Move to the next auction
                self.auction_next_fish()
        # If fish already sold or bid is invalid, ignore

    def check_for_replies(self, *args, **kwargs):
        # To be implemented in subclasses
        pass

    def on_stop(self):
        log_transactions(self.transactions)


class OperatorInfinite(Operator):
    def on_init(self):
        super().on_init()
        self.fish_in_stock = 30
        self.unsold_count = 0
        self.max_unsold = 3

    def auction_next_fish(self):
        if self.fish_in_stock > 0 and self.unsold_count < self.max_unsold:
            fish_type = self.fish_types[self.fish_index % len(self.fish_types)]
            self.fish_index += 1
            self.fish_in_stock -= 1
            self.current_auction = {
                'fish_type': fish_type,
                'product_number': self.fish_index,
                'current_price': 30,
                'bottom_price': 10,
                'price_decrement': 2,
                'sold': False
            }
            self.send_fish_info()
        else:
            self.log_info("Auction ended.")
            self.running = False  # Set running to False when auction ends

    def check_for_replies(self, *args, **kwargs):
        auction = self.current_auction
        if not auction['sold']:
            auction['current_price'] -= auction['price_decrement']
            if auction['current_price'] >= auction['bottom_price']:
                self.send_fish_info()
            else:
                self.log_info(f"Fish {auction['product_number']} was not sold.")
                self.unsold_count += 1
                self.transactions.append({
                    'Product': auction['product_number'],
                    'SellPrice': 0,
                    'Merchant': 0  # Indicate unsold
                })
                self.auction_next_fish()


class OperatorFinite(Operator):
    def on_init(self):
        super().on_init()
        self.total_fish_to_sell = self.get_attr('total_fish_to_sell')
        self.fish_sold_count = 0

    def auction_next_fish(self):
        if self.fish_sold_count < self.total_fish_to_sell:
            fish_type = self.fish_types[self.fish_index % len(self.fish_types)]
            self.fish_index += 1
            self.current_auction = {
                'fish_type': fish_type,
                'product_number': self.fish_index,
                'current_price': 30,
                'bottom_price': 10,
                'price_decrement': 2,
                'sold': False
            }
            self.send_fish_info()
        else:
            self.log_info("Auction ended after selling the specified number of fish.")
            self.running = False  # Set running to False when auction ends

    def check_for_replies(self, *args, **kwargs):
        auction = self.current_auction
        if not auction['sold']:
            auction['current_price'] -= auction['price_decrement']
            if auction['current_price'] >= auction['bottom_price']:
                self.send_fish_info()
            else:
                self.log_info(f"Fish {auction['product_number']} was not sold.")
                self.transactions.append({
                    'Product': auction['product_number'],
                    'SellPrice': 0,
                    'Merchant': 0  # Indicate unsold
                })
                self.fish_sold_count += 1  # Increment the sold count for unsold fish
                self.auction_next_fish()


    def on_bid(self, bid):
        self.log_info(f"Received bid: {bid}")
        merchant_id = bid.get('merchant_id')
        auction = self.current_auction
        if auction and not auction['sold']:
            if bid.get('product_number') == auction['product_number']:
                # Sell the fish
                self.log_info(
                    f"Fish {auction['product_number']} sold to Merchant {merchant_id} at price {auction['current_price']}."
                )
                auction['sold'] = True
                self.transactions.append({
                    'Product': auction['product_number'],
                    'SellPrice': auction['current_price'],
                    'Merchant': merchant_id
                })
                # Increment fish_sold_count for sold fish
                self.fish_sold_count += 1

                # Stop the timer
                self.stop_timer('price_decrement_timer')

                # Send confirmation with quality
                confirmation = {
                    'message_type': 'confirmation',
                    'status': 'confirmed',
                    'product_number': auction['product_number'],
                    'merchant_id': merchant_id,
                    'price': auction['current_price'],
                    'product_type': auction['fish_type'],
                    'quality': auction.get('quality')  # Include quality in confirmation
                }
                self.send('publish_channel', confirmation)

                # Move to the next auction
                self.auction_next_fish()


class OperatorInfiniteQuality(OperatorInfinite):
    def auction_next_fish(self):
        if self.fish_in_stock > 0 and self.unsold_count < self.max_unsold:
            fish_type = self.fish_types[self.fish_index % len(self.fish_types)]
            fish_quality = random.choice(['good', 'normal', 'bad'])
            self.fish_index += 1
            self.fish_in_stock -= 1
            self.current_auction = {
                'fish_type': fish_type,
                'quality': fish_quality,
                'product_number': self.fish_index,
                'current_price': 30,
                'bottom_price': 10,
                'price_decrement': 2,
                'sold': False
            }
            self.send_fish_info()
        else:
            self.log_info("Auction ended.")
            self.running = False  # Set running to False when auction ends

    def send_fish_info(self):
        auction = self.current_auction
        if not auction['sold']:
            self.log_info(
                f"Auctioning Fish {auction['product_number']}: Type {auction['fish_type']}, "
                f"Quality {auction['quality']}, Price {auction['current_price']}."
            )
            product_info = {
                'message_type': 'auction_info',
                'product_number': auction['product_number'],
                'product_type': auction['fish_type'],
                'quality': auction['quality'],
                'price': auction['current_price']
            }
            self.send('publish_channel', product_info)
            self.timer = self.after(1, self.check_for_replies, alias='price_decrement_timer')


# New OperatorFiniteQuality subclass with quality
class OperatorFiniteQuality(OperatorFinite):
    def auction_next_fish(self):
        if self.fish_sold_count < self.total_fish_to_sell:
            fish_type = self.fish_types[self.fish_index % len(self.fish_types)]
            fish_quality = random.choice(['good', 'normal', 'bad'])
            self.fish_index += 1
            self.current_auction = {
                'fish_type': fish_type,
                'quality': fish_quality,
                'product_number': self.fish_index,
                'current_price': 30,
                'bottom_price': 10,
                'price_decrement': 2,
                'sold': False
            }
            self.send_fish_info()
        else:
            self.log_info("Auction ended after selling the specified number of fish.")
            self.running = False  # Set running to False when auction ends

    def send_fish_info(self):
        auction = self.current_auction
        if not auction['sold']:
            self.log_info(
                f"Auctioning Fish {auction['product_number']}: Type {auction['fish_type']}, "
                f"Quality {auction['quality']}, Price {auction['current_price']}."
            )
            product_info = {
                'message_type': 'auction_info',
                'product_number': auction['product_number'],
                'product_type': auction['fish_type'],
                'quality': auction['quality'],
                'price': auction['current_price']
            }
            self.send('publish_channel', product_info)
            self.timer = self.after(1, self.check_for_replies, alias='price_decrement_timer')


class Merchant(Agent):
    def on_init(self):
        self.inventory = {}
        self.budget = 100  # Default budget, adjustable by subclasses
        self.preference = random.choice(['H', 'S', 'T'])  # Random fish type preference
        self.log_info(f"My preference is: {self.preference}")
        self.fish_types = ['H', 'S', 'T']
        self.current_auctions = {}

        # Inventory counts per fish type
        self.inventory_counts = {fish_type: 0 for fish_type in self.fish_types}

        # Quality-based price thresholds and minimums
        self.preferred_price_thresholds = {'good': 30, 'normal': 20, 'bad': 10}
        self.preferred_price_minimums = {'good': 10, 'normal': 10, 'bad': 10}

    def on_operator_message(self, message):
        """Handles incoming messages from the operator."""
        message_type = message.get('message_type')
        if message_type == 'auction_info':
            self.on_product_info(message)
        elif message_type == 'confirmation':
            self.on_confirmation(message)

    def on_product_info(self, message):
        """
        Handles product auction information and decides whether to bid.
        Supports quality as an optional attribute.
        """
        product_number = message.get('product_number')
        product_type = message.get('product_type')
        price = message.get('price')
        quality = message.get('quality', None)  # Defaults to None if not provided

        # Skip if auction is closed or budget is insufficient
        if self.budget < price or self.current_auctions.get(product_number, {}).get('status') == 'closed':
            return

        # Store auction details
        self.current_auctions[product_number] = {
            'product_type': product_type,
            'quality': quality,
            'price': price,
            'status': 'open'
        }

        # Determine the threshold for quality (default to mid-range if not specified)
        threshold = self.preferred_price_thresholds.get(quality, 20)

        # Buying logic
        should_buy = False
        if product_type == self.preference:
            # Buy preferred fish within acceptable price range
            if price <= threshold:
                should_buy = True
        else:
            # Buy non-preferred fish if discounted and inventory is empty
            if self.inventory_counts[product_type] == 0 and price <= (threshold / 2):
                should_buy = True

        if should_buy:
            self.log_info(f"Attempting to buy Fish {product_number} at price {price} with quality {quality}")
            bid = {
                'merchant_id': self.name,
                'product_number': product_number,
            }
            # Send bid to operator
            self.send('bid_channel', bid)
            # Mark auction as pending
            self.current_auctions[product_number]['status'] = 'pending'

    def on_confirmation(self, message):
        """
        Handles confirmation of purchase and updates inventory, budget, and price thresholds.
        """
        merchant_id = message.get('merchant_id')
        if merchant_id != self.name:
            return  # Ignore confirmations not meant for this merchant

        product_number = message.get('product_number')
        price = message.get('price')
        product_type = message.get('product_type')
        quality = message.get('quality', None)

        self.log_info(f"Purchase confirmed for Fish {product_number} at price {price} with quality {quality}")
        self.budget -= price

        # Update inventory
        self.inventory[product_number] = {
            'type': product_type,
            'quality': quality,
            'price': price
        }
        self.inventory_counts[product_type] += 1
        self.log_info(f"Remaining budget: {self.budget}")

        # Mark auction as closed
        self.current_auctions[product_number]['status'] = 'closed'

        # Adjust thresholds if preferred fish is bought
        if product_type == self.preference and quality in self.preferred_price_thresholds:
            old_threshold = self.preferred_price_thresholds[quality]
            self.preferred_price_thresholds[quality] *= 0.8  # Reduce threshold by 20%
            if self.preferred_price_thresholds[quality] < self.preferred_price_minimums[quality]:
                self.preferred_price_thresholds[quality] = self.preferred_price_minimums[quality]
            self.log_info(
                f"Threshold for {quality} quality reduced from {old_threshold:.2f} to {self.preferred_price_thresholds[quality]:.2f}"
            )

    def on_exit(self):
        """Optional cleanup logic."""
        self.log_info("Merchant shutting down.")



class BasicMerchant(Merchant):
    def on_init(self):
        super().on_init()
        self.budget = 100


class RichMerchant(Merchant):
    def on_init(self):
        super().on_init()
        self.budget = 500
        # Rich merchants always accept the max price for preferred fish
        self.preferred_price_threshold = 30
        self.preferred_price_minimum = 30  # No decrease

    def on_confirmation(self, message):
        # Override to prevent decreasing the price threshold
        merchant_id = message.get('merchant_id')
        if merchant_id == self.name:
            product_number = message.get('product_number')
            price = message.get('price')
            product_type = message.get('product_type')
            self.log_info(f"Purchase confirmed for Fish {product_number} at price {price}")
            self.budget -= price
            # Update inventory
            self.inventory[product_number] = {
                'type': product_type,
                'price': price
            }
            self.inventory_counts[product_type] += 1
            self.log_info(f"Remaining budget: {self.budget}")
            # Mark auction as closed
            self.current_auctions[product_number]['status'] = 'closed'
            # Do not adjust preferred_price_threshold


class PoorMerchant(Merchant):
    def on_init(self):
        super().on_init()
        self.budget = 50
        # Set a low preferred price threshold
        self.preferred_price_threshold = 15
        self.preferred_price_minimum = 10

    def on_product_info(self, message):
        # Override buying logic to only buy at heavy discounts
        product_number = message.get('product_number')
        product_type = message.get('product_type')
        price = message.get('price')

        if self.budget >= price and self.current_auctions.get(product_number, {}).get('status') != 'closed':
            self.current_auctions[product_number] = {
                'product_type': product_type,
                'price': price,
                'status': 'open'
            }
            should_buy = False

            if price <= 15:
                # Only buy if price is heavily discounted
                should_buy = True

            if should_buy:
                self.log_info(f"Attempting to buy Fish {product_number} at price {price}")
                bid = {
                    'merchant_id': self.name,
                    'product_number': product_number,
                }
                self.send('bid_channel', bid)
                self.current_auctions[product_number]['status'] = 'pending'







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

    # Shutdown all agents
    operator.shutdown()
    for merchant in merchants:
        merchant.shutdown()
    ns.shutdown()


from osbrain import run_nameserver, run_agent, Agent
import csv
import random
from datetime import datetime
import time
import logging

# Set logging level to DEBUG for osBrain
logging.getLogger('osbrain').setLevel(logging.DEBUG)


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
        writer = csv.DictWriter(file, fieldnames=['Merchant', 'Preference', 'Budget'])
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
        self.fish_in_stock = 30
        self.unsold_count = 0
        self.max_unsold = 3
        self.transactions = []
        self.current_auction = None
        self.running = True  # Indicates whether the auction is running

    def start_auction(self):
        self.auction_next_fish()

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
                self.unsold_count = 0
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

    def on_stop(self):
        log_transactions(self.transactions)


class BasicMerchant(Agent):
    def on_init(self):
        self.inventory = []
        self.budget = 100
        self.current_auctions = {}
        self.preference = random.choice(['H', 'S', 'T'])  # Random preference
        self.log_info(f"My preference is: {self.preference}")

    def on_operator_message(self, message):
        message_type = message.get('message_type')
        if message_type == 'auction_info':
            self.on_product_info(message)
        elif message_type == 'confirmation':
            self.on_confirmation(message)

    def on_product_info(self, message):
        product_number = message.get('product_number')
        product_type = message.get('product_type')
        price = message.get('price')

        if self.budget >= price and self.current_auctions.get(product_number, {}).get('status') != 'closed':
            # Store auction details
            self.current_auctions[product_number] = {
                'product_type': product_type,
                'price': price,
                'status': 'open'
            }

            # Logic to decide whether to buy or not
            should_buy = False

            if len(self.inventory) == 0:
                # Buy the first fish to have at least one
                should_buy = True
            elif product_type == self.preference and price <= 25:
                # Buy preferred fish if price is acceptable
                should_buy = True
            elif price <= 15:
                # Buy any fish if the price is very low
                should_buy = True

            if should_buy:
                self.log_info(f"Attempting to buy Fish {product_number} at price {price}")
                bid = {
                    'merchant_id': self.name,
                    'product_number': product_number,
                }
                # Send bid to the operator
                self.send('bid_channel', bid)
                # Mark auction as pending
                self.current_auctions[product_number]['status'] = 'pending'

    def on_confirmation(self, message):
        merchant_id = message.get('merchant_id')
        if merchant_id == self.name:
            product_number = message.get('product_number')
            price = message.get('price')
            product_type = message.get('product_type')
            self.log_info(f"Purchase confirmed for Fish {product_number} at price {price}")
            self.budget -= price
            self.inventory.append((product_number, product_type, price))
            self.log_info(f"Remaining budget: {self.budget}")
            # Mark auction as closed
            self.current_auctions[product_number]['status'] = 'closed'

    def on_exit(self):
        pass  # Optional cleanup code can go here


# Main program execution
if __name__ == '__main__':
    ns = run_nameserver()
    operator = run_agent('Operator', base=Operator)

    num_basic_merchants = int(input("Enter the number of the Basic Merchants: "))
    merchants = []
    merchants_info = []

    # Get operator's addresses
    publish_address = operator.addr('publish_channel')
    bid_address = operator.addr('bid_channel')

    for i in range(1, num_basic_merchants + 1):
        merchant_name = f'BasicMerchant_{i}'
        merchant = run_agent(merchant_name, base=BasicMerchant)
        merchant.set_attr(budget=100)

        # Connect merchant to operator's publish channel (SUB socket)
        merchant.connect(publish_address, handler='on_operator_message')

        # Merchant binds PUSH socket to send bids
        merchant.bind('PUSH', alias='bid_channel')
        # Merchant connects bid_channel to operator's bid_channel (PULL socket)
        merchant.connect(bid_address, alias='bid_channel')

        merchants.append(merchant)
        merchants_info.append({
            'Merchant': merchant_name,
            'Preference': merchant.get_attr('preference'),
            'Budget': merchant.get_attr('budget')
        })

    log_setup(merchants_info)
    operator.start_auction()

    # Wait until the auction is over
    while operator.get_attr('running'):
        time.sleep(1)

    # Shutdown agents
    operator.shutdown()
    for merchant in merchants:
        merchant.shutdown()

    ns.shutdown()

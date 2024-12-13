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
                # Process the sale
                self.log_info(
                    f"Fish {auction['product_number']} sold to {merchant_id} at price {auction['current_price']}."
                )
                auction['sold'] = True
                self.transactions.append({
                    'Product': auction['product_number'],
                    'SellPrice': auction['current_price'],
                    'Merchant': merchant_id
                })
                self.stop_timer('price_decrement_timer')

                # Send confirmation to the buyer
                confirmation = {
                    'message_type': 'confirmation',
                    'status': 'confirmed',
                    'product_number': auction['product_number'],
                    'merchant_id': merchant_id,
                    'price': auction['current_price'],
                    'product_type': auction['fish_type']
                }
                self.send('publish_channel', confirmation)

                # Start the next auction
                self.auction_next_fish()


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
                self.auction_next_fish()

    def on_bid(self, bid):
        self.log_info(f"Received bid: {bid}")
        merchant_id = bid.get('merchant_id')
        auction = self.current_auction
        if auction and not auction['sold']:
            if bid.get('product_number') == auction['product_number']:
                # Sell the fish
                self.log_info(f"Fish {auction['product_number']} sold to Merchant {merchant_id} at price {auction['current_price']}.")
                auction['sold'] = True
                self.fish_sold_count += 1  # Increment fish sold count here
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
        self.budget = 100
        self.preference = random.choice(['H', 'S', 'T'])  # Random preference
        self.log_info(f"My preference is: {self.preference}")
        self.fish_types = ['H', 'S', 'T']
        self.current_auctions = {}

        # Initialize inventory counts for each fish type
        self.inventory_counts = {fish_type: 0 for fish_type in self.fish_types}

        # Initialize preferred price thresholds
        self.preferred_price_threshold = 30  # Starting acceptable price for preferred fish
        self.preferred_price_minimum = 10    # Minimum acceptable price for preferred fish

    def join_coalition(self, coalition):
        """Join an existing coalition."""
        self.coalition = coalition
        coalition.members.append(self)
        coalition.update_budget()
        self.log_info(f"Joined coalition: {coalition.name}")

    def form_coalitions(merchants):
        coalitions = []
        ungrouped_merchants = merchants[:]

        while ungrouped_merchants:
            # Form a coalition of 2-3 merchants if possible
            if len(ungrouped_merchants) > 1:
                members = ungrouped_merchants[:3]
                coalition_name = f"Coalition_{len(coalitions) + 1}"
                coalition = Coalition(coalition_name, members)
                coalitions.append(coalition)

                # Remove merchants from ungrouped list
                for member in members:
                    member.join_coalition(coalition)
                    ungrouped_merchants.remove(member)
            else:
                # Single merchant remains, no coalition
                break

        return coalitions


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

        if self.coalition:
            # Coalition-level decision
            if self.coalition.shared_budget >= price:
                self.coalition.add_to_inventory(product_number, price)
                bid = {
                    'merchant_id': self.coalition.name,
                    'product_number': product_number,
                }
                self.send('bid_channel', bid)
        else:

            if self.budget >= price and self.current_auctions.get(product_number, {}).get('status') != 'closed':
                # Store auction details
                self.current_auctions[product_number] = {
                    'product_type': product_type,
                    'price': price,
                    'status': 'open'
                }

                # Buying logic
                should_buy = False

                if product_type == self.preference:
                    # Buy preferred fish if price is within acceptable threshold
                    if price <= self.preferred_price_threshold:
                        should_buy = True
                else:
                    # For non-preferred fish, buy at least one if price is discounted
                    if self.inventory_counts[product_type] == 0 and price <= 20:
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
            # Update inventory
            self.inventory[product_number] = {
                'type': product_type,
                'price': price
            }
            self.inventory_counts[product_type] += 1
            self.log_info(f"Remaining budget: {self.budget}")
            # Mark auction as closed
            self.current_auctions[product_number]['status'] = 'closed'

            if product_type == self.preference:
                # Decrease acceptable price threshold by 20%, down to minimum
                old_threshold = self.preferred_price_threshold
                self.preferred_price_threshold *= 0.8
                if self.preferred_price_threshold < self.preferred_price_minimum:
                    self.preferred_price_threshold = self.preferred_price_minimum
                self.log_info(f"Preferred price threshold reduced from {old_threshold:.2f} to {self.preferred_price_threshold:.2f}")

    def on_exit(self):
        pass  # Optional cleanup code can go here


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


class BasicMerchantQuality(BasicMerchant):
    def on_init(self):
        super().on_init()
        # Initialize thresholds per quality
        self.preferred_price_thresholds = {
            'good': 30,  # Starting threshold for good quality
            'normal': 30,
            'bad': 30
        }
        self.preferred_price_minimums = {
            'good': 10,  # Minimum acceptable price
            'normal': 10,
            'bad': 10
        }

    def on_product_info(self, message):
        product_number = message.get('product_number')
        product_type = message.get('product_type')
        quality = message.get('quality', None)
        price = message.get('price')

        if quality is None:
            # If quality is not provided, act as base class
            super().on_product_info(message)
            return

        if self.budget >= price and self.current_auctions.get(product_number, {}).get('status') != 'closed':
            # Store auction details
            self.current_auctions[product_number] = {
                'product_type': product_type,
                'quality': quality,
                'price': price,
                'status': 'open'
            }

            should_buy = False

            if product_type == self.preference:
                # Preferred fish
                if quality == 'good':
                    # Buy at high prices, reducing bid by 5% per purchase
                    threshold = self.preferred_price_thresholds['good']
                    if price <= threshold:
                        should_buy = True
                elif quality == 'normal':
                    # Reduce bid by 20% per purchase
                    threshold = self.preferred_price_thresholds['normal']
                    if price <= threshold:
                        should_buy = True
                elif quality == 'bad':
                    # 50% chance to skip
                    if random.random() < 0.5:
                        should_buy = False
                        self.log_info(f"Decided to skip bad quality preferred Fish {product_number}")
                    else:
                        threshold = self.preferred_price_thresholds['bad']
                        if price <= threshold:
                            should_buy = True
                else:
                    # Unrecognized quality, act as base class
                    super().on_product_info(message)
                    return
            else:
                # Non-preferred fish
                if self.inventory_counts[product_type] == 0:
                    if quality == 'good':
                        # Buy at 50% price
                        if price <= 15:
                            should_buy = True
                    elif quality == 'normal':
                        # Buy at 30% price
                        if price <= 9:
                            should_buy = True
                    else:
                        # Bad quality, do not buy
                        should_buy = False

            if should_buy:
                self.log_info(f"Attempting to buy Fish {product_number} at price {price} with quality {quality}")
                bid = {
                    'merchant_id': self.name,
                    'product_number': product_number,
                }
                self.send('bid_channel', bid)
                self.current_auctions[product_number]['status'] = 'pending'

    def on_confirmation(self, message):
        # Similar to base class but adjust thresholds per quality
        merchant_id = message.get('merchant_id')
        if merchant_id == self.name:
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

            if product_type == self.preference:
                # Adjust thresholds based on quality
                if quality == 'good':
                    old_threshold = self.preferred_price_thresholds['good']
                    self.preferred_price_thresholds['good'] *= 0.95  # Reduce by 5%
                    if self.preferred_price_thresholds['good'] < self.preferred_price_minimums['good']:
                        self.preferred_price_thresholds['good'] = self.preferred_price_minimums['good']
                    self.log_info(
                        f"Good quality threshold reduced from {old_threshold:.2f} to {self.preferred_price_thresholds['good']:.2f}")
                elif quality == 'normal':
                    old_threshold = self.preferred_price_thresholds['normal']
                    self.preferred_price_thresholds['normal'] *= 0.8  # Reduce by 20%
                    if self.preferred_price_thresholds['normal'] < self.preferred_price_minimums['normal']:
                        self.preferred_price_thresholds['normal'] = self.preferred_price_minimums['normal']
                    self.log_info(
                        f"Normal quality threshold reduced from {old_threshold:.2f} to {self.preferred_price_thresholds['normal']:.2f}")
                # No threshold adjustment for bad quality


class RichMerchantQuality(RichMerchant):
    def on_init(self):
        super().on_init()
        # Initialize thresholds per quality
        self.preferred_price_thresholds = {
            'good': 30,  # Starting threshold for good quality
            'normal': 30,
            'bad': 30
        }
        self.preferred_price_minimums = {
            'good': 30,  # No decrease for good quality
            'normal': 10,
            'bad': 10
        }

    def on_product_info(self, message):
        product_number = message.get('product_number')
        product_type = message.get('product_type')
        quality = message.get('quality', None)
        price = message.get('price')

        if quality is None:
            # If quality is not provided, act as base class
            super().on_product_info(message)
            return

        if self.budget >= price and self.current_auctions.get(product_number, {}).get('status') != 'closed':
            # Store auction details
            self.current_auctions[product_number] = {
                'product_type': product_type,
                'quality': quality,
                'price': price,
                'status': 'open'
            }

            should_buy = False

            if product_type == self.preference:
                # Preferred fish
                if quality == 'good':
                    # Buy at full price
                    if price <= 30:
                        should_buy = True
                elif quality == 'normal':
                    # Reduce bid as inventory grows
                    threshold = self.preferred_price_thresholds['normal']
                    if price <= threshold:
                        should_buy = True
                elif quality == 'bad':
                    # 80% chance to skip
                    if random.random() < 0.8:
                        should_buy = False
                        self.log_info(f"Decided to skip bad quality preferred Fish {product_number}")
                    else:
                        threshold = self.preferred_price_thresholds['bad']
                        if price <= threshold:
                            should_buy = True
                else:
                    # Unrecognized quality, act as base class
                    super().on_product_info(message)
                    return
            else:
                # Non-preferred fish
                if self.inventory_counts[product_type] == 0:
                    if quality == 'good':
                        # Buy at 50% price
                        if price <= 15:
                            should_buy = True
                    elif quality == 'normal':
                        # Buy at 30% price
                        if price <= 9:
                            should_buy = True
                    else:
                        # Bad quality, do not buy
                        should_buy = False

            if should_buy:
                self.log_info(f"Attempting to buy Fish {product_number} at price {price} with quality {quality}")
                bid = {
                    'merchant_id': self.name,
                    'product_number': product_number,
                }
                self.send('bid_channel', bid)
                self.current_auctions[product_number]['status'] = 'pending'

    def on_confirmation(self, message):
        # Similar to base class but adjust thresholds per quality
        merchant_id = message.get('merchant_id')
        if merchant_id == self.name:
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

            if product_type == self.preference:
                # Adjust thresholds based on quality
                if quality == 'normal':
                    old_threshold = self.preferred_price_thresholds['normal']
                    self.preferred_price_thresholds['normal'] *= 0.8  # Reduce by 20%
                    if self.preferred_price_thresholds['normal'] < self.preferred_price_minimums['normal']:
                        self.preferred_price_thresholds['normal'] = self.preferred_price_minimums['normal']
                    self.log_info(
                        f"Normal quality threshold reduced from {old_threshold:.2f} to {self.preferred_price_thresholds['normal']:.2f}")
                # No threshold adjustment for good or bad quality


class PoorMerchantQuality(PoorMerchant):
    def on_init(self):
        super().on_init()
        # Poor merchant ignores quality

    # Inherit on_product_info and on_confirmation without changes


class Coalition:
    def __init__(self, name, members):
        self.name = name
        self.members = members
        self.shared_budget = sum(member.budget for member in members)
        self.inventory = {}

    def update_budget(self):
        """Recalculate the coalition's shared budget."""
        self.shared_budget = sum(member.budget for member in self.members)

    def add_to_inventory(self, product, price):
        """Distribute purchased items among members."""
        # Simple round-robin allocation
        for member in self.members:
            if member.budget >= price:
                member.budget -= price
                if product not in member.inventory:
                    member.inventory[product] = 1
                else:
                    member.inventory[product] += 1
                break

    def log_info(self):
        """Log coalition's current state."""
        inventory_summary = {member.name: member.inventory for member in self.members}
        return {
            'Coalition Name': self.name,
            'Shared Budget': self.shared_budget,
            'Members': [member.name for member in self.members],
            'Inventory': inventory_summary
        }


    # Main program execution


if __name__ == '__main__':
    ns = run_nameserver()
    operator_type = input("Select the operator version:\n"
                          "1 for Infinite Operator\n"
                          "2 for Finite Operator\n"
                          "3 for Infinite Operator with Quality\n"
                          "4 for Finite Operator with Quality\n"
                          "Your choice: ")
    operator = None

    if operator_type == '1':
        operator = run_agent('OperatorInfinite', base=OperatorInfinite)
        use_quality_merchants = False
    elif operator_type == '2':
        total_fish_to_sell = int(input("Enter the total number of fish to sell: "))
        operator = run_agent(
            'OperatorFinite',
            base=OperatorFinite,
            attributes={'total_fish_to_sell': total_fish_to_sell}
        )
        use_quality_merchants = False
    elif operator_type == '3':
        operator = run_agent('OperatorInfiniteQuality', base=OperatorInfiniteQuality)
        use_quality_merchants = True
    elif operator_type == '4':
        total_fish_to_sell = int(input("Enter the total number of fish to sell: "))
        operator = run_agent(
            'OperatorFiniteQuality',
            base=OperatorFiniteQuality,
            attributes={'total_fish_to_sell': total_fish_to_sell}
        )
        use_quality_merchants = True
    else:
        print("Invalid operator type selected.")
        ns.shutdown()
        exit()

    # Prompt user for the number of each merchant type
    if use_quality_merchants:
        num_basic_merchants = int(input("Enter the number of Basic Merchants considering quality: "))
        num_rich_merchants = int(input("Enter the number of Rich Merchants considering quality: "))
        num_poor_merchants = int(input("Enter the number of Poor Merchants considering quality: "))
    else:
        num_basic_merchants = int(input("Enter the number of Basic Merchants: "))
        num_rich_merchants = int(input("Enter the number of Rich Merchants: "))
        num_poor_merchants = int(input("Enter the number of Poor Merchants: "))

    merchants = []
    merchants_info = []

    # Get operator's addresses
    publish_address = operator.addr('publish_channel')
    bid_address = operator.addr('bid_channel')

    # Create Basic Merchants
    for i in range(1, num_basic_merchants + 1):
        merchant_name = f'BasicMerchant_{i}'
        if use_quality_merchants:
            merchant = run_agent(merchant_name, base=BasicMerchantQuality)
        else:
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
            'Type': 'Basic' + ('Quality' if use_quality_merchants else ''),
            'Preference': merchant.get_attr('preference'),
            'Budget': merchant.get_attr('budget')
        })

    # Create Rich Merchants
    for i in range(1, num_rich_merchants + 1):
        merchant_name = f'RichMerchant_{i}'
        if use_quality_merchants:
            merchant = run_agent(merchant_name, base=RichMerchantQuality)
        else:
            merchant = run_agent(merchant_name, base=RichMerchant)
        merchant.set_attr(budget=500)

        # Connect merchant to operator's publish channel (SUB socket)
        merchant.connect(publish_address, handler='on_operator_message')

        # Merchant binds PUSH socket to send bids
        merchant.bind('PUSH', alias='bid_channel')
        # Merchant connects bid_channel to operator's bid_channel (PULL socket)
        merchant.connect(bid_address, alias='bid_channel')

        merchants.append(merchant)
        merchants_info.append({
            'Merchant': merchant_name,
            'Type': 'Rich' + ('Quality' if use_quality_merchants else ''),
            'Preference': merchant.get_attr('preference'),
            'Budget': merchant.get_attr('budget')
        })

    # Create Poor Merchants
    for i in range(1, num_poor_merchants + 1):
        merchant_name = f'PoorMerchant_{i}'
        if use_quality_merchants:
            merchant = run_agent(merchant_name, base=PoorMerchantQuality)
        else:
            merchant = run_agent(merchant_name, base=PoorMerchant)
        merchant.set_attr(budget=50)

        # Connect merchant to operator's publish channel (SUB socket)
        merchant.connect(publish_address, handler='on_operator_message')

        # Merchant binds PUSH socket to send bids
        merchant.bind('PUSH', alias='bid_channel')
        # Merchant connects bid_channel to operator's bid_channel (PULL socket)
        merchant.connect(bid_address, alias='bid_channel')

        merchants.append(merchant)
        merchants_info.append({
            'Merchant': merchant_name,
            'Type': 'Poor' + ('Quality' if use_quality_merchants else ''),
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
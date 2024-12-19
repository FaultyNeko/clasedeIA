import random
from osbrain import Agent

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









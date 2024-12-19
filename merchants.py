import random
from osbrain import Agent

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

    def get_name(self):
        """
        Return the name of the merchant for external access.
        """
        return self.name

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
        """
        Handles confirmation of purchase and updates inventory, budget, and price thresholds.
        """
        merchant_id = message.get('merchant_id')
        if merchant_id != self.name:
            return  # Ignore confirmations not meant for this merchant

        product_number = message.get('product_number')
        price = message.get('price')
        product_type = message.get('product_type')
        quality = message.get('quality', 'N/A')  # Ensure quality is logged correctly

        self.log_info(f"Purchase confirmed for Fish {product_number} at price {price} with quality {quality}")
        self.budget -= price

        # Update inventory with quality
        self.inventory[product_number] = {
            'type': product_type,
            'quality': quality,
            'price': price
        }
        self.inventory_counts[product_type] += 1
        self.log_info(f"Remaining budget: {self.budget}")


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